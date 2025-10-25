import json
import httpx
from typing import Optional
from semantic_kernel.functions import kernel_function
from app.config.settings import settings


class RagFunction:
    """RAG函数，对应C#的RagFunction类"""
    
    def __init__(self, warehouse_id: str):
        """
        初始化RagFunction
        
        Args:
            warehouse_id: 仓库ID
        """
        self.warehouse_id = warehouse_id
        self.mem0_client = None
        
        # 对应C#的Mem0Client初始化
        if hasattr(settings, 'mem0') and settings.mem0.enable_mem0:
            self.mem0_client = self._create_mem0_client()
    
    def _create_mem0_client(self):
        """创建Mem0客户端，对应C#的Mem0Client"""
        return httpx.AsyncClient(
            timeout=httpx.Timeout(600),  # 对应C#的TimeSpan.FromMinutes(600)
            headers={
                "User-Agent": "KoalaWiki/1.0",  # 对应C#的ProductInfoHeaderValue("KoalaWiki", "1.0")
                "Authorization": f"Bearer {settings.mem0.mem0_api_key}"
            }
        )
    
    @kernel_function(
        name="RagSearch",
        description="Search and retrieve relevant code or documentation content from the current repository index using specific keywords. "
                   "Parameters: "
                   "- query (str): Detailed description of the code or documentation you need. Specify whether you're looking for a function, class, method, or specific documentation. Be as specific as possible to improve search accuracy. "
                   "- limit (int): Number of search results to return. Default is 5. Increase for broader coverage or decrease for focused results. "
                   "- min_relevance (float): Minimum relevance threshold for vector search results, ranging from 0 to 1. Default is 0.3. Higher values (e.g., 0.7) return more precise matches, while lower values provide more varied results."
    )
    async def search_async(
        self,
        query: str,
        limit: int = 5,
        min_relevance: float = 0.3
    ) -> str:
        """
        搜索相关代码或文档内容，对应C#的SearchAsync方法
        
        Args:
            query: 详细描述您需要的代码或文档。指定您是在寻找函数、类、方法还是特定文档。尽可能具体以提高搜索准确性。
            limit: 返回的搜索结果数量。默认为5。增加以获得更广泛的覆盖范围，减少以获得更集中的结果。
            min_relevance: 向量搜索结果的最小相关性阈值，范围从0到1。默认为0.3。较高的值（例如0.7）返回更精确的匹配，而较低的值提供更多样化的结果。
            
        Returns:
            序列化的搜索结果
        """
        try:
            if not self.mem0_client:
                return json.dumps({
                    "error": "Mem0功能未启用",
                    "results": []
                })
            
            # 构建搜索请求，对应C#的SearchRequest
            search_request = {
                "query": query,
                "user_id": self.warehouse_id,
                "threshold": min_relevance,
                "limit": limit
            }
            
            # 调用Mem0 API，对应C#的_mem0Client.SearchAsync
            response = await self.mem0_client.post(
                f"{settings.mem0.mem0_endpoint}/search",
                json=search_request
            )
            
            if response.status_code == 200:
                result = response.json()
                # 对应C#的JsonSerializer.Serialize(result, JsonSerializerOptions.Web)
                return json.dumps(result, ensure_ascii=False)
            else:
                return json.dumps({
                    "error": f"Mem0搜索失败: {response.status_code}",
                    "results": []
                })
                
        except Exception as e:
            return json.dumps({
                "error": f"RAG搜索失败: {str(e)}",
                "results": []
            })
    
    async def close(self):
        """关闭客户端"""
        if self.mem0_client:
            await self.mem0_client.aclose() 