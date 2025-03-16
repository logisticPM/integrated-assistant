#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
本地模型设置脚本
用于下载和设置本地模型，包括 Whisper 和 LLM 模型
"""

import os
import sys
import logging
import argparse
import shutil
import json
import yaml
import requests
from tqdm import tqdm
from pathlib import Path

# 添加项目根目录到 Python 路径
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("setup_local_models")

# 模型信息
MODEL_INFO = {
    "whisper": {
        "tiny": {
            "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin",
            "size": 75000000,  # 约 75MB
            "description": "Whisper Tiny 模型 (英文)"
        },
        "base": {
            "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin",
            "size": 142000000,  # 约 142MB
            "description": "Whisper Base 模型 (英文)"
        },
        "tiny-onnx": {
            "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en-q5_1.bin",
            "size": 31000000,  # 约 31MB
            "description": "Whisper Tiny ONNX 模型 (英文, 量化)"
        },
        "base-onnx": {
            "url": "https://huggingface.co/openai/whisper-base/resolve/main/model.onnx",
            "size": 142000000,  # 约 142MB
            "description": "Whisper Base ONNX 模型 (英文)"
        }
    },
    "llm": {
        "llama2-7b-onnx": {
            "url": "https://huggingface.co/TheBloke/Llama-2-7B-ONNX/resolve/main/Llama-2-7B-ONNX-fp16.onnx",
            "size": 7000000000,  # 约 7GB
            "description": "Llama 2 7B ONNX 模型 (FP16)",
            "tokenizer_url": "https://huggingface.co/TheBloke/Llama-2-7B-ONNX/raw/main/tokenizer.json"
        },
        "phi2-onnx": {
            "url": "https://huggingface.co/microsoft/phi-2/resolve/main/onnx/model_optimized_fp16.onnx",
            "size": 2500000000,  # 约 2.5GB
            "description": "Microsoft Phi-2 ONNX 模型 (FP16)",
            "tokenizer_url": "https://huggingface.co/microsoft/phi-2/raw/main/tokenizer.json"
        }
    }
}

def download_file(url, dest_path, description=None):
    """
    下载文件，显示进度条
    
    Args:
        url: 下载 URL
        dest_path: 目标路径
        description: 描述
    
    Returns:
        是否下载成功
    """
    try:
        # 创建目标目录
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        # 如果文件已存在，跳过下载
        if os.path.exists(dest_path):
            logger.info(f"文件已存在: {dest_path}")
            return True
        
        # 下载文件
        logger.info(f"开始下载: {description or url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # 获取文件大小
        total_size = int(response.headers.get('content-length', 0))
        
        # 显示进度条
        with open(dest_path, 'wb') as f, tqdm(
            desc=os.path.basename(dest_path),
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))
        
        logger.info(f"下载完成: {dest_path}")
        return True
    
    except Exception as e:
        logger.error(f"下载失败: {url} - {str(e)}")
        return False

def setup_whisper_model(model_size="base", force=False, use_onnx=True):
    """
    设置 Whisper 模型
    
    Args:
        model_size: 模型大小，tiny 或 base
        force: 是否强制重新下载
        use_onnx: 是否使用 ONNX 模型
    
    Returns:
        是否成功
    """
    # 确定模型类型
    model_key = f"{model_size}{'-onnx' if use_onnx else ''}"
    
    if model_key not in MODEL_INFO["whisper"]:
        logger.error(f"不支持的 Whisper 模型: {model_key}")
        return False
    
    # 模型信息
    model_info = MODEL_INFO["whisper"][model_key]
    
    # 模型目录
    model_dir = os.path.join(root_dir, "models", "whisper")
    os.makedirs(model_dir, exist_ok=True)
    
    # 模型路径
    model_path = os.path.join(model_dir, f"whisper-{model_key}.bin")
    
    # 如果强制重新下载，删除现有文件
    if force and os.path.exists(model_path):
        os.remove(model_path)
    
    # 下载模型
    success = download_file(
        url=model_info["url"],
        dest_path=model_path,
        description=model_info["description"]
    )
    
    if success:
        # 创建配置文件
        config = {
            "model_file": f"whisper-{model_key}.bin",
            "model_type": model_size,
            "use_onnx": use_onnx,
            "use_qnn": False,  # 默认不使用 QNN
            "language": "auto"
        }
        
        config_path = os.path.join(model_dir, "config.json")
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"已创建 Whisper 模型配置文件: {config_path}")
        
        # 更新配置文件
        update_config(
            model_type="whisper",
            model_path=model_dir,
            use_local=True,
            use_onnx=use_onnx
        )
    
    return success

def setup_llm_model(model_name="phi2-onnx", force=False, use_qnn=False):
    """
    设置 LLM 模型
    
    Args:
        model_name: 模型名称
        force: 是否强制重新下载
        use_qnn: 是否使用 QNN 执行提供程序
    
    Returns:
        是否成功
    """
    if model_name not in MODEL_INFO["llm"]:
        logger.error(f"不支持的 LLM 模型: {model_name}")
        return False
    
    # 模型信息
    model_info = MODEL_INFO["llm"][model_name]
    
    # 模型目录
    model_dir = os.path.join(root_dir, "models", "llm")
    os.makedirs(model_dir, exist_ok=True)
    
    # 模型路径
    model_file = f"{model_name.split('-')[0]}.onnx"
    model_path = os.path.join(model_dir, model_file)
    tokenizer_file = "tokenizer.json"
    tokenizer_path = os.path.join(model_dir, tokenizer_file)
    
    # 如果强制重新下载，删除现有文件
    if force:
        if os.path.exists(model_path):
            os.remove(model_path)
        if os.path.exists(tokenizer_path):
            os.remove(tokenizer_path)
    
    # 下载模型
    success = download_file(
        url=model_info["url"],
        dest_path=model_path,
        description=model_info["description"]
    )
    
    # 下载分词器
    if success and "tokenizer_url" in model_info:
        success = download_file(
            url=model_info["tokenizer_url"],
            dest_path=tokenizer_path,
            description=f"{model_info['description']} 分词器"
        )
    
    if success:
        # 创建配置文件
        config = {
            "model_file": model_file,
            "tokenizer_file": tokenizer_file,
            "model_name": model_name.split('-')[0],
            "use_qnn": use_qnn,
            "max_context_length": 2048,
            "max_new_tokens": 512,
            "temperature": 0.7
        }
        
        config_path = os.path.join(model_dir, "config.json")
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"已创建 LLM 模型配置文件: {config_path}")
        
        # 更新配置文件
        update_config(
            model_type="llm",
            model_path=model_dir,
            use_local=True,
            use_qnn=use_qnn
        )
    
    return success

def update_config(model_type, model_path, use_local=True, use_onnx=True, use_qnn=False):
    """
    更新配置文件
    
    Args:
        model_type: 模型类型，whisper 或 llm
        model_path: 模型路径
        use_local: 是否使用本地模型
        use_onnx: 是否使用 ONNX 模型
        use_qnn: 是否使用 QNN 执行提供程序
    """
    try:
        # 配置文件路径
        config_path = os.path.join(root_dir, "config.yaml")
        
        # 读取配置文件
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 更新配置
        if model_type == "whisper":
            config["meeting"]["whisper"]["model_path"] = model_path
            config["meeting"]["whisper"]["use_local"] = use_local
            config["meeting"]["whisper"]["use_onnx"] = use_onnx
            config["meeting"]["whisper"]["use_qnn"] = use_qnn
        elif model_type == "llm":
            config["llm"]["model"] = "local" if use_local else "api"
            config["llm"]["model_path"] = model_path
            config["llm"]["local"]["enabled"] = use_local
            config["llm"]["local"]["use_qnn"] = use_qnn
        
        # 保存配置文件
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"已更新配置文件: {config_path}")
    
    except Exception as e:
        logger.error(f"更新配置文件失败: {str(e)}")

def check_dependencies():
    """
    检查依赖项
    
    Returns:
        是否满足依赖
    """
    try:
        # 检查 ONNX Runtime
        try:
            import onnxruntime
            logger.info(f"ONNX Runtime 版本: {onnxruntime.__version__}")
            
            # 检查可用的执行提供程序
            providers = onnxruntime.get_available_providers()
            logger.info(f"可用的执行提供程序: {providers}")
            
            # 检查是否支持 QNN
            if "QNNExecutionProvider" in providers:
                logger.info("支持 QNN 执行提供程序")
            else:
                logger.warning("不支持 QNN 执行提供程序，将使用 CPU 执行提供程序")
        except ImportError:
            logger.warning("未安装 ONNX Runtime，请安装: pip install onnxruntime")
            return False
        
        # 检查 Transformers
        try:
            import transformers
            logger.info(f"Transformers 版本: {transformers.__version__}")
        except ImportError:
            logger.warning("未安装 Transformers，请安装: pip install transformers")
            return False
        
        # 检查 NumPy
        try:
            import numpy
            logger.info(f"NumPy 版本: {numpy.__version__}")
        except ImportError:
            logger.warning("未安装 NumPy，请安装: pip install numpy==1.24.3")
            return False
        
        return True
    
    except Exception as e:
        logger.error(f"检查依赖项失败: {str(e)}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="设置本地模型")
    parser.add_argument("--whisper", choices=["tiny", "base"], help="设置 Whisper 模型")
    parser.add_argument("--llm", choices=["llama2-7b-onnx", "phi2-onnx"], help="设置 LLM 模型")
    parser.add_argument("--force", action="store_true", help="强制重新下载")
    parser.add_argument("--use-onnx", action="store_true", default=True, help="使用 ONNX 模型")
    parser.add_argument("--use-qnn", action="store_true", help="使用 QNN 执行提供程序")
    
    args = parser.parse_args()
    
    # 检查依赖项
    if not check_dependencies():
        logger.error("依赖项检查失败，请安装必要的依赖")
        return
    
    # 设置 Whisper 模型
    if args.whisper:
        setup_whisper_model(
            model_size=args.whisper,
            force=args.force,
            use_onnx=args.use_onnx
        )
    
    # 设置 LLM 模型
    if args.llm:
        setup_llm_model(
            model_name=args.llm,
            force=args.force,
            use_qnn=args.use_qnn
        )
    
    # 如果没有指定任何操作，显示帮助
    if not args.whisper and not args.llm:
        parser.print_help()

if __name__ == "__main__":
    main()
