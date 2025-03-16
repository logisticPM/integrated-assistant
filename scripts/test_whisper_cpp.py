#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Whisper.cpp 测试脚本
用于测试 Whisper.cpp 服务在 Snapdragon XElite 上的性能
"""

import os
import sys
import time
import json
import argparse
import logging
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional

# 添加项目根目录到 Python 路径
ROOT_DIR = Path(__file__).parent.parent.absolute()
sys.path.append(str(ROOT_DIR))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_whisper_cpp")

def load_config():
    """
    加载配置
    
    Returns:
        配置信息
    """
    config_file = os.path.join(ROOT_DIR, "config.yaml")
    
    try:
        import yaml
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"加载配置失败: {str(e)}")
        return {}

def check_server_running(host: str, port: int) -> bool:
    """
    检查服务是否运行
    
    Args:
        host: 服务主机地址
        port: 服务端口
    
    Returns:
        服务是否运行
    """
    try:
        response = requests.get(f"http://{host}:{port}/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def start_server():
    """
    启动服务
    
    Returns:
        服务进程
    """
    try:
        # 导入启动脚本
        sys.path.append(os.path.join(ROOT_DIR, "scripts"))
        from start_whisper_cpp_server import start_server as start_whisper_server
        from start_whisper_cpp_server import load_config as load_whisper_config
        
        # 加载配置
        config = load_whisper_config()
        
        # 启动服务
        return start_whisper_server(config)
        
    except Exception as e:
        logger.error(f"启动服务失败: {str(e)}")
        return None

def transcribe_audio(audio_path: str, host: str, port: int) -> Dict[str, Any]:
    """
    转录音频
    
    Args:
        audio_path: 音频文件路径
        host: 服务主机地址
        port: 服务端口
    
    Returns:
        转录结果
    """
    try:
        # 检查音频文件是否存在
        if not os.path.exists(audio_path):
            logger.error(f"音频文件不存在: {audio_path}")
            return {"error": f"音频文件不存在: {audio_path}"}
        
        # 记录开始时间
        start_time = time.time()
        
        # 发送转录请求
        with open(audio_path, "rb") as f:
            files = {"file": f}
            response = requests.post(
                f"http://{host}:{port}/inference",
                files=files,
                timeout=300  # 5分钟超时
            )
        
        # 检查响应状态
        if response.status_code != 200:
            return {"error": f"转录请求失败，状态码: {response.status_code}"}
        
        # 解析响应
        result = response.json()
        
        # 计算处理时间
        processing_time = time.time() - start_time
        
        # 构建转录结果
        transcription = {
            "text": result.get("text", ""),
            "segments": result.get("segments", []),
            "language": result.get("language", "auto"),
            "processing_time": processing_time
        }
        
        logger.info(f"转录完成，耗时: {processing_time:.2f}秒")
        return transcription
        
    except Exception as e:
        logger.error(f"转录失败: {str(e)}")
        return {"error": f"转录失败: {str(e)}"}

def benchmark(audio_path: str, host: str, port: int, iterations: int = 3) -> Dict[str, Any]:
    """
    性能基准测试
    
    Args:
        audio_path: 音频文件路径
        host: 服务主机地址
        port: 服务端口
        iterations: 迭代次数
    
    Returns:
        基准测试结果
    """
    try:
        # 检查音频文件是否存在
        if not os.path.exists(audio_path):
            logger.error(f"音频文件不存在: {audio_path}")
            return {"error": f"音频文件不存在: {audio_path}"}
        
        # 检查服务是否运行
        if not check_server_running(host, port):
            logger.error(f"服务未运行: {host}:{port}")
            return {"error": f"服务未运行: {host}:{port}"}
        
        # 记录音频文件大小
        audio_size = os.path.getsize(audio_path) / (1024 * 1024)  # MB
        
        # 运行基准测试
        processing_times = []
        
        for i in range(iterations):
            logger.info(f"运行基准测试 {i+1}/{iterations}")
            
            # 转录音频
            result = transcribe_audio(audio_path, host, port)
            
            if "error" in result:
                logger.error(f"基准测试失败: {result['error']}")
                return {"error": f"基准测试失败: {result['error']}"}
            
            # 记录处理时间
            processing_times.append(result["processing_time"])
        
        # 计算平均处理时间
        avg_processing_time = sum(processing_times) / len(processing_times)
        
        # 计算实时因子（处理时间 / 音频长度）
        # 假设音频长度为 1 分钟
        audio_length = 60  # 秒
        rtf = avg_processing_time / audio_length
        
        # 构建基准测试结果
        benchmark_result = {
            "audio_path": audio_path,
            "audio_size_mb": audio_size,
            "iterations": iterations,
            "processing_times": processing_times,
            "avg_processing_time": avg_processing_time,
            "rtf": rtf
        }
        
        logger.info(f"基准测试完成，平均处理时间: {avg_processing_time:.2f}秒，RTF: {rtf:.4f}")
        return benchmark_result
        
    except Exception as e:
        logger.error(f"基准测试失败: {str(e)}")
        return {"error": f"基准测试失败: {str(e)}"}

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Whisper.cpp 测试脚本")
    parser.add_argument("--audio", required=True, help="音频文件路径")
    parser.add_argument("--host", default="127.0.0.1", help="服务主机地址")
    parser.add_argument("--port", type=int, default=8178, help="服务端口")
    parser.add_argument("--benchmark", action="store_true", help="运行基准测试")
    parser.add_argument("--iterations", type=int, default=3, help="基准测试迭代次数")
    
    args = parser.parse_args()
    
    # 检查服务是否运行
    if not check_server_running(args.host, args.port):
        logger.info(f"服务未运行，尝试启动服务")
        process = start_server()
        
        if not process:
            logger.error("启动服务失败")
            return 1
        
        # 等待服务启动
        for _ in range(10):
            if check_server_running(args.host, args.port):
                logger.info("服务已启动")
                break
            time.sleep(1)
        else:
            logger.error("服务启动超时")
            return 1
    
    # 运行基准测试
    if args.benchmark:
        logger.info(f"运行基准测试，音频文件: {args.audio}，迭代次数: {args.iterations}")
        result = benchmark(args.audio, args.host, args.port, args.iterations)
        
        if "error" in result:
            logger.error(f"基准测试失败: {result['error']}")
            return 1
        
        # 打印基准测试结果
        print("\n" + "="*50)
        print("Whisper.cpp 基准测试结果")
        print("="*50)
        print(f"音频文件: {result['audio_path']}")
        print(f"音频大小: {result['audio_size_mb']:.2f} MB")
        print(f"迭代次数: {result['iterations']}")
        print(f"处理时间: {', '.join([f'{t:.2f}秒' for t in result['processing_times']])}")
        print(f"平均处理时间: {result['avg_processing_time']:.2f}秒")
        print(f"实时因子 (RTF): {result['rtf']:.4f}")
        print("="*50)
        
        # 保存基准测试结果
        result_file = os.path.join(ROOT_DIR, "data", "whisper_cpp_benchmark.json")
        os.makedirs(os.path.dirname(result_file), exist_ok=True)
        
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4)
        
        logger.info(f"基准测试结果已保存到: {result_file}")
        
    else:
        # 转录音频
        logger.info(f"转录音频文件: {args.audio}")
        result = transcribe_audio(args.audio, args.host, args.port)
        
        if "error" in result:
            logger.error(f"转录失败: {result['error']}")
            return 1
        
        # 打印转录结果
        print("\n" + "="*50)
        print("Whisper.cpp 转录结果")
        print("="*50)
        print(f"文本: {result['text']}")
        print(f"语言: {result['language']}")
        print(f"处理时间: {result['processing_time']:.2f}秒")
        print("="*50)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
