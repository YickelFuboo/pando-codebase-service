"""
Go代码压缩器
专门用于压缩Go代码，保留重要的结构和注释
"""

import re
from .base_compressor import BaseCompressor


class GoCompressor(BaseCompressor):
    """Go代码压缩器类"""
    
    def compress(self, content: str) -> str:
        """
        压缩Go代码内容
        
        Args:
            content: 原始Go代码内容
            
        Returns:
            压缩后的Go代码内容
        """
        lines = content.split('\n')
        result = []
        
        for line in lines:
            trimmed_line = line.strip()
            
            if not trimmed_line:
                continue
            
            # 保留注释
            if trimmed_line.startswith('//') or trimmed_line.startswith('/*'):
                result.append(line)
                continue
            
            # 保留重要结构
            if self._is_important_go_line(trimmed_line):
                result.append(self._normalize_go_line(line))
                continue
        
        return '\n'.join(result)
    
    def _is_important_go_line(self, line: str) -> bool:
        """
        判断是否为重要的Go代码行
        
        Args:
            line: 代码行
            
        Returns:
            如果是重要的Go行返回 True
        """
        important_patterns = [
            r'^\s*(package|import)\s+',           # package 和 import 语句
            r'^\s*(type|func|var|const)\s+',      # 类型、函数、变量、常量定义
            r'^\s*(interface|struct)\s+',          # 接口和结构体定义
            r'^\s*(if|else|for|switch|case|default|select|go|defer|return|break|continue|fallthrough)\s',  # 控制语句
            r'^\s*\{|\}',                         # 大括号
        ]
        
        return any(re.match(pattern, line) for pattern in important_patterns)
    
    def _normalize_go_line(self, line: str) -> str:
        """
        规范化Go代码行
        
        Args:
            line: 原始代码行
            
        Returns:
            规范化后的代码行
        """
        working = line.rstrip()
        
        # 处理函数定义
        if re.match(r'^\s*func\s+\w+\s*\(', working):
            # 找到函数签名的结束位置
            paren_count = 0
            for i, char in enumerate(working):
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                    if paren_count == 0:
                        return working[:i+1] + " { }"
        
        # 处理类型定义
        if re.match(r'^\s*type\s+\w+', working):
            match = re.match(r'^(\s*type\s+\w+)', working)
            if match:
                return match.group(1) + " { }"
        
        return working 