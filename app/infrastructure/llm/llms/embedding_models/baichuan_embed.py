from app.infrastructure.llm.llms.embedding_models.openai_embed import OpenAIEmbed


class BaiChuanEmbed(OpenAIEmbed):
    def __init__(self, api_key: str, model_name: str = "Baichuan-Text-Embedding", base_url: str = "https://api.baichuan-ai.com/v1", **kwargs):
        """
        初始化百川嵌入模型
        
        Args:
            api_key (str): API密钥
            model_name (str): 模型名称，默认为Baichuan-Text-Embedding
            base_url (str): API基础URL，默认为百川官方URL
        """
        super().__init__(api_key, model_name, base_url, **kwargs)