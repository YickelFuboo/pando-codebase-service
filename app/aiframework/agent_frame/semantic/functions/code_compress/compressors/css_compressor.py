"""
CSS代码压缩器
专门用于压缩CSS代码，保留重要的结构和注释
"""

import re
from .base_compressor import BaseCompressor


class CssCompressor(BaseCompressor):
    """CSS代码压缩器类"""
    
    def compress(self, content: str) -> str:
        """
        压缩CSS代码内容
        
        Args:
            content: 原始CSS代码内容
            
        Returns:
            压缩后的CSS代码内容
        """
        lines = content.split('\n')
        result = []
        
        for line in lines:
            trimmed_line = line.strip()
            
            if not trimmed_line:
                continue
            
            # 保留注释
            if trimmed_line.startswith('/*') or trimmed_line.startswith('*'):
                result.append(line)
                continue
            
            # 保留重要结构
            if self._is_important_css_line(trimmed_line):
                result.append(self._normalize_css_line(line))
                continue
        
        return '\n'.join(result)
    
    def _is_important_css_line(self, line: str) -> bool:
        """
        判断是否为重要的CSS代码行
        
        Args:
            line: 代码行
            
        Returns:
            如果是重要的CSS行返回 True
        """
        important_patterns = [
            r'^\s*@\w+',                          # @规则
            r'^\s*[.#]?\w+\s*\{',                 # 选择器
            r'^\s*\}',                            # 结束大括号
            r'^\s*/\*',                           # 注释开始
            r'^\s*\*/',                           # 注释结束
        ]
        
        return any(re.match(pattern, line) for pattern in important_patterns)
    
    def _normalize_css_line(self, line: str) -> str:
        """
        规范化CSS代码行
        
        Args:
            line: 原始代码行
            
        Returns:
            规范化后的代码行
        """
        working = line.rstrip()
        
        # 处理选择器，移除属性
        if re.match(r'^\s*[.#]?\w+\s*\{', working):
            match = re.match(r'^(\s*[.#]?\w+\s*\{)', working)
            if match:
                return match.group(1) + " }"
        
        # 处理@规则
        if re.match(r'^\s*@\w+', working):
            match = re.match(r'^(\s*@\w+)', working)
            if match:
                return match.group(1) + " { }"
        
        return working 