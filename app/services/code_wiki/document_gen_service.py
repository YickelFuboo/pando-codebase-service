import uuid
import re
import json
import asyncio
import logging
from git import Repo
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, delete, insert
from semantic_kernel.functions import KernelArguments
from semantic_kernel.connectors.ai import PromptExecutionSettings, FunctionChoiceBehavior
from app.config.settings import settings
from app.models.code_wiki import ProcessingStatus, ClassifyType, RepoWikiOverview, RepoWikiCommitRecord
from app.aiframework.prompts.prompt_template_load import get_prompt_template
from app.aiframework.agent_frame.semantic.kernel_factory import KernelFactory
from app.aiframework.agent_frame.semantic.functions.file_function import FileFunction
from app.services.common.local_repo_service import LocalRepoService
from app.services.code_wiki.document_service import CodeWikiDocumentService
from app.services.code_wiki.content_gen_service import CodeWikiContentGenService
from app.services.code_wiki.minimap_gen_service import MiniMapService


@dataclass
class CommitResultDto:
    date: datetime
    title: str
    description: str

    @staticmethod
    def from_json(json_str: str) -> 'CommitResultDto':
        data = json.loads(json_str)
        return CommitResultDto(
            date=datetime.fromisoformat(data['date']),
            title=data['title'],
            description=data['description']
        )
    
    @staticmethod
    def from_dict(data: dict) -> 'CommitResultDto':
        return CommitResultDto(
            date=datetime.fromisoformat(data['date']),
            title=data['title'],
            description=data['description']
        )
    
    @staticmethod
    def from_json_list(json_str: str) -> list['CommitResultDto']:
        data_list = json.loads(json_str)
        return [CommitResultDto.from_dict(item) for item in data_list]

