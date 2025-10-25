from typing import List, Tuple
from urllib.parse import urljoin
import numpy as np
import aiohttp
import asyncio
import logging
from app.infrastructure.llm.llms.rerank_models.base import BaseRank, MAX_RETRY_ATTEMPTS
from app.infrastructure.llm.llms.utils import num_tokens_from_string


class NvidiaRank(BaseRank):
    """NVIDIA重排序模型实现"""
    
    def __init__(self, api_key: str, model_name: str, base_url: str = "https://ai.api.nvidia.com/v1/retrieval/nvidia/", **kwargs):
        """
        初始化NVIDIA重排序模型
        
        Args:
            api_key (str): NVIDIA API密钥
            model_name (str): 模型名称
            base_url (str): API基础URL，默认为NVIDIA官方URL
        """
        super().__init__(api_key, model_name, base_url, **kwargs)

        if self.model_name == "nvidia/nv-rerankqa-mistral-4b-v3":
            self.base_url = urljoin(base_url, "nv-rerankqa-mistral-4b-v3/reranking")

        if self.model_name == "nvidia/rerank-qa-mistral-4b":
            self.base_url = urljoin(base_url, "reranking")
            self.model_name = "nv-rerank-qa-mistral-4b:1"

        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

    async def similarity(self, query: str, texts: List[str]) -> Tuple[np.ndarray, int]:
        """
        计算查询与文本列表的相似度分数
        
        Args:
            query (str): 查询文本
            texts (List[str]): 待排序的文本列表
            
        Returns:
            Tuple[np.ndarray, int]: (相似度分数数组, token数量)
        """
        data = {
            "model": self.model_name,
            "query": {"text": query},
            "passages": [{"text": text} for text in texts],
            "truncate": "END",
            "top_n": len(texts),
        }
        
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.base_url, headers=self.headers, json=data) as response:
                        response.raise_for_status()
                        res = await response.json()
                    
                    rank = np.zeros(len(texts), dtype=float)
                    
                    for d in res["rankings"]:
                        rank[d["index"]] = d["logit"]
                    
                    return rank, self._total_token_count(res, texts)
                
            except Exception as e:
                if attempt < MAX_RETRY_ATTEMPTS - 1 and self._is_retryable_error(e):
                    delay = self._get_delay(attempt)
                    logging.warning(f"NVIDIA重排序失败，重试 (尝试 {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}. 等待 {delay:.2f}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logging.error(f"NVIDIA重排序最终失败: {e}")
                    raise RuntimeError(f"**ERROR**: {e}")