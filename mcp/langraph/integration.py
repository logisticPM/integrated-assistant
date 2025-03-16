#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Langraph 架构与现有 MCP 服务器的集成
提供无缝集成功能
"""

import os
import sys
import logging
import time
import json
import yaml
import importlib
from typing import Dict, Any, List, Optional, Union, Callable

from mcp.langraph.mcp_server import MCPServer, create_mcp_server
from mcp.langraph.transcription import TranscriptionService
from mcp.langraph.llm_adapter import LLMService
from mcp.langraph.vector_service import VectorService
from mcp.langraph.tool_service import ToolService
from mcp.langraph.agent_service import AgentServiceGraph
from mcp.langraph.meeting_service import MeetingServiceGraph

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("langraph.integration")

class LangraphIntegration:
    """Langraph 集成类"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化 Langraph 集成
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.mcp_server = None
        self.original_handlers = {}
        self.integrated = False
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """
        加载配置
        
        Args:
            config_path: 配置文件路径
        
        Returns:
            配置
        """
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            logger.info(f"已加载配置: {config_path}")
            return config
        
        except Exception as e:
            logger.error(f"加载配置失败: {str(e)}")
            return {}
    
    def initialize(self) -> bool:
        """
        初始化 Langraph 集成
        
        Returns:
            是否成功初始化
        """
        try:
            # 创建 MCP 服务器
            self.mcp_server = create_mcp_server(self.config)
            
            logger.info("Langraph 集成初始化成功")
            return True
        
        except Exception as e:
            logger.error(f"Langraph 集成初始化失败: {str(e)}")
            return False
    
    def integrate_with_server(self, server_module_path: str = "mcp.server") -> bool:
        """
        与现有 MCP 服务器集成
        
        Args:
            server_module_path: 服务器模块路径
        
        Returns:
            是否成功集成
        """
        if self.integrated:
            logger.warning("已经与 MCP 服务器集成")
            return True
        
        if not self.mcp_server:
            logger.error("Langraph 集成未初始化")
            return False
        
        try:
            # 导入服务器模块
            server_module = importlib.import_module(server_module_path)
            
            # 获取 JSON-RPC 处理程序
            if hasattr(server_module, "JsonRpcHandler"):
                handler_class = server_module.JsonRpcHandler
                
                # 保存原始处理方法
                self.original_handlers = {
                    "transcribe": handler_class.transcribe if hasattr(handler_class, "transcribe") else None,
                    "chat": handler_class.chat if hasattr(handler_class, "chat") else None,
                    "search": handler_class.search if hasattr(handler_class, "search") else None,
                    "execute_tool": handler_class.execute_tool if hasattr(handler_class, "execute_tool") else None,
                    "process_meeting": handler_class.process_meeting if hasattr(handler_class, "process_meeting") else None,
                    "search_meetings": handler_class.search_meetings if hasattr(handler_class, "search_meetings") else None
                }
                
                # 替换处理方法
                self._patch_handler(handler_class, "transcribe", self._handle_transcribe)
                self._patch_handler(handler_class, "chat", self._handle_chat)
                self._patch_handler(handler_class, "search", self._handle_search)
                self._patch_handler(handler_class, "execute_tool", self._handle_execute_tool)
                self._patch_handler(handler_class, "process_meeting", self._handle_process_meeting)
                self._patch_handler(handler_class, "search_meetings", self._handle_search_meetings)
                
                self.integrated = True
                logger.info("已成功与 MCP 服务器集成")
                return True
            
            else:
                logger.error(f"服务器模块 {server_module_path} 中未找到 JsonRpcHandler 类")
                return False
        
        except Exception as e:
            logger.error(f"与 MCP 服务器集成失败: {str(e)}")
            return False
    
    def _patch_handler(self, handler_class, method_name: str, new_handler: Callable) -> bool:
        """
        修补处理程序
        
        Args:
            handler_class: 处理程序类
            method_name: 方法名称
            new_handler: 新处理程序
        
        Returns:
            是否成功修补
        """
        try:
            if hasattr(handler_class, method_name):
                setattr(handler_class, method_name, new_handler)
                logger.info(f"已修补处理程序: {method_name}")
                return True
            
            else:
                logger.warning(f"处理程序类中未找到方法: {method_name}")
                return False
        
        except Exception as e:
            logger.error(f"修补处理程序失败: {str(e)}")
            return False
    
    def restore_original_handlers(self, server_module_path: str = "mcp.server") -> bool:
        """
        恢复原始处理程序
        
        Args:
            server_module_path: 服务器模块路径
        
        Returns:
            是否成功恢复
        """
        if not self.integrated:
            logger.warning("未与 MCP 服务器集成")
            return True
        
        try:
            # 导入服务器模块
            server_module = importlib.import_module(server_module_path)
            
            # 获取 JSON-RPC 处理程序
            if hasattr(server_module, "JsonRpcHandler"):
                handler_class = server_module.JsonRpcHandler
                
                # 恢复原始处理方法
                for method_name, handler in self.original_handlers.items():
                    if handler:
                        setattr(handler_class, method_name, handler)
                        logger.info(f"已恢复原始处理程序: {method_name}")
                
                self.integrated = False
                logger.info("已成功恢复原始处理程序")
                return True
            
            else:
                logger.error(f"服务器模块 {server_module_path} 中未找到 JsonRpcHandler 类")
                return False
        
        except Exception as e:
            logger.error(f"恢复原始处理程序失败: {str(e)}")
            return False
    
    def _handle_transcribe(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理转录请求
        
        Args:
            params: 请求参数
        
        Returns:
            处理结果
        """
        try:
            # 使用 Langraph MCP 服务器处理请求
            request = {
                "jsonrpc": "2.0",
                "method": "transcribe",
                "params": params,
                "id": str(time.time())
            }
            
            response = self.mcp_server.handle_request_sync(request)
            
            if "result" in response:
                return response["result"]
            
            elif "error" in response:
                logger.error(f"处理转录请求失败: {response['error']}")
                raise Exception(response["error"]["message"])
            
            else:
                logger.error("处理转录请求失败: 未知错误")
                raise Exception("未知错误")
        
        except Exception as e:
            logger.error(f"处理转录请求失败: {str(e)}")
            
            # 回退到原始处理程序
            if "transcribe" in self.original_handlers and self.original_handlers["transcribe"]:
                logger.info("回退到原始转录处理程序")
                return self.original_handlers["transcribe"](params)
            
            raise
    
    def _handle_chat(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理聊天请求
        
        Args:
            params: 请求参数
        
        Returns:
            处理结果
        """
        try:
            # 使用 Langraph MCP 服务器处理请求
            request = {
                "jsonrpc": "2.0",
                "method": "chat",
                "params": params,
                "id": str(time.time())
            }
            
            response = self.mcp_server.handle_request_sync(request)
            
            if "result" in response:
                return response["result"]
            
            elif "error" in response:
                logger.error(f"处理聊天请求失败: {response['error']}")
                raise Exception(response["error"]["message"])
            
            else:
                logger.error("处理聊天请求失败: 未知错误")
                raise Exception("未知错误")
        
        except Exception as e:
            logger.error(f"处理聊天请求失败: {str(e)}")
            
            # 回退到原始处理程序
            if "chat" in self.original_handlers and self.original_handlers["chat"]:
                logger.info("回退到原始聊天处理程序")
                return self.original_handlers["chat"](params)
            
            raise
    
    def _handle_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理搜索请求
        
        Args:
            params: 请求参数
        
        Returns:
            处理结果
        """
        try:
            # 使用 Langraph MCP 服务器处理请求
            request = {
                "jsonrpc": "2.0",
                "method": "search",
                "params": params,
                "id": str(time.time())
            }
            
            response = self.mcp_server.handle_request_sync(request)
            
            if "result" in response:
                return response["result"]
            
            elif "error" in response:
                logger.error(f"处理搜索请求失败: {response['error']}")
                raise Exception(response["error"]["message"])
            
            else:
                logger.error("处理搜索请求失败: 未知错误")
                raise Exception("未知错误")
        
        except Exception as e:
            logger.error(f"处理搜索请求失败: {str(e)}")
            
            # 回退到原始处理程序
            if "search" in self.original_handlers and self.original_handlers["search"]:
                logger.info("回退到原始搜索处理程序")
                return self.original_handlers["search"](params)
            
            raise
    
    def _handle_execute_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理执行工具请求
        
        Args:
            params: 请求参数
        
        Returns:
            处理结果
        """
        try:
            # 使用 Langraph MCP 服务器处理请求
            request = {
                "jsonrpc": "2.0",
                "method": "execute_tool",
                "params": params,
                "id": str(time.time())
            }
            
            response = self.mcp_server.handle_request_sync(request)
            
            if "result" in response:
                return response["result"]
            
            elif "error" in response:
                logger.error(f"处理执行工具请求失败: {response['error']}")
                raise Exception(response["error"]["message"])
            
            else:
                logger.error("处理执行工具请求失败: 未知错误")
                raise Exception("未知错误")
        
        except Exception as e:
            logger.error(f"处理执行工具请求失败: {str(e)}")
            
            # 回退到原始处理程序
            if "execute_tool" in self.original_handlers and self.original_handlers["execute_tool"]:
                logger.info("回退到原始执行工具处理程序")
                return self.original_handlers["execute_tool"](params)
            
            raise
    
    def _handle_process_meeting(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理会议请求
        
        Args:
            params: 请求参数
        
        Returns:
            处理结果
        """
        try:
            # 使用 Langraph MCP 服务器处理请求
            request = {
                "jsonrpc": "2.0",
                "method": "process_meeting",
                "params": params,
                "id": str(time.time())
            }
            
            response = self.mcp_server.handle_request_sync(request)
            
            if "result" in response:
                return response["result"]
            
            elif "error" in response:
                logger.error(f"处理会议请求失败: {response['error']}")
                raise Exception(response["error"]["message"])
            
            else:
                logger.error("处理会议请求失败: 未知错误")
                raise Exception("未知错误")
        
        except Exception as e:
            logger.error(f"处理会议请求失败: {str(e)}")
            
            # 回退到原始处理程序
            if "process_meeting" in self.original_handlers and self.original_handlers["process_meeting"]:
                logger.info("回退到原始会议处理程序")
                return self.original_handlers["process_meeting"](params)
            
            raise
    
    def _handle_search_meetings(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理搜索会议请求
        
        Args:
            params: 请求参数
        
        Returns:
            处理结果
        """
        try:
            # 使用 Langraph MCP 服务器处理请求
            request = {
                "jsonrpc": "2.0",
                "method": "search_meetings",
                "params": params,
                "id": str(time.time())
            }
            
            response = self.mcp_server.handle_request_sync(request)
            
            if "result" in response:
                return response["result"]
            
            elif "error" in response:
                logger.error(f"处理搜索会议请求失败: {response['error']}")
                raise Exception(response["error"]["message"])
            
            else:
                logger.error("处理搜索会议请求失败: 未知错误")
                raise Exception("未知错误")
        
        except Exception as e:
            logger.error(f"处理搜索会议请求失败: {str(e)}")
            
            # 回退到原始处理程序
            if "search_meetings" in self.original_handlers and self.original_handlers["search_meetings"]:
                logger.info("回退到原始搜索会议处理程序")
                return self.original_handlers["search_meetings"](params)
            
            raise

# 创建 Langraph 集成实例
def create_langraph_integration(config_path: str = "config.yaml") -> LangraphIntegration:
    """
    创建 Langraph 集成实例
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        Langraph 集成实例
    """
    integration = LangraphIntegration(config_path)
    integration.initialize()
    
    return integration
