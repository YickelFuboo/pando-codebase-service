import contextvars
from typing import List, Optional, Dict, Any, Iterator
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
from contextlib import contextmanager
from pathlib import Path

# 使用 contextvars 确保线程安全和异步安全
_document_context = contextvars.ContextVar('document_context', default=None)


@dataclass
class GitIssue:
    """Git Issue 信息"""
    title: str
    url: str
    content: str
    author: str = ""
    url_html: str = ""
    state: str = ""
    number: str = ""
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "author": self.author,
            "url_html": self.url_html,
            "state": self.state,
            "number": self.number,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class DocumentContext:
    """文档上下文数据存储"""
    files: List[str] = field(default_factory=list)
    git_issues: List[GitIssue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_file(self, file_path: str) -> None:
        """添加文件路径"""
        if file_path not in self.files:
            self.files.append(file_path)
            logging.debug(f"Added file: {file_path}")
    
    def add_files(self, file_paths: List[str]) -> None:
        """批量添加文件路径"""
        for file_path in file_paths:
            self.add_file(file_path)
    
    def add_git_issue(self, issue: GitIssue) -> None:
        """添加 Git Issue"""
        self.git_issues.append(issue)
        logging.debug(f"Added git issue: {issue.title}")
    
    def add_git_issues(self, issues: List[GitIssue]) -> None:
        """批量添加 Git Issues"""
        self.git_issues.extend(issues)
    
    def clear_git_issues(self) -> None:
        """清理 Git Issues"""
        self.git_issues.clear()
        logging.debug("Cleared git issues")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "files": self.files,
            "git_issues": [issue.to_dict() for issue in self.git_issues],
            "metadata": self.metadata
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """获取摘要信息"""
        return {
            "file_count": len(self.files),
            "issue_count": len(self.git_issues),
            "files": self.files,
            "git_issues": [issue.to_dict() for issue in self.git_issues]
        }


class DocumentContextManager:
    """文档上下文管理器"""
    
    @staticmethod
    def get_context() -> Optional[DocumentContext]:
        """获取当前上下文"""
        return _document_context.get()
    
    @staticmethod
    def set_context(context: DocumentContext) -> None:
        """设置当前上下文"""
        _document_context.set(context)
    
    @staticmethod
    def reset_context() -> None:
        """重置当前上下文"""
        _document_context.set(None)
    
    @staticmethod
    def get_or_create_context() -> DocumentContext:
        """获取或创建上下文"""
        context = _document_context.get()
        if context is None:
            context = DocumentContext()
            _document_context.set(context)
            logging.debug("Created new document context")
        return context
    
    @staticmethod
    @contextmanager
    def context() -> Iterator[DocumentContext]:
        """上下文管理器"""
        context = DocumentContext()
        _document_context.set(context)
        try:
            yield context
        finally:
            _document_context.set(None)
            logging.debug("Cleaned up document context")
    
    # 便捷方法
    @staticmethod
    def add_file(file_path: str) -> None:
        """添加文件到当前上下文"""
        context = DocumentContextManager.get_or_create_context()
        context.add_file(file_path)
    
    @staticmethod
    def add_files(file_paths: List[str]) -> None:
        """批量添加文件到当前上下文"""
        context = DocumentContextManager.get_or_create_context()
        context.add_files(file_paths)
    
    @staticmethod
    def add_git_issue(issue: GitIssue) -> None:
        """添加 Git Issue 到当前上下文"""
        context = DocumentContextManager.get_or_create_context()
        context.add_git_issue(issue)
    
    @staticmethod
    def add_git_issues(issues: List[GitIssue]) -> None:
        """批量添加 Git Issues 到当前上下文"""
        context = DocumentContextManager.get_or_create_context()
        context.add_git_issues(issues)
    
    @staticmethod
    def clear_git_issues() -> None:
        """清理当前上下文的 Git Issues"""
        context = DocumentContextManager.get_context()
        if context:
            context.clear_git_issues()
    
    @staticmethod
    def get_summary() -> Dict[str, Any]:
        """获取当前上下文摘要"""
        context = DocumentContextManager.get_context()
        return context.get_summary() if context else {"file_count": 0, "issue_count": 0, "files": [], "git_issues": []}