import os
import asyncio
from typing import List, Dict, Optional
from .semantic_analyzer.base import BaseSemanticAnalyzer, ProjectSemanticModel, FunctionInfo, TypeInfo
from .semantic_analyzer.go_semantic_analyzer import GoSemanticAnalyzer


class EnhancedDependencyAnalyzer:
    """
    增强的依赖分析器
    
    功能：
    - 支持多种编程语言的语义分析
    - 自动注册对应语言的语义分析器
    - 构建完整的项目依赖树
    - 处理循环依赖检测
    - 合并多语言项目的语义模型
    """

    def __init__(self, base_path: str) -> None:
        """
        初始化依赖分析器
        
        Args:
            base_path: 项目根目录路径
        """
        # 存储不同文件扩展名对应的语义分析器
        self._analyzers: Dict[str, BaseSemanticAnalyzer] = {}
        # 项目根目录
        self._base_path = base_path
        # 合并后的项目语义模型
        self._project_model: Optional[ProjectSemanticModel] = None
        # 初始化状态标志
        self._is_initialized = False

        # 注册各种语言的语义分析器
        self._register_analyzer(GoSemanticAnalyzer())
        # 其他语言的语义分析器注册（占位符，可后续添加）
        # self._register_analyzer(CSharpSemanticAnalyzer())
        # self._register_analyzer(PythonSemanticAnalyzer())
        # self._register_analyzer(JavaScriptSemanticAnalyzer())
        # self._register_analyzer(JavaSemanticAnalyzer())

    def _register_analyzer(self, analyzer: BaseSemanticAnalyzer) -> None:
        """
        注册语义分析器
        
        Args:
            analyzer: 要注册的语义分析器实例
        """
        # 为分析器支持的每个文件扩展名注册该分析器
        for ext in analyzer.supported_extensions:
            self._analyzers[ext] = analyzer

    async def initialize(self) -> None:
        """
        初始化项目分析
        
        执行步骤：
        1. 扫描项目中的所有源文件
        2. 按文件扩展名分组
        3. 使用对应的语义分析器分析每组文件
        4. 合并所有分析结果
        """
        # 避免重复初始化
        if self._is_initialized:
            return
            
        # 获取项目中的所有源文件
        files = self._get_all_source_files(self._base_path)
        
        # 按文件扩展名分组
        grouped: Dict[str, List[str]] = {}
        for f in files:
            grouped.setdefault(os.path.splitext(f)[1].lower(), []).append(f)
        
        # 并行处理不同语言的文件
        tasks = []
        for ext, fpaths in grouped.items():
            if ext in self._analyzers:
                analyzer = self._analyzers[ext]
                task = analyzer.analyze_project_async(fpaths)
                tasks.append(task)
        
        # 等待所有任务完成
        models = await asyncio.gather(*tasks)
        
        # 合并所有分析结果
        self._project_model = self._merge_project_models(models)
        self._is_initialized = True

    async def analyze_file_dependency_tree(self, file_path: str):
        """
        分析指定文件的依赖树
        
        Args:
            file_path: 要分析的文件路径
            
        Returns:
            文件的依赖树结构
        """
        # 确保已初始化
        await self.initialize()
        # 标准化文件路径
        normalized = os.path.abspath(file_path)
        # 用于检测循环依赖的访问记录
        visited: set[str] = set()
        return self._build_semantic_file_dependency_tree(normalized, visited, 0)

    def _build_semantic_file_dependency_tree(self, file_path: str, visited: set[str], level: int, max_depth: int = 10):
        """
        构建语义文件依赖树
        
        Args:
            file_path: 当前文件路径
            visited: 已访问的文件集合（用于检测循环依赖）
            level: 当前深度
            max_depth: 最大深度限制
            
        Returns:
            依赖树节点
        """
        from .code_map_service import DependencyTree, DependencyTreeFunction, DependencyNodeType
        
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
        
        # 如果项目模型存在且包含当前文件
        if self._project_model and file_path in self._project_model.files:
            # 添加导入依赖
            if file_path in self._project_model.dependencies:
                for dep in self._project_model.dependencies[file_path]:
                    # 递归构建依赖文件的依赖树
                    child = self._build_semantic_file_dependency_tree(dep, set(visited), level + 1, max_depth)
                    tree.children.append(child)
            
            # 添加类型继承依赖
            for t in file_model.types:
                # 处理基类依赖
                for base_type in t.base_types:
                    base_type_info = self._find_type_in_project(base_type)
                    if base_type_info and base_type_info.file_path != file_path:
                        child_visited = set(visited)
                        child = self._build_semantic_file_dependency_tree(base_type_info.file_path, child_visited, level + 1, max_depth)
                        tree.children.append(child)
                
                # 处理接口依赖
                for interface_type in t.interfaces:
                    interface_info = self._find_type_in_project(interface_type)
                    if interface_info and interface_info.file_path != file_path:
                        child_visited = set(visited)
                        child = self._build_semantic_file_dependency_tree(interface_info.file_path, child_visited, level + 1, max_depth)
                        tree.children.append(child)
            
            # 获取当前文件的语义模型
            file_model = self._project_model.files[file_path]
            
            # 添加函数信息
            for func in file_model.functions:
                tree.functions.append(DependencyTreeFunction(name=func.name, line_number=func.line_number))
            
            # 添加类型的方法信息
            for t in file_model.types:
                for m in t.methods:
                    tree.functions.append(DependencyTreeFunction(name=f"{t.name}.{m.name}", line_number=m.line_number))
        
        return tree

    def _merge_project_models(self, models: List[ProjectSemanticModel]) -> ProjectSemanticModel:
        """
        合并多个项目语义模型
        
        Args:
            models: 要合并的项目语义模型列表
            
        Returns:
            合并后的项目语义模型
        """
        merged = ProjectSemanticModel()
        
        # 合并所有模型的数据
        for m in models:
            # 合并文件信息
            merged.files.update(m.files)
            # 合并依赖关系
            merged.dependencies.update(m.dependencies)
            # 合并所有类型信息
            merged.all_types.update(m.all_types)
            # 合并所有函数信息
            merged.all_functions.update(m.all_functions)
        
        return merged

    def _get_all_source_files(self, path: str) -> List[str]:
        """
        获取指定路径下的所有源文件
        
        Args:
            path: 要扫描的目录路径
            
        Returns:
            源文件路径列表
        """
        # 支持的源文件扩展名
        exts = {".cs", ".go", ".py", ".js", ".ts", ".java", ".cpp", ".h", ".hpp", ".cc"}
        results: List[str] = []
        
        # 递归遍历目录
        for root, _, files in os.walk(path):
            for f in files:
                # 检查文件扩展名是否在支持的列表中
                if os.path.splitext(f)[1].lower() in exts:
                    results.append(os.path.join(root, f))
        
        return results
    
    def _find_type_in_project(self, type_name: str) -> Optional[TypeInfo]:
        """
        在项目中查找类型信息
        
        Args:
            type_name: 类型名称
            
        Returns:
            类型信息，如果未找到则返回None
        """
        if not self._project_model:
            return None
            
        for type_info in self._project_model.all_types.values():
            if (type_info.name == type_name or 
                type_info.full_name == type_name or 
                type_info.full_name.endswith(f".{type_name}")):
                return type_info
        return None
    
    def _find_function_in_file(self, file_path: str, function_name: str):
        """
        在指定文件中查找函数
        
        Args:
            file_path: 文件路径
            function_name: 函数名称
            
        Returns:
            函数信息，如果未找到则返回None
        """
        if not self._project_model or file_path not in self._project_model.files:
            return None
            
        file_model = self._project_model.files[file_path]
        
        # 查找顶级函数
        for func in file_model.functions:
            if func.name == function_name:
                return self._convert_to_code_map_function_info(func)
        
        # 查找类型中的方法
        for t in file_model.types:
            for method in t.methods:
                if method.name == function_name or f"{t.name}.{method.name}" == function_name:
                    return self._convert_to_code_map_function_info(method)
        
        return None
    
    def _resolve_function_call(self, call_name: str, current_file: str):
        """
        解析函数调用
        
        Args:
            call_name: 调用名称
            current_file: 当前文件
            
        Returns:
            函数信息，如果未找到则返回None
        """
        # 在当前文件中查找
        local_func = self._find_function_in_file(current_file, call_name)
        if local_func:
            return local_func
        
        # 在依赖文件中查找
        if (self._project_model and 
            current_file in self._project_model.dependencies):
            for dependency in self._project_model.dependencies[current_file]:
                dep_func = self._find_function_in_file(dependency, call_name)
                if dep_func:
                    return dep_func
        
        # 全局搜索
        if self._project_model:
            for file_model in self._project_model.files.values():
                search_func = self._find_function_in_file(file_model.file_path, call_name)
                if search_func:
                    return search_func
        
        return None
    
    def _convert_to_code_map_function_info(self, semantic_func: FunctionInfo):
        """
        将语义函数信息转换为代码映射函数信息
        
        Args:
            semantic_func: 语义函数信息
            
        Returns:
            代码映射函数信息
        """
        from .code_map_service import CodeMapFunctionInfo
        return CodeMapFunctionInfo(
            name=semantic_func.name,
            full_name=semantic_func.full_name,
            file_path=semantic_func.file_path,
            line_number=semantic_func.line_number,
            body=""  # 语义分析不提供函数体
        )
    
    def generate_dependency_tree_visualization(self, tree) -> str:
        """
        生成依赖树可视化
        
        Args:
            tree: 依赖树
            
        Returns:
            可视化字符串
        """
        sb = []
        self._generate_tree_visualization(tree, sb, "", True)
        return "\n".join(sb)
    
    def _generate_tree_visualization(self, node, sb: List[str], indent: str, is_last: bool):
        """
        生成树可视化
        
        Args:
            node: 树节点
            sb: 字符串构建器
            indent: 缩进
            is_last: 是否为最后一个节点
        """
        from .code_map_service import DependencyNodeType
        
        node_marker = "└── " if is_last else "├── "
        node_type = "[文件]" if node.node_type == DependencyNodeType.File else "[函数]"
        cyclic_marker = " (循环引用)" if node.is_cyclic else ""
        line_info = f" (行: {node.line_number})" if node.line_number > 0 else ""
        
        sb.append(f"{indent}{node_marker}{node_type} {node.name}{line_info}{cyclic_marker}")
        
        child_indent = indent + ("    " if is_last else "│   ")
        
        if (node.node_type == DependencyNodeType.File and 
            hasattr(node, 'functions') and 
            node.functions and 
            not node.is_cyclic):
            sb.append(f"{child_indent}├── [函数列表]")
            functions_indent = child_indent + "│   "
            
            for i, function in enumerate(node.functions):
                function_marker = "└── " if i == len(node.functions) - 1 else "├── "
                function_line_info = f" (行: {function.line_number})" if function.line_number > 0 else ""
                sb.append(f"{functions_indent}{function_marker}{function.name}{function_line_info}")
        
        if hasattr(node, 'children') and node.children and not node.is_cyclic:
            for i, child in enumerate(node.children):
                self._generate_tree_visualization(child, sb, child_indent, i == len(node.children) - 1) 