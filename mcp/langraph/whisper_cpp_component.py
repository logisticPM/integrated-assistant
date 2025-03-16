#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Whisper.cpp 组件
基于 Langraph 架构的 Whisper.cpp 服务组件，针对 Snapdragon XElite 优化
"""

import os
import time
import json
import logging
import requests
import subprocess
import threading
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

import numpy as np

from mcp.langraph.core import MCPComponent, MCPState

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("langraph.whisper_cpp")

class WhisperCppComponent(MCPComponent):
    """Whisper.cpp 组件，用于将音频转换为文本，针对 Snapdragon XElite 优化"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 Whisper.cpp 组件
        
        Args:
            config: 配置信息
        """
        super().__init__()
        self.config = config
        self.whisper_config = config.get("meeting", {}).get("whisper", {})
        
        # Whisper.cpp 服务配置
        self.server_host = self.whisper_config.get("server_host", "127.0.0.1")
        self.server_port = self.whisper_config.get("server_port", 8178)
        self.model_path = self.whisper_config.get("model_path", "")
        self.model_name = self.whisper_config.get("model_name", "small")
        self.server_process = None
        self.server_url = f"http://{self.server_host}:{self.server_port}"
        
        # Snapdragon XElite 优化配置
        self.use_xelite = self.whisper_config.get("use_xelite", True)
        self.xelite_config = {
            "num_threads": self.whisper_config.get("num_threads", 8),
            "use_gpu": self.whisper_config.get("use_gpu", True),
            "use_dsp": self.whisper_config.get("use_dsp", True),
            "use_npu": self.whisper_config.get("use_npu", True)
        }
        
        # 服务状态
        self.is_server_running = False
        self.server_lock = threading.Lock()
        
        # 初始化服务
        self._init_server()
    
    def _init_server(self):
        """初始化 Whisper.cpp 服务"""
        try:
            # 检查服务是否已经运行
            if self._check_server_running():
                logger.info(f"Whisper.cpp 服务已经在运行: {self.server_url}")
                self.is_server_running = True
                return
            
            # 检查模型路径
            if not self.model_path or not os.path.exists(self.model_path):
                logger.error(f"Whisper.cpp 模型路径不存在: {self.model_path}")
                return
            
            # 启动服务
            self._start_server()
            
        except Exception as e:
            logger.error(f"初始化 Whisper.cpp 服务失败: {str(e)}")
    
    def _check_server_running(self) -> bool:
        """
        检查 Whisper.cpp 服务是否运行
        
        Returns:
            服务是否运行
        """
        try:
            response = requests.get(f"{self.server_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _start_server(self):
        """启动 Whisper.cpp 服务"""
        with self.server_lock:
            if self.is_server_running:
                return
            
            try:
                # 获取项目根目录
                root_dir = Path(__file__).parent.parent.parent.absolute()
                
                # 构建服务启动命令
                server_dir = os.path.join(root_dir, "whisper_cpp")
                server_exe = os.path.join(server_dir, "whisper-server.exe")
                model_file = os.path.join(self.model_path, f"ggml-{self.model_name}.bin")
                
                # 检查服务可执行文件是否存在
                if not os.path.exists(server_exe):
                    logger.error(f"Whisper.cpp 服务可执行文件不存在: {server_exe}")
                    return
                
                # 检查模型文件是否存在
                if not os.path.exists(model_file):
                    logger.error(f"Whisper.cpp 模型文件不存在: {model_file}")
                    return
                
                # 构建命令行参数
                cmd = [
                    server_exe,
                    "--model", model_file,
                    "--host", self.server_host,
                    "--port", str(self.server_port),
                    "--diarize",
                    "--print-progress"
                ]
                
                # 添加 Snapdragon XElite 优化参数
                if self.use_xelite:
                    cmd.extend([
                        "--threads", str(self.xelite_config["num_threads"]),
                        "--use-gpu", "1" if self.xelite_config["use_gpu"] else "0",
                        "--use-dsp", "1" if self.xelite_config["use_dsp"] else "0",
                        "--use-npu", "1" if self.xelite_config["use_npu"] else "0"
                    ])
                
                # 启动服务进程
                logger.info(f"启动 Whisper.cpp 服务: {' '.join(cmd)}")
                self.server_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # 等待服务启动
                for _ in range(10):
                    if self._check_server_running():
                        self.is_server_running = True
                        logger.info(f"Whisper.cpp 服务启动成功: {self.server_url}")
                        return
                    time.sleep(1)
                
                logger.error("Whisper.cpp 服务启动超时")
                
            except Exception as e:
                logger.error(f"启动 Whisper.cpp 服务失败: {str(e)}")
    
    def _stop_server(self):
        """停止 Whisper.cpp 服务"""
        with self.server_lock:
            if not self.is_server_running or self.server_process is None:
                return
            
            try:
                # 终止服务进程
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
                self.is_server_running = False
                logger.info("Whisper.cpp 服务已停止")
            except Exception as e:
                logger.error(f"停止 Whisper.cpp 服务失败: {str(e)}")
                # 强制终止进程
                try:
                    self.server_process.kill()
                    self.is_server_running = False
                except:
                    pass
    
    def transcribe(self, audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        转录音频
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码
        
        Returns:
            转录结果
        """
        if not self.is_server_running:
            self._init_server()
            
            if not self.is_server_running:
                return {"error": "Whisper.cpp 服务不可用"}
        
        try:
            # 检查音频文件是否存在
            if not os.path.exists(audio_path):
                return {"error": f"音频文件不存在: {audio_path}"}
            
            # 记录开始时间
            start_time = time.time()
            
            # 准备请求参数
            params = {}
            if language:
                params["language"] = language
            
            # 发送转录请求
            with open(audio_path, "rb") as f:
                files = {"file": f}
                response = requests.post(
                    f"{self.server_url}/inference",
                    params=params,
                    files=files,
                    timeout=300  # 5分钟超时
                )
            
            # 检查响应状态
            if response.status_code != 200:
                return {"error": f"转录请求失败，状态码: {response.status_code}"}
            
            # 解析响应
            result = response.json()
            
            # 计算处理时间
            processing_time = time.time() - start_time
            
            # 构建转录结果
            transcription = {
                "text": result.get("text", ""),
                "segments": result.get("segments", []),
                "language": result.get("language", language or "auto"),
                "model": f"whisper_cpp_{self.model_name}",
                "processing_time": processing_time
            }
            
            logger.info(f"转录完成，耗时: {processing_time:.2f}秒")
            return transcription
            
        except Exception as e:
            logger.error(f"转录失败: {str(e)}")
            return {"error": f"转录失败: {str(e)}"}
    
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
        
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 执行转录
            logger.info(f"开始转录音频: {audio_path}")
            result = self.transcribe(audio_path, language)
            
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
    
    def __del__(self):
        """析构函数，确保服务进程被终止"""
        self._stop_server()

def create_whisper_cpp_component(config: Dict[str, Any]) -> Optional[WhisperCppComponent]:
    """
    创建 Whisper.cpp 组件
    
    Args:
        config: 配置信息
    
    Returns:
        Whisper.cpp 组件实例
    """
    try:
        # 检查配置
        whisper_config = config.get("meeting", {}).get("whisper", {})
        use_cpp = whisper_config.get("use_cpp", False)
        
        if not use_cpp:
            logger.info("未启用 Whisper.cpp，跳过创建组件")
            return None
        
        # 创建组件
        component = WhisperCppComponent(config)
        
        # 检查服务是否可用
        if component.is_server_running:
            logger.info("Whisper.cpp 组件创建成功")
            return component
        else:
            logger.warning("Whisper.cpp 服务不可用，组件创建失败")
            return None
        
    except Exception as e:
        logger.error(f"创建 Whisper.cpp 组件失败: {str(e)}")
        return None
