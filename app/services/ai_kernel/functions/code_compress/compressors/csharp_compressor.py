"""
C#代码压缩器
专门用于压缩C#代码，保留重要的结构和注释
支持复杂的C#语法特性
"""

import re
from .base_compressor import BaseCompressor


class CSharpCompressor(BaseCompressor):
    """C#代码压缩器类"""
    
    def compress(self, content: str) -> str:
        """
        压缩C#代码内容
        
        Args:
            content: 原始C#代码内容
            
        Returns:
            压缩后的C#代码内容
        """
        lines = content.split('\n')
        result = []
        in_multi_line_comment = False
        
        for line in lines:
            trimmed_line = line.strip()
            
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
            
            # 保留注释
            if (trimmed_line.startswith('//') or trimmed_line.startswith('/*') or 
                trimmed_line.startswith('*') or trimmed_line.startswith('///')):
                result.append(line)
                continue
            
            # 保留重要结构
            if self._is_important_csharp_line(trimmed_line):
                result.append(self._normalize_csharp_line(line))
                continue
        
        return '\n'.join(result)
    
    def _is_important_csharp_line(self, line: str) -> bool:
        """
        判断是否为重要的C#代码行
        
        Args:
            line: 代码行
            
        Returns:
            如果是重要的C#行返回 True
        """
        important_patterns = [
            r'^\s*(using|namespace)\s+',          # using 和 namespace 语句
            r'^\s*(public|private|protected|internal|static|readonly|const|virtual|abstract|override|sealed|partial)\s+',  # 修饰符
            r'^\s*(class|interface|struct|enum|delegate|event)\s+',  # 类型定义
            r'^\s*(get|set|add|remove)\s*\{',     # 属性访问器
            r'^\s*\[.*\]',                         # 特性
            r'^\s*\{|\}',                         # 大括号
            r'^\s*(if|else|for|foreach|while|do|switch|case|default|try|catch|finally|throw|return|break|continue|goto)\s',  # 控制语句
            r'^\s*operator\s+',                   # 运算符重载
            r'^\s*implicit\s+operator',           # 隐式转换
            r'^\s*explicit\s+operator',           # 显式转换
            r'^\s*where\s+',                      # 泛型约束
            r'^\s*new\s+',                        # new 表达式
            r'^\s*base\s*\(',                     # 基类构造函数调用
            r'^\s*this\s*\(',                     # 构造函数链式调用
            r'^\s*out\s+',                        # out 参数
            r'^\s*ref\s+',                        # ref 参数
            r'^\s*params\s+',                     # params 参数
            r'^\s*async\s+',                      # async 方法
            r'^\s*await\s+',                      # await 表达式
            r'^\s*yield\s+',                      # yield 语句
            r'^\s*lock\s*\(',                     # lock 语句
            r'^\s*using\s*\(',                    # using 语句
            r'^\s*fixed\s*\(',                    # fixed 语句
            r'^\s*checked\s*\{',                  # checked 块
            r'^\s*unchecked\s*\{',                # unchecked 块
            r'^\s*unsafe\s+',                     # unsafe 块
            r'^\s*stackalloc\s+',                 # stackalloc 表达式
            r'^\s*sizeof\s*\(',                   # sizeof 表达式
            r'^\s*typeof\s*\(',                   # typeof 表达式
            r'^\s*nameof\s*\(',                   # nameof 表达式
            r'^\s*default\s*\(',                  # default 表达式
            r'^\s*is\s+',                         # is 模式匹配
            r'^\s*as\s+',                         # as 转换
        ]
        
        return any(re.match(pattern, line) for pattern in important_patterns)
    
    def _normalize_csharp_line(self, line: str) -> str:
        """
        规范化C#代码行
        
        Args:
            line: 原始代码行
            
        Returns:
            规范化后的代码行
        """
        working = line.rstrip()
        
        # 处理类、接口、结构体、枚举定义
        if re.match(r'^\s*(class|interface|struct|enum)\s+\w+', working):
            match = re.match(r'^(\s*(?:class|interface|struct|enum)\s+\w+)', working)
            if match:
                return match.group(1) + " { }"
        
        # 处理方法定义，包括复杂的方法签名
        if re.match(r'^\s*(?:public|private|protected|internal|static|readonly|const|virtual|abstract|override|sealed|partial)?\s*[\w<>\[\]]+\s+\w+\s*\(', working):
            # 找到方法签名的结束位置
            paren_count = 0
            for i, char in enumerate(working):
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                    if paren_count == 0:
                        # 检查是否有 throws 子句
                        throws_match = re.search(r'\s+throws\s+[\w\s,]+', working[i:])
                        if throws_match:
                            return working[:i+1] + throws_match.group() + " { }"
                        else:
                            return working[:i+1] + " { }"
        
        # 处理属性定义
        if re.match(r'^\s*(?:public|private|protected|internal|static|readonly|const|virtual|abstract|override|sealed|partial)?\s*[\w<>\[\]]+\s+\w+\s*\{', working):
            # 简化属性定义
            match = re.match(r'^(\s*(?:public|private|protected|internal|static|readonly|const|virtual|abstract|override|sealed|partial)?\s*[\w<>\[\]]+\s+\w+)', working)
            if match:
                return match.group(1) + " { get; set; }"
        
        # 处理索引器定义
        if re.match(r'^\s*(?:public|private|protected|internal|static|readonly|const|virtual|abstract|override|sealed|partial)?\s*[\w<>\[\]]+\s+this\s*\[', working):
            # 找到索引器签名的结束位置
            bracket_count = 0
            paren_count = 0
            for i, char in enumerate(working):
                if char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                elif char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                    if bracket_count == 0 and paren_count == 0:
                        return working[:i+1] + " { get; set; }"
        
        # 处理事件定义
        if re.match(r'^\s*(?:public|private|protected|internal|static|readonly|const|virtual|abstract|override|sealed|partial)?\s*event\s+', working):
            match = re.match(r'^(\s*(?:public|private|protected|internal|static|readonly|const|virtual|abstract|override|sealed|partial)?\s*event\s+[\w<>\[\]]+\s+\w+)', working)
            if match:
                return match.group(1) + ";"
        
        # 处理委托定义
        if re.match(r'^\s*(?:public|private|protected|internal|static|readonly|const|virtual|abstract|override|sealed|partial)?\s*delegate\s+', working):
            # 找到委托签名的结束位置
            paren_count = 0
            for i, char in enumerate(working):
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                    if paren_count == 0:
                        return working[:i+1] + ";"
        
        # 处理字段定义，移除初始化值
        if re.match(r'^\s*(?:public|private|protected|internal|static|readonly|const|virtual|abstract|override|sealed|partial)?\s*[\w<>\[\]]+\s+\w+\s*=', working):
            match = re.match(r'^(\s*(?:public|private|protected|internal|static|readonly|const|virtual|abstract|override|sealed|partial)?\s*[\w<>\[\]]+\s+\w+)\s*=', working)
            if match:
                return match.group(1) + ";"
        
        return working 