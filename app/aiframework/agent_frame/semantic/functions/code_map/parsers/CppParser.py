import os
import re
from typing import List, Optional
from .BaseParser import BaseParser, Function


class CppParser(BaseParser):
    def extract_imports(self, file_content: str) -> List[str]:
        imports: List[str] = []

        # 匹配 #include 语句
        include_regex = re.compile(r"#include\s+[<\"]([^>\"]+)[>\"]")
        for m in include_regex.finditer(file_content):
            imports.append(m.group(1))
        return imports

    def extract_functions(self, file_content: str) -> List[Function]:
        functions: List[Function] = []

        func_regex = re.compile(r"(?:(?:[a-zA-Z0-9_\*&\s:<>,]+)\s+)?([a-zA-Z0-9_]+)\s*\([^)]*\)\s*(?:const)?\s*(?:noexcept)?\s*(?:override)?\s*(?:final)?\s*(?:=\s*default)?\s*(?:=\s*delete)?\s*(?:=\s*0)?\s*\{([^{}]*(?:{[^{}]*(?:{[^{}]*}[^{}]*)*}[^{}]*)*)\}")
        for m in func_regex.finditer(file_content):
            name = m.group(1)
            if not name.startswith("~") and name not in {"if", "for", "while", "switch", "catch"}:
                functions.append(Function(name=name, body=m.group(2) or ""))
        return functions

    def extract_function_calls(self, function_body: str) -> List[str]:
        calls: List[str] = []

        call_regex = re.compile(r"(?:(?:[a-zA-Z0-9_]+)::)?([a-zA-Z0-9_]+)\s*\(")
        for m in call_regex.finditer(function_body):
            name = m.group(1)
            if name not in {"if", "for", "while", "switch", "catch"}:
                calls.append(name)
        return calls

    def resolve_import_path(self, imp: str, current_file_path: str, base_path: str) -> Optional[str]:
        current_dir = os.path.dirname(current_file_path)
        
        if "/" in imp or "\\" in imp:
            for root, _, files in os.walk(base_path):
                for f in files:
                    if f == os.path.basename(imp):
                        return os.path.join(root, f)
        else:
            local_path = os.path.join(current_dir, imp)
            if os.path.isfile(local_path):
                return local_path
            for root, _, files in os.walk(base_path):
                for f in files:
                    if f == imp:
                        return os.path.join(root, f)
        return None

    def get_function_line_number(self, file_content: str, function_name: str) -> int:
        lines = file_content.split("\n")
        
        func_regex = re.compile(rf"(?:(?:[a-zA-Z0-9_\*&\s:<>,]+)\s+)?{re.escape(function_name)}\s*\(")
        for i, line in enumerate(lines, 1):
            if func_regex.search(line):
                return i
        return 0 