import os
import re
from typing import List, Optional
from .BaseParser import BaseParser, Function


class JavaScriptParser(BaseParser):
    def extract_imports(self, file_content: str) -> List[str]:
        imports: List[str] = []

        # 匹配 import 语句
        import_regex = re.compile(r"import\s+(?:{[^}]*}|\*\s+as\s+\w+|\w+)\s+from\s+['\"]([^'\"]+)['\"];", re.MULTILINE)
        imports += [m.group(1) for m in import_regex.finditer(file_content)]

        # 匹配 require 语句
        require_regex = re.compile(r"(?:const|let|var)\s+(?:{\s*[^}]*\s*}|\w+)\s*=\s*require\(['\"]([^'\"]+)['\"]", re.MULTILINE)
        imports += [m.group(1) for m in require_regex.finditer(file_content)]

        return imports

    # 提取函数
    def extract_functions(self, file_content: str) -> List[Function]:
        functions: List[Function] = []

        # 匹配函数声明
        func_regex = re.compile(r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*function|(?:const|let|var)\s+(\w+)\s*=\s*\([^)]*\)\s*=>)\s*{([^{}]*(?:{[^{}]*(?:{[^{}]*}[^{}]*)*}[^{}]*)*)}", re.DOTALL)
        for m in func_regex.finditer(file_content):
            name = m.group(1) or m.group(2) or m.group(3)
            body = m.group(4) or ""
            functions.append(Function(name=name, body=body))

        # 匹配方法声明
        method_regex = re.compile(r"(\w+)\s*\([^)]*\)\s*{([^{}]*(?:{[^{}]*(?:{[^{}]*}[^{}]*)*}[^{}]*)*)}", re.DOTALL)
        for m in method_regex.finditer(file_content):
            if m.group(1).lower() != "function":
                functions.append(Function(name=m.group(1), body=m.group(2) or ""))
        
        return functions

    # 提取函数调用
    def extract_function_calls(self, function_body: str) -> List[str]:
        calls: List[str] = []

        # 匹配函数调用
        call_regex = re.compile(r"(\w+)\s*\(")
        for m in call_regex.finditer(function_body):
            name = m.group(1)
            if name not in {"if", "for", "while", "switch", "catch"}:
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
        if imp.startswith("./") or imp.startswith("../"):
            resolved_path = os.path.abspath(os.path.join(current_dir, imp))
            if not os.path.splitext(resolved_path)[1]:
                for ext in [".js", ".jsx", ".ts", ".tsx"]:
                    if os.path.isfile(resolved_path + ext):
                        return resolved_path + ext
                if os.path.isdir(resolved_path):
                    for idx in ["index.js", "index.jsx", "index.ts", "index.tsx"]:
                        p = os.path.join(resolved_path, idx)
                        if os.path.isfile(p):
                            return p
            elif os.path.isfile(resolved_path):
                return resolved_path
        # 处理非相对路径导入
        elif not imp.startswith("/"):
            node_modules = self._find_node_modules_path(current_dir)
            if node_modules:
                package_path = os.path.join(node_modules, imp)
                if os.path.isdir(package_path):
                    package_json = os.path.join(package_path, "package.json")
                    if os.path.isfile(package_json):
                        try:
                            with open(package_json, "r", encoding="utf-8") as f:
                                content = f.read()
                            m = re.search(r'"main"\s*:\s*"([^"]+)"', content)
                            if m:
                                main_file = os.path.join(package_path, m.group(1))
                                if os.path.isfile(main_file):
                                    return main_file
                        except Exception:
                            pass
                    idx = os.path.join(package_path, "index.js")
                    if os.path.isfile(idx):
                        return idx
            for root, _, files in os.walk(base_path):
                for file in files:
                    if file.endswith(".js"):
                        full = os.path.join(root, file)
                        if os.path.splitext(file)[0] == imp or file == imp + ".js":
                            return full
        return None

    # 查找 node_modules 路径
    def _find_node_modules_path(self, start_dir: str) -> Optional[str]:
        current = start_dir

        # 遍历当前目录及父目录
        while current:
            candidate = os.path.join(current, "node_modules")
            if os.path.isdir(candidate):
                return candidate
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
        return None

    # 获取函数行号
    def get_function_line_number(self, file_content: str, function_name: str) -> int:
        lines = file_content.split("\n")

        # 匹配函数声明
        func_regex = re.compile(rf"function\s+{re.escape(function_name)}\s*\(|const\s+{re.escape(function_name)}\s*=\s*function|const\s+{re.escape(function_name)}\s*=\s*\(|let\s+{re.escape(function_name)}\s*=\s*function|let\s+{re.escape(function_name)}\s*=\s*\(|var\s+{re.escape(function_name)}\s*=\s*function|var\s+{re.escape(function_name)}\s*=\s*\(")
        for i, line in enumerate(lines, 1):
            if func_regex.search(line):
                return i

        # 匹配方法声明
        method_regex = re.compile(rf"\b{re.escape(function_name)}\s*\([^)]*\)\s*{{")
        for i, line in enumerate(lines, 1):
            if method_regex.search(line):
                return i
        return 0 