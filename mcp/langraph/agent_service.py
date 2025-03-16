#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基于 langraph 的代理服务组件
提供智能代理功能
"""

import os
import sys
import logging
import time
import json
import re
from typing import Dict, Any, List, Optional, Union, Callable, Tuple
from pydantic import BaseModel, Field

from mcp.langraph.core import MCPComponent, AgentComponent, MCPState, MCPGraph
from mcp.langraph.llm_adapter import LLMService
from mcp.langraph.tool_service import ToolService
from mcp.langraph.vector_service import VectorService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("langraph.agent_service")

class AgentState(MCPState):
    """代理状态"""
    input: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None
    output: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_results: Optional[List[Dict[str, Any]]] = None
    history: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None

class SimpleAgentComponent(AgentComponent):
    """简单代理组件"""
    
    def __init__(
        self,
        name: str = "simple_agent",
        llm_service: LLMService = None,
        tool_service: ToolService = None,
        config: Dict[str, Any] = None
    ):
        """
        初始化简单代理组件
        
        Args:
            name: 组件名称
            llm_service: LLM 服务
            tool_service: 工具服务
            config: 配置
        """
        super().__init__(
            name=name,
            description="简单代理组件"
        )
        
        self.llm_service = llm_service
        self.tool_service = tool_service
        self.config = config or {}
    
    def is_available(self) -> bool:
        """
        检查组件是否可用
        
        Returns:
            是否可用
        """
        return self.llm_service is not None and self.llm_service.get_available_component() is not None
    
    def process(self, input_data: Dict[str, Any], tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理输入
        
        Args:
            input_data: 输入数据
            tools: 可用工具列表
        
        Returns:
            处理结果
        """
        if not self.is_available():
            raise RuntimeError("代理不可用")
        
        try:
            # 获取输入文本
            input_text = input_data.get("text", "")
            if not input_text:
                raise ValueError("输入文本为空")
            
            # 获取历史记录
            history = input_data.get("history", [])
            
            # 获取可用工具
            available_tools = tools or []
            if not available_tools and self.tool_service:
                available_tools = self.tool_service.get_available_tools()
            
            # 准备提示
            prompt = self._build_prompt(input_text, history, available_tools)
            
            # 调用 LLM
            response = self.llm_service.process(prompt)
            
            # 解析响应
            output, tool_calls = self._parse_response(response)
            
            # 执行工具调用
            tool_results = []
            if tool_calls and self.tool_service:
                for tool_call in tool_calls:
                    tool_name = tool_call.get("name")
                    tool_action = tool_call.get("action")
                    tool_params = tool_call.get("parameters", {})
                    
                    try:
                        result = self.tool_service.execute_tool(tool_name, tool_action, tool_params)
                        tool_results.append({
                            "tool_call": tool_call,
                            "result": result
                        })
                    except Exception as e:
                        logger.error(f"执行工具 {tool_name}.{tool_action} 失败: {str(e)}")
                        tool_results.append({
                            "tool_call": tool_call,
                            "error": str(e)
                        })
            
            # 如果有工具调用结果，再次调用 LLM 处理
            if tool_results:
                final_prompt = self._build_final_prompt(input_text, history, available_tools, output, tool_calls, tool_results)
                final_response = self.llm_service.process(final_prompt)
                output, _ = self._parse_response(final_response)
            
            # 更新历史记录
            new_history = history + [
                {"role": "user", "content": input_text},
                {"role": "assistant", "content": output}
            ]
            
            return {
                "output": output,
                "tool_calls": tool_calls,
                "tool_results": tool_results,
                "history": new_history
            }
        
        except Exception as e:
            logger.error(f"处理失败: {str(e)}")
            raise
    
    def _build_prompt(self, input_text: str, history: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> str:
        """
        构建提示
        
        Args:
            input_text: 输入文本
            history: 历史记录
            tools: 可用工具列表
        
        Returns:
            提示文本
        """
        # 构建历史记录文本
        history_text = ""
        for item in history:
            role = item.get("role", "")
            content = item.get("content", "")
            
            if role == "user":
                history_text += f"用户: {content}\n\n"
            elif role == "assistant":
                history_text += f"助手: {content}\n\n"
        
        # 构建工具描述文本
        tools_text = ""
        if tools:
            tools_text = "可用工具:\n\n"
            for tool in tools:
                tools_text += f"- {tool.get('name')}: {tool.get('description')}\n"
        
        # 构建提示模板
        prompt_template = f"""你是一个智能助手，能够理解用户的请求并提供帮助。

{tools_text}

如果你需要使用工具，请使用以下格式：
```tool
{{
    "name": "工具名称",
    "action": "动作名称",
    "parameters": {{
        "参数名": "参数值"
    }}
}}
```

历史对话:
{history_text}

用户: {input_text}

助手: """
        
        return prompt_template
    
    def _build_final_prompt(
        self,
        input_text: str,
        history: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        initial_output: str,
        tool_calls: List[Dict[str, Any]],
        tool_results: List[Dict[str, Any]]
    ) -> str:
        """
        构建最终提示
        
        Args:
            input_text: 输入文本
            history: 历史记录
            tools: 可用工具列表
            initial_output: 初始输出
            tool_calls: 工具调用
            tool_results: 工具调用结果
        
        Returns:
            提示文本
        """
        # 构建历史记录文本
        history_text = ""
        for item in history:
            role = item.get("role", "")
            content = item.get("content", "")
            
            if role == "user":
                history_text += f"用户: {content}\n\n"
            elif role == "assistant":
                history_text += f"助手: {content}\n\n"
        
        # 构建工具调用和结果文本
        tools_text = ""
        if tools:
            tools_text = "可用工具:\n\n"
            for tool in tools:
                tools_text += f"- {tool.get('name')}: {tool.get('description')}\n"
        
        tool_calls_text = ""
        for i, (tool_call, tool_result) in enumerate(zip(tool_calls, tool_results)):
            tool_name = tool_call.get("name")
            tool_action = tool_call.get("action")
            tool_params = json.dumps(tool_call.get("parameters", {}), ensure_ascii=False, indent=2)
            
            tool_calls_text += f"工具调用 {i+1}:\n"
            tool_calls_text += f"名称: {tool_name}\n"
            tool_calls_text += f"动作: {tool_action}\n"
            tool_calls_text += f"参数: {tool_params}\n\n"
            
            if "result" in tool_result:
                result = json.dumps(tool_result["result"], ensure_ascii=False, indent=2)
                tool_calls_text += f"结果: {result}\n\n"
            else:
                error = tool_result.get("error", "未知错误")
                tool_calls_text += f"错误: {error}\n\n"
        
        # 构建提示模板
        prompt_template = f"""你是一个智能助手，能够理解用户的请求并提供帮助。

{tools_text}

历史对话:
{history_text}

用户: {input_text}

你的初始回复: {initial_output}

你使用了以下工具:
{tool_calls_text}

现在，请根据工具调用的结果，提供一个完整的回复。不要再次调用工具，直接回答用户的问题。

助手: """
        
        return prompt_template
    
    def _parse_response(self, response: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        解析响应
        
        Args:
            response: LLM 响应
        
        Returns:
            输出文本和工具调用列表
        """
        # 查找工具调用
        tool_calls = []
        
        # 使用正则表达式查找工具调用
        pattern = r"```tool\s*\n([\s\S]*?)\n```"
        matches = re.findall(pattern, response)
        
        for match in matches:
            try:
                tool_call = json.loads(match)
                tool_calls.append(tool_call)
            except json.JSONDecodeError:
                logger.warning(f"无法解析工具调用: {match}")
        
        # 移除工具调用部分
        output = re.sub(pattern, "", response)
        
        # 清理输出
        output = output.strip()
        
        return output, tool_calls

class RAGAgentComponent(AgentComponent):
    """RAG 代理组件"""
    
    def __init__(
        self,
        name: str = "rag_agent",
        llm_service: LLMService = None,
        tool_service: ToolService = None,
        vector_service: VectorService = None,
        config: Dict[str, Any] = None
    ):
        """
        初始化 RAG 代理组件
        
        Args:
            name: 组件名称
            llm_service: LLM 服务
            tool_service: 工具服务
            vector_service: 向量服务
            config: 配置
        """
        super().__init__(
            name=name,
            description="RAG 代理组件"
        )
        
        self.llm_service = llm_service
        self.tool_service = tool_service
        self.vector_service = vector_service
        self.config = config or {}
    
    def is_available(self) -> bool:
        """
        检查组件是否可用
        
        Returns:
            是否可用
        """
        return (
            self.llm_service is not None and
            self.llm_service.get_available_component() is not None and
            self.vector_service is not None and
            self.vector_service.get_available_component() is not None
        )
    
    def process(self, input_data: Dict[str, Any], tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理输入
        
        Args:
            input_data: 输入数据
            tools: 可用工具列表
        
        Returns:
            处理结果
        """
        if not self.is_available():
            raise RuntimeError("代理不可用")
        
        try:
            # 获取输入文本
            input_text = input_data.get("text", "")
            if not input_text:
                raise ValueError("输入文本为空")
            
            # 获取历史记录
            history = input_data.get("history", [])
            
            # 获取可用工具
            available_tools = tools or []
            if not available_tools and self.tool_service:
                available_tools = self.tool_service.get_available_tools()
            
            # 搜索相关文档
            search_results = self.vector_service.search(input_text, k=5)
            
            # 准备提示
            prompt = self._build_prompt(input_text, history, available_tools, search_results)
            
            # 调用 LLM
            response = self.llm_service.process(prompt)
            
            # 解析响应
            output, tool_calls = self._parse_response(response)
            
            # 执行工具调用
            tool_results = []
            if tool_calls and self.tool_service:
                for tool_call in tool_calls:
                    tool_name = tool_call.get("name")
                    tool_action = tool_call.get("action")
                    tool_params = tool_call.get("parameters", {})
                    
                    try:
                        result = self.tool_service.execute_tool(tool_name, tool_action, tool_params)
                        tool_results.append({
                            "tool_call": tool_call,
                            "result": result
                        })
                    except Exception as e:
                        logger.error(f"执行工具 {tool_name}.{tool_action} 失败: {str(e)}")
                        tool_results.append({
                            "tool_call": tool_call,
                            "error": str(e)
                        })
            
            # 如果有工具调用结果，再次调用 LLM 处理
            if tool_results:
                final_prompt = self._build_final_prompt(input_text, history, available_tools, search_results, output, tool_calls, tool_results)
                final_response = self.llm_service.process(final_prompt)
                output, _ = self._parse_response(final_response)
            
            # 更新历史记录
            new_history = history + [
                {"role": "user", "content": input_text},
                {"role": "assistant", "content": output}
            ]
            
            return {
                "output": output,
                "tool_calls": tool_calls,
                "tool_results": tool_results,
                "search_results": search_results,
                "history": new_history
            }
        
        except Exception as e:
            logger.error(f"处理失败: {str(e)}")
            raise
    
    def _build_prompt(
        self,
        input_text: str,
        history: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        search_results: List[Dict[str, Any]]
    ) -> str:
        """
        构建提示
        
        Args:
            input_text: 输入文本
            history: 历史记录
            tools: 可用工具列表
            search_results: 搜索结果
        
        Returns:
            提示文本
        """
        # 构建历史记录文本
        history_text = ""
        for item in history:
            role = item.get("role", "")
            content = item.get("content", "")
            
            if role == "user":
                history_text += f"用户: {content}\n\n"
            elif role == "assistant":
                history_text += f"助手: {content}\n\n"
        
        # 构建工具描述文本
        tools_text = ""
        if tools:
            tools_text = "可用工具:\n\n"
            for tool in tools:
                tools_text += f"- {tool.get('name')}: {tool.get('description')}\n"
        
        # 构建搜索结果文本
        search_results_text = ""
        if search_results:
            search_results_text = "相关文档:\n\n"
            for i, result in enumerate(search_results):
                content = result.get("content", "")
                metadata = result.get("metadata", {})
                score = result.get("score", 0.0)
                
                search_results_text += f"文档 {i+1} (相关度: {score:.2f}):\n"
                search_results_text += f"{content}\n\n"
        
        # 构建提示模板
        prompt_template = f"""你是一个智能助手，能够理解用户的请求并提供帮助。

{tools_text}

如果你需要使用工具，请使用以下格式：
```tool
{{
    "name": "工具名称",
    "action": "动作名称",
    "parameters": {{
        "参数名": "参数值"
    }}
}}
```

{search_results_text}

历史对话:
{history_text}

用户: {input_text}

助手: """
        
        return prompt_template
    
    def _build_final_prompt(
        self,
        input_text: str,
        history: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        search_results: List[Dict[str, Any]],
        initial_output: str,
        tool_calls: List[Dict[str, Any]],
        tool_results: List[Dict[str, Any]]
    ) -> str:
        """
        构建最终提示
        
        Args:
            input_text: 输入文本
            history: 历史记录
            tools: 可用工具列表
            search_results: 搜索结果
            initial_output: 初始输出
            tool_calls: 工具调用
            tool_results: 工具调用结果
        
        Returns:
            提示文本
        """
        # 构建历史记录文本
        history_text = ""
        for item in history:
            role = item.get("role", "")
            content = item.get("content", "")
            
            if role == "user":
                history_text += f"用户: {content}\n\n"
            elif role == "assistant":
                history_text += f"助手: {content}\n\n"
        
        # 构建工具调用和结果文本
        tools_text = ""
        if tools:
            tools_text = "可用工具:\n\n"
            for tool in tools:
                tools_text += f"- {tool.get('name')}: {tool.get('description')}\n"
        
        # 构建搜索结果文本
        search_results_text = ""
        if search_results:
            search_results_text = "相关文档:\n\n"
            for i, result in enumerate(search_results):
                content = result.get("content", "")
                metadata = result.get("metadata", {})
                score = result.get("score", 0.0)
                
                search_results_text += f"文档 {i+1} (相关度: {score:.2f}):\n"
                search_results_text += f"{content}\n\n"
        
        tool_calls_text = ""
        for i, (tool_call, tool_result) in enumerate(zip(tool_calls, tool_results)):
            tool_name = tool_call.get("name")
            tool_action = tool_call.get("action")
            tool_params = json.dumps(tool_call.get("parameters", {}), ensure_ascii=False, indent=2)
            
            tool_calls_text += f"工具调用 {i+1}:\n"
            tool_calls_text += f"名称: {tool_name}\n"
            tool_calls_text += f"动作: {tool_action}\n"
            tool_calls_text += f"参数: {tool_params}\n\n"
            
            if "result" in tool_result:
                result = json.dumps(tool_result["result"], ensure_ascii=False, indent=2)
                tool_calls_text += f"结果: {result}\n\n"
            else:
                error = tool_result.get("error", "未知错误")
                tool_calls_text += f"错误: {error}\n\n"
        
        # 构建提示模板
        prompt_template = f"""你是一个智能助手，能够理解用户的请求并提供帮助。

{tools_text}

{search_results_text}

历史对话:
{history_text}

用户: {input_text}

你的初始回复: {initial_output}

你使用了以下工具:
{tool_calls_text}

现在，请根据工具调用的结果，提供一个完整的回复。不要再次调用工具，直接回答用户的问题。

助手: """
        
        return prompt_template
    
    def _parse_response(self, response: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        解析响应
        
        Args:
            response: LLM 响应
        
        Returns:
            输出文本和工具调用列表
        """
        # 查找工具调用
        tool_calls = []
        
        # 使用正则表达式查找工具调用
        pattern = r"```tool\s*\n([\s\S]*?)\n```"
        matches = re.findall(pattern, response)
        
        for match in matches:
            try:
                tool_call = json.loads(match)
                tool_calls.append(tool_call)
            except json.JSONDecodeError:
                logger.warning(f"无法解析工具调用: {match}")
        
        # 移除工具调用部分
        output = re.sub(pattern, "", response)
        
        # 清理输出
        output = output.strip()
        
        return output, tool_calls

class AgentServiceGraph:
    """代理服务图，管理代理相关组件和流程"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化代理服务图
        
        Args:
            config: 配置
        """
        self.config = config
        
        # 创建服务
        self.llm_service = LLMService(config)
        self.tool_service = ToolService(config)
        self.vector_service = VectorService(config)
        
        # 创建图
        self.graph = MCPGraph("agent_service", "代理服务图")
        
        # 创建组件
        self.simple_agent = SimpleAgentComponent(
            llm_service=self.llm_service,
            tool_service=self.tool_service,
            config=config
        )
        
        self.rag_agent = RAGAgentComponent(
            llm_service=self.llm_service,
            tool_service=self.tool_service,
            vector_service=self.vector_service,
            config=config
        )
        
        # 添加组件到图
        self.graph.add_component(self.simple_agent)
        self.graph.add_component(self.rag_agent)
    
    def process_input(self, input_text: str, agent_type: str = "simple", history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理输入
        
        Args:
            input_text: 输入文本
            agent_type: 代理类型，可选值: "simple", "rag"
            history: 历史记录
        
        Returns:
            处理结果
        """
        # 准备初始状态
        initial_state = AgentState(
            input={
                "text": input_text,
                "history": history or []
            },
            tools=self.tool_service.get_available_tools()
        )
        
        # 选择代理
        if agent_type == "rag" and self.rag_agent.is_available():
            agent_name = "rag_agent"
        else:
            agent_name = "simple_agent"
        
        # 运行图
        logger.info(f"开始处理输入: {input_text[:50]}...")
        
        # 手动运行单个组件
        agent = self.graph.components[agent_name]
        result = agent.process(initial_state.input, initial_state.tools)
        
        logger.info(f"输入处理完成")
        
        return result
