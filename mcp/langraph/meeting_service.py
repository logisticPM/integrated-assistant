#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基于 langraph 的会议服务组件
提供会议记录、总结和分析功能
"""

import os
import sys
import logging
import time
import json
import datetime
from typing import Dict, Any, List, Optional, Union, Callable
from pydantic import BaseModel, Field

from mcp.langraph.core import MCPComponent, MCPState, MCPGraph
from mcp.langraph.transcription import TranscriptionService
from mcp.langraph.llm_adapter import LLMService
from mcp.langraph.vector_service import VectorService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("langraph.meeting_service")

class MeetingState(MCPState):
    """会议状态"""
    meeting_id: Optional[str] = None
    audio_path: Optional[str] = None
    transcription: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None
    action_items: Optional[List[str]] = None
    participants: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class MeetingRecorderComponent(MCPComponent):
    """会议记录组件"""
    
    def __init__(
        self,
        name: str = "meeting_recorder",
        transcription_service: TranscriptionService = None,
        config: Dict[str, Any] = None
    ):
        """
        初始化会议记录组件
        
        Args:
            name: 组件名称
            transcription_service: 转录服务
            config: 配置
        """
        super().__init__(
            name=name,
            description="会议记录组件"
        )
        
        self.transcription_service = transcription_service
        self.config = config or {}
    
    def to_runnable(self) -> Callable:
        """转换为可运行组件"""
        def _run(state: MeetingState, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            if not state.audio_path:
                raise ValueError("状态中缺少 audio_path 字段")
            
            logger.info(f"开始记录会议: {state.audio_path}")
            
            try:
                # 生成会议 ID
                if not state.meeting_id:
                    state.meeting_id = f"meeting_{int(time.time())}"
                
                # 转录音频
                transcription = self.transcription_service.transcribe(state.audio_path)
                
                # 更新状态
                return {
                    "meeting_id": state.meeting_id,
                    "transcription": transcription,
                    "metadata": {
                        "recorded_at": datetime.datetime.now().isoformat(),
                        "audio_path": state.audio_path
                    }
                }
            
            except Exception as e:
                logger.error(f"记录会议失败: {str(e)}")
                raise
        
        return _run

class MeetingSummarizerComponent(MCPComponent):
    """会议总结组件"""
    
    def __init__(
        self,
        name: str = "meeting_summarizer",
        llm_service: LLMService = None,
        config: Dict[str, Any] = None
    ):
        """
        初始化会议总结组件
        
        Args:
            name: 组件名称
            llm_service: LLM 服务
            config: 配置
        """
        super().__init__(
            name=name,
            description="会议总结组件"
        )
        
        self.llm_service = llm_service
        self.config = config or {}
    
    def to_runnable(self) -> Callable:
        """转换为可运行组件"""
        def _run(state: MeetingState, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            if not state.transcription:
                raise ValueError("状态中缺少 transcription 字段")
            
            logger.info(f"开始总结会议: {state.meeting_id}")
            
            try:
                # 获取转录文本
                transcription_text = state.transcription.get("text", "")
                
                if not transcription_text:
                    raise ValueError("转录文本为空")
                
                # 准备提示
                prompt = f"""
                请根据以下会议转录内容，提供一个简洁的会议总结，包括主要讨论点、决策和行动项。

                会议转录:
                {transcription_text}

                请提供:
                1. 会议总结 (不超过 300 字)
                2. 行动项列表 (每项以 "- " 开头)
                3. 参与者列表 (如果能从转录中识别)

                格式如下:
                ## 会议总结
                [总结内容]

                ## 行动项
                - [行动项1]
                - [行动项2]
                ...

                ## 参与者
                - [参与者1]
                - [参与者2]
                ...
                """
                
                # 调用 LLM
                response = self.llm_service.process(prompt)
                
                # 解析响应
                summary = ""
                action_items = []
                participants = []
                
                # 简单解析 Markdown 格式的响应
                sections = response.split("##")
                for section in sections:
                    section = section.strip()
                    if section.startswith("会议总结"):
                        summary = section.replace("会议总结", "").strip()
                    elif section.startswith("行动项"):
                        items = section.replace("行动项", "").strip().split("\n")
                        for item in items:
                            item = item.strip()
                            if item.startswith("- "):
                                action_items.append(item[2:])
                    elif section.startswith("参与者"):
                        parts = section.replace("参与者", "").strip().split("\n")
                        for part in parts:
                            part = part.strip()
                            if part.startswith("- "):
                                participants.append(part[2:])
                
                # 更新状态
                return {
                    "summary": summary,
                    "action_items": action_items,
                    "participants": participants
                }
            
            except Exception as e:
                logger.error(f"总结会议失败: {str(e)}")
                raise
        
        return _run

class MeetingIndexerComponent(MCPComponent):
    """会议索引组件"""
    
    def __init__(
        self,
        name: str = "meeting_indexer",
        vector_service: VectorService = None,
        config: Dict[str, Any] = None
    ):
        """
        初始化会议索引组件
        
        Args:
            name: 组件名称
            vector_service: 向量服务
            config: 配置
        """
        super().__init__(
            name=name,
            description="会议索引组件"
        )
        
        self.vector_service = vector_service
        self.config = config or {}
    
    def to_runnable(self) -> Callable:
        """转换为可运行组件"""
        def _run(state: MeetingState, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            if not state.transcription or not state.summary:
                raise ValueError("状态中缺少 transcription 或 summary 字段")
            
            logger.info(f"开始索引会议: {state.meeting_id}")
            
            try:
                # 获取转录文本和总结
                transcription_text = state.transcription.get("text", "")
                summary = state.summary
                
                if not transcription_text or not summary:
                    raise ValueError("转录文本或总结为空")
                
                # 准备元数据
                metadata = {
                    "meeting_id": state.meeting_id,
                    "recorded_at": state.metadata.get("recorded_at") if state.metadata else None,
                    "type": "meeting",
                    "summary": summary
                }
                
                # 将转录文本分段
                segments = []
                if "segments" in state.transcription:
                    for segment in state.transcription["segments"]:
                        segments.append(segment.get("text", ""))
                else:
                    # 简单分段
                    words = transcription_text.split()
                    chunk_size = 100
                    for i in range(0, len(words), chunk_size):
                        chunk = " ".join(words[i:i+chunk_size])
                        segments.append(chunk)
                
                # 添加到向量存储
                texts = [summary] + segments
                metadatas = [metadata] + [metadata.copy() for _ in segments]
                
                # 为每个段落添加索引
                for i, meta in enumerate(metadatas[1:], 1):
                    meta["segment_index"] = i
                
                # 添加到向量存储
                ids = self.vector_service.add_texts(texts, metadatas)
                
                # 更新状态
                return {
                    "indexed": True,
                    "index_ids": ids
                }
            
            except Exception as e:
                logger.error(f"索引会议失败: {str(e)}")
                raise
        
        return _run

class MeetingServiceGraph:
    """会议服务图，管理会议相关组件和流程"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化会议服务图
        
        Args:
            config: 配置
        """
        self.config = config
        
        # 创建服务
        self.transcription_service = TranscriptionService(config)
        self.llm_service = LLMService(config)
        self.vector_service = VectorService(config)
        
        # 创建图
        self.graph = MCPGraph("meeting_service", "会议服务图")
        
        # 创建组件
        self.recorder = MeetingRecorderComponent(
            transcription_service=self.transcription_service,
            config=config
        )
        
        self.summarizer = MeetingSummarizerComponent(
            llm_service=self.llm_service,
            config=config
        )
        
        self.indexer = MeetingIndexerComponent(
            vector_service=self.vector_service,
            config=config
        )
        
        # 添加组件到图
        self.graph.add_component(self.recorder)
        self.graph.add_component(self.summarizer)
        self.graph.add_component(self.indexer)
        
        # 添加边
        self.graph.add_edge("meeting_recorder", "meeting_summarizer")
        self.graph.add_edge("meeting_summarizer", "meeting_indexer")
        self.graph.add_edge("meeting_indexer", "END")
    
    def process_meeting(self, audio_path: str, meeting_id: Optional[str] = None) -> Dict[str, Any]:
        """
        处理会议
        
        Args:
            audio_path: 音频文件路径
            meeting_id: 会议 ID，如果为 None 则自动生成
        
        Returns:
            处理结果
        """
        # 检查音频文件
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        # 准备初始状态
        initial_state = MeetingState(
            meeting_id=meeting_id,
            audio_path=audio_path
        )
        
        # 运行图
        logger.info(f"开始处理会议: {audio_path}")
        result = self.graph.run(initial_state)
        logger.info(f"会议处理完成: {meeting_id or result.get('meeting_id')}")
        
        return result
    
    def search_meetings(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        搜索会议
        
        Args:
            query: 查询文本
            k: 结果数量
        
        Returns:
            搜索结果
        """
        logger.info(f"开始搜索会议: {query}")
        
        results = self.vector_service.search(query, k=k)
        
        # 过滤会议类型
        meeting_results = [
            result for result in results
            if result.get("metadata", {}).get("type") == "meeting"
        ]
        
        logger.info(f"搜索完成，找到 {len(meeting_results)} 个会议")
        
        return meeting_results
