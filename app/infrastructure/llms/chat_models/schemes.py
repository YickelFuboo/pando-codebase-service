from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel


class ChatResponse(BaseModel):   
    """聊天响应格式"""
    success: bool = True         # 返回申请情况下成功与否
    content: str                 # 返回内容，包含成功情况下正确内容和失败情况下错误信息


class ToolInfo(BaseModel):
    """工具调用信息"""
    id: str
    name: str
    args: Dict[str, Any]


class AskToolResponse(BaseModel):
    """工具调用响应格式"""
    success: bool = True         # 返回申请情况下成功与否
    content: Optional[str] = None                 # 返回内容，包含成功情况下思考内容和失败情况下错误信息
    tool_calls: Optional[List[ToolInfo]] = None  # 支持多个工具调用


class LLMInfo(BaseModel):
    """LLM信息模型"""
    name: str
    type: str
    description: str
    max_tokens: int
    api_style: str

