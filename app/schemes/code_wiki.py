from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime


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

