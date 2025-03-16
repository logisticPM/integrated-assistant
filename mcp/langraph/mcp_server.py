#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基于 langraph 的 MCP 服务器
提供 MCP 服务功能
"""

import os
import sys
import logging
import time
import json
import asyncio
import threading
from typing import Dict, Any, List, Optional, Union, Callable
from pydantic import BaseModel, Field

from mcp.langraph.core import MCPComponent, MCPState, MCPGraph
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
logger = logging.getLogger("langraph.mcp_server")

class MCPServerState(MCPState):
    """MCP 服务器状态"""
    request_id: Optional[str] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

class MCPServerComponent(MCPComponent):
    """MCP 服务器组件"""
    
    def __init__(
        self,
        name: str = "mcp_server",
        config: Dict[str, Any] = None,
        transcription_service: Optional[TranscriptionService] = None,
        llm_service: Optional[LLMService] = None,
        vector_service: Optional[VectorService] = None,
        tool_service: Optional[ToolService] = None,
        agent_service_graph: Optional[AgentServiceGraph] = None,
        meeting_service_graph: Optional[MeetingServiceGraph] = None
    ):
        """
        初始化 MCP 服务器组件
        
        Args:
            name: 组件名称
            config: 配置
            transcription_service: 转录服务
            llm_service: LLM 服务
            vector_service: 向量服务
            tool_service: 工具服务
            agent_service_graph: 代理服务图
            meeting_service_graph: 会议服务图
        """
        super().__init__(
            name=name,
            description="MCP 服务器组件"
        )
        
        self.config = config or {}
        self.transcription_service = transcription_service
        self.llm_service = llm_service
        self.vector_service = vector_service
        self.tool_service = tool_service
        self.agent_service_graph = agent_service_graph
        self.meeting_service_graph = meeting_service_graph
        
        # 注册方法处理函数
        self.method_handlers = {
            "transcribe": self._handle_transcribe,
            "chat": self._handle_chat,
            "search": self._handle_search,
            "execute_tool": self._handle_execute_tool,
            "process_meeting": self._handle_process_meeting,
            "search_meetings": self._handle_search_meetings
        }
    
    def to_runnable(self) -> Callable:
        """转换为可运行组件"""
        def _run(state: MCPServerState, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            if not state.method:
                raise ValueError("状态中缺少 method 字段")
            
            if state.method not in self.method_handlers:
                return {
                    "error": {
                        "code": -32601,
                        "message": f"方法不存在: {state.method}"
                    }
                }
            
            try:
                handler = self.method_handlers[state.method]
                result = handler(state.params or {})
                
                return {
                    "result": result
                }
            
            except Exception as e:
                logger.error(f"处理方法 {state.method} 失败: {str(e)}")
                
                return {
                    "error": {
                        "code": -32603,
                        "message": f"内部错误: {str(e)}"
                    }
                }
        
        return _run
    
    def _handle_transcribe(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理转录请求
        
        Args:
            params: 请求参数
        
        Returns:
            处理结果
        """
        if not self.transcription_service:
            raise RuntimeError("转录服务不可用")
        
        audio_path = params.get("audio_path")
        if not audio_path:
            raise ValueError("缺少 audio_path 参数")
        
        # 转录音频
        result = self.transcription_service.transcribe(audio_path)
        
        return result
    
    def _handle_chat(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理聊天请求
        
        Args:
            params: 请求参数
        
        Returns:
            处理结果
        """
        if not self.agent_service_graph:
            raise RuntimeError("代理服务不可用")
        
        input_text = params.get("input")
        if not input_text:
            raise ValueError("缺少 input 参数")
        
        agent_type = params.get("agent_type", "simple")
        history = params.get("history", [])
        
        # 处理输入
        result = self.agent_service_graph.process_input(input_text, agent_type, history)
        
        return result
    
    def _handle_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理搜索请求
        
        Args:
            params: 请求参数
        
        Returns:
            处理结果
        """
        if not self.vector_service:
            raise RuntimeError("向量服务不可用")
        
        query = params.get("query")
        if not query:
            raise ValueError("缺少 query 参数")
        
        k = params.get("k", 5)
        
        # 搜索向量存储
        results = self.vector_service.search(query, k=k)
        
        return {
            "results": results
        }
    
    def _handle_execute_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理执行工具请求
        
        Args:
            params: 请求参数
        
        Returns:
            处理结果
        """
        if not self.tool_service:
            raise RuntimeError("工具服务不可用")
        
        tool_name = params.get("tool_name")
        if not tool_name:
            raise ValueError("缺少 tool_name 参数")
        
        action = params.get("action")
        if not action:
            raise ValueError("缺少 action 参数")
        
        parameters = params.get("parameters", {})
        
        # 执行工具
        result = self.tool_service.execute_tool(tool_name, action, parameters)
        
        return result
    
    def _handle_process_meeting(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理会议请求
        
        Args:
            params: 请求参数
        
        Returns:
            处理结果
        """
        if not self.meeting_service_graph:
            raise RuntimeError("会议服务不可用")
        
        audio_path = params.get("audio_path")
        if not audio_path:
            raise ValueError("缺少 audio_path 参数")
        
        meeting_id = params.get("meeting_id")
        
        # 处理会议
        result = self.meeting_service_graph.process_meeting(audio_path, meeting_id)
        
        return result
    
    def _handle_search_meetings(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理搜索会议请求
        
        Args:
            params: 请求参数
        
        Returns:
            处理结果
        """
        if not self.meeting_service_graph:
            raise RuntimeError("会议服务不可用")
        
        query = params.get("query")
        if not query:
            raise ValueError("缺少 query 参数")
        
        k = params.get("k", 5)
        
        # 搜索会议
        results = self.meeting_service_graph.search_meetings(query, k=k)
        
        return {
            "results": results
        }

class MCPServer:
    """MCP 服务器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 MCP 服务器
        
        Args:
            config: 配置
        """
        self.config = config
        
        # 创建服务
        self.transcription_service = TranscriptionService(config)
        self.llm_service = LLMService(config)
        self.vector_service = VectorService(config)
        self.tool_service = ToolService(config)
        
        # 创建服务图
        self.agent_service_graph = AgentServiceGraph(config)
        self.meeting_service_graph = MeetingServiceGraph(config)
        
        # 创建 MCP 服务器组件
        self.server_component = MCPServerComponent(
            config=config,
            transcription_service=self.transcription_service,
            llm_service=self.llm_service,
            vector_service=self.vector_service,
            tool_service=self.tool_service,
            agent_service_graph=self.agent_service_graph,
            meeting_service_graph=self.meeting_service_graph
        )
        
        # 创建 MCP 服务器图
        self.graph = MCPGraph("mcp_server_graph", "MCP 服务器图")
        self.graph.add_component(self.server_component)
        
        # 请求队列和响应字典
        self.request_queue = asyncio.Queue()
        self.response_dict = {}
        self.response_dict_lock = threading.Lock()
        
        # 处理线程
        self.processing_thread = None
        self.running = False
    
    def start(self):
        """启动 MCP 服务器"""
        if self.running:
            logger.warning("MCP 服务器已经在运行")
            return
        
        self.running = True
        self.processing_thread = threading.Thread(target=self._process_requests)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        logger.info("MCP 服务器已启动")
    
    def stop(self):
        """停止 MCP 服务器"""
        if not self.running:
            logger.warning("MCP 服务器未在运行")
            return
        
        self.running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        
        logger.info("MCP 服务器已停止")
    
    def _process_requests(self):
        """处理请求线程"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while self.running:
            try:
                # 获取请求
                request = loop.run_until_complete(self.request_queue.get())
                
                # 解析请求
                request_id = request.get("id")
                method = request.get("method")
                params = request.get("params", {})
                
                # 创建状态
                state = MCPServerState(
                    request_id=request_id,
                    method=method,
                    params=params
                )
                
                # 处理请求
                logger.info(f"处理请求: {method} (ID: {request_id})")
                result = self.server_component.to_runnable()(state)
                
                # 构建响应
                response = {
                    "id": request_id,
                    "jsonrpc": "2.0"
                }
                
                if "result" in result:
                    response["result"] = result["result"]
                elif "error" in result:
                    response["error"] = result["error"]
                
                # 保存响应
                with self.response_dict_lock:
                    self.response_dict[request_id] = response
                
                logger.info(f"请求处理完成: {method} (ID: {request_id})")
            
            except Exception as e:
                logger.error(f"处理请求失败: {str(e)}")
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理请求
        
        Args:
            request: 请求
        
        Returns:
            响应
        """
        # 验证请求
        if "jsonrpc" not in request or request["jsonrpc"] != "2.0":
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "无效的请求"
                },
                "id": request.get("id")
            }
        
        if "method" not in request:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "缺少方法"
                },
                "id": request.get("id")
            }
        
        request_id = request.get("id")
        if not request_id:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "缺少 ID"
                },
                "id": None
            }
        
        # 添加请求到队列
        await self.request_queue.put(request)
        
        # 等待响应
        while True:
            with self.response_dict_lock:
                if request_id in self.response_dict:
                    response = self.response_dict.pop(request_id)
                    return response
            
            await asyncio.sleep(0.1)
    
    def handle_request_sync(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        同步处理请求
        
        Args:
            request: 请求
        
        Returns:
            响应
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.handle_request(request))

# 创建 MCP 服务器实例
def create_mcp_server(config: Dict[str, Any]) -> MCPServer:
    """
    创建 MCP 服务器实例
    
    Args:
        config: 配置
    
    Returns:
        MCP 服务器实例
    """
    server = MCPServer(config)
    server.start()
    
    return server
