#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MCP服务器 - 提供模块间通信的服务器
"""

import json
import uuid
import threading
import time
import logging
from typing import Dict, Any, Callable, List, Optional
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify

# 导入服务模块
from mcp.transcription import register_transcription_service
from mcp.llm_adapter import register_llm_service
from mcp.vector_service import register_vector_service
from mcp.email_service import register_email_service
from mcp.gmail_auth import register_gmail_auth_service
from mcp.chatbot_service import register_chatbot_service
from mcp.gmail_service import register_gmail_service
from mcp.email_analysis import register_email_analysis_service
from mcp.meeting_service import register_meeting_service

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_server")

class MCPServer:
    """MCP服务器类，处理模块间的通信"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化MCP服务器
        
        Args:
            config: 服务器配置
        """
        self.config = config
        self.methods: Dict[str, Callable] = {}
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.executor = ThreadPoolExecutor(max_workers=config["mcp"]["max_workers"])
        
        # 创建Flask应用
        self.app = Flask(__name__)
        self.setup_routes()
    
    def setup_routes(self):
        """设置Flask路由"""
        
        @self.app.route('/rpc', methods=['POST'])
        def handle_rpc():
            """处理RPC请求"""
            try:
                # 解析请求数据
                request_data = request.json
                
                # 验证请求数据
                if not request_data or not isinstance(request_data, dict):
                    return jsonify({
                        "error": {
                            "code": -32600,
                            "message": "Invalid Request"
                        }
                    }), 400
                
                request_id = request_data.get("id", str(uuid.uuid4()))
                method_name = request_data.get("method")
                params = request_data.get("params", {})
                is_async = request_data.get("async", False)
                
                # 检查方法是否存在
                if method_name not in self.methods:
                    return jsonify({
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method '{method_name}' not found"
                        }
                    }), 404
                
                # 获取方法
                method = self.methods[method_name]
                
                if is_async:
                    # 异步执行方法
                    task_id = str(uuid.uuid4())
                    self.tasks[task_id] = {
                        "id": task_id,
                        "method": method_name,
                        "params": params,
                        "status": "pending",
                        "created_at": time.time()
                    }
                    
                    # 提交任务到线程池
                    self.executor.submit(self._execute_task, task_id, method, params)
                    
                    # 返回任务ID
                    return jsonify({
                        "id": request_id,
                        "result": {
                            "task_id": task_id
                        }
                    })
                else:
                    # 同步执行方法
                    try:
                        result = method(**params)
                        return jsonify({
                            "id": request_id,
                            "result": result
                        })
                    except Exception as e:
                        logger.exception(f"Error executing method '{method_name}'")
                        return jsonify({
                            "id": request_id,
                            "error": {
                                "code": -32603,
                                "message": str(e)
                            }
                        }), 500
            
            except Exception as e:
                logger.exception("Error handling RPC request")
                return jsonify({
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    }
                }), 500
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """健康检查"""
            return jsonify({
                "status": "ok",
                "version": "1.0.0",
                "tasks": len(self.tasks)
            })
    
    def _execute_task(self, task_id: str, method: Callable, params: Dict[str, Any]):
        """
        执行异步任务
        
        Args:
            task_id: 任务ID
            method: 要执行的方法
            params: 方法参数
        """
        try:
            # 更新任务状态为运行中
            self.tasks[task_id]["status"] = "running"
            self.tasks[task_id]["started_at"] = time.time()
            
            # 执行方法
            result = method(**params)
            
            # 更新任务状态为完成
            self.tasks[task_id]["status"] = "completed"
            self.tasks[task_id]["completed_at"] = time.time()
            self.tasks[task_id]["result"] = result
        
        except Exception as e:
            logger.exception(f"Error executing task {task_id}")
            
            # 更新任务状态为失败
            self.tasks[task_id]["status"] = "failed"
            self.tasks[task_id]["completed_at"] = time.time()
            self.tasks[task_id]["error"] = str(e)
    
    def register_method(self, name: str, method: Callable):
        """
        注册方法
        
        Args:
            name: 方法名称，格式为"模块.方法"
            method: 方法函数
        """
        self.methods[name] = method
        logger.info(f"Registered method: {name}")
    
    def register_module(self, module_name: str, methods: Dict[str, Callable]):
        """
        注册模块
        
        Args:
            module_name: 模块名称
            methods: 方法字典，键为方法名，值为方法函数
        """
        for method_name, method in methods.items():
            full_name = f"{module_name}.{method_name}"
            self.register_method(full_name, method)
    
    def start(self, host: str = None, port: int = None):
        """
        启动服务器
        
        Args:
            host: 主机地址，默认使用配置中的值
            port: 端口号，默认使用配置中的值
        """
        if host is None:
            host = self.config["mcp"]["server_host"]
        
        if port is None:
            port = self.config["mcp"]["server_port"]
        
        # 注册任务管理方法
        self.register_module("task", {
            "get_status": self.get_task_status,
            "list": self.list_tasks,
            "cancel": self.cancel_task,
            "clean": self.clean_tasks
        })
        
        logger.info(f"Starting MCP server at {host}:{port}")
        self.app.run(host=host, port=port, threaded=True)
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
        
        Returns:
            任务状态信息
        
        Raises:
            Exception: 任务不存在时抛出异常
        """
        if task_id not in self.tasks:
            raise Exception(f"Task '{task_id}' not found")
        
        return self.tasks[task_id]
    
    def list_tasks(self, status: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        列出任务
        
        Args:
            status: 任务状态过滤
            limit: 最大返回数量
        
        Returns:
            任务列表
        """
        tasks = list(self.tasks.values())
        
        # 按状态过滤
        if status:
            tasks = [task for task in tasks if task["status"] == status]
        
        # 按创建时间排序
        tasks.sort(key=lambda x: x["created_at"], reverse=True)
        
        # 限制数量
        return tasks[:limit]
    
    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """
        取消任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            任务状态信息
        
        Raises:
            Exception: 任务不存在或无法取消时抛出异常
        """
        if task_id not in self.tasks:
            raise Exception(f"Task '{task_id}' not found")
        
        task = self.tasks[task_id]
        
        if task["status"] not in ["pending", "running"]:
            raise Exception(f"Cannot cancel task with status '{task['status']}'")
        
        # 更新任务状态为取消
        task["status"] = "cancelled"
        task["completed_at"] = time.time()
        
        return task
    
    def clean_tasks(self, max_age: int = 3600) -> int:
        """
        清理旧任务
        
        Args:
            max_age: 最大任务年龄（秒）
        
        Returns:
            清理的任务数量
        """
        current_time = time.time()
        task_ids_to_remove = []
        
        for task_id, task in self.tasks.items():
            # 检查任务是否已完成且超过最大年龄
            if task["status"] in ["completed", "failed", "cancelled"]:
                completed_at = task.get("completed_at", 0)
                if current_time - completed_at > max_age:
                    task_ids_to_remove.append(task_id)
        
        # 移除旧任务
        for task_id in task_ids_to_remove:
            del self.tasks[task_id]
        
        return len(task_ids_to_remove)

def start_mcp_server(config: Dict[str, Any]) -> threading.Thread:
    """
    启动MCP服务器（后台线程）
    
    Args:
        config: 服务器配置
    
    Returns:
        服务器线程
    """
    # 创建MCP服务器实例
    server = MCPServer(config)
    
    # 注册服务模块
    register_transcription_service(server)
    register_llm_service(server)
    register_vector_service(server)
    register_email_service(server)
    register_gmail_auth_service(server)
    register_chatbot_service(server)
    register_gmail_service(server)
    register_email_analysis_service(server)
    register_meeting_service(server)
    
    # 创建服务器线程
    server_thread = threading.Thread(
        target=server.start,
        daemon=True
    )
    
    # 启动服务器线程
    server_thread.start()
    
    logger.info(f"MCP服务器已启动: {config['mcp']['server_host']}:{config['mcp']['server_port']}")
    
    return server_thread
