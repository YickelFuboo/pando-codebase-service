"""
PHP代码压缩器
专门用于压缩PHP代码，保留重要的结构和注释
"""

import re
from .base_compressor import BaseCompressor


class PhpCompressor(BaseCompressor):
    """PHP代码压缩器类"""
    
    def compress(self, content: str) -> str:
        """
        压缩PHP代码内容
        
        Args:
            content: 原始PHP代码内容
            
        Returns:
            压缩后的PHP代码内容
        """
        lines = content.split('\n')
        result = []
        
        for line in lines:
            trimmed_line = line.strip()
            
            if not trimmed_line:
                continue
            
            # 保留注释
            if (trimmed_line.startswith('//') or trimmed_line.startswith('/*') or 
                trimmed_line.startswith('*') or trimmed_line.startswith('#')):
                result.append(line)
                continue
            
            # 保留重要结构
            if self._is_important_php_line(trimmed_line):
                result.append(self._normalize_php_line(line))
                continue
        
        return '\n'.join(result)
    
    def _is_important_php_line(self, line: str) -> bool:
        """
        判断是否为重要的PHP代码行
        
        Args:
            line: 代码行
            
        Returns:
            如果是重要的PHP行返回 True
        """
        important_patterns = [
            r'^\s*<\?php',                        # PHP开始标签
            r'^\s*\?>',                           # PHP结束标签
            r'^\s*(namespace|use)\s+',            # namespace 和 use 语句
            r'^\s*(class|interface|trait|abstract|final)\s+',  # 类、接口、特性定义
            r'^\s*(public|private|protected|static|const|var)\s+',  # 修饰符
            r'^\s*function\s+\w+\s*\(',          # 函数定义
            r'^\s*\{|\}',                         # 大括号
            r'^\s*(if|else|for|while|foreach|switch|case|default|try|catch|finally|throw|return|break|continue)\s',  # 控制语句
        ]
        
        return any(re.match(pattern, line) for pattern in important_patterns)
    
    def _normalize_php_line(self, line: str) -> str:
        """
        规范化PHP代码行
        
        Args:
            line: 原始代码行
            
        Returns:
            规范化后的代码行
        """
        working = line.rstrip()
        
        # 处理类定义
        if re.match(r'^\s*(class|interface|trait)\s+\w+', working):
            match = re.match(r'^(\s*(?:class|interface|trait)\s+\w+)', working)
            if match:
                return match.group(1) + " { }"
        
        # 处理函数定义
        if re.match(r'^\s*function\s+\w+\s*\(', working):
            # 找到函数签名的结束位置
            paren_count = 0
            for i, char in enumerate(working):
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                    if paren_count == 0:
                        return working[:i+1] + " { }"
        
        return working 