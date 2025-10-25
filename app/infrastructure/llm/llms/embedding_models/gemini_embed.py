from typing import List, Tuple
import asyncio
import google.generativeai as genai
import numpy as np
import logging
from app.infrastructure.llm.llms.embedding_models.base import BaseEmbedding, MAX_RETRY_ATTEMPTS
from app.infrastructure.llm.llms.utils import truncate, num_tokens_from_string


class GeminiEmbed(BaseEmbedding):
    """Google Gemini嵌入模型实现"""

    def __init__(self, api_key: str, model_name: str = "text-embedding-004", **kwargs):
        """
        初始化Gemini嵌入模型
        
        Args:
            api_key (str): Google API密钥
            model_name (str): 模型名称，默认为text-embedding-004
            **kwargs: 其他参数
        """
        if not model_name.startswith("models/"):
            model_name = "models/" + model_name

        super().__init__(api_key, model_name)


    async def encode(self, texts: List[str]) -> Tuple[np.ndarray, int]:
        """
        将文本列表编码为嵌入向量
        
        Args:
            texts (List[str]): 待编码的文本列表
            
        Returns:
            Tuple[np.ndarray, int]: (嵌入向量数组, token总数)
        """
        texts = [truncate(t, 2048) for t in texts]
        
        genai.configure(api_key=self.key)
        
        batch_size = 16
        ress = []
        
        for i in range(0, len(texts), batch_size):
            for attempt in range(MAX_RETRY_ATTEMPTS):
                try:
                    result = await asyncio.to_thread(
                        genai.embed_content,
                        model=self.model_name, 
                        content=texts[i : i + batch_size], 
                        task_type="retrieval_document", 
                        title="Embedding of single string"
                    )
                    ress.extend(result["embedding"])
                    break  # 成功，跳出重试循环
                except Exception as e:
                    if attempt < MAX_RETRY_ATTEMPTS - 1 and self._is_retryable_error(e):
                        delay = self._get_delay(attempt)
                        logging.warning(f"Gemini嵌入编码失败，重试 (尝试 {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}. 等待 {delay:.2f}s...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logging.error(f"Gemini嵌入编码最终失败: {e}")
                        raise e
        
        return np.array(ress), self._total_token_count(texts=texts)

    async def encode_queries(self, text: str) -> Tuple[np.ndarray, int]:
        """
        将查询文本编码为嵌入向量
        
        Args:
            text (str): 待编码的查询文本
            
        Returns:
            Tuple[np.ndarray, int]: (嵌入向量, token总数)
        """
        genai.configure(api_key=self.key)
        
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                result = await asyncio.to_thread(
                    genai.embed_content,
                    model=self.model_name, 
                    content=truncate(text, 2048), 
                    task_type="retrieval_document", 
                    title="Embedding of single string"
                )
                return np.array(result["embedding"]), self._total_token_count(texts=[text])
            except Exception as e:
                if attempt < MAX_RETRY_ATTEMPTS - 1 and self._is_retryable_error(e):
                    delay = self._get_delay(attempt)
                    logging.warning(f"Gemini查询编码失败，重试 (尝试 {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}. 等待 {delay:.2f}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logging.error(f"Gemini查询编码最终失败: {e}")
                    raise e