import os
import asyncio
import json
import logging
from typing import Optional
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, AzureChatCompletion
from openai import AsyncOpenAI
from semantic_kernel.functions import kernel_function
from app.config.settings import settings, APP_VERSION
from app.infrastructure.llms.chat_models.factory import llm_factory
from .functions.file_function import FileFunction


class KernelFactory:
    """AI内核工厂类"""
    
    def __init__(self):
        self.kernel_cache = {}
    
    
    async def get_kernel(self, git_local_path: str,  
                        is_code_analysis: bool = True) -> Kernel:
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
            
            # 创建缓存键
            cache_key = f"{base_url}_{api_key}_{git_local_path}_{model_name}_{is_code_analysis}"
            
            # 检查缓存
            if cache_key in self.kernel_cache:
                return self.kernel_cache[cache_key]
            
            # 创建内核
            kernel = Kernel()
            
            # 配置AI模型服务
            await self._configure_ai_service_with_model(kernel, model_provider, model_name, base_url, api_key)
            
            # 配置代码分析插件
            if False and is_code_analysis:
                # 从目录加载语义插件（config.json + skprompt.txt）
                plugins_path = os.path.join(os.path.dirname(__file__), "plugins")
                if os.path.exists(plugins_path):
                    try:
                        # 从目录加载插件 - 使用KernelPlugin.from_directory
                        from semantic_kernel.functions.kernel_plugin import KernelPlugin
                        plugin = KernelPlugin.from_directory( "code_analysis", plugins_path)
                        kernel.add_plugin(plugin)                      
                        logging.info(f"成功加载语义插件: {plugins_path}")
                    except Exception as e:
                        logging.error(f"加载语义插件失败: {e}")
                else:
                    logging.warning(f"代码分析插件目录不存在: {plugins_path}")
            
            # 配置文件操作插件
            try:
                file_function = FileFunction(git_local_path)
                # 直接传入类实例，add_plugin 会自动处理所有带有 @kernel_function 装饰器的方法
                kernel.add_plugin(file_function, plugin_name="FileFunction")
                logging.info("加载文件操作插件")
            except Exception as e:
                logging.error(f"配置文件操作插件失败: {e}")
        
            
            # 缓存内核
            self.kernel_cache[cache_key] = kernel
            
            logging.info(f"创建AI内核成功: {model_config.get('model_name')}")
            return kernel
            
        except Exception as e:
            logging.error(f"创建AI内核失败: {e}")
            raise
    
    async def _configure_ai_service_with_model(self, kernel: Kernel, model_provider: str, model_name: str, base_url: str, api_key: str):
        """使用模型配置配置AI服务"""
        try:
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
                
        except Exception as e:
            logging.error(f"配置AI服务失败: {e}")
            raise