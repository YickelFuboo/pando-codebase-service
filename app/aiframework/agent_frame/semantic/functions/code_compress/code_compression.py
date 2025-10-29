from typing import Dict, Optional
from .code_file_detector import CodeFileDetector
from .compressors.generic_compressor import GenericCompressor
from .compressors.python_compressor import PythonCompressor
from .compressors.javascript_compressor import JavaScriptCompressor
from .compressors.java_compressor import JavaCompressor
from .compressors.cpp_compressor import CppCompressor
from .compressors.go_compressor import GoCompressor
from .compressors.rust_compressor import RustCompressor
from .compressors.php_compressor import PhpCompressor
from .compressors.ruby_compressor import RubyCompressor
from .compressors.swift_compressor import SwiftCompressor
from .compressors.shell_compressor import ShellCompressor
from .compressors.sql_compressor import SqlCompressor
from .compressors.html_compressor import HtmlCompressor
from .compressors.css_compressor import CssCompressor
from .compressors.json_compressor import JsonCompressor
from .compressors.xml_compressor import XmlCompressor
from .compressors.yaml_compressor import YamlCompressor
from .compressors.markdown_compressor import MarkdownCompressor
from .compressors.csharp_compressor import CSharpCompressor


class CodeCompressionService:
    """代码压缩服务类"""
    
    def __init__(self):
        """初始化压缩器字典"""
        self._compressors: Dict[str, object] = {}
        self._generic_compressor = GenericCompressor()
        
        # 初始化各种语言的压缩器
        self._compressors["csharp"] = CSharpCompressor()
        self._compressors["javascript"] = JavaScriptCompressor()
        self._compressors["typescript"] = JavaScriptCompressor()
        self._compressors["python"] = PythonCompressor()
        self._compressors["java"] = JavaCompressor()
        self._compressors["kotlin"] = JavaCompressor()
        self._compressors["scala"] = JavaCompressor()
        self._compressors["c"] = CppCompressor()
        self._compressors["cpp"] = CppCompressor()
        self._compressors["go"] = GoCompressor()
        self._compressors["rust"] = RustCompressor()
        self._compressors["php"] = PhpCompressor()
        self._compressors["ruby"] = RubyCompressor()
        self._compressors["swift"] = SwiftCompressor()
        self._compressors["bash"] = ShellCompressor()
        self._compressors["zsh"] = ShellCompressor()
        self._compressors["fish"] = ShellCompressor()
        self._compressors["powershell"] = ShellCompressor()
        self._compressors["sql"] = SqlCompressor()
        self._compressors["html"] = HtmlCompressor()
        self._compressors["css"] = CssCompressor()
        self._compressors["scss"] = CssCompressor()
        self._compressors["sass"] = CssCompressor()
        self._compressors["less"] = CssCompressor()
        self._compressors["json"] = JsonCompressor()
        self._compressors["xml"] = XmlCompressor()
        self._compressors["yaml"] = YamlCompressor()
        self._compressors["yml"] = YamlCompressor()
        self._compressors["markdown"] = MarkdownCompressor()
    
    def compress_code(self, content: str, language_type: str = None, file_path: str = None) -> str:
        """
        压缩代码内容
        
        Args:
            content: 原始代码内容
            language_type: 语言类型（可选）
            file_path: 文件路径（可选，用于确定语言类型）
            
        Returns:
            压缩后的代码内容
        """
        if not content:
            return content
        
        # 确定语言类型
        if language_type is None:
            if file_path is None:
                return content  # 无法确定语言类型，不进行压缩
            language_type = CodeFileDetector.get_language_type(file_path)
            if language_type is None:
                return content  # 不是代码文件，不进行压缩
        
        if language_type in self._compressors:
            compressor = self._compressors[language_type]
            return compressor.compress(content)
        
        return self._generic_compressor.compress(content) 