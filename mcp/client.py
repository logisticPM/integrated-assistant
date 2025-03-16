#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MCP客户端 - 提供与MCP服务器通信的客户端接口
"""

import json
import requests
import uuid
from typing import Dict, Any, Optional

class MCPClient:
    """MCP客户端类，用于与MCP服务器通信"""
    
    def __init__(self, server_url: str = "http://127.0.0.1:5000"):
        """
        初始化MCP客户端
        
        Args:
            server_url: MCP服务器URL
        """
        self.server_url = server_url
        self.client_id = str(uuid.uuid4())
    
    def call(self, method: str, params: Dict[str, Any] = None) -> Any:
        """
        调用MCP服务方法
        
        Args:
            method: 方法名称，格式为"模块.方法"
            params: 方法参数
        
        Returns:
            方法返回结果
        
        Raises:
            Exception: 调用失败时抛出异常
        """
        if params is None:
            params = {}
        
        # 构建请求数据
        request_data = {
            "id": str(uuid.uuid4()),
            "client_id": self.client_id,
            "method": method,
            "params": params
        }
        
        try:
            # 发送请求
            response = requests.post(
                f"{self.server_url}/rpc",
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应数据
            result = response.json()
            
            # 检查是否有错误
            if "error" in result:
                raise Exception(result["error"].get("message", "Unknown error"))
            
            # 返回结果
            return result.get("result")
        
        except requests.RequestException as e:
            raise Exception(f"MCP通信错误: {str(e)}")
        except json.JSONDecodeError:
            raise Exception("MCP响应格式错误")
        except Exception as e:
            raise Exception(f"MCP调用错误: {str(e)}")
    
    def async_call(self, method: str, params: Dict[str, Any] = None) -> str:
        """
        异步调用MCP服务方法
        
        Args:
            method: 方法名称，格式为"模块.方法"
            params: 方法参数
        
        Returns:
            任务ID
        
        Raises:
            Exception: 调用失败时抛出异常
        """
        if params is None:
            params = {}
        
        # 构建请求数据
        request_data = {
            "id": str(uuid.uuid4()),
            "client_id": self.client_id,
            "method": method,
            "params": params,
            "async": True
        }
        
        try:
            # 发送请求
            response = requests.post(
                f"{self.server_url}/rpc",
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应数据
            result = response.json()
            
            # 检查是否有错误
            if "error" in result:
                raise Exception(result["error"].get("message", "Unknown error"))
            
            # 返回任务ID
            return result.get("result", {}).get("task_id")
        
        except requests.RequestException as e:
            raise Exception(f"MCP通信错误: {str(e)}")
        except json.JSONDecodeError:
            raise Exception("MCP响应格式错误")
        except Exception as e:
            raise Exception(f"MCP调用错误: {str(e)}")
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取异步任务状态
        
        Args:
            task_id: 任务ID
        
        Returns:
            任务状态信息
        
        Raises:
            Exception: 调用失败时抛出异常
        """
        return self.call("task.get_status", {"task_id": task_id})
    
    def wait_for_task(self, task_id: str, timeout: int = 300) -> Any:
        """
        等待异步任务完成
        
        Args:
            task_id: 任务ID
            timeout: 超时时间（秒）
        
        Returns:
            任务结果
        
        Raises:
            Exception: 调用失败或超时时抛出异常
        """
        import time
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_task_status(task_id)
            
            if status["status"] == "completed":
                return status["result"]
            elif status["status"] == "failed":
                raise Exception(f"任务失败: {status.get('error', '未知错误')}")
            
            # 等待一段时间再检查
            time.sleep(1)
        
        raise Exception(f"任务等待超时 (ID: {task_id})")
