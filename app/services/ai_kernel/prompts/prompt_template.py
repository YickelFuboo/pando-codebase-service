import os
import asyncio


class PromptTemplate:

    @staticmethod
    async def get_prompt_template(file_name: str) -> str:
        """
        Load and return a prompt template using Jinja2.

        Args:
            file_name: Name of the prompt template file (without .md extension)

        Returns:
            The template string with proper variable substitution syntax
        """
        try:
            #根据file_name获取文件路径
            file_path = os.path.join(os.path.dirname(__file__), file_name)

            # 异步读取文件内容
            content = await asyncio.to_thread(lambda: open(file_path, "r", encoding="utf-8").read())

            return content
        except Exception as e:
            raise ValueError(f"Error loading template {file_name}: {e}")