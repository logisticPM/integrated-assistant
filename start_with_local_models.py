#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
使用本地模型启动集成助手
一键启动使用本地 Whisper 和 LLM 模型的集成助手
"""

import os
import sys
import time
import logging
import argparse
import yaml
import json
import subprocess
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("start_with_local_models")

def check_models():
    """
    检查本地模型是否已下载
    
    Returns:
        (bool, bool): (Whisper模型是否可用, LLM模型是否可用)
    """
    # 获取项目根目录
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 检查 Whisper 模型
    whisper_model_dir = os.path.join(root_dir, "models", "whisper")
    whisper_available = False
    
    if os.path.exists(whisper_model_dir):
        # 检查是否有模型文件
        model_files = [f for f in os.listdir(whisper_model_dir) 
                      if f.endswith(".bin") or f.endswith(".onnx")]
        
        if model_files:
            whisper_available = True
            logger.info(f"找到 Whisper 模型文件: {model_files}")
    
    # 检查 LLM 模型
    llm_model_dir = os.path.join(root_dir, "models", "llm")
    llm_available = False
    
    if os.path.exists(llm_model_dir):
        # 检查是否有模型文件
        model_files = [f for f in os.listdir(llm_model_dir) 
                      if f.endswith(".onnx")]
        
        if model_files:
            llm_available = True
            logger.info(f"找到 LLM 模型文件: {model_files}")
    
    return whisper_available, llm_available

def update_config(use_local_whisper=True, use_local_llm=True, use_qnn=False):
    """
    更新配置文件
    
    Args:
        use_local_whisper: 是否使用本地 Whisper 模型
        use_local_llm: 是否使用本地 LLM 模型
        use_qnn: 是否使用 QNN 执行提供程序
    """
    # 获取项目根目录
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 配置文件路径
    config_path = os.path.join(root_dir, "config.yaml")
    
    try:
        # 读取配置文件
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 更新 Whisper 配置
        if use_local_whisper:
            config["meeting"]["whisper"]["use_local"] = True
            config["meeting"]["whisper"]["use_qnn"] = use_qnn
            config["transcription"]["provider"] = "whisper_onnx"
        
        # 更新 LLM 配置
        if use_local_llm:
            config["llm"]["model"] = "local"
            config["llm"]["local"]["enabled"] = True
            config["llm"]["local"]["use_qnn"] = use_qnn
        
        # 确保使用 Langraph 架构
        config["server"]["use_langraph"] = True
        
        # 保存配置文件
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"已更新配置文件: {config_path}")
        return True
    
    except Exception as e:
        logger.error(f"更新配置文件失败: {str(e)}")
        return False

def download_models(whisper_model="base", llm_model="phi2-onnx", force=False):
    """
    下载模型
    
    Args:
        whisper_model: Whisper 模型大小
        llm_model: LLM 模型名称
        force: 是否强制重新下载
    
    Returns:
        是否成功
    """
    try:
        # 获取项目根目录
        root_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 设置模型脚本路径
        setup_script = os.path.join(root_dir, "scripts", "setup_local_models.py")
        
        if not os.path.exists(setup_script):
            logger.error(f"模型设置脚本不存在: {setup_script}")
            return False
        
        # 构建命令
        cmd = [sys.executable, setup_script]
        
        # 添加 Whisper 参数
        if whisper_model:
            cmd.extend(["--whisper", whisper_model, "--use-onnx"])
        
        # 添加 LLM 参数
        if llm_model:
            cmd.extend(["--llm", llm_model])
        
        # 添加强制重新下载参数
        if force:
            cmd.append("--force")
        
        # 执行命令
        logger.info(f"执行命令: {' '.join(cmd)}")
        process = subprocess.run(cmd, check=True)
        
        if process.returncode == 0:
            logger.info("模型下载成功")
            return True
        else:
            logger.error(f"模型下载失败，返回码: {process.returncode}")
            return False
    
    except Exception as e:
        logger.error(f"下载模型失败: {str(e)}")
        return False

def start_server(use_langraph=True):
    """
    启动服务器
    
    Args:
        use_langraph: 是否使用 Langraph 架构
    """
    try:
        # 获取项目根目录
        root_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 设置启动脚本路径
        if use_langraph:
            start_script = os.path.join(root_dir, "start_with_langraph.py")
        else:
            start_script = os.path.join(root_dir, "start.py")
        
        if not os.path.exists(start_script):
            logger.error(f"启动脚本不存在: {start_script}")
            return False
        
        # 构建命令
        cmd = [sys.executable, start_script]
        
        # 执行命令
        logger.info(f"执行命令: {' '.join(cmd)}")
        process = subprocess.Popen(cmd)
        
        # 等待服务器启动
        logger.info("等待服务器启动...")
        time.sleep(5)
        
        logger.info("服务器已启动")
        return True
    
    except Exception as e:
        logger.error(f"启动服务器失败: {str(e)}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="使用本地模型启动集成助手")
    parser.add_argument("--whisper", choices=["tiny", "base"], default="base", help="Whisper 模型大小")
    parser.add_argument("--llm", choices=["llama2-7b-onnx", "phi2-onnx"], default="phi2-onnx", help="LLM 模型名称")
    parser.add_argument("--force-download", action="store_true", help="强制重新下载模型")
    parser.add_argument("--use-qnn", action="store_true", help="使用 QNN 执行提供程序")
    parser.add_argument("--skip-download", action="store_true", help="跳过模型下载")
    parser.add_argument("--api-only", action="store_true", help="仅使用 API 服务，不使用本地模型")
    
    args = parser.parse_args()
    
    # 检查本地模型是否已下载
    whisper_available, llm_available = check_models()
    
    # 如果需要下载模型
    if not args.skip_download and not args.api_only:
        # 如果模型不可用或强制重新下载
        if not whisper_available or not llm_available or args.force_download:
            logger.info("开始下载模型...")
            download_models(
                whisper_model=args.whisper,
                llm_model=args.llm,
                force=args.force_download
            )
            
            # 重新检查模型
            whisper_available, llm_available = check_models()
    
    # 更新配置
    if not args.api_only:
        update_config(
            use_local_whisper=whisper_available,
            use_local_llm=llm_available,
            use_qnn=args.use_qnn
        )
    else:
        # 使用 API 服务
        update_config(
            use_local_whisper=False,
            use_local_llm=False,
            use_qnn=False
        )
    
    # 启动服务器
    start_server(use_langraph=True)

if __name__ == "__main__":
    main()
