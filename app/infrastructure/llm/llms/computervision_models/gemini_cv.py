import base64
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from io import BytesIO
from PIL.Image import open as pil_open
from transformers import GenerationConfig
import asyncio
from google.generativeai import GenerativeModel, client
from app.infrastructure.llm.llms.computervision_models.base.base import BaseComputerVision, MAX_RETRY_ATTEMPTS
from app.infrastructure.llm.prompts.prompt_template_load import get_prompt_template_with_params


class GeminiCV(BaseComputerVision):
    """Google Gemini 计算机视觉模型实现"""

    def __init__(self, api_key: str, model_name: str = "gemini-1.0-pro-vision-latest", 
                 base_url: Optional[str] = None, language: str = "Chinese"):
        """
        初始化Google Gemini计算机视觉模型
        
        Args:
            api_key (str): Google API密钥
            model_name (str): 模型名称，默认为gemini-1.0-pro-vision-latest
            base_url (Optional[str]): API基础URL
            lang (str): 语言设置
            **kwargs: 额外参数
        """
        super().__init__(api_key, model_name, base_url, language)
        
        client.configure(api_key=api_key)
        _client = client.get_default_generative_client()
        self.model = GenerativeModel(model_name=self.model_name)
        self.model._client = _client

    async def describe(self, image: Union[str, bytes, BytesIO, Any]) -> Tuple[str, int]:
        """
        描述图像内容
        
        Args:
            image: 图像对象或路径
            
        Returns:
            Tuple[str, int]: (图像描述文本, token数量)
        """
        message = self._create_describe_message("")
        b64 = self._image2base64(image)
        img = open(BytesIO(base64.b64decode(b64)))
        input_content = [message[0]["content"][1]["text"], img]
        
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                response = await asyncio.to_thread(
                    lambda: self.model.generate_content(input_content)
                )
                return response.text, response.usage_metadata.total_token_count
                
            except Exception as e:
                if attempt < MAX_RETRY_ATTEMPTS - 1 and self._should_retry(e):
                    delay = self._get_delay(attempt)
                    logging.warning(f"图像描述失败，重试 (尝试 {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}. 等待 {delay:.2f}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logging.error(f"图像描述最终失败: {e}")
                    return f"**ERROR**: {str(e)}", 0

    async def describe_with_prompt(self, image: Union[str, bytes, BytesIO, Any], 
                           prompt: Optional[str] = None) -> Tuple[str, int]:
        """
        使用自定义提示词描述图像
        
        Args:
            image: 图像对象或路径
            prompt (Optional[str]): 自定义提示词
            
        Returns:
            Tuple[str, int]: (图像描述文本, token数量)
        """
        b64 = self._image2base64(image)
        vision_prompt = prompt if prompt else get_prompt_template_with_params("cv/computer_vision_describe_prompt.md", {"page": None})
        
        img = open(BytesIO(base64.b64decode(b64)))
        input_content = [vision_prompt, img]
        
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                response = await asyncio.to_thread(
                    lambda: self.model.generate_content(input_content)
                )
                return response.text, response.usage_metadata.total_token_count
                
            except Exception as e:
                if attempt < MAX_RETRY_ATTEMPTS - 1 and self._should_retry(e):
                    delay = self._get_delay(attempt)
                    logging.warning(f"自定义提示词图像描述失败，重试 (尝试 {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}. 等待 {delay:.2f}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logging.error(f"自定义提示词图像描述最终失败: {e}")
                    return f"**ERROR**: {str(e)}", 0

    async def chat(self, system: str, history: List[Dict[str, Any]], 
             gen_conf: Dict[str, Any], image: str = "") -> Tuple[str, int]:
        """
        执行视觉聊天对话
        
        Args:
            system (str): 系统提示词
            history (List[Dict[str, Any]]): 对话历史
            gen_conf (Dict[str, Any]): 生成配置
            image (str): 图像内容（base64编码）
            
        Returns:
            Tuple[str, int]: (回答内容, token数量)
        """
        if system:
            history[-1]["content"] = system + history[-1]["content"] + "user query: " + history[-1]["content"]
        
        # 转换消息格式为Gemini格式
        for his in history:
            if his["role"] == "assistant":
                his["role"] = "model"
                his["parts"] = [his["content"]]
                his.pop("content")
            if his["role"] == "user":
                his["parts"] = [his["content"]]
                his.pop("content")
        
        # 添加图像到最后一个用户消息
        history[-1]["parts"].append("data:image/jpeg;base64," + image)

        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                response = await asyncio.to_thread(
                    lambda: self.model.generate_content(
                        history, 
                        generation_config=GenerationConfig(
                            temperature=gen_conf.get("temperature", 0.3), 
                            top_p=gen_conf.get("top_p", 0.7)
                        )
                    )
                )

                ans = response.text
                return ans, response.usage_metadata.total_token_count
                
            except Exception as e:
                if attempt < MAX_RETRY_ATTEMPTS - 1 and self._should_retry(e):
                    delay = self._get_delay(attempt)
                    logging.warning(f"视觉聊天失败，重试 (尝试 {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}. 等待 {delay:.2f}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logging.error(f"视觉聊天最终失败: {e}")
                    return f"**ERROR**: {str(e)}", 0

    async def chat_stream(self, system: str, history: List[Dict[str, Any]], 
                     gen_conf: Dict[str, Any], image: str = "") -> Tuple[str, int]:
        """
        执行流式视觉聊天对话
        
        Args:
            system (str): 系统提示词
            history (List[Dict[str, Any]]): 对话历史
            gen_conf (Dict[str, Any]): 生成配置
            image (str): 图像内容（base64编码）
            
        Yields:
            Tuple[str, int]: (流式响应内容, token数量)
        """
        if system:
            history[-1]["content"] = system + history[-1]["content"] + "user query: " + history[-1]["content"]

        # 转换消息格式为Gemini格式
        for his in history:
            if his["role"] == "assistant":
                his["role"] = "model"
                his["parts"] = [his["content"]]
                his.pop("content")
            if his["role"] == "user":
                his["parts"] = [his["content"]]
                his.pop("content")
        
        # 添加图像到最后一个用户消息
        history[-1]["parts"].append("data:image/jpeg;base64," + image)

        ans = ""
        
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                response = await asyncio.to_thread(
                    lambda: self.model.generate_content(
                        history,
                        generation_config=GenerationConfig(
                            temperature=gen_conf.get("temperature", 0.3), 
                            top_p=gen_conf.get("top_p", 0.7)
                        ),
                        stream=True,
                    )
                )

                for resp in response:
                    if not resp.text:
                        continue
                    ans += resp.text
                    token_count = resp.usage_metadata.total_token_count if hasattr(resp, 'usage_metadata') else 0
                    yield ans, token_count
                
                # 如果成功完成流式响应，跳出重试循环
                return
                
            except Exception as e:
                if attempt < MAX_RETRY_ATTEMPTS - 1 and self._should_retry(e):
                    delay = self._get_delay(attempt)
                    logging.warning(f"流式视觉聊天失败，重试 (尝试 {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}. 等待 {delay:.2f}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logging.error(f"流式视觉聊天最终失败: {e}")
                    yield ans + "\n**ERROR**: " + str(e), 0
                    return