"""
XML代码压缩器
使用结构化解析进行精确的XML代码压缩
"""

import xml.etree.ElementTree as ET
from typing import Optional
from .base_compressor import BaseCompressor


class XmlCompressor(BaseCompressor):
    """XML代码压缩器类 - 使用结构化解析"""
    
    def compress(self, content: str) -> str:
        """
        压缩XML代码内容
        
        Args:
            content: 原始XML代码内容
            
        Returns:
            压缩后的XML代码内容
        """
        try:
            # 使用结构化解析
            return self._compress_with_parser(content)
        except ET.ParseError as e:
            # 如果解析失败，返回原始内容的非空行，作为降级方案
            print(f"XML解析失败，使用降级方案: {e}")
            return self._compress_with_fallback(content)
    
    def _compress_with_parser(self, content: str) -> str:
        """使用结构化解析压缩"""
        # 解析XML
        root = ET.fromstring(content)
        
        # 压缩XML
        self._strip_content(root)
        
        # 格式化输出
        return self._to_string(root)
    
    def _compress_with_fallback(self, content: str) -> str:
        """降级方案：返回非空行"""
        lines = content.split('\n')
        result = []
        
        for line in lines:
            trimmed_line = line.strip()
            if trimmed_line:
                result.append(line)
        
        return '\n'.join(result)
    
    def _strip_content(self, element: ET.Element) -> None:
        """
        移除XML内容，保留结构
        
        Args:
            element: XML元素
        """
        # 移除文本内容
        if element.text and element.text.strip():
            element.text = None
        
        # 移除尾随文本
        if element.tail and element.tail.strip():
            element.tail = None
        
        # 递归处理子元素
        for child in element:
            self._strip_content(child)
    
    def _to_string(self, element: ET.Element) -> str:
        """
        将XML元素转换为字符串
        
        Args:
            element: XML元素
            
        Returns:
            格式化的XML字符串
        """
        # 创建临时根元素以包含XML声明
        root = ET.Element("root")
        root.append(element)
        
        # 转换为字符串
        xml_str = ET.tostring(root, encoding='unicode', method='xml')
        
        # 移除临时根元素标签
        xml_str = xml_str.replace('<root>', '').replace('</root>', '')
        
        # 添加XML声明
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str 