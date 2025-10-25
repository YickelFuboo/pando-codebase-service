"""
HTML代码压缩器
使用结构化解析进行精确的HTML代码压缩
"""

from bs4 import BeautifulSoup
from typing import Optional
from .base_compressor import BaseCompressor


class HtmlCompressor(BaseCompressor):
    """HTML代码压缩器类 - 使用结构化解析"""
    
    def compress(self, content: str) -> str:
        """
        压缩HTML代码内容
        
        Args:
            content: 原始HTML代码内容
            
        Returns:
            压缩后的HTML代码内容
        """
        try:
            # 使用结构化解析
            return self._compress_with_parser(content)
        except Exception as e:
            # 如果解析失败，返回原始内容的非空行，作为降级方案
            print(f"HTML解析失败，使用降级方案: {e}")
            return self._compress_with_fallback(content)
    
    def _compress_with_parser(self, content: str) -> str:
        """使用结构化解析压缩"""
        # 解析HTML
        soup = BeautifulSoup(content, 'html.parser')
        
        # 压缩HTML
        self._strip_content(soup)
        
        # 格式化输出
        return str(soup)
    
    def _compress_with_fallback(self, content: str) -> str:
        """降级方案：返回非空行"""
        lines = content.split('\n')
        result = []
        
        for line in lines:
            trimmed_line = line.strip()
            if trimmed_line:
                result.append(line)
        
        return '\n'.join(result)
    
    def _strip_content(self, element) -> None:
        """
        移除HTML内容，保留结构
        
        Args:
            element: HTML元素
        """
        if element is None:
            return
        
        # 收集要移除的文本节点和注释节点
        nodes_to_remove = []
        for child in element.children:
            if child.name is None:  # 文本节点
                if child.string and child.string.strip():
                    nodes_to_remove.append(child)
            elif child.name == 'comment':  # 注释节点
                nodes_to_remove.append(child)
        
        # 移除它们
        for node in nodes_to_remove:
            node.extract()
        
        # 对所有剩余的元素子节点进行递归处理
        for child in element.find_all(recursive=False):
            self._strip_content(child) 