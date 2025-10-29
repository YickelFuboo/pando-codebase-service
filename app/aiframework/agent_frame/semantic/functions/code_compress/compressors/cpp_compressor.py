"""
C++代码压缩器
专门用于压缩C++代码，保留重要的结构和注释
支持复杂的C++语法特性
"""

import re
from .base_compressor import BaseCompressor


class CppCompressor(BaseCompressor):
    """C++代码压缩器类"""
    
    def compress(self, content: str) -> str:
        """
        压缩C++代码内容
        
        Args:
            content: 原始C++代码内容
            
        Returns:
            压缩后的C++代码内容
        """
        lines = content.split('\n')
        result = []
        in_multi_line_comment = False
        in_preprocessor = False
        
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
            
            # 保留单行注释
            if trimmed_line.startswith('//'):
                result.append(line)
                continue
            
            # 处理预处理指令
            if trimmed_line.startswith('#'):
                result.append(line)
                in_preprocessor = trimmed_line.endswith('\\')
                continue
            
            if in_preprocessor:
                result.append(line)
                in_preprocessor = trimmed_line.endswith('\\')
                continue
            
            # 保留重要结构行并对其进行规范化
            if self._is_important_cpp_line(trimmed_line):
                result.append(self._normalize_cpp_line(line))
                continue
            
            # 保留独立的大括号以维持语法结构
            if trimmed_line == '{' or trimmed_line == '}' or trimmed_line == '};':
                result.append(line)
        
        return '\n'.join(result)
    
    def _is_important_cpp_line(self, line: str) -> bool:
        """
        判断是否为重要的C++代码行
        
        Args:
            line: 代码行
            
        Returns:
            如果是重要的C++行返回 True
        """
        important_patterns = [
            r'^\s*#include\s+',                 # 头文件包含
            r'^\s*#define\s+',                  # 宏定义
            r'^\s*#if',                         # 条件编译开始
            r'^\s*#else',                       # 条件编译else
            r'^\s*#elif',                       # 条件编译elif
            r'^\s*#endif',                      # 条件编译结束
            r'^\s*#pragma',                     # 编译器指令
            r'^\s*namespace\s+',                # 命名空间声明
            r'^\s*using\s+',                    # using 声明
            r'^\s*template\s*<',                # 模板声明
            r'^\s*(class|struct|union|enum)\s+', # 类型声明
            r'^\s*(public|private|protected):',  # 访问修饰符
            r'^\s*(virtual|static|explicit|inline|constexpr|friend|extern|mutable)\s+', # 函数修饰符
            r'^\s*(const|volatile|noexcept|throw|final|override|delete|default)\s+', # 函数特性
            r'^\s*\w+::\w+\s*\(',               # 类方法实现
            r'^\s*\w+\s*\([^)]*\)\s*(\{|const|override|final|noexcept|throw|->|=|;)', # 函数声明/定义
            r'^\s*typedef\s+',                  # 类型定义
            r'^\s*using\s+\w+\s*=',             # 类型别名
            r'^\s*friend\s+',                   # 友元声明
            r'^\s*operator\s*',                 # 运算符重载
            r'^\s*~\w+\s*\(',                   # 析构函数
            r'^\s*\w+\s*\(\)\s*:\s*',           # 构造函数初始化列表
            r'^\s*static_assert\s*\(',          # 静态断言
            r'^\s*concept\s+',                  # C++20 概念
            r'^\s*requires\s+',                 # C++20 约束
            r'^\s*export\s+',                   # 模块导出
            r'^\s*import\s+',                   # 模块导入
            r'^\s*module\s+',                   # 模块声明
            r'^\s*\{',                          # 开始大括号
            r'^\s*\}',                          # 结束大括号
            r'^\s*};',                          # 类/结构体定义结束
            r'^\s*auto\s+',                     # auto 关键字
            r'^\s*decltype\s*\(',               # decltype 表达式
            r'^\s*typeid\s*\(',                 # typeid 表达式
            r'^\s*alignas\s*\(',                # alignas 说明符
            r'^\s*alignof\s*\(',                # alignof 操作符
            r'^\s*nullptr',                     # nullptr 关键字
            r'^\s*override\s+',                 # override 说明符
            r'^\s*final\s+',                    # final 说明符
            r'^\s*delete\s+',                   # delete 说明符
            r'^\s*default\s+',                  # default 说明符
            r'^\s*noexcept\s*\(',               # noexcept 操作符
            r'^\s*constexpr\s+',                # constexpr 说明符
            r'^\s*consteval\s+',                # consteval 说明符（C++20）
            r'^\s*constinit\s+',                # constinit 说明符（C++20）
            r'^\s*co_await\s+',                 # co_await 表达式
            r'^\s*co_yield\s+',                 # co_yield 表达式
            r'^\s*co_return\s+',                # co_return 语句
            r'^\s*requires\s+',                 # requires 子句
            r'^\s*concept\s+',                  # concept 定义
        ]
        
        return any(re.match(pattern, line, re.IGNORECASE) for pattern in important_patterns)
    
    def _normalize_cpp_line(self, line: str) -> str:
        """
        规范化C++代码行
        
        Args:
            line: 原始代码行
            
        Returns:
            规范化后的代码行
        """
        working = line.rstrip()
        
        # 处理 lambda 表达式
        lambda_index = working.find('](')
        if lambda_index >= 0 and '->' in working:
            arrow_index = working.find('->')
            if arrow_index > lambda_index:
                prefix = working[:arrow_index].rstrip()
                return prefix + " -> { }"
        
        # 处理变量初始化
        equal_index = working.find('=')
        if equal_index >= 0 and '==' not in working and '<=' not in working and '>=' not in working and '!=' not in working:
            # 检查是否是类型别名或宏定义
            if not re.match(r'^\s*(using|#define)', working[:equal_index]):
                prefix = working[:equal_index].rstrip()
                if not prefix.endswith(';'):
                    prefix += ";"
                return prefix
        
        # 处理函数声明，确保函数体为空
        if re.match(r'^\s*\w+\s*\([^)]*\)\s*(const|override|final|noexcept|throw)?\s*\{?\s*$', working):
            if not working.endswith('{'):
                return working + " { }"
            else:
                return working
        
        # 处理模板特化
        if re.match(r'^\s*template\s*<.*>\s*$', working):
            return working
        
        # 处理类定义
        if re.match(r'^\s*(class|struct|union)\s+\w+', working):
            match = re.match(r'^(\s*(?:class|struct|union)\s+\w+)', working)
            if match:
                return match.group(1) + " { }"
        
        # 处理枚举定义
        if re.match(r'^\s*enum\s+', working):
            match = re.match(r'^(\s*enum\s+\w+)', working)
            if match:
                return match.group(1) + " { }"
        
        # 处理命名空间定义
        if re.match(r'^\s*namespace\s+\w+', working):
            match = re.match(r'^(\s*namespace\s+\w+)', working)
            if match:
                return match.group(1) + " { }"
        
        return working 