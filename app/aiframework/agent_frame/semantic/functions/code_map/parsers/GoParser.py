import os
import re
from typing import List, Optional
from .BaseParser import BaseParser, Function


class GoParser(BaseParser):
    def extract_imports(self, file_content: str) -> List[str]:
        imports: List[str] = []

        # 匹配单个导入
        single_import_regex = re.compile(r'import\s+"([^"]+)"')
        for m in single_import_regex.finditer(file_content):
            imports.append(m.group(1))

        # 匹配多个导入
        multi_import_regex = re.compile(r'import\s*\(\s*((?:[^)]*\n?)*)\s*\)', re.DOTALL)
        for block in multi_import_regex.finditer(file_content):
            import_block = block.group(1)
            import_line_regex = re.compile(r'"([^"]+)"')
            for m in import_line_regex.finditer(import_block):
                imports.append(m.group(1))
        return imports

    # 提取函数
    def extract_functions(self, file_content: str) -> List[Function]:
        functions: List[Function] = []

        # 匹配函数
        func_regex = re.compile(r'func\s+(?:\([^)]*\)\s+)?(\w+)\s*\([^)]*\)(?:\s*[^\{]*)?\{([^{}]*(?:{[^{}]*(?:{[^{}]*}[^{}]*)*}[^{}]*)*)\}', re.DOTALL)
        for m in func_regex.finditer(file_content):
            name = m.group(1)
            if name not in {"if", "for", "switch", "select", "range"}:
                functions.append(Function(name=name, body=m.group(2) or ""))
        return functions

    # 提取函数调用
    def extract_function_calls(self, function_body: str) -> List[str]:
        calls: List[str] = []

        # 匹配函数调用
        call_regex = re.compile(r'(\w+)\s*\(')
        for m in call_regex.finditer(function_body):
            name = m.group(1)
            if name not in {"if", "for", "switch", "select", "range", "make", "new", "len", "cap", "append", "copy", "delete", "panic", "recover"}:
                calls.append(name)

        # 匹配方法调用
        method_call_regex = re.compile(r'(\w+)\.(\w+)\s*\(')
        for m in method_call_regex.finditer(function_body):
            calls.append(m.group(2))

        # 匹配包调用
        package_call_regex = re.compile(r'(\w+)\.(\w+)\s*\(')
        for m in package_call_regex.finditer(function_body):
            package_name = m.group(1)
            function_name = m.group(2)
            if function_name not in calls:
                calls.append(f"{package_name}.{function_name}")
        return calls

    # 解析导入路径
    def resolve_import_path(self, imp: str, current_file_path: str, base_path: str) -> Optional[str]:
        current_dir = os.path.dirname(current_file_path)

        # 如果路径是相对路径，则解析为绝对路径
        if imp.startswith('./') or imp.startswith('../'):
            resolved_path = os.path.abspath(os.path.join(current_dir, imp))
            if os.path.isdir(resolved_path):
                for f in os.listdir(resolved_path):
                    if f.endswith('.go'):
                        return os.path.join(resolved_path, f)
            
            # 如果路径没有后缀，则添加 .go 后缀
            if not os.path.splitext(resolved_path)[1]:
                resolved_path += '.go'
            if os.path.isfile(resolved_path):
                return resolved_path
        # 处理标准库导入和三方库导入
        else:
            # 如果路径是标准库，则返回 None
            if self._is_standard_library(imp):
                return None
            
            # 处理三方库导入
            package_name = imp.split('/')[-1]
            for root, dirs, files in os.walk(base_path):
                if os.path.basename(root) == package_name:
                    for f in files:
                        if f.endswith('.go'):
                            return os.path.join(root, f)

            # 如果路径是三方库，则查找 go.mod 文件
            go_mod = self._find_go_mod_file(current_dir)
            if go_mod:
                module_root = os.path.dirname(go_mod)
                full_path = os.path.join(module_root, imp.replace('/', os.sep))
                if os.path.isdir(full_path):
                    for f in os.listdir(full_path):
                        if f.endswith('.go'):
                            return os.path.join(full_path, f)
        return None

    # 获取函数行号
    def get_function_line_number(self, file_content: str, function_name: str) -> int:
        lines = file_content.split('\n')
        
        func_regex = re.compile(rf'func\s+(?:\([^)]*\)\s+)?{re.escape(function_name)}\s*\(')
        for i, line in enumerate(lines, 1):
            if func_regex.search(line):
                return i
        return 0

    def _is_standard_library(self, imp: str) -> bool:
        standard_libs = {"fmt", "os", "io", "net", "http", "json", "time", "strings", "strconv",
                         "context", "sync", "log", "errors", "sort", "math", "crypto", "encoding",
                         "database", "html", "image", "mime", "path", "regexp", "runtime", "testing",
                         "unsafe", "archive", "bufio", "bytes", "compress", "container", "debug",
                         "go", "hash", "index", "plugin", "reflect", "text", "unicode"}
        first = imp.split('/')[0]
        return first in standard_libs or '.' not in imp

    def _find_go_mod_file(self, start_dir: str) -> Optional[str]:
        current = start_dir
        while current:
            candidate = os.path.join(current, 'go.mod')
            if os.path.isfile(candidate):
                return candidate
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
        return None 