"""
OpenDeepWiki CodeFoundation Python版本
提供对不同编程语言的代码压缩功能，保留注释、方法名等关键信息
"""

from .code_compression import CodeCompressionService
from .code_file_detector import CodeFileDetector

__version__ = "1.0.0"
__author__ = "OpenDeepWiki Team"

__all__ = [
    'CodeCompressionService',
    'CodeFileDetector'
] 