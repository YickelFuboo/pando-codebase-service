from typing import Dict, Type
from app.infrastructure.llm.llms.base_factory import BaseModelFactory
from app.infrastructure.llm.llms.chat_models.base.base import LLM
from app.infrastructure.llm.llms.chat_models.deepseek_llm import DeepSeekModels
from app.infrastructure.llm.llms.chat_models.claude_llm import ClaudeModels
from app.infrastructure.llm.llms.chat_models.openai_llm import OpenAIModels
from app.infrastructure.llm.llms.chat_models.qwen_llm import QwenModels
from app.infrastructure.llm.llms.chat_models.siliconflow_llm import SiliconFlowModels
from app.infrastructure.llm.llms.chat_models.fuyao_llm import FuYaoModels

# =============================================================================
# 聊天模型工厂
# =============================================================================

class LLMFactory(BaseModelFactory):
    """聊天模型工厂类"""
    
    @property
    def _models(self) -> Dict[str, Type[LLM]]:
        return {
            "deepseek": DeepSeekModels,
            "claude": ClaudeModels,
            "openai": OpenAIModels,
            "qwen": QwenModels,
            "siliconflow": SiliconFlowModels,
            "fuyao": FuYaoModels,
        }
    
    def __init__(self):
        super().__init__("chat_models.json")
    

# 全局工厂实例
llm_factory = LLMFactory()