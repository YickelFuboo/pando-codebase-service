import uuid
import os
import shutil
import zipfile
import tempfile
import gzip
import tarfile
import brotli
import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, and_, or_
from fastapi import UploadFile
from app.config.settings import settings
from app.schemes.git_repo import CreateRepositoryFromUrl, UpdateRepository, RepositoryInfo
from app.services.common.remote_git_service import RemoteGitService
from app.models.git_repo import ProcessingStatus, GitRepository
from app.tasks.git_repo_clone_task import clone_repository_task


class GitRepositoryService:
    """仓库管理服务"""
    
    @staticmethod
    def _get_base_storage_path():
        """获取基础存储路径"""
        return settings.repo_storage_path
    
    @staticmethod
    async def create_repository_from_url(session: AsyncSession, user_id: str, create_data: CreateRepositoryFromUrl) -> GitRepository:
        """通过Git URL创建仓库""" 
        try:       
            # 验证URL
            await GitRepositoryService._validate_url_repository(create_data.repository_url)
            
            # 从URL解析仓库信息
            provider = RemoteGitService.get_git_provider(create_data.repository_url)
            repo_organization, repo_name = RemoteGitService.get_git_url_info(create_data.repository_url)
            
            # 检查仓库是否已存在
            existing_repo = await session.execute(
                select(GitRepository).where(
                    GitRepository.git_provider == provider,
                    GitRepository.organization == repo_organization,
                    GitRepository.repository_name == repo_name,
                    GitRepository.user_id == user_id
                )
            )   
            if existing_repo.scalar_one_or_none():
                raise ValueError("仓库已存在")

            # 创建本地路径
            local_repo_path = os.path.join(GitRepositoryService._get_base_storage_path(), repo_organization, repo_name)
            
            # 创建仓库记录，状态为等待克隆
            repository = GitRepository(
                id=str(uuid.uuid4()),
                user_id=user_id,
                git_provider=provider,
                repository_url=create_data.repository_url,
                organization=repo_organization,
                repository_name=repo_name,
                description=create_data.description,
                branch=create_data.branch,
                local_path=local_repo_path,
                is_cloned=False,
                last_sync_time=None
            )
            session.add(repository)
            await session.commit()
            await session.refresh(repository)
            
            # 启动异步克隆任务
            clone_repository_task.delay(repository.id)
        
            logging.info(f"Created repository: {repository.repository_name} by user {user_id}")
            return repository
        
        except Exception as e:
            logging.error(f"Failed to create repository: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def _validate_url_repository(repo_url: str):
        """验证URL仓库是否可访问"""
        # 这里可以添加Git URL验证逻辑
        if not repo_url or not repo_url.startswith(('http://', 'https://', 'git@')):
            raise ValueError("无效的仓库URL")
    
    @staticmethod
    async def create_repository_from_package(
        session: AsyncSession, 
        user_id: str, 
        name: str, 
        description: str, 
        file: UploadFile) -> GitRepository:
        """通过上传压缩包创建仓库"""
        try:
            # 检查仓库是否已存在
            existing_repo = await session.execute(
                select(GitRepository).where(
                    GitRepository.repository_name == name,
                    GitRepository.user_id == user_id
                )
            )
            if existing_repo.scalar_one_or_none():
                raise ValueError("仓库已存在")

            # 创建本地存储路径 - 使用用户名和仓库名构建路径
            local_path = os.path.join(GitRepositoryService._get_base_storage_path(), "uploads", user_id, name)
            os.makedirs(local_path, exist_ok=True)
            
            try:
                # 保存上传的文件
                file_path = os.path.join(local_path, file.filename)
                with open(file_path, "wb") as buffer:
                    content = await file.read()
                    buffer.write(content)
                
                # 解压文件
                await GitRepositoryService._extract_archive(file_path, local_path)

                # 处理解压目录
                await GitRepositoryService._process_extracted_directory(local_path)
                
                # 删除原始压缩包
                os.remove(file_path)
                
            except Exception as e:
                # 清理失败的文件
                if os.path.exists(local_path):
                    shutil.rmtree(local_path)
                raise ValueError(f"处理上传文件失败: {str(e)}")
            
            # 创建仓库记录
            repository = GitRepository(
                id=str(uuid.uuid4()),
                user_id=user_id,
                git_provider="uploaded",
                repository_url="",  # 上传方式没有URL
                organization="uploaded",  # 上传方式没有组织
                repository_name=name,
                description=description,
                branch="main",  # 上传方式默认分支
                local_path=local_path,
                is_cloned=False,
                last_sync_time=None
            )
            
            session.add(repository)
            await session.commit()
            await session.refresh(repository)
        
            logging.info(f"Created repository from package: {repository.repository_name} by user {user_id}")
            return repository
            
        except Exception as e:
            # 清理失败的文件
            if local_path and os.path.exists(local_path):
                shutil.rmtree(local_path, ignore_errors=True)
            logging.error(f"创建仓库失败: {str(e)}")
            raise
    
    @staticmethod
    async def _extract_archive(file_path: str, extract_path: str):
        """解压压缩包"""
        try:            
            if file_path.endswith('.zip'):
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
            elif file_path.endswith('.gz'):
                with gzip.open(file_path, 'rb') as f_in:
                    with open(extract_path, 'wb') as f_out:
                        f_out.write(f_in.read())
            elif file_path.endswith('.tar'):
                with tarfile.open(file_path, 'r') as tar_ref:
                    tar_ref.extractall(extract_path)
            elif file_path.endswith('.br'):
                with open(file_path, 'rb') as f_in:
                    with open(extract_path, 'wb') as f_out:
                        f_out.write(brotli.decompress(f_in.read()))
        except Exception as e:
            logging.error(f"解压文件失败: {str(e)}")
            raise
    
    @staticmethod
    async def _process_extracted_directory(extract_path: str):
        """处理解压后的目录结构"""
        try:
            if os.path.exists(extract_path) and os.path.isdir(extract_path):
                # 如果解压后目录下只有一个文件夹，将其内容移动到上级目录
                items = os.listdir(extract_path)
                if len(items) == 1 and os.path.isdir(os.path.join(extract_path, items[0])):
                    sub_dir = os.path.join(extract_path, items[0])
                    for item in os.listdir(sub_dir):
                        src = os.path.join(sub_dir, item)
                        dst = os.path.join(extract_path, item)
                        if os.path.exists(dst):
                            if os.path.isdir(dst):
                                import shutil
                                shutil.rmtree(dst)
                            else:
                                os.remove(dst)
                        os.rename(src, dst)
                    os.rmdir(sub_dir)
        except Exception as e:
            logging.error(f"处理解压目录失败: {str(e)}")
            raise
    
    @staticmethod
    async def create_repository_from_path(
        session: AsyncSession, 
        user_id: str, 
        name: str, 
        description: str, 
        local_repo_path: str) -> GitRepository:
        """通过指定路径创建仓库"""
        try:
            # 验证服务端路径
            GitRepositoryService._validate_repo_path(local_repo_path)
            
            # 检查仓库是否已存在
            existing_repo = await session.execute(
                select(GitRepository).where(
                    GitRepository.repository_name == name,
                    GitRepository.user_id == user_id
                )
            )
            if existing_repo.scalar_one_or_none():
                raise ValueError("仓库已存在")
            
            # 创建仓库记录
            repository = GitRepository(
                id=str(uuid.uuid4()),
                user_id=user_id,
                git_provider="local",  # 路径方式
                repository_url="",  # 路径方式没有URL
                organization="local",  # 路径方式没有组织
                repository_name=name,
                description=description,
                branch="main",  # 路径方式默认分支
                local_path=local_repo_path,  # 直接使用服务端路径
                is_cloned=False,
                last_sync_time=None
            )
            
            session.add(repository)
            await session.commit()
            await session.refresh(repository)
            
            logging.info(f"Created repository from path: {repository.repository_name} by user {user_id}")
            return repository
            
        except Exception as e:
            logging.error(f"创建路径仓库失败: {str(e)}")
            raise
    
    @staticmethod
    def _validate_repo_path(repo_path: str):
        if not repo_path:
            raise ValueError("路径不能为空")
        if not os.path.exists(repo_path):
            raise ValueError(f"路径不存在: {repo_path}")
        if not os.path.isdir(repo_path):
            raise ValueError(f"路径不是目录: {repo_path}")
        if not os.access(repo_path, os.R_OK):
            raise ValueError(f"路径无读取权限: {repo_path}")
    
    @staticmethod
    async def get_repository_by_id(db: AsyncSession, repository_id: str) -> Optional[GitRepository]:
        """根据ID获取仓库"""
        try:
            result = await db.execute(
                select(GitRepository).where(GitRepository.id == repository_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logging.error(f"Failed to get repository by id: {e}")
            raise
    
    @staticmethod
    async def get_repository_list(
        db: AsyncSession,
        user_id: str, 
        page: int = 1, 
        page_size: int = 10, 
        keyword: Optional[str] = None
    ) -> tuple[List[GitRepository], int]:
        """获取用户仓库列表"""
        try:
            query = select(GitRepository).where(GitRepository.user_id == user_id)
            
            # 如果有关键词，则按名称或描述搜索
            if keyword:
                query = query.where(
                    GitRepository.repository_name.contains(keyword) | 
                    GitRepository.description.contains(keyword) |
                    GitRepository.organization.contains(keyword)
                )
            
            # 按创建时间降序排序
            query = query.order_by(GitRepository.created_at.desc())
            
            # 计算总数
            count_result = await db.execute(
                select(GitRepository).where(query.whereclause)
            )
            total = len(count_result.scalars().all())
            
            # 获取分页数据
            query = query.offset((page - 1) * page_size).limit(page_size)
            result = await db.execute(query)
            repositories = result.scalars().all()
            
            return repositories, total
        except Exception as e:
            logging.error(f"Failed to get repository list: {e}")
            raise

    @staticmethod
    async def update_repository(
        db: AsyncSession,
        repository_id: str, 
        user_id: str, 
        update_data: UpdateRepository
    ) -> Optional[GitRepository]:
        """更新仓库"""
        try:
            repository = await GitRepositoryService.get_repository_by_id(db, repository_id)
            if not repository:
                raise ValueError("仓库不存在")
            
            if repository.user_id != user_id:
                raise ValueError("无权限更新仓库")
            
            # 更新仓库信息
            if update_data.description is not None:
                repository.description = update_data.description
            
            if update_data.branch is not None:
                repository.branch = update_data.branch
                # 如果更新了分支，需要重新克隆或切换分支
                await GitRepositoryService._update_repository_branch(repository, update_data.branch)
            
            repository.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(repository)
            
            logging.info(f"Updated repository: {repository.repository_name}")
            return repository
            
        except Exception as e:
            logging.error(f"更新仓库失败: {e}")
            raise
    
    @staticmethod
    async def _update_repository_branch(repository: GitRepository, new_branch: str):
        """更新仓库分支"""
        try:
            # 检查仓库类型
            if repository.git_provider == "uploaded":
                # 上传的仓库没有Git URL，无法切换分支
                logging.warning(f"Repository {repository.repository_name} is uploaded type, cannot switch branch")
                return
            
            if repository.git_provider == "local":
                # 路径类型的仓库，检查是否为Git仓库
                if not os.path.exists(os.path.join(repository.local_path, '.git')):
                    logging.warning(f"Repository {repository.repository_name} is not a Git repository, cannot switch branch")
                    return
            
            # 使用GitService切换分支
            success = RemoteGitService.checkout_branch(repository.local_path, new_branch)
            if success:
                logging.info(f"Successfully switched repository {repository.repository_name} to branch {new_branch}")
            else:
                logging.error(f"Failed to switch repository {repository.repository_name} to branch {new_branch}")
                raise ValueError(f"切换分支失败: {new_branch}")
                
        except Exception as e:
            logging.error(f"更新仓库分支失败: {e}")
            raise
    
    @staticmethod
    async def delete_repository(db: AsyncSession, repository_id: str, user_id: str) -> bool:
        """删除仓库"""
        try:
            repository = await GitRepositoryService.get_repository_by_id(db, repository_id)
            if not repository:
                raise ValueError("仓库不存在")
            
            if repository.user_id != user_id:
                raise ValueError("无权限删除仓库")
            
            # 删除本地文件
            if repository.local_path and os.path.exists(repository.local_path):
                shutil.rmtree(repository.local_path)
            
            await db.execute(delete(GitRepository).where(GitRepository.id == repository_id))
            await db.commit()
            logging.info(f"Deleted repository: {repository.repository_name}")
            return True
        except Exception as e:
            logging.error(f"删除仓库失败: {e}")
            raise    
    @staticmethod
    async def update_repo_processing_status(
        session: AsyncSession,
        repo_id: str,
        status: ProcessingStatus,
        progress: int = None,
        message: str = None,
        error: str = None
    ) -> bool:
        """更新仓库处理状态"""
        try:
            update_data = {
                "processing_status": status,
                "updated_at": datetime.utcnow()
            }
            
            if progress is not None:
                update_data["processing_progress"] = progress
            if message is not None:
                update_data["processing_message"] = message
            if error is not None:
                update_data["processing_error"] = error
            
            result = await session.execute(
                update(GitRepository)
                .where(GitRepository.id == repo_id)
                .values(**update_data)
            )
            
            await session.commit()
            return result.rowcount > 0
            
        except Exception as e:
            logging.error(f"更新仓库克隆状态失败: {e}")
            return False


