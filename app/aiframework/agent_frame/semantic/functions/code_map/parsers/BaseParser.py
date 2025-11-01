from __future__ import annotations
from typing import List, Optional, Protocol
from dataclasses import dataclass


@dataclass
class Function:
    name: str
    body: str


class BaseParser(Protocol):
    # 提取导入语句
    def extract_imports(self, file_content: str) -> List[str]: ...
    # 提取函数
    def extract_functions(self, file_content: str) -> List[Function]: ...
    # 提取函数调用
    def extract_function_calls(self, function_body: str) -> List[str]: ...
    # 解析导入路径
    def resolve_import_path(self, imp: str, current_file_path: str, base_path: str) -> Optional[str]: ...
    # 获取函数行号
    def get_function_line_number(self, file_content: str, function_name: str) -> int: ... 