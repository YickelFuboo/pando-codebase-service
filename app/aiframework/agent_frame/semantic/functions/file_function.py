import os
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from semantic_kernel.functions import kernel_function
from app.aiframework.agent_frame.semantic.functions.code_compress.code_file_detector import CodeFileDetector
from app.aiframework.agent_frame.semantic.functions.code_compress.code_compression import CodeCompressionService
from app.config.settings import settings  
from app.services.task_context.document_context import DocumentContextManager
from app.services.common.local_repo_service import LocalRepoService
from app.services.common.file_tree_service import FileTreeService


@dataclass
class ReadFileItemInput:
    """文件读取项输入类"""
    file_path: str
    offset: int = 0
    limit: int = 200

# 文件操作函数
class FileFunction:
    """文件操作函数类，提供AI内核与本地文件系统交互的功能"""
    
    def __init__(self, git_local_path: str):
        """
        初始化文件操作函数
        
        Args:
            git_local_path: Git仓库的本地路径
        """
        self.git_local_path = os.path.normpath(git_local_path)
        self._code_compression_service = CodeCompressionService()  # 代码压缩服务
    
    def _normalize_file_path(self, file_path: str) -> tuple[str, str]:
        """
        规范化文件路径
        
        Args:
            file_path: 原始文件路径
            
        Returns:
            (normalized_path, full_path): 规范化后的相对路径和完整路径
        """
        # 规范化路径：移除开头的 / 和 ./
        normalized_path = file_path.lstrip('/').lstrip('./').replace('\\', '/')
        # 构建完整路径并规范化（处理 .. 和 . 等相对路径）
        full_path = os.path.normpath(os.path.join(self.git_local_path, normalized_path))
        
        # 安全检查：确保路径在 git_local_path 内（防止路径遍历攻击）
        git_local_path_normalized = os.path.normpath(self.git_local_path)
        if not full_path.startswith(git_local_path_normalized):
            raise ValueError(f"Access denied: Path {file_path} is outside the repository root")
        
        return normalized_path, full_path
    
    def get_tree(self) -> str:
        """
        获取当前仓库的压缩目录结构
        
        Returns:
            压缩后的目录结构字符串
        """
        try:
            # 步骤1：获取忽略文件列表
            ignore_files = LocalRepoService.get_ignore_files(self.git_local_path)
            path_infos = []
            
            # 步骤2：递归扫描目录
            LocalRepoService.scan_directory(self.git_local_path, path_infos, ignore_files)
            
            # 步骤3：构建文件树
            file_tree = FileTreeService.build_tree(path_infos, self.git_local_path)
            
            # 步骤4：转换为压缩字符串
            return FileTreeService.to_compact_string(file_tree)
            
        except Exception as e:
            logging.error(f"获取目录结构失败: {e}")
            return f"获取目录结构失败: {str(e)}"
    
    @kernel_function(
        name="FileInfo",
        description="""Before accessing or reading any file content, always use this method to retrieve the basic information for all specified files. Batch as many file paths as possible into a single call to maximize efficiency. Provide file paths as an array. The function returns a JSON object where each key is the file path and each value contains the file's name, size, extension, creation time, last write time, and last access time. Ensure this information is obtained and reviewed before proceeding to any file content operations.
        
        Returns: 
        Return a JSON object with file paths as keys and file information as values. The information includes file name, size, extension, creation time, last write time, and last access time.
        
        Parameters:
        - file_paths (array): file path array"""
    )
    def get_file_info_async(self, file_paths: List[str]) -> str:
        """
        获取文件基本信息
        
        Args:
            file_paths: 文件路径数组
            
        Returns:
            JSON格式的文件信息
        """
        try:
            # 步骤1：初始化结果字典
            result_dict = {}
            
            # 步骤2：去重处理
            file_paths = list(set(file_paths))

            # 记录到上下文
            DocumentContextManager.add_files(file_paths)
            
            # 步骤4：批量处理文件信息
            for file_path in file_paths:
                try:
                    _, full_path = self._normalize_file_path(file_path)
                except ValueError as e:
                    result_dict[file_path] = str(e)
                    continue
                
                if not os.path.exists(full_path):
                    result_dict[file_path] = "File not found"
                    continue
                
                # 检查是否为文件
                if not os.path.isfile(full_path):
                    if os.path.isdir(full_path):
                        result_dict[file_path] = f"Error: {file_path} is a directory, not a file"
                    else:
                        result_dict[file_path] = f"Error: {file_path} is not a valid file path"
                    continue
                
                try:
                    stat = os.stat(full_path)
                    # 文件大小
                    file_size = stat.st_size
                    # 文件名
                    file_name = os.path.basename(full_path)
                    # 文件扩展名
                    file_ext = os.path.splitext(file_name)[1]
                    
                    # 获取文件行数（优化版本）
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            total_lines = sum(1 for _ in f)  # 逐行计数，不加载整个文件到内存
                    except Exception:
                        total_lines = 0  # 如果无法读取行数，设为0
                    
                    file_info = {
                        "name": file_name,
                        "length": file_size,
                        "extension": file_ext,
                        "total_line": total_lines,
                    }
                    
                    result_dict[file_path] = json.dumps(file_info, ensure_ascii=False)
                    
                except Exception as e:
                    result_dict[file_path] = f"Error reading file: {str(e)}"
            
            return json.dumps(result_dict, ensure_ascii=False)
            
        except Exception as e:
            logging.error(f"Error getting file info: {e}")
            return f"Error getting file info: {str(e)}"
    
    @kernel_function(
        name="ReadFiles",
        description="File Path array. Always batch multiple file paths to reduce the number of function calls. "
                   "Parameters: "
                   "- file_paths (array): file path array"
    )
    async def read_files_async(self, file_paths: List[str]) -> str:
        """
        批量读取文件内容
        """
        try:
            # 步骤1：去重处理
            file_paths = list(set(file_paths))

            # 记录到上下文
            DocumentContextManager.add_files(file_paths)
            
            # 步骤2：批量读取文件内容
            result_dict = {}
            
            for file_path in file_paths:
                try:
                    _, full_path = self._normalize_file_path(file_path)
                except ValueError:
                    continue
                
                if not os.path.exists(full_path):
                    continue
                
                # 检查是否为文件
                if not os.path.isfile(full_path):
                    continue
                
                try:
                    stat = os.stat(full_path)
                    
                    # 大文件处理
                    if stat.st_size > 1024 * 100:
                        result_dict[file_path] = "If the file exceeds 100KB, you should use ReadFileFromLineAsync to read the file content line by line"
                    else:
                        # 读取文件内容
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        # 代码压缩处理
                        if settings.enable_code_compression and CodeFileDetector.is_code_file(file_path):
                            content = self._code_compression_service.compress_code(content, file_path)
                        
                        result_dict[file_path] = content
                        
                except Exception as e:
                    result_dict[file_path] = f"Error reading file: {str(e)}"
            
            return json.dumps(result_dict, ensure_ascii=False)
            
        except Exception as e:
            logging.error(f"Error reading files: {e}")
            return f"Error reading files: {str(e)}"
    
    @kernel_function(
        name="ReadFile",
        description="Read a single file from the local filesystem. "
                   "Parameters: "
                   "- file_path (string): file path"
    )
    async def read_file_async(self, file_path: str) -> str:
        """
        读取单个文件内容
        """
        try:         
            # 记录到上下文
            DocumentContextManager.add_file(file_path)

            try:
                _, full_path = self._normalize_file_path(file_path)
            except ValueError as e:
                return str(e)
            
            if not os.path.exists(full_path):
                return f"File not found: {file_path}"
            
            # 检查是否为文件
            if not os.path.isfile(full_path):
                if os.path.isdir(full_path):
                    return f"Error: {file_path} is a directory, not a file. Please specify a file path."
                else:
                    return f"Error: {file_path} is not a valid file path."
            
            stat = os.stat(full_path)
            
            # 大文件检测
            if stat.st_size > 1024 * 100:
                return f"File too large: {file_path} ({stat.st_size // 1024 // 100}KB)"
            
            # 读取文件内容
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 代码压缩处理
            if settings.enable_code_compression and CodeFileDetector.is_code_file(file_path):
                content = self._code_compression_service.compress_code(content, file_path)
            
            return content
            
        except Exception as e:
            logging.error(f"Error reading file: {e}")
            return f"Error reading file: {str(e)}"
    
    @kernel_function(
        name="File",
        description="Reads a file from the local filesystem. You can access any file directly by using this tool.\nAssume this tool is able to read all files on the machine. If the User provides a path to a file assume that path is valid. It is okay to read a file that does not exist; an error will be returned.\n\nUsage:\n- The file_path parameter must be an absolute path, not a relative path\n- By default, it reads up to 2000 lines starting from the beginning of the file\n- You can optionally specify a line offset and limit (especially handy for long files), but it's recommended to read the whole file by not providing these parameters\n- Any lines longer than 2000 characters will be truncated\n- Results are returned using cat -n format, with line numbers starting at 1\n- This tool allows Claude Code to read images (eg PNG, JPG, etc). When reading an image file the contents are presented visually as Claude Code is a multimodal LLM.\n- For Jupyter notebooks (.ipynb files), use the NotebookRead instead\n- You have the capability to call multiple tools in a single response. It is always better to speculatively read multiple files as a batch that are potentially useful. \n- You will regularly be asked to read screenshots. If the user provides a path to a screenshot ALWAYS use this tool to view the file at the path. This tool will work with all temporary file paths like /var/folders/123/abc/T/TemporaryItems/NSIRD_screencaptureui_ZfB1tD/Screenshot.png\n- If you read a file that exists but has empty contents you will receive a system reminder warning in place of file contents. "
                   "Parameters: "
                   "- items (array): file path array"
    )
    async def read_file_from_line_async(self, items: List[ReadFileItemInput]) -> str:
        """
        从指定行读取文件内容
        
        Args:
            items: 读取文件项输入列表
            
        Returns:
            JSON格式的读取结果
        """
        try:
            result_dict = {}
            
            for item in items:
                result_key = f"fileName:{item.file_path}\nstartLine:{item.offset}\nendLine:{item.limit}"
                result_dict[result_key] = await self._read_item(item.file_path, item.offset, item.limit)
            
            return json.dumps(result_dict, ensure_ascii=False)
            
        except Exception as e:
            logging.error(f"Error reading files from line: {e}")
            return f"Error reading files from line: {str(e)}"
    
    async def _read_item(self, file_path: str, offset: int = 0, limit: int = 200) -> str:
        """
        读取单个文件的指定行范围内容
        
        Args:
            file_path: 文件路径
            offset: 开始读取的行号
            limit: 要读取的行数
            
        Returns:
            带行号的文件内容字符串
        """
        try:
            try:
                _, full_path = self._normalize_file_path(file_path)
            except ValueError as e:
                return str(e)
            
            if not os.path.exists(full_path):
                return f"File not found: {file_path}"
            
            # 检查是否为文件
            if not os.path.isfile(full_path):
                if os.path.isdir(full_path):
                    return f"Error: {file_path} is a directory, not a file. Please specify a file path."
                else:
                    return f"Error: {file_path} is not a valid file path."
            
            # 特殊参数处理
            if offset < 0 and limit < 0:
                return await self.read_file_async(file_path)
            
            if limit < 0:
                limit = float('inf')
            
            # 读取文件内容
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                file_content = f.read()
            
            # 代码压缩处理
            if settings.enable_code_compression and CodeFileDetector.is_code_file(file_path):
                file_content = self._compress_code(file_content, file_path)
            
            # 按行分割内容
            lines = file_content.split('\n')
            
            # 边界检查
            if offset >= len(lines):
                return f"No content to read from line {offset} in file: {file_path}"
            
            # 计算实际读取范围
            actual_limit = min(limit, len(lines) - offset)
            
            # 读取指定行范围
            result_lines = []
            for i in range(offset, min(offset + actual_limit, len(lines))):
                line = lines[i]
                # 行长度限制
                if len(line) > 2000:
                    line = line[:2000]
                result_lines.append(line)
            
            # 添加行号
            numbered_lines = [f"{i + 1}: {line}" for i, line in enumerate(result_lines)]
            
            return '\n'.join(numbered_lines)
            
        except Exception as e:
            logging.error(f"Error reading file: {e}")
            return f"Error reading file: {str(e)}"