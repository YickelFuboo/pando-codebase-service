"""
基础压缩器接口
定义所有压缩器必须实现的方法
"""

from abc import ABC, abstractmethod


class BaseCompressor(ABC):
    """代码压缩器基础接口"""
    
    @abstractmethod
    def compress(self, content: str) -> str:
        """
        压缩代码内容
        
        Args:
            content: 原始代码内容
            
        Returns:
            压缩后的代码内容
        """
        pass 