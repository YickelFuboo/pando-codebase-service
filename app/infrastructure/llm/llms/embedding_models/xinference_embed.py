from typing import List, Tuple
from urllib.parse import urljoin
import numpy as np
import asyncio
import logging
from openai import AsyncOpenAI
from app.infrastructure.llm.llms.embedding_models.base import BaseEmbedding, MAX_RETRY_ATTEMPTS


class XinferenceEmbed(BaseEmbedding):
    """Xinference嵌入模型实现"""
    
    _FACTORY_NAME = "Xinference"

    def __init__(self, api_key: str, model_name: str = "", base_url: str = "", **kwargs):
        """
        初始化Xinference嵌入模型
        
        Args:
            api_key (str): API密钥
            model_name (str): 模型名称
            base_url (str): Xinference服务的基础URL
        """
        # 确保base_url以/v1结尾
        base_url = urljoin(base_url, "v1")
        
        super().__init__(api_key, model_name, base_url, **kwargs)
        
        # 创建OpenAI兼容客户端
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

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
        total_tokens = 0
        
        for i in range(0, len(texts), batch_size):
            for attempt in range(MAX_RETRY_ATTEMPTS):
                try:
                    res = await self.client.embeddings.create(
                        input=texts[i : i + batch_size], 
                        model=self.model_name
                    )
                    ress.extend([d.embedding for d in res.data])
                    
                    total_tokens += self._total_token_count(res)
                    break  # 成功，跳出重试循环

                except Exception as e:
                    if attempt < MAX_RETRY_ATTEMPTS - 1 and self._is_retryable_error(e):
                        delay = self._get_delay(attempt)
                        logging.warning(f"Xinference嵌入编码失败，重试 (尝试 {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}. 等待 {delay:.2f}s...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logging.error(f"Xinference嵌入编码最终失败: {e}")
                        raise e
        
        return np.array(ress), total_tokens

    async def encode_queries(self, text: str) -> Tuple[np.ndarray, int]:
        """
        将查询文本编码为嵌入向量
        
        Args:
            text (str): 待编码的查询文本
            
        Returns:
            Tuple[np.ndarray, int]: (嵌入向量, token总数)
        """
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                res = await self.client.embeddings.create(
                    input=[text], 
                    model=self.model_name
                )

                return np.array(res.data[0].embedding), self._total_token_count(res)

            except Exception as e:
                if attempt < MAX_RETRY_ATTEMPTS - 1 and self._is_retryable_error(e):
                    delay = self._get_delay(attempt)
                    logging.warning(f"Xinference查询编码失败，重试 (尝试 {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}. 等待 {delay:.2f}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logging.error(f"Xinference查询编码最终失败: {e}")
                    raise e