#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试 Whisper ONNX 功能
用于验证 Whisper ONNX 转录是否正常工作
"""

import os
import sys
import argparse
import logging
import time
from pathlib import Path

# 添加项目根目录到 Python 路径
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_whisper_onnx")

def test_whisper_onnx(audio_path):
    """测试 Whisper ONNX 转录功能"""
    try:
        # 导入 Whisper ONNX 模块
        from mcp.whisper_onnx import WhisperONNX, is_whisper_onnx_available
        
        # 检查 Whisper ONNX 是否可用
        if not is_whisper_onnx_available():
            logger.error("Whisper ONNX 不可用，请先运行 setup_whisper_onnx.py 安装")
            return False
        
        # 获取模型目录
        model_dir = os.path.join(ROOT_DIR, "models", "whisper_onnx")
        
        # 创建 Whisper ONNX 实例
        logger.info("创建 Whisper ONNX 实例...")
        whisper = WhisperONNX(
            model_dir=model_dir,
            model_size="base"
        )
        
        # 执行转录
        logger.info(f"开始转录音频: {audio_path}")
        start_time = time.time()
        
        result = whisper.transcribe(audio_path)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 输出结果
        logger.info(f"转录完成，耗时: {processing_time:.2f}秒")
        logger.info(f"转录文本: {result['text']}")
        
        # 保存结果到文件
        output_path = os.path.join(ROOT_DIR, "data", "test_transcription.json")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        import json
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"转录结果已保存到: {output_path}")
        
        return True
    
    except ImportError as e:
        logger.error(f"导入 Whisper ONNX 模块失败: {str(e)}")
        logger.error("请先运行 setup_whisper_onnx.py 安装必要的依赖")
        return False
    
    except Exception as e:
        logger.error(f"测试 Whisper ONNX 时出错: {str(e)}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="测试 Whisper ONNX 功能")
    parser.add_argument("--audio", type=str, help="音频文件路径")
    
    args = parser.parse_args()
    
    # 检查音频文件
    audio_path = args.audio
    if not audio_path:
        # 使用默认测试音频
        audio_path = os.path.join(ROOT_DIR, "data", "test.mp3")
        if not os.path.exists(audio_path):
            logger.error(f"默认测试音频不存在: {audio_path}")
            logger.error("请提供音频文件路径: --audio /path/to/audio.mp3")
            return 1
    
    if not os.path.exists(audio_path):
        logger.error(f"音频文件不存在: {audio_path}")
        return 1
    
    print("\n" + "=" * 50)
    print("Whisper ONNX 测试程序")
    print("=" * 50 + "\n")
    
    # 测试 Whisper ONNX
    success = test_whisper_onnx(audio_path)
    
    if success:
        print("\n" + "=" * 50)
        print("测试成功!")
        print("=" * 50 + "\n")
        return 0
    else:
        print("\n" + "=" * 50)
        print("测试失败!")
        print("=" * 50 + "\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
