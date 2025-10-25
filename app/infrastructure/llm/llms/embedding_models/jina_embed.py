from typing import List, Tuple
import numpy as np
import aiohttp
import asyncio
import logging
from app.infrastructure.llm.llms.embedding_models.base import BaseEmbedding, MAX_RETRY_ATTEMPTS
from app.infrastructure.llm.llms.utils import truncate


class JinaEmbed(BaseEmbedding):
    """Jina嵌入模型实现"""

    def __init__(self, api_key: str, model_name: str = "jina-embeddings-v3", base_url: str = "https://api.jina.ai/v1/embeddings", **kwargs):
        """
        初始化Jina嵌入模型
        
        Args:
            api_key (str): API密钥
            model_name (str): 模型名称，默认为jina-embeddings-v3
            base_url (str): API基础URL，默认为Jina官方URL
        """
        super().__init__(api_key, model_name, base_url, **kwargs)
        self.headers = {
            "Content-Type": "application/json", 
            "Authorization": f"Bearer {api_key}"
        }

    async def encode(self, texts: List[str]) -> Tuple[np.ndarray, int]:
        """
        将文本列表编码为嵌入向量
        
        Args:
            texts (List[str]): 待编码的文本列表
            
        Returns:
            Tuple[np.ndarray, int]: (嵌入向量数组, token总数)
        """
        texts = [truncate(t, 8196) for t in texts]
        batch_size = 16
        ress = []
        token_count = 0

        for i in range(0, len(texts), batch_size):
            for attempt in range(MAX_RETRY_ATTEMPTS):
                try:
                    async with aiohttp.ClientSession() as session:
                        data = {
                            "model": self.model_name, 
                            "input": texts[i : i + batch_size], 
                            "encoding_type": "float"
                        }
                        async with session.post(self.base_url, headers=self.headers, json=data) as response:
                            res = await response.json()
                            ress.extend([d["embedding"] for d in res["data"]])
                            
                            token_count += self._total_token_count(res)
                            break  # 成功，跳出重试循环
                except Exception as e:
                    if attempt < MAX_RETRY_ATTEMPTS - 1 and self._is_retryable_error(e):
                        delay = self._get_delay(attempt)
                        logging.warning(f"Jina嵌入编码失败，重试 (尝试 {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}. 等待 {delay:.2f}s...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logging.error(f"Jina嵌入编码最终失败: {e}")
                        raise e
        return np.array(ress), token_count

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