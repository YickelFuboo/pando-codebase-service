"""
Swift代码压缩器
专门用于压缩Swift代码，保留重要的结构和注释
"""

import re
from .base_compressor import BaseCompressor


class SwiftCompressor(BaseCompressor):
    """Swift代码压缩器类"""
    
    def compress(self, content: str) -> str:
        """
        压缩Swift代码内容
        
        Args:
            content: 原始Swift代码内容
            
        Returns:
            压缩后的Swift代码内容
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
            if self._is_important_swift_line(trimmed_line):
                result.append(self._normalize_swift_line(line))
                continue
        
        return '\n'.join(result)
    
    def _is_important_swift_line(self, line: str) -> bool:
        """
        判断是否为重要的Swift代码行
        
        Args:
            line: 代码行
            
        Returns:
            如果是重要的Swift行返回 True
        """
        important_patterns = [
            r'^\s*(import|@import)\s+',           # import 语句
            r'^\s*(class|struct|enum|protocol|extension)\s+',  # 类型定义
            r'^\s*(public|private|internal|fileprivate|open)\s+',  # 访问修饰符
            r'^\s*(static|class|final|mutating|nonmutating)\s+',  # 其他修饰符
            r'^\s*func\s+\w+\s*\(',               # 函数定义
            r'^\s*var\s+\w+',                     # 变量定义
            r'^\s*let\s+\w+',                     # 常量定义
            r'^\s*\{|\}',                         # 大括号
            r'^\s*(if|else|for|while|repeat|switch|case|default|guard|defer|return|break|continue|fallthrough)\s',  # 控制语句
        ]
        
        return any(re.match(pattern, line) for pattern in important_patterns)
    
    def _normalize_swift_line(self, line: str) -> str:
        """
        规范化Swift代码行
        
        Args:
            line: 原始代码行
            
        Returns:
            规范化后的代码行
        """
        working = line.rstrip()
        
        # 处理类、结构体、枚举定义
        if re.match(r'^\s*(class|struct|enum|protocol)\s+\w+', working):
            match = re.match(r'^(\s*(?:class|struct|enum|protocol)\s+\w+)', working)
            if match:
                return match.group(1) + " { }"
        
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
        
        return working 