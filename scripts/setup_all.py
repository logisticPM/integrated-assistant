#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
集成助手一键部署脚本
用于安装和配置所有必要的组件，包括Whisper、知识库和AnythingLLM集成
"""

import os
import sys
import argparse
import subprocess
import logging
import yaml
import time
import getpass
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("setup_all")

# 项目根目录
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def run_script(script_name, args=None):
    """
    运行指定的Python脚本
    
    Args:
        script_name: 脚本名称
        args: 命令行参数
    
    Returns:
        是否成功
    """
    script_path = os.path.join(ROOT_DIR, "scripts", script_name)
    cmd = [sys.executable, script_path]
    
    if args:
        cmd.extend(args)
    
    logger.info(f"运行脚本: {script_name} {' '.join(args) if args else ''}")
    
    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        logger.error(f"运行脚本 {script_name} 失败: {str(e)}")
        return False

def update_config_anything_llm(api_key=None, api_url=None):
    """
    更新配置文件中的AnythingLLM设置
    
    Args:
        api_key: AnythingLLM API密钥
        api_url: AnythingLLM API URL
    
    Returns:
        是否成功
    """
    config_path = os.path.join(ROOT_DIR, "config.yaml")
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        # 更新AnythingLLM配置
        if "llm" not in config:
            config["llm"] = {}
        
        if "anything_llm" not in config["llm"]:
            config["llm"]["anything_llm"] = {}
        
        config["llm"]["anything_llm"]["enabled"] = True
        
        if api_key:
            config["llm"]["anything_llm"]["api_key"] = api_key
        
        if api_url:
            config["llm"]["anything_llm"]["api_url"] = api_url
        
        # 写回配置文件
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        logger.info("已更新AnythingLLM配置")
        return True
    
    except Exception as e:
        logger.error(f"更新AnythingLLM配置失败: {str(e)}")
        return False

def create_directories():
    """
    创建必要的目录结构
    
    Returns:
        是否成功
    """
    try:
        directories = [
            os.path.join(ROOT_DIR, "data"),
            os.path.join(ROOT_DIR, "data", "audio"),
            os.path.join(ROOT_DIR, "data", "transcriptions"),
            os.path.join(ROOT_DIR, "data", "documents"),
            os.path.join(ROOT_DIR, "data", "vector_db"),
            os.path.join(ROOT_DIR, "models"),
            os.path.join(ROOT_DIR, "models", "llm"),
            os.path.join(ROOT_DIR, "models", "embedding"),
            os.path.join(ROOT_DIR, "credentials"),
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"创建目录: {directory}")
        
        return True
    
    except Exception as e:
        logger.error(f"创建目录失败: {str(e)}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="集成助手一键部署脚本")
    parser.add_argument("--whisper-model", type=str, choices=["tiny", "base", "small", "medium", "large"], 
                        default="base", help="Whisper模型大小 (默认: base)")
    parser.add_argument("--anything-llm-url", type=str, 
                        default="http://localhost:3001/api", help="AnythingLLM API URL")
    parser.add_argument("--skip-whisper", action="store_true", help="跳过Whisper安装")
    parser.add_argument("--skip-knowledge", action="store_true", help="跳过知识库设置")
    parser.add_argument("--skip-gmail", action="store_true", help="跳过Gmail设置")
    
    args = parser.parse_args()
    
    logger.info("开始集成助手一键部署")
    logger.info("=" * 50)
    
    # 创建必要的目录结构
    logger.info("步骤1: 创建必要的目录结构")
    if not create_directories():
        logger.error("创建目录失败，部署终止")
        return 1
    
    # 询问AnythingLLM API密钥
    print("\n" + "=" * 50)
    print("AnythingLLM集成设置")
    print("=" * 50)
    print("请输入AnythingLLM API密钥 (如果没有可以留空):")
    api_key = getpass.getpass("API密钥: ")
    
    # 更新AnythingLLM配置
    if not update_config_anything_llm(api_key=api_key, api_url=args.anything_llm_url):
        logger.warning("更新AnythingLLM配置失败，将使用默认配置")
    
    # 安装和设置Whisper
    if not args.skip_whisper:
        logger.info("\n步骤2: 安装和设置Whisper")
        whisper_args = ["--model", args.whisper_model]
        if not run_script("setup_whisper.py", whisper_args):
            logger.error("Whisper安装失败，部署继续但语音转录功能可能不可用")
    else:
        logger.info("跳过Whisper安装")
    
    # 设置知识库
    if not args.skip_knowledge:
        logger.info("\n步骤3: 设置知识库")
        if not run_script("setup_knowledge.py"):
            logger.error("知识库设置失败，部署继续但知识库功能可能不可用")
    else:
        logger.info("跳过知识库设置")
    
    # 设置Gmail集成
    if not args.skip_gmail:
        logger.info("\n步骤4: 设置Gmail集成")
        if not run_script("setup_gmail.py"):
            logger.error("Gmail设置失败，部署继续但邮件集成功能可能不可用")
    else:
        logger.info("跳过Gmail设置")
    
    # 设置定时任务
    logger.info("\n步骤5: 设置定时任务")
    if not run_script("setup_cron.py"):
        logger.warning("定时任务设置失败，部署继续但自动化功能可能不可用")
    
    logger.info("\n" + "=" * 50)
    logger.info("集成助手部署完成!")
    logger.info("您可以通过运行以下命令启动服务:")
    logger.info(f"cd {ROOT_DIR} && python -m mcp.server")
    logger.info("=" * 50)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
