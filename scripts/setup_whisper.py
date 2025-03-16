#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Whisper 安装和设置脚本
用于安装 openai-whisper 包并下载所需模型
"""

import os
import sys
import argparse
import subprocess
import logging
import yaml
import time
import torch
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("setup_whisper")

# 定义模型大小和对应的磁盘空间需求（MB）
MODEL_SIZES = {
    "tiny": 75,
    "base": 142,
    "small": 466,
    "medium": 1446,
    "large": 2900,
}

def check_gpu():
    """检查是否有可用的GPU"""
    try:
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)  # GB
            logger.info(f"检测到GPU: {gpu_name}, 内存: {gpu_memory:.2f} GB")
            return True, gpu_name, gpu_memory
        else:
            logger.warning("未检测到GPU，将使用CPU进行处理，这可能会很慢")
            return False, None, None
    except Exception as e:
        logger.warning(f"检查GPU时出错: {str(e)}")
        return False, None, None

def check_disk_space(model_size):
    """检查是否有足够的磁盘空间"""
    try:
        # 获取当前目录所在磁盘的可用空间
        if sys.platform == 'win32':
            import ctypes
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(os.getcwd()), None, None, ctypes.pointer(free_bytes))
            free_space_mb = free_bytes.value / (1024 * 1024)
        else:
            import shutil
            free_space_mb = shutil.disk_usage(os.getcwd()).free / (1024 * 1024)
        
        required_space = MODEL_SIZES.get(model_size, 3000)  # 默认使用large模型的空间需求
        
        if free_space_mb < required_space * 1.5:  # 预留50%的额外空间
            logger.warning(f"磁盘空间不足! 需要至少 {required_space * 1.5:.2f} MB, 当前可用: {free_space_mb:.2f} MB")
            return False
        else:
            logger.info(f"磁盘空间充足: 可用 {free_space_mb:.2f} MB, 需要 {required_space * 1.5:.2f} MB")
            return True
    except Exception as e:
        logger.warning(f"检查磁盘空间时出错: {str(e)}")
        return True  # 出错时默认继续

def install_whisper():
    """安装 openai-whisper 包及其依赖"""
    try:
        logger.info("开始安装 openai-whisper 包...")
        
        # 安装 FFmpeg (Windows)
        if sys.platform == 'win32':
            try:
                # 检查 FFmpeg 是否已安装
                subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                logger.info("FFmpeg 已安装")
            except (subprocess.SubprocessError, FileNotFoundError):
                logger.info("FFmpeg 未安装，正在安装...")
                # 使用 pip 安装 ffmpeg-python
                subprocess.run([sys.executable, "-m", "pip", "install", "ffmpeg-python"], check=True)
                logger.info("请手动下载并安装 FFmpeg: https://ffmpeg.org/download.html")
                input("安装完成后按回车键继续...")
        
        # 安装 PyTorch (如果尚未安装)
        try:
            import torch
            logger.info(f"PyTorch 已安装，版本: {torch.__version__}")
        except ImportError:
            logger.info("PyTorch 未安装，正在安装...")
            has_gpu, _, _ = check_gpu()
            if has_gpu:
                # 使用 CUDA 安装 PyTorch
                subprocess.run([sys.executable, "-m", "pip", "install", "torch", "torchvision", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cu118"], check=True)
            else:
                # 使用 CPU 安装 PyTorch
                subprocess.run([sys.executable, "-m", "pip", "install", "torch", "torchvision", "torchaudio"], check=True)
        
        # 安装 openai-whisper
        subprocess.run([sys.executable, "-m", "pip", "install", "openai-whisper"], check=True)
        
        # 安装其他依赖
        subprocess.run([sys.executable, "-m", "pip", "install", "setuptools-rust"], check=True)
        
        logger.info("openai-whisper 安装完成")
        return True
    except subprocess.SubprocessError as e:
        logger.error(f"安装 openai-whisper 失败: {str(e)}")
        return False

def download_model(model_size):
    """下载指定大小的 Whisper 模型"""
    try:
        if model_size not in MODEL_SIZES:
            logger.warning(f"未知的模型大小: {model_size}，将使用 'base' 模型")
            model_size = "base"
        
        logger.info(f"开始下载 Whisper {model_size} 模型...")
        
        # 使用 Python 代码下载模型
        import whisper
        start_time = time.time()
        
        # 加载模型会自动下载
        whisper.load_model(model_size)
        
        end_time = time.time()
        logger.info(f"Whisper {model_size} 模型下载完成，耗时: {end_time - start_time:.2f} 秒")
        return True
    except Exception as e:
        logger.error(f"下载 Whisper 模型失败: {str(e)}")
        return False

def update_config(config_path, model_size):
    """更新配置文件中的 Whisper 模型设置"""
    try:
        # 读取配置文件
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 更新 Whisper 模型设置
        if 'meeting' in config and 'whisper' in config['meeting']:
            config['meeting']['whisper']['model'] = model_size
            logger.info(f"更新配置文件中的 Whisper 模型为: {model_size}")
        
        # 写回配置文件
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"配置文件 {config_path} 已更新")
        return True
    except Exception as e:
        logger.error(f"更新配置文件失败: {str(e)}")
        return False

def test_whisper():
    """测试 Whisper 是否正常工作"""
    try:
        logger.info("测试 Whisper 模型...")
        
        import whisper
        model = whisper.load_model("base")
        
        # 创建一个简单的测试音频文件
        test_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_whisper.wav")
        
        if not os.path.exists(test_file):
            logger.info("未找到测试音频文件，跳过测试")
            return True
        
        # 转录测试音频
        result = model.transcribe(test_file)
        
        logger.info(f"测试转录结果: {result['text']}")
        logger.info("Whisper 测试成功")
        return True
    except Exception as e:
        logger.error(f"Whisper 测试失败: {str(e)}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="安装 Whisper 并下载模型")
    parser.add_argument("--model", type=str, default="base", choices=["tiny", "base", "small", "medium", "large"],
                        help="要下载的模型大小 (默认: base)")
    parser.add_argument("--config", type=str, default="../config.yaml",
                        help="配置文件路径 (默认: ../config.yaml)")
    parser.add_argument("--skip-install", action="store_true",
                        help="跳过安装 Whisper 包，只下载模型")
    parser.add_argument("--skip-download", action="store_true",
                        help="跳过下载模型，只安装 Whisper 包")
    parser.add_argument("--test", action="store_true",
                        help="测试 Whisper 是否正常工作")
    
    args = parser.parse_args()
    
    # 获取配置文件的绝对路径
    if not os.path.isabs(args.config):
        args.config = os.path.abspath(os.path.join(os.path.dirname(__file__), args.config))
    
    logger.info(f"使用配置文件: {args.config}")
    logger.info(f"选择的模型大小: {args.model}")
    
    # 检查系统环境
    has_gpu, gpu_name, gpu_memory = check_gpu()
    
    # 根据 GPU 情况推荐模型大小
    if has_gpu:
        if gpu_memory and gpu_memory < 4:
            if args.model in ["medium", "large"]:
                logger.warning(f"GPU 内存不足 ({gpu_memory:.2f} GB)，不推荐使用 {args.model} 模型，建议使用 small 或更小的模型")
    
    # 检查磁盘空间
    if not check_disk_space(args.model):
        if input("磁盘空间可能不足，是否继续? (y/n): ").lower() != 'y':
            logger.info("用户取消安装")
            return
    
    # 安装 Whisper
    if not args.skip_install:
        if not install_whisper():
            logger.error("Whisper 安装失败，退出")
            return
    
    # 下载模型
    if not args.skip_download:
        if not download_model(args.model):
            logger.error("Whisper 模型下载失败，退出")
            return
        
        # 更新配置文件
        if os.path.exists(args.config):
            update_config(args.config, args.model)
    
    # 测试 Whisper
    if args.test:
        test_whisper()
    
    logger.info("Whisper 设置完成")

if __name__ == "__main__":
    main()
