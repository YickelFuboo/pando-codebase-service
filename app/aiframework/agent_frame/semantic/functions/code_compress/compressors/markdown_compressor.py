"""
Markdown代码压缩器
专门用于压缩Markdown代码，保留重要的结构和注释
"""

import re
from .base_compressor import BaseCompressor


class MarkdownCompressor(BaseCompressor):
    """Markdown代码压缩器类"""
    
    def compress(self, content: str) -> str:
        """
        压缩Markdown代码内容
        
        Args:
            content: 原始Markdown代码内容
            
        Returns:
            压缩后的Markdown代码内容
        """
        lines = content.split('\n')
        result = []
        
        for line in lines:
            trimmed_line = line.strip()
            
            if not trimmed_line:
                continue
            
            # 保留重要结构
            if self._is_important_markdown_line(trimmed_line):
                result.append(self._normalize_markdown_line(line))
                continue
        
        return '\n'.join(result)
    
    def _is_important_markdown_line(self, line: str) -> bool:
        """
        判断是否为重要的Markdown代码行
        
        Args:
            line: 代码行
            
        Returns:
            如果是重要的Markdown行返回 True
        """
        important_patterns = [
            r'^\s*#{1,6}\s+',                     # 标题
            r'^\s*[-*+]\s+',                      # 无序列表
            r'^\s*\d+\.\s+',                      # 有序列表
            r'^\s*>\s+',                          # 引用
            r'^\s*```',                           # 代码块
            r'^\s*\[.*\]\(.*\)',                  # 链接
            r'^\s*!\[.*\]\(.*\)',                 # 图片
            r'^\s*\|.*\|',                        # 表格
            r'^\s*---+\s*$',                      # 分隔线
        ]
        
        return any(re.match(pattern, line) for pattern in important_patterns)
    
    def _normalize_markdown_line(self, line: str) -> str:
        """
        规范化Markdown代码行
        
        Args:
            line: 原始代码行
            
        Returns:
            规范化后的代码行
        """
        working = line.rstrip()
        
        # 处理标题，保留标题级别和名称
        if re.match(r'^\s*#{1,6}\s+', working):
            match = re.match(r'^(\s*#{1,6}\s+[^\n]*)', working)
            if match:
                return match.group(1)
        
        # 处理列表项，保留列表标记
        if re.match(r'^\s*[-*+]\s+', working):
            match = re.match(r'^(\s*[-*+]\s+)', working)
            if match:
                return match.group(1) + "..."
        
        # 处理有序列表
        if re.match(r'^\s*\d+\.\s+', working):
            match = re.match(r'^(\s*\d+\.\s+)', working)
            if match:
                return match.group(1) + "..."
        
        # 处理引用
        if re.match(r'^\s*>\s+', working):
            match = re.match(r'^(\s*>\s+)', working)
            if match:
                return match.group(1) + "..."
        
        return working 