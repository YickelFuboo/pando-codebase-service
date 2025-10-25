"""
通用代码压缩器
提供通用的代码压缩功能，适用于大多数编程语言
"""

import re
from typing import List
from .base_compressor import BaseCompressor


class GenericCompressor(BaseCompressor):
    """通用代码压缩器类"""
    
    def compress(self, content: str) -> str:
        """
        压缩代码内容
        
        Args:
            content: 原始代码内容
            
        Returns:
            压缩后的代码内容
        """
        lines = content.split('\n')
        result = []
        in_multi_line_comment = False
        
        for line in lines:
            trimmed_line = line.strip()
            
            # 跳过空行
            if not trimmed_line:
                continue
            
            # 处理多行注释
            if trimmed_line.startswith('/*'):
                in_multi_line_comment = True
                result.append(line)
                if '*/' in trimmed_line:
                    in_multi_line_comment = False
                continue
            
            if in_multi_line_comment:
                result.append(line)
                if '*/' in trimmed_line:
                    in_multi_line_comment = False
                continue
            
            # 保留注释行
            if (trimmed_line.startswith('//') or trimmed_line.startswith('#') or 
                trimmed_line.startswith('/*') or trimmed_line.startswith('*') or
                trimmed_line.startswith("'''") or trimmed_line.startswith('"""')):
                result.append(line)
                continue
            
            # 保留结构性行（如函数声明、类声明等）
            if self._is_structural_line(trimmed_line):
                result.append(self._normalize_structural_line(line))
                continue
            
            # 保留非空行但移除实现细节
            normalized_line = self._normalize_implementation_line(line)
            if normalized_line.strip():
                result.append(normalized_line)
        
        return '\n'.join(result)
    
    def _is_structural_line(self, line: str) -> bool:
        """
        判断是否为结构性代码行（如函数声明、类声明等）
        
        Args:
            line: 代码行
            
        Returns:
            如果是结构性行返回 True
        """
        # 检查常见的结构性关键字
        structural_patterns = [
            r'^\s*(class|interface|enum|struct|namespace|import|using|include|require|from|package)\s+',
            r'^\s*(public|private|protected|internal|static|final|abstract|override|virtual|extern|const)\s+',
            r'^\s*(function|def|func|sub|proc|method|procedure|fn|fun|async|await|export)\s+',
            r'^\s*(var|let|const|dim|int|string|bool|float|double|void|auto|val|char)\s+',
            r'^\s*(@|\[|#)\w+',  # 装饰器、特性、注解
            r'^\s*<\w+',         # XML/HTML标签
            r'^\s*\w+\s*\(',     # 函数调用
            r'^\s*\{|\}|\(|\)|\[|\]', # 括号
            r'^\s*#\w+',         # 预处理指令
        ]
        
        return any(re.match(pattern, line, re.IGNORECASE) for pattern in structural_patterns)
    
    def _normalize_structural_line(self, line: str) -> str:
        """
        规范化结构性代码行
        
        Args:
            line: 原始代码行
            
        Returns:
            规范化后的代码行
        """
        # 保留函数/方法声明，但移除函数体
        if re.match(r'^\s*(\w+\s+)*\w+\s*\([^)]*\)\s*(\{|\=>)', line):
            match = re.match(r'^(.*?\([^)]*\))', line)
            if match:
                return match.group(1) + " { }"
        
        # 保留变量声明，但移除初始化表达式
        if re.match(r'^\s*(\w+\s+)*\w+\s*=', line):
            match = re.match(r'^(.*?)=', line)
            if match:
                return match.group(1) + ";"
        
        return line
    
    def _normalize_implementation_line(self, line: str) -> str:
        """
        规范化实现代码行（移除实现细节）
        
        Args:
            line: 原始代码行
            
        Returns:
            规范化后的代码行
        """
        # 移除赋值表达式右侧
        if ('=' in line and '==' not in line and '!=' not in line and 
            '<=' not in line and '>=' not in line):
            parts = line.split('=', 1)
            if len(parts) > 1:
                return parts[0] + ";"
        
        # 移除函数调用参数
        if re.search(r'\w+\s*\(', line):
            return re.sub(r'(\w+\s*)\([^)]*\)', r'\1();', line)
        
        return line 