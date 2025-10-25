"""
SQL代码压缩器
专门用于压缩SQL代码，保留重要的结构和注释
"""

import re
from .base_compressor import BaseCompressor


class SqlCompressor(BaseCompressor):
    """SQL代码压缩器类"""
    
    def compress(self, content: str) -> str:
        """
        压缩SQL代码内容
        
        Args:
            content: 原始SQL代码内容
            
        Returns:
            压缩后的SQL代码内容
        """
        lines = content.split('\n')
        result = []
        
        for line in lines:
            trimmed_line = line.strip()
            
            if not trimmed_line:
                continue
            
            # 保留注释
            if trimmed_line.startswith('--') or trimmed_line.startswith('/*'):
                result.append(line)
                continue
            
            # 保留重要结构
            if self._is_important_sql_line(trimmed_line):
                result.append(self._normalize_sql_line(line))
                continue
        
        return '\n'.join(result)
    
    def _is_important_sql_line(self, line: str) -> bool:
        """
        判断是否为重要的SQL代码行
        
        Args:
            line: 代码行
            
        Returns:
            如果是重要的SQL行返回 True
        """
        important_patterns = [
            r'^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|GRANT|REVOKE|COMMIT|ROLLBACK|BEGIN|END)\s',  # DDL/DML语句
            r'^\s*(FROM|WHERE|GROUP\s+BY|ORDER\s+BY|HAVING|JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|INNER\s+JOIN|OUTER\s+JOIN)\s',  # 子句
            r'^\s*(UNION|INTERSECT|EXCEPT)\s',    # 集合操作
            r'^\s*(WITH|CTE)\s',                  # CTE
            r'^\s*(IF|CASE|WHEN|THEN|ELSE|END)\s',  # 条件语句
            r'^\s*\(|\)',                         # 括号
        ]
        
        return any(re.match(pattern, line, re.IGNORECASE) for pattern in important_patterns)
    
    def _normalize_sql_line(self, line: str) -> str:
        """
        规范化SQL代码行
        
        Args:
            line: 原始代码行
            
        Returns:
            规范化后的代码行
        """
        working = line.rstrip()
        
        # 处理SELECT语句，保留基本结构
        if re.match(r'^\s*SELECT\s+', working, re.IGNORECASE):
            # 简化SELECT语句，只保留基本结构
            if 'FROM' in working.upper():
                parts = re.split(r'\s+FROM\s+', working, flags=re.IGNORECASE, maxsplit=1)
                if len(parts) > 1:
                    return parts[0] + " FROM ..."
        
        # 处理CREATE语句
        if re.match(r'^\s*CREATE\s+', working, re.IGNORECASE):
            match = re.match(r'^(\s*CREATE\s+\w+)', working, re.IGNORECASE)
            if match:
                return match.group(1) + " ..."
        
        return working 