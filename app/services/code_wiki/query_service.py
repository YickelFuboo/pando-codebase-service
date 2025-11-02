import zipfile
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import io
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.models.code_wiki import RepoWikiCatalog, RepoWikiContent, RepoWikiOverview, RepoWikiCommitRecord, RepoWikiMiniMap
from app.schemes.code_wiki import RepoWikiCatalogTreeItem, RepoWikiCatalogResponse, RepoWikiContentResponse, RepoWikiContentSourceResponse, UpdateRepoWikiCatalogRequest, UpdateRepoWikiContentRequest
from app.services.git_repo_service import GitRepositoryService
from app.services.code_wiki.document_service import CodeWikiDocumentService


class CodeWikiQueryService:
    """CodeWiki查询服务"""

    async def get_overview(
        db: AsyncSession, 
        document_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """获取仓库概述"""
        try:           
            # 获取仓库信息
            document = await CodeWikiDocumentService.get_wiki_document_by_id(db, document_id)
            if not document:
                raise ValueError(f"文档ID {document_id} 不存在")
                        
            # 获取概述
            overview_result = await db.execute(
                select(RepoWikiOverview).where(RepoWikiOverview.document_id == document.id)
            )
            overview = overview_result.scalar_one_or_none()
            
            if not overview:
                raise ValueError(f"文档ID {document_id} 没有找到概述")
            
            return {
                "title": overview.title,
                "content": overview.content
            }
            
        except Exception as e:
            logging.error(f"获取仓库概述失败: {str(e)}")
            raise ValueError(f"获取仓库概述失败: {str(e)}") 
    
    @staticmethod
    async def get_catalogs(db: AsyncSession, document_id: str, user_id: str) -> List[RepoWikiCatalog]:
        """获取目录列表"""
        try:
            # 获取仓库信息
            document = await CodeWikiDocumentService.get_wiki_document_by_id(db, document_id)
            if not document:
                raise ValueError(f"文档ID {document_id} 不存在")

            repo = await GitRepositoryService.get_repository_by_id(db, document.repo_id)
            if not repo:
                raise ValueError(f"仓库ID {document.repo_id} 不存在")

            # 查找目录
            catalogs_result = await db.execute(
                select(RepoWikiCatalog).where(
                    RepoWikiCatalog.document_id == document.id,
                    RepoWikiCatalog.is_deleted == False
                )
            )
            catalogs = catalogs_result.scalars().all()
            
            # 构建目录树
            items = CodeWikiQueryService._build_document_tree(catalogs)
            
            # 计算进度
            completed_count = sum(1 for catalog in catalogs if catalog.is_completed)
            progress = (completed_count * 100 // len(catalogs)) if catalogs else 0
            
            return RepoWikiCatalogResponse(
                items=items,
                last_update=document.updated_at if document else None,
                description=document.description if document else None,
                progress=progress,
                git=repo.repository_url,
                branchs=[repo.branch],
                document_id=document.id,
            )
            
        except Exception as e:
            logging.error(f"获取文档目录失败: {e}")
            raise

    @staticmethod
    def _build_document_tree(self, catalogs: List[RepoWikiCatalog]) -> List[RepoWikiCatalogTreeItem]:
        """构建文档树"""
        # 创建根节点列表
        root_items = []
        
        # 创建所有节点的映射
        node_map = {}
        for cat in catalogs:
            node_map[cat.id] = RepoWikiCatalogTreeItem(
                id=cat.id,
                name=cat.name,
                url=cat.url,
                description=cat.description,
                parent_id=cat.parent_id,
                order=cat.order,
                is_completed=cat.is_completed,
                prompt=cat.prompt,
                children=[]
            )
        
        # 构建树结构
        for cat in catalogs:
            node = node_map[cat.id]
            if cat.parent_id and cat.parent_id in node_map:
                # 添加到父节点
                parent = node_map[cat.parent_id]
                parent.children.append(node)
            else:
                # 根节点
                root_items.append(node)
        
        # 按order排序
        def sort_children(items):
            items.sort(key=lambda x: x.order)
            for item in items:
                sort_children(item.children)
        
        sort_children(root_items)
        return root_items 
    
    @staticmethod
    async def get_catalog_contents_by_id(db: AsyncSession, catalog_id: str) -> Optional[RepoWikiContentResponse]:
        """根据目录id获取文件"""
        try:  
            # 查找目录
            catalog_result = await db.execute(
                select(RepoWikiCatalog).where(
                    RepoWikiCatalog.id == catalog_id,
                    RepoWikiCatalog.is_deleted == False
                )
            )
            catalog = catalog_result.scalar_one_or_none()
            
            if not catalog:
                raise ValueError(f"目录ID {catalog_id} 不存在")
            
            # 查找内容
            content_result = await db.execute(
                select(RepoWikiContent).where(RepoWikiContent.catalog_id == catalog.id)
            )
            content = content_result.scalar_one_or_none()
            
            if not content:
                raise ValueError(f"目录ID {catalog_id} 没有找到内容")
            
            # 查询内容源
            sources = []
            for source in content.sources:
                sources.append(RepoWikiContentSourceResponse(
                    id=source.id,
                    content_id=source.content_id,
                    source_path=source.source_path,
                    source_name=source.source_name
                ))
            
            return RepoWikiContentResponse(
                id=content.id,
                catalog_id=content.catalog_id,
                title=content.title,
                description=content.description,
                content=content.content,
                size=content.size,
                source_file_items=content.source_file_items,
                meta_data=content.meta_data,
                extra=content.extra,
                sources=sources
            )
            
        except Exception as e:
            logging.error(f"获取文档文件失败: {e}")
            raise

    @staticmethod
    async def get_change_log(db: AsyncSession, document_id: str, user_id: str) -> Optional[RepoWikiCommitRecord]:
        """获取变更日志"""
        try:
            # 获取仓库信息
            document = await CodeWikiDocumentService.get_wiki_document_by_id(db, document_id)
            if not document:
                raise ValueError(f"文档ID {document_id} 不存在")
            
            # 获取提交记录
            commits_result = await db.execute(
                select(RepoWikiCommitRecord).where(RepoWikiCommitRecord.document_id == document.id)
            )
            commits = commits_result.scalars().all()
            
            # 构建变更日志内容
            content = []
            for record in commits:
                content.append(f"## {record.created_at.strftime('%Y-%m-%d %H:%M:%S')} {record.title}")
                content.append(f" {record.commit_message}")
            
            # 创建变更日志记录
            change_log = RepoWikiCommitRecord(
                commit_id="",
                commit_message="\n".join(content),
                created_at=datetime.now(),
                title="更新日志",
                last_update=datetime.now(),
                document_id=document_id,
            )
            
            return change_log
            
        except Exception as e:
            logging.error(f"获取变更日志失败: {str(e)}")
            raise ValueError(f"获取变更日志失败: {str(e)}") 

    @staticmethod
    async def get_mini_map(db: AsyncSession, document_id: str) -> Dict[str, Any]:
        try:
            # 获取仓库信息
            document = await CodeWikiDocumentService.get_wiki_document_by_id(db, document_id)
            if not document:
                raise ValueError(f"文档ID {document_id} 不存在")

            repo = await GitRepositoryService.get_repository_by_id(db, document.repo_id)
            if not repo:
                raise ValueError(f"仓库ID {document.repo_id} 不存在")
            
            # 查找思维导图
            mini_map_result = await db.execute(
                select(RepoWikiMiniMap).where(RepoWikiMiniMap.document_id == document.id)
            )
            mini_map = mini_map_result.scalar_one_or_none()
            
            if not mini_map:
                return {
                    "code": 200,
                    "message": "没有找到知识图谱",
                    "data": {}
                }
            
            # 解析思维导图数据
            mini_map_data = json.loads(mini_map.value)
            
            # 构建跳转地址
            address = repo.repository_url.replace(".git", "").rstrip('/').lower()            
            if "github.com" in address:
                address += f"/tree/{repo.branch}/"
            elif "gitee.com" in address:
                address += f"/tree/{repo.branch}/"
            
            # 更新节点URL
            def update_url(node):
                if node.get("url", "").startswith("http"):
                    node["url"] = node["url"].replace(repo.repository_url, "")
                
                if node.get("url") and not node["url"].startswith("http"):
                    node["url"] = address + node["url"].lstrip('/')
                
                for child in node.get("nodes", []):
                    update_url(child)
            
            for node in mini_map_data.get("nodes", []):
                update_url(node)
            
            return {
                "code": 200,
                "message": "获取知识图谱成功",
                "data": mini_map_data
            }
            
        except Exception as e:
            logging.error(f"获取思维导图失败: {str(e)}")
            raise ValueError(f"获取思维导图失败: {str(e)}") 

    @staticmethod
    async def export_markdown_zip(db: AsyncSession, document_id: str, user_id: str) -> bytes:
        """导出Markdown压缩包"""
        try:
            # 获取仓库信息
            document = await CodeWikiDocumentService.get_wiki_document_by_id(db, document_id)
            if not document:
                raise ValueError(f"文档ID {document_id} 不存在")
            
            # 获取文档目录
            catalogs_result = await db.execute(
                select(RepoWikiCatalog).where(
                    RepoWikiCatalog.document_id == document.id,
                    RepoWikiCatalog.is_deleted == False
                )
            )
            catalogs = catalogs_result.scalars().all()
            
            catalog_ids = [catalog.id for catalog in catalogs]
            
            # 获取所有文档内容
            content_result = await db.execute(
                select(RepoWikiContent).where(
                    RepoWikiContent.catalog_id.in_(catalog_ids)
                )
            )
            content_items = content_result.scalars().all()
            
            # 获取仓库概述
            overview = CodeWikiQueryService.get_overview()
            
            # 创建内存流
            memory_stream = io.BytesIO()
            
            with zipfile.ZipFile(memory_stream, 'w', zipfile.ZIP_DEFLATED) as archive:
                # 添加仓库概述文件
                if overview:
                    archive.writestr("README.md", f"# 概述\n\n{overview.get("content", "")}")
                
                # 构建目录树结构
                catalog_dict = {catalog.id: catalog for catalog in catalogs}
                root_catalogs = [catalog for catalog in catalogs if not catalog.parent_id]
                
                # 递归处理目录及其子目录
                await CodeWikiQueryService._process_catalogs_for_export(
                    archive, root_catalogs, catalog_dict, content_items, ""
                )
            
            memory_stream.seek(0)
            return memory_stream.getvalue()
            
        except Exception as e:
            logging.error(f"导出Markdown压缩包失败: {str(e)}")
            raise ValueError(f"导出Markdown压缩包失败: {str(e)}")
    
    @staticmethod
    async def _process_catalogs_for_export(
        self, 
        archive: zipfile.ZipFile, 
        catalogs: List[RepoWikiCatalog],
        catalog_dict: Dict[str, RepoWikiCatalog],
        content_items: List[RepoWikiContent], 
        current_path: str
    ):
        """递归处理目录及其子目录"""
        for catalog in catalogs:
            # 查找对应的文件条目
            file_item = next(
                (item for item in content_items if item.catalog_id == catalog.id), 
                None
            )
            
            # 跳过空文档
            if not file_item or not file_item.content:
                continue
            
            # 创建当前目录的路径
            dir_path = catalog.url.replace(" ", "_")
            if current_path:
                dir_path = f"{current_path}/{dir_path}"
            
            # 文档路径
            entry_path = f"{dir_path}/{file_item.title.replace(' ', '_')}.md"
            
            # 创建并写入文档内容
            content = f"# {catalog.name}\n\n{file_item.content}"
            archive.writestr(entry_path, content)
            
            # 获取并处理子目录
            children = [c for c in catalog_dict.values() if c.parent_id == catalog.id]
            if children:
                await self._process_catalogs_for_export(
                    archive, children, catalog_dict, content_items, dir_path
                )

    @staticmethod
    async def update_catalog(db: AsyncSession, request: UpdateRepoWikiCatalogRequest) -> bool:
        """更新目录"""
        try:
            catalog_result = await db.execute(
                select(RepoWikiCatalog).where(RepoWikiCatalog.id == request.id)
            )
            catalog = catalog_result.scalar_one_or_none()
            
            if not catalog:
                return False
            
            catalog.name = request.name
            catalog.prompt = request.prompt
            
            await db.commit()
            return True
            
        except Exception as e:
            await db.rollback()
            logging.error(f"更新目录失败: {e}")
            raise
    
    @staticmethod
    async def update_content(db: AsyncSession, request: UpdateRepoWikiContentRequest) -> bool:
        """更新文档内容"""
        try:
            content_result = await db.execute(
                select(RepoWikiContent).where(RepoWikiContent.id == request.id)
            )
            content = content_result.scalar_one_or_none()
            
            if not content:
                return False
            
            content.content = request.content
            
            await db.commit()
            return True
            
        except Exception as e:
            await db.rollback()
            logging.error(f"更新文档内容失败: {e}")
            raise

    @staticmethod
    async def get_overview_by_document_id(db: AsyncSession, document_id: str) -> Optional[RepoWikiOverview]:
        """根据文档ID获取概述"""
        try:
            overview_result = await db.execute(
                select(RepoWikiOverview).where(RepoWikiOverview.document_id == document_id)
            )
            return overview_result.scalar_one_or_none()
        except Exception as e:
            logging.error(f"获取概述失败: {e}")
            raise

    @staticmethod
    async def update_overview(db: AsyncSession, document_id: str, title: Optional[str] = None, content: Optional[str] = None) -> bool:
        """更新概述"""
        try:
            overview_result = await db.execute(
                select(RepoWikiOverview).where(RepoWikiOverview.document_id == document_id)
            )
            overview = overview_result.scalar_one_or_none()
            
            if not overview:
                return False
            
            if title is not None:
                overview.title = title
            if content is not None:
                overview.content = content
            
            await db.commit()
            return True
            
        except Exception as e:
            await db.rollback()
            logging.error(f"更新概述失败: {e}")
            raise

    @staticmethod
    async def get_minimap_by_document_id(db: AsyncSession, document_id: str) -> Optional[RepoWikiMiniMap]:
        """根据文档ID获取迷你地图"""
        try:
            minimap_result = await db.execute(
                select(RepoWikiMiniMap).where(RepoWikiMiniMap.document_id == document_id)
            )
            return minimap_result.scalar_one_or_none()
        except Exception as e:
            logging.error(f"获取迷你地图失败: {e}")
            raise

    @staticmethod
    async def get_commit_records_by_document_id(db: AsyncSession, document_id: str) -> List[RepoWikiCommitRecord]:
        """根据文档ID获取提交记录列表"""
        try:
            commits_result = await db.execute(
                select(RepoWikiCommitRecord).where(RepoWikiCommitRecord.document_id == document_id)
            )
            return list(commits_result.scalars().all())
        except Exception as e:
            logging.error(f"获取提交记录失败: {e}")
            raise