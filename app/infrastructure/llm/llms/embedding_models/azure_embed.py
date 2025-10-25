import json
from typing import List, Tuple
import numpy as np
from openai.lib.azure import AsyncAzureOpenAI
from app.infrastructure.llm.llms.embedding_models.openai_embed import OpenAIEmbed
from app.infrastructure.llm.llms.embedding_models.base import CONNECTION_TIMEOUT, MAX_RETRY_ATTEMPTS


class AzureEmbed(OpenAIEmbed):
    """Azure OpenAI嵌入模型实现"""

    def __init__(self, api_key: str, model_name: str, base_url: str, **kwargs):
        """
        初始化Azure OpenAI嵌入模型
        
        Args:
            api_key (str): API密钥（JSON格式，包含api_key、api_version等）
            model_name (str): 模型名称
            base_url (str): API基础URL
            **kwargs: 其他参数
        """
        #super().__init__(api_key, model_name, base_url)
        key_data = json.loads(api_key)
        api_key_value = key_data.get("api_key", "")
        api_version = key_data.get("api_version", "2024-02-01")
        
        self.client = AsyncAzureOpenAI(
            api_key=api_key_value, 
            azure_endpoint=base_url, 
            api_version=api_version,
            timeout=CONNECTION_TIMEOUT,
            max_retries=MAX_RETRY_ATTEMPTS
        )
        self.model_name = model_name