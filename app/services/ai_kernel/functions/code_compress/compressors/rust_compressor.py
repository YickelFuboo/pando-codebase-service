"""
Rust代码压缩器
专门用于压缩Rust代码，保留重要的结构和注释
"""

import re
from .base_compressor import BaseCompressor


class RustCompressor(BaseCompressor):
    """Rust代码压缩器类"""
    
    def compress(self, content: str) -> str:
        """
        压缩Rust代码内容
        
        Args:
            content: 原始Rust代码内容
            
        Returns:
            压缩后的Rust代码内容
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
            if self._is_important_rust_line(trimmed_line):
                result.append(self._normalize_rust_line(line))
                continue
        
        return '\n'.join(result)
    
    def _is_important_rust_line(self, line: str) -> bool:
        """
        判断是否为重要的Rust代码行
        
        Args:
            line: 代码行
            
        Returns:
            如果是重要的Rust行返回 True
        """
        important_patterns = [
            r'^\s*(use|mod|extern|crate)\s+',     # use、mod、extern、crate 语句
            r'^\s*(pub|pub\(crate\)|pub\(super\)|pub\(in\s+\w+\))\s+',  # 可见性修饰符
            r'^\s*(fn|struct|enum|trait|impl|type|const|static|macro_rules!)\s+',  # 定义关键字
            r'^\s*(if|else|for|while|loop|match|if\s+let|while\s+let)\s',  # 控制语句
            r'^\s*\{|\}',                         # 大括号
        ]
        
        return any(re.match(pattern, line) for pattern in important_patterns)
    
    def _normalize_rust_line(self, line: str) -> str:
        """
        规范化Rust代码行
        
        Args:
            line: 原始代码行
            
        Returns:
            规范化后的代码行
        """
        working = line.rstrip()
        
        # 处理函数定义
        if re.match(r'^\s*fn\s+\w+\s*\(', working):
            # 找到函数签名的结束位置
            paren_count = 0
            for i, char in enumerate(working):
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                    if paren_count == 0:
                        return working[:i+1] + " { }"
        
        # 处理结构体和枚举定义
        if re.match(r'^\s*(struct|enum)\s+\w+', working):
            match = re.match(r'^(\s*(?:struct|enum)\s+\w+)', working)
            if match:
                return match.group(1) + " { }"
        
        return working 