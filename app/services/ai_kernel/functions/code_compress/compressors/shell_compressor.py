"""
Shell代码压缩器
专门用于压缩Shell脚本代码，保留重要的结构和注释
"""

import re
from .base_compressor import BaseCompressor


class ShellCompressor(BaseCompressor):
    """Shell代码压缩器类"""
    
    def compress(self, content: str) -> str:
        """
        压缩Shell代码内容
        
        Args:
            content: 原始Shell代码内容
            
        Returns:
            压缩后的Shell代码内容
        """
        lines = content.split('\n')
        result = []
        
        for line in lines:
            trimmed_line = line.strip()
            
            if not trimmed_line:
                continue
            
            # 保留注释
            if trimmed_line.startswith('#'):
                result.append(line)
                continue
            
            # 保留重要结构
            if self._is_important_shell_line(trimmed_line):
                result.append(self._normalize_shell_line(line))
                continue
        
        return '\n'.join(result)
    
    def _is_important_shell_line(self, line: str) -> bool:
        """
        判断是否为重要的Shell代码行
        
        Args:
            line: 代码行
            
        Returns:
            如果是重要的Shell行返回 True
        """
        important_patterns = [
            r'^\s*#!/',                           # shebang
            r'^\s*(source|\.)\s+',                # source 命令
            r'^\s*(export|declare|readonly|local)\s+',  # 变量声明
            r'^\s*(function\s+\w+|function\s*\(\s*\)|\(\s*\)\s*\{)',  # 函数定义
            r'^\s*(if|elif|else|fi|for|while|until|do|done|case|esac|select)\s',  # 控制语句
            r'^\s*\{|\}',                         # 大括号
        ]
        
        return any(re.match(pattern, line) for pattern in important_patterns)
    
    def _normalize_shell_line(self, line: str) -> str:
        """
        规范化Shell代码行
        
        Args:
            line: 原始代码行
            
        Returns:
            规范化后的代码行
        """
        working = line.rstrip()
        
        # 处理函数定义
        if re.match(r'^\s*function\s+\w+', working):
            match = re.match(r'^(\s*function\s+\w+)', working)
            if match:
                return match.group(1) + " { }"
        
        # 处理匿名函数
        if re.match(r'^\s*\(\s*\)\s*\{', working):
            return "() { }"
        
        return working 