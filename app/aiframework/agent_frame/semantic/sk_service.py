import os
import asyncio
import json
import logging
from typing import Optional, Dict, Any, List, Union, AsyncGenerator
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, AzureChatCompletion
from openai import AsyncOpenAI
from semantic_kernel.functions import kernel_function
from app.config.settings import settings, APP_VERSION
from app.infrastructure.llms.chat_models.factory import llm_factory
from semantic_kernel.contents import ChatHistory
from semantic_kernel.functions import KernelArguments
from semantic_kernel.connectors.ai import PromptExecutionSettings, FunctionChoiceBehavior
from app.utils.common import get_project_base_directory


class SemanticKernelService:
    """Semantic Kernel服务类 - 提供AI内核的创建、配置和执行能力"""
    
    def __init__(self):
        # 获取模型配置
        model_provider, model_name = llm_factory.get_default_model()
        model_config = llm_factory.get_model_info_by_name(model_name)
        if not model_config:
            logging.error("没有可用的模型配置")
            raise Exception("没有可用的模型配置")
        
        self.model_provider = model_provider
        self.model_name = model_name
        self.api_key = model_config.get('provider_info').get('api_key')
        self.base_url = model_config.get('provider_info').get('base_url')
        self.model_params = model_config.get('model_info')

        # 创建kernel实例
        self.kernel = self._create_kernel()

    def _create_kernel(self) -> Kernel:
        """创建和配置AI内核实例"""
        try:
            # 创建内核
            kernel = Kernel()

            if self.model_provider.lower() in ["openai", "deepseek", "silicon", "siliconflow", "qwen", "anthropic"]:
                # 配置OpenAI服务
                async_client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
                chat_service = OpenAIChatCompletion(
                    service_id=f"chat_service_{self.model_name}",
                    ai_model_id=self.model_name,
                    api_key=self.api_key,
                    async_client=async_client
                )
                kernel.add_service(chat_service)
            elif self.model_provider.lower() == "azure":
                # 配置Azure OpenAI服务
                chat_service = AzureChatCompletion(
                    service_id=f"azure_chat_service_{self.model_name}",
                    deployment_name=self.model_name,
                    api_key=self.api_key,
                    base_url=self.base_url,
                    api_version="2024-02-15-preview",
                    default_headers={
                        "User-Agent": f"pando-codebase-service/{APP_VERSION}",
                        "Content-Type": "application/json"
                    },
                    instruction_role="system"
                )
                kernel.add_service(chat_service) 
            else:
                raise Exception(f"不支持的模型提供商: {self.model_provider}")
            
            logging.info(f"创建AI内核成功: {self.model_name}")
            return kernel
            
        except Exception as e:
            logging.error(f"创建AI内核失败: {e}")
            raise
    
    async def add_semantic_plugins(self, parent_path: str, plugins_name: str) -> bool:
        """
        添加Semantic Functions到Kernel
        自动判断：如果目录包含config.json则直接加载，否则扫描子目录
        
        Semantic Functions目录标准格式：
        plugin_directory/
        ├── config.json          # 函数配置文件
        └── skprompt.txt         # 提示词模板文件
        
        Args:
            parent_path: 相对于插件目录的上层目录
            plugin_name: 插件名称
        Returns:
            bool: 是否成功加载
        """
        try:
            if not self.kernel:
                raise ValueError("Kernel未初始化，请先调用initialize()方法")
            
            # 将相对路径转换为绝对路径
            plugins_path = os.path.join(get_project_base_directory(), parent_path)            
            if os.path.exists(plugins_path):
                # 从目录加载插件 - 使用KernelPlugin.from_directory
                from semantic_kernel.functions.kernel_plugin import KernelPlugin
                plugin = KernelPlugin.from_directory(plugins_name, plugins_path)
                self.kernel.add_plugin(plugin)
                logging.info(f"成功加载语义插件: {plugins_path}")
                return True
            else:
                logging.error(f"插件目录不存在: {plugins_path}")
                return False
        
        except Exception as e:
            logging.error(f"从目录加载插件失败: {e}")
            return False
    
    async def add_native_function(self, function_instance: Any, function_name: Optional[str] = None) -> bool:
        """
        添加Native Functions到Kernel
        
        Native Functions是使用@kernel_function装饰器标记的Python函数
        
        Args:
            function_instance: Function对象实例
            function_name: 函数名称（可选，如果不提供则使用类名）
            
        Returns:
            bool: 是否成功添加
        """
        try:
            if not self.kernel:
                raise ValueError("Kernel未初始化，请先调用initialize()方法")
                
            if function_name is None:
                function_name = function_instance.__class__.__name__
            
            self.kernel.add_plugin(function_instance, plugin_name=function_name)
            
            logging.info(f"成功添加函数到Kernel: {function_name}")
            return True
            
        except Exception as e:
            logging.error(f"添加函数到Kernel失败: {e}")
            return False
    
    
    async def invoke_prompt(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None, auto_calls: Optional[bool] = True, **kwargs) -> str:
        """
        执行Prompt调用（非流式）
        
        Args:
            messages: 用户消息
            system_prompt: 系统提示词（可选）
            auto_calls: 是否自动调用工具（默认True）
            **kwargs: 其他参数（temperature, max_tokens, history, arguments等）
            
        Returns:
            str: 完整响应内容
        """
        try:

            history = ChatHistory()

            if system_prompt:
                history.add_system_message(system_prompt)

            for message in messages:
                if message["role"] == "user":
                    history.add_user_message(message["content"])
                elif message["role"] == "assistant":
                    history.add_assistant_message(message["content"])

            # 执行调用
            if auto_calls:
                result = await self.kernel.invoke_prompt(
                    prompt="{{history}}",
                    arguments=KernelArguments(
                        settings=PromptExecutionSettings(
                            function_choice_behavior=FunctionChoiceBehavior.Auto()
                        ),
                        history=history,
                    ),
                    **kwargs
                )
            else:
                result = await self.kernel.invoke_prompt(
                    prompt="{{history}}",
                    arguments=KernelArguments(
                        history=history,
                    ),
                    **kwargs
                )

            # 提取内容
            if hasattr(result, 'content') and result.content:
                content = str(result.content)
            else:
                content = str(result)
            
            logging.info("Prompt调用执行完成")
            return content
            
        except Exception as e:
            logging.error(f"执行Prompt调用失败: {e}")
            raise
    

    async def invoke_prompt_stream(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None, auto_calls: Optional[bool] = True, **kwargs) -> AsyncGenerator[str, None]:
        """
        执行Prompt流式调用
        
        Args:
            messages: 用户消息
            system_prompt: 系统提示词（可选）
            auto_calls: 是否自动调用工具（默认True）
            **kwargs: 其他参数（temperature, max_tokens, history, arguments等）
            
        Yields:
            str: 流式响应内容
        """
        try:
            logging.info(f"开始执行Prompt流式调用: {len(messages)}条消息")
            
            history = ChatHistory()

            if system_prompt:
                history.add_system_message(system_prompt)

            for message in messages:
                if message["role"] == "user":
                    history.add_user_message(message["content"])
                elif message["role"] == "assistant":
                    history.add_assistant_message(message["content"])

            # 执行流式调用
            if auto_calls:
                async for chunk in self.kernel.invoke_prompt_stream(
                    prompt="{{history}}",
                    arguments=KernelArguments(
                        settings=PromptExecutionSettings(
                            function_choice_behavior=FunctionChoiceBehavior.Auto()
                        ),
                        history=history,
                    ),
                    **kwargs
                ):
                    if hasattr(chunk, "content") and chunk.content:
                        yield str(chunk.content)
                    elif isinstance(chunk, list):
                        for m in chunk:
                            if hasattr(m, "content") and m.content:
                                yield str(m.content)
                    else:
                        yield str(chunk)
            else:
                async for chunk in self.kernel.invoke_prompt_stream(
                    prompt="{{history}}",
                    arguments=KernelArguments(
                        history=history,
                    ),
                    **kwargs
                ):
                    if hasattr(chunk, "content") and chunk.content:
                        yield str(chunk.content)
                    elif isinstance(chunk, list):
                        for m in chunk:
                            if hasattr(m, "content") and m.content:
                                yield str(m.content)
                    else:
                        yield str(chunk)
            
            logging.info("Prompt流式调用执行完成")
            
        except Exception as e:
            logging.error(f"执行Prompt流式调用失败: {e}")
            raise
    
    
    async def invoke_by_plugin(self, plugins_name: str, plugin_function_name: str, **kwargs) -> str:
        """
        执行指定插件的函数
        
        Args:
            plugins_name: 插件集名称
            plugin_function_name: 插件函数名称
            **kwargs: 函数参数
            
        Returns:
            str: 执行结果
        """
        try:
            logging.info(f"开始执行插件函数: {plugins_name}.{plugin_function_name}")

            generate_fn = self.kernel.get_plugin(plugins_name).get(plugin_function_name)
            if generate_fn is not None:
                result = await self.kernel.invoke(
                    function=generate_fn,
                    arguments=KernelArguments(
                        settings=PromptExecutionSettings(
                            function_choice_behavior=FunctionChoiceBehavior.Auto()
                        ),
                        **kwargs
                    )
                )
                generated = str(result) if result else None
            else:
                logging.error(f"未发现语义插件 {plugins_name}.{plugin_function_name}，跳过AI生成。")
                generated = None
            
            logging.info(f"插件函数执行完成: {plugins_name}.{plugin_function_name}")
            return generated
            
        except Exception as e:
            logging.error(f"执行插件函数 {plugins_name}.{plugin_function_name} 失败: {e}")
            raise
    
    async def invoke_by_plugin_stream(self, plugins_name: str, plugin_function_name: str, **kwargs) -> AsyncGenerator[str, None]:
        """
        执行指定插件的函数（流式）
        
        Args:
            plugins_name: 插件集名称
            plugin_function_name: 插件函数名称
            **kwargs: 函数参数
            
        Yields:
            str: 流式响应内容
        """
        try:
            logging.info(f"开始执行插件函数流式调用: {plugins_name}.{plugin_function_name}")
            
            generate_fn = self.kernel.get_plugin(plugins_name).get(plugin_function_name)
            if generate_fn is not None:
                # 执行流式调用
                async for chunk in self.kernel.invoke_stream(
                        function=generate_fn,
                        arguments=KernelArguments(
                            settings=PromptExecutionSettings(
                                function_choice_behavior=FunctionChoiceBehavior.Auto()
                            ),
                            **kwargs
                        )
                ):
                    if hasattr(chunk, "content") and chunk.content:
                        yield str(chunk.content)
                    elif isinstance(chunk, list):
                        for m in chunk:
                            if hasattr(m, "content") and m.content:
                                yield str(m.content)
                    else:
                        yield str(chunk)
            else:
                logging.error(f"未发现语义插件 {plugins_name}.{plugin_function_name}，跳过AI生成。")
                return
            
            logging.info(f"插件函数流式调用执行完成: {plugins_name}.{plugin_function_name}")
            
        except Exception as e:
            logging.error(f"执行插件函数流式调用 {plugins_name}.{plugin_function_name} 失败: {e}")
            raise
    
    
    

