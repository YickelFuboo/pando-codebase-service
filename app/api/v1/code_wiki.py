from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database import get_db
from app.services.code_wiki.document_gen_service import CodeWikiGenService

router = APIRouter(prefix="/code-wiki", tags=["代码Wiki管理"])


@router.post("/generate_readme")
async def generate_readme(
    local_path: str,
    git_url: str,
    git_name: str,  
    branch: str,
    session: AsyncSession = Depends(get_db),
):
    """生成README文档"""
    try:
        if not local_path or  not git_url or not branch:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="参数错误"
            )
        
        code_wiki_gen_service = CodeWikiGenService(session, "test", local_path, git_url, git_name, branch)
        readme = await code_wiki_gen_service.generate_readme()
        return {
            "message": "Wiki生成任务已启动", 
            "content": readme,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成README文档失败: {str(e)}"
        )


@router.post("/generate_readme_new")
async def generate_readme_new( 
    local_path: str,
    git_url: str,
    git_name: str,
    branch: str,
    session: AsyncSession = Depends(get_db),
):
    """生成README文档"""
    try:
        if not local_path or  not git_url or not branch:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="参数错误"
            )
        
        code_wiki_gen_service = CodeWikiGenService(session, "test", local_path, git_url, git_name, branch)
        readme = await code_wiki_gen_service.generate_readme_new()
        return {
            "message": "Wiki生成任务已启动", 
            "content": readme,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成README文档失败: {str(e)}"
        )

