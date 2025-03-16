#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Integrated Assistant Startup Script
One-click startup for the integrated assistant service
"""

import os
import sys
import subprocess
import logging
import argparse
import webbrowser
import time
from pathlib import Path
import yaml
import requests
import importlib.util
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("start")

# Project root directory
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def check_api_transcription(config):
    """检查 AnythingLLM API 转录服务是否可用"""
    if not config["llm"]["anything_llm"]["enabled"]:
        return False
        
    try:
        # 检查 AnythingLLM API 是否可用
        api_url = config["llm"]["anything_llm"]["api_url"]
        api_key = config["llm"]["anything_llm"]["api_key"]
        
        headers = {}
        if api_key:
            headers["x-api-key"] = api_key
            
        response = requests.get(
            f"{api_url}/api/health",
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            logger.info("AnythingLLM API 转录服务可用")
            return True
        else:
            logger.warning(f"AnythingLLM API 不可用，状态码: {response.status_code}")
            return False
    except Exception as e:
        logger.warning(f"检查 AnythingLLM API 时出错: {str(e)}")
        return False

def check_whisper_onnx_installation():
    """检查 Whisper ONNX 是否已安装"""
    try:
        # 检查必要的包
        for package in ["onnxruntime", "qai_hub_models", "audio2numpy", "samplerate"]:
            spec = importlib.util.find_spec(package)
            if spec is None:
                logger.warning(f"{package} 未安装")
                return False
        
        # 检查模型文件
        model_dir = os.path.join(ROOT_DIR, "models", "whisper_onnx")
        encoder_path = os.path.join(model_dir, "whisper_base_en_WhisperEncoder.onnx")
        decoder_path = os.path.join(model_dir, "whisper_base_en_WhisperDecoder.onnx")
        
        if not os.path.exists(encoder_path) or not os.path.exists(decoder_path):
            logger.warning(f"Whisper ONNX 模型文件不存在: {encoder_path} 或 {decoder_path}")
            return False
        
        logger.info("Whisper ONNX 已安装")
        return True
    
    except Exception as e:
        logger.warning(f"检查 Whisper ONNX 安装时出错: {str(e)}")
        return False

def load_config():
    """加载配置文件"""
    config_path = os.path.join(ROOT_DIR, "config.yaml")
    
    if not os.path.exists(config_path):
        logger.error(f"配置文件不存在: {config_path}")
        sys.exit(1)
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    return config

def start_server(host, port, install_first=False):
    """启动服务器"""
    # 如果需要先安装依赖
    if install_first:
        logger.info("安装依赖...")
        install_script = os.path.join(ROOT_DIR, "scripts", "setup_all.py")
        if os.path.exists(install_script):
            subprocess.run([sys.executable, install_script], check=True)
        else:
            logger.warning(f"安装脚本不存在: {install_script}")
    
    # 加载配置
    config = load_config()
    
    # 检查转录服务可用性
    api_available = check_api_transcription(config)
    onnx_available = check_whisper_onnx_installation()
    
    if not api_available and not onnx_available:
        logger.warning("AnythingLLM API 和 Whisper ONNX 均不可用，语音转录功能可能受限")
        
        # 询问是否安装 Whisper ONNX
        if config["meeting"]["whisper"].get("use_onnx", False):
            print("\n未检测到 Whisper ONNX，是否要安装？(y/n)")
            choice = input().strip().lower()
            if choice == 'y':
                logger.info("安装 Whisper ONNX...")
                setup_script = os.path.join(ROOT_DIR, "scripts", "setup_whisper_onnx.py")
                if os.path.exists(setup_script):
                    subprocess.run([sys.executable, setup_script], check=True)
                    # 重新检查
                    onnx_available = check_whisper_onnx_installation()
                    if onnx_available:
                        logger.info("Whisper ONNX 安装成功")
                    else:
                        logger.warning("Whisper ONNX 安装失败")
                else:
                    logger.warning(f"Whisper ONNX 安装脚本不存在: {setup_script}")
    
    # 导入 MCP 服务器模块
    from mcp.server import MCPServer
    
    # 创建 MCP 服务器实例
    server = MCPServer(config)
    
    # 注册服务
    from mcp.email_service import EmailService
    from mcp.calendar_service import CalendarService
    from mcp.transcription import TranscriptionService
    from mcp.meeting import MeetingService
    from mcp.llm_service import LLMService
    from mcp.project import ProjectService
    
    # 数据库路径
    db_path = os.path.join(ROOT_DIR, "data", "mcp.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # 注册服务
    server.register_service("email", EmailService(config, db_path))
    server.register_service("calendar", CalendarService(config, db_path))
    server.register_service("transcription", TranscriptionService(config, db_path))
    server.register_service("meeting", MeetingService(config, db_path))
    server.register_service("llm", LLMService(config, db_path))
    server.register_service("project", ProjectService(config, db_path))
    
    # 启动服务器
    server_thread = threading.Thread(
        target=server.run,
        kwargs={"host": host, "port": port, "debug": False},
        daemon=True
    )
    server_thread.start()
    
    logger.info(f"MCP 服务器已启动: http://{host}:{port}")
    
    return server_thread

def start_ui(host="localhost", port=8080):
    """启动前端UI"""
    ui_dir = os.path.join(ROOT_DIR, "ui")
    
    if not os.path.exists(ui_dir):
        logger.error(f"UI目录不存在: {ui_dir}")
        return None
    
    # 检查是否有 package.json
    package_json_path = os.path.join(ui_dir, "package.json")
    if not os.path.exists(package_json_path):
        logger.error(f"package.json 不存在: {package_json_path}")
        return None
    
    # 启动 UI
    logger.info("启动前端 UI...")
    
    # 设置环境变量
    env = os.environ.copy()
    env["BROWSER"] = "none"  # 不自动打开浏览器
    
    # 使用 npm start 启动
    ui_process = subprocess.Popen(
        ["npm", "start"],
        cwd=ui_dir,
        env=env,
        shell=True
    )
    
    logger.info(f"前端 UI 已启动，进程 ID: {ui_process.pid}")
    
    return ui_process

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="一键启动集成助手")
    parser.add_argument("--host", type=str, default="localhost", help="服务器主机地址")
    parser.add_argument("--port", type=int, default=5000, help="服务器端口")
    parser.add_argument("--ui-port", type=int, default=3000, help="UI端口")
    parser.add_argument("--install", action="store_true", help="启动前先安装依赖")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    
    args = parser.parse_args()
    
    print("\n" + "=" * 50)
    print("集成助手启动程序")
    print("=" * 50 + "\n")
    
    # 启动服务器
    server_thread = start_server(args.host, args.port, args.install)
    
    # 等待服务器启动
    time.sleep(2)
    
    # 启动前端UI
    ui_process = start_ui(args.host, args.ui_port)
    
    # 等待UI启动
    time.sleep(5)
    
    # 打开浏览器
    if not args.no_browser:
        url = f"http://{args.host}:{args.ui_port}"
        logger.info(f"打开浏览器: {url}")
        webbrowser.open(url)
    
    print("\n" + "=" * 50)
    print(f"集成助手已启动!")
    print(f"- 后端API: http://{args.host}:{args.port}")
    print(f"- 前端UI: http://{args.host}:{args.ui_port}")
    print("=" * 50)
    print("\n按 Ctrl+C 停止服务\n")
    
    try:
        # 保持主线程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("接收到停止信号，正在关闭...")
        
        # 关闭UI进程
        if ui_process:
            ui_process.terminate()
            logger.info("UI进程已关闭")
        
        logger.info("服务已停止")

if __name__ == "__main__":
    main()
