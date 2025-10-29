"""
Java代码压缩器
专门用于压缩Java代码，保留重要的结构和注释
支持复杂的Java语法特性
"""

import re
from .base_compressor import BaseCompressor


class JavaCompressor(BaseCompressor):
    """Java代码压缩器类"""
    
    def compress(self, content: str) -> str:
        """
        压缩Java代码内容
        
        Args:
            content: 原始Java代码内容
            
        Returns:
            压缩后的Java代码内容
        """
        lines = content.split('\n')
        result = []
        in_multi_line_comment = False
        
        for raw_line in lines:
            line = raw_line
            trimmed_line = line.strip()
            
            # 跳过空行
            if not trimmed_line:
                continue
            
            # 处理多行注释开始/结束
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
            
            # 保留单行/文档注释
            if trimmed_line.startswith('//'):
                result.append(line)
                continue
            
            # 保留重要结构行并对其进行规范化
            if self._is_important_java_line(trimmed_line):
                result.append(self._normalize_java_line(line))
                continue
            
            # 保留独立的大括号以维持语法结构
            if trimmed_line == '{' or trimmed_line == '}':
                result.append(line)
        
        return '\n'.join(result)
    
    def _is_important_java_line(self, line: str) -> bool:
        """
        判断是否为重要的Java代码行
        
        Args:
            line: 代码行
            
        Returns:
            如果是重要的Java行返回 True
        """
        important_patterns = [
            r'^\s*package\s+',                  # package 声明
            r'^\s*import\s+',                   # import 语句
            r'^\s*(public|private|protected|static|abstract|final|native|synchronized|transient|volatile)\s+.*class\s+',  # 类声明
            r'^\s*(public|private|protected|static|abstract|final|native|synchronized|transient|volatile)\s+.*interface\s+',  # 接口声明
            r'^\s*(public|private|protected|static|abstract|final|native|synchronized|transient|volatile)\s+.*enum\s+',  # 枚举声明
            r'^\s*@\w+',                        # 注解
            r'^\s*(public|private|protected|static|abstract|final|native|synchronized|transient|volatile)\s+.*\(',  # 方法声明
            r'^\s*(public|private|protected|static|final|volatile|transient)\s+.*\s+\w+\s*[{;=]', # 属性/字段声明
            r'^\s*\{',                          # 开始大括号
            r'^\s*\}',                          # 结束大括号
            r'^\s*throws\s+',                   # 异常声明
            r'^\s*extends\s+',                  # 继承声明
            r'^\s*implements\s+',               # 接口实现声明
            r'^\s*@Override',                   # 重写注解
            r'^\s*@Deprecated',                 # 弃用注解
            r'^\s*@SuppressWarnings',           # 忽略警告注解
            r'^\s*@FunctionalInterface',        # 函数式接口注解
            r'^\s*record\s+',                   # Java 16+ record 声明
            r'^\s*sealed\s+',                   # Java 17+ sealed 类声明
            r'^\s*permits\s+',                  # Java 17+ permits 声明
            r'^\s*non-sealed\s+',               # Java 17+ non-sealed 声明
            r'^\s*default\s+',                  # 默认方法
            r'^\s*static\s+',                   # 静态方法
            r'^\s*abstract\s+',                 # 抽象方法
            r'^\s*final\s+',                    # final 方法
            r'^\s*native\s+',                   # native 方法
            r'^\s*synchronized\s+',             # synchronized 方法
            r'^\s*strictfp\s+',                 # strictfp 方法
            r'^\s*transient\s+',                # transient 字段
            r'^\s*volatile\s+',                 # volatile 字段
            r'^\s*const\s+',                    # const 字段（已废弃）
            r'^\s*assert\s+',                   # 断言
            r'^\s*break\s+',                    # break 语句
            r'^\s*continue\s+',                 # continue 语句
            r'^\s*return\s+',                   # return 语句
            r'^\s*throw\s+',                    # throw 语句
            r'^\s*new\s+',                      # new 表达式
            r'^\s*super\s*\(',                  # super 构造函数调用
            r'^\s*this\s*\(',                   # this 构造函数调用
            r'^\s*instanceof\s+',               # instanceof 操作符
            r'^\s*cast\s+',                     # 类型转换
            r'^\s*var\s+',                      # Java 10+ var 关键字
            r'^\s*yield\s+',                    # Java 14+ yield 语句
            r'^\s*switch\s*\(',                 # switch 表达式
            r'^\s*case\s+',                     # case 标签
            r'^\s*default\s*:',                 # default 标签
            r'^\s*->\s*',                       # 箭头操作符
        ]
        
        return any(re.match(pattern, line, re.IGNORECASE) for pattern in important_patterns)
    
    def _normalize_java_line(self, line: str) -> str:
        """
        规范化Java代码行
        
        Args:
            line: 原始代码行
            
        Returns:
            规范化后的代码行
        """
        working = line.rstrip()
        
        # 处理 lambda 表达式
        arrow_index = working.find('->')
        if arrow_index >= 0:
            prefix = working[:arrow_index].rstrip()
            # 替换为空方法体
            return prefix + " -> { }"
        
        # 处理字段/属性赋值
        equal_index = working.find('=')
        if equal_index >= 0 and '==' not in working:
            prefix = working[:equal_index].rstrip()
            if not prefix.endswith(';'):
                prefix += ";"
            return prefix
        
        # 处理方法声明，确保方法体为空
        if re.match(r'^\s*(public|private|protected|static|abstract|final|native|synchronized)\s+.*\)\s*\{?\s*$', working):
            if not working.endswith('{'):
                return working + " { }"
            else:
                return working
        
        # 处理类定义，移除继承和实现部分
        if re.match(r'^\s*(public|private|protected)?\s*(abstract|final)?\s*class\s+\w+', working):
            # 保留类名，移除 extends 和 implements
            match = re.match(r'^(\s*(?:public|private|protected)?\s*(?:abstract|final)?\s*class\s+\w+)', working)
            if match:
                return match.group(1) + " { }"
        
        # 处理接口定义
        if re.match(r'^\s*(public|private|protected)?\s*(abstract|final)?\s*interface\s+\w+', working):
            match = re.match(r'^(\s*(?:public|private|protected)?\s*(?:abstract|final)?\s*interface\s+\w+)', working)
            if match:
                return match.group(1) + " { }"
        
        # 处理枚举定义
        if re.match(r'^\s*(public|private|protected)?\s*(abstract|final)?\s*enum\s+\w+', working):
            match = re.match(r'^(\s*(?:public|private|protected)?\s*(?:abstract|final)?\s*enum\s+\w+)', working)
            if match:
                return match.group(1) + " { }"
        
        # 处理注解定义
        if re.match(r'^\s*@interface\s+\w+', working):
            match = re.match(r'^(\s*@interface\s+\w+)', working)
            if match:
                return match.group(1) + " { }"
        
        # 处理记录定义（Java 16+）
        if re.match(r'^\s*(public|private|protected)?\s*record\s+\w+', working):
            match = re.match(r'^(\s*(?:public|private|protected)?\s*record\s+\w+)', working)
            if match:
                return match.group(1) + " { }"
        
        return working 