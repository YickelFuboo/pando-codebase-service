from typing import List, Tuple
import numpy as np
import aiohttp
import asyncio
import logging
from app.infrastructure.llm.llms.rerank_models.base import BaseRank, MAX_RETRY_ATTEMPTS

class JinaRank(BaseRank):
    """Jina重排序模型实现"""
    
    def __init__(self, api_key: str, model_name: str = "jina-reranker-v2-base-multilingual", base_url: str = "https://api.jina.ai/v1/rerank", **kwargs):
        """
        初始化Jina重排序模型
        
        Args:
            api_key (str): Jina API密钥
            model_name (str): 模型名称，默认为jina-reranker-v2-base-multilingual
            base_url (str): API基础URL，默认为Jina官方URL
        """
        super().__init__(api_key, model_name, base_url, **kwargs)
 
        self.headers = {
            "Content-Type": "application/json", 
            "Authorization": f"Bearer {api_key}"
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
        # 截断文本到8196字符
        texts = [self._truncate_text(t, 8196) for t in texts]
        
        data = {
            "model": self.model_name, 
            "query": query, 
            "documents": texts, 
            "top_n": len(texts)
        }
        
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.base_url, headers=self.headers, json=data) as response:
                        response.raise_for_status()
                        res = await response.json()
                    
                    rank = np.zeros(len(texts), dtype=float)
                    
                    for d in res["results"]:
                        rank[d["index"]] = d["relevance_score"]
                        
                    return rank, self._total_token_count(res, texts)
                
            except Exception as e:
                if attempt < MAX_RETRY_ATTEMPTS - 1 and self._is_retryable_error(e):
                    delay = self._get_delay(attempt)
                    logging.warning(f"Jina重排序失败，重试 (尝试 {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}. 等待 {delay:.2f}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logging.error(f"Jina重排序最终失败: {e}")
                    raise RuntimeError(f"**ERROR**: {e}")