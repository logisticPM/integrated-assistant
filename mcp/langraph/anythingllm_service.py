#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AnythingLLM Service Adapter
提供与 AnythingLLM API 交互的功能
"""

import os
import json
import logging
import requests
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger("anythingllm_service")

class AnythingLLMService:
    """AnythingLLM API 服务适配器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化 AnythingLLM 服务
        
        Args:
            config: 配置参数，包含 API 密钥和基础 URL
        """
        self.config = config or {}
        self.api_key = self.config.get("api_key", os.environ.get("ANYTHINGLLM_API_KEY", "YM549NQ-R1R44WX-QHAPNKK-59X6VDG"))
        base_url = self.config.get("base_url", os.environ.get("ANYTHINGLLM_BASE_URL", "http://localhost:3001/api"))
        
        # Ensure base_url is using port 3001 as recommended by AnythingLLM
        if "localhost" in base_url and ":3001" not in base_url:
            base_url = base_url.replace("localhost", "localhost:3001")
        self.base_url = base_url
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        logger.info(f"初始化 AnythingLLM 服务，基础 URL: {self.base_url}")
    
    def test_connection(self) -> bool:
        """测试与 AnythingLLM 的连接"""
        try:
            response = requests.get(
                f"{self.base_url}/v1/auth",
                headers=self.headers,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"连接 AnythingLLM 失败: {e}")
            return False
    
    def get_workspaces(self) -> List[Dict[str, Any]]:
        """获取所有可用的工作区"""
        try:
            response = requests.get(
                f"{self.base_url}/v1/workspaces",
                headers=self.headers
            )
            if response.status_code == 200:
                return response.json().get("workspaces", [])
            else:
                logger.error(f"获取工作区失败: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"获取工作区异常: {e}")
            return []
    
    def get_workspace_details(self, slug: str) -> Optional[Dict[str, Any]]:
        """获取特定工作区的详细信息"""
        try:
            response = requests.get(
                f"{self.base_url}/v1/workspace/{slug}",
                headers=self.headers
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"获取工作区详情失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"获取工作区详情异常: {e}")
            return None
    
    def create_workspace(self, name: str, description: str = "") -> Optional[Dict[str, Any]]:
        """创建新的工作区"""
        try:
            data = {
                "name": name,
                "description": description
            }
            
            response = requests.post(
                f"{self.base_url}/v1/workspace/new",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"创建工作区失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"创建工作区异常: {e}")
            return None
    
    def chat_with_workspace(self, slug: str, message: str, chat_mode: str = "chat") -> Optional[Dict[str, Any]]:
        """向工作区发送聊天消息"""
        try:
            data = {
                "message": message,
                "chatMode": chat_mode  # "chat" 或 "query"
            }
            
            response = requests.post(
                f"{self.base_url}/v1/workspace/{slug}/chat",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"工作区聊天失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"工作区聊天异常: {e}")
            return None
    
    def upload_document(self, file_path: str, workspace_slug: Optional[str] = None) -> bool:
        """上传文档到 AnythingLLM"""
        try:
            url = f"{self.base_url}/v1/document/upload"
            if workspace_slug:
                url = f"{self.base_url}/v1/document/upload/{workspace_slug}"
            
            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(
                    url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files=files
                )
            
            if response.status_code == 200:
                logger.info(f"文档上传成功: {file_path}")
                return True
            else:
                logger.error(f"文档上传失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"文档上传异常: {e}")
            return False
    
    def upload_raw_text(self, text: str, title: str, workspace_slug: Optional[str] = None) -> bool:
        """上传原始文本到 AnythingLLM"""
        try:
            data = {
                "text": text,
                "title": title,
                "workspaceSlug": workspace_slug
            }
            
            response = requests.post(
                f"{self.base_url}/v1/document/raw-text",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                logger.info(f"文本上传成功: {title}")
                return True
            else:
                logger.error(f"文本上传失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"文本上传异常: {e}")
            return False
    
    def vector_search(self, slug: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """在工作区中执行向量搜索"""
        try:
            data = {
                "query": query,
                "limit": limit
            }
            
            response = requests.post(
                f"{self.base_url}/v1/workspace/{slug}/vector-search",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                return response.json().get("results", [])
            else:
                logger.error(f"向量搜索失败: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"向量搜索异常: {e}")
            return []
    
    def chat_completion(self, messages: List[Dict[str, str]], model: str = "my-workspace", temperature: float = 0.7) -> Optional[Dict[str, Any]]:
        """使用 OpenAI 兼容的聊天完成端点"""
        try:
            data = {
                "messages": messages,
                "model": model,
                "temperature": temperature
            }
            
            response = requests.post(
                f"{self.base_url}/v1/openai/chat/completions",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"聊天完成失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"聊天完成异常: {e}")
            return None
    
    def get_system_info(self) -> Optional[Dict[str, Any]]:
        """获取系统信息"""
        try:
            response = requests.get(
                f"{self.base_url}/v1/system",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json().get("settings", {})
            else:
                logger.error(f"获取系统信息失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"获取系统信息异常: {e}")
            return None

    def transcribe_audio(self, audio_path: str, workspace_slug: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        使用 AnythingLLM API 转录音频文件
        
        Args:
            audio_path: 音频文件路径
            workspace_slug: 工作区标识（可选）
        
        Returns:
            转录结果，包含文本和元数据
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(audio_path):
                logger.error(f"音频文件不存在: {audio_path}")
                return None
            
            # 尝试多个转录端点
            endpoints = [
                f"{self.base_url}/v1/audio/transcribe",
                f"{self.base_url}/audio/transcribe",
                f"{self.base_url}/v1/audio/transcriptions",
                f"{self.base_url}/audio/transcriptions",
                f"{self.base_url}/v1/transcribe",
                f"{self.base_url}/transcribe",
                f"{self.base_url}/v1/whisper/transcribe",
                f"{self.base_url}/whisper/transcribe"
            ]
            
            # 如果提供了工作区，添加工作区特定的端点
            if workspace_slug:
                workspace_endpoints = [
                    f"{self.base_url}/v1/workspace/{workspace_slug}/transcribe",
                    f"{self.base_url}/workspace/{workspace_slug}/transcribe",
                    f"{self.base_url}/v1/audio/transcribe/{workspace_slug}",
                    f"{self.base_url}/audio/transcribe/{workspace_slug}"
                ]
                endpoints = workspace_endpoints + endpoints  # 优先尝试工作区端点
            
            logger.info(f"使用 AnythingLLM API 转录音频: {audio_path}")
            
            # 尝试所有端点
            for endpoint in endpoints:
                try:
                    logger.info(f"尝试端点: {endpoint}")
                    
                    # 上传音频文件
                    with open(audio_path, 'rb') as f:
                        files = {'file': (os.path.basename(audio_path), f)}
                        data = {}
                        if workspace_slug and "workspace" not in endpoint:
                            data["workspace"] = workspace_slug
                            
                        response = requests.post(
                            endpoint,
                            headers={"Authorization": f"Bearer {self.api_key}"},
                            files=files,
                            data=data
                        )
                    
                    if response.status_code == 200:
                        result = response.json()
                        logger.info(f"音频转录成功，使用端点: {endpoint}")
                        logger.info(f"文本长度: {len(result.get('text', ''))}")
                        return result
                    else:
                        logger.warning(f"端点 {endpoint} 失败: {response.status_code} - {response.text}")
                except Exception as e:
                    logger.warning(f"端点 {endpoint} 异常: {e}")
            
            logger.error("所有转录端点都失败")
            return None
        except Exception as e:
            logger.error(f"音频转录异常: {e}")
            return None
    
    def get_stt_settings(self) -> Optional[Dict[str, Any]]:
        """
        获取语音转文本设置
        
        Returns:
            语音转文本设置
        """
        try:
            # 获取系统设置
            system_info = self.get_system_info()
            if not system_info:
                return None
            
            # 提取 STT 相关设置
            stt_settings = {
                "SpeechToTextProvider": system_info.get("SpeechToTextProvider", ""),
                "SpeechToTextLocalWhisperModel": system_info.get("SpeechToTextLocalWhisperModel", ""),
                "WhisperModelPref": system_info.get("WhisperModelPref", "")
            }
            
            return stt_settings
        except Exception as e:
            logger.error(f"获取 STT 设置异常: {e}")
            return None
    
    def update_stt_settings(self, model_name: str) -> bool:
        """
        更新语音转文本设置
        
        Args:
            model_name: Whisper 模型名称
        
        Returns:
            更新是否成功
        """
        try:
            # 构建更新数据
            data = {
                "SpeechToTextProvider": "local-whisper",
                "SpeechToTextLocalWhisperModel": model_name,
                "WhisperModelPref": model_name
            }
            
            # 发送更新请求
            response = requests.post(
                f"{self.base_url}/v1/system/update-settings",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                logger.info(f"STT 设置更新成功，模型: {model_name}")
                return True
            else:
                logger.error(f"STT 设置更新失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"更新 STT 设置异常: {e}")
            return False
    
    def list_available_whisper_models(self) -> List[str]:
        """
        获取可用的 Whisper 模型列表
        
        Returns:
            可用模型列表
        """
        # AnythingLLM 支持的 Whisper 模型列表
        return [
            "Xenova/whisper-tiny",
            "Xenova/whisper-tiny.en",
            "Xenova/whisper-base",
            "Xenova/whisper-base.en",
            "Xenova/whisper-small",
            "Xenova/whisper-small.en",
            "Xenova/whisper-medium",
            "Xenova/whisper-medium.en",
            "Xenova/whisper-large-v3"
        ]
