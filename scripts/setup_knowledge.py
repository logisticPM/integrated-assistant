#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
知识库设置脚本
用于安装知识库所需的依赖和模型
"""

import os
import sys
import argparse
import logging
import subprocess
import shutil
import yaml
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("setup_knowledge")

def check_disk_space(required_space_gb=5):
    """检查可用磁盘空间"""
    try:
        if sys.platform == 'win32':
            import ctypes
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(os.getcwd()), None, None, ctypes.pointer(free_bytes)
            )
            free_gb = free_bytes.value / (1024 ** 3)
        else:
            # Linux/Mac
            import os
            stat = os.statvfs(os.getcwd())
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
        
        logger.info(f"可用磁盘空间: {free_gb:.2f} GB")
        if free_gb < required_space_gb:
            logger.warning(f"磁盘空间不足! 需要至少 {required_space_gb} GB，但只有 {free_gb:.2f} GB 可用")
            return False
        return True
    except Exception as e:
        logger.error(f"检查磁盘空间时出错: {str(e)}")
        return False

def install_dependencies():
    """安装知识库所需的依赖"""
    try:
        logger.info("安装知识库所需的依赖...")
        
        # 使用pip安装依赖
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "lancedb>=0.3.0",
            "sentence-transformers>=2.2.2",
            "pypdf>=3.15.1",
            "python-docx>=0.8.11",
            "langchain>=0.0.267",
            "langchain-text-splitters>=0.0.1"
        ])
        
        logger.info("依赖安装完成")
        return True
    except Exception as e:
        logger.error(f"安装依赖时出错: {str(e)}")
        return False

def download_embedding_model(model_name="all-MiniLM-L6-v2"):
    """下载嵌入模型"""
    try:
        logger.info(f"下载嵌入模型: {model_name}")
        
        # 使用sentence-transformers下载模型
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(model_name)
        
        # 测试模型
        test_embedding = model.encode("这是一个测试句子")
        logger.info(f"模型测试成功，嵌入维度: {len(test_embedding)}")
        
        return True
    except Exception as e:
        logger.error(f"下载嵌入模型时出错: {str(e)}")
        return False

def update_config(config_path, model_name):
    """更新配置文件"""
    try:
        # 读取配置文件
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 更新知识库配置
        if 'knowledge' not in config:
            config['knowledge'] = {}
        
        config['knowledge']['embedding_model'] = model_name
        
        # 写回配置文件
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"配置文件已更新: {config_path}")
        return True
    except Exception as e:
        logger.error(f"更新配置文件时出错: {str(e)}")
        return False

def create_data_directories(config_path):
    """创建数据目录"""
    try:
        # 读取配置文件
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 创建知识库数据目录
        docs_dir = config.get('knowledge', {}).get('docs_dir', './data/documents')
        vector_db_path = config.get('db', {}).get('vector_db_path', './data/vector_db')
        
        os.makedirs(docs_dir, exist_ok=True)
        os.makedirs(vector_db_path, exist_ok=True)
        
        logger.info(f"数据目录已创建: {docs_dir}, {vector_db_path}")
        return True
    except Exception as e:
        logger.error(f"创建数据目录时出错: {str(e)}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="设置知识库")
    parser.add_argument("--model", type=str, default="all-MiniLM-L6-v2", 
                        help="要使用的嵌入模型 (默认: all-MiniLM-L6-v2)")
    parser.add_argument("--config", type=str, default="../config.yaml", 
                        help="配置文件路径 (默认: ../config.yaml)")
    parser.add_argument("--skip-deps", action="store_true", 
                        help="跳过依赖安装")
    
    args = parser.parse_args()
    
    # 获取配置文件的绝对路径
    if not os.path.isabs(args.config):
        args.config = os.path.abspath(os.path.join(os.path.dirname(__file__), args.config))
    
    logger.info(f"使用配置文件: {args.config}")
    logger.info(f"使用嵌入模型: {args.model}")
    
    # 检查磁盘空间
    if not check_disk_space(5):
        logger.warning("磁盘空间不足，但将继续安装")
    
    # 安装依赖
    if not args.skip_deps:
        if not install_dependencies():
            logger.error("依赖安装失败")
            return
    
    # 下载嵌入模型
    if not download_embedding_model(args.model):
        logger.error("嵌入模型下载失败")
        return
    
    # 更新配置文件
    if not update_config(args.config, args.model):
        logger.error("配置文件更新失败")
        return
    
    # 创建数据目录
    if not create_data_directories(args.config):
        logger.error("数据目录创建失败")
        return
    
    logger.info("知识库设置完成！")

if __name__ == "__main__":
    main()
