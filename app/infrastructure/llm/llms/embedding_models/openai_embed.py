from typing import List, Tuple
import numpy as np
import logging
import asyncio
from openai import AsyncOpenAI
from app.infrastructure.llm.llms.embedding_models.base import BaseEmbedding, CONNECTION_TIMEOUT, MAX_RETRY_ATTEMPTS
from app.infrastructure.llm.llms.utils import truncate


class OpenAIEmbed(BaseEmbedding):
    """OpenAI嵌入模型实现"""
    def __init__(self, api_key: str, model_name: str = "text-embedding-ada-002", base_url: str = "https://api.openai.com/v1", **kwargs):
        """
        初始化OpenAI嵌入模型
        
        Args:
            api_key (str): OpenAI API密钥
            model_name (str): 模型名称，默认为text-embedding-ada-002
            base_url (str): API基础URL，默认为OpenAI官方URL
            **kwargs: 其他参数
        """
        super().__init__(api_key, model_name, base_url, **kwargs)

        self.client = AsyncOpenAI(
            api_key=api_key, 
            base_url=base_url,
            timeout=CONNECTION_TIMEOUT,
            max_retries=MAX_RETRY_ATTEMPTS
        )

    async def encode(self, texts: List[str]) -> Tuple[np.ndarray, int]:
        """
        将文本列表编码为嵌入向量
        
        Args:
            texts (List[str]): 待编码的文本列表
            
        Returns:
            Tuple[np.ndarray, int]: (嵌入向量数组, token总数)
        """
        # OpenAI要求批次大小<=16
        batch_size = 16
        texts = [truncate(t, 8191) for t in texts]
        ress = []

        total_tokens = 0
        for i in range(0, len(texts), batch_size):
            # 重试逻辑
            for attempt in range(MAX_RETRY_ATTEMPTS):
                try:
                    res = await self.client.embeddings.create(input=texts[i : i + batch_size], model=self.model_name)
                    ress.extend([d.embedding for d in res.data])
                    total_tokens += self._total_token_count(res)
                    break  # 成功则跳出重试循环
                    
                except Exception as e:
                    if attempt < MAX_RETRY_ATTEMPTS - 1 and self._is_retryable_error(e):
                        delay = self._get_delay(attempt)
                        logging.warning(f"OpenAI嵌入编码失败，重试 (尝试 {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}. 等待 {delay:.2f}s...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logging.error(f"OpenAI嵌入编码最终失败: {e}")
                        raise
        
        return np.array(ress), total_tokens

    async def encode_queries(self, text: str) -> Tuple[np.ndarray, int]:
        """
        将查询文本编码为嵌入向量
        
        Args:
            text (str): 待编码的查询文本
            
        Returns:
            Tuple[np.ndarray, int]: (嵌入向量, token总数)
        """
        # 重试逻辑
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                res = await self.client.embeddings.create(input=[truncate(text, 8191)], model=self.model_name)
                return np.array(res.data[0].embedding), self._total_token_count(res)
                
            except Exception as e:
                if attempt < MAX_RETRY_ATTEMPTS - 1 and self._is_retryable_error(e):
                    delay = self._get_delay(attempt)
                    logging.warning(f"OpenAI查询编码失败，重试 (尝试 {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}. 等待 {delay:.2f}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logging.error(f"OpenAI查询编码最终失败: {e}")
                    raise