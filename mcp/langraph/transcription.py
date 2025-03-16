#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Langraph 转录组件
基于 Langraph 架构的转录服务组件
"""

import os
import time
import logging
from typing import Dict, Any, List, Optional, Union

from mcp.langraph.core import MCPComponent, MCPState

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("langraph.transcription")

class TranscriptionComponent(MCPComponent):
    """转录组件，用于将音频转换为文本"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化转录组件
        
        Args:
            config: 配置信息
        """
        super().__init__()
        self.config = config
        self.transcription_service = None
        
        # 初始化转录服务
        self._init_transcription_service()
    
    def _init_transcription_service(self):
        """初始化转录服务"""
        try:
            from mcp.transcription import TranscriptionService
            self.transcription_service = TranscriptionService(self.config)
            logger.info("转录服务初始化成功")
        except Exception as e:
            logger.error(f"初始化转录服务失败: {str(e)}")
            self.transcription_service = None
    
    def process(self, state: MCPState) -> MCPState:
        """
        处理转录请求
        
        Args:
            state: 当前状态
        
        Returns:
            更新后的状态
        """
        # 检查是否需要转录
        if "audio_path" not in state.inputs:
            logger.warning("没有提供音频路径，跳过转录")
            state.outputs["transcription"] = {"error": "没有提供音频路径"}
            return state
        
        audio_path = state.inputs["audio_path"]
        language = state.inputs.get("language")
        
        # 检查音频文件是否存在
        if not os.path.exists(audio_path):
            error_msg = f"音频文件不存在: {audio_path}"
            logger.error(error_msg)
            state.outputs["transcription"] = {"error": error_msg}
            return state
        
        # 检查转录服务是否可用
        if self.transcription_service is None:
            logger.error("转录服务不可用")
            state.outputs["transcription"] = {"error": "转录服务不可用"}
            return state
        
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 执行转录
            logger.info(f"开始转录音频: {audio_path}")
            result = self.transcription_service.transcribe(audio_path, language)
            
            # 记录处理时间
            processing_time = time.time() - start_time
            logger.info(f"转录完成，耗时: {processing_time:.2f}秒")
            
            # 更新状态
            state.outputs["transcription"] = result
            state.outputs["text"] = result.get("text", "")
            
            # 如果有错误，记录到状态中
            if "error" in result:
                state.outputs["error"] = result["error"]
            
            return state
            
        except Exception as e:
            error_msg = f"转录失败: {str(e)}"
            logger.exception(error_msg)
            
            # 更新状态
            state.outputs["transcription"] = {"error": error_msg}
            state.outputs["error"] = error_msg
            
            return state

class MockTranscriptionComponent(MCPComponent):
    """模拟转录组件，用于测试"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化模拟转录组件
        
        Args:
            config: 配置信息
        """
        super().__init__()
        self.config = config or {}
    
    def process(self, state: MCPState) -> MCPState:
        """
        处理转录请求
        
        Args:
            state: 当前状态
        
        Returns:
            更新后的状态
        """
        # 检查是否需要转录
        if "audio_path" not in state.inputs:
            logger.warning("没有提供音频路径，跳过转录")
            state.outputs["transcription"] = {"error": "没有提供音频路径"}
            return state
        
        audio_path = state.inputs["audio_path"]
        
        # 模拟处理延迟
        time.sleep(1)
        
        # 模拟转录结果
        result = {
            "text": "这是一个模拟的转录结果。在实际部署中，您需要配置 AnythingLLM API 或者 Whisper ONNX 模型来获取真实的转录结果。",
            "segments": [],
            "language": "zh",
            "model": "mock",
            "processing_time": 1.0
        }
        
        # 更新状态
        state.outputs["transcription"] = result
        state.outputs["text"] = result["text"]
        
        logger.info(f"模拟转录完成: {audio_path}")
        return state

def create_transcription_component(config: Dict[str, Any]) -> MCPComponent:
    """
    创建转录组件
    
    Args:
        config: 配置信息
    
    Returns:
        转录组件实例
    """
    # 首先检查是否启用了本地 Whisper 模型
    try:
        whisper_config = config.get("meeting", {}).get("whisper", {})
        use_local = whisper_config.get("use_local", False)
        
        if use_local:
            # 尝试创建本地 Whisper 组件
            from mcp.langraph.local_whisper_component import create_local_whisper_component
            local_whisper = create_local_whisper_component(config)
            
            if local_whisper:
                logger.info("使用本地 Whisper 组件")
                return local_whisper
    except Exception as e:
        logger.error(f"创建本地 Whisper 组件失败: {str(e)}")
    
    # 检查转录服务是否可用
    try:
        from mcp.transcription import TranscriptionService
        
        # 检查配置中的转录提供商
        provider = config["transcription"]["provider"]
        
        if provider == "whisper_onnx":
            # 检查 Whisper ONNX 是否可用
            from mcp.whisper_onnx import is_whisper_onnx_available
            if is_whisper_onnx_available():
                logger.info("使用 Whisper ONNX 转录组件")
                return TranscriptionComponent(config)
        
        elif provider == "anything_llm":
            # 检查 AnythingLLM API 是否可用
            anything_llm_enabled = config["llm"]["anything_llm"]["enabled"]
            if anything_llm_enabled:
                logger.info("使用 AnythingLLM API 转录组件")
                return TranscriptionComponent(config)
        
        # 如果没有可用的转录服务，使用模拟组件
        logger.warning("没有可用的转录服务，使用模拟转录组件")
        return MockTranscriptionComponent(config)
    
    except Exception as e:
        logger.error(f"创建转录组件失败: {str(e)}")
        logger.warning("使用模拟转录组件")
        return MockTranscriptionComponent(config)
