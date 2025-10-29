import uuid
import re
import json
import asyncio
import os
import logging
from git import Repo
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, delete, insert
from semantic_kernel.functions import KernelArguments
from semantic_kernel.connectors.ai import PromptExecutionSettings, FunctionChoiceBehavior
from sqlalchemy.orm.session import Session
from app.aiframework.prompts.prompt_template_load import get_prompt_template
from app.models.code_wiki import ClassifyType, RepoWikiCatalog, RepoWikiContent
from app.services.ai_kernel.kernel_factory import KernelFactory
from semantic_kernel.contents.chat_history import ChatHistory
from app.config.settings import settings
from app.services.ai_kernel.functions.file_function import FileFunction
from app.services.common.local_repo_service import LocalRepoService
from app.services.code_wiki.document_service import CodeWikiDocumentService
from app.services.git_repo_service import GitRepositoryService

@dataclass
class DocumentResultCatalogueItem:
    """文档目录项"""
    name: str = ""
    title: str = ""
    prompt: str = ""
    children: Optional[List['DocumentResultCatalogueItem']] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []

class CodeWikiContentGenService:
    """Code Wiki服务类 - 提供代码Wiki的创建、更新和查询功能"""
    def __init__(self, session: AsyncSession, document_id: str, local_path: str, git_url: str, git_name: str, branch: str):
        self.session = session
        self.document_id = document_id
        self.local_path = local_path    
        self.git_url = git_url
        self.git_name = git_name
        self.branch = branch
    
    async def generate_wiki_catalogue(
        self, 
        catalogue: str,
        classify: Optional[ClassifyType] = None
    ) -> List[RepoWikiCatalog]:
        """生成目录"""
        try:
            doucument = await CodeWikiDocumentService.get_wiki_document_by_id(self.session, self.document_id)
            if not doucument:
                raise ValueError(f"文档ID {self.document_id} 不存在")

            # 构建提示词名称
            prompt_name = "AnalyzeCatalogue"
            if classify:
                prompt_name += classify.value

            prompt = await get_prompt_template("app/services/ai_kernel/prompts/Warehouse", prompt_name, {
                "code_files": catalogue,
                "git_repository_url": self.git_url.replace(".git", ""),
                "repository_name": self.git_name
            })

            if not prompt:
                logging.error(f"获取提示词模板失败: {prompt_name}")
                raise ValueError(f"获取提示词模板失败: {prompt_name}")

            # 获取系统提示词
            system_prompt = await get_prompt_template("app/services/ai_kernel/prompts/Warehouse", "SystemExtensionPrompt")

            history = ChatHistory()
            history.add_system_message(system_prompt)
            history.add_user_message(prompt)
            history.add_assistant_message("Ok. Now I will start analyzing the core file. And I won't ask you questions or notify you. I will directly provide you with the required content. Please confirm")
            history.add_user_message("OK, I confirm that you can start analyzing the core file now. Please proceed with the analysis and provide the relevant content as required. There is no need to ask questions or notify me. The generated document structure will be refined and a complete and detailed directory structure of document types will be provided through project file reading and analysis.")

            kernel_factory = KernelFactory()
            kernel = await kernel_factory.get_kernel(git_local_path=self.local_path, is_code_analysis=False)
            
            # 创建分析模型内核
            kernel = KernelFactory.get_kernel(self.local_path, is_code_analysis=False)
            response = await kernel.invoke_prompt(
                prompt={{history}},
                arguments=KernelArguments(
                    settings=PromptExecutionSettings(
                        function_choice_behavior=FunctionChoiceBehavior.Auto()
                    ),
                    Temperature=0.5,
                    max_tokens=settings.llm.get_default_model().max_context_tokens,
                    history=history,
                ),
                kwargs={
                    "code_files": catalogue,
                    "git_repository_url": self.git_url.replace(".git", ""),
                    "repository_name": self.git_name,
                },
            )
            result_str = str(response)

            if settings.refine_and_enhance_quality:
                history.add_assistant_message(result_str)
                history.add_user_message("The directory you have provided now is not detailed enough, and the project code files have not been carefully analyzed.  Generate a complete project document directory structure and conduct a detailed analysis Organize hierarchically with clear explanations for each component's role and functionality. Please do your best and spare no effort.")

                response = await kernel.invoke_prompt(
                    prompt={{history}},
                    arguments=KernelArguments(
                        settings=PromptExecutionSettings(
                            function_choice_behavior=FunctionChoiceBehavior.Auto()
                        ),
                        Temperature=0.5,
                        max_tokens=settings.llm.get_default_model().max_context_tokens,
                        history=history,
                    ),
                    kwargs={
                        "code_files": catalogue,
                        "git_repository_url": self.git_url.replace(".git", ""),
                        "repository_name": self.git_name,
                    },
                )
                result_str = str(response)
                    
            # 提取JSON内容
            result_str = self._extract_json_content(result_str)
            
            # 解析JSON
            catalogue_result = []
            result_data = json.loads(result_str.strip())
            items = result_data.get("items", [])
            for item_data in items:
                catalogue_item = self._create_catalogs_item(item_data)
                catalogue_result.append(catalogue_item)

            # 结果转换为RepoWikiCatalog
            wiki_catalogs = []
            self._cover_to_repo_wiki_catalogs(catalogue_result, None, wiki_catalogs)

            # 删除遗留的目录数据
            await self.session.execute(
                delete(RepoWikiCatalog).where(RepoWikiCatalog.document_id == self.document_id)
            )
            # 将解析的目录结构保存到数据库
            await self.session.add_all(wiki_catalogs)
            await self.session.commit()

            return wiki_catalogs

        except Exception as e:
            logging.warning(f"处理仓库 {self.local_path}, 处理标题 {self.git_name} 失败: {e}")
            return None
    
    def _extract_json_content(self, content: str) -> str:
        """提取JSON内容"""
        doc_pattern = r'<documentation_structure>(.*?)</documentation_structure>'
        doc_match = re.search(doc_pattern, content, re.DOTALL)
        
        if doc_match:
            return doc_match.group(1)
        
        # 尝试提取```json代码块
        json_pattern = r'```json(.*?)```'
        json_match = re.search(json_pattern, content, re.DOTALL)
        
        if json_match:
            return json_match.group(1)
        
        # 尝试提取JSON对象
        json_obj_pattern = r'\{(?:[^{}]|(?<open>{)|(?<-open>}))*(?(open)(?!))\}'
        json_obj_match = re.search(json_obj_pattern, content, re.DOTALL)
        
        if json_obj_match:
            return json_obj_match.group(0)
        
        return content

    def _create_catalogs_item(self, item_data: dict) -> DocumentResultCatalogueItem:
        """从字典数据创建目录项"""
        item = DocumentResultCatalogueItem(
            name=item_data.get("name", ""),
            title=item_data.get("title", ""),
            prompt=item_data.get("prompt", "")
        )
        
        # 递归处理子项
        children_data = item_data.get("children", [])
        if children_data:
            for child_data in children_data:
                child_item = self._create_catalogs_item(child_data)
                item.children.append(child_item)
        
        return item

    def _cover_to_repo_wiki_catalogs(self, items: List[dict], parent_id: Optional[str], catalogs: List[RepoWikiCatalog]):
        """处理目录项，递归生成文档目录 - 基于DocumentsHelper逻辑"""
        order = 0
        for item in items:
            title = item.get("title", "").replace(" ", "")
            name = item.get("name", "")
            prompt = item.get("prompt", "")
            children = item.get("children", [])
            
            catalog_item = RepoWikiCatalog(
                id=str(uuid.uuid4()),
                document_id=self.document_id,
                name=name,
                url=title,
                description=title,
                parent_id=parent_id,
                prompt=prompt,
                order=order
            )
            order += 1
            
            catalogs.append(catalog_item)
            
            if children:
                self.cover_to_repo_wiki_catalogs(children, catalog_item.id, catalogs)
            
    async def generate_wiki_content(
        self, 
        wiki_catalogs: List[RepoWikiCatalog], 
        repo_catalogue: str, 
        classify: Optional[ClassifyType] = None
    ) -> List[RepoWikiContent]:
        
        try:
            # 生成章节内容
            for catalog in wiki_catalogs:
                await self.generate_single_wiki_content(catalog, repo_catalogue, classify)
        except Exception as e:
            logging.error(f"生成章节内容失败: {e}")
            return []

    async def generate_single_wiki_content(
        self,
        wiki_catalog: RepoWikiCatalog, 
        repo_catalogue: str, 
        classify) -> RepoWikiContent:
        try:        
            # 构建提示词名称
            prompt_name = "GenerateDocs"
            if classify:
                prompt_name += classify
            
            # 获取提示词模板
            prompt = await get_prompt_template("app/services/ai_kernel/prompts/Warehouse", prompt_name)
            system_prompt = await get_prompt_template("app/services/ai_kernel/prompts/Warehouse", "SystemExtensionPrompt")

            history = ChatHistory()
            history.add_system_message(system_prompt)
            history.add_user_message(prompt)

            kernel_factory = KernelFactory()
            kernel = await kernel_factory.get_kernel(git_local_path=self.local_path, is_code_analysis=False)

            # 非流式调用
            result = await kernel.invoke_prompt(
                prompt="{{history}}",
                arguments=KernelArguments(
                    settings=PromptExecutionSettings(
                        function_choice_behavior=FunctionChoiceBehavior.Auto()
                    ),
                    Temperature=0.5,
                    max_tokens=settings.llm.get_default_model().max_context_tokens,
                    history=history,
                ),
                kwargs={
                    "catalogue": repo_catalogue,
                    "prompt": wiki_catalog.prompt,
                    "git_repository": (self.git_url or "").replace(".git", ""),
                    "branch": self.branch,
                    "title": wiki_catalog.name
                },
            )
            result_str = str(result) if result else ""


            if settings.refine_and_enhance_quality:
                history.add_assistant_message(result_str)
                history.add_user_message("""
                    You need to further refine the previous content and provide more detailed information. All the content comes from the code repository and the style of the documentation should be more standardized.
                    Create thorough documentation that:
                    - Covers all key functionality with precise technical details
                    - Includes practical code examples and usage patterns  
                    - Ensures completeness without gaps or omissions
                    - Maintains clarity and professional quality throughout
                    Please do your best and spare no effort.
                    """)

                # 流式调用，聚合文本
                result = await kernel.invoke_prompt(
                    prompt="{{history}}",
                    arguments=KernelArguments(
                        settings=PromptExecutionSettings(
                            function_choice_behavior=FunctionChoiceBehavior.Auto()
                        ),
                        Temperature=0.5,
                        max_tokens=settings.llm.get_default_model().max_context_tokens,
                        history=history,
                    ),
                    kwargs={
                        "catalogue": repo_catalogue,
                        "prompt": wiki_catalog.prompt,
                        "git_repository": (self.git_url or "").replace(".git", ""),
                        "branch": self.branch,
                        "title": wiki_catalog.name
                    },
                )
                result_str = str(result) if result else ""
            
            # 提取JSON内容
            result_str = self._extract_document_item_json_content(result_str)

            repo_wiki_content = RepoWikiContent(
                content=result_str,
                catalog_id=wiki_catalog.id,
                title=wiki_catalog.name,
                description="",
                size=0,
                source_file_items=[],
                meta_data={},
                extra={})

            # 保存数据到数据库
            self.session.add(repo_wiki_content)
            await self.session.commit()

            return repo_wiki_content
            
        except Exception as e:
            logging.error(f"生成章节内容失败: {e}, catalog: {wiki_catalog.name}")
            return None
        
    @staticmethod
    def _extract_document_item_json_content(content: str) -> str:
        """提取JSON内容 - 基于C#代码逻辑"""
        # 删除内容中所有的<thinking>内的内容，可能存在多个<thinking>标签
        thinking_pattern = r'<thinking>.*?</thinking>'
        content = re.sub(thinking_pattern, '', content, flags=re.DOTALL)
        
        # 使用正则表达式将<blog></blog>中的内容提取
        blog_pattern = r'<blog>(.*?)</blog>'
        blog_match = re.search(blog_pattern, content, re.DOTALL)
        
        if blog_match:
            # 提取到的内容
            content = blog_match.group(1)
        
        content = content.strip()
        
        # 删除所有的<think></think>
        think_pattern = r'<think>.*?</think>'
        content = re.sub(think_pattern, '', content, flags=re.DOTALL)
        
        # 从docs提取
        docs_pattern = r'<docs>(.*?)</docs>'
        docs_match = re.search(docs_pattern, content, re.DOTALL)
        if docs_match:
            # 提取到的内容
            extracted_docs = docs_match.group(1)
            content = content.replace(docs_match.group(0), extracted_docs)
        
        return content