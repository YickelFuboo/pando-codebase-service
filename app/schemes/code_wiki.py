from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime


class RepoWikiDocumentResponse(BaseModel):
    """文档响应模型"""
    id: str = Field(..., description="文档ID")
    repo_id: str = Field(..., description="仓库ID")
    classify: Optional[str] = Field(None, description="分类")
    description: Optional[str] = Field(None, description="文档描述")
    readme_content: Optional[str] = Field(None, description="README内容")
    optimized_directory_struct: Optional[str] = Field(None, description="优化目录结构")
    processing_status: str = Field(..., description="处理状态")
    processing_progress: int = Field(0, description="处理进度")
    processing_message: Optional[str] = Field(None, description="处理消息")
    is_embedded: bool = Field(False, description="是否嵌入")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        from_attributes = True


class CreateWikiDocumentRequest(BaseModel):
    """创建文档请求"""
    git_repo_id: str = Field(..., description="Git仓库ID")

    @validator('git_repo_id')
    def validate_git_repo_id(cls, v):
        if not v or not v.strip():
            raise ValueError("仓库ID不能为空")
        return v.strip()


class UpdateWikiDocumentRequest(BaseModel):
    """更新文档请求"""
    classify: Optional[str] = Field(None, description="分类")
    description: Optional[str] = Field(None, description="文档描述")
    readme_content: Optional[str] = Field(None, description="README内容")
    optimized_directory_struct: Optional[str] = Field(None, description="优化目录结构")
    is_embedded: Optional[bool] = Field(None, description="是否嵌入")


class UpdateProcessingStatusRequest(BaseModel):
    """更新处理状态请求"""
    status: str = Field(..., description="处理状态")
    progress: Optional[int] = Field(None, description="处理进度")
    message: Optional[str] = Field(None, description="处理消息")

    @validator('status')
    def validate_status(cls, v):
        if not v or not v.strip():
            raise ValueError("处理状态不能为空")
        return v.strip()


class RepoWikiCatalogTreeItem(BaseModel):
    """文档目录树项"""
    id: str = Field(..., description="目录ID")
    name: str = Field(..., description="目录名称")
    url: str = Field(..., description="目录URL")
    description: Optional[str] = Field(None, description="目录描述")
    parent_id: Optional[str] = Field(None, description="目录父级ID")
    order: int = Field(0, description="当前目录排序")
    is_completed: bool = Field(False, description="是否处理完成")
    prompt: Optional[str] = Field(None, description="提示词")
    is_deleted: bool = Field(False, description="是否删除")
    deleted_time: Optional[datetime] = Field(None, description="删除时间")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    children: List['RepoWikiCatalogTreeItem'] = Field(default_factory=list, description="子目录")

class RepoWikiCatalogResponse(BaseModel):
    """文档目录响应"""
    items: List[RepoWikiCatalogTreeItem] = Field(default_factory=list, description="目录树")
    last_update: Optional[datetime] = Field(None, description="最后更新时间")
    description: Optional[str] = Field(None, description="文档描述")
    progress: int = Field(0, description="处理进度")
    git: str = Field(..., description="Git地址")
    branchs: List[str] = Field(default_factory=list, description="分支列表")
    document_id: Optional[str] = Field(None, description="文档ID")

class RepoWikiContentResponse(BaseModel):
    """文档内容响应"""
    id: str = Field(..., description="内容ID")
    catalog_id: str = Field(..., description="目录ID")
    title: str = Field(..., description="标题")
    description: Optional[str] = Field(None, description="描述")
    content: Optional[str] = Field(None, description="文档实际内容")
    size: int = Field(0, description="文档大小")
    source_file_items: Dict[str, Any] = Field(default_factory=dict, description="相关源文件源数据")
    meta_data: Dict[str, Any] = Field(default_factory=dict, description="源数据")
    extra: Dict[str, Any] = Field(default_factory=dict, description="扩展数据")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    sources: List['RepoWikiContentSourceResponse'] = Field(default_factory=list, description="相关源文件")


class RepoWikiContentSourceResponse(BaseModel):
    """文档内容源响应"""
    id: str = Field(..., description="源ID")
    content_id: str = Field(..., description="内容ID")
    source_path: str = Field(..., description="源路径")
    source_name: str = Field(..., description="源名称")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")


class UpdateRepoWikiCatalogRequest(BaseModel):
    """更新目录请求"""
    id: str = Field(..., description="目录ID")
    name: str = Field(..., description="目录名称")
    prompt: str = Field("", description="提示词")

    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("目录名称不能为空")
        return v.strip()


class UpdateRepoWikiContentRequest(BaseModel):
    """更新文档内容请求"""
    id: str = Field(..., description="文档ID")
    content: str = Field(..., description="文档内容")

    @validator('content')
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError("文档内容不能为空")
        return v.strip()


class RepoWikiOverviewResponse(BaseModel):
    """文档概述响应"""
    id: str = Field(..., description="概述ID")
    document_id: str = Field(..., description="文档ID")
    title: str = Field(..., description="标题")
    content: str = Field(..., description="内容")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        from_attributes = True


class UpdateRepoWikiOverviewRequest(BaseModel):
    """更新概述请求"""
    title: Optional[str] = Field(None, description="标题")
    content: Optional[str] = Field(None, description="内容")


class RepoWikiMiniMapResponse(BaseModel):
    """迷你地图响应"""
    id: str = Field(..., description="迷你地图ID")
    document_id: str = Field(..., description="文档ID")
    value: str = Field(..., description="思维导图数据")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        from_attributes = True


class RepoWikiCommitRecordResponse(BaseModel):
    """提交记录响应"""
    id: str = Field(..., description="记录ID")
    document_id: str = Field(..., description="文档ID")
    commit_id: str = Field(..., description="提交ID")
    commit_message: str = Field(..., description="提交消息")
    title: str = Field(..., description="标题")
    author: str = Field(..., description="作者")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        from_attributes = True
