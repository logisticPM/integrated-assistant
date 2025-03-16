#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
安装 langraph 及其依赖
"""

import os
import sys
import subprocess
import logging
import argparse
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("setup_langraph")

def install_dependencies(requirements_file):
    """安装依赖"""
    try:
        logger.info(f"安装依赖: {requirements_file}")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", requirements_file
        ])
        logger.info("依赖安装完成")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"安装依赖失败: {str(e)}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="安装 langraph 及其依赖")
    parser.add_argument("--skip-deps", action="store_true", help="跳过安装依赖")
    
    args = parser.parse_args()
    
    # 获取项目根目录
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    # 安装依赖
    if not args.skip_deps:
        requirements_file = os.path.join(root_dir, "requirements-langraph.txt")
        if not os.path.exists(requirements_file):
            logger.error(f"依赖文件不存在: {requirements_file}")
            return 1
        
        if not install_dependencies(requirements_file):
            return 1
    
    # 创建必要的目录
    langraph_dir = os.path.join(root_dir, "mcp", "langraph")
    os.makedirs(langraph_dir, exist_ok=True)
    
    # 创建 __init__.py 文件
    init_file = os.path.join(langraph_dir, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w") as f:
            f.write("# langraph 模块\n")
    
    logger.info(f"langraph 目录已创建: {langraph_dir}")
    logger.info("langraph 安装完成")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
