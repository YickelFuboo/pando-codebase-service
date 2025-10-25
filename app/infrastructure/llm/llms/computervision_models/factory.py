from typing import Dict, Type
from app.infrastructure.llm.llms.base_factory import BaseModelFactory
from .base.base import BaseComputerVision
from .openai_cv import OpenAICV
from .azure_cv import AzureOpenAICV
from .qwen_cv import QWenCV
from .zhipu_cv import ZhipuCV
from .ollama_cv import OllamaCV
from .gemini_cv import GeminiCV
from .siliconflow_cv import SiliconFlowCV


class ComputerVisionModelFactory(BaseModelFactory[BaseComputerVision]):
    """计算机视觉模型工厂类"""
    
    @property
    def _models(self) -> Dict[str, Type[BaseComputerVision]]:
        return {
            "openai": OpenAICV,
            "azure_openai": AzureOpenAICV,
            "qwen": QWenCV,
            "zhipu": ZhipuCV,
            "ollama": OllamaCV,
            "gemini": GeminiCV,
            "siliconflow": SiliconFlowCV,
        }

    def __init__(self):
        super().__init__("cv_models.json")


# 全局工厂实例
cv_factory = ComputerVisionModelFactory()
