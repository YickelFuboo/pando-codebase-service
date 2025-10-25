import uuid
import re
import json
import asyncio
import logging
from typing import List
from datetime import datetime
from semantic_kernel.functions import KernelArguments
from semantic_kernel.connectors.ai import PromptExecutionSettings, FunctionChoiceBehavior
from app.services.ai_kernel.kernel_factory import KernelFactory
from .local_repo_service import LocalRepoService


class CodeWikiService:
    """Code Wiki服务类 - 提供代码Wiki的创建、更新和查询功能"""

    def __init__(self, document_id: str, local_path: str, git_url: str, branch: str):
        self.document_id = document_id
        self.local_path = local_path
        self.git_url = git_url
        self.branch = branch
        self.kernel_factory = KernelFactory()
        self.kernel = self.kernel_factory.get_kernel(self.local_path)

    async def generate_readme(self) -> str:
        """步骤1: 生成README文档
        1) 优先读取本地 README（多种扩展名）
        2) 若不存在，则获取目录结构并尝试通过语义插件 CodeAnalysis/GenerateReadme 生成
        3) 解析 <readme> 标签内容；若失败则直接使用原始文本
        4) 返回生成/读取的 README 文本（本项目模型暂无 readme 字段，暂不落库）
        """
        try:
            # 1. 优先读取现有 README
            readme: str = await LocalRepoService.get_readme_file(self.local_path)

            # 2. 若无本地 README，则使用AI生成
            if not readme:
                # 2.1 获取目录结构（紧凑格式）
                try:
                    catalogue = await LocalRepoService.get_catalogue(self.local_path)
                except Exception as e:
                    logging.warning(f"获取目录结构失败，将使用空目录结构。错误: {e}")
                    catalogue = ""

                # 2.2 创建 AI 内核（加载 CodeAnalysis 语义插件 + FileFunction 原生插件）
                try:
                    kernel_factory = KernelFactory()
                    # 加载语义插件以便可用 CodeAnalysis/GenerateReadme
                    kernel = await kernel_factory.get_kernel(git_local_path=self.local_path, is_code_analysis=True)
                except Exception as e:
                    logging.error(f"创建AI内核失败，将回退到基础README。错误: {e}")
                    kernel = None

                # 2.3 调用生成 README 的语义插件
                generated = None
                if kernel is not None:
                    try:
                        generate_fn = kernel.get_plugin("code_analysis").get("GenerateReadme")
                        if generate_fn is not None:
                            result = await kernel.invoke(
                                function=generate_fn,
                                arguments=KernelArguments(
                                    settings=PromptExecutionSettings(
                                        function_choice_behavior=FunctionChoiceBehavior.Auto()
                                    ),
                                    catalogue=catalogue or "",
                                    git_repository=self.git_url,
                                    branch=self.branch,
                                )
                            )
                            generated = str(result) if result else None
                        else:
                            logging.warning("未发现语义插件 CodeAnalysis/GenerateReadme，跳过AI生成。")
                            generated = None
                    except Exception as e:
                        logging.error(f"调用GenerateReadme插件失败，将回退到基础README。错误: {e}")

                # 2.4 解析 AI 输出
                if generated:
                    match = re.search(r"<readme>(.*?)</readme>", generated, re.DOTALL | re.IGNORECASE)
                    readme = match.group(1) if match else generated

            return readme
        except Exception as e:
            logging.error(f"生成README失败: {e}")
            return ""