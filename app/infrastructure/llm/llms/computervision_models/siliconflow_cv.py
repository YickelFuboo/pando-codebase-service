from typing import Optional
import asyncio
import logging
from openai import AsyncOpenAI
from app.infrastructure.llm.llms.computervision_models.base.openai_base import OpenAIBase
from app.infrastructure.llm.llms.computervision_models.base.base import CONNECTION_TIMEOUT, MAX_RETRY_ATTEMPTS

class SiliconFlowCV(OpenAIBase):
    """硅基流动计算机视觉模型实现"""

    def __init__(self, api_key: str, model_name: str = "Qwen/Qwen2-VL-7B-Instruct", 
                 base_url: str = "https://api.siliconflow.cn/v1", language: str = "Chinese", **kwargs):
        """
        初始化硅基流动计算机视觉模型
        
        Args:
            api_key (str): 硅基流动API密钥
            model_name (str): 模型名称，默认为Qwen/Qwen2-VL-7B-Instruct
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
