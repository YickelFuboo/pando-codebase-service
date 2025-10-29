import httpx
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass
from semantic_kernel.functions import kernel_function
from app.config.settings import settings
from app.services.task_context.document_context import DocumentContextManager, GitIssue


@dataclass
class GithubUser:
    """GitHub用户信息"""
    login: str
    id: int
    node_id: str
    avatar_url: str
    gravatar_id: str
    url: str
    html_url: str
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
    site_admin: bool
    name: Optional[str] = None
    email: Optional[str] = None
    bio: Optional[str] = None
    company: Optional[str] = None
    blog: Optional[str] = None
    location: Optional[str] = None
    hireable: Optional[bool] = None
    twitter_username: Optional[str] = None
    public_repos: Optional[int] = None
    public_gists: Optional[int] = None
    followers: Optional[int] = None
    following: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class GithubIssue:
    """GitHub Issue信息"""
    url: str
    repository_url: str
    labels_url: str
    comments_url: str
    events_url: str
    html_url: str
    id: int
    node_id: str
    number: int
    title: str
    user: GithubUser
    labels: List[dict]
    state: str
    locked: bool
    assignee: Optional[GithubUser]
    assignees: List[GithubUser]
    milestone: Optional[dict]
    comments: int
    created_at: str
    updated_at: str
    closed_at: Optional[str]
    author_association: str
    active_lock_reason: Optional[str]
    body: Optional[str]
    reactions: dict
    timeline_url: str
    performed_via_github_app: Optional[bool]
    state_reason: Optional[str]


@dataclass
class GithubIssueComment:
    """GitHub Issue评论信息"""
    url: str
    html_url: str
    issue_url: str
    id: int
    node_id: str
    user: GithubUser
    created_at: str
    updated_at: str
    author_association: str
    body: str
    reactions: dict


class GithubFunction:
    """GitHub相关功能，对应C#的GithubFunction类"""
    
    def __init__(self, owner: str, name: str, branch: str):
        """
        初始化GithubFunction
        
        Args:
            owner: 仓库所有者
            name: 仓库名称
            branch: 分支名称
        """
        self.owner = owner
        self.name = name
        self.branch = branch
        self.base_url = "https://api.github.com"
    
    def _get_headers(self):
        """获取请求头，对应C#的GitHubClient配置"""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "KoalaWiki/1.0"  # 对应C#的ProductHeaderValue("KoalaWiki")
        }
        
        # 对应C#的Credentials配置
        if hasattr(settings, 'github') and settings.github.token:
            headers["Authorization"] = f"token {settings.github.token}"
        
        return headers
    
    @kernel_function(
        name="SearchIssues",
        description="搜索相关 Issue 内容. "
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
            async with httpx.AsyncClient() as client:
                # 构建搜索查询，对应C#的SearchIssuesRequest
                search_query = f"{query} repo:{self.owner}/{self.name} is:issue"
                url = f"{self.base_url}/search/issues"
                params = {
                    "q": search_query,
                    "per_page": max_results,
                    "sort": "updated",
                    "order": "desc"
                }
                
                response = await client.get(url, params=params, headers=self._get_headers())
                
                if not response.is_success:
                    return f"GitHub API 请求失败: {response.status_code}"
                
                search_result = response.json()
                issues_data = search_result.get("items", [])
                
                if not issues_data:
                    return "未找到相关 Issue。"
                
                # 构建结果字符串，对应C#的StringBuilder逻辑
                result_lines = []
                for issue_data in issues_data:
                    issue = GithubIssue(**issue_data)
                    result_lines.append(f"[{issue.title}]({issue.html_url}) # {issue.number} - {issue.state}")
                
                # 保存到文档上下文，使用DocumentContextManager
                git_issues = []
                for issue_data in issues_data:
                    issue = GithubIssue(**issue_data)
                    git_issue = GitIssue(
                        title=issue.title,
                        url=issue.url,
                        content=issue.body or "",
                        author=issue.user.name or issue.user.login,
                        url_html=issue.html_url,
                        state=issue.state,
                        number=str(issue.number),
                        created_at=datetime.fromisoformat(issue.created_at.replace('Z', '+00:00')) if issue.created_at else None
                    )
                    git_issues.append(git_issue)
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
            async with httpx.AsyncClient() as client:
                # 对应C#的client.Issue.Comment.GetAllForIssue
                url = f"{self.base_url}/repos/{self.owner}/{self.name}/issues/{issue_number}/comments"
                params = {
                    "per_page": max_results
                }
                
                response = await client.get(url, params=params, headers=self._get_headers())
                
                if not response.is_success:
                    return f"GitHub API 请求失败: {response.status_code}"
                
                comments_data = response.json()
                
                # 构建结果字符串，对应C#的StringBuilder逻辑
                result_lines = []
                
                if comments_data and len(comments_data) > 0:
                    result_lines.append(f"Issue #{issue_number} 评论：\n")
                    for comment_data in comments_data:
                        comment = GithubIssueComment(**comment_data)
                        result_lines.append(f"  创建时间: {comment.created_at}")
                        result_lines.append(f"- [{comment.user.login}]({comment.user.html_url}): {comment.body}")
                else:
                    result_lines.append("未找到相关评论。")
                
                return "\n".join(result_lines)
                
        except Exception as e:
            return f"获取 Issue 评论失败: {str(e)}" 