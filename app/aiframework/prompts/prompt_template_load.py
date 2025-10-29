import os
import dataclasses
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.utils.common import get_project_base_directory

def get_prompt_template(path: str, name: str, params: dict = None) -> str:
    """
    Load and return a prompt template using Jinja2.

    Args:
        path: Relative path to the template directory within the project
        name: Name of the prompt template file (without .md extension)
        params: Dictionary of parameters to substitute in the template (optional)

    Returns:
        The template string with proper variable substitution syntax
    """
    try:
        # 获取项目根目录
        project_root = get_project_base_directory()
        
        # 构建完整的模板目录路径
        template_dir = os.path.join(project_root, path)
        
        # 创建Jinja2环境
        custom_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        
        # 加载模板
        template = custom_env.get_template(f"{name}.md")
        
        # 如果有参数则应用参数，否则直接渲染
        if params:
            return template.render(**params)
        else:
            return template.render()
    except Exception as e:
        raise ValueError(f"Error loading template {name} from {path}: {e}")
