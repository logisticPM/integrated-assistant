#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Whisper ONNX 模型实现
基于 ONNX 运行时的 Whisper 语音转录实现
"""

import os
import logging
import numpy as np
import time
from typing import Dict, Any, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("whisper_onnx")

class WhisperONNX:
    """基于 ONNX 的 Whisper 模型实现"""
    
    def __init__(self, model_dir: str, model_size: str = "base"):
        """
        初始化 Whisper ONNX 模型
        
        Args:
            model_dir: 模型目录
            model_size: 模型大小，目前仅支持 base
        """
        self.model_dir = model_dir
        self.model_size = model_size
        self.model = None
        self.app = None
        
        # 检查模型文件是否存在
        self.encoder_path = os.path.join(model_dir, f"whisper_{model_size}_en_WhisperEncoder.onnx")
        self.decoder_path = os.path.join(model_dir, f"whisper_{model_size}_en_WhisperDecoder.onnx")
        
        if not os.path.exists(self.encoder_path) or not os.path.exists(self.decoder_path):
            raise FileNotFoundError(f"Whisper ONNX 模型文件不存在: {self.encoder_path} 或 {self.decoder_path}")
        
        # 延迟加载模型，在第一次使用时初始化
    
    def _load_model(self):
        """加载 Whisper ONNX 模型"""
        try:
            # 导入必要的模块
            import onnxruntime
            from qai_hub_models.models.whisper_base_en import App as WhisperApp
            
            # 定义 ONNX 运行时会话获取函数
            def get_onnxruntime_session(path):
                options = onnxruntime.SessionOptions()
                session = onnxruntime.InferenceSession(
                    path,
                    sess_options=options,
                    providers=["CPUExecutionProvider"]
                )
                return session
            
            # 定义编码器包装器
            class ONNXEncoderWrapper:
                def __init__(self, encoder_path):
                    self.session = get_onnxruntime_session(encoder_path)
                
                def to(self, *args):
                    return self
                
                def __call__(self, audio):
                    return self.session.run(None, {"audio": audio})
            
            # 定义解码器包装器
            class ONNXDecoderWrapper:
                def __init__(self, decoder_path):
                    self.session = get_onnxruntime_session(decoder_path)
                
                def to(self, *args):
                    return self
                
                def __call__(
                    self, x, index, k_cache_cross, v_cache_cross, k_cache_self, v_cache_self
                ):
                    return self.session.run(
                        None,
                        {
                            "x": x.astype(np.int32),
                            "index": np.array(index),
                            "k_cache_cross": k_cache_cross,
                            "v_cache_cross": v_cache_cross,
                            "k_cache_self": k_cache_self,
                            "v_cache_self": v_cache_self,
                        },
                    )
            
            # 定义 Whisper 模型类
            from qai_hub_models.models._shared.whisper.model import Whisper
            
            class WhisperBaseEnONNX(Whisper):
                def __init__(self, encoder_path, decoder_path):
                    return super().__init__(
                        ONNXEncoderWrapper(encoder_path),
                        ONNXDecoderWrapper(decoder_path),
                        num_decoder_blocks=6,
                        num_heads=8,
                        attention_dim=512,
                    )
            
            # 创建模型实例
            self.model = WhisperBaseEnONNX(self.encoder_path, self.decoder_path)
            self.app = WhisperApp(self.model)
            
            logger.info(f"Whisper ONNX 模型加载成功: {self.model_size}")
            return True
        
        except Exception as e:
            logger.error(f"加载 Whisper ONNX 模型时出错: {str(e)}")
            return False
    
    def transcribe(self, audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        转录音频文件
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码，目前不支持
        
        Returns:
            转录结果
        """
        # 首次使用时加载模型
        if self.model is None or self.app is None:
            if not self._load_model():
                raise RuntimeError("Whisper ONNX 模型加载失败")
        
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 执行转录
            logger.info(f"开始转录音频: {audio_path}")
            text = self.app.transcribe(audio_path)
            
            # 计算耗时
            end_time = time.time()
            processing_time = end_time - start_time
            
            logger.info(f"转录完成，耗时: {processing_time:.2f}秒")
            
            # 构建结果
            result = {
                "text": text,
                "segments": [],  # ONNX 版本不提供分段信息
                "language": language or "en",
                "model": f"whisper_{self.model_size}_onnx",
                "processing_time": processing_time
            }
            
            return result
        
        except Exception as e:
            logger.error(f"转录音频时出错: {str(e)}")
            raise

def is_whisper_onnx_available():
    """检查 Whisper ONNX 是否可用"""
    try:
        # 检查必要的包
        import onnxruntime
        import qai_hub_models
        import audio2numpy
        import samplerate
        
        # 检查模型文件
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        model_dir = os.path.join(root_dir, "models", "whisper_onnx")
        encoder_path = os.path.join(model_dir, "whisper_base_en_WhisperEncoder.onnx")
        decoder_path = os.path.join(model_dir, "whisper_base_en_WhisperDecoder.onnx")
        
        if not os.path.exists(encoder_path) or not os.path.exists(decoder_path):
            logger.warning(f"Whisper ONNX 模型文件不存在: {encoder_path} 或 {decoder_path}")
            return False
        
        logger.info("Whisper ONNX 可用")
        return True
    
    except ImportError as e:
        logger.warning(f"Whisper ONNX 依赖不可用: {str(e)}")
        return False
    except Exception as e:
        logger.warning(f"检查 Whisper ONNX 时出错: {str(e)}")
        return False
