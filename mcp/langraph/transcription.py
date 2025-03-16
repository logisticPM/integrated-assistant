#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基于 langraph 的转录组件
包括 Whisper ONNX 和 AnythingLLM API 转录实现
"""

import os
import sys
import logging
import time
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from mcp.langraph.core import MCPComponent, TranscriptionComponent
from mcp.whisper_onnx import WhisperONNX, is_whisper_onnx_available

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("langraph.transcription")

class WhisperONNXComponent(TranscriptionComponent):
    """Whisper ONNX 转录组件"""
    
    def __init__(
        self, 
        name: str = "whisper_onnx",
        model_dir: Optional[str] = None,
        model_size: str = "base",
        language: Optional[str] = None
    ):
        """
        初始化 Whisper ONNX 转录组件
        
        Args:
            name: 组件名称
            model_dir: 模型目录，默认为 "models/whisper_onnx"
            model_size: 模型大小，默认为 "base"
            language: 语言，默认为 None (自动检测)
        """
        super().__init__(
            name=name,
            description=f"Whisper ONNX 转录组件 (model_size={model_size})"
        )
        
        # 获取项目根目录
        if model_dir is None:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            model_dir = os.path.join(root_dir, "models", "whisper_onnx")
        
        self.model_dir = model_dir
        self.model_size = model_size
        self.language = language
        self.whisper = None
        
        # 检查 Whisper ONNX 是否可用
        if not is_whisper_onnx_available():
            logger.warning("Whisper ONNX 不可用，请先运行 setup_whisper_onnx.py 安装")
        else:
            try:
                self.whisper = WhisperONNX(
                    model_dir=self.model_dir,
                    model_size=self.model_size
                )
                logger.info(f"Whisper ONNX 组件已初始化: {self.name}")
            except Exception as e:
                logger.error(f"初始化 Whisper ONNX 失败: {str(e)}")
    
    def is_available(self) -> bool:
        """
        检查组件是否可用
        
        Returns:
            是否可用
        """
        return self.whisper is not None
    
    def process(self, audio_path: str) -> Dict[str, Any]:
        """
        处理音频
        
        Args:
            audio_path: 音频文件路径
        
        Returns:
            转录结果
        """
        if not self.is_available():
            raise RuntimeError("Whisper ONNX 不可用")
        
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        try:
            logger.info(f"开始转录音频: {audio_path}")
            start_time = time.time()
            
            result = self.whisper.transcribe(audio_path, language=self.language)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            logger.info(f"转录完成，耗时: {processing_time:.2f}秒")
            
            return result
        except Exception as e:
            logger.error(f"转录失败: {str(e)}")
            raise

class AnythingLLMTranscriptionComponent(TranscriptionComponent):
    """AnythingLLM API 转录组件"""
    
    def __init__(
        self,
        name: str = "anything_llm_transcription",
        api_url: str = "http://localhost:3001",
        api_key: Optional[str] = None
    ):
        """
        初始化 AnythingLLM API 转录组件
        
        Args:
            name: 组件名称
            api_url: API URL
            api_key: API 密钥
        """
        super().__init__(
            name=name,
            description="AnythingLLM API 转录组件"
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
    
    def process(self, audio_path: str) -> Dict[str, Any]:
        """
        处理音频
        
        Args:
            audio_path: 音频文件路径
        
        Returns:
            转录结果
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        try:
            import requests
            
            logger.info(f"开始通过 AnythingLLM API 转录音频: {audio_path}")
            start_time = time.time()
            
            # 准备请求头
            headers = {}
            if self.api_key:
                headers["x-api-key"] = self.api_key
            
            # 准备文件
            with open(audio_path, "rb") as f:
                files = {"file": (os.path.basename(audio_path), f, "audio/mpeg")}
                
                # 发送请求
                response = requests.post(
                    f"{self.api_url}/api/transcribe",
                    headers=headers,
                    files=files,
                    timeout=60
                )
            
            # 检查响应
            if response.status_code != 200:
                raise Exception(f"API 请求失败: {response.status_code} {response.text}")
            
            # 解析响应
            result = response.json()
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            logger.info(f"转录完成，耗时: {processing_time:.2f}秒")
            
            return {
                "text": result.get("text", ""),
                "segments": result.get("segments", []),
                "language": result.get("language", "")
            }
        except Exception as e:
            logger.error(f"转录失败: {str(e)}")
            raise

class MockTranscriptionComponent(TranscriptionComponent):
    """模拟转录组件，用于测试和开发"""
    
    def __init__(self, name: str = "mock_transcription"):
        """
        初始化模拟转录组件
        
        Args:
            name: 组件名称
        """
        super().__init__(
            name=name,
            description="模拟转录组件"
        )
    
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
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        logger.info(f"模拟转录音频: {audio_path}")
        
        # 模拟处理时间
        time.sleep(1)
        
        # 返回模拟结果
        return {
            "text": "这是一段模拟转录的文本，用于测试和开发。",
            "segments": [
                {
                    "id": 0,
                    "start": 0,
                    "end": 5,
                    "text": "这是一段模拟转录的文本，"
                },
                {
                    "id": 1,
                    "start": 5,
                    "end": 10,
                    "text": "用于测试和开发。"
                }
            ],
            "language": "zh"
        }

class TranscriptionService:
    """转录服务，管理多个转录组件"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化转录服务
        
        Args:
            config: 配置
        """
        self.config = config
        self.components: Dict[str, TranscriptionComponent] = {}
        
        # 初始化组件
        self._init_components()
    
    def _init_components(self):
        """初始化组件"""
        # 添加 AnythingLLM API 组件
        if self.config.get("llm", {}).get("anything_llm", {}).get("enabled", False):
            api_url = self.config.get("llm", {}).get("anything_llm", {}).get("api_url", "http://localhost:3001")
            api_key = self.config.get("llm", {}).get("anything_llm", {}).get("api_key")
            
            component = AnythingLLMTranscriptionComponent(
                api_url=api_url,
                api_key=api_key
            )
            
            self.add_component(component)
        
        # 添加 Whisper ONNX 组件
        if self.config.get("meeting", {}).get("whisper", {}).get("use_onnx", False):
            model_size = self.config.get("meeting", {}).get("whisper", {}).get("model", "base")
            language = self.config.get("meeting", {}).get("whisper", {}).get("language", "auto")
            
            component = WhisperONNXComponent(
                model_size=model_size,
                language=None if language == "auto" else language
            )
            
            self.add_component(component)
        
        # 添加模拟组件
        self.add_component(MockTranscriptionComponent())
    
    def add_component(self, component: TranscriptionComponent):
        """
        添加组件
        
        Args:
            component: 要添加的组件
        """
        self.components[component.name] = component
        logger.info(f"添加转录组件: {component.name}")
    
    def get_available_component(self) -> Optional[TranscriptionComponent]:
        """
        获取可用的组件
        
        Returns:
            可用的组件，如果没有则返回 None
        """
        # 优先级：AnythingLLM API > Whisper ONNX > 模拟
        for name in ["anything_llm_transcription", "whisper_onnx", "mock_transcription"]:
            if name in self.components and self.components[name].is_available():
                return self.components[name]
        
        return None
    
    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        转录音频
        
        Args:
            audio_path: 音频文件路径
        
        Returns:
            转录结果
        
        Raises:
            RuntimeError: 没有可用的转录组件时抛出
        """
        component = self.get_available_component()
        
        if component is None:
            raise RuntimeError("没有可用的转录组件")
        
        logger.info(f"使用组件 {component.name} 转录音频")
        
        return component.process(audio_path)
