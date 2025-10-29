from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class ProcessingStatus:
    """处理状态枚举"""
    Pending = "pending"
    Processing = "processing"
    Completed = "completed"
    Canceled = "canceled"
    Failed = "failed"


class ClassifyType:
    """项目分类枚举"""
    Applications = "Applications"
    Frameworks = "Frameworks"
    Libraries = "Libraries"
    DevelopmentTools = "DevelopmentTools"
    CLITools = "CLITools"
    DevOpsConfiguration = "DevOpsConfiguration"
    Documentation = "Documentation"

class RepoWikiDocument(Base, TimestampMixin):
    """支持嵌架构文模型"""
    __tablename__ = "repo_wiki_documents"
    
    id = Column(String, primary_key=True, index=True, comment="ID")
    
    # 代码仓信息 - 与RepoRecord建立外键关系
    repo_id = Column(String, ForeignKey("repo_records.id"), nullable=False, index=True, comment="代码仓对象库ID")    
    
    # wiki信息
    classify = Column(String, nullable=True, comment="分类") 
    description = Column(Text, nullable=True, comment="文档描述")
    readme_content = Column(Text, nullable=True, comment="README内容")
    optimized_directory_struct = Column(Text, nullable=True, comment="优化目录结构")

    # 状态信息
    processing_status = Column(String, default=ProcessingStatus.Pending, comment="处理状态")
    processing_progress = Column(Integer, default=0, comment="处理进度")
    processing_message = Column(Text, nullable=True, comment="处理消息")

    # 嵌入信息
    is_embedded = Column(Boolean, default=False, comment="是否嵌入")

    # 关系
    overview = relationship("RepoWikiOverview", back_populates="document", uselist=False, cascade="all, delete-orphan")
    catalogs = relationship("RepoWikiCatalog", back_populates="document", cascade="all, delete-orphan")
    commit_records = relationship("RepoWikiCommitRecord", back_populates="document", cascade="all, delete-orphan")

    def to_dict(self, include_children=False):
        result = {
            "id": self.id,
            "repo_id": self.repo_id,
            "classify": self.classify,
            "description": self.description,
            "readme_content": self.readme_content,
            "optimized_directory_struct": self.optimized_directory_struct,
            "processing_status": self.processing_status,
            "processing_progress": self.processing_progress,
            "processing_message": self.processing_message,
            "is_embedded": self.is_embedded,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_children and hasattr(self, 'children') and self.children:
            result["children"] = [child.to_dict(include_children=True) for child in self.children]
        
        return result

class RepoWikiOverview(Base, TimestampMixin):
    """文档概述模型"""
    __tablename__ = "repo_wiki_overviews"
    
    id = Column(String(36), primary_key=True, index=True, comment="ID")
    document_id = Column(String(36), ForeignKey("repo_wiki_documents.id"), nullable=False, comment="文档ID")
    title = Column(String(200), nullable=False, default="", comment="标题")
    content = Column(Text, nullable=False, default="", comment="内容")
    
    # 关联关系
    document = relationship("RepoWikiDocument", back_populates="overview")
    
    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "title": self.title,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class RepoWikiMiniMap(Base, TimestampMixin):
    """迷你地图模型"""
    __tablename__ = "mini_maps"
    
    id = Column(String(36), primary_key=True, index=True, comment="ID")  
    document_id = Column(String(36), ForeignKey("repo_wiki_documents.id"), nullable=False, comment="文档ID")    
    value = Column(Text, nullable=False, default="", comment="思维导图数据")   

    # 关联关系
    document = relationship("RepoWikiDocument", back_populates="mini_maps")  

class RepoWikiCatalog(Base, TimestampMixin):
    """RepoWiki目录模型"""
    __tablename__ = "repo_wiki_catalogs"

    id = Column(String, primary_key=True, index=True, comment="ID")    
    document_id = Column(String, ForeignKey("repo_wiki_documents.id"), nullable=False, index=True, comment="文档ID")

    name = Column(String(200), nullable=False, comment="目录名称")
    url = Column(String(500), nullable=False, comment="目录URL")
    description = Column(Text, nullable=True, comment="目录描述")
    parent_id = Column(String(36), nullable=True, comment="目录父级ID")
    order = Column(Integer, default=0, comment="当前目录排序")

    # 状态信息
    is_completed = Column(Boolean, default=False, comment="是否处理完成")
    prompt = Column(Text, nullable=True, comment="提示词")
    is_deleted = Column(Boolean, default=False, comment="是否删除")
    deleted_time = Column(DateTime, nullable=True, comment="删除时间")
    
    # 关系
    document = relationship("RepoWikiDocument", back_populates="catalogs")
    contents = relationship("RepoWikiContent", back_populates="catalog", cascade="all, delete-orphan")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "parent_id": self.parent_id,
            "order": self.order,
            "is_completed": self.is_completed,
            "prompt": self.prompt,
            "is_deleted": self.is_deleted,
            "deleted_time": self.deleted_time.isoformat() if self.deleted_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class RepoWikiContent(Base, TimestampMixin):
    """RepoWiki内容模型"""
    __tablename__ = "repo_wiki_contents"

    id = Column(String, primary_key=True, index=True, comment="ID")
    catalog_id = Column(String(36), ForeignKey("repo_wiki_catalogs.id"), nullable=False, comment="绑定的repowiki目录ID")
    
    title = Column(String(200), nullable=False, comment="标题")
    description = Column(Text, nullable=True, comment="描述")
    content = Column(Text, nullable=True, comment="文档实际内容")
    size = Column(Integer, default=0, comment="文档大小")
    source_file_items = Column(JSON, default=dict, comment="相关源文件源数据，DocumentFileItemSource")
    meta_data = Column(JSON, default=dict, comment="源数据")
    extra = Column(JSON, default=dict, comment="扩展数据")

    # 关系
    catalog = relationship("RepoWikiCatalog", back_populates="contents")
    sources = relationship("RepoWikiContentSource", back_populates="content", cascade="all, delete-orphan")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "catalog_id": self.catalog_id,
            "title": self.title,
            "description": self.description,
            "content": self.content,
            "size": self.size,
            "source_file_items": self.source_file_items,
            "meta_data": self.meta_data,
            "extra": self.extra,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class RepoWikiContentSource(Base, TimestampMixin):
    """RepoWiki内容源模型"""
    __tablename__ = "repo_wiki_content_sources"

    id = Column(String, primary_key=True, index=True, comment="ID")
    content_id = Column(String(36), nullable=False, comment="内容ID")

    # 源代码仓文件信息
    source_path = Column(String(500), nullable=False, comment="源路径")
    source_name = Column(String(200), nullable=False, comment="源名称")
    
    # 关系
    content = relationship("RepoWikiContent", back_populates="sources")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "content_id": self.content_id,
            "source_path": self.source_path,
            "source_name": self.source_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        } 

class RepoWikiCommitRecord(Base, TimestampMixin):
    """文档提交记录模型"""
    __tablename__ = "repo_wiki_commit_records"
    
    id = Column(String(36), primary_key=True, index=True, comment="ID")
    document_id = Column(String(36), ForeignKey("repo_wiki_documents.id"), nullable=False, comment="文档ID") 
    commit_id = Column(String(100), nullable=False, default="", comment="提交ID")    
    commit_message = Column(String(1000), nullable=False, default="", comment="提交消息")    
    title = Column(String(200), nullable=False, default="", comment="标题")    
    author = Column(String(100), nullable=False, default="", comment="作者")
    
    # 关联关系
    document = relationship("RepoWikiDocument", back_populates="commit_records") 

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "commit_id": self.commit_id,
            "commit_message": self.commit_message,
            "title": self.title,
            "author": self.author,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }