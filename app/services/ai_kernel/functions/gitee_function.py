import json
import httpx
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from semantic_kernel.functions import kernel_function

from app.config.settings import settings
from app.services.task_context.document_context import DocumentContextManager


@dataclass
class User:
    """用户信息，对应C#的User类"""
    id: int
    login: str
    name: str
    avatar_url: str
    url: str
    html_url: str
    remark: str
    followers_url: str
    following_url: str
    gists_url: str
    starred_url: str
    subscriptions_url: str
    organizations_url: str
    repos_url: str
    events_url: str
    received_events_url: str
    type: str


@dataclass
class Issue:
    """Issue信息，对应C#的Issue类"""
    id: int
    title: str
    number: str


@dataclass
class Target:
    """目标信息，对应C#的Target类"""
    issue: Optional[Issue]
    pull_request: Optional[Any]


@dataclass
class GiteeIssusItem:
    """Gitee Issue评论项，对应C#的GiteeIssusItem类"""
    id: int
    body: str
    user: User
    source: Optional[Any]
    target: Optional[Target]
    created_at: str
    updated_at: str


@dataclass
class Issue_type_detail:
    """Issue类型详情，对应C#的Issue_type_detail类"""
    id: int
    title: str
    template: Optional[Any]
    ident: str
    color: str
    is_system: bool
    created_at: str
    updated_at: str


@dataclass
class Issue_state_detail:
    """Issue状态详情，对应C#的Issue_state_detail类"""
    id: int
    title: str
    color: str
    icon: str
    command: Optional[Any]
    serial: int
    created_at: str
    updated_at: str


@dataclass
class Owner:
    """所有者信息，对应C#的Owner类"""
    id: int
    login: str
    name: str
    avatar_url: str
    url: str
    html_url: str
    remark: str
    followers_url: str
    following_url: str
    gists_url: str
    starred_url: str
    subscriptions_url: str
    organizations_url: str
    repos_url: str
    events_url: str
    received_events_url: str
    type: str


@dataclass
class Assigner:
    """分配者信息，对应C#的Assigner类"""
    id: int
    login: str
    name: str
    avatar_url: str
    url: str
    html_url: str
    remark: str
    followers_url: str
    following_url: str
    gists_url: str
    starred_url: str
    subscriptions_url: str
    organizations_url: str
    repos_url: str
    events_url: str
    received_events_url: str
    type: str


@dataclass
class Assignee:
    """被分配者信息，对应C#的Assignee类"""
    id: int
    login: str
    name: str
    avatar_url: str
    url: str
    html_url: str
    remark: str
    followers_url: str
    following_url: str
    gists_url: str
    starred_url: str
    subscriptions_url: str
    organizations_url: str
    repos_url: str
    events_url: str
    received_events_url: str
    type: str


@dataclass
class Testers:
    """测试者信息，对应C#的Testers类"""
    id: int
    login: str
    name: str
    avatar_url: str
    url: str
    html_url: str
    remark: str
    followers_url: str
    following_url: str
    gists_url: str
    starred_url: str
    subscriptions_url: str
    organizations_url: str
    repos_url: str
    events_url: str
    received_events_url: str
    type: str


@dataclass
class Namespace:
    """命名空间信息，对应C#的Namespace类"""
    id: int
    type: str
    name: str
    path: str
    html_url: str


@dataclass
class Repository:
    """仓库信息，对应C#的Repository类"""
    id: int
    full_name: str
    human_name: str
    url: str
    path: str
    name: str
    owner: Owner
    assigner: Assigner
    description: str
    fork: bool
    html_url: str
    ssh_url: str
    forks_url: str
    keys_url: str
    collaborators_url: str
    hooks_url: str
    branches_url: str
    tags_url: str
    blobs_url: str
    stargazers_url: str
    contributors_url: str
    commits_url: str
    comments_url: str
    issue_comment_url: str
    issues_url: str
    pulls_url: str
    milestones_url: str
    notifications_url: str
    labels_url: str
    releases_url: str
    recommend: bool
    gvp: bool
    homepage: Optional[Any]
    language: Optional[str]
    forks_count: int
    stargazers_count: int
    watchers_count: int
    default_branch: str
    open_issues_count: int
    has_issues: bool
    has_wiki: bool
    issue_comment: bool
    can_comment: bool
    pull_requests_enabled: bool
    has_page: bool
    license: Optional[Any]
    outsourced: bool
    project_creator: str
    members: List[str]
    pushed_at: str
    created_at: str
    updated_at: str
    parent: Optional[Any]
    paas: Optional[Any]
    assignees_number: int
    testers_number: int
    assignee: List[Assignee]
    testers: List[Testers]
    status: str
    programs: List[Any]
    enterprise: Optional[Any]
    project_labels: List[Any]
    issue_template_source: str


@dataclass
class GiteeIssueListDto:
    """Gitee Issue列表DTO，对应C#的GiteeIssueListDto类"""
    id: int
    url: str
    repository_url: str
    labels_url: str
    comments_url: str
    html_url: str
    parent_url: Optional[Any]
    number: str
    parent_id: int
    depth: int
    state: str
    title: str
    body: str
    user: User
    repository: Repository
    milestone: Optional[Any]
    created_at: str
    updated_at: str
    plan_started_at: Optional[Any]
    deadline: Optional[Any]
    finished_at: Optional[Any]
    scheduled_time: int
    comments: int
    priority: int
    issue_type: str
    program: Optional[Any]
    security_hole: bool
    issue_state: str
    branch: Optional[Any]
    issue_type_detail: Issue_type_detail
    issue_state_detail: Issue_state_detail


class GiteeFunction:
    """Gitee相关功能，对应C#的GiteeFunction类"""
    
    def __init__(self, owner: str, name: str, branch: str):
        """
        初始化GiteeFunction
        
        Args:
            owner: 仓库所有者
            name: 仓库名称
            branch: 分支名称
        """
        self.owner = owner
        self.name = name
        self.branch = branch
        self.base_url = "https://gitee.com/api/v5"
    
    @kernel_function(
        name="SearchIssues",
        description="搜索 Issue 内容. "
                   "Parameters: "
                   "- query (string): 搜索关键词 "
                   "- max_results (integer): 最大返回数量"
    )
    async def search_issues_async(
        self,
        query: str,
        max_results: int = 5
    ) -> str:
        """
        搜索相关issue内容，对应C#的SearchIssuesAsync方法
        
        Args:
            query: 搜索关键词
            max_results: 最大返回数量
            
        Returns:
            搜索结果字符串
        """
        try:
            # 检查Token配置，对应C#的GiteeOptions.Token检查
            if not hasattr(settings, 'gitee') or not settings.gitee.token:
                return "未配置 Gitee Token，无法搜索 Issue。"
            
            async with httpx.AsyncClient() as client:
                # 构建URL，对应C#的URL构建逻辑
                url = f"{self.base_url}/repos/{self.owner}/{self.name}/issues"
                params = {
                    "page": 1,
                    "per_page": max_results,
                    "access_token": settings.gitee.token,
                    "q": query
                }
                
                response = await client.get(url, params=params)
                
                if not response.is_success:
                    return f"Gitee API 请求失败: {response.status_code}"
                
                # 解析JSON响应，对应C#的JsonSerializer.Deserialize
                issues_data = response.json()
                if not issues_data:
                    return "未找到相关 Issue。"
                
                # 构建结果字符串，对应C#的StringBuilder逻辑
                result_lines = []
                for issue_data in issues_data:
                    issue = GiteeIssueListDto(**issue_data)
                    result_lines.append(f"[{issue.title}]({issue.html_url}) # {issue.number} - {issue.state}")
                
                # 保存到文档上下文，对应C#的DocumentContext.DocumentStore逻辑
                git_issues = []
                for issue_data in issues_data:
                    issue = GiteeIssueListDto(**issue_data)
                    git_issue_item = {
                        "author": issue.user.name,
                        "title": issue.title,
                        "url": issue.url,
                        "content": issue.body,
                        "created_at": datetime.fromisoformat(issue.created_at.replace('Z', '+00:00')) if issue.created_at else None,
                        "url_html": issue.html_url,
                        "state": issue.state,
                        "number": issue.number
                    }
                    git_issues.append(git_issue_item)
                DocumentContextManager.add_git_issues(git_issues)
                
                return "\n".join(result_lines)
                
        except Exception as e:
            return f"搜索 Issue 失败: {str(e)}"
    
    @kernel_function(
        name="SearchIssueComments",
        description="搜索指定编号 Issue 评论内容. "
                   "Parameters: "
                   "- issue_number (integer): Issue编号 "
                   "- max_results (integer): 最大返回数量"
    )
    async def search_issue_comments_async(
        self,
        issue_number: int,
        max_results: int = 5
    ) -> str:
        """
        搜索指定的一个issue下评论内容，对应C#的SearchIssueCommentsAsync方法
        
        Args:
            issue_number: Issue编号
            max_results: 最大返回数量
            
        Returns:
            评论内容字符串
        """
        try:
            # 检查Token配置，对应C#的GiteeOptions.Token检查
            if not hasattr(settings, 'gitee') or not settings.gitee.token:
                return "未配置 Gitee Token，无法搜索 Issue 评论。"
            
            async with httpx.AsyncClient() as client:
                # 构建URL，对应C#的URL构建逻辑
                url = f"{self.base_url}/repos/{self.owner}/{self.name}/issues/{issue_number}/comments"
                params = {
                    "access_token": settings.gitee.token,
                    "page": 1,
                    "per_page": max_results
                }
                
                response = await client.get(url, params=params)
                
                if not response.is_success:
                    return f"Gitee API 请求失败: {response.status_code}"
                
                # 解析JSON响应，对应C#的GetFromJsonAsync<GiteeIssusItem[]>
                comments_data = response.json()
                
                # 构建结果字符串，对应C#的StringBuilder逻辑
                result_lines = []
                
                if comments_data and len(comments_data) > 0:
                    result_lines.append(f"Issue #{issue_number} 评论：\n")
                    for comment_data in comments_data:
                        comment = GiteeIssusItem(**comment_data)
                        result_lines.append(f"  创建时间: {comment.created_at}")
                        result_lines.append(f"- [{comment.user.name}]({comment.user.html_url}): {comment.body}")
                else:
                    result_lines.append("未找到相关评论。")
                
                return "\n".join(result_lines)
                
        except Exception as e:
            return f"搜索 Issue 评论失败: {str(e)}" 