class CodeWikiGenService:
    """Code Wiki服务类 - 提供代码Wiki的创建、更新和查询功能"""
    def __init__(self, session: AsyncSession, document_id: str, local_path: str, git_url: str, git_name: str, branch: str):
        self.session = session
        self.document_id = document_id
        self.local_path = local_path    
        self.git_url = git_url
        self.git_name = git_name
        self.branch = branch
    
    async def generate_wiki(self):
        """生成文档"""
        try:
            # 更新状态为处理中
            await CodeWikiDocumentService.update_processing_status(
                self.session, 
                self.document_id, 
                ProcessingStatus.Processing, 
                0, 
                "开始生成Wiki文档"
            )

            # 步骤1: 读取或生成README
            readme = await self.generate_readme()
            
            # 步骤2: 读取并且生成目录结构
            repo_catalogue = await self.generate_repo_catalogue(readme)
            
            # 步骤3: 读取或生成项目类别
            classify = await self.generate_classify(repo_catalogue, readme)
            
            # 步骤4: 生成知识图谱
            minimap_service = MiniMapService(self.session, self.document_id, self.local_path, self.git_url, self.branch, repo_catalogue)
            minmap = await minimap_service.generate_mini_map()

            # 步骤5: 生成项目概述
            overview = await self.generate_overview(repo_catalogue, readme, classify)
            
            # 步骤6: 生成目录结构 和目录结构中的文档内容
            content_gen_service = CodeWikiContentGenService(
                self.session, 
                self.document_id, 
                self.local_path, 
                self.git_url, 
                self.git_name, 
                self.branch,
                repo_catalogue,
                classify
            )
            await content_gen_service.generate_wiki_catalogue_and_content()
            
            # 步骤7: 生成更新日志 (仅Git仓库)
            if self.git_url:
                await self.generate_update_log(readme)
            
            # 更新状态为完成
            await CodeWikiDocumentService.update_processing_status(
                self.session, 
                self.document_id, 
                ProcessingStatus.Completed, 
                100, 
                "文档生成完成"
            )
            
            logging.info(f"AI文档处理完成: {self.document_id}")
            
        except Exception as e:
            logging.error(f"AI文档处理失败: {self.document_id}, 错误: {e}")
            
            # 更新状态为失败
            await CodeWikiDocumentService.update_processing_status(
                self.session, 
                self.document_id, 
                ProcessingStatus.Failed, 
                None, 
                f"文档生成失败: {str(e)}"
            )
            
            # 重新抛出异常，触发Celery重试
            raise

    async def generate_readme(self) -> str:
        """步骤1: 生成README文档
        1) 优先读取本地 README（多种扩展名）
        2) 若不存在，则获取目录结构并尝试通过语义插件 CodeAnalysis/GenerateReadme 生成
        3) 解析 <readme> 标签内容；若失败则直接使用原始文本
        4) 返回生成/读取的 README 文本（本项目模型暂无 readme 字段，暂不落库）
        """
        try:
            # 1. 优先读取现有 README
            readme: str = await LocalRepoService.get_readme_file(self.local_path)

            # 2. 若无本地 README，则使用AI生成
            if not readme:
                # 2.1 获取目录结构（紧凑格式）
                try:
                    catalogue = await LocalRepoService.get_catalogue(self.local_path)
                    # 确保传入SK的是字符串
                    if not isinstance(catalogue, str):
                        try:
                            catalogue = json.dumps(catalogue, ensure_ascii=False)
                        except Exception:
                            catalogue = str(catalogue)
                except Exception as e:
                    logging.warning(f"获取目录结构失败，将使用空目录结构。错误: {e}")
                    catalogue = ""

                # 2.2 创建 AI 内核（FileFunction 原生插件）
                kernel = await KernelFactory.get_kernel()
                kernel.add_plugin(FileFunction(self.local_path), "FileFunction")

                # 2.3 调用生成 README 的语义插件
                if kernel is not None:
                    prompt = get_prompt_template(
                        "app/aiframework/prompts/code_wiki", 
                        "GenerateReadme",
                        {
                            "catalogue": catalogue,
                            "git_repository": self.git_url,
                            "branch": self.branch,
                        }
                    )
                        
                    result = await kernel.invoke_prompt(
                        prompt=prompt,
                        arguments=KernelArguments(
                            settings=PromptExecutionSettings(
                                function_choice_behavior=FunctionChoiceBehavior.Auto()
                            )
                        )
                    )
                    generated = str(result) if result else None

                    if generated:
                        match = re.search(r"<readme>(.*?)</readme>", generated, re.DOTALL | re.IGNORECASE)
                        readme = match.group(1) if match else generated
                else:
                    logging.error(f"创建AI内核失败，将回退到基础README。错误: {e}")
                    raise

            # 更新README内容
            await CodeWikiDocumentService.update_wiki_document_fields(
                self.session, 
                self.document_id, 
                readme_content=readme
            )

            return readme
        except Exception as e:
            logging.error(f"生成README失败: {e}")
            return ""
    
    async def generate_repo_catalogue(self, readme: str) -> str:
        """步骤2: 生成目录结构
        - 扫描目录统计条目数；小于阈值或未启用智能过滤时，直接构建优化目录结构
        - 否则启用 AI 智能过滤：使用 CodeAnalysis/CodeDirSimplifier 插件，支持重试与解析结果
        - 成功后写入 warehouse.optimized_directory_structure
        """
        try:
            # 获取目录文件列表
            path_infos = await LocalRepoService.get_folders_and_files(self.local_path)
            total_items = len(path_infos)
            catalogue = await LocalRepoService.get_catalogue_optimized(self.local_path, settings.catalogue_format)

            if total_items > 800 and settings.enable_smart_filter:
                # 启动AI智能过滤
                kernel = await KernelFactory.get_kernel()
                kernel.add_plugin(FileFunction(self.local_path), "FileFunction")

                if kernel is not None:
                    result_text = ""
                    prompt = get_prompt_template(
                        "app/aiframework/prompts/code_wiki", 
                        "CodeDirSimplifier",
                        {
                            "readme": readme or "",
                            "code_files": catalogue
                        }
                    )

                    result = await kernel.invoke_prompt(
                        prompt=prompt,
                        arguments=KernelArguments(
                            settings=PromptExecutionSettings(
                                function_choice_behavior=FunctionChoiceBehavior.Auto()
                            )
                        )
                    )
                    result_text = str(result) if result else None
                else:
                    logging.error(f"创建AI内核失败，将回退到基础目录结构。错误: {e}")
                    raise

                # 3.2 解析 AI 输出，或在失败时回退
                if result_text:
                    # 解析 <response_file>...</response_file>
                    match = re.search(r"<response_file>(.*?)</response_file>", result_text, re.DOTALL | re.IGNORECASE)
                    if match:
                        catalogue = match.group(1)
                    else:
                        # 解析 ```json ... ```
                        json_match = re.search(r"```json(.*?)```", result_text, re.DOTALL | re.IGNORECASE)
                        if json_match:
                            catalogue = json_match.group(1).strip()
                        else:
                            catalogue = result_text

            # 4) 写入数据库
            if catalogue:
                await CodeWikiDocumentService.update_wiki_document_fields(
                    self.session, 
                    self.document_id, 
                    optimized_directory_struct=catalogue
                )
            return catalogue

        except Exception as e:
            logging.error(f"生成目录结构失败: {e}")
            return ""
    
    async def generate_classify(self, catalogue: str, readme: str) -> str:
        """步骤3: 生成项目类别"""
        try:
            document = await CodeWikiDocumentService.get_wiki_document_by_id(self.session, self.document_id)
            if not document:
                raise ValueError(f"文档ID {self.document_id} 不存在")

            # 如果数据库中没有项目分类，则使用AI进行分类分析
            classify = document.classify
            if not classify:
                # 启动AI智能过滤
                kernel = await KernelFactory.get_kernel()
                kernel.add_plugin(FileFunction(self.local_path), "FileFunction")

                prompt = get_prompt_template("app/aiframework/prompts/code_wiki", "RepositoryClassification", {
                    "category": catalogue,
                    "readme": readme
                })

                # 调用AI进行分类分析
                result = await kernel.invoke_prompt(
                    prompt=prompt,
                    arguments=KernelArguments(                    
                        temperature=0.1,
                    )
                )
                
                result_text = str(result) if result else ""

                classify = None
                if result_text:
                    match = re.search(r"<classify>(.*?)</classify>", result_text, re.DOTALL | re.IGNORECASE)
                    if match:
                        extracted = match.group(1) or ""
                        extracted = re.sub(r"^\s*classifyName\s*:\s*", "", extracted, flags=re.IGNORECASE).strip()
                        if extracted:
                            try:
                                classify = getattr(ClassifyType, extracted)
                            except AttributeError:
                                pass

            # 将项目分类结果保存到数据库
            await CodeWikiDocumentService.update_wiki_document_fields(
                self.session, 
                self.document_id, 
                classify=classify
            )
            
            return classify
        except Exception as e:
            logging.error(f"生成项目类别失败: {e}")
            return None

    async def generate_overview(
        self, 
        catalog: str, 
        readme: str, 
        classify: Optional[ClassifyType] = None
    ) -> str:
        """生成项目概述"""
        try:
            # 构建提示词名称
            prompt_name = "Overview"
            if classify:
                prompt_name += classify
            
            # 获取提示词模板
            prompt = get_prompt_template("app/aiframework/prompts/code_wiki", prompt_name, {
                    "catalogue": catalog,
                    "git_repository": self.git_url.replace(".git", ""),
                    "branch": self.branch,
                    "readme": readme
                }
            )
            if not prompt:
                logging.error(f"获取提示词模板失败: {prompt_name}")
                raise ValueError(f"获取提示词模板失败: {prompt_name}")

            # 启动AI智能过滤
            kernel = await KernelFactory.get_kernel()
            kernel.add_plugin(FileFunction(self.local_path), "FileFunction")

            # 调用AI生成项目概述
            respone = await kernel.invoke_prompt(
                prompt=prompt,
                arguments=KernelArguments(
                    settings=PromptExecutionSettings(
                        function_choice_behavior=FunctionChoiceBehavior.Auto()
                    )
                )
            )
            # 获取AI生成的结果
            result = str(respone) if respone else ""
            
            # 提取<blog></blog>中的内容
            blog_pattern = r'<blog>(.*?)</blog>'
            blog_match = re.search(blog_pattern, result, re.DOTALL)
            if blog_match:
                result = blog_match.group(1)
            
            # 提取```markdown中的内容
            markdown_pattern = r'```markdown(.*?)```'
            markdown_match = re.search(markdown_pattern, result, re.DOTALL)
            if markdown_match:
                result = markdown_match.group(1)
            
            overview = result.strip()

            # 新增 或 更新overview表内容
            await self.session.execute(
               delete(RepoWikiOverview)
                .where(RepoWikiOverview.document_id == self.document_id)
            )
            await self.session.commit()

            # 保存新的项目概述到数据库
            await self.session.execute(
                insert(RepoWikiOverview)
                .values(
                    content=overview,
                    title="",
                    document_id=self.document_id,
                    id=str(uuid.uuid4())
                )
            )
            await self.session.commit()

            return overview

        except Exception as e:
            print(f"生成项目概述失败: {e}")
            return ""

    async def generate_update_log(self, readme: str):
        try:
            # 删除旧的提交记录
            await self.session.execute(
                delete(RepoWikiCommitRecord).where(RepoWikiCommitRecord.document_id == self.document_id)
            )

            # 读取git log
            repo = Repo(self.local_path)
            commits = list(repo.iter_commits(max_count=20))
            logs = sorted(commits, key=lambda x: x.committed_datetime, reverse=True)

            commit_message = ""
            for commit in logs:
                commit_message += "提交人：" + commit.committer.name + "\n提交内容\n<message>\n" + commit.message + "<message>"
                commit_message += "\n提交时间：" + commit.committed_datetime.strftime("%Y-%m-%d %H:%M:%S") + "\n"

            kernel = await KernelFactory.get_kernel()
            kernel.add_plugin(FileFunction(self.local_path), "FileFunction")

            # 2.3 调用生成 README 的语义插件
            log_result = None
            if kernel is not None:
                prompt = get_prompt_template("app/aiframework/prompts/code_wiki", "CommitAnalyze", {
                    "readme": readme,
                    "git_repository": self.git_url,
                    "commit_message": commit_message,
                    "branch": self.branch
                })

                result = await kernel.invoke_prompt(
                    prompt=prompt,
                    arguments=KernelArguments(
                        settings=PromptExecutionSettings(
                            function_choice_behavior=FunctionChoiceBehavior.Auto()
                        )
                    )
                )
                log_result = str(result) if result else None
            else:
                logging.error(f"创建AI内核失败，将回退到基础更新日志。错误: {e}")
                raise

            if log_result:
                match = re.search(r"<changelog>(.*?)</changelog>", log_result, re.DOTALL | re.IGNORECASE)
                if match:
                    log_result = match.group(1)

            commit_results = CommitResultDto.from_json_list(log_result)

            records = []
            for item in commit_results:
                records.append({
                    "id": str(uuid.uuid4()),
                    "document_id": self.document_id,
                    "commit_id": "",
                    "commit_message": item.description,
                    "title": item.title,
                    "author": "",
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                })
            await self.session.execute(insert(RepoWikiCommitRecord).values(records))
            await self.session.commit()
            
        except Exception as e:
            logging.error(f"生成更新日志失败: {e}")
            raise