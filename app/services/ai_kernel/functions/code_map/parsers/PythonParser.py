import os
import re
from typing import List, Optional
from .BaseParser import BaseParser, Function


class PythonParser(BaseParser):
    # 提取导入语句
    def extract_imports(self, file_content: str) -> List[str]:
        imports: List[str] = []

        # 匹配 import 语句
        import_regex = re.compile(r"import\s+([^\n]+)")
        for m in import_regex.finditer(file_content):
            parts = [p.strip() for p in m.group(1).split(',') if p.strip()]
            imports.extend(parts)
        
        # 匹配 from 语句
        from_import_regex = re.compile(r"from\s+([^\s]+)\s+import\s+(?:([^\s,;]+)(?:\s*,\s*([^\s,;]+))*|\*)")
        for m in from_import_regex.finditer(file_content):
            imports.append(m.group(1))
        return imports

    # 提取函数
    def extract_functions(self, file_content: str) -> List[Function]:
        functions: List[Function] = []

        # 匹配函数声明
        func_regex = re.compile(r"def\s+(\w+)\s*\([^)]*\)\s*(?:->\s*[^:]+)?\s*:(.*?)(?=\n(?:def|class)|\Z)", re.DOTALL)
        for m in func_regex.finditer(file_content):
            functions.append(Function(name=m.group(1), body=m.group(2) or ""))
        return functions

    # 提取函数调用
    def extract_function_calls(self, function_body: str) -> List[str]:
        calls: List[str] = []

        # 匹配函数调用
        call_regex = re.compile(r"(\w+)\s*\(")
        for m in call_regex.finditer(function_body):
            name = m.group(1)
            if name not in {"print", "len", "int", "str", "list", "dict", "set", "tuple", "if", "while", "for"}:
                calls.append(name)

        # 匹配方法调用
        method_call_regex = re.compile(r"(\w+)\.(\w+)\s*\(")
        for m in method_call_regex.finditer(function_body):
            calls.append(m.group(2))
        return calls

    # 解析导入路径
    def resolve_import_path(self, imp: str, current_file_path: str, base_path: str) -> Optional[str]:
        current_dir = os.path.dirname(current_file_path)

        # 处理相对路径导入
        if imp.startswith('.'):
            parts = imp.split('.')
            dir_path = current_dir
            i = 0
            while i < len(parts) and parts[i] == '':
                dir_path = os.path.dirname(dir_path)
                i += 1
            for part in parts[i:]:
                module_path = os.path.join(dir_path, part + '.py')
                if os.path.isfile(module_path):
                    return module_path
                package_path = os.path.join(dir_path, part)
                init_path = os.path.join(package_path, '__init__.py')
                if os.path.isdir(package_path) and os.path.isfile(init_path):
                    return init_path
            return None
        else:
            module_name = imp.split('.')[0]
            for root, dirs, files in os.walk(base_path):
                for f in files:
                    if f == module_name + '.py':
                        return os.path.join(root, f)
            for root, dirs, files in os.walk(base_path):
                for d in dirs:
                    if d == module_name:
                        init_path = os.path.join(root, d, '__init__.py')
                        if os.path.isfile(init_path):
                            return init_path
        return None

    # 获取函数行号
    def get_function_line_number(self, file_content: str, function_name: str) -> int:
        lines = file_content.split('\n')
        
        func_regex = re.compile(rf"def\s+{re.escape(function_name)}\s*\(")
        for i, line in enumerate(lines, 1):
            if func_regex.search(line):
                return i
        return 0 