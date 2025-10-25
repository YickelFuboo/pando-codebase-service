from typing import List, Tuple
from urllib.parse import urljoin
import numpy as np
import asyncio
import logging
from openai import AsyncOpenAI
from app.infrastructure.llm.llms.embedding_models.base import BaseEmbedding, MAX_RETRY_ATTEMPTS
from app.infrastructure.llm.llms.utils import truncate


class LocalAIEmbed(BaseEmbedding):
    """LocalAI嵌入模型实现"""
    
    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        """
        初始化LocalAI嵌入模型
        
        Args:
            api_key (str): API密钥（LocalAI通常使用"empty"）
            model_name (str): 模型名称
            base_url (str): LocalAI服务的基础URL
        """
        if not base_url:
            raise ValueError("Local embedding model url cannot be None")
        
        # 确保base_url以/v1结尾
        base_url = urljoin(base_url, "v1")
        
        super().__init__(api_key, model_name, base_url, **kwargs)
        
        # 处理模型名称，移除可能的"___"分隔符
        self.model_name = model_name.split("___")[0]
        
        # 创建AsyncOpenAI客户端，使用空API密钥
        self.client = AsyncOpenAI(api_key="empty", base_url=base_url)

    async def encode(self, texts: List[str]) -> Tuple[np.ndarray, int]:
        """
        将文本列表编码为嵌入向量
        
        Args:
            texts (List[str]): 待编码的文本列表
            
        Returns:
            Tuple[np.ndarray, int]: (嵌入向量数组, token总数)
        """
        batch_size = 16
        ress = []
        
        for i in range(0, len(texts), batch_size):
            for attempt in range(MAX_RETRY_ATTEMPTS):
                try:
                    res = await self.client.embeddings.create(
                        input=texts[i : i + batch_size], 
                        model=self.model_name
                    )
                    ress.extend([d.embedding for d in res.data])
                    break  # 成功，跳出重试循环
                except Exception as e:
                    if attempt < MAX_RETRY_ATTEMPTS - 1 and self._is_retryable_error(e):
                        delay = self._get_delay(attempt)
                        logging.warning(f"LocalAI嵌入编码失败，重试 (尝试 {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}. 等待 {delay:.2f}s...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logging.error(f"LocalAI嵌入编码最终失败: {e}")
                        raise e
        
        # LocalAI/LMStudio通常不提供token计数，使用固定值
        return np.array(ress), 1024

    async def encode_queries(self, text: str) -> Tuple[np.ndarray, int]:
        """
        将查询文本编码为嵌入向量
        
        Args:
            text (str): 待编码的查询文本
            
        Returns:
            Tuple[np.ndarray, int]: (嵌入向量, token总数)
        """
        embds, token_count = await self.encode([text])
        return np.array(embds[0]), token_count