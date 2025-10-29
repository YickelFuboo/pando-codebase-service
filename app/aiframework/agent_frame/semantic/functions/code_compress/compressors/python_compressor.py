"""
Python代码压缩器
专门用于压缩Python代码，保留重要的结构和注释
"""

import re
from .base_compressor import BaseCompressor


class PythonCompressor(BaseCompressor):
    """Python代码压缩器类"""
    
    def compress(self, content: str) -> str:
        """
        压缩Python代码内容
        
        Args:
            content: 原始Python代码内容
            
        Returns:
            压缩后的Python代码内容
        """
        lines = content.split('\n')
        result = []
        
        for raw_line in lines:
            line = raw_line
            if not line.strip():
                continue
            
            trimmed_line = line.rstrip()
            
            # 保留注释
            if trimmed_line.strip().startswith('#'):
                result.append(trimmed_line)
                continue
            
            # 保留重要结构
            if self._is_important_python_line(line):
                result.append(trimmed_line)
                
                # 对于 def/class，插入占位 pass 保持语法有效
                if re.match(r'^\s*(def|class)\s+', trimmed_line, re.IGNORECASE):
                    indent = re.match(r'^\s*', trimmed_line).group()
                    result.append(indent + "    pass")
                continue
        
        return '\n'.join(result)
    
    def _is_important_python_line(self, line: str) -> bool:
        """
        判断是否为重要的 Python 代码行（去除变量赋值条目）
        
        Args:
            line: 代码行
            
        Returns:
            如果是重要的Python行返回 True
        """
        important_patterns = [
            r'^\s*import\s+',                   # import 语句
            r'^\s*from\s+.*import',             # from import 语句
            r'^\s*def\s+',                      # 函数定义
            r'^\s*class\s+',                    # 类定义
            r'^\s*@\w+',                        # 装饰器
            r'^\s*if\s+__name__\s*==',          # 主程序入口
            r'^\s*(if|elif|else|for|while|try|except|finally|with)[\s:]', # 控制结构
            r'^\s*return\s+',                   # return
            r'^\s*print\s*\('                   # print
        ]
        
        return any(re.match(pattern, line) for pattern in important_patterns) 