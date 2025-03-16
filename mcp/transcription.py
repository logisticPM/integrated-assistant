#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
转录服务模块 - 提供音频转文本功能
支持多种转录提供商，包括 AnythingLLM API 和本地 Whisper ONNX 模型
"""

import os
import json
import time
import logging
import requests
from typing import Dict, Any, List, Optional, Union

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("transcription_service")

class TranscriptionService:
    """转录服务类，处理音频转文本请求"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化转录服务
        
        Args:
            config: 服务配置
        """
        self.config = config
        self.provider = config["transcription"]["provider"]
        
        # AnythingLLM 集成配置
        self.anything_llm_enabled = config["llm"]["anything_llm"]["enabled"]
        self.anything_llm_api_url = config["llm"]["anything_llm"]["api_url"]
        self.anything_llm_api_key = config["llm"]["anything_llm"]["api_key"]
        
        # Whisper ONNX 配置
        self.whisper_model_path = config["transcription"].get("whisper_model_path", "")
        self.whisper_onnx = None
        self.whisper_onnx_available = self._check_whisper_onnx()
    
    def _check_whisper_onnx(self) -> bool:
        """检查 Whisper ONNX 是否可用"""
        if self.provider != "whisper_onnx":
            return False
            
        try:
            # 检查 Whisper ONNX 模块是否可用
            from mcp.whisper_onnx import is_whisper_onnx_available
            return is_whisper_onnx_available()
        except ImportError:
            logger.warning("Whisper ONNX 模块不可用")
            return False
        except Exception as e:
            logger.warning(f"检查 Whisper ONNX 时出错: {str(e)}")
            return False
    
    def _init_whisper_onnx(self):
        """初始化 Whisper ONNX"""
        if self.whisper_onnx is None and self.whisper_onnx_available:
            try:
                from mcp.whisper_onnx import WhisperONNX
                self.whisper_onnx = WhisperONNX(
                    model_path=self.whisper_model_path
                )
                logger.info("Whisper ONNX 模型初始化成功")
            except Exception as e:
                logger.error(f"初始化 Whisper ONNX 模型失败: {str(e)}")
                self.whisper_onnx_available = False
    
    def _call_anything_llm(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用 AnythingLLM API
        
        Args:
            endpoint: API 端点
            data: 请求数据
        
        Returns:
            API 响应
        
        Raises:
            Exception: API 调用失败时抛出异常
        """
        if not self.anything_llm_enabled:
            raise Exception("AnythingLLM 集成未启用")
        
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.anything_llm_api_key:
            headers["Authorization"] = f"Bearer {self.anything_llm_api_key}"
        
        try:
            response = requests.post(
                f"{self.anything_llm_api_url}/{endpoint}",
                headers=headers,
                json=data,
                timeout=60
            )
            
            response.raise_for_status()
            return response.json()
        
        except requests.RequestException as e:
            logger.exception(f"AnythingLLM API 调用失败: {endpoint}")
            raise Exception(f"AnythingLLM API 调用失败: {str(e)}")
    
    def transcribe(self, audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        转录音频
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码，默认为 None（自动检测）
        
        Returns:
            转录结果，包含文本和元数据
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        # 记录开始时间
        start_time = time.time()
        
        try:
            result = None
            
            # 根据提供商选择转录方法
            if self.provider == "anything_llm" and self.anything_llm_enabled:
                # 使用 AnythingLLM API 转录
                logger.info(f"使用 AnythingLLM API 转录音频: {audio_path}")
                
                with open(audio_path, "rb") as audio_file:
                    # 将音频文件编码为 base64
                    import base64
                    audio_base64 = base64.b64encode(audio_file.read()).decode("utf-8")
                
                # 调用 API
                api_response = self._call_anything_llm("transcribe", {
                    "audio": audio_base64,
                    "language": language
                })
                
                # 构建结果
                result = {
                    "text": api_response.get("text", ""),
                    "segments": api_response.get("segments", []),
                    "language": api_response.get("language", language or "auto"),
                    "model": api_response.get("model", "anything_llm"),
                    "processing_time": time.time() - start_time
                }
            
            elif self.provider == "whisper_onnx" and self.whisper_onnx_available:
                # 使用本地 Whisper ONNX 模型转录
                logger.info(f"使用 Whisper ONNX 转录音频: {audio_path}")
                
                # 初始化 Whisper ONNX
                self._init_whisper_onnx()
                
                if self.whisper_onnx:
                    # 执行转录
                    text = self.whisper_onnx.transcribe(audio_path)
                    
                    # 构建结果
                    result = {
                        "text": text,
                        "segments": [],  # 本地模型不提供分段信息
                        "language": language or "auto",
                        "model": "whisper_onnx",
                        "processing_time": time.time() - start_time
                    }
                else:
                    raise Exception("Whisper ONNX 模型未初始化")
            
            else:
                # 使用模拟转录（用于测试）
                logger.warning(f"没有可用的转录提供商，使用模拟转录: {audio_path}")
                
                # 模拟处理延迟
                time.sleep(2)
                
                # 构建模拟结果
                result = {
                    "text": "这是一个模拟的转录结果。在实际部署中，您需要配置 AnythingLLM API 或者 Whisper ONNX 模型来获取真实的转录结果。",
                    "segments": [],
                    "language": language or "zh",
                    "model": "mock",
                    "processing_time": time.time() - start_time
                }
            
            logger.info(f"转录完成，耗时: {result['processing_time']:.2f}秒")
            return result
        
        except Exception as e:
            logger.exception(f"转录音频失败: {audio_path}")
            
            # 返回错误结果
            return {
                "text": f"转录失败: {str(e)}",
                "segments": [],
                "language": language or "auto",
                "model": "error",
                "processing_time": time.time() - start_time,
                "error": str(e)
            }
