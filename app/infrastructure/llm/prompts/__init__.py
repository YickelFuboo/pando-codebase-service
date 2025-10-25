# 各模型工厂实例
from .prompt_template_load import get_prompt_template
from .prompt_template_load import get_prompt_template_with_params

__all__ = [
    # 工厂实例
    "get_prompt_template",
    "get_prompt_template_with_params",
]