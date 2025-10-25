from openai import AsyncOpenAI
from app.infrastructure.llm.llms.chat_models.base.openai_base import OpenAIBase
from app.infrastructure.llm.llms.chat_models.base.base import CONNECTION_TIMEOUT, MAX_RETRY_ATTEMPTS

class DeepSeekModels(OpenAIBase):
    """DeepSeek模型系列"""
    
    def __init__(self, api_key: str, model_name: str = "deepseek-chat", base_url: str = "https://api.deepseek.com/v1", language: str = "Chinese", **kwargs):
        """
        初始化DeepSeek模型
        
        Args:
            api_key (str): DeepSeek API密钥
            model_name (str): 模型名称，默认为deepseek-chat
            base_url (str): API基础URL，默认为DeepSeek官方API
            language (str): 语言设置
            **kwargs: 其他参数
        """
        super().__init__(api_key, model_name, base_url, language, **kwargs)
        
        # 创建DeepSeek客户端（使用OpenAI兼容接口）
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=CONNECTION_TIMEOUT,  # 使用统一超时配置
            max_retries=MAX_RETRY_ATTEMPTS
        )