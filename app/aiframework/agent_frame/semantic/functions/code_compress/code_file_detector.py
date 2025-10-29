"""
代码文件类型检测器
用于识别文件是否为代码文件，以及确定编程语言类型
"""

import os
from typing import Dict, List, Optional


class CodeFileDetector:
    """代码文件类型检测器类"""
    
    # 支持的代码文件扩展名及其对应的语言类型
    CODE_EXTENSIONS: Dict[str, str] = {
        # C# 相关
        ".cs": "csharp",
        ".csx": "csharp",
        
        # JavaScript/TypeScript 相关
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        
        # Python 相关
        ".py": "python",
        ".pyw": "python",
        ".pyi": "python",
        
        # Java 相关
        ".java": "java",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".scala": "scala",
        
        # C/C++ 相关
        ".c": "c",
        ".cpp": "cpp",
        ".cxx": "cpp",
        ".cc": "cpp",
        ".c++": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".hxx": "cpp",
        ".hh": "cpp",
        ".h++": "cpp",
        
        # Go 相关
        ".go": "go",
        
        # Rust 相关
        ".rs": "rust",
        
        # PHP 相关
        ".php": "php",
        ".php3": "php",
        ".php4": "php",
        ".php5": "php",
        ".phtml": "php",
        
        # Ruby 相关
        ".rb": "ruby",
        ".rbw": "ruby",
        
        # Swift 相关
        ".swift": "swift",
        
        # Shell 脚本相关
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "zsh",
        ".fish": "fish",
        ".ps1": "powershell",
        ".psm1": "powershell",
        ".psd1": "powershell",
        
        # 数据库相关
        ".sql": "sql",
        
        # Web 相关
        ".html": "html",
        ".htm": "html",
        ".xhtml": "html",
        ".css": "css",
        ".scss": "scss",
        ".sass": "sass",
        ".less": "less",
        ".vue": "vue",
        ".svelte": "svelte",
        
        # 配置文件相关
        ".json": "json",
        ".xml": "xml",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".ini": "ini",
        ".cfg": "ini",
        ".conf": "ini",
        
        # 其他语言
        ".r": "r",
        ".R": "r",
        ".m": "matlab",
        ".tex": "latex",
        ".dart": "dart",
        ".lua": "lua",
        ".perl": "perl",
        ".pl": "perl",
        ".pm": "perl",
        ".vim": "vim",
        
        # 构建和配置文件
        ".dockerfile": "dockerfile",
        ".makefile": "makefile",
        ".cmake": "cmake",
        ".gradle": "gradle",
        ".groovy": "groovy",
        
        # 文档相关
        ".md": "markdown",
        ".markdown": "markdown",
        ".rst": "rst",
        ".adoc": "asciidoc",
        ".asciidoc": "asciidoc"
    }
    
    @staticmethod
    def is_code_file(file_path: str) -> bool:
        """
        检查文件是否为代码文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            如果是代码文件返回 True，否则返回 False
        """
        if not file_path:
            return False
        
        extension = os.path.splitext(file_path)[1].lower()
        
        # 检查是否在支持的扩展名列表中
        if extension in CodeFileDetector.CODE_EXTENSIONS:
            return True
        
        # 检查特殊文件名（无扩展名的配置文件等）
        file_name = os.path.basename(file_path).lower()
        special_files = [
            "dockerfile", "makefile", "rakefile", "gemfile", "podfile",
            "vagrantfile", "gulpfile", "gruntfile", "webpack.config",
            "rollup.config", "vite.config", "jest.config", "babel.config",
            "eslint.config", "prettier.config", "tsconfig", "jsconfig"
        ]
        
        return any(special in file_name for special in special_files)
    
    @staticmethod
    def get_language_type(file_path: str) -> Optional[str]:
        """
        获取文件的编程语言类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            编程语言类型，如果不是代码文件返回 None
        """
        if not file_path:
            return None
        
        extension = os.path.splitext(file_path)[1].lower()
        
        if extension in CodeFileDetector.CODE_EXTENSIONS:
            return CodeFileDetector.CODE_EXTENSIONS[extension]
        
        # 检查特殊文件名
        file_name = os.path.basename(file_path).lower()
        
        if "dockerfile" in file_name:
            return "dockerfile"
        if "makefile" in file_name:
            return "makefile"
        if "rakefile" in file_name:
            return "ruby"
        if "gemfile" in file_name:
            return "ruby"
        if "podfile" in file_name:
            return "ruby"
        if "vagrantfile" in file_name:
            return "ruby"
        if "gulpfile" in file_name or "gruntfile" in file_name:
            return "javascript"
        if any(config in file_name for config in [
            "webpack.config", "rollup.config", "vite.config", "jest.config",
            "babel.config", "eslint.config", "prettier.config"
        ]):
            return "javascript"
        if "tsconfig" in file_name or "jsconfig" in file_name:
            return "json"
        
        return None
    
    @staticmethod
    def get_supported_extensions() -> List[str]:
        """
        获取所有支持的代码文件扩展名
        
        Returns:
            支持的扩展名列表
        """
        return list(CodeFileDetector.CODE_EXTENSIONS.keys())
    
    @staticmethod
    def get_supported_languages() -> List[str]:
        """
        获取所有支持的编程语言类型
        
        Returns:
            支持的语言类型列表
        """
        return list(set(CodeFileDetector.CODE_EXTENSIONS.values()))
    
    @staticmethod
    def requires_special_handling(file_path: str) -> bool:
        """
        检查是否为需要特殊处理的代码文件类型
        这些文件类型在压缩时需要特别小心保留结构
        
        Args:
            file_path: 文件路径
            
        Returns:
            如果需要特殊处理返回 True
        """
        language = CodeFileDetector.get_language_type(file_path)
        
        # 这些语言对缩进和格式敏感，需要特殊处理
        sensitive_languages = ["python", "yaml", "yml", "makefile", "dockerfile"]
        
        return language is not None and language in sensitive_languages 