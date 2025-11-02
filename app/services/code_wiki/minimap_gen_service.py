import re
import uuid
import json
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, insert
from dataclasses import dataclass, field
from semantic_kernel.functions import KernelArguments
from semantic_kernel.connectors.ai import PromptExecutionSettings, FunctionChoiceBehavior
from semantic_kernel.contents.chat_history import ChatHistory
from app.aiframework.agent_frame.semantic.kernel_factory import KernelFactory
from app.aiframework.prompts.prompt_template_load import get_prompt_template
from app.aiframework.agent_frame.semantic.functions.file_function import FileFunction
from app.config.settings import settings
from app.models.code_wiki import RepoWikiMiniMap


@dataclass
class MiniMapResult:
    """迷你地图结果"""
    title: Optional[str] = None
    url: Optional[str] = None
    nodes: List['MiniMapResult'] = field(default_factory=list)

class MiniMapService:
    def __init__(self, session: AsyncSession, document_id: str, local_path: str, git_url: str, branch: str, repo_catalogue: str):
        self.session = session
        self.document_id = document_id
        self.local_path = local_path
        self.git_url = git_url
        self.branch = branch
        self.repo_catalogue = repo_catalogue

    """迷你地图服务"""
    async def generate_mini_map(self) -> MiniMapResult:
        """生成知识图谱"""

        try:
            #document = await CodeWikiDocumentService.get_wiki_document_by_id(self.session, self.document_id)
            #if not document:
            #    raise ValueError(f"文档ID {self.document_id} 不存在")

            # 启动AI智能过滤
            kernel = await KernelFactory.get_kernel()
            kernel.add_plugin(FileFunction(self.local_path), "FileFunction")

            system_prompt = get_prompt_template("app/aiframework/prompts/code_wiki", "SystemExtensionPrompt")
            prompt = get_prompt_template("app/aiframework/prompts/code_wiki", "GenerateMindMap", {
                    "code_files": self.repo_catalogue,
                    "repository_url": self.git_url.replace(".git", ""),
                    "branch_name": self.branch,
                },
            )

            history = ChatHistory()
            history.add_system_message(system_prompt)
            history.add_user_message(prompt)

            # 将历史消息转换为字符串
            history_str = "\n".join(f"{msg.role}: {msg.content}" for msg in history.messages)

            # 流式调用，聚合文本
            response = await kernel.invoke_prompt(
                prompt=history_str,
                arguments=KernelArguments(
                    settings=PromptExecutionSettings(
                        function_choice_behavior=FunctionChoiceBehavior.Auto()
                    )
                )
            )
            result_str = str(response)

            # 删除<thinking>...</thinking>内容
            mini_map_text = re.sub(r"<thinking>.*?</thinking>", "", result_str, flags=re.DOTALL | re.IGNORECASE).strip()

            # 解析知识图谱
            lines = mini_map_text.split("\n")
            result = self._parse_mini_map_recursive(lines, 0, 0)

            # 删除旧的知识图谱
            await self.session.execute(
                delete(RepoWikiMiniMap)
                .where(RepoWikiMiniMap.document_id == self.document_id)
            )
            await self.session.commit()
            # 插入新的知识图谱
            await self.session.execute(
                insert(RepoWikiMiniMap)
                .values(
                    id=str(uuid.uuid4()),
                    document_id=self.document_id,
                    value=json.dumps(result, ensure_ascii=False)
                )
            )
            await self.session.commit()

            return result
        except Exception as e:
            logging.error(f"生成迷你地图失败: {e}")
            return MiniMapResult()
    
    def _parse_mini_map_recursive(self, lines: List[str], start_index: int, current_level: int) -> MiniMapResult:
        """递归解析迷你地图"""
        result = MiniMapResult()
        
        i = start_index
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            # 计算当前行的标题级别
            level = self._get_header_level(line)
            
            if level == 0:
                i += 1
                continue  # 不是标题行，跳过
            
            if level <= current_level and i > start_index:
                # 遇到同级或更高级的标题，结束当前层级的解析
                break
            
            if level == current_level + 1:
                # 解析标题和URL
                title, url = self._parse_title_and_url(line)
                node = MiniMapResult(title=title, url=url)
                
                # 递归解析子节点
                child_result = self._parse_mini_map_recursive(lines, i + 1, level)
                node.nodes = child_result.nodes
                
                if result.title is None:
                    # 如果这是第一个节点，设置为根节点
                    result.title = node.title
                    result.url = node.url
                    result.nodes = node.nodes
                else:
                    # 否则添加到子节点列表
                    result.nodes.append(node)
                
                # 跳过已处理的子节点
                i += 1
                while i < len(lines):
                    child_level = self._get_header_level(lines[i].strip())
                    if child_level > level:
                        i += 1
                    else:
                        break
            else:
                i += 1
        
        return result
    
    def _get_header_level(self, line: str) -> int:
        """获取标题级别"""
        level = 0
        for char in line:
            if char == '#':
                level += 1
            else:
                break
        return level
    
    def _parse_title_and_url(self, line: str) -> tuple[str, str]:
        """解析标题和URL"""
        # 移除开头的#号和空格
        content = line.lstrip('#').strip()
        
        # 检查是否包含URL格式 "标题:文件"
        if ':' in content:
            parts = content.split(':', 2)
            title = parts[0].strip()
            url = parts[1].strip()
            return title, url
        
        return content, ""