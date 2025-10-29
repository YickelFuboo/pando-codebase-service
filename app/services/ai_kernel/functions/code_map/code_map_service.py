import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional

from .parsers.BaseParser import BaseParser, Function
from .parsers.JavaScriptParser import JavaScriptParser
from .parsers.PythonParser import PythonParser
from .parsers.JavaParser import JavaParser
from .parsers.CppParser import CppParser
from .parsers.GoParser import GoParser
from .semantic_analyzer.base import BaseSemanticAnalyzer, ProjectSemanticModel
from .semantic_analyzer.go_semantic_analyzer import GoSemanticAnalyzer

@dataclass
class CodeMapFunctionInfo:
    """
    代码映射函数信息
    
    存储单个函数的详细信息，包括名称、位置、调用关系等
    """
    name: str                    # 函数名称
    full_name: str               # 完整函数标识（文件路径:函数名）
    body: str                    # 函数体内容
    file_path: str               # 所在文件路径
    line_number: int             # 函数定义行号
    calls: List[str] = field(default_factory=list)  # 函数调用的其他函数列表


class DependencyNodeType:
    """
    依赖树节点类型枚举
    
    定义依赖树中节点的类型，用于区分文件和函数节点
    """
    File = 'File'        # 文件节点
    Function = 'Function'  # 函数节点


@dataclass
class DependencyTreeFunction:
    """
    依赖树中的函数信息
    
    用于在依赖树中表示单个函数的信息
    """
    name: str            # 函数名称
    line_number: int = 0  # 函数定义行号


@dataclass
class DependencyTree:
    """
    依赖树节点
    
    表示依赖关系树中的一个节点，可以是文件或函数
    """
    node_type: str       # 节点类型（文件或函数）
    name: str            # 节点名称
    full_path: str       # 完整路径
    line_number: int = 0  # 行号
    is_cyclic: bool = False  # 是否为循环依赖
    children: List['DependencyTree'] = field(default_factory=list)  # 子节点列表
    functions: List[DependencyTreeFunction] = field(default_factory=list)  # 函数列表（仅文件节点）


@dataclass
class GitIgnoreRule:
    """
    Git忽略规则
    
    解析并存储 .gitignore 文件中的规则信息
    """
    original_pattern: str     # 原始模式字符串
    regex: re.Pattern        # 编译后的正则表达式
    is_negation: bool        # 是否为否定规则（以!开头）
    is_directory: bool       # 是否为目录规则（以/结尾）


class DependencyAnalyzer:
    """
    依赖分析器
    
    核心功能：
    - 解析多种编程语言的源代码文件
    - 提取函数定义和调用关系
    - 构建文件级和函数级的依赖树
    - 支持语义分析和传统解析两种模式
    - 处理 .gitignore 规则
    - 生成依赖关系的可视化输出
    """

    def __init__(self, base_path: str) -> None:
        """
        初始化依赖分析器
        
        Args:
            base_path: 项目根目录路径
        """
        # 文件依赖关系映射：文件路径 -> 依赖文件集合
        self._file_dependencies: Dict[str, Set[str]] = {}
        # 函数依赖关系映射：函数标识 -> 依赖函数集合
        self._function_dependencies: Dict[str, Set[str]] = {}
        # 文件到函数的映射：文件路径 -> 函数信息列表
        self._file_to_functions: Dict[str, List[CodeMapFunctionInfo]] = {}
        # 函数到文件的映射：函数标识 -> 文件路径
        self._function_to_file: Dict[str, str] = {}
        # 语言解析器列表
        self._parsers: List[BaseParser] = []
        # 语义分析器映射：文件扩展名 -> 语义分析器
        self._semantic_analyzers: Dict[str, GoSemanticAnalyzer] = {}
        # 项目根目录
        self._base_path = base_path
        # 初始化状态标志
        self._is_initialized = False
        # 语义分析模型
        self._semantic_model: Optional[ProjectSemanticModel] = None
        # Git忽略规则列表
        self._gitignore_rules: List[GitIgnoreRule] = []

        # 注册各种语言的解析器
        self._parsers.append(JavaScriptParser())
        self._parsers.append(PythonParser())
        self._parsers.append(JavaParser())
        self._parsers.append(CppParser())
        self._parsers.append(GoParser())

        # 注册语义分析器（当前未启用）
        self._register_semantic_analyzer(GoSemanticAnalyzer())

    def _register_semantic_analyzer(self, analyzer: GoSemanticAnalyzer) -> None:
        """
        注册语义分析器
        
        Args:
            analyzer: 要注册的语义分析器实例
        """
        # 为分析器支持的每个文件扩展名注册该分析器
        for ext in analyzer.supported_extensions:
            self._semantic_analyzers[ext.lower()] = analyzer  # type: ignore[index]

    async def initialize(self) -> None:
        """
        初始化依赖分析器
        
        执行步骤：
        1. 初始化 .gitignore 规则
        2. 获取所有源文件
        3. 执行语义分析（如果支持）
        4. 使用传统解析器处理剩余文件
        """
        # 避免重复初始化
        if self._is_initialized:
            return
            
        # 初始化 .gitignore 规则
        await self._initialize_gitignore()
        
        # 获取所有源文件
        files = self._get_all_source_files(self._base_path)
        
        # 执行语义分析
        await self._initialize_semantic_analysis(files)

        # 使用传统解析器处理不支持语义分析的文件
        traditional_files = [f for f in files if not self._has_semantic_analyzer(f)]
        
        # 顺序处理文件（可以后续改为并行处理）
        for file in traditional_files:
            parser = self._get_parser_for_file(file)
            if parser is None:
                continue
            try:
                # 读取文件内容并处理
                with open(file, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                await self._process_file(file, content, parser)
            except Exception:
                # 忽略处理错误，保持兼容性
                pass
                
        self._is_initialized = True

    async def _initialize_semantic_analysis(self, files: List[str]) -> None:
        """
        初始化语义分析
        
        Args:
            files: 要分析的文件列表
        """
        # 按文件扩展名分组
        grouped: Dict[str, List[str]] = {}
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in self._semantic_analyzers:
                grouped.setdefault(ext, []).append(f)
        
        # 使用对应的语义分析器分析每组文件
        models: List[ProjectSemanticModel] = []
        for ext, fpaths in grouped.items():
            analyzer = self._semantic_analyzers[ext]
            model = await analyzer.analyze_project_async(fpaths)
            models.append(model)
        
        # 合并语义分析结果
        self._semantic_model = self._merge_semantic_models(models)
        # 将语义分析结果转换为传统格式
        self._convert_semantic_to_traditional()

    def _has_semantic_analyzer(self, file_path: str) -> bool:
        """
        检查文件是否有对应的语义分析器
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否有语义分析器支持
        """
        return os.path.splitext(file_path)[1].lower() in self._semantic_analyzers

    def _merge_semantic_models(self, models: List[ProjectSemanticModel]) -> ProjectSemanticModel:
        """
        合并多个语义分析模型
        
        Args:
            models: 要合并的语义分析模型列表
            
        Returns:
            合并后的语义分析模型
        """
        merged = ProjectSemanticModel()
        
        # 合并所有模型的数据
        for m in models:
            # 合并文件信息
            for k, v in m.files.items():
                merged.files[k] = v
            # 合并依赖关系
            for k, v in m.dependencies.items():
                merged.dependencies[k] = v
            # 合并类型信息
            for k, v in m.all_types.items():
                merged.all_types[k] = v
            # 合并函数信息
            for k, v in m.all_functions.items():
                merged.all_functions[k] = v
                
        return merged

    def _convert_semantic_to_traditional(self) -> None:
        """
        将语义分析结果转换为传统解析格式
        
        将语义分析得到的结构化数据转换为传统的文件依赖和函数映射格式

        格式样例：
        {
            "dependencies": {
                "file1.go": ["file2.go", "file3.go"],
                "file2.go": ["file3.go", "file4.go"],
                "file3.go": ["file4.go", "file5.go", "file6.go"],
                "file4.go": ["file5.go", "file6.go"],
                "file5.go": ["file6.go"],
                "file6.go": [],
            },
        }
        """
        if not self._semantic_model:
            return
            
        # 转换依赖关系
        for path, deps in self._semantic_model.dependencies.items():
            self._file_dependencies[path] = set(deps)
        
        # 转换函数信息
        for file_model in self._semantic_model.files.values():
            function_list: List[CodeMapFunctionInfo] = []
            
            # 转换普通函数
            for func in file_model.functions:
                function_list.append(self._convert_semantic_function(func))
            
            # 转换类型的方法
            for t in file_model.types:
                for m in t.methods:
                    function_list.append(self._convert_semantic_function(m))
            
            # 更新映射关系
            self._file_to_functions[file_model.file_path] = function_list
            for func in function_list:
                self._function_to_file[func.full_name] = file_model.file_path

    def _convert_semantic_function(self, semantic_func) -> CodeMapFunctionInfo:
        """
        将语义分析函数转换为传统函数信息格式
        
        Args:
            semantic_func: 语义分析函数对象
            
        Returns:
            转换后的函数信息
        """
        return CodeMapFunctionInfo(
            name=semantic_func.name,
            full_name=semantic_func.full_name,
            file_path=semantic_func.file_path,
            line_number=semantic_func.line_number,
            body="",  # 语义分析通常不保存函数体
            calls=[c.name for c in getattr(semantic_func, 'calls', [])],  # 提取调用关系
        )

    async def _process_file(self, file_path: str, file_content: str, parser: BaseParser) -> None:
        """
        处理单个文件
        
        Args:
            file_path: 文件路径
            file_content: 文件内容
            parser: 对应的语言解析器
        """
        try:
            # 提取导入语句并解析依赖
            imports = parser.extract_imports(file_content)
            resolved = self._resolve_import_paths(imports, file_path, self._base_path, parser)
            self._file_dependencies[file_path] = resolved

            # 提取函数定义
            functions = parser.extract_functions(file_content)
            info_list: List[CodeMapFunctionInfo] = []
            
            for function in functions:
                # 创建函数信息对象
                info = CodeMapFunctionInfo(
                    name=function.name,
                    full_name=f"{file_path}:{function.name}",
                    body=function.body,
                    file_path=file_path,
                    line_number=parser.get_function_line_number(file_content, function.name),
                    calls=parser.extract_function_calls(function.body),
                )
                info_list.append(info)
                self._function_to_file[info.full_name] = file_path
                
            self._file_to_functions[file_path] = info_list
        except Exception as ex:
            # 忽略处理错误，保持兼容性
            pass

    def _resolve_import_paths(self, imports: List[str], current_file: str, base_path: str, parser: BaseParser) -> Set[str]:
        """
        解析导入路径为实际文件路径
        
        Args:
            imports: 导入语句列表
            current_file: 当前文件路径
            base_path: 项目根目录
            parser: 语言解析器
            
        Returns:
            解析后的文件路径集合
        """
        result: Set[str] = set()
        for imp in imports:
            resolved = parser.resolve_import_path(imp, current_file, base_path)
            if resolved and os.path.isfile(resolved):
                result.add(os.path.abspath(resolved))
        return result

    async def analyze_file_dependency_tree(self, file_path: str) -> 'DependencyTree':
        """
        分析文件依赖树
        
        Args:
            file_path: 要分析的文件路径
            
        Returns:
            文件的依赖树
        """
        await self.initialize()
        normalized = os.path.abspath(file_path)
        visited: Set[str] = set()
        return self._build_file_dependency_tree(normalized, visited, 0)

    async def analyze_function_dependency_tree(self, file_path: str, function_name: str) -> 'DependencyTree':
        """
        分析函数依赖树
        
        Args:
            file_path: 文件路径
            function_name: 函数名称
            
        Returns:
            函数的依赖树
        """
        await self.initialize()
        normalized = os.path.abspath(file_path)
        visited: Set[str] = set()
        return self._build_function_dependency_tree(normalized, function_name, visited, 0)

    def _build_file_dependency_tree(self, file_path: str, visited: Set[str], level: int, max_depth: int = 10) -> 'DependencyTree':
        """
        构建文件依赖树
        
        Args:
            file_path: 文件路径
            visited: 已访问的文件集合（用于检测循环依赖）
            level: 当前深度
            max_depth: 最大深度限制
            
        Returns:
            文件依赖树节点
        """
        # 检查深度限制和循环依赖
        if level > max_depth or file_path in visited:
            return DependencyTree(
                node_type=DependencyNodeType.File, 
                name=os.path.basename(file_path), 
                full_path=file_path, 
                is_cyclic=file_path in visited
            )
        
        # 标记当前文件为已访问
        visited.add(file_path)
        
        # 创建当前文件的依赖树节点
        tree = DependencyTree(
            node_type=DependencyNodeType.File, 
            name=os.path.basename(file_path), 
            full_path=file_path
        )
        
        # 添加依赖文件的子节点
        deps = self._file_dependencies.get(file_path, set())
        for dep in deps:
            child = self._build_file_dependency_tree(dep, set(visited), level + 1, max_depth)
            tree.children.append(child)
        
        # 添加文件中的函数信息
        for func in self._file_to_functions.get(file_path, []):
            tree.functions.append(DependencyTreeFunction(name=func.name, line_number=func.line_number))
            
        return tree

    def _build_function_dependency_tree(self, file_path: str, function_name: str, visited: Set[str], level: int, max_depth: int = 10) -> 'DependencyTree':
        """
        构建函数依赖树
        
        Args:
            file_path: 文件路径
            function_name: 函数名称
            visited: 已访问的函数集合（用于检测循环依赖）
            level: 当前深度
            max_depth: 最大深度限制
            
        Returns:
            函数依赖树节点
        """
        full_id = f"{file_path}:{function_name}"
        
        # 检查深度限制和循环依赖
        if level > max_depth or full_id in visited:
            return DependencyTree(
                node_type=DependencyNodeType.Function, 
                name=function_name, 
                full_path=full_id, 
                is_cyclic=full_id in visited
            )
        
        # 标记当前函数为已访问
        visited.add(full_id)
        
        # 创建当前函数的依赖树节点
        tree = DependencyTree(
            node_type=DependencyNodeType.Function, 
            name=function_name, 
            full_path=full_id
        )
        
        # 查找目标函数
        functions = self._file_to_functions.get(file_path, [])
        target = next((f for f in functions if f.name == function_name), None)
        
        if target:
            tree.line_number = target.line_number
            
            # 添加被调用函数的子节点
            for called in target.calls:
                resolved = self._resolve_function_call(called, file_path)
                if resolved:
                    child = self._build_function_dependency_tree(
                        resolved.file_path, 
                        resolved.name, 
                        set(visited), 
                        level + 1, 
                        max_depth
                    )
                    tree.children.append(child)
                    
        return tree

    def _resolve_function_call(self, function_call: str, current_file: str) -> Optional[CodeMapFunctionInfo]:
        """
        解析函数调用
        
        按优先级查找函数定义：
        1. 当前文件中的函数
        2. 依赖文件中的函数
        3. 项目中任意文件中的函数
        
        Args:
            function_call: 函数调用名称
            current_file: 当前文件路径
            
        Returns:
            找到的函数信息，如果未找到则返回 None
        """
        # 在当前文件中查找
        for f in self._file_to_functions.get(current_file, []):
            if f.name == function_call:
                return f
        
        # 在依赖文件中查找
        for dep in self._file_dependencies.get(current_file, set()):
            for f in self._file_to_functions.get(dep, []):
                if f.name == function_call:
                    return f
        
        # 在项目中任意文件中查找
        for _, funcs in self._file_to_functions.items():
            for f in funcs:
                if f.name == function_call:
                    return f
                    
        return None

    def _get_parser_for_file(self, file_path: str) -> Optional[BaseParser]:
        """
        根据文件扩展名获取对应的语言解析器
        
        Args:
            file_path: 文件路径
            
        Returns:
            对应的语言解析器，如果未找到则返回 None
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        # 根据文件扩展名匹配对应的解析器
        for p in self._parsers:
            if ext == ".js" and isinstance(p, JavaScriptParser):
                return p
            if ext == ".py" and isinstance(p, PythonParser):
                return p
            if ext == ".java" and isinstance(p, JavaParser):
                return p
            if ext in {".cpp", ".h", ".hpp", ".cc"} and isinstance(p, CppParser):
                return p
            if ext == ".go" and isinstance(p, GoParser):
                return p
                
        return None

    def _get_all_source_files(self, path: str) -> List[str]:
        """
        获取指定路径下的所有源文件
        
        Args:
            path: 要扫描的目录路径
            
        Returns:
            源文件路径列表（已过滤 .gitignore 规则）
        """
        # 支持的源文件扩展名
        extensions = {".cs", ".js", ".py", ".java", ".cpp", ".h", ".hpp", ".cc", ".go"}
        all_files = []
        
        # 递归遍历目录
        for root, _, files in os.walk(path):
            for f in files:
                if os.path.splitext(f)[1].lower() in extensions:
                    full = os.path.join(root, f)
                    # 检查是否被 .gitignore 忽略
                    if not self._is_ignored_by_gitignore(full):
                        all_files.append(full)
                        
        return all_files

    async def _initialize_gitignore(self) -> None:
        """
        初始化 .gitignore 规则
        
        读取并解析项目根目录下的 .gitignore 文件
        """
        gitignore_path = os.path.join(self._base_path, '.gitignore')
        if os.path.isfile(gitignore_path):
            try:
                # 读取 .gitignore 文件内容
                with open(gitignore_path, 'r', encoding='utf-8', errors='ignore') as fp:
                    lines = [line.rstrip('\n') for line in fp]
                # 解析规则
                self._gitignore_rules = self._parse_gitignore_rules(lines)
            except Exception:
                # 解析失败时使用空规则列表
                self._gitignore_rules = []

    def _parse_gitignore_rules(self, lines: List[str]) -> List[GitIgnoreRule]:
        """
        解析 .gitignore 规则
        
        Args:
            lines: .gitignore 文件的行列表
            
        Returns:
            解析后的规则列表
        """
        rules: List[GitIgnoreRule] = []
        
        for line in lines:
            # 去除行首尾的空白字符
            trimmed = line.strip()
            # 跳过空行和注释行
            if not trimmed or trimmed.startswith('#'):
                continue
                
            # 解析否定规则（以!开头）
            is_negation = trimmed.startswith('!')
            pattern = trimmed[1:] if is_negation else trimmed
            
            # 解析目录规则（以/结尾），如果以/结尾，则去掉/
            is_directory = pattern.endswith('/')
            if is_directory:
                pattern = pattern[:-1]
                
            # 转换为正则表达式
            regex = self._convert_gitignore_pattern_to_regex(pattern)
            # 编译正则表达式
            compiled = re.compile(regex, re.IGNORECASE)
            
            # 创建规则对象
            rules.append(GitIgnoreRule(
                original_pattern=trimmed, 
                regex=compiled, 
                is_negation=is_negation, 
                is_directory=is_directory
            ))
            
        return rules

    def _convert_gitignore_pattern_to_regex(self, pattern: str) -> str:
        """
        将 .gitignore 模式转换为正则表达式
        
        Args:
            pattern: .gitignore 模式字符串
            
        Returns:
            对应的正则表达式字符串
        """
        sb: List[str] = []
        
        # 处理绝对路径（以/开头）
        is_absolute = pattern.startswith('/')
        if is_absolute:
            pattern = pattern[1:]
            sb.append('^')
        else:
            sb.append('(^|/)')
            
        i = 0
        while i < len(pattern):
            c = pattern[i]
            
            if c == '*':
                # 处理 ** 模式（递归匹配）
                if i + 1 < len(pattern) and pattern[i + 1] == '*':
                    if i + 2 < len(pattern) and pattern[i + 2] == '/':
                        sb.append('(.*/)')
                        i += 3
                        continue
                    else:
                        sb.append('.*')
                        i += 2
                        continue
                else:
                    # 处理单个 *（匹配非路径分隔符）
                    sb.append('[^/]*')
                    i += 1
                    continue
            elif c == '?':
                # 处理 ?（匹配单个非路径分隔符字符）
                sb.append('[^/]')
            elif c in '[]':
                # 处理字符类
                sb.append(re.escape(c))
            elif c in '.^$+(){}|\\':
                # 转义特殊字符
                sb.append('\\' + c)
            else:
                # 普通字符
                sb.append(c)
            i += 1
            
        # 添加结尾匹配
        if not is_absolute:
            sb.append('($|/)')
        else:
            sb.append('$')
            
        return ''.join(sb)

    def _is_ignored_by_gitignore(self, file_path: str) -> bool:
        """
        检查文件是否被 .gitignore 规则忽略
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否被忽略
        """
        if not self._gitignore_rules:
            return False
            
        # 转换为相对于项目根目录的路径
        relative = os.path.relpath(file_path, self._base_path).replace('\\', '/')
        is_ignored = False
        
        # 应用所有规则
        for rule in self._gitignore_rules:
            matches = False
            
            if rule.is_directory:
                # 目录规则：匹配目录路径或文件路径
                dir_path = os.path.dirname(relative).replace('\\', '/')
                matches = bool(rule.regex.search(dir_path)) or bool(rule.regex.search(relative))
            else:
                # 文件规则：匹配文件路径
                matches = bool(rule.regex.search(relative))
                
            if matches:
                if rule.is_negation:
                    # 否定规则：取消忽略
                    is_ignored = False
                else:
                    # 普通规则：标记为忽略
                    is_ignored = True
                    
        return is_ignored
    def generate_dependency_tree_visualization(self, tree: DependencyTree) -> str:
        """
        生成依赖树的可视化文本表示
        
        Args:
            tree: 要可视化的依赖树
            
        Returns:
            格式化的树形结构文本
        """
        sb: List[str] = []
        self._generate_tree_visualization(tree, sb, '', True)
        return '\n'.join(sb)

    def _generate_tree_visualization(self, node: DependencyTree, sb: List[str], indent: str, is_last: bool) -> None:
        """
        递归生成树形可视化文本
        
        Args:
            node: 当前节点
            sb: 字符串构建器列表
            indent: 当前缩进
            is_last: 是否为最后一个子节点
        """
        # 选择节点标记符号
        node_marker = '└── ' if is_last else '├── '
        # 根据节点类型选择显示标签
        node_type = '[文件]' if node.node_type == DependencyNodeType.File else '[函数]'
        # 添加循环引用标记
        cyclic_marker = ' (循环引用)' if node.is_cyclic else ''
        # 添加行号信息
        line_info = f" (行: {node.line_number})" if node.line_number > 0 else ''
        # 构建节点显示文本
        sb.append(f"{indent}{node_marker}{node_type} {node.name}{line_info}{cyclic_marker}")
        
        # 计算子节点的缩进
        child_indent = indent + ('    ' if is_last else '│   ')
        
        # 如果是文件节点且包含函数列表，则显示函数
        if node.node_type == DependencyNodeType.File and node.functions and not node.is_cyclic:
            sb.append(f"{child_indent}├── [函数列表]")
            functions_indent = child_indent + '│   '
            for i, f in enumerate(node.functions):
                marker = '└── ' if i == len(node.functions) - 1 else '├── '
                line_info = f" (行: {f.line_number})" if f.line_number > 0 else ''
                sb.append(f"{functions_indent}{marker}{f.name}{line_info}")
        
        # 递归处理子节点（避免循环引用）
        if not node.is_cyclic and node.children:
            for i, child in enumerate(node.children):
                self._generate_tree_visualization(child, sb, child_indent, i == len(node.children) - 1)

    def generate_dot_graph(self, tree: DependencyTree) -> str:
        """
        生成 DOT 格式的图形描述（用于 Graphviz 可视化）
        
        Args:
            tree: 要生成图形的依赖树
            
        Returns:
            DOT 格式的图形描述字符串
        """
        sb: List[str] = []
        # 添加图形头部
        sb.append('digraph DependencyTree {')
        sb.append('  node [shape=box, style=filled, fontname="Arial"];')
        sb.append('  edge [fontname="Arial"];')
        # 节点计数器，用于生成唯一节点ID
        node_counter: Dict[str, int] = {}
        self._generate_dot_nodes(tree, sb, node_counter)
        sb.append('}')
        return '\n'.join(sb)

    async def is_file_ignored(self, file_path: str) -> bool:
        """
        检查文件是否被 .gitignore 忽略
        
        Args:
            file_path: 要检查的文件路径
            
        Returns:
            如果文件被忽略则返回 True，否则返回 False
        """
        await self._initialize_gitignore()
        return self._is_ignored_by_gitignore(file_path)

    async def get_gitignore_rules(self) -> List[str]:
        """
        获取所有 .gitignore 规则
        
        Returns:
            .gitignore 规则列表
        """
        await self._initialize_gitignore()
        return [r.original_pattern for r in self._gitignore_rules]

    def _generate_dot_nodes(self, node: DependencyTree, sb: List[str], node_counter: Dict[str, int], parent_id: Optional[str] = None) -> None:
        """
        递归生成 DOT 格式的节点和边
        
        Args:
            node: 当前节点
            sb: 字符串构建器列表
            node_counter: 节点计数器字典
            parent_id: 父节点ID（用于生成边）
        """
        # 为节点生成唯一ID
        if node.full_path not in node_counter:
            node_counter[node.full_path] = len(node_counter)
        node_id = f"node{node_counter[node.full_path]}"
        
        # 根据节点类型和状态选择颜色
        node_color = 'lightblue' if node.node_type == DependencyNodeType.File else 'lightgreen'
        if node.is_cyclic:
            node_color = 'lightsalmon'  # 循环引用用橙色标记
        
        # 构建节点标签
        label = node.name
        if node.line_number > 0:
            label += f"\\n(行: {node.line_number})"
        if node.is_cyclic:
            label += "\\n(循环引用)"
        
        # 生成节点定义
        sb.append(f"  {node_id} [label=\"{label}\", fillcolor=\"{node_color}\"];")
        
        # 如果有父节点，生成边
        if parent_id is not None:
            sb.append(f"  {parent_id} -> {node_id};")
        
        # 递归处理子节点（避免循环引用）
        if not node.is_cyclic and node.children:
            for child in node.children:
                self._generate_dot_nodes(child, sb, node_counter, node_id)
        """
        递归生成 DOT 格式的节点和边
        
        Args:
            node: 当前节点
            sb: 字符串构建器列表
            node_counter: 节点计数器字典
            parent_id: 父节点ID（用于生成边）
        """
        # 为节点生成唯一ID
        if node.full_path not in node_counter:
            node_counter[node.full_path] = len(node_counter)
        node_id = f"node{node_counter[node.full_path]}"
        
        # 根据节点类型和状态选择颜色
        node_color = 'lightblue' if node.node_type == DependencyNodeType.File else 'lightgreen'
        if node.is_cyclic:
            node_color = 'lightsalmon'  # 循环引用用橙色标记
        
        # 构建节点标签
        label = node.name
        if node.line_number > 0:
            label += f"\\n(行: {node.line_number})"
        if node.is_cyclic:
            label += "\\n(循环引用)"
        
        # 生成节点定义
        sb.append(f"  {node_id} [label=\"{label}\", fillcolor=\"{node_color}\"];")
        
        # 如果有父节点，生成边
        if parent_id is not None:
            sb.append(f"  {parent_id} -> {node_id};")
        
        # 递归处理子节点（避免循环引用）
        if not node.is_cyclic and node.children:
            for child in node.children:
                self._generate_dot_nodes(child, sb, node_counter, node_id) 