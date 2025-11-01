import os
from typing import List, Dict, Optional
from .base import BaseSemanticAnalyzer, SemanticModel, ProjectSemanticModel, ImportInfo


class GoSemanticAnalyzer(BaseSemanticAnalyzer):
    """
    Go 语言语义分析器（基础实现）

    与原 C# 版本保持一致的行为：
    - 仅支持 .go 文件
    - 文件级分析返回基础的包名信息
    - 项目级分析会：
      1) 收集所有 Go 文件
      2) 对每个文件读取内容并提取导入
      3) 记录文件模型与导入
      4) 基于简化规则解析导入依赖（优先在存在 go.mod 的工程内按包名匹配目录）
      5) 忽略解析异常，保证稳定性
    """

    @property
    def supported_extensions(self) -> List[str]:
        """支持的文件扩展名。"""
        return [".go"]

    async def analyze_file_async(self, file_path: str, content: str) -> SemanticModel:
        """文件级分析：返回基础模型（文件路径与包名）。"""
        return SemanticModel(
            file_path=file_path,
            namespace=self._extract_package_name(content),
        )

    async def analyze_project_async(self, file_paths: List[str]) -> ProjectSemanticModel:
        """项目级分析：遍历 Go 文件，提取导入并解析依赖。"""
        project = ProjectSemanticModel()

        # 只处理 .go 文件
        go_files = [f for f in file_paths if os.path.splitext(f)[1].lower() in self.supported_extensions]

        for file in go_files:
            try:
                # 读取文件内容
                with open(file, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()

                # 基础文件分析（包名）
                model = await self.analyze_file_async(file, content)

                # 提取导入并写入模型
                imports = self._extract_imports(content)
                model.imports = [ImportInfo(name=imp) for imp in imports]
                project.files[file] = model

                # 解析导入依赖（保持与 C# 一致：传入所有 file_paths，而非仅 go_files）
                deps: List[str] = []
                for imp in imports:
                    resolved = self._resolve_go_import(imp, file, file_paths)
                    if resolved:
                        deps.append(resolved)
                project.dependencies[file] = deps
            except Exception:
                # 忽略解析错误，确保系统稳定性
                pass
        return project

    def _extract_package_name(self, content: str) -> str:
        """从文件内容中提取 package 名，缺省为 'main'。"""
        for line in content.split('\n'):
            t = line.strip()
            if t.startswith('package '):
                parts = t.split(' ')
                if len(parts) > 1:
                    return parts[1].strip()
        return 'main'

    def _extract_imports(self, content: str) -> List[str]:
        """提取 import 路径，支持单行与 import 块，以及别名导入。"""
        imports: List[str] = []
        in_block = False
        for line in content.split('\n'):
            t = line.strip()
            if t.startswith('import ('):
                in_block = True
                continue
            if in_block and t == ')':
                in_block = False
                continue
            if in_block:
                imp = self._extract_import_path(t)
                if imp:
                    imports.append(imp)
            elif t.startswith('import '):
                # 跳过关键字，保留后续内容（可能包含别名与引号）
                imp = self._extract_import_path(t[7:])
                if imp:
                    imports.append(imp)
        return imports

    def _extract_import_path(self, line: str) -> str:
        """从一行 import 语句中提取真实路径，兼容别名写法。"""
        t = line.strip()
        # 纯路径（带引号）
        if t.startswith('"') and t.endswith('"'):
            return t[1:-1]
        # 别名导入：alias "path/to/pkg"
        parts = t.split(' ')
        if len(parts) > 1:
            last = parts[-1]
            if last.startswith('"') and last.endswith('"'):
                return last[1:-1]
        return ''

    def _resolve_go_import(self, imp: str, current_file: str, all_files: List[str]) -> Optional[str]:
        """
        简化的 Go 导入解析：
        - 取包名为导入路径最后一段
        - 若当前工程（从当前文件向上查找）存在 go.mod，则在传入的 all_files 中
          查找任意位于同名目录下的文件，并返回遇到的第一个文件路径
        - 与原 C# 行为保持一致：这里的 all_files 是"项目中的所有文件"，不只限 .go
        """
        package_name = imp.split('/')[-1]
        current_dir = os.path.dirname(current_file)
        root = self._find_go_mod_root(current_dir)
        if root:
            for f in all_files:
                if os.path.basename(os.path.dirname(f)) == package_name:
                    return f
        return None

    def _find_go_mod_root(self, start_dir: str) -> Optional[str]:
        """从起始目录向上查找包含 go.mod 的目录，找不到则返回 None。"""
        current = start_dir
        while current:
            if os.path.isfile(os.path.join(current, 'go.mod')):
                return current
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
        return None