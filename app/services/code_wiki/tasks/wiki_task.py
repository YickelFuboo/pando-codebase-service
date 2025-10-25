import asyncio
import logging
from datetime import datetime
from sqlalchemy import select, update
from app.infrastructure.celery.app import celery_app
from app.infrastructure.database.factory import get_db
from app.domains.repo_mgmt.models.repository import RepoRecord, ProcessingStatus


@celery_app.task(bind=True)
def generate_wiki_task(self, repo_id: str):
    """异步生成仓库wiki任务"""
    
    async def _generate_wiki():
        async for session in get_db():
            try:
                # 更新状态为生成wiki中
                await session.execute(
                    update(RepoRecord)
                    .where(RepoRecord.id == repo_id)
                    .values(
                        processing_status=ProcessingStatus.WIKI_GENERATING,
                        processing_progress=10,
                        processing_message="开始生成wiki",
                        updated_at=datetime.utcnow()
                    )
                )
                await session.commit()
                
                # 获取仓库信息
                result = await session.execute(
                    select(RepoRecord).where(RepoRecord.id == repo_id)
                )
                repo_record = result.scalar_one_or_none()
                if not repo_record:
                    raise Exception(f"仓库 {repo_id} 不存在")
                
                logging.info(f"开始为仓库 {repo_record.repo_name} 生成wiki")
                
                # 更新进度
                await session.execute(
                    update(RepoRecord)
                    .where(RepoRecord.id == repo_id)
                    .values(
                        processing_progress=30,
                        processing_message="wiki文档已创建，开始分析代码",
                        updated_at=datetime.utcnow()
                    )
                )
                await session.commit()
                
                # TODO: 执行代码分析任务
                # 这里可以调用代码分析服务
                # 分析仓库代码结构、函数、类等
                # 生成wiki内容
                
                # 模拟分析过程
                await asyncio.sleep(2)  # 模拟分析耗时
                
                # 更新进度
                await session.execute(
                    update(RepoRecord)
                    .where(RepoRecord.id == repo_id)
                    .values(
                        processing_progress=80,
                        processing_message="代码分析完成，正在生成wiki内容",
                        updated_at=datetime.utcnow()
                    )
                )
                await session.commit()
                
                # 模拟生成wiki内容
                await asyncio.sleep(1)  # 模拟生成耗时
                
                # 更新仓库状态为完成
                await session.execute(
                    update(RepoRecord)
                    .where(RepoRecord.id == repo_id)
                    .values(
                        processing_status=ProcessingStatus.COMPLETED,
                        processing_progress=100,
                        processing_message="wiki生成完成",
                        is_wiki_generated=True,
                        updated_at=datetime.utcnow()
                    )
                )
                await session.commit()
                
                logging.info(f"仓库 {repo_record.repo_name} wiki生成完成")
                
            except Exception as e:
                # 更新状态为失败
                await session.execute(
                    update(RepoRecord)
                    .where(RepoRecord.id == repo_id)
                    .values(
                        processing_status=ProcessingStatus.FAILED,
                        processing_progress=0,
                        processing_message="wiki生成失败",
                        processing_error=str(e),
                        updated_at=datetime.utcnow()
                    )
                )
                await session.commit()
                logging.error(f"仓库 {repo_id} wiki生成失败: {e}")
                raise
    
    # 运行异步任务
    asyncio.run(_generate_wiki())