"""
Ruby代码压缩器
专门用于压缩Ruby代码，保留重要的结构和注释
"""

import re
from .base_compressor import BaseCompressor


class RubyCompressor(BaseCompressor):
    """Ruby代码压缩器类"""
    
    def compress(self, content: str) -> str:
        """
        压缩Ruby代码内容
        
        Args:
            content: 原始Ruby代码内容
            
        Returns:
            压缩后的Ruby代码内容
        """
        lines = content.split('\n')
        result = []
        
        for line in lines:
            trimmed_line = line.strip()
            
            if not trimmed_line:
                continue
            
            # 保留注释
            if trimmed_line.startswith('#') or trimmed_line.startswith('=begin'):
                result.append(line)
                continue
            
            # 保留重要结构
            if self._is_important_ruby_line(trimmed_line):
                result.append(self._normalize_ruby_line(line))
                continue
        
        return '\n'.join(result)
    
    def _is_important_ruby_line(self, line: str) -> bool:
        """
        判断是否为重要的Ruby代码行
        
        Args:
            line: 代码行
            
        Returns:
            如果是重要的Ruby行返回 True
        """
        important_patterns = [
            r'^\s*(require|require_relative|load|include|extend)\s+',  # 加载和包含语句
            r'^\s*(class|module)\s+',              # 类和模块定义
            r'^\s*(def|alias|undef)\s+',           # 方法定义
            r'^\s*(attr_accessor|attr_reader|attr_writer)\s+',  # 属性定义
            r'^\s*(public|private|protected)\s*$', # 访问修饰符
            r'^\s*(if|unless|elsif|else|case|when|for|while|until|begin|rescue|ensure|retry|return|break|next|redo)\s',  # 控制语句
            r'^\s*end\s*$',                        # end 关键字
        ]
        
        return any(re.match(pattern, line) for pattern in important_patterns)
    
    def _normalize_ruby_line(self, line: str) -> str:
        """
        规范化Ruby代码行
        
        Args:
            line: 原始代码行
            
        Returns:
            规范化后的代码行
        """
        working = line.rstrip()
        
        # 处理类定义
        if re.match(r'^\s*(class|module)\s+\w+', working):
            match = re.match(r'^(\s*(?:class|module)\s+\w+)', working)
            if match:
                return match.group(1)
        
        # 处理方法定义
        if re.match(r'^\s*def\s+\w+', working):
            match = re.match(r'^(\s*def\s+\w+)', working)
            if match:
                return match.group(1)
        
        return working 