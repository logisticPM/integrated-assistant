#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基于 langraph 的 LLM 适配器服务
支持多种 LLM 组件，包括 AnythingLLM 和本地 LLM
"""

import os
import sys
import logging
import time
import json
from typing import Dict, Any, List, Optional, Union, Callable
from pydantic import BaseModel, Field

from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser

from mcp.langraph.core import MCPComponent, MCPState, MCPGraph, LLMComponent
from mcp.langraph.local_llm_component import LocalLLMComponent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("langraph.llm_adapter")

class AnythingLLMComponent(LLMComponent):
    """AnythingLLM 组件"""
    
    def __init__(
        self, 
        name: str = "anything_llm",
        api_url: str = None,
        api_key: str = None
    ):
        """
        初始化 AnythingLLM 组件
        
        Args:
            name: 组件名称
            api_url: API URL
            api_key: API 密钥
        """
        super().__init__(
            name=name,
            description="AnythingLLM 组件"
        )
        self.api_url = api_url
        self.api_key = api_key
    
    def is_available(self) -> bool:
        """
        检查组件是否可用
        
        Returns:
            是否可用
        """
        import requests
        
        if not self.api_url:
            logger.warning("AnythingLLM API URL 未配置")
            return False
        
        try:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            response = requests.get(
                f"{self.api_url}/health",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info("AnythingLLM API 可用")
                return True
            else:
                logger.warning(f"AnythingLLM API 不可用: {response.status_code}")
                return False
        
        except Exception as e:
            logger.warning(f"检查 AnythingLLM API 可用性失败: {str(e)}")
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
        import requests
        
        logger.info(f"开始通过 AnythingLLM API 处理提示")
        start_time = time.time()
        
        # 提取参数
        max_tokens = kwargs.get("max_tokens", 1000)
        temperature = kwargs.get("temperature", 0.7)
        
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            response = requests.post(
                f"{self.api_url}/completions",
                headers=headers,
                json={
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json().get("text", "")
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            logger.info(f"处理完成，耗时: {processing_time:.2f}秒")
            
            return result
        
        except Exception as e:
            logger.error(f"处理失败: {str(e)}")
            raise

class MockLLMComponent(LLMComponent):
    """模拟 LLM 组件，用于测试"""
    
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
        logger.info(f"开始通过模拟 LLM 处理提示")
        
        # 模拟处理延迟
        time.sleep(0.5)
        
        # 根据不同的提示词模拟不同的响应
        if "会议记录" in prompt and "摘要" in prompt and "结构化" in prompt:
            # 模拟结构化会议摘要的JSON响应
            return json.dumps({
                "summary": "会议主要讨论了项目进度和下一步计划。团队报告了当前的开发状态，并确定了需要解决的关键问题。会议决定在下周五前完成初步原型，并安排了下一次评审会议的时间。",
                "agenda": "1. 项目进度回顾\n2. 问题讨论\n3. 下一步计划\n4. 任务分配",
                "decisions": "1. 决定将发布日期推迟一周\n2. 同意增加两名开发人员到团队\n3. 批准了新的UI设计方案",
                "action_items": [
                    {"assignee": "张三", "task": "完成前端界面开发", "due_date": "2023-10-15", "status": "进行中"},
                    {"assignee": "李四", "task": "修复已知的3个关键bug", "due_date": "2023-10-10", "status": "待处理"},
                    {"assignee": "王五", "task": "准备下周的演示文稿", "due_date": "2023-10-12", "status": "未开始"}
                ],
                "key_points": [
                    {"timestamp": "00:05:23", "speaker": "张三", "point": "报告了前端开发的当前进度，完成了约70%的计划功能"},
                    {"timestamp": "00:12:45", "speaker": "李四", "point": "提出了后端API的性能问题，需要优化数据库查询"},
                    {"timestamp": "00:25:30", "speaker": "王五", "point": "建议增加用户反馈收集功能，以便及时调整产品方向"}
                ]
            }, ensure_ascii=False)
        elif "会议记录" in prompt and "摘要" in prompt:
            # 模拟会议摘要
            return "会议主要讨论了项目进度和下一步计划。团队报告了当前的开发状态，并确定了需要解决的关键问题。会议决定在下周五前完成初步原型，并安排了下一次评审会议的时间。"
        elif "会议记录" in prompt and "关键点" in prompt:
            # 模拟会议关键点
            return "1. [00:05:23] 张三报告了前端开发的当前进度，完成了约70%的计划功能\n2. [00:12:45] 李四提出了后端API的性能问题，需要优化数据库查询\n3. [00:25:30] 王五建议增加用户反馈收集功能，以便及时调整产品方向"
        else:
            # 通用回复
            return f"这是对您提问的回复。您的提问内容涉及到了{prompt[:20]}...等方面的内容。这是一个模拟的回复，用于测试系统功能。"

class LLMAdapterComponent(MCPComponent):
    """LLM 适配器组件，提供对 LLM 模型的统一接口"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 LLM 适配器组件
        
        Args:
            config: 配置信息
        """
        super().__init__()
        self.config = config
        
        # 初始化 LLM 客户端
        self.anything_llm_client = None
        self.local_llm_component = None
        
        # 初始化 LLM 服务
        self._init_llm_services()
    
    def _init_llm_services(self):
        """初始化 LLM 服务"""
        # 检查是否使用本地模型
        if self.config["llm"]["model"] == "local":
            try:
                # 初始化本地 LLM 组件
                self.local_llm_component = LocalLLMComponent(
                    model_path=self.config["llm"]["model_path"]
                )
                logger.info("本地 LLM 组件初始化成功")
            except Exception as e:
                logger.error(f"初始化本地 LLM 组件失败: {str(e)}")
                self.local_llm_component = None
        
        # 检查是否启用 AnythingLLM
        if self.config["llm"]["anything_llm"]["enabled"]:
            try:
                # 导入 AnythingLLM 客户端
                from mcp.llm_adapter import AnythingLLMClient
                
                # 初始化 AnythingLLM 客户端
                self.anything_llm_client = AnythingLLMClient(
                    api_url=self.config["llm"]["anything_llm"]["api_url"],
                    api_key=self.config["llm"]["anything_llm"]["api_key"]
                )
                logger.info("AnythingLLM 客户端初始化成功")
            except Exception as e:
                logger.error(f"初始化 AnythingLLM 客户端失败: {str(e)}")
                self.anything_llm_client = None
    
    def process(self, state: MCPState) -> MCPState:
        """
        处理 LLM 请求
        
        Args:
            state: 当前状态
        
        Returns:
            更新后的状态
        """
        # 检查是否需要生成文本
        if "prompt" not in state.inputs:
            logger.warning("没有提供提示词，跳过 LLM 处理")
            state.outputs["llm_response"] = {"error": "没有提供提示词"}
            return state
        
        prompt = state.inputs["prompt"]
        max_tokens = state.inputs.get("max_tokens", 512)
        temperature = state.inputs.get("temperature", 0.7)
        
        # 检查是否有可用的 LLM 服务
        if self.local_llm_component is None and self.anything_llm_client is None:
            error_msg = "没有可用的 LLM 服务"
            logger.error(error_msg)
            state.outputs["llm_response"] = {"error": error_msg}
            state.outputs["error"] = error_msg
            return state
        
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 根据配置选择 LLM 服务
            if self.config["llm"]["model"] == "local" and self.local_llm_component is not None:
                # 使用本地 LLM 组件
                logger.info("使用本地 LLM 组件生成文本")
                response = self.local_llm_component.generate_text(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            elif self.anything_llm_client is not None:
                # 使用 AnythingLLM API
                logger.info("使用 AnythingLLM API 生成文本")
                response = self.anything_llm_client.generate_text(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            else:
                # 使用模拟 LLM
                logger.warning("使用模拟 LLM 生成文本")
                response = self._mock_generate_text(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            
            # 记录处理时间
            processing_time = time.time() - start_time
            logger.info(f"文本生成完成，耗时: {processing_time:.2f}秒")
            
            # 更新状态
            state.outputs["llm_response"] = response
            state.outputs["text"] = response.get("text", "")
            
            # 如果有错误，记录到状态中
            if "error" in response:
                state.outputs["error"] = response["error"]
            
            return state
            
        except Exception as e:
            error_msg = f"LLM 处理失败: {str(e)}"
            logger.exception(error_msg)
            
            # 更新状态
            state.outputs["llm_response"] = {"error": error_msg}
            state.outputs["error"] = error_msg
            
            return state
    
    def _mock_generate_text(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> Dict[str, Any]:
        """
        模拟生成文本
        
        Args:
            prompt: 提示词
            max_tokens: 最大生成长度
            temperature: 温度参数
        
        Returns:
            生成结果
        """
        # 模拟处理延迟
        time.sleep(1)
        
        # 模拟生成结果
        return {
            "text": f"这是一个模拟的 LLM 响应。在实际部署中，您需要配置 AnythingLLM API 或者本地 LLM 模型来获取真实的响应。\n\n您的提示词是: {prompt[:100]}...",
            "model": "mock",
            "processing_time": 1.0
        }

class MockLLMAdapterComponent(MCPComponent):
    """模拟 LLM 适配器组件，用于测试"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化模拟 LLM 适配器组件
        
        Args:
            config: 配置信息
        """
        super().__init__()
        self.config = config or {}
    
    def process(self, state: MCPState) -> MCPState:
        """
        处理 LLM 请求
        
        Args:
            state: 当前状态
        
        Returns:
            更新后的状态
        """
        # 检查是否需要生成文本
        if "prompt" not in state.inputs:
            logger.warning("没有提供提示词，跳过 LLM 处理")
            state.outputs["llm_response"] = {"error": "没有提供提示词"}
            return state
        
        prompt = state.inputs["prompt"]
        
        # 模拟处理延迟
        time.sleep(1)
        
        # 模拟生成结果
        result = {
            "text": f"这是一个模拟的 LLM 响应。在实际部署中，您需要配置 AnythingLLM API 或者本地 LLM 模型来获取真实的响应。\n\n您的提示词是: {prompt[:100]}...",
            "model": "mock",
            "processing_time": 1.0
        }
        
        # 更新状态
        state.outputs["llm_response"] = result
        state.outputs["text"] = result["text"]
        
        logger.info("模拟 LLM 处理完成")
        return state

class LLMAdapterService:
    """LLM 适配器服务，管理多个 LLM 组件"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 LLM 适配器服务
        
        Args:
            config: 服务配置
        """
        self.config = config
        self.components: Dict[str, LLMComponent] = {}
        self.graph = MCPGraph("llm_adapter", "LLM 适配器服务")
        
        # 初始化组件
        self._init_components()
    
    def _init_components(self):
        """初始化 LLM 组件"""
        # 添加 AnythingLLM 组件
        if self.config.get("llm", {}).get("anything_llm", {}).get("enabled", False):
            api_url = self.config.get("llm", {}).get("anything_llm", {}).get("api_url", "")
            api_key = self.config.get("llm", {}).get("anything_llm", {}).get("api_key", "")
            
            component = AnythingLLMComponent(
                api_url=api_url,
                api_key=api_key
            )
            
            self.add_component(component)
        
        # 添加本地 LLM 组件
        if self.config.get("llm", {}).get("model") == "local":
            model_path = self.config.get("llm", {}).get("model_path", "./models/llm")
            
            component = LocalLLMComponent(
                model_dir=model_path
            )
            
            self.add_component(component)
        
        # 如果没有可用的组件，添加模拟组件
        if not self.components:
            component = MockLLMComponent()
            self.add_component(component)
    
    def add_component(self, component: LLMComponent):
        """
        添加 LLM 组件
        
        Args:
            component: LLM 组件
        """
        if component.is_available():
            self.components[component.name] = component
            self.graph.add_component(component)
            logger.info(f"添加 LLM 组件: {component.name}")
        else:
            logger.warning(f"LLM 组件不可用: {component.name}")
    
    def get_available_components(self) -> List[str]:
        """
        获取可用的 LLM 组件列表
        
        Returns:
            组件名称列表
        """
        return list(self.components.keys())
    
    def process(self, prompt: str, component_name: str = None, **kwargs) -> str:
        """
        处理提示
        
        Args:
            prompt: 提示文本
            component_name: 组件名称，如果为 None，则使用第一个可用的组件
            **kwargs: 其他参数
        
        Returns:
            LLM 响应
        """
        # 如果未指定组件，使用第一个可用的组件
        if component_name is None and self.components:
            component_name = next(iter(self.components.keys()))
        
        if component_name not in self.components:
            available_components = ", ".join(self.components.keys())
            raise ValueError(f"LLM 组件不存在: {component_name}，可用组件: {available_components}")
        
        component = self.components[component_name]
        return component.process(prompt, **kwargs)
    
    def compile(self) -> Runnable:
        """
        编译 LLM 适配器服务图
        
        Returns:
            可运行的图
        """
        return self.graph.compile()
    
    def run(self, inputs: Dict[str, Any], config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
        """
        运行 LLM 适配器服务图
        
        Args:
            inputs: 输入数据
            config: 运行配置
        
        Returns:
            处理结果
        """
        return self.graph.run(inputs, config)

def create_llm_adapter_service(config: Dict[str, Any]) -> LLMAdapterService:
    """
    创建 LLM 适配器服务
    
    Args:
        config: 服务配置
    
    Returns:
        LLM 适配器服务实例
    """
    return LLMAdapterService(config)

def create_llm_adapter_component(config: Dict[str, Any]) -> MCPComponent:
    """
    创建 LLM 适配器组件
    
    Args:
        config: 配置信息
    
    Returns:
        LLM 适配器组件实例
    """
    try:
        # 创建 LLM 适配器组件
        component = LLMAdapterComponent(config)
        
        # 检查是否有可用的 LLM 服务
        if component.local_llm_component is None and component.anything_llm_client is None:
            logger.warning("没有可用的 LLM 服务，使用模拟 LLM 适配器组件")
            return MockLLMAdapterComponent(config)
        
        return component
    
    except Exception as e:
        logger.error(f"创建 LLM 适配器组件失败: {str(e)}")
        logger.warning("使用模拟 LLM 适配器组件")
        return MockLLMAdapterComponent(config)
