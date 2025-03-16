#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
集成助手启动脚本
用于一键启动集成助手服务
"""

import os
import sys
import subprocess
import logging
import argparse
import webbrowser
import time
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("start")

# 项目根目录
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))

def check_whisper_installation():
    """检查Whisper是否已安装"""
    try:
        import whisper
        return True
    except ImportError:
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="集成助手启动脚本")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="服务器主机地址")
    parser.add_argument("--port", type=int, default=7860, help="服务器端口")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--setup", action="store_true", help="在启动前运行安装脚本")
    
    args = parser.parse_args()
    
    # 如果需要，先运行安装脚本
    if args.setup:
        logger.info("运行安装脚本...")
        setup_script = os.path.join(ROOT_DIR, "scripts", "setup_all.py")
        try:
            subprocess.run([sys.executable, setup_script], check=True)
        except subprocess.CalledProcessError:
            logger.warning("安装脚本运行失败，尝试继续启动服务")
    
    # 检查Whisper安装
    if not check_whisper_installation():
        logger.warning("Whisper未安装，语音转录功能可能不可用")
        print("\n注意: Whisper未安装，语音转录功能将使用模拟实现")
        print("如需使用完整的语音转录功能，请运行: python scripts/setup_whisper.py\n")
    
    # 启动服务器
    logger.info(f"启动集成助手服务，地址: {args.host}:{args.port}")
    
    # 构建启动命令
    env = os.environ.copy()
    env["PYTHONPATH"] = ROOT_DIR
    
    server_process = subprocess.Popen(
        [sys.executable, "-m", "mcp.server"],
        cwd=ROOT_DIR,
        env=env
    )
    
    # 等待服务器启动
    time.sleep(2)
    
    # 检查服务器是否成功启动
    if server_process.poll() is not None:
        logger.error("服务器启动失败")
        return 1
    
    # 启动前端UI
    ui_url = f"http://localhost:{args.port}"
    ui_process = subprocess.Popen(
        [sys.executable, "-m", "frontend.app", "--host", args.host, "--port", str(args.port)],
        cwd=ROOT_DIR,
        env=env
    )
    
    # 等待UI启动
    time.sleep(2)
    
    # 自动打开浏览器
    if not args.no_browser:
        logger.info(f"在浏览器中打开UI: {ui_url}")
        webbrowser.open(ui_url)
    
    print("\n" + "=" * 50)
    print(f"集成助手已启动!")
    print(f"访问地址: {ui_url}")
    print("按Ctrl+C停止服务")
    print("=" * 50 + "\n")
    
    try:
        # 等待UI进程结束
        ui_process.wait()
    except KeyboardInterrupt:
        logger.info("接收到停止信号，正在关闭服务...")
    finally:
        # 确保两个进程都被终止
        if ui_process.poll() is None:
            ui_process.terminate()
        
        if server_process.poll() is None:
            server_process.terminate()
    
    logger.info("集成助手服务已停止")
    return 0

if __name__ == "__main__":
    sys.exit(main())
