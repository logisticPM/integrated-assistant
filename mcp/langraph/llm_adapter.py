#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基于 langraph 的 LLM 适配器组件
支持多种 LLM 服务
"""

import os
import sys
import logging
import time
import json
from typing import Dict, Any, List, Optional, Union, Callable
from pydantic import BaseModel, Field

from mcp.langraph.core import MCPComponent, LLMComponent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("langraph.llm_adapter")

class AnythingLLMComponent(LLMComponent):
    """AnythingLLM API 组件"""
    
    def __init__(
        self,
        name: str = "anything_llm",
        api_url: str = "http://localhost:3001",
        api_key: Optional[str] = None
    ):
        """
        初始化 AnythingLLM API 组件
        
        Args:
            name: 组件名称
            api_url: API URL
            api_key: API 密钥
        """
        super().__init__(
            name=name,
            description="AnythingLLM API 组件"
        )
        
        self.api_url = api_url
        self.api_key = api_key
    
    def is_available(self) -> bool:
        """
        检查组件是否可用
        
        Returns:
            是否可用
        """
        try:
            import requests
            
            # 检查 API 是否可用
            headers = {}
            if self.api_key:
                headers["x-api-key"] = self.api_key
            
            response = requests.get(
                f"{self.api_url}/api/health",
                headers=headers,
                timeout=5
            )
            
            return response.status_code == 200
        except Exception as e:
            logger.error(f"检查 AnythingLLM API 可用性失败: {str(e)}")
            return False
    
    def process(self, prompt: str, **kwargs) -> str:
        """
        处理提示
        
        Args:
            prompt: 提示文本
            **kwargs: 其他参数
        
        Returns:
            LLM 响应
        """
        try:
            import requests
            
            logger.info(f"开始通过 AnythingLLM API 处理提示")
            start_time = time.time()
            
            # 准备请求头
            headers = {
                "Content-Type": "application/json"
            }
            if self.api_key:
                headers["x-api-key"] = self.api_key
            
            # 准备请求体
            data = {
                "prompt": prompt,
                **kwargs
            }
            
            # 发送请求
            response = requests.post(
                f"{self.api_url}/api/chat",
                headers=headers,
                json=data,
                timeout=60
            )
            
            # 检查响应
            if response.status_code != 200:
                raise Exception(f"API 请求失败: {response.status_code} {response.text}")
            
            # 解析响应
            result = response.json()
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            logger.info(f"处理完成，耗时: {processing_time:.2f}秒")
            
            return result.get("response", "")
        except Exception as e:
            logger.error(f"处理失败: {str(e)}")
            raise

class MockLLMComponent(LLMComponent):
    """模拟 LLM 组件，用于测试和开发"""
    
    def __init__(self, name: str = "mock_llm"):
        """
        初始化模拟 LLM 组件
        
        Args:
            name: 组件名称
        """
        super().__init__(
            name=name,
            description="模拟 LLM 组件"
        )
    
    def is_available(self) -> bool:
        """
        检查组件是否可用
        
        Returns:
            是否可用
        """
        return True
    
    def process(self, prompt: str, **kwargs) -> str:
        """
        处理提示
        
        Args:
            prompt: 提示文本
            **kwargs: 其他参数
        
        Returns:
            LLM 响应
        """
        logger.info(f"模拟处理提示: {prompt[:50]}...")
        
        # 模拟处理时间
        time.sleep(1)
        
        # 返回模拟结果
        return f"这是对提示 '{prompt[:20]}...' 的模拟回复。"

class LLMService:
    """LLM 服务，管理多个 LLM 组件"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 LLM 服务
        
        Args:
            config: 配置
        """
        self.config = config
        self.components: Dict[str, LLMComponent] = {}
        
        # 初始化组件
        self._init_components()
    
    def _init_components(self):
        """初始化组件"""
        # 添加 AnythingLLM API 组件
        if self.config.get("llm", {}).get("anything_llm", {}).get("enabled", False):
            api_url = self.config.get("llm", {}).get("anything_llm", {}).get("api_url", "http://localhost:3001")
            api_key = self.config.get("llm", {}).get("anything_llm", {}).get("api_key")
            
            component = AnythingLLMComponent(
                api_url=api_url,
                api_key=api_key
            )
            
            self.add_component(component)
        
        # 添加模拟组件
        self.add_component(MockLLMComponent())
    
    def add_component(self, component: LLMComponent):
        """
        添加组件
        
        Args:
            component: 要添加的组件
        """
        self.components[component.name] = component
        logger.info(f"添加 LLM 组件: {component.name}")
    
    def get_available_component(self) -> Optional[LLMComponent]:
        """
        获取可用的组件
        
        Returns:
            可用的组件，如果没有则返回 None
        """
        # 优先级：AnythingLLM API > 模拟
        for name in ["anything_llm", "mock_llm"]:
            if name in self.components and self.components[name].is_available():
                return self.components[name]
        
        return None
    
    def process(self, prompt: str, **kwargs) -> str:
        """
        处理提示
        
        Args:
            prompt: 提示文本
            **kwargs: 其他参数
        
        Returns:
            LLM 响应
        
        Raises:
            RuntimeError: 没有可用的 LLM 组件时抛出
        """
        component = self.get_available_component()
        
        if component is None:
            raise RuntimeError("没有可用的 LLM 组件")
        
        logger.info(f"使用组件 {component.name} 处理提示")
        
        return component.process(prompt, **kwargs)
