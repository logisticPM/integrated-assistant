#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AnythingLLM 组件
提供与 AnythingLLM 集成的 langraph 组件
"""

import os
import logging
import json
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from mcp.langraph.core import MCPComponent, MCPState
from mcp.langraph.anythingllm_service import AnythingLLMService

logger = logging.getLogger("anythingllm_component")

class AnythingLLMComponent(MCPComponent):
    """AnythingLLM 集成组件"""
    
    def __init__(self, name="anythingllm", config=None, anythingllm_service=None):
        """
        初始化 AnythingLLM 组件
        
        Args:
            name: 组件名称
            config: 配置参数
            anythingllm_service: AnythingLLM 服务实例，如果为 None 则创建新实例
        """
        super().__init__(name=name, description="与 AnythingLLM 集成的组件")
        self.config = config or {}
        self.anythingllm_service = anythingllm_service or AnythingLLMService(self.config)
        
        # 确保连接可用
        if not self.anythingllm_service.test_connection():
            logger.warning("无法连接到 AnythingLLM 服务，某些功能可能不可用")
    
    def to_runnable(self):
        """转换为可运行组件"""
        return self._run
    
    def _run(self, state: MCPState, config=None):
        """
        运行组件
        
        Args:
            state: 当前状态
            config: 运行时配置
        
        Returns:
            更新后的状态
        """
        logger.info(f"运行 {self.name} 组件")
        
        # 合并配置
        run_config = {**self.config, **(config or {})}
        
        # 获取操作类型
        operation = run_config.get("operation", "process_meeting")
        
        if operation == "process_meeting":
            return self._process_meeting(state, run_config)
        elif operation == "query_knowledge":
            return self._query_knowledge(state, run_config)
        elif operation == "generate_summary":
            return self._generate_summary(state, run_config)
        else:
            logger.warning(f"未知操作类型: {operation}")
            return state
    
    def _process_meeting(self, state: MCPState, config: Dict[str, Any]) -> MCPState:
        """
        处理会议信息并上传到 AnythingLLM
        
        Args:
            state: 当前状态
            config: 配置参数
        
        Returns:
            更新后的状态
        """
        # 检查是否有转录内容
        if not hasattr(state, "transcription") or not state.transcription:
            logger.warning("没有找到转录内容，无法处理会议")
            return state
        
        # 获取或创建工作区
        workspace_slug = config.get("workspace_slug")
        if not workspace_slug:
            # 使用会议 ID 作为工作区名称
            meeting_id = getattr(state, "meeting_id", f"meeting_{int(time.time())}")
            workspace_name = f"Meeting {meeting_id}"
            
            # 创建新工作区
            workspace = self.anythingllm_service.create_workspace(workspace_name)
            if workspace:
                workspace_slug = workspace.get("slug")
                logger.info(f"创建了新的工作区: {workspace_name} (slug: {workspace_slug})")
            else:
                logger.error("创建工作区失败")
                return state
        
        # 上传转录内容
        transcription_text = state.transcription.get("text", "")
        if transcription_text:
            title = f"Transcription - {getattr(state, 'meeting_id', 'Unknown')}"
            success = self.anythingllm_service.upload_raw_text(
                transcription_text, 
                title, 
                workspace_slug
            )
            if success:
                logger.info(f"成功上传转录内容到工作区 {workspace_slug}")
            else:
                logger.error(f"上传转录内容到工作区 {workspace_slug} 失败")
        
        # 如果有摘要，也上传摘要
        if hasattr(state, "summary") and state.summary:
            summary_text = state.summary.get("text", "")
            if summary_text:
                title = f"Summary - {getattr(state, 'meeting_id', 'Unknown')}"
                success = self.anythingllm_service.upload_raw_text(
                    summary_text, 
                    title, 
                    workspace_slug
                )
                if success:
                    logger.info(f"成功上传摘要到工作区 {workspace_slug}")
                else:
                    logger.error(f"上传摘要到工作区 {workspace_slug} 失败")
        
        # 更新状态
        setattr(state, "anythingllm_workspace", workspace_slug)
        return state
    
    def _query_knowledge(self, state: MCPState, config: Dict[str, Any]) -> MCPState:
        """
        查询 AnythingLLM 知识库
        
        Args:
            state: 当前状态
            config: 配置参数
        
        Returns:
            更新后的状态
        """
        # 获取工作区
        workspace_slug = config.get("workspace_slug") or getattr(state, "anythingllm_workspace", None)
        if not workspace_slug:
            logger.warning("没有指定工作区，无法查询知识")
            return state
        
        # 获取查询
        query = config.get("query", "")
        if not query and hasattr(state, "query"):
            query = state.query
        
        if not query:
            logger.warning("没有指定查询内容")
            return state
        
        # 执行向量搜索
        results = self.anythingllm_service.vector_search(
            workspace_slug,
            query,
            limit=config.get("limit", 5)
        )
        
        # 更新状态
        setattr(state, "knowledge_results", results)
        return state
    
    def _generate_summary(self, state: MCPState, config: Dict[str, Any]) -> MCPState:
        """
        使用 AnythingLLM 生成摘要
        
        Args:
            state: 当前状态
            config: 配置参数
        
        Returns:
            更新后的状态
        """
        # 检查是否有转录内容
        if not hasattr(state, "transcription") or not state.transcription:
            logger.warning("没有找到转录内容，无法生成摘要")
            return state
        
        transcription_text = state.transcription.get("text", "")
        if not transcription_text:
            logger.warning("转录内容为空，无法生成摘要")
            return state
        
        # 构建提示
        prompt = config.get("prompt", "请为以下会议内容生成一个详细的摘要，包括主要讨论点和决策:")
        
        # 限制转录文本长度，避免超出模型上下文窗口
        max_length = config.get("max_length", 6000)
        if len(transcription_text) > max_length:
            transcription_text = transcription_text[:max_length] + "...(内容已截断)"
        
        messages = [
            {"role": "system", "content": "你是一个专业的会议助手，擅长总结会议内容并提取关键信息。"},
            {"role": "user", "content": f"{prompt}\n\n{transcription_text}"}
        ]
        
        # 使用 AnythingLLM 的 OpenAI 兼容端点生成摘要
        model = config.get("model", "my-workspace")
        temperature = config.get("temperature", 0.3)
        
        response = self.anythingllm_service.chat_completion(
            messages,
            model=model,
            temperature=temperature
        )
        
        if response:
            # 提取生成的摘要
            try:
                summary_text = response.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # 更新状态
                if not hasattr(state, "summary"):
                    state.summary = {}
                
                state.summary["text"] = summary_text
                state.summary["source"] = "anythingllm"
                
                logger.info("成功使用 AnythingLLM 生成摘要")
            except (KeyError, IndexError) as e:
                logger.error(f"解析 AnythingLLM 响应失败: {e}")
        else:
            logger.error("使用 AnythingLLM 生成摘要失败")
        
        return state
