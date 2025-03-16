#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Langraph 服务器启动脚本
启动基于 Langraph 架构的 MCP 服务器
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
import traceback

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "langraph_server.log"), mode="a")
    ]
)
logger = logging.getLogger("langraph_server")

# 获取项目根目录
ROOT_DIR = Path(__file__).parent.parent.absolute()

# 创建日志目录
os.makedirs(os.path.join(ROOT_DIR, "logs"), exist_ok=True)

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
    except FileNotFoundError:
        logger.error(f"配置文件不存在: {config_path}")
        logger.info(f"将使用默认配置")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"YAML 格式错误: {e}")
        logger.info(f"将使用默认配置")
        return {}
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        logger.error(traceback.format_exc())
        return {}

def check_anythingllm_api(config):
    """检查 AnythingLLM API 是否可用"""
    api_key = config.get("llm", {}).get("anything_llm", {}).get("api_key")
    api_url = config.get("llm", {}).get("anything_llm", {}).get("api_url", "http://localhost:3001")
    
    if not api_key:
        logger.warning("未配置 AnythingLLM API 密钥")
        return False
    
    try:
        # 尝试连接 AnythingLLM API
        response = requests.get(
            f"{api_url}/api/health",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=5
        )
        
        if response.status_code == 200:
            logger.info("AnythingLLM API 连接成功")
            return True
        else:
            logger.warning(f"AnythingLLM API 连接失败: 状态码 {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        logger.warning(f"无法连接到 AnythingLLM API: {api_url}")
        return False
    except requests.exceptions.Timeout:
        logger.warning(f"连接 AnythingLLM API 超时: {api_url}")
        return False
    except Exception as e:
        logger.warning(f"检查 AnythingLLM API 时出错: {e}")
        logger.debug(traceback.format_exc())
        return False

def run_setup_if_needed(args):
    """如果需要，运行安装脚本"""
    if args.setup:
        setup_script = os.path.join(ROOT_DIR, "scripts", "setup_langraph.py")
        try:
            logger.info("运行 Langraph 安装脚本...")
            subprocess.run([sys.executable, setup_script], check=True)
            logger.info("Langraph 安装完成")
        except subprocess.CalledProcessError as e:
            logger.error(f"Langraph 安装失败: {e}")
            logger.error("继续尝试启动服务器...")
        except Exception as e:
            logger.error(f"运行安装脚本时出错: {e}")
            logger.error(traceback.format_exc())

def start_mcp_server(host, port, config_path, use_langraph=True):
    """启动 MCP 服务器"""
    # 确保配置文件存在
    if not os.path.exists(config_path):
        logger.error(f"配置文件不存在: {config_path}")
        return None
    
    # 构建命令
    if use_langraph:
        server_script = os.path.join(ROOT_DIR, "mcp", "langraph", "main.py")
    else:
        server_script = os.path.join(ROOT_DIR, "mcp", "server.py")
    
    cmd = [
        sys.executable,
        server_script,
        "--host", host,
        "--port", str(port),
        "--config", config_path
    ]
    
    logger.info(f"启动 MCP 服务器: {'使用 Langraph' if use_langraph else '标准模式'}")
    logger.info(f"服务器地址: http://{host}:{port}")
    
    try:
        # 启动服务器进程
        server_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        # 创建线程读取输出
        def read_output(stream, log_func):
            for line in iter(stream.readline, ""):
                log_func(line.strip())
        
        threading.Thread(
            target=read_output,
            args=(server_process.stdout, logger.info),
            daemon=True
        ).start()
        
        threading.Thread(
            target=read_output,
            args=(server_process.stderr, logger.error),
            daemon=True
        ).start()
        
        return server_process
    except Exception as e:
        logger.error(f"启动 MCP 服务器失败: {e}")
        logger.error(traceback.format_exc())
        return None

def wait_for_server(host, port, timeout=30, retry_interval=0.5):
    """等待服务器启动"""
    logger.info(f"等待服务器启动 (最多 {timeout} 秒)...")
    start_time = time.time()
    url = f"http://{host}:{port}/health"
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                logger.info(f"服务器已启动: {url}")
                return True
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(retry_interval)
    
    logger.warning(f"等待服务器启动超时: {url}")
    return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Langraph 服务器启动脚本")
    parser.add_argument("--host", type=str, default=DEFAULT_HOST, help="服务器主机地址")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="服务器端口")
    parser.add_argument("--config", type=str, default=DEFAULT_CONFIG_PATH, help="配置文件路径")
    parser.add_argument("--setup", action="store_true", help="启动前运行安装脚本")
    parser.add_argument("--standard", action="store_true", help="使用标准模式（不使用 Langraph）")
    
    args = parser.parse_args()
    
    # 创建必要的目录
    os.makedirs(os.path.join(ROOT_DIR, "data"), exist_ok=True)
    os.makedirs(os.path.join(ROOT_DIR, "data", "audio"), exist_ok=True)
    os.makedirs(os.path.join(ROOT_DIR, "data", "transcriptions"), exist_ok=True)
    
    # 如果需要，运行安装脚本
    run_setup_if_needed(args)
    
    # 加载配置
    config = load_config(args.config)
    
    # 检查配置中是否指定使用 Langraph
    use_langraph = not args.standard
    if "server" in config and "use_langraph" in config["server"]:
        use_langraph = config["server"]["use_langraph"] and not args.standard
    
    # 启动 MCP 服务器
    server_process = start_mcp_server(args.host, args.port, args.config, use_langraph=use_langraph)
    if not server_process:
        logger.error("启动服务器失败，退出...")
        return 1
    
    # 等待服务器启动
    if not wait_for_server(args.host, args.port):
        logger.warning("服务器可能未正确启动，但将继续运行...")
    
    logger.info("=" * 50)
    logger.info(f"Langraph 服务器正在运行: http://{args.host}:{args.port}")
    logger.info("按 Ctrl+C 停止")
    logger.info("=" * 50)
    
    try:
        # 保持主进程运行
        server_process.wait()
    except KeyboardInterrupt:
        logger.info("正在停止服务器...")
        server_process.terminate()
        logger.info("服务器已停止")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        logger.critical(f"发生未处理的异常: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)
