from openai import AsyncOpenAI
from app.infrastructure.llm.llms.computervision_models.base.openai_base import OpenAIBase
from app.infrastructure.llm.llms.computervision_models.base.base import CONNECTION_TIMEOUT, MAX_RETRY_ATTEMPTS


class OpenAICV(OpenAIBase):
    """OpenAI 计算机视觉模型实现"""

    def __init__(self, api_key: str, model_name: str = "gpt-4-vision-preview", 
                 base_url: str = "https://api.openai.com/v1", language: str = "Chinese", **kwargs):
        """
        初始化OpenAI计算机视觉模型
        
        Args:
            api_key (str): OpenAI API密钥
            model_name (str): 模型名称，默认为gpt-4-vision-preview
            base_url (Optional[str]): API基础URL
            language (str): 语言设置
        """
        super().__init__(api_key, model_name, base_url, language, **kwargs)
        
        # 配置客户端，添加超时和重试设置
        self.client = AsyncOpenAI(
            api_key=api_key, 
            base_url=base_url,
            timeout=CONNECTION_TIMEOUT,
            max_retries=MAX_RETRY_ATTEMPTS
        )