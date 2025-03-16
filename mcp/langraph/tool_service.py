#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基于 langraph 的工具服务组件
提供各种工具功能
"""

import os
import sys
import logging
import time
import json
import subprocess
import requests
from typing import Dict, Any, List, Optional, Union, Callable
from pydantic import BaseModel, Field

from mcp.langraph.core import MCPComponent, ToolComponent, MCPState

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("langraph.tool_service")

class WebSearchTool(ToolComponent):
    """网络搜索工具"""
    
    def __init__(
        self,
        name: str = "web_search",
        api_key: Optional[str] = None,
        search_engine: str = "duckduckgo"
    ):
        """
        初始化网络搜索工具
        
        Args:
            name: 工具名称
            api_key: API 密钥
            search_engine: 搜索引擎
        """
        super().__init__(
            name=name,
            description="网络搜索工具，用于搜索互联网上的信息"
        )
        
        self.api_key = api_key
        self.search_engine = search_engine
    
    def is_available(self) -> bool:
        """
        检查工具是否可用
        
        Returns:
            是否可用
        """
        try:
            # 简单的网络连接测试
            requests.get("https://www.baidu.com", timeout=5)
            return True
        except Exception as e:
            logger.error(f"网络连接测试失败: {str(e)}")
            return False
    
    def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工具
        
        Args:
            action: 动作名称
            parameters: 参数
        
        Returns:
            执行结果
        """
        if action != "search":
            raise ValueError(f"不支持的动作: {action}")
        
        query = parameters.get("query")
        if not query:
            raise ValueError("缺少查询参数")
        
        try:
            logger.info(f"开始搜索: {query}")
            
            # 这里是一个模拟实现，实际应用中应该使用真实的搜索 API
            if self.search_engine == "duckduckgo":
                results = self._search_duckduckgo(query)
            else:
                results = self._mock_search(query)
            
            return {
                "success": True,
                "results": results
            }
        
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _mock_search(self, query: str) -> List[Dict[str, Any]]:
        """
        模拟搜索
        
        Args:
            query: 查询文本
        
        Returns:
            搜索结果
        """
        # 模拟处理时间
        time.sleep(1)
        
        # 返回模拟结果
        return [
            {
                "title": f"关于 '{query}' 的搜索结果 1",
                "url": "https://example.com/result1",
                "snippet": f"这是关于 '{query}' 的详细信息..."
            },
            {
                "title": f"关于 '{query}' 的搜索结果 2",
                "url": "https://example.com/result2",
                "snippet": f"更多关于 '{query}' 的信息..."
            },
            {
                "title": f"关于 '{query}' 的搜索结果 3",
                "url": "https://example.com/result3",
                "snippet": f"'{query}' 的其他相关内容..."
            }
        ]
    
    def _search_duckduckgo(self, query: str) -> List[Dict[str, Any]]:
        """
        使用 DuckDuckGo 搜索
        
        Args:
            query: 查询文本
        
        Returns:
            搜索结果
        """
        try:
            url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "no_html": 1,
                "no_redirect": 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            results = []
            
            # 处理 AbstractText
            if data.get("AbstractText"):
                results.append({
                    "title": data.get("Heading", "摘要"),
                    "url": data.get("AbstractURL", ""),
                    "snippet": data.get("AbstractText", "")
                })
            
            # 处理 RelatedTopics
            for topic in data.get("RelatedTopics", []):
                if "Text" in topic and "FirstURL" in topic:
                    results.append({
                        "title": topic.get("Text", "").split(" - ")[0] if " - " in topic.get("Text", "") else topic.get("Text", ""),
                        "url": topic.get("FirstURL", ""),
                        "snippet": topic.get("Text", "")
                    })
            
            return results
        
        except Exception as e:
            logger.error(f"DuckDuckGo 搜索失败: {str(e)}")
            # 回退到模拟搜索
            return self._mock_search(query)

class FileOperationTool(ToolComponent):
    """文件操作工具"""
    
    def __init__(
        self,
        name: str = "file_operation",
        base_dir: Optional[str] = None
    ):
        """
        初始化文件操作工具
        
        Args:
            name: 工具名称
            base_dir: 基础目录，所有操作都将限制在此目录下
        """
        super().__init__(
            name=name,
            description="文件操作工具，用于读取、写入和管理文件"
        )
        
        # 如果未指定基础目录，使用当前工作目录
        if base_dir is None:
            base_dir = os.getcwd()
        
        self.base_dir = os.path.abspath(base_dir)
        
        # 确保基础目录存在
        os.makedirs(self.base_dir, exist_ok=True)
    
    def is_available(self) -> bool:
        """
        检查工具是否可用
        
        Returns:
            是否可用
        """
        return os.path.exists(self.base_dir) and os.access(self.base_dir, os.R_OK | os.W_OK)
    
    def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工具
        
        Args:
            action: 动作名称
            parameters: 参数
        
        Returns:
            执行结果
        """
        supported_actions = ["read", "write", "list", "delete"]
        
        if action not in supported_actions:
            raise ValueError(f"不支持的动作: {action}")
        
        try:
            if action == "read":
                return self._read_file(parameters)
            elif action == "write":
                return self._write_file(parameters)
            elif action == "list":
                return self._list_files(parameters)
            elif action == "delete":
                return self._delete_file(parameters)
        
        except Exception as e:
            logger.error(f"文件操作失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _safe_path(self, path: str) -> str:
        """
        确保路径安全，不允许访问基础目录之外的文件
        
        Args:
            path: 路径
        
        Returns:
            安全的绝对路径
        
        Raises:
            ValueError: 如果路径不安全
        """
        # 获取绝对路径
        abs_path = os.path.abspath(os.path.join(self.base_dir, path))
        
        # 检查路径是否在基础目录下
        if not abs_path.startswith(self.base_dir):
            raise ValueError(f"不允许访问基础目录之外的文件: {path}")
        
        return abs_path
    
    def _read_file(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        读取文件
        
        Args:
            parameters: 参数
        
        Returns:
            执行结果
        """
        path = parameters.get("path")
        if not path:
            raise ValueError("缺少路径参数")
        
        safe_path = self._safe_path(path)
        
        if not os.path.exists(safe_path):
            return {
                "success": False,
                "error": f"文件不存在: {path}"
            }
        
        if not os.path.isfile(safe_path):
            return {
                "success": False,
                "error": f"不是文件: {path}"
            }
        
        with open(safe_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        return {
            "success": True,
            "content": content
        }
    
    def _write_file(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        写入文件
        
        Args:
            parameters: 参数
        
        Returns:
            执行结果
        """
        path = parameters.get("path")
        content = parameters.get("content")
        
        if not path:
            raise ValueError("缺少路径参数")
        
        if content is None:
            raise ValueError("缺少内容参数")
        
        safe_path = self._safe_path(path)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return {
            "success": True,
            "path": path
        }
    
    def _list_files(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        列出文件
        
        Args:
            parameters: 参数
        
        Returns:
            执行结果
        """
        path = parameters.get("path", "")
        
        safe_path = self._safe_path(path)
        
        if not os.path.exists(safe_path):
            return {
                "success": False,
                "error": f"路径不存在: {path}"
            }
        
        if not os.path.isdir(safe_path):
            return {
                "success": False,
                "error": f"不是目录: {path}"
            }
        
        files = []
        for item in os.listdir(safe_path):
            item_path = os.path.join(safe_path, item)
            files.append({
                "name": item,
                "is_dir": os.path.isdir(item_path),
                "size": os.path.getsize(item_path) if os.path.isfile(item_path) else None
            })
        
        return {
            "success": True,
            "files": files
        }
    
    def _delete_file(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        删除文件
        
        Args:
            parameters: 参数
        
        Returns:
            执行结果
        """
        path = parameters.get("path")
        if not path:
            raise ValueError("缺少路径参数")
        
        safe_path = self._safe_path(path)
        
        if not os.path.exists(safe_path):
            return {
                "success": False,
                "error": f"文件不存在: {path}"
            }
        
        if os.path.isfile(safe_path):
            os.remove(safe_path)
        else:
            import shutil
            shutil.rmtree(safe_path)
        
        return {
            "success": True,
            "path": path
        }

class ShellCommandTool(ToolComponent):
    """Shell 命令工具"""
    
    def __init__(
        self,
        name: str = "shell_command",
        allowed_commands: Optional[List[str]] = None,
        working_dir: Optional[str] = None
    ):
        """
        初始化 Shell 命令工具
        
        Args:
            name: 工具名称
            allowed_commands: 允许执行的命令列表，如果为 None 则不限制
            working_dir: 工作目录
        """
        super().__init__(
            name=name,
            description="Shell 命令工具，用于执行 Shell 命令"
        )
        
        self.allowed_commands = allowed_commands
        
        # 如果未指定工作目录，使用当前工作目录
        if working_dir is None:
            working_dir = os.getcwd()
        
        self.working_dir = os.path.abspath(working_dir)
    
    def is_available(self) -> bool:
        """
        检查工具是否可用
        
        Returns:
            是否可用
        """
        return os.path.exists(self.working_dir) and os.access(self.working_dir, os.R_OK | os.W_OK | os.X_OK)
    
    def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工具
        
        Args:
            action: 动作名称
            parameters: 参数
        
        Returns:
            执行结果
        """
        if action != "execute":
            raise ValueError(f"不支持的动作: {action}")
        
        command = parameters.get("command")
        if not command:
            raise ValueError("缺少命令参数")
        
        # 检查命令是否允许执行
        if self.allowed_commands is not None:
            command_name = command.split()[0]
            if command_name not in self.allowed_commands:
                return {
                    "success": False,
                    "error": f"不允许执行命令: {command_name}"
                }
        
        try:
            logger.info(f"执行命令: {command}")
            
            # 执行命令
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=self.working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(timeout=60)
            
            return {
                "success": process.returncode == 0,
                "exit_code": process.returncode,
                "stdout": stdout,
                "stderr": stderr
            }
        
        except subprocess.TimeoutExpired:
            logger.error(f"命令执行超时: {command}")
            return {
                "success": False,
                "error": "命令执行超时"
            }
        
        except Exception as e:
            logger.error(f"命令执行失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

class ToolService:
    """工具服务，管理多个工具组件"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化工具服务
        
        Args:
            config: 配置
        """
        self.config = config
        self.tools: Dict[str, ToolComponent] = {}
        
        # 初始化工具
        self._init_tools()
    
    def _init_tools(self):
        """初始化工具"""
        # 添加网络搜索工具
        if self.config.get("tools", {}).get("web_search", {}).get("enabled", True):
            api_key = self.config.get("tools", {}).get("web_search", {}).get("api_key")
            search_engine = self.config.get("tools", {}).get("web_search", {}).get("search_engine", "duckduckgo")
            
            tool = WebSearchTool(
                api_key=api_key,
                search_engine=search_engine
            )
            
            self.add_tool(tool)
        
        # 添加文件操作工具
        if self.config.get("tools", {}).get("file_operation", {}).get("enabled", True):
            base_dir = self.config.get("tools", {}).get("file_operation", {}).get("base_dir")
            
            tool = FileOperationTool(
                base_dir=base_dir
            )
            
            self.add_tool(tool)
        
        # 添加 Shell 命令工具
        if self.config.get("tools", {}).get("shell_command", {}).get("enabled", False):
            allowed_commands = self.config.get("tools", {}).get("shell_command", {}).get("allowed_commands")
            working_dir = self.config.get("tools", {}).get("shell_command", {}).get("working_dir")
            
            tool = ShellCommandTool(
                allowed_commands=allowed_commands,
                working_dir=working_dir
            )
            
            self.add_tool(tool)
    
    def add_tool(self, tool: ToolComponent):
        """
        添加工具
        
        Args:
            tool: 要添加的工具
        """
        self.tools[tool.name] = tool
        logger.info(f"添加工具: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[ToolComponent]:
        """
        获取工具
        
        Args:
            name: 工具名称
        
        Returns:
            工具，如果不存在则返回 None
        """
        return self.tools.get(name)
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        获取可用的工具
        
        Returns:
            可用的工具列表
        """
        available_tools = []
        
        for name, tool in self.tools.items():
            if tool.is_available():
                available_tools.append({
                    "name": name,
                    "description": tool.description
                })
        
        return available_tools
    
    def execute_tool(self, name: str, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工具
        
        Args:
            name: 工具名称
            action: 动作名称
            parameters: 参数
        
        Returns:
            执行结果
        
        Raises:
            ValueError: 如果工具不存在或不可用
        """
        tool = self.get_tool(name)
        
        if tool is None:
            raise ValueError(f"工具不存在: {name}")
        
        if not tool.is_available():
            raise ValueError(f"工具不可用: {name}")
        
        logger.info(f"执行工具 {name}.{action}")
        
        return tool.execute(action, parameters)
