import json
from openai.lib.azure import AsyncAzureOpenAI
from app.infrastructure.llm.llms.computervision_models.base.openai_base import OpenAIBase
from app.infrastructure.llm.llms.computervision_models.base.base import CONNECTION_TIMEOUT, MAX_RETRY_ATTEMPTS

class AzureOpenAICV(OpenAIBase):
    """Azure OpenAI 计算机视觉模型实现"""

    def __init__(self, api_key: str, model_name: str, base_url: str = None, 
                 language: str = "Chinese"):
        """
        初始化Azure OpenAI计算机视觉模型
        
        Args:
            api_key (str): Azure OpenAI API密钥（JSON格式）
            model_name (str): 模型名称
            base_url (str): Azure端点URL
            language (str): 语言设置
        """
        if not base_url:
            raise ValueError("Azure OpenAI base_url 不能为空")

        super().__init__(api_key, model_name, base_url, language)
        
        try:
            key_config = json.loads(api_key)
            api_key_value = key_config.get("api_key", "")
            api_version = key_config.get("api_version", "2024-02-01")
            
            self.client = AsyncAzureOpenAI(
                api_key=api_key_value, 
                azure_endpoint=base_url, 
                api_version=api_version,
                timeout=CONNECTION_TIMEOUT,  # 使用统一超时配置
                max_retries=MAX_RETRY_ATTEMPTS  # 最多重试3次
            )
        except json.JSONDecodeError:
            # 如果不是JSON格式，直接使用api_key
            self.client = AsyncAzureOpenAI(
                api_key=api_key, 
                azure_endpoint=base_url, 
                api_version="2024-02-01",
                timeout=CONNECTION_TIMEOUT,  # 使用统一超时配置
                max_retries=MAX_RETRY_ATTEMPTS  # 最多重试3次
            )