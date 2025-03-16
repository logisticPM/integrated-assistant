#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Whisper 测试脚本
用于测试 Whisper 转录功能是否正常工作
"""

import os
import sys
import argparse
import logging
import time
import yaml
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_whisper")

def load_config(config_path):
    """加载配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"加载配置文件失败: {str(e)}")
        return None

def check_whisper_installed():
    """检查 Whisper 是否已安装"""
    try:
        import whisper
        logger.info(f"Whisper 已安装，版本: {whisper.__version__ if hasattr(whisper, '__version__') else '未知'}")
        return True
    except ImportError:
        logger.error("Whisper 未安装，请先运行 setup_whisper.py 安装")
        return False

def create_test_audio(output_path, duration=5):
    """
    创建测试音频文件（需要 ffmpeg）
    
    Args:
        output_path: 输出文件路径
        duration: 音频时长（秒）
    
    Returns:
        是否成功创建
    """
    try:
        import subprocess
        
        # 检查输出目录是否存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 使用 ffmpeg 生成测试音频（静音）
        cmd = [
            "ffmpeg",
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=mono",
            "-t", str(duration),
            "-q:a", "9",
            "-acodec", "libmp3lame",
            output_path,
            "-y"  # 覆盖已存在的文件
        ]
        
        logger.info(f"创建测试音频文件: {output_path}")
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        return os.path.exists(output_path)
    except Exception as e:
        logger.error(f"创建测试音频失败: {str(e)}")
        return False

def test_transcription(audio_path, model_name="base", language="auto"):
    """
    测试音频转录
    
    Args:
        audio_path: 音频文件路径
        model_name: 模型名称
        language: 语言设置
    
    Returns:
        转录结果
    """
    try:
        import whisper
        
        # 检查音频文件是否存在
        if not os.path.exists(audio_path):
            logger.error(f"音频文件不存在: {audio_path}")
            return None
        
        # 加载模型
        logger.info(f"加载 Whisper 模型: {model_name}")
        start_time = time.time()
        model = whisper.load_model(model_name)
        load_time = time.time() - start_time
        logger.info(f"模型加载完成，耗时: {load_time:.2f}秒")
        
        # 设置语言参数
        lang = None if language == "auto" else language
        
        # 执行转录
        logger.info(f"开始转录音频: {audio_path}")
        start_time = time.time()
        
        result = model.transcribe(
            audio_path,
            language=lang,
            verbose=True
        )
        
        transcribe_time = time.time() - start_time
        logger.info(f"转录完成，耗时: {transcribe_time:.2f}秒")
        
        # 输出结果
        logger.info(f"转录结果: {result['text']}")
        
        return {
            "text": result["text"],
            "segments": result["segments"],
            "load_time": load_time,
            "transcribe_time": transcribe_time
        }
    
    except Exception as e:
        logger.error(f"转录测试失败: {str(e)}")
        return None

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="测试 Whisper 转录功能")
    parser.add_argument("--audio", type=str, help="音频文件路径（如不指定，将创建测试音频）")
    parser.add_argument("--model", type=str, default="base", choices=["tiny", "base", "small", "medium", "large"],
                        help="要使用的模型大小 (默认: base)")
    parser.add_argument("--language", type=str, default="auto", help="语言设置 (默认: auto)")
    parser.add_argument("--config", type=str, default="../config.yaml", help="配置文件路径 (默认: ../config.yaml)")
    
    args = parser.parse_args()
    
    # 获取配置文件的绝对路径
    if not os.path.isabs(args.config):
        args.config = os.path.abspath(os.path.join(os.path.dirname(__file__), args.config))
    
    # 加载配置
    config = load_config(args.config)
    if not config:
        return
    
    # 如果未指定模型，使用配置文件中的设置
    if not args.model and config and "meeting" in config and "whisper" in config["meeting"]:
        args.model = config["meeting"]["whisper"]["model"]
    
    # 如果未指定语言，使用配置文件中的设置
    if not args.language and config and "meeting" in config and "whisper" in config["meeting"]:
        args.language = config["meeting"]["whisper"]["language"]
    
    logger.info(f"使用模型: {args.model}, 语言: {args.language}")
    
    # 检查 Whisper 是否已安装
    if not check_whisper_installed():
        logger.info("请先运行 setup_whisper.py 安装 Whisper")
        return
    
    # 准备音频文件
    audio_path = args.audio
    if not audio_path:
        # 创建测试音频
        audio_dir = config["meeting"]["audio_dir"] if config and "meeting" in config else "./data/audio"
        if not os.path.isabs(audio_dir):
            audio_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", audio_dir))
        
        os.makedirs(audio_dir, exist_ok=True)
        audio_path = os.path.join(audio_dir, "whisper_test.mp3")
        
        if not create_test_audio(audio_path):
            logger.error("无法创建测试音频，请手动指定音频文件")
            return
    
    # 测试转录
    result = test_transcription(audio_path, args.model, args.language)
    
    if result:
        logger.info("Whisper 测试成功完成！")
        logger.info(f"模型加载时间: {result['load_time']:.2f}秒")
        logger.info(f"转录处理时间: {result['transcribe_time']:.2f}秒")
        logger.info(f"转录文本: {result['text']}")
    else:
        logger.error("Whisper 测试失败")

if __name__ == "__main__":
    main()
