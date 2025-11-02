from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database import get_db
from app.services.code_wiki.document_service import CodeWikiDocumentService
from app.schemes.code_wiki import (
    RepoWikiDocumentResponse,
    CreateWikiDocumentRequest,
    UpdateWikiDocumentRequest,
    UpdateProcessingStatusRequest
)

router = APIRouter(prefix="/code-wiki", tags=["代码Wiki管理"])


@router.post("/create", response_model=RepoWikiDocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_wiki_document(
    request: CreateWikiDocumentRequest,
    db: AsyncSession = Depends(get_db)
):
    """为指定仓库创建Wiki文档"""
    try:
        document = await CodeWikiDocumentService.create_wiki_document(
            db, request.git_repo_id
        )
        return document
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建Wiki文档失败: {str(e)}"
        )


@router.get("/documents/{doc_id}", response_model=RepoWikiDocumentResponse)
async def get_wiki_document_by_id(
    doc_id: str = Path(..., description="文档ID"),
    db: AsyncSession = Depends(get_db)
):
    """根据ID获取Wiki文档"""
    try:
        document = await CodeWikiDocumentService.get_wiki_document_by_id(db, doc_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文档ID {doc_id} 不存在"
            )
        return document
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取Wiki文档失败: {str(e)}"
        )


@router.get("/documents", response_model=RepoWikiDocumentResponse)
async def get_wiki_document_by_repository_id(
    git_repository_id: str = Query(..., description="Git仓库ID"),
    db: AsyncSession = Depends(get_db)
):
    """根据仓库ID获取Wiki文档"""
    try:
        document = await CodeWikiDocumentService.get_wiki_document_by_git_repository_id(
            db, git_repository_id
        )
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"仓库ID {git_repository_id} 对应的文档不存在"
            )
        return document
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取Wiki文档失败: {str(e)}"
        )


@router.put("/documents/{doc_id}", response_model=RepoWikiDocumentResponse)
async def update_wiki_document(
    doc_id: str = Path(..., description="文档ID"),
    request: UpdateWikiDocumentRequest = ...,
    db: AsyncSession = Depends(get_db)
):
    """更新Wiki文档字段"""
    try:
        update_data = request.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有需要更新的字段"
            )
        
        success = await CodeWikiDocumentService.update_wiki_document_fields(
            db, doc_id, **update_data
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文档ID {doc_id} 不存在"
            )
        
        document = await CodeWikiDocumentService.get_wiki_document_by_id(db, doc_id)
        return document
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新Wiki文档失败: {str(e)}"
        )


@router.patch("/documents/{doc_id}/status", response_model=RepoWikiDocumentResponse)
async def update_processing_status(
    doc_id: str = Path(..., description="文档ID"),
    request: UpdateProcessingStatusRequest = ...,
    db: AsyncSession = Depends(get_db)
):
    """更新文档处理状态"""
    try:
        success = await CodeWikiDocumentService.update_processing_status(
            db,
            doc_id,
            request.status,
            request.progress,
            request.message
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文档ID {doc_id} 不存在"
            )
        
        document = await CodeWikiDocumentService.get_wiki_document_by_id(db, doc_id)
        return document
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新处理状态失败: {str(e)}"
        )


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wiki_document(
    doc_id: str = Path(..., description="文档ID"),
    db: AsyncSession = Depends(get_db)
):
    """删除Wiki文档"""
    try:
        success = await CodeWikiDocumentService.delete_wiki_document(db, doc_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文档ID {doc_id} 不存在"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除Wiki文档失败: {str(e)}"
        )

