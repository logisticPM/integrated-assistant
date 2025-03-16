#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AnythingLLM Speech-to-Text Demo
演示如何使用 AnythingLLM 的语音转文本功能
"""

import os
import sys
import argparse
import requests
import json
import logging
import time
from pathlib import Path

# 添加项目根目录到 Python 路径
ROOT_DIR = Path(__file__).parent.parent.absolute()
sys.path.append(str(ROOT_DIR))

# 导入 AnythingLLM 服务
try:
    from mcp.langraph.anythingllm_service import AnythingLLMService
    USE_ANYTHINGLLM_SERVICE = True
except ImportError:
    USE_ANYTHINGLLM_SERVICE = False
    print("Warning: Could not import AnythingLLMService, falling back to direct API calls")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("anythingllm_stt_demo")

class AnythingLLMSTTClient:
    """AnythingLLM 语音转文本客户端"""
    
    def __init__(self, api_key=None, base_url=None):
        """
        初始化客户端
        
        Args:
            api_key: AnythingLLM API 密钥
            base_url: AnythingLLM API 基础 URL
        """
        self.api_key = api_key or os.environ.get("ANYTHINGLLM_API_KEY", "YM549NQ-R1R44WX-QHAPNKK-59X6VDG")
        self.base_url = base_url or os.environ.get("ANYTHINGLLM_BASE_URL", "http://localhost:3001/api")
        
        # 使用 AnythingLLM 服务
        if USE_ANYTHINGLLM_SERVICE:
            config = {
                "api_key": self.api_key,
                "base_url": self.base_url
            }
            self.service = AnythingLLMService(config)
            logger.info(f"使用 AnythingLLMService 初始化 STT 客户端，基础 URL: {self.base_url}")
        else:
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            logger.info(f"使用直接 API 调用初始化 STT 客户端，基础 URL: {self.base_url}")
    
    def test_connection(self):
        """测试与 AnythingLLM 的连接"""
        if USE_ANYTHINGLLM_SERVICE:
            try:
                result = self.service.test_connection()
                if result:
                    logger.info("连接 AnythingLLM 成功")
                else:
                    logger.error("连接 AnythingLLM 失败")
                return result
            except Exception as e:
                logger.error(f"连接 AnythingLLM 异常: {e}")
                return False
        else:
            try:
                response = requests.get(
                    f"{self.base_url}/v1/auth",
                    headers=self.headers,
                    timeout=5
                )
                if response.status_code == 200:
                    logger.info("连接 AnythingLLM 成功")
                    return True
                else:
                    logger.error(f"连接 AnythingLLM 失败: {response.status_code} - {response.text}")
                    return False
            except Exception as e:
                logger.error(f"连接 AnythingLLM 异常: {e}")
                return False
    
    def get_system_settings(self):
        """获取系统设置"""
        if USE_ANYTHINGLLM_SERVICE:
            try:
                return self.service.get_system_info()
            except Exception as e:
                logger.error(f"获取系统设置异常: {e}")
                return None
        else:
            try:
                response = requests.get(
                    f"{self.base_url}/v1/system",
                    headers=self.headers
                )
                if response.status_code == 200:
                    settings = response.json().get("settings", {})
                    logger.info("成功获取系统设置")
                    return settings
                else:
                    logger.error(f"获取系统设置失败: {response.status_code} - {response.text}")
                    return None
            except Exception as e:
                logger.error(f"获取系统设置异常: {e}")
                return None
    
    def get_stt_settings(self):
        """获取语音转文本设置"""
        if USE_ANYTHINGLLM_SERVICE:
            try:
                return self.service.get_stt_settings()
            except Exception as e:
                logger.error(f"获取 STT 设置异常: {e}")
                return None
        else:
            settings = self.get_system_settings()
            if not settings:
                return None
            
            stt_settings = {
                "SpeechToTextProvider": settings.get("SpeechToTextProvider"),
                "SpeechToTextLocalWhisperModel": settings.get("SpeechToTextLocalWhisperModel"),
                "WhisperProvider": settings.get("WhisperProvider"),
                "WhisperModelPref": settings.get("WhisperModelPref")
            }
            
            return stt_settings
    
    def update_stt_settings(self, model=None, provider="local_whisper"):
        """
        更新语音转文本设置
        
        Args:
            model: Whisper 模型名称
            provider: 提供者，默认为 local_whisper
        
        Returns:
            bool: 是否更新成功
        """
        if USE_ANYTHINGLLM_SERVICE and model:
            try:
                return self.service.update_stt_settings(model)
            except Exception as e:
                logger.error(f"更新 STT 设置异常: {e}")
                return False
        else:
            try:
                current_settings = self.get_system_settings()
                if not current_settings:
                    return False
                
                # 准备更新的设置
                update_data = {
                    "SpeechToTextProvider": provider
                }
                
                if model:
                    update_data["SpeechToTextLocalWhisperModel"] = model
                    update_data["WhisperModelPref"] = model
                
                # 发送更新请求
                response = requests.post(
                    f"{self.base_url}/v1/system",
                    headers=self.headers,
                    json={"settings": update_data}
                )
                
                if response.status_code == 200:
                    logger.info(f"成功更新语音转文本设置: {update_data}")
                    return True
                else:
                    logger.error(f"更新语音转文本设置失败: {response.status_code} - {response.text}")
                    return False
            except Exception as e:
                logger.error(f"更新语音转文本设置异常: {e}")
                return False
    
    def list_whisper_models(self):
        """列出可用的 Whisper 模型"""
        if USE_ANYTHINGLLM_SERVICE:
            try:
                return self.service.list_available_whisper_models()
            except Exception as e:
                logger.error(f"获取 Whisper 模型列表异常: {e}")
                # 失败后使用硬编码列表
        
        # AnythingLLM 使用的 Whisper 模型来自 Xenova
        models = [
            "Xenova/whisper-tiny",
            "Xenova/whisper-base",
            "Xenova/whisper-small",
            "Xenova/whisper-medium",
            "Xenova/whisper-large-v3",
            "Xenova/whisper-tiny.en",
            "Xenova/whisper-base.en",
            "Xenova/whisper-small.en",
            "Xenova/whisper-medium.en"
        ]
        return models
    
    def transcribe_audio(self, audio_file_path, workspace_slug=None):
        """
        转录音频文件
        
        Args:
            audio_file_path: 音频文件路径
            workspace_slug: 可选的工作区 slug，如果提供则将转录结果保存到该工作区
        
        Returns:
            dict: 转录结果
        """
        if USE_ANYTHINGLLM_SERVICE:
            try:
                return self.service.transcribe_audio(audio_file_path, workspace_slug)
            except Exception as e:
                logger.error(f"转录音频文件异常: {e}")
                return None
        else:
            try:
                # 检查文件是否存在
                if not os.path.exists(audio_file_path):
                    logger.error(f"音频文件不存在: {audio_file_path}")
                    return None
                
                # 构建 URL
                url = f"{self.base_url}/v1/audio/transcribe"
                if workspace_slug:
                    url = f"{self.base_url}/v1/audio/transcribe/{workspace_slug}"
                
                # 准备文件
                with open(audio_file_path, "rb") as f:
                    files = {"file": f}
                    
                    # 发送请求
                    response = requests.post(
                        url,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        files=files
                    )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"成功转录音频文件: {audio_file_path}")
                    return result
                else:
                    logger.error(f"转录音频文件失败: {response.status_code} - {response.text}")
                    return None
            except Exception as e:
                logger.error(f"转录音频文件异常: {e}")
                return None

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AnythingLLM 语音转文本演示")
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # 获取设置子命令
    get_parser = subparsers.add_parser("get", help="获取当前语音转文本设置")
    
    # 更新设置子命令
    update_parser = subparsers.add_parser("update", help="更新语音转文本设置")
    update_parser.add_argument("--model", help="Whisper 模型名称")
    
    # 列出模型子命令
    list_parser = subparsers.add_parser("list-models", help="列出可用的 Whisper 模型")
    
    # 转录子命令
    transcribe_parser = subparsers.add_parser("transcribe", help="转录音频文件")
    transcribe_parser.add_argument("--audio", required=True, help="音频文件路径")
    transcribe_parser.add_argument("--workspace", help="工作区 slug")
    
    # 解析参数
    args = parser.parse_args()
    
    # 创建客户端
    client = AnythingLLMSTTClient()
    
    # 测试连接
    if not client.test_connection():
        logger.error("无法连接到 AnythingLLM，请确保服务正在运行")
        return 1
    
    # 处理命令
    if args.command == "get":
        settings = client.get_stt_settings()
        if settings:
            print(json.dumps(settings, indent=2))
        else:
            logger.error("获取设置失败")
            return 1
    
    elif args.command == "update":
        if not args.model:
            logger.error("请指定要使用的 Whisper 模型")
            return 1
        
        success = client.update_stt_settings(model=args.model)
        if success:
            print(f"成功更新语音转文本设置，使用模型: {args.model}")
        else:
            logger.error("更新设置失败")
            return 1
    
    elif args.command == "list-models":
        models = client.list_whisper_models()
        print("可用的 Whisper 模型:")
        for model in models:
            print(f"  - {model}")
    
    elif args.command == "transcribe":
        result = client.transcribe_audio(args.audio, args.workspace)
        if result:
            print("转录结果:")
            print("-" * 50)
            print(result.get("text", "无转录结果"))
            print("-" * 50)
            
            # 如果有工作区信息，显示
            if "workspace" in result:
                print(f"已保存到工作区: {result['workspace']}")
        else:
            logger.error("转录失败")
            return 1
    
    else:
        parser.print_help()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
