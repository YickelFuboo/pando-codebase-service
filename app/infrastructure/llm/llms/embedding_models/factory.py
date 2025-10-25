from typing import Dict, Type
from app.infrastructure.llm.llms.base_factory import BaseModelFactory
from .azure_embed import AzureEmbed
from .baai_embed import BAAIEmbedding
from .baichuan_embed import BaiChuanEmbed
from .baidu_yiyan_embed import BaiduYiyanEmbed
from .base import BaseEmbedding
from .bedrock_embed import BedrockEmbed
from .cohere_embed import CoHereEmbed
from .gemini_embed import GeminiEmbed
from .huggingface_embed import HuggingFaceEmbed
from .jina_embed import JinaEmbed
from .localai_embed import LocalAIEmbed
from .mistral_embed import MistralEmbed
from .nvidia_embed import NvidiaEmbed
from .ollama_embed import OllamaEmbed
from .openai_embed import OpenAIEmbed
from .qwen_embed import QWenEmbed
from .siliconflow_embed import SILICONFLOWEmbed
from .voyage_embed import VoyageEmbed
from .xinference_embed import XinferenceEmbed
from .zhipu_embed import ZhipuEmbed


class EmbeddingModelFactory(BaseModelFactory[BaseEmbedding]):
    """嵌入模型工厂类"""
    
    @property
    def _models(self) -> Dict[str, Type[BaseEmbedding]]:
        return {
            "baai": BAAIEmbedding,
            "openai": OpenAIEmbed,
            "qwen": QWenEmbed,
            "zhipu": ZhipuEmbed,
            "ollama": OllamaEmbed,
            "azure": AzureEmbed,
            "baichuan": BaiChuanEmbed,
            "jina": JinaEmbed,
            "cohere": CoHereEmbed,
            "siliconflow": SILICONFLOWEmbed,
            "localai": LocalAIEmbed,
            "bedrock": BedrockEmbed,
            "gemini": GeminiEmbed,
            "nvidia": NvidiaEmbed,
            "xinference": XinferenceEmbed,
            "mistral": MistralEmbed,
            "baidu_yiyan": BaiduYiyanEmbed,
            "voyage": VoyageEmbed,
            "huggingface": HuggingFaceEmbed,
        }

    def __init__(self):
        super().__init__("embedding_models.json")


# 全局工厂实例
embedding_factory = EmbeddingModelFactory()