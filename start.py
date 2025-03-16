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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("start")

# Project root directory
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))

def check_whisper_installation():
    """检查 Whisper 服务是否可用"""
    try:
        # 加载配置
        config_path = os.path.join(ROOT_DIR, "config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        # 检查 AnythingLLM API 配置
        anything_llm_enabled = config["llm"]["anything_llm"]["enabled"]
        anything_llm_api_url = config["llm"]["anything_llm"]["api_url"]
        anything_llm_api_key = config["llm"]["anything_llm"]["api_key"]
        
        if not anything_llm_enabled:
            print("Note: AnythingLLM API 未启用，语音转录将使用模拟实现")
            print("For full speech transcription functionality, enable AnythingLLM API in config.yaml")
            return False
        
        # 检查 AnythingLLM API 是否可用
        try:
            headers = {}
            if anything_llm_api_key:
                headers["x-api-key"] = anything_llm_api_key
                
            response = requests.get(
                f"{anything_llm_api_url}/api/health",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                return True
            else:
                print(f"Note: AnythingLLM API 不可用，状态码: {response.status_code}")
                print("Note: Speech transcription will use simulated implementation")
                print(f"For full speech transcription functionality, ensure AnythingLLM API is running at {anything_llm_api_url}")
                return False
        except Exception as e:
            print(f"Note: 检查 AnythingLLM API 时出错: {e}")
            print("Note: Speech transcription will use simulated implementation")
            print(f"For full speech transcription functionality, ensure AnythingLLM API is running at {anything_llm_api_url}")
            return False
    except Exception as e:
        print(f"Warning: Error checking Whisper service: {e}")
        print("Note: Speech transcription will use simulated implementation")
        print("For full speech transcription functionality, configure AnythingLLM API in config.yaml")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Integrated Assistant Startup Script")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Server host address")
    parser.add_argument("--port", type=int, default=7860, help="Server port")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    parser.add_argument("--setup", action="store_true", help="Run setup script before starting")
    
    args = parser.parse_args()
    
    # Run setup script if needed
    if args.setup:
        logger.info("Running setup script...")
        setup_script = os.path.join(ROOT_DIR, "scripts", "setup_all.py")
        try:
            subprocess.run([sys.executable, setup_script], check=True, shell=True)
        except subprocess.CalledProcessError:
            logger.warning("Setup script failed, attempting to continue with startup")
    
    # Check Whisper installation
    if not check_whisper_installation():
        logger.warning("AnythingLLM API not available, speech transcription may be limited")
    
    # Start server
    logger.info(f"Starting integrated assistant service at: {args.host}:{args.port}")
    
    # Build startup command
    env = os.environ.copy()
    env["PYTHONPATH"] = ROOT_DIR
    
    # 直接导入并启动服务器，而不是使用子进程
    try:
        # 加载配置
        config_path = os.path.join(ROOT_DIR, "config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        # 确保 MCP 配置存在
        if "mcp" not in config:
            config["mcp"] = {}
        
        # 设置服务器配置
        config["mcp"]["server_host"] = args.host
        config["mcp"]["server_port"] = args.port
        config["mcp"]["max_workers"] = 10
        
        # 导入服务器模块
        from mcp.server import MCPServer, start_mcp_server
        
        # 启动服务器（后台线程）
        server_thread = start_mcp_server(config)
        
        # 检查服务器是否启动成功
        time.sleep(2)
        if not server_thread.is_alive():
            logger.error("Server failed to start")
            return 1
        
        logger.info(f"MCP server started successfully at {args.host}:{args.port}")
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        return 1
    
    # Start frontend UI
    ui_url = f"http://localhost:{args.port}"
    ui_process = subprocess.Popen(
        f"{sys.executable} -m frontend.app --host {args.host} --port {str(args.port)}",
        cwd=ROOT_DIR,
        env=env,
        shell=True
    )
    
    # Wait for UI to start
    time.sleep(2)
    
    # Open browser automatically
    if not args.no_browser:
        logger.info(f"Opening UI in browser: {ui_url}")
        webbrowser.open(ui_url)
    
    print("\n" + "=" * 50)
    print(f"Integrated Assistant started successfully!")
    print(f"Access URL: {ui_url}")
    print("Press Ctrl+C to stop the service")
    print("=" * 50 + "\n")
    
    try:
        # Wait for UI process to end
        ui_process.wait()
    except KeyboardInterrupt:
        logger.info("Received stop signal, shutting down services...")
    finally:
        # Ensure both processes are terminated
        if ui_process.poll() is None:
            ui_process.terminate()
    
    logger.info("Integrated Assistant service stopped")
    return 0

if __name__ == "__main__":
    sys.exit(main())
