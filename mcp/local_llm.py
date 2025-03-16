#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
本地 LLM 模型实现
基于 ONNX 运行时的本地 LLM 模型实现
"""

import os
import logging
import time
import json
import numpy as np
from typing import Dict, Any, List, Optional, Union

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("local_llm")

class LocalLLM:
    """基于 ONNX 的本地 LLM 模型实现"""
    
    def __init__(self, model_path: str = None):
        """
        初始化本地 LLM 模型
        
        Args:
            model_path: 模型路径，如果为 None，则使用默认路径
        """
        # 如果未指定模型路径，使用默认路径
        if model_path is None:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            model_path = os.path.join(root_dir, "models", "llm")
        
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        self.config = None
        
        # 加载模型配置
        self._load_config()
        
        # 延迟加载模型，在第一次使用时初始化
    
    def _load_config(self):
        """加载模型配置"""
        try:
            config_path = os.path.join(self.model_path, "config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                logger.info(f"加载模型配置成功: {config_path}")
            else:
                # 使用默认配置
                self.config = {
                    "model_name": "llama2",
                    "model_file": "llama2.onnx",
                    "tokenizer_file": "tokenizer.json",
                    "use_qnn": False,
                    "max_context_length": 2048,
                    "max_new_tokens": 512
                }
                logger.warning(f"模型配置文件不存在，使用默认配置: {config_path}")
        except Exception as e:
            logger.error(f"加载模型配置时出错: {str(e)}")
            # 使用默认配置
            self.config = {
                "model_name": "llama2",
                "model_file": "llama2.onnx",
                "tokenizer_file": "tokenizer.json",
                "use_qnn": False,
                "max_context_length": 2048,
                "max_new_tokens": 512
            }
    
    def _get_model_file_path(self):
        """获取模型文件路径"""
        model_file = self.config.get("model_file", "llama2.onnx")
        return os.path.join(self.model_path, model_file)
    
    def _get_tokenizer_path(self):
        """获取分词器路径"""
        tokenizer_file = self.config.get("tokenizer_file", "tokenizer.json")
        tokenizer_path = os.path.join(self.model_path, tokenizer_file)
        
        # 如果是目录，则使用 AutoTokenizer.from_pretrained
        if os.path.isdir(tokenizer_path):
            return tokenizer_path
        
        # 如果是文件，则返回文件所在目录
        return self.model_path
    
    def _get_onnxruntime_session(self, path):
        """
        获取 ONNX 运行时会话
        
        Args:
            path: 模型文件路径
        
        Returns:
            ONNX 运行时会话
        """
        try:
            import onnxruntime
            
            # 检查是否使用 QNN 执行提供程序
            if self.config.get("use_qnn", False):
                return self._get_onnxruntime_session_with_qnn_ep(path)
            
            # 使用 CPU 执行提供程序
            options = onnxruntime.SessionOptions()
            session = onnxruntime.InferenceSession(
                path,
                sess_options=options,
                providers=["CPUExecutionProvider"]
            )
            
            logger.info("使用 CPU 执行提供程序创建 ONNX 会话")
            return session
            
        except Exception as e:
            logger.error(f"创建 ONNX 会话时出错: {str(e)}")
            raise
    
    def _get_onnxruntime_session_with_qnn_ep(self, path):
        """
        使用 QNN 执行提供程序获取 ONNX 运行时会话
        
        Args:
            path: 模型文件路径
        
        Returns:
            ONNX 运行时会话
        """
        try:
            import onnxruntime
            
            options = onnxruntime.SessionOptions()
            session = onnxruntime.InferenceSession(
                path,
                sess_options=options,
                providers=["QNNExecutionProvider"],
                provider_options=[{
                    "backend_path": self.config.get("qnn_backend_path", ""),
                    "enable_htp": self.config.get("qnn_enable_htp", "1"),
                    "profiling_level": self.config.get("qnn_profiling_level", "off"),
                    "device_id": self.config.get("qnn_device_id", "0")
                }]
            )
            
            logger.info("使用 QNN 执行提供程序创建 ONNX 会话")
            return session
            
        except Exception as e:
            logger.error(f"创建 QNN ONNX 会话时出错: {str(e)}")
            # 回退到 CPU 执行提供程序
            logger.warning("回退到 CPU 执行提供程序")
            
            import onnxruntime
            options = onnxruntime.SessionOptions()
            session = onnxruntime.InferenceSession(
                path,
                sess_options=options,
                providers=["CPUExecutionProvider"]
            )
            return session
    
    def _load_model(self):
        """加载本地 LLM 模型"""
        try:
            # 导入必要的模块
            from transformers import AutoTokenizer
            
            # 获取模型和分词器路径
            model_file_path = self._get_model_file_path()
            tokenizer_path = self._get_tokenizer_path()
            
            # 检查模型文件是否存在
            if not os.path.exists(model_file_path):
                raise FileNotFoundError(f"本地 LLM 模型文件不存在: {model_file_path}")
            
            # 加载模型和分词器
            self.model = self._get_onnxruntime_session(model_file_path)
            
            # 加载分词器
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
                logger.info(f"分词器加载成功: {tokenizer_path}")
            except Exception as e:
                logger.error(f"加载分词器时出错: {str(e)}")
                raise
            
            logger.info(f"本地 LLM 模型加载成功: {model_file_path}")
            return True
        
        except Exception as e:
            logger.error(f"加载本地 LLM 模型时出错: {str(e)}")
            return False
    
    def generate(self, prompt: str, max_tokens: int = None, temperature: float = 0.7) -> str:
        """
        生成文本
        
        Args:
            prompt: 提示词
            max_tokens: 最大生成标记数，如果为 None，则使用配置中的值
            temperature: 温度参数
        
        Returns:
            生成的文本
        """
        # 首次使用时加载模型
        if self.model is None or self.tokenizer is None:
            if not self._load_model():
                raise RuntimeError("本地 LLM 模型加载失败")
        
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 如果未指定最大生成标记数，使用配置中的值
            if max_tokens is None:
                max_tokens = self.config.get("max_new_tokens", 512)
            
            # 对提示词进行分词
            inputs = self.tokenizer(prompt, return_tensors="np")
            
            # 准备输入
            onnx_inputs = {
                "input_ids": inputs["input_ids"].astype(np.int64),
                "attention_mask": inputs["attention_mask"].astype(np.int64)
            }
            
            # 添加生成参数
            if "max_length" in self.model.get_inputs_names():
                onnx_inputs["max_length"] = np.array([max_tokens], dtype=np.int64)
            elif "max_new_tokens" in self.model.get_inputs_names():
                onnx_inputs["max_new_tokens"] = np.array([max_tokens], dtype=np.int64)
            
            if "temperature" in self.model.get_inputs_names():
                onnx_inputs["temperature"] = np.array([temperature], dtype=np.float32)
            
            # 执行推理
            logger.info(f"开始生成文本，最大生成标记数: {max_tokens}，温度: {temperature}")
            outputs = self.model.run(None, onnx_inputs)
            
            # 解码输出
            output_ids = outputs[0]
            generated_text = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
            
            # 计算耗时
            end_time = time.time()
            processing_time = end_time - start_time
            
            logger.info(f"生成完成，耗时: {processing_time:.2f}秒")
            
            return generated_text
        
        except Exception as e:
            logger.error(f"生成文本时出错: {str(e)}")
            raise

def is_local_llm_available():
    """检查本地 LLM 是否可用"""
    try:
        # 检查必要的包
        import onnxruntime
        import transformers
        
        # 检查模型文件
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        model_dir = os.path.join(root_dir, "models", "llm")
        
        # 检查配置文件
        config_path = os.path.join(model_dir, "config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            model_file = config.get("model_file", "llama2.onnx")
            model_path = os.path.join(model_dir, model_file)
            
            if not os.path.exists(model_path):
                logger.warning(f"本地 LLM 模型文件不存在: {model_path}")
                return False
        else:
            # 检查默认模型文件
            model_path = os.path.join(model_dir, "llama2.onnx")
            if not os.path.exists(model_path):
                logger.warning(f"本地 LLM 模型文件不存在: {model_path}")
                return False
        
        logger.info("本地 LLM 可用")
        return True
    
    except ImportError as e:
        logger.warning(f"本地 LLM 依赖不可用: {str(e)}")
        return False
    except Exception as e:
        logger.warning(f"检查本地 LLM 时出错: {str(e)}")
        return False
