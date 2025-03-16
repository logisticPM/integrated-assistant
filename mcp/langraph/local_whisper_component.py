#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
本地 Whisper 组件
基于 Langraph 架构的本地 Whisper 模型组件
"""

import os
import time
import json
import logging
from typing import Dict, Any, List, Optional, Union

import numpy as np

from mcp.langraph.core import MCPComponent, MCPState

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("langraph.local_whisper")

class LocalWhisperComponent(MCPComponent):
    """本地 Whisper 组件，用于将音频转换为文本"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化本地 Whisper 组件
        
        Args:
            config: 配置信息
        """
        super().__init__()
        self.config = config
        self.whisper_config = config.get("meeting", {}).get("whisper", {})
        self.model_path = self.whisper_config.get("model_path", "")
        self.use_onnx = self.whisper_config.get("use_onnx", True)
        self.use_qnn = self.whisper_config.get("use_qnn", False)
        self.language = self.whisper_config.get("language", "auto")
        
        # 初始化 Whisper 模型
        self.whisper_model = None
        self._init_whisper_model()
    
    def _init_whisper_model(self):
        """初始化 Whisper 模型"""
        try:
            # 检查模型路径是否存在
            if not os.path.exists(self.model_path):
                logger.error(f"Whisper 模型路径不存在: {self.model_path}")
                return
            
            # 加载模型配置
            config_path = os.path.join(self.model_path, "config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    model_config = json.load(f)
                
                # 获取模型文件路径
                model_file = model_config.get("model_file", "")
                model_file_path = os.path.join(self.model_path, model_file)
                
                if not os.path.exists(model_file_path):
                    logger.error(f"Whisper 模型文件不存在: {model_file_path}")
                    return
                
                # 根据配置决定是否使用 ONNX
                use_onnx = model_config.get("use_onnx", self.use_onnx)
                
                if use_onnx:
                    # 初始化 ONNX 模型
                    self._init_onnx_model(model_file_path)
                else:
                    # 初始化普通 Whisper 模型
                    self._init_regular_model(model_file_path)
            else:
                # 尝试查找模型文件
                model_files = [f for f in os.listdir(self.model_path) 
                              if f.endswith(".bin") or f.endswith(".onnx")]
                
                if not model_files:
                    logger.error(f"未找到 Whisper 模型文件")
                    return
                
                # 使用第一个找到的模型文件
                model_file_path = os.path.join(self.model_path, model_files[0])
                
                # 根据文件扩展名判断是否为 ONNX 模型
                if model_file_path.endswith(".onnx"):
                    self._init_onnx_model(model_file_path)
                else:
                    self._init_regular_model(model_file_path)
        
        except Exception as e:
            logger.error(f"初始化 Whisper 模型失败: {str(e)}")
    
    def _init_onnx_model(self, model_path: str):
        """
        初始化 ONNX 模型
        
        Args:
            model_path: 模型文件路径
        """
        try:
            import onnxruntime
            
            # 获取可用的执行提供程序
            available_providers = onnxruntime.get_available_providers()
            
            # 设置执行提供程序
            providers = ["CPUExecutionProvider"]
            provider_options = [{}]
            
            # 如果启用了 QNN 并且可用，则使用 QNN 执行提供程序
            if self.use_qnn and "QNNExecutionProvider" in available_providers:
                providers = ["QNNExecutionProvider", "CPUExecutionProvider"]
                provider_options = [
                    {
                        "backend_path": "",
                        "profiling_level": 0,
                        "debug_level": 0,
                        "enable_htp": 1
                    },
                    {}
                ]
                logger.info("使用 QNN 执行提供程序")
            
            # 创建 ONNX 运行时会话
            options = onnxruntime.SessionOptions()
            self.whisper_model = onnxruntime.InferenceSession(
                model_path,
                sess_options=options,
                providers=providers,
                provider_options=provider_options
            )
            
            logger.info(f"Whisper ONNX 模型加载成功: {model_path}")
        
        except Exception as e:
            logger.error(f"初始化 ONNX 模型失败: {str(e)}")
            raise
    
    def _init_regular_model(self, model_path: str):
        """
        初始化普通 Whisper 模型
        
        Args:
            model_path: 模型文件路径
        """
        try:
            # 尝试导入 whisper 模块
            import whisper
            
            # 加载模型
            self.whisper_model = whisper.load_model(model_path)
            
            logger.info(f"Whisper 模型加载成功: {model_path}")
        
        except ImportError:
            logger.error("未安装 whisper 模块，无法加载普通 Whisper 模型")
            raise
        except Exception as e:
            logger.error(f"初始化普通 Whisper 模型失败: {str(e)}")
            raise
    
    def _load_audio(self, audio_path: str) -> np.ndarray:
        """
        加载音频文件
        
        Args:
            audio_path: 音频文件路径
        
        Returns:
            音频数据
        """
        try:
            import librosa
            
            # 加载音频
            audio, sr = librosa.load(audio_path, sr=16000, mono=True)
            
            # 确保音频长度不超过模型支持的最大长度（30秒）
            max_length = 30 * 16000
            if len(audio) > max_length:
                logger.warning(f"音频长度超过30秒，将被截断")
                audio = audio[:max_length]
            
            # 转换为 float32 类型
            audio = audio.astype(np.float32)
            
            return audio.reshape(1, -1)
        
        except Exception as e:
            logger.error(f"加载音频时出错: {str(e)}")
            raise
    
    def _decode_output(self, outputs: List[np.ndarray]) -> str:
        """
        解码模型输出
        
        Args:
            outputs: 模型输出
        
        Returns:
            解码后的文本
        """
        # 这里需要根据具体的模型输出格式进行解码
        # 由于不同的 Whisper ONNX 模型输出格式可能不同，这里使用简化的实现
        
        # 假设输出是文本 ID
        if len(outputs) > 0:
            # 导入分词器
            from transformers import WhisperTokenizer
            
            try:
                tokenizer = WhisperTokenizer.from_pretrained("openai/whisper-base")
                text_ids = outputs[0][0]
                text = tokenizer.decode(text_ids, skip_special_tokens=True)
                return text
            except Exception as e:
                logger.error(f"解码输出时出错: {str(e)}")
                # 返回原始输出的字符串表示
                return str(outputs)
        
        return ""
    
    def _transcribe_with_onnx(self, audio_path: str) -> Dict[str, Any]:
        """
        使用 ONNX 模型转录音频
        
        Args:
            audio_path: 音频文件路径
        
        Returns:
            转录结果
        """
        # 加载音频
        audio_data = self._load_audio(audio_path)
        
        # 执行推理
        outputs = self.whisper_model.run(None, {"audio": audio_data})
        
        # 解码输出
        text = self._decode_output(outputs)
        
        return {
            "text": text,
            "segments": [],  # ONNX 模型不提供分段信息
            "language": self.language,
            "model": "whisper_onnx"
        }
    
    def _transcribe_with_regular(self, audio_path: str) -> Dict[str, Any]:
        """
        使用普通 Whisper 模型转录音频
        
        Args:
            audio_path: 音频文件路径
        
        Returns:
            转录结果
        """
        # 执行转录
        result = self.whisper_model.transcribe(
            audio_path,
            language=None if self.language == "auto" else self.language
        )
        
        # 提取文本和分段信息
        text = result.get("text", "")
        segments = result.get("segments", [])
        
        return {
            "text": text,
            "segments": segments,
            "language": result.get("language", self.language),
            "model": "whisper"
        }
    
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
        
        # 检查音频文件是否存在
        if not os.path.exists(audio_path):
            error_msg = f"音频文件不存在: {audio_path}"
            logger.error(error_msg)
            state.outputs["transcription"] = {"error": error_msg}
            return state
        
        # 检查模型是否可用
        if self.whisper_model is None:
            logger.error("Whisper 模型不可用")
            state.outputs["transcription"] = {"error": "Whisper 模型不可用"}
            return state
        
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 执行转录
            logger.info(f"开始转录音频: {audio_path}")
            
            # 根据模型类型选择转录方法
            if hasattr(self.whisper_model, "run"):
                # ONNX 模型
                result = self._transcribe_with_onnx(audio_path)
            else:
                # 普通 Whisper 模型
                result = self._transcribe_with_regular(audio_path)
            
            # 记录处理时间
            processing_time = time.time() - start_time
            result["processing_time"] = processing_time
            
            logger.info(f"转录完成，耗时: {processing_time:.2f}秒")
            
            # 更新状态
            state.outputs["transcription"] = result
            state.outputs["text"] = result.get("text", "")
            
            return state
            
        except Exception as e:
            error_msg = f"转录失败: {str(e)}"
            logger.exception(error_msg)
            
            # 更新状态
            state.outputs["transcription"] = {"error": error_msg}
            state.outputs["error"] = error_msg
            
            return state

def create_local_whisper_component(config: Dict[str, Any]) -> MCPComponent:
    """
    创建本地 Whisper 组件
    
    Args:
        config: 配置信息
    
    Returns:
        本地 Whisper 组件实例
    """
    try:
        # 检查配置
        whisper_config = config.get("meeting", {}).get("whisper", {})
        use_local = whisper_config.get("use_local", False)
        
        if not use_local:
            logger.warning("未启用本地 Whisper 模型")
            return None
        
        # 检查模型路径
        model_path = whisper_config.get("model_path", "")
        if not model_path or not os.path.exists(model_path):
            logger.error(f"Whisper 模型路径不存在: {model_path}")
            return None
        
        # 创建组件
        logger.info("创建本地 Whisper 组件")
        return LocalWhisperComponent(config)
    
    except Exception as e:
        logger.error(f"创建本地 Whisper 组件失败: {str(e)}")
        return None
