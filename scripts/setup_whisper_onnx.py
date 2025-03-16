#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Whisper ONNX 安装脚本
安装基于 ONNX 的 Whisper 模型和依赖
"""

import os
import sys
import subprocess
import logging
import argparse
from pathlib import Path
import shutil

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("setup_whisper_onnx")

# 项目根目录
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Whisper ONNX 模型目录
WHISPER_ONNX_DIR = os.path.join(ROOT_DIR, "models", "whisper_onnx")

# 依赖列表
DEPENDENCIES = [
    "opencv-python",
    "qai_hub_models[whisper_base_en]",
    "audio2numpy",
    "samplerate",
    "onnxruntime",
    "numpy",
    "requests",
    "pyyaml"
]

def check_ffmpeg():
    """检查 FFmpeg 是否已安装"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            shell=True
        )
        if result.returncode == 0:
            logger.info("FFmpeg 已安装")
            return True
        else:
            logger.warning("FFmpeg 未安装或无法访问")
            return False
    except Exception as e:
        logger.warning(f"检查 FFmpeg 时出错: {str(e)}")
        return False

def install_dependencies():
    """安装依赖包"""
    logger.info("安装 Whisper ONNX 依赖...")
    
    for package in DEPENDENCIES:
        logger.info(f"安装 {package}...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                check=True,
                shell=True
            )
            logger.info(f"{package} 安装成功")
        except subprocess.CalledProcessError as e:
            logger.error(f"{package} 安装失败: {str(e)}")
            return False
    
    logger.info("所有依赖安装完成")
    return True

def export_onnx_model(model_size="base"):
    """导出 ONNX 模型"""
    logger.info(f"导出 Whisper {model_size} ONNX 模型...")
    
    # 创建模型目录
    os.makedirs(WHISPER_ONNX_DIR, exist_ok=True)
    
    # 导出模型
    try:
        if model_size == "base":
            # 使用 qai_hub_models 导出 base 模型
            subprocess.run(
                [sys.executable, "-m", "qai_hub_models.models.whisper_base_en.export", "--target-runtime", "onnx"],
                check=True,
                cwd=ROOT_DIR,
                shell=True
            )
            
            # 移动模型文件到指定目录
            build_dir = os.path.join(ROOT_DIR, "build")
            if os.path.exists(build_dir):
                for file in os.listdir(build_dir):
                    if file.endswith(".onnx"):
                        src = os.path.join(build_dir, file)
                        dst = os.path.join(WHISPER_ONNX_DIR, file)
                        shutil.copy(src, dst)
                        logger.info(f"已复制模型文件: {file}")
            
            logger.info(f"Whisper {model_size} ONNX 模型导出成功")
            return True
        else:
            logger.error(f"暂不支持 {model_size} 模型大小，目前仅支持 base")
            return False
    except Exception as e:
        logger.error(f"导出 ONNX 模型时出错: {str(e)}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Whisper ONNX 安装脚本")
    parser.add_argument("--model", type=str, default="base", choices=["base"], help="模型大小 (目前仅支持 base)")
    
    args = parser.parse_args()
    
    print("\n" + "=" * 50)
    print("Whisper ONNX 安装脚本")
    print("=" * 50 + "\n")
    
    # 检查 FFmpeg
    if not check_ffmpeg():
        print("\n警告: FFmpeg 未安装或无法访问")
        print("请安装 FFmpeg 并确保其在系统路径中")
        print("Windows: 下载 https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip")
        print("解压并将 bin 目录添加到系统路径")
        print("\n继续安装其他组件...\n")
    
    # 安装依赖
    if not install_dependencies():
        print("\n错误: 依赖安装失败")
        print("请检查错误信息并重试")
        return 1
    
    # 导出 ONNX 模型
    if not export_onnx_model(args.model):
        print("\n错误: ONNX 模型导出失败")
        print("请检查错误信息并重试")
        return 1
    
    print("\n" + "=" * 50)
    print("Whisper ONNX 安装完成!")
    print(f"模型文件位于: {WHISPER_ONNX_DIR}")
    print("=" * 50 + "\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
