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
from semantic_kernel.contents.chat_history import ChatHistory
from app.models.code_wiki import ClassifyType, RepoWikiDocument, RepoWikiOverview, RepoWikiCommitRecord, ProcessingStatus
from app.aiframework.prompts.prompt_template_load import get_prompt_template
from app.aiframework.agent_frame.semantic.kernel_factory import KernelFactory
from app.config.settings import settings
from app.services.ai_kernel.functions.file_function import FileFunction
from app.services.common.local_repo_service import LocalRepoService
from app.services.code_wiki.document_service import CodeWikiDocumentService
from app.services.code_wiki.content_gen_service import CodeWikiContentGenService


@dataclass
class CommitResultDto:
    date: datetime
    title: str
    description: str

    def from_json(json_str: str) -> 'CommitResultDto':
        data = json.loads(json_str)
        return CommitResultDto(
            date=datetime.fromisoformat(data['date']),
            title=data['title'],
            description=data['description']
        )

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
            # 检查文档是否存在
            document = await CodeWikiDocumentService.get_wiki_document_by_id(self.session, self.document_id)
            if not document:
                raise ValueError(f"文档ID {self.document_id} 不存在")

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
            minmap = await self.generate_mini_map(repo_catalogue)

            # 步骤5: 生成项目概述
            overview = await self.generate_overview(repo_catalogue, readme, classify)
            
            # 步骤6: 生成目录结构
            content_gen_service = CodeWikiContentGenService(self.session, self.document_id, self.local_path, self.git_url, self.git_name, self.branch)
            wiki_catalogs = await content_gen_service.generate_wiki_catalogue(repo_catalogue, classify)
            
            # 步骤7: 生成目录结构中的文档内容
            await content_gen_service.generate_wiki_content(wiki_catalogs, repo_catalogue, classify)
            
            # 步骤8: 生成更新日志 (仅Git仓库)
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
                readme = None
                if kernel is not None:
                    prompt = get_prompt_template(
                        "app/services/ai_kernel/plugins/code_analysis/GenerateReadme", 
                        "generatereadme",
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
                    readme = str(result) if result else None
                else:
                    logging.error(f"创建AI内核失败，将回退到基础README。错误: {e}")
                    raise

            # 更新README内容
            #await CodeWikiDocumentService.update_wiki_document_fields(
            #    self.session, 
            #    self.document_id, 
            #    readme_content=readme
            #)

            return readme
        except Exception as e:
            logging.error(f"生成README失败: {e}")
            return ""
    
    async def generate_repo_catalogue(self, path: str, readme: str) -> str:
        """步骤2: 生成目录结构
        - 扫描目录统计条目数；小于阈值或未启用智能过滤时，直接构建优化目录结构
        - 否则启用 AI 智能过滤：使用 CodeAnalysis/CodeDirSimplifier 插件，支持重试与解析结果
        - 成功后写入 warehouse.optimized_directory_structure
        """
        try:
            # 获取配置参数
            enable_smart_filter = settings.code_wiki_gen.enable_smart_filter
            catalogue_format = settings.code_wiki_gen.catalogue_format

            # 获取目录文件列表
            path_infos = await LocalRepoService.get_folders_and_files(path)
            total_items = len(path_infos)
            catalogue = await LocalRepoService.get_catalogue_optimized(path, catalogue_format)

            if total_items > 800 and enable_smart_filter:
                # 启动AI智能过滤
                kernel_factory = KernelFactory()
                kernel = await kernel_factory.get_kernel(git_local_path=path, is_code_analysis=True)

                if kernel is not None:
                    result_text = ""
                    max_retries = 5
                    last_exception = None

                    for retry_idx in range(max_retries):
                        try:
                            simplify_fn = kernel.get_plugin("CodeAnalysis").get_function("CodeDirSimplifier")
                            if simplify_fn is not None:
                                result = await kernel.invoke(
                                    function=simplify_fn,
                                    arguments=KernelArguments(
                                        settings=PromptExecutionSettings(
                                            function_choice_behavior=FunctionChoiceBehavior.Auto()
                                        )
                                    ),
                                    kwargs={
                                        "code_files": catalogue,
                                        "readme": readme or ""
                                    }
                                )
                                result_text = str(result) if result else ""
                                last_exception = None
                                break
                            else:
                                logging.warning("未发现语义插件 CodeAnalysis/CodeDirSimplifier，回退为直接构建目录结构。")
                                break
                        except Exception as ex:
                            last_exception = ex
                            logging.error(f"优化目录结构失败，重试第{retry_idx + 1}次：{ex}")
                            await asyncio.sleep(5 * (retry_idx + 1))

                    if last_exception is not None:
                        logging.error(f"优化目录结构失败，已重试{max_retries}次：{last_exception}")

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
                kernel_factory = KernelFactory()
                kernel = await kernel_factory.get_kernel(git_local_path=self.local_path, is_code_analysis=False)

                prompt = await get_prompt_template("app/services/ai_kernel/prompts/Warehouse", "RepositoryClassification", {
                    "catalogue": catalogue,
                    "readme": readme
                })

                # 调用AI进行分类分析
                result = await kernel.invoke_prompt(
                    prompt=prompt,
                    arguments=KernelArguments(                    
                        temperature=0.1,
                        max_tokens=settings.llm.get_default_model().max_context_tokens,
                    ),
                    kwargs={
                        "code_files": catalogue,
                        "readme": readme or ""
                    }
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
                prompt_name += classify.value
            
            # 获取提示词模板
            prompt_template = get_prompt_template("app\services\ai_kernel\prompts\Warehouse", prompt_name, {
                    "catalogue": catalog,
                    "git_repository": self.git_url.replace(".git", ""),
                    "branch": self.branch,
                    "readme": readme
                }
            )
            if not prompt_template:
                logging.error(f"获取提示词模板失败: {prompt_name}")
                raise ValueError(f"获取提示词模板失败: {prompt_name}")

            # 启动AI智能过滤
            kernel_factory = KernelFactory()
            kernel = await kernel_factory.get_kernel(git_local_path=self.local_path, is_code_analysis=True)

            # 调用AI生成项目概述
            respone = await kernel.invoke_prompt(
                prompt=prompt_template,
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
            logs = repo.commits.order_by(lambda x: x.committer.when).take(20).order_by(lambda x: x.committer.when).to_list()

            commit_message = ""
            for commit in logs:
                commit_message += "提交人：" + commit.committer.name + "\n提交内容\n<message>\n" + commit.message + "<message>"
                commit_message += "\n提交时间：" + commit.committer.when.strftime("%Y-%m-%d %H:%M:%S") + "\n"

            kernel_factory = KernelFactory()
            kernel = await kernel_factory.get_kernel(git_local_path=self.local_path, is_code_analysis=True)
            # 2.3 调用生成 README 的语义插件
            log_result = None
            if kernel is not None:
                try:
                    generate_fn = kernel.get_plugin("CodeAnalysis").get_function("CommitAnalyze")
                    if generate_fn is not None:
                        result = await kernel.invoke(
                            function=generate_fn,
                            kwargs={
                                "readme": readme,
                                "git_repository": self.git_url,
                                "commit_message": commit_message,
                                "branch": self.branch
                            }
                        )
                        log_result = str(result) if result else None
                    else:
                        logging.warning("未发现语义插件 CodeAnalysis/CommitAnalyze，跳过AI生成。")
                        log_result = None
                except Exception as e:
                    logging.error(f"调用CommitAnalyze插件失败，将回退到基础README。错误: {e}")

            if log_result:
                match = re.search(r"<changelog>(.*?)</changelog>", log_result, re.DOTALL | re.IGNORECASE)
                if match:
                    log_result = match.group(1)

            commit_result = CommitResultDto.from_json(log_result)

            record = []
            for item in commit_result:
                record.append(RepoWikiCommitRecord(
                    document_id=self.document_id,
                    author="",
                    id=str(uuid.uuid4()),
                    commit_message=item.description,
                    title=item.title,                    
                    created_at=datetime.now()
                ))
            await self.session.execute(insert(RepoWikiCommitRecord).values(record))
            await self.session.commit()
            
        except Exception as e:
            logging.error(f"生成更新日志失败: {e}")
            raise