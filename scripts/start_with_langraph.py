#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
集成助手启动脚本 - 使用 Langraph 架构
一键启动后端服务和前端 UI
"""

import os
import sys
import time
import subprocess
import argparse
import webbrowser
import logging
import yaml
import threading
import signal
import requests
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("start_with_langraph")

# 获取项目根目录
ROOT_DIR = Path(__file__).parent.parent.absolute()

# 默认配置
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_UI_PORT = 3000
DEFAULT_CONFIG_PATH = os.path.join(ROOT_DIR, "config.yaml")

def load_config(config_path):
    """加载配置文件"""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return {}

def check_anythingllm_api(config):
    """检查 AnythingLLM API 是否可用"""
    api_key = config.get("anythingllm", {}).get("api_key")
    if not api_key:
        logger.warning("未配置 AnythingLLM API 密钥")
        return False
    
    try:
        # 简单的 API 测试请求
        response = requests.get(
            "https://api.anythingllm.com/api/health",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=5
        )
        if response.status_code == 200:
            logger.info("AnythingLLM API 连接正常")
            return True
        else:
            logger.warning(f"AnythingLLM API 返回错误状态码: {response.status_code}")
            return False
    except Exception as e:
        logger.warning(f"AnythingLLM API 连接失败: {e}")
        return False

def run_setup_if_needed(args):
    """如果需要，运行安装脚本"""
    if args.run_setup:
        logger.info("运行安装脚本...")
        setup_script = os.path.join(ROOT_DIR, "scripts", "setup_all.py")
        subprocess.run([sys.executable, setup_script], check=True)
        
        # 安装 langraph
        logger.info("安装 langraph...")
        setup_langraph_script = os.path.join(ROOT_DIR, "scripts", "setup_langraph.py")
        subprocess.run([sys.executable, setup_langraph_script], check=True)

def start_mcp_server(host, port, config_path, use_langraph=True):
    """启动 MCP 服务器"""
    logger.info(f"启动 MCP 服务器 (使用 Langraph: {use_langraph})...")
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT_DIR)
    
    if use_langraph:
        # 使用 langraph 架构
        server_script = os.path.join(ROOT_DIR, "mcp", "langraph", "main.py")
        cmd = [
            sys.executable, 
            server_script, 
            "--host", host, 
            "--port", str(port),
            "--config", config_path
        ]
    else:
        # 使用原始 MCP 服务器
        server_script = os.path.join(ROOT_DIR, "mcp", "server.py")
        cmd = [
            sys.executable, 
            server_script, 
            "--host", host, 
            "--port", str(port)
        ]
    
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    
    # 启动日志线程
    def log_output():
        for line in process.stdout:
            logger.info(f"[MCP] {line.strip()}")
    
    log_thread = threading.Thread(target=log_output, daemon=True)
    log_thread.start()
    
    return process

def start_ui(ui_port, mcp_host, mcp_port):
    """启动前端 UI"""
    logger.info("启动前端 UI...")
    
    ui_dir = os.path.join(ROOT_DIR, "ui")
    env = os.environ.copy()
    env["PORT"] = str(ui_port)
    env["REACT_APP_MCP_HOST"] = mcp_host
    env["REACT_APP_MCP_PORT"] = str(mcp_port)
    
    # 检查是否需要安装依赖
    if not os.path.exists(os.path.join(ui_dir, "node_modules")):
        logger.info("安装 UI 依赖...")
        subprocess.run(
            ["npm", "install"],
            cwd=ui_dir,
            check=True
        )
    
    # 启动 UI
    process = subprocess.Popen(
        ["npm", "start"],
        cwd=ui_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    
    # 启动日志线程
    def log_output():
        for line in process.stdout:
            logger.info(f"[UI] {line.strip()}")
    
    log_thread = threading.Thread(target=log_output, daemon=True)
    log_thread.start()
    
    return process

def wait_for_server(host, port, timeout=30):
    """等待服务器启动"""
    logger.info(f"等待 MCP 服务器启动 (http://{host}:{port})...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"http://{host}:{port}/health", timeout=1)
            if response.status_code == 200:
                logger.info("MCP 服务器已启动")
                return True
        except:
            pass
        
        time.sleep(1)
    
    logger.warning(f"等待 MCP 服务器启动超时 ({timeout}秒)")
    return False

def wait_for_ui(host, port, timeout=60):
    """等待 UI 启动"""
    logger.info(f"等待 UI 启动 (http://{host}:{port})...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"http://{host}:{port}", timeout=1)
            if response.status_code == 200:
                logger.info("UI 已启动")
                return True
        except:
            pass
        
        time.sleep(1)
    
    logger.warning(f"等待 UI 启动超时 ({timeout}秒)")
    return False

def open_browser(host, port):
    """打开浏览器"""
    url = f"http://{host}:{port}"
    logger.info(f"在浏览器中打开 {url}")
    webbrowser.open(url)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="集成助手启动脚本 - 使用 Langraph 架构")
    parser.add_argument("--host", type=str, default=DEFAULT_HOST, help="MCP 服务器主机地址")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="MCP 服务器端口")
    parser.add_argument("--ui-port", type=int, default=DEFAULT_UI_PORT, help="UI 端口")
    parser.add_argument("--config", type=str, default=DEFAULT_CONFIG_PATH, help="配置文件路径")
    parser.add_argument("--run-setup", action="store_true", help="在启动前运行安装脚本")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--use-original", action="store_true", help="使用原始 MCP 服务器而不是 Langraph 架构")
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config(args.config)
    
    # 检查 AnythingLLM API
    check_anythingllm_api(config)
    
    # 如果需要，运行安装脚本
    run_setup_if_needed(args)
    
    # 启动 MCP 服务器
    mcp_process = start_mcp_server(args.host, args.port, args.config, not args.use_original)
    
    # 等待 MCP 服务器启动
    if not wait_for_server(args.host, args.port):
        logger.error("MCP 服务器启动失败")
        mcp_process.terminate()
        sys.exit(1)
    
    # 启动 UI
    ui_process = start_ui(args.ui_port, args.host, args.port)
    
    # 等待 UI 启动
    if not wait_for_ui(args.host, args.ui_port):
        logger.error("UI 启动失败")
        mcp_process.terminate()
        ui_process.terminate()
        sys.exit(1)
    
    # 打开浏览器
    if not args.no_browser:
        open_browser(args.host, args.ui_port)
    
    logger.info(f"集成助手已启动:")
    logger.info(f"- MCP 服务器: http://{args.host}:{args.port}")
    logger.info(f"- 前端 UI: http://{args.host}:{args.ui_port}")
    logger.info("按 Ctrl+C 停止服务")
    
    # 处理信号
    def signal_handler(sig, frame):
        logger.info("正在停止服务...")
        mcp_process.terminate()
        ui_process.terminate()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 等待进程结束
    try:
        mcp_process.wait()
        ui_process.wait()
    except KeyboardInterrupt:
        logger.info("正在停止服务...")
        mcp_process.terminate()
        ui_process.terminate()

if __name__ == "__main__":
    main()
