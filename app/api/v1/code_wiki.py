from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database import get_db
from app.services.code_wiki.document_service import CodeWikiDocumentService
from app.services.code_wiki.query_service import CodeWikiQueryService
from app.schemes.code_wiki import (
    RepoWikiDocumentResponse,
    CreateWikiDocumentRequest,
    UpdateWikiDocumentRequest,
    UpdateProcessingStatusRequest,
    RepoWikiOverviewResponse,
    UpdateRepoWikiOverviewRequest,
    RepoWikiMiniMapResponse,
    RepoWikiCatalogResponse,
    UpdateRepoWikiCatalogRequest,
    RepoWikiContentResponse,
    UpdateRepoWikiContentRequest,
    RepoWikiCommitRecordResponse
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


@router.delete("/repositories/{repo_id}/documents", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wiki_document_by_repo_id(
    repo_id: str = Path(..., description="仓库ID"),
    db: AsyncSession = Depends(get_db)
):
    """根据仓库ID删除Wiki文档"""
    try:
        success = await CodeWikiDocumentService.delete_wiki_document_by_repo_id(db, repo_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"仓库ID {repo_id} 对应的文档不存在"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除Wiki文档失败: {str(e)}"
        )


@router.get("/documents/{doc_id}/overview", response_model=RepoWikiOverviewResponse)
async def get_overview(
    doc_id: str = Path(..., description="文档ID"),
    db: AsyncSession = Depends(get_db)
):
    """查询document对应的OverView"""
    try:
        overview = await CodeWikiQueryService.get_overview_by_document_id(db, doc_id)
        if not overview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文档ID {doc_id} 对应的概述不存在"
            )
        return overview
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取概述失败: {str(e)}"
        )


@router.put("/documents/{doc_id}/overview", response_model=RepoWikiOverviewResponse)
async def update_overview(
    doc_id: str = Path(..., description="文档ID"),
    request: UpdateRepoWikiOverviewRequest = ...,
    db: AsyncSession = Depends(get_db)
):
    """修改document对应的OverView"""
    try:
        update_data = request.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有需要更新的字段"
            )
        
        success = await CodeWikiQueryService.update_overview(
            db, doc_id, update_data.get("title"), update_data.get("content")
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文档ID {doc_id} 对应的概述不存在"
            )
        
        overview = await CodeWikiQueryService.get_overview_by_document_id(db, doc_id)
        return overview
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新概述失败: {str(e)}"
        )


@router.get("/documents/{doc_id}/minimap", response_model=RepoWikiMiniMapResponse)
async def get_minimap(
    doc_id: str = Path(..., description="文档ID"),
    db: AsyncSession = Depends(get_db)
):
    """查询document对应的minimap"""
    try:
        minimap = await CodeWikiQueryService.get_minimap_by_document_id(db, doc_id)
        if not minimap:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文档ID {doc_id} 对应的迷你地图不存在"
            )
        return minimap
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取迷你地图失败: {str(e)}"
        )


@router.get("/documents/{doc_id}/catalogs", response_model=RepoWikiCatalogResponse)
async def get_catalogs(
    doc_id: str = Path(..., description="文档ID"),
    db: AsyncSession = Depends(get_db)
):
    """查询document对应的wiki目录（RepoWikiCatalog）"""
    try:
        query_service = CodeWikiQueryService()
        catalog_response = await query_service.get_catalogs(db, doc_id, "")
        return catalog_response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取目录失败: {str(e)}"
        )


@router.put("/catalogs/{catalog_id}", response_model=Dict[str, Any])
async def update_catalog(
    catalog_id: str = Path(..., description="目录ID"),
    request: UpdateRepoWikiCatalogRequest = ...,
    db: AsyncSession = Depends(get_db)
):
    """修改document对应的wiki目录（RepoWikiCatalog）"""
    try:
        if request.id != catalog_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="目录ID不匹配"
            )
        success = await CodeWikiQueryService.update_catalog(db, request)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"目录ID {catalog_id} 不存在"
            )
        return {"message": "更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新目录失败: {str(e)}"
        )


@router.get("/catalogs/{catalog_id}/contents", response_model=RepoWikiContentResponse)
async def get_catalog_contents(
    catalog_id: str = Path(..., description="目录ID"),
    db: AsyncSession = Depends(get_db)
):
    """指定目录id，查询document的目录的内容，包含RepoWikiContent、RepoWikiContentSource表数据"""
    try:
        content = await CodeWikiQueryService.get_catalog_contents_by_id(db, catalog_id)
        return content
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取目录内容失败: {str(e)}"
        )


@router.put("/catalogs/{catalog_id}/contents", response_model=RepoWikiContentResponse)
async def update_catalog_contents(
    catalog_id: str = Path(..., description="目录ID"),
    request: UpdateRepoWikiContentRequest = ...,
    db: AsyncSession = Depends(get_db)
):
    """指定目录id，修改document的目录的内容，包含RepoWikiContent表数据"""
    try:
        content = await CodeWikiQueryService.get_catalog_contents_by_id(db, catalog_id)
        
        update_request = UpdateRepoWikiContentRequest(id=content.id, content=request.content)
        success = await CodeWikiQueryService.update_content(db, update_request)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新内容失败"
            )
        
        updated_content = await CodeWikiQueryService.get_catalog_contents_by_id(db, catalog_id)
        return updated_content
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新目录内容失败: {str(e)}"
        )


@router.get("/documents/{doc_id}/commit-records", response_model=List[RepoWikiCommitRecordResponse])
async def get_commit_records(
    doc_id: str = Path(..., description="文档ID"),
    db: AsyncSession = Depends(get_db)
):
    """查询Document对应的RepoWikiCommitRecord"""
    try:
        records = await CodeWikiQueryService.get_commit_records_by_document_id(db, doc_id)
        return records
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取提交记录失败: {str(e)}"
        )

