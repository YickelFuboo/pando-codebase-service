import uuid
import logging
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.models.code_wiki import RepoWikiDocument, ClassifyType, ProcessingStatus
from app.models.git_repo import GitRepository
from app.services.git_repo_service import GitRepositoryService


class CodeWikiDocumentService:
    """RepoWikiDocument内部服务"""

    @staticmethod
    async def create_wiki_document(db: AsyncSession, git_repo_id: str) -> RepoWikiDocument:
        """
        为指定仓库创建CodeWikiDocument记录
        
        Args:
            db: 数据库会话
            repo_id: 仓库ID（必须指定）
            
        Returns:
            RepoWikiDocument: 创建的文档记录
            
        Raises:
            ValueError: 当repo_id不存在时
        """
        try:
            git_repository = await GitRepositoryService.get_repository_by_id(db, git_repo_id)
            if not git_repository:
                raise ValueError(f"仓库ID {git_repo_id} 不存在")

            # 检查Document是否存在
            existing_doc_result = await db.execute(
                select(RepoWikiDocument).where(RepoWikiDocument.repo_id == git_repository.id)
            )
            document = existing_doc_result.scalar_one_or_none()

            if not document:
                document_id = str(uuid.uuid4())   

                document = RepoWikiDocument(
                    id=document_id,
                    repo_id=git_repository.id,
                    classify=None,  # 后续通过AI分析生成
                    readme_content=None,  # 后续通过AI分析生成
                    optimized_directory_struct=None,  # 后续通过AI分析生成
                    processing_status=ProcessingStatus.Pending,
                    processing_progress=0,
                    processing_message="等待处理"
                )
                
                db.add(document)
                await db.commit()
                await db.refresh(document)
       
            # 启动Document分析任务
            from app.services.code_wiki.document_gen_service import CodeWikiGenService
            doc_gen_service = CodeWikiGenService(
                db, 
                document.id, 
                git_repository.local_path, 
                git_repository.repository_url, 
                git_repository.repository_name, 
                git_repository.branch
            )
            await doc_gen_service.generate_wiki()
            
            logging.info(f"为仓库 {git_repo_id} 创建CodeWikiDocument记录成功: {document.id}")
            return document
            
        except ValueError:
            # 重新抛出业务异常
            raise
        except Exception as e:
            await db.rollback()
            logging.error(f"为仓库 {git_repo_id} 创建CodeWikiDocument记录失败: {e}")
            raise

    @staticmethod
    async def get_wiki_document_by_id(db: AsyncSession, doc_id: str) -> Optional[RepoWikiDocument]:
        """
        根据ID获取CodeWikiDocument记录
        
        Args:
            db: 数据库会话
            doc_id: 文档ID
            
        Returns:
            CodeWikiDocument: 文档记录，如果不存在返回None
        """
        try:
            result = await db.execute(
                select(RepoWikiDocument).where(RepoWikiDocument.id == doc_id)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logging.error(f"获取RepoWikiDocument记录失败: {e}")
            raise

    @staticmethod
    async def get_wiki_document_by_git_repository_id(db: AsyncSession, git_repository_id: str) -> Optional[RepoWikiDocument]:
        """
        根据仓库ID获取CodeWikiDocument记录（一个仓库只有一个文档）
        
        Args:
            db: 数据库会话
            git_repository_id: 仓库ID
            
        Returns:
            CodeWikiDocument: 文档记录，如果不存在返回None
        """
        try:
            result = await db.execute(
                select(RepoWikiDocument).where(RepoWikiDocument.repo_id == git_repository_id)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logging.error(f"根据仓库ID获取CodeWikiDocument记录失败: {e}")
            raise

    @staticmethod
    async def delete_wiki_document(db: AsyncSession, doc_id: str) -> bool:
        """
        删除CodeWikiDocument记录
        
        Args:
            db: 数据库会话
            doc_id: 文档ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            result = await db.execute(
                delete(RepoWikiDocument).where(RepoWikiDocument.id == doc_id)
            )
            
            if result.rowcount == 0:
                return False
            
            await db.commit()
            logging.info(f"删除CodeWikiDocument记录成功: {doc_id}")
            return True
            
        except Exception as e:
            await db.rollback()
            logging.error(f"删除CodeWikiDocument记录失败: {e}")
            raise

    @staticmethod
    async def update_wiki_document_fields(db: AsyncSession, doc_id: str, **kwargs) -> bool:
        """
        更新CodeWikiDocument的指定字段
        
        Args:
            db: 数据库会话
            doc_id: 文档ID
            **kwargs: 要更新的字段，如 readme_content, classify, optimized_directory_struct 等
            
        Returns:
            bool: 更新是否成功
        """
        try:
            if not kwargs:
                return True  # 没有需要更新的字段
            
            result = await db.execute(
                update(RepoWikiDocument)
                .where(RepoWikiDocument.id == doc_id)
                .values(**kwargs)
            )
            
            if result.rowcount == 0:
                return False
            
            await db.commit()
            logging.info(f"更新CodeWikiDocument字段成功: {doc_id}, 字段: {list(kwargs.keys())}")
            return True
            
        except Exception as e:
            await db.rollback()
            logging.error(f"更新CodeWikiDocument字段失败: {e}")
            raise

    @staticmethod
    async def update_processing_status(db: AsyncSession, doc_id: str, status: str, 
                                     progress: int = None, message: str = None) -> bool:
        """
        更新处理状态
        
        Args:
            db: 数据库会话
            doc_id: 文档ID
            status: 处理状态
            progress: 处理进度
            message: 处理消息
            
        Returns:
            bool: 更新是否成功
        """
        try:
            update_dict = {"processing_status": status}
            
            if progress is not None:
                update_dict["processing_progress"] = progress
            if message is not None:
                update_dict["processing_message"] = message
            
            result = await db.execute(
                update(RepoWikiDocument)
                .where(RepoWikiDocument.id == doc_id)
                .values(**update_dict)
            )
            
            if result.rowcount == 0:
                return False
            
            await db.commit()
            logging.info(f"更新CodeWikiDocument处理状态成功: {doc_id} -> {status}")
            return True
            
        except Exception as e:
            await db.rollback()
            logging.error(f"更新CodeWikiDocument处理状态失败: {e}")
            raise
