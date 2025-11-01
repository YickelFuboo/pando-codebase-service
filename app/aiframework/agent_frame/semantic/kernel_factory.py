import logging
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, AzureChatCompletion
from openai import AsyncOpenAI
from app.config.settings import APP_VERSION
from app.infrastructure.llms.chat_models.factory import llm_factory


class KernelFactory:
    """AI内核工厂类"""

    @staticmethod
    async def get_kernel() -> Kernel:
        """创建和配置AI内核实例"""
        try:
            # 获取模型配置
            model_provider, model_name = llm_factory.get_default_model()
            model_config = llm_factory.get_model_info_by_name(model_name)
            if not model_config:
                logging.error("没有可用的模型配置")
                raise Exception("没有可用的模型配置")
            base_url = model_config.get('provider_info').get('base_url')
            api_key = model_config.get('provider_info').get('api_key')

            logging.info(f"模型配置: provider:{model_provider}, model:{model_name}, base_url:{base_url}, api_key:{api_key}")
            
            # 创建内核
            kernel = Kernel()
            
            # 配置AI模型服务
            if model_provider.lower() in ["openai", "deepseek", "silicon", "siliconflow", "qwen", "anthropic"]:
                # 配置OpenAI服务
                async_client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=base_url
                )
                chat_service = OpenAIChatCompletion(
                    service_id=f"chat_service_{model_name}",
                    ai_model_id=model_name,
                    api_key=api_key,
                    async_client=async_client
                )
                kernel.add_service(chat_service)
            elif model_provider.lower() == "azure":
                # 配置Azure OpenAI服务
                chat_service = AzureChatCompletion(
                    service_id=f"azure_chat_service_{model_name}",
                    deployment_name=model_name,
                    api_key=api_key,
                    base_url=base_url,
                    api_version="2024-02-15-preview",
                    default_headers={
                        "User-Agent": f"pando-codebase-service/{APP_VERSION}",
                        "Content-Type": "application/json"
                    },
                    instruction_role="system"
                )
                kernel.add_service(chat_service) 
            else:
                raise Exception(f"不支持的模型提供商: {model_provider}")
            
            logging.info(f"创建AI内核成功: {model_config.get('model_name')}")            
            return kernel
            
        except Exception as e:
            logging.error(f"创建AI内核失败: {e}")
            raise
    

