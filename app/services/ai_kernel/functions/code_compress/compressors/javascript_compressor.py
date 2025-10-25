"""
JavaScript/TypeScript代码压缩器
专门用于压缩JavaScript和TypeScript代码，保留重要的结构和注释
"""

import re
from .base_compressor import BaseCompressor


class JavaScriptCompressor(BaseCompressor):
    """JavaScript/TypeScript代码压缩器类"""
    
    def compress(self, content: str) -> str:
        """
        压缩JavaScript/TypeScript代码内容
        
        Args:
            content: 原始JavaScript/TypeScript代码内容
            
        Returns:
            压缩后的JavaScript/TypeScript代码内容
        """
        lines = content.split('\n')
        result = []
        
        for raw_line in lines:
            line = raw_line
            trimmed_line = line.strip()
            
            if not trimmed_line:
                continue
            
            # 保留注释
            if trimmed_line.startswith('//') or trimmed_line.startswith('/*'):
                result.append(line)
                continue
            
            # 保留重要结构并进行规范化
            if self._is_important_javascript_line(trimmed_line):
                result.append(self._normalize_javascript_line(line))
                continue
            
            # 保留独立的大括号
            if trimmed_line == '{' or trimmed_line == '}':
                result.append(trimmed_line)
        
        return '\n'.join(result)
    
    def _normalize_javascript_line(self, line: str) -> str:
        """
        规范化 JavaScript/TypeScript 重要代码行：
        1. 移除箭头函数/表达式主体实现
        2. 移除变量赋值右侧表达式
        
        Args:
            line: 原始代码行
            
        Returns:
            规范化后的代码行
        """
        working = line.rstrip()
        
        # 1. 统一处理函数/方法体，将其替换为 {}
        # 匹配以 { 结尾的行，并且不是单独的 {
        if working.endswith('{') and working.strip() != '{':
            # 找到最后一个 ')' 或 '=>'，这通常是函数签名的结束
            signature_end = working.rfind(')')
            arrow_end = working.rfind('=>')
            last_index = max(signature_end, arrow_end + 1)
            
            if last_index > -1 and last_index < len(working) - 1:
                prefix = working[:last_index + 1].rstrip()
                return prefix + " {}"
        
        # 2. 处理箭头函数 =>
        arrow_index = working.find('=>')
        if arrow_index >= 0:
            # 避免处理已经有 {} 的情况
            if '{' not in working[arrow_index:]:
                prefix = working[:arrow_index].rstrip()
                return prefix + " => {}"
        
        # 3. 处理变量赋值，仅当它是函数表达式时
        equal_index = working.find('=')
        if equal_index > 0 and ('function' in working or '=>' in working):
            # 这部分逻辑主要由上面的函数体处理覆盖，这里作为一个补充
            # 对于复杂的单行函数，保留其定义，由上面的逻辑处理
            return working
        # 对于非函数的重要行（如 import/export），保持原样
        elif equal_index == -1:
            return working
        
        # 对于其他情况，如果不是函数赋值，则可能是一个简单的值，我们不在这里处理
        # _is_important_javascript_line 应该足够智能以避免匹配它们
        return working
    
    def _is_important_javascript_line(self, line: str) -> bool:
        """
        判断是否为重要的 JavaScript/TypeScript 代码行
        
        Args:
            line: 代码行
            
        Returns:
            如果是重要的JavaScript行返回 True
        """
        # 这组正则表达式旨在更精确地捕获结构性代码
        important_patterns = [
            # ES6+ 模块导入/导出
            r'^\s*(import|export)\s+',
            
            # 类、接口、枚举、类型别名声明 (支持 public/private/protected 等 TS 修饰符)
            r'^\s*((public|private|protected|static|readonly|abstract|async)\s+)*\s*(class|interface|enum|type)\s+\w+',
            
            # 标准函数声明 (function foo() {}) 和生成器函数 (function* foo() {})
            r'^\s*(async\s+)?function\*?\s+\w+\s*\(',
            
            # 变量/常量声明，且其值为函数表达式或箭头函数
            r'^\s*(const|let|var)\s+[\w\d_]+\s*[:=]\s*(async\s+)?(\([^)]*\)|[\w\d_]+)\s*=>',  # const myFunc = (a) => ...
            r'^\s*(const|let|var)\s+[\w\d_]+\s*=\s*(async\s+)?function\*?',  # const myFunc = function...
            
            # 类或对象中的方法定义
            r'^\s*(static\s+|get\s+|set\s+|async\s+)?\*?[\w\d_]+\s*\([^)]*\)\s*\{',  # myMethod(args) {
            r'^\s*[\w\d_]+\s*:\s*(async\s+)?(function\*?\(|\([^)]*\)\s*=>)',  # myProp: function() 或 myProp: () =>
            
            # 独立的大括号
            r'^\s*\{',
            r'^\s*\}'
        ]
        
        return any(re.match(pattern, line) for pattern in important_patterns) 