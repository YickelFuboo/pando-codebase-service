import asyncio
import os
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
import logging
import httpx
from app.models.code_wiki import RepoWikiDocument, ProcessingStatus, RepoWikiCatalog, RepoWikiContent, RepoWikiContentSource
from app.services.common.file_tree_service import PathInfo
from app.services.common.local_repo_service import LocalRepoService
from app.services.code_wiki.document_service import CodeWikiDocumentService
from app.aiframework.prompts.prompt_template_load import get_prompt_template
from app.config.settings import settings


class Mem0Client:
    """Mem0客户端"""
    
    def __init__(self):
        self.api_key = settings.mem0_api_key
        self.endpoint = settings.mem0_endpoint
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(600),  # 10分钟超时
            headers={
                "User-Agent": "KoalaWiki/1.0",
                "Authorization": f"Bearer {settings.mem0_api_key}"
            }
        )
    
    async def add_message(self, messages: List[Dict[str, str]], user_id: str, 
                         metadata: Dict[str, Any], memory_type: str = "procedural_memory") -> bool:
        """添加消息到Mem0"""
        try:
            payload = {
                "messages": messages,
                "user_id": user_id,
                "metadata": metadata,
                "memory_type": memory_type
            }
            
            response = await self.client.post(
                f"{self.endpoint}/add",
                json=payload
            )
            
            if response.status_code == 200:
                logging.info(f"成功添加消息到Mem0: {user_id}")
                return True
            else:
                logging.error(f"添加消息到Mem0失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logging.error(f"Mem0客户端错误: {e}")
            return False
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


class Mem0Rag:
    """Mem0 RAG服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.mem0_client = None
        
        if hasattr(settings, 'enable_mem0') and settings.enable_mem0:
            self.mem0_client = Mem0Client(
                settings.mem0_api_key,
                settings.mem0_endpoint
            )
    
    async def process_repo_wiki_document(self, document_id: str) -> bool:
        """处理仓库的Mem0嵌入"""
        try:
            if not self.mem0_client:
                logging.warning("Mem0功能未启用")
                return False
            
            # 获取文档信息
            document_result = await self.db.execute(
                select(RepoWikiDocument).where(
                    RepoWikiDocument.id == document_id,
                    RepoWikiDocument.processing_status == ProcessingStatus.Completed,
                    RepoWikiDocument.is_embedded == False
                )
            )
            document = document_result.scalar_one_or_none()
            
            if not document:
                logging.info(f"文档 {document_id} 不存在或已处理完成")
                return False
            
            # 获取文件列表
            files = LocalRepoService.get_folders_and_files(document.git_path)
            
            # 获取已完成的目录
            catalogs_result = await self.db.execute(
                select(RepoWikiCatalog).where(
                    RepoWikiCatalog.document_id == document.id,
                    RepoWikiCatalog.is_completed == True,
                    RepoWikiCatalog.is_deleted == False
                )
            )
            catalogs = catalogs_result.scalars().all()
            
            # 处理目录内容
            await self._process_catalogs(catalogs, document)
            
            # 处理文件内容
            await self._process_files(files, document)
            
            # 标记仓库为已嵌入
            await self._mark_repo_wiki_document_embedded(document_id)
            
            logging.info(f"文档 {document_id} Mem0处理完成")
            return True
            
        except Exception as e:
            logging.error(f"处理文档Mem0失败: {e}")
            return False
    
    async def _process_catalogs(self, catalogs: List[RepoWikiCatalog], document: RepoWikiDocument):
        """处理目录内容"""
        for catalog in catalogs:
            try:
                # 获取目录内容
                content_result = await self.db.execute(
                    select(RepoWikiContent).where(
                        RepoWikiContent.catalog_id == catalog.id
                    )
                )
                content = content_result.scalar_one_or_none()
                
                if not content or not content.content:
                    logging.warning(f"目录 {catalog.name} 内容为空，跳过")
                    break
                
                # 获取依赖文件
                sources_result = await self.db.execute(
                    select(RepoWikiContentSource).where(
                        RepoWikiContentSource.content_id == content.id
                    )
                )
                dependent_files = sources_result.scalars().all()
                
                # 获取系统提示词
                system_prompt = await get_prompt_template("app/services/ai_kernel/prompts/Mem0", "DocsSystem")
                if not system_prompt:
                    system_prompt = "你是一个文档分析助手。"
                
                # 构建消息
                messages = [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": f"""# {catalog.name}
<file name="{catalog.url}">
{content.content}
</file>"""
                    }
                ]
                
                # 构建元数据
                metadata = {
                    "id": catalog.id,
                    "name": catalog.name,
                    "url": catalog.url,
                    "documentId": document.id,
                    "type": "docs",
                    "reference": [
                        {
                            "id": source.id,
                            "name": source.name,
                            "address": source.address,
                            "created_at": source.created_at.isoformat() if source.created_at else None
                        }
                        for source in dependent_files
                    ]
                }
                
                # 添加到Mem0
                success = await self.mem0_client.add_message(
                    messages, document.id, metadata, "procedural_memory"
                )
                
                if success:
                    logging.info(f"成功处理目录: {catalog.name}")
                    break
                else:
                    raise Exception("Mem0添加失败")
                    
            except Exception as e:
                logging.warning(f"处理目录 {catalog.name} 失败: {e}")
                raise
    
    async def _process_files(self, files: List[PathInfo], document: RepoWikiDocument):
        """处理文件内容"""
        file_failure_count = 0
        file_failure_threshold = 5
        circuit_broken = False
        
        for file in files:
            if circuit_broken:
                break
            
            try:
                # 读取文件内容
                if not os.path.exists(file.path):
                    logging.warning(f"文件不存在: {file.path}")
                    continue
                
                with open(file.path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if not content.strip():
                    logging.warning(f"文件 {file.path} 内容为空，跳过")
                    continue
                
                # 获取系统提示词
                system_prompt = await get_prompt_template("app/services/ai_kernel/prompts/Mem0", "CodeSystem")
                if not system_prompt:
                    system_prompt = "你是一个代码分析助手。"
                
                # 构建消息
                relative_path = file.path.replace(document.git_path, "").lstrip("/").lstrip("\\")
                messages = [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": f"```{relative_path}\n{content}\n```"
                    }
                ]
                
                # 构建元数据
                metadata = {
                    "fileName": file.name,
                    "filePath": file.path,
                    "fileType": os.path.splitext(file.path)[1] if file.path else "",
                    "type": "code",
                    "documentId": document.id
                }
                
                # 添加到Mem0
                success = await self.mem0_client.add_message(
                    messages, document.id, metadata, "procedural_memory"
                )
                
                if success:
                    logging.info(f"成功处理文件: {file.path}")
                else:
                    raise Exception("Mem0添加失败")
                    
            except Exception as e:
                file_failure_count += 1
                logging.error(f"处理文件 {file.path} 失败: {e}")
                
                if file_failure_count >= file_failure_threshold:
                    logging.error("文件处理连续失败超过阈值，触发熔断，停止后续处理。")
                    circuit_broken = True
    
    async def _mark_repo_wiki_document_embedded(self, document_id: str):
        """标记仓库为已嵌入"""
        try:
            await self.db.execute(
                update(RepoWikiDocument)
                .where(RepoWikiDocument.id == document_id)
                .values(is_embedded=True)
            )
            await self.db.commit()
            logging.info(f"文档 {document_id} 已标记为已嵌入")
        except Exception as e:
            logging.error(f"标记文档嵌入状态失败: {e}")
            await self.db.rollback()
    
    async def close(self):
        """关闭服务"""
        if self.mem0_client:
            await self.mem0_client.close() 