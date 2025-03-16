#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Whisper ONNX 模型实现
基于 ONNX 运行时的 Whisper 模型实现
"""

import os
import logging
import time
import numpy as np
from typing import Dict, Any, List, Optional, Union

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("whisper_onnx")

class WhisperONNX:
    """基于 ONNX 的 Whisper 模型实现"""
    
    def __init__(self, model_path: str):
        """
        初始化 Whisper ONNX 模型
        
        Args:
            model_path: 模型路径
        """
        self.model_path = model_path
        self.model = None
        
        # 检查模型文件是否存在
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Whisper 模型文件不存在: {model_path}")
        
        # 延迟加载模型，在第一次使用时初始化
    
    def _load_model(self):
        """加载 Whisper 模型"""
        try:
            # 导入必要的模块
            import onnxruntime
            
            # 定义 ONNX 运行时会话获取函数
            def get_onnxruntime_session(path):
                options = onnxruntime.SessionOptions()
                providers = ["CPUExecutionProvider"]
                
                # 检查是否可以使用 QNN 执行提供程序
                if "QNNExecutionProvider" in onnxruntime.get_available_providers():
                    providers = ["QNNExecutionProvider", "CPUExecutionProvider"]
                    logger.info("使用 QNN 执行提供程序")
                
                session = onnxruntime.InferenceSession(
                    path,
                    sess_options=options,
                    providers=providers
                )
                return session
            
            # 加载模型
            self.model = get_onnxruntime_session(self.model_path)
            
            logger.info(f"Whisper 模型加载成功: {self.model_path}")
            return True
        
        except Exception as e:
            logger.error(f"加载 Whisper 模型时出错: {str(e)}")
            return False
    
    def transcribe(self, audio_path: str) -> str:
        """
        转录音频
        
        Args:
            audio_path: 音频文件路径
        
        Returns:
            转录结果
        """
        # 首次使用时加载模型
        if self.model is None:
            if not self._load_model():
                raise RuntimeError("Whisper 模型加载失败")
        
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 加载音频
            audio_data = self._load_audio(audio_path)
            
            # 执行推理
            logger.info(f"开始转录音频: {audio_path}")
            outputs = self.model.run(None, {"audio": audio_data})
            
            # 解码输出
            transcription = self._decode_output(outputs)
            
            # 计算耗时
            end_time = time.time()
            processing_time = end_time - start_time
            
            logger.info(f"转录完成，耗时: {processing_time:.2f}秒")
            
            return transcription
        
        except Exception as e:
            logger.error(f"转录音频时出错: {str(e)}")
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

def is_whisper_onnx_available():
    """检查 Whisper ONNX 是否可用"""
    try:
        # 检查必要的包
        import onnxruntime
        import librosa
        import transformers
        
        # 检查模型文件
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        model_dir = os.path.join(root_dir, "models", "whisper")
        
        # 检查是否有任何 Whisper 模型文件
        if not os.path.exists(model_dir):
            logger.warning(f"Whisper 模型目录不存在: {model_dir}")
            return False
        
        model_files = [f for f in os.listdir(model_dir) if f.endswith(".bin") or f.endswith(".onnx")]
        if not model_files:
            logger.warning(f"Whisper 模型文件不存在")
            return False
        
        logger.info("Whisper ONNX 可用")
        return True
    
    except ImportError as e:
        logger.warning(f"Whisper ONNX 依赖不可用: {str(e)}")
        return False
    except Exception as e:
        logger.warning(f"检查 Whisper ONNX 时出错: {str(e)}")
        return False
