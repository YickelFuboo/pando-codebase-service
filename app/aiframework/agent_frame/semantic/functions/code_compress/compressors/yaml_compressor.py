"""
YAML代码压缩器
使用结构化解析进行精确的YAML代码压缩
"""

import yaml
from typing import Any, Dict, List, Union
from .base_compressor import BaseCompressor


class YamlCompressor(BaseCompressor):
    """YAML代码压缩器类 - 使用结构化解析"""
    
    def compress(self, content: str) -> str:
        """
        压缩YAML代码内容
        
        Args:
            content: 原始YAML代码内容
            
        Returns:
            压缩后的YAML代码内容
        """
        try:
            # 使用结构化解析
            return self._compress_with_parser(content)
        except yaml.YAMLError as e:
            # 如果解析失败，返回原始内容的非空行，作为降级方案
            print(f"YAML解析失败，使用降级方案: {e}")
            return self._compress_with_fallback(content)
    
    def _compress_with_parser(self, content: str) -> str:
        """使用结构化解析压缩"""
        # 解析YAML
        data = yaml.safe_load(content)
        
        # 压缩数据
        compressed_data = self._strip_values(data)
        
        # 格式化输出
        return yaml.dump(compressed_data, default_flow_style=False, allow_unicode=True)
    
    def _compress_with_fallback(self, content: str) -> str:
        """降级方案：返回非空行"""
        lines = content.split('\n')
        result = []
        
        for line in lines:
            trimmed_line = line.strip()
            if trimmed_line:
                result.append(line)
        
        return '\n'.join(result)
    
    def _strip_values(self, data: Any) -> Any:
        """
        移除YAML值，保留结构
        
        Args:
            data: YAML数据
            
        Returns:
            压缩后的YAML数据
        """
        if isinstance(data, dict):
            # 处理映射
            new_obj = {}
            for key, value in data.items():
                new_obj[key] = self._strip_values(value)
            return new_obj
        
        elif isinstance(data, list):
            # 处理序列
            new_array = []
            if data:
                # 只保留第一个元素的结构作为示例
                first_element = data[0]
                if first_element is not None:
                    new_array.append(self._strip_values(first_element))
            return new_array
        
        elif isinstance(data, (str, int, float, bool)):
            # 将所有原始值替换为默认值
            return None
        
        else:
            return data 