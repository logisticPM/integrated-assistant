#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基于 langraph 的本地 LLM 组件
支持使用本地 ONNX 模型进行推理
"""

import os
import logging
import time
import json
from typing import Dict, Any, List, Optional, Union

from mcp.langraph.core import MCPComponent, MCPState

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("langraph.local_llm_component")

class LocalLLMComponent(MCPComponent):
    """本地 LLM 组件，使用 ONNX 运行时"""
    
    def __init__(self, model_path: str = None):
        """
        初始化本地 LLM 组件
        
        Args:
            model_path: 模型路径，如果为 None，则使用默认路径
        """
        super().__init__()
        
        # 如果未指定模型路径，使用默认路径
        if model_path is None:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            model_path = os.path.join(root_dir, "models", "llm")
        
        self.model_path = model_path
        self.local_llm = None
        
        # 检查本地 LLM 是否可用
        self.local_llm_available = self._check_local_llm()
    
    def _check_local_llm(self) -> bool:
        """
        检查本地 LLM 是否可用
        
        Returns:
            是否可用
        """
        try:
            from mcp.local_llm import is_local_llm_available
            return is_local_llm_available()
        except ImportError:
            logger.warning("本地 LLM 模块不可用")
            return False
        except Exception as e:
            logger.error(f"检查本地 LLM 可用性失败: {str(e)}")
            return False
    
    def _init_local_llm(self):
        """初始化本地 LLM"""
        if self.local_llm is None and self.local_llm_available:
            try:
                from mcp.local_llm import LocalLLM
                self.local_llm = LocalLLM(model_path=self.model_path)
                logger.info(f"本地 LLM 初始化成功: {self.model_path}")
            except Exception as e:
                logger.error(f"初始化本地 LLM 失败: {str(e)}")
                self.local_llm_available = False
    
    def generate_text(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> Dict[str, Any]:
        """
        生成文本
        
        Args:
            prompt: 提示文本
            max_tokens: 最大生成长度
            temperature: 温度参数
        
        Returns:
            生成结果
        """
        # 初始化本地 LLM
        self._init_local_llm()
        
        if not self.local_llm_available or self.local_llm is None:
            error_msg = "本地 LLM 不可用"
            logger.error(error_msg)
            return {"error": error_msg}
        
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 生成文本
            logger.info(f"开始通过本地 LLM 生成文本")
            result = self.local_llm.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # 计算处理时间
            processing_time = time.time() - start_time
            logger.info(f"文本生成完成，耗时: {processing_time:.2f}秒")
            
            # 构建结果
            return {
                "text": result,
                "model": "local_llm",
                "processing_time": processing_time
            }
            
        except Exception as e:
            error_msg = f"生成文本失败: {str(e)}"
            logger.exception(error_msg)
            return {"error": error_msg}
    
    def process(self, state: MCPState) -> MCPState:
        """
        处理 LLM 请求
        
        Args:
            state: 当前状态
        
        Returns:
            更新后的状态
        """
        # 检查是否需要生成文本
        if "prompt" not in state.inputs:
            logger.warning("没有提供提示词，跳过 LLM 处理")
            state.outputs["llm_response"] = {"error": "没有提供提示词"}
            return state
        
        prompt = state.inputs["prompt"]
        max_tokens = state.inputs.get("max_tokens", 512)
        temperature = state.inputs.get("temperature", 0.7)
        
        # 生成文本
        result = self.generate_text(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        # 更新状态
        state.outputs["llm_response"] = result
        
        if "error" in result:
            state.outputs["error"] = result["error"]
        else:
            state.outputs["text"] = result["text"]
        
        return state

class MockLocalLLMComponent(MCPComponent):
    """模拟本地 LLM 组件，用于测试"""
    
    def __init__(self):
        """初始化模拟本地 LLM 组件"""
        super().__init__()
    
    def generate_text(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> Dict[str, Any]:
        """
        生成文本
        
        Args:
            prompt: 提示文本
            max_tokens: 最大生成长度
            temperature: 温度参数
        
        Returns:
            生成结果
        """
        # 模拟处理延迟
        time.sleep(1)
        
        # 模拟生成结果
        return {
            "text": f"这是一个模拟的本地 LLM 响应。在实际部署中，您需要配置本地 LLM 模型来获取真实的响应。\n\n您的提示词是: {prompt[:100]}...",
            "model": "mock_local_llm",
            "processing_time": 1.0
        }
    
    def process(self, state: MCPState) -> MCPState:
        """
        处理 LLM 请求
        
        Args:
            state: 当前状态
        
        Returns:
            更新后的状态
        """
        # 检查是否需要生成文本
        if "prompt" not in state.inputs:
            logger.warning("没有提供提示词，跳过 LLM 处理")
            state.outputs["llm_response"] = {"error": "没有提供提示词"}
            return state
        
        prompt = state.inputs["prompt"]
        max_tokens = state.inputs.get("max_tokens", 512)
        temperature = state.inputs.get("temperature", 0.7)
        
        # 生成文本
        result = self.generate_text(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        # 更新状态
        state.outputs["llm_response"] = result
        state.outputs["text"] = result["text"]
        
        logger.info("模拟本地 LLM 处理完成")
        return state

def create_local_llm_component(model_path: str = None) -> MCPComponent:
    """
    创建本地 LLM 组件
    
    Args:
        model_path: 模型路径
    
    Returns:
        本地 LLM 组件实例
    """
    try:
        # 检查本地 LLM 是否可用
        from mcp.local_llm import is_local_llm_available
        
        if is_local_llm_available():
            logger.info("使用本地 LLM 组件")
            return LocalLLMComponent(model_path=model_path)
        else:
            logger.warning("本地 LLM 不可用，使用模拟组件")
            return MockLocalLLMComponent()
    
    except Exception as e:
        logger.error(f"创建本地 LLM 组件失败: {str(e)}")
        logger.warning("使用模拟本地 LLM 组件")
        return MockLocalLLMComponent()
