#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
langraph 核心组件
提供基于 langraph 的组件和图结构
"""

import os
import logging
from typing import Dict, Any, List, Optional, Callable, Type, Union
from pydantic import BaseModel, Field
import langchain
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
import langraph
from langraph.graph import StateGraph, END

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("langraph.core")

class MCPComponent(BaseModel):
    """MCP 组件基类"""
    name: str
    description: str = ""
    version: str = "1.0.0"
    
    def to_runnable(self) -> Runnable:
        """转换为可运行组件"""
        raise NotImplementedError("子类必须实现此方法")

class MCPState(BaseModel):
    """MCP 状态基类"""
    pass

class MCPGraph:
    """MCP 图类，用于管理组件和流程"""
    
    def __init__(self, name: str, description: str = ""):
        """
        初始化 MCP 图
        
        Args:
            name: 图名称
            description: 图描述
        """
        self.name = name
        self.description = description
        self.components: Dict[str, MCPComponent] = {}
        self.graph = StateGraph(MCPState)
    
    def add_component(self, component: MCPComponent) -> None:
        """
        添加组件
        
        Args:
            component: 要添加的组件
        """
        if component.name in self.components:
            logger.warning(f"组件 {component.name} 已存在，将被覆盖")
        
        self.components[component.name] = component
        self.graph.add_node(component.name, component.to_runnable())
        logger.info(f"添加组件: {component.name}")
    
    def add_edge(self, from_component: str, to_component: str, condition: Optional[Callable] = None) -> None:
        """
        添加边
        
        Args:
            from_component: 源组件名称
            to_component: 目标组件名称
            condition: 条件函数，决定是否执行此边
        """
        if from_component not in self.components:
            raise ValueError(f"源组件不存在: {from_component}")
        
        if to_component != END and to_component not in self.components:
            raise ValueError(f"目标组件不存在: {to_component}")
        
        self.graph.add_edge(from_component, to_component, condition)
        logger.info(f"添加边: {from_component} -> {to_component}")
    
    def compile(self) -> Runnable:
        """
        编译图
        
        Returns:
            可运行的图
        """
        return self.graph.compile()
    
    def run(self, inputs: Dict[str, Any], config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
        """
        运行图
        
        Args:
            inputs: 输入数据
            config: 运行配置
        
        Returns:
            运行结果
        """
        compiled_graph = self.compile()
        return compiled_graph.invoke(inputs, config)
    
    def run_async(self, inputs: Dict[str, Any], config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
        """
        异步运行图
        
        Args:
            inputs: 输入数据
            config: 运行配置
        
        Returns:
            运行结果
        """
        compiled_graph = self.compile()
        return compiled_graph.ainvoke(inputs, config)

    def visualize(self, output_path: Optional[str] = None) -> None:
        """
        可视化图
        
        Args:
            output_path: 输出路径，如果为 None 则显示图而不保存
        """
        try:
            import graphviz
            
            dot = self.graph.get_graph()
            
            if output_path:
                dot.render(output_path, format="png", cleanup=True)
                logger.info(f"图已保存到: {output_path}.png")
            else:
                dot.view()
                logger.info("图已显示")
        
        except ImportError:
            logger.warning("未安装 graphviz，无法可视化图")
        
        except Exception as e:
            logger.error(f"可视化图失败: {str(e)}")

# 常用组件类型

class TranscriptionComponent(MCPComponent):
    """转录组件"""
    
    def is_available(self) -> bool:
        """
        检查组件是否可用
        
        Returns:
            是否可用
        """
        return True
    
    def process(self, audio_path: str) -> Dict[str, Any]:
        """
        处理音频
        
        Args:
            audio_path: 音频文件路径
        
        Returns:
            转录结果
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def to_runnable(self) -> Callable:
        """转换为可运行组件"""
        def _run(state: MCPState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
            if not hasattr(state, "audio_path"):
                raise ValueError("状态中缺少 audio_path 字段")
            
            return {"transcription": self.process(state.audio_path)}
        
        return _run

class LLMComponent(MCPComponent):
    """LLM 组件"""
    
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
        raise NotImplementedError("子类必须实现此方法")
    
    def to_runnable(self) -> Callable:
        """转换为可运行组件"""
        def _run(state: MCPState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
            if not hasattr(state, "prompt"):
                raise ValueError("状态中缺少 prompt 字段")
            
            return {"response": self.process(state.prompt)}
        
        return _run

class VectorStoreComponent(MCPComponent):
    """向量存储组件"""
    
    def is_available(self) -> bool:
        """
        检查组件是否可用
        
        Returns:
            是否可用
        """
        return True
    
    def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        搜索向量存储
        
        Args:
            query: 查询文本
            **kwargs: 其他参数
        
        Returns:
            搜索结果
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def to_runnable(self) -> Callable:
        """转换为可运行组件"""
        def _run(state: MCPState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
            if not hasattr(state, "query"):
                raise ValueError("状态中缺少 query 字段")
            
            return {"results": self.search(state.query)}
        
        return _run

class ToolComponent(MCPComponent):
    """工具组件"""
    
    def is_available(self) -> bool:
        """
        检查组件是否可用
        
        Returns:
            是否可用
        """
        return True
    
    def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工具
        
        Args:
            action: 动作名称
            parameters: 参数
        
        Returns:
            执行结果
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def to_runnable(self) -> Callable:
        """转换为可运行组件"""
        def _run(state: MCPState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
            if not hasattr(state, "action") or not hasattr(state, "parameters"):
                raise ValueError("状态中缺少 action 或 parameters 字段")
            
            return {"tool_result": self.execute(state.action, state.parameters)}
        
        return _run

class AgentComponent(MCPComponent):
    """代理组件"""
    
    def is_available(self) -> bool:
        """
        检查组件是否可用
        
        Returns:
            是否可用
        """
        return True
    
    def process(self, input_data: Dict[str, Any], tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理输入
        
        Args:
            input_data: 输入数据
            tools: 可用工具列表
        
        Returns:
            处理结果
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def to_runnable(self) -> Callable:
        """转换为可运行组件"""
        def _run(state: MCPState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
            if not hasattr(state, "input"):
                raise ValueError("状态中缺少 input 字段")
            
            tools = getattr(state, "tools", None)
            
            return self.process(state.input, tools)
        
        return _run

class MemoryComponent(MCPComponent):
    """记忆组件"""
    
    def is_available(self) -> bool:
        """
        检查组件是否可用
        
        Returns:
            是否可用
        """
        return True
    
    def save(self, key: str, value: Any) -> bool:
        """
        保存记忆
        
        Args:
            key: 键
            value: 值
        
        Returns:
            是否成功
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def load(self, key: str) -> Optional[Any]:
        """
        加载记忆
        
        Args:
            key: 键
        
        Returns:
            记忆值，如果不存在则返回 None
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def to_runnable(self) -> Callable:
        """转换为可运行组件"""
        def _run(state: MCPState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
            if hasattr(state, "save_key") and hasattr(state, "save_value"):
                success = self.save(state.save_key, state.save_value)
                return {"memory_saved": success}
            
            if hasattr(state, "load_key"):
                value = self.load(state.load_key)
                return {"memory_value": value}
            
            raise ValueError("状态中缺少 save_key 和 save_value 或 load_key 字段")
        
        return _run
