#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Whisper.cpp 设置脚本
用于下载、编译和配置 Whisper.cpp，针对 Snapdragon XElite 优化
"""

import os
import sys
import subprocess
import platform
import argparse
import logging
import shutil
import json
import requests
import zipfile
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
logger = logging.getLogger("setup_whisper_cpp")

# Whisper.cpp 仓库 URL
WHISPER_CPP_REPO = "https://github.com/ggerganov/whisper.cpp.git"

# 可用的模型列表
AVAILABLE_MODELS = [
    "tiny.en", "tiny", "base.en", "base", "small.en", "small", 
    "medium.en", "medium", "large-v1", "large-v2", "large-v3", "large-v3-turbo",
    # 量化模型
    "tiny-q5_1", "tiny.en-q5_1", "tiny-q8_0", 
    "base-q5_1", "base.en-q5_1", "base-q8_0", 
    "small.en-tdrz", "small-q5_1", "small.en-q5_1", "small-q8_0", 
    "medium-q5_0", "medium.en-q5_0", "medium-q8_0", 
    "large-v2-q5_0", "large-v2-q8_0", "large-v3-q5_0", 
    "large-v3-turbo-q5_0", "large-v3-turbo-q8_0"
]

def run_command(cmd: List[str], cwd: Optional[str] = None) -> bool:
    """
    运行命令
    
    Args:
        cmd: 命令列表
        cwd: 工作目录
    
    Returns:
        命令是否成功执行
    """
    try:
        logger.info(f"运行命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.info(f"命令执行成功")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"命令执行失败: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"命令执行异常: {str(e)}")
        return False

def check_dependencies() -> bool:
    """
    检查依赖项
    
    Returns:
        依赖项是否满足
    """
    dependencies = ["git", "cmake"]
    
    for dep in dependencies:
        try:
            subprocess.run(
                [dep, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            logger.info(f"依赖项 {dep} 已安装")
        except:
            logger.error(f"依赖项 {dep} 未安装")
            return False
    
    return True

def download_whisper_cpp(target_dir: str) -> bool:
    """
    下载 Whisper.cpp 代码
    
    Args:
        target_dir: 目标目录
    
    Returns:
        是否成功下载
    """
    # 检查目标目录是否已存在
    if os.path.exists(target_dir):
        logger.info(f"目标目录已存在: {target_dir}")
        
        # 检查是否为 git 仓库
        git_dir = os.path.join(target_dir, ".git")
        if os.path.exists(git_dir):
            logger.info("更新 Whisper.cpp 代码")
            return run_command(["git", "pull"], cwd=target_dir)
        else:
            logger.info("目标目录不是 git 仓库，将删除并重新克隆")
            shutil.rmtree(target_dir)
    
    # 创建父目录
    os.makedirs(os.path.dirname(target_dir), exist_ok=True)
    
    # 克隆仓库
    logger.info(f"克隆 Whisper.cpp 仓库: {WHISPER_CPP_REPO}")
    return run_command(["git", "clone", WHISPER_CPP_REPO, target_dir])

def download_model(model_name: str, model_dir: str) -> bool:
    """
    下载 Whisper 模型
    
    Args:
        model_name: 模型名称
        model_dir: 模型目录
    
    Returns:
        是否成功下载
    """
    # 检查模型名称是否有效
    if model_name not in AVAILABLE_MODELS:
        logger.error(f"无效的模型名称: {model_name}")
        logger.info(f"可用的模型: {', '.join(AVAILABLE_MODELS)}")
        return False
    
    # 检查模型目录是否存在
    os.makedirs(model_dir, exist_ok=True)
    
    # 检查模型文件是否已存在
    model_file = os.path.join(model_dir, f"ggml-{model_name}.bin")
    if os.path.exists(model_file):
        logger.info(f"模型文件已存在: {model_file}")
        return True
    
    # 构建下载脚本路径
    download_script = os.path.join(ROOT_DIR, "whisper_cpp", "models", "download-ggml-model.sh")
    
    # 检查下载脚本是否存在
    if not os.path.exists(download_script):
        logger.error(f"下载脚本不存在: {download_script}")
        return False
    
    # 在 Windows 上使用 Git Bash 运行脚本
    if platform.system() == "Windows":
        # 尝试查找 Git Bash
        git_bash_paths = [
            "C:\\Program Files\\Git\\bin\\bash.exe",
            "C:\\Program Files (x86)\\Git\\bin\\bash.exe"
        ]
        
        bash_path = None
        for path in git_bash_paths:
            if os.path.exists(path):
                bash_path = path
                break
        
        if bash_path:
            logger.info(f"使用 Git Bash 下载模型: {bash_path}")
            return run_command([bash_path, download_script, model_name], cwd=os.path.dirname(download_script))
        else:
            logger.error("未找到 Git Bash，无法下载模型")
            return False
    else:
        # 在 Linux/Mac 上直接运行脚本
        return run_command(["bash", download_script, model_name], cwd=os.path.dirname(download_script))

def build_whisper_cpp(source_dir: str, build_dir: str, optimize_for_xelite: bool = True) -> bool:
    """
    编译 Whisper.cpp
    
    Args:
        source_dir: 源代码目录
        build_dir: 构建目录
        optimize_for_xelite: 是否针对 Snapdragon XElite 优化
    
    Returns:
        是否成功编译
    """
    # 检查源代码目录是否存在
    if not os.path.exists(source_dir):
        logger.error(f"源代码目录不存在: {source_dir}")
        return False
    
    # 创建构建目录
    os.makedirs(build_dir, exist_ok=True)
    
    # 构建 CMake 命令
    cmake_args = [
        "cmake",
        "..",
        "-DBUILD_SHARED_LIBS=OFF",
        "-DWHISPER_BUILD_TESTS=OFF",
        "-DWHISPER_BUILD_SERVER=ON"
    ]
    
    # 添加 Snapdragon XElite 优化选项
    if optimize_for_xelite:
        cmake_args.extend([
            "-DWHISPER_ENABLE_OPENVINO=ON",  # 启用 OpenVINO 支持
            "-DWHISPER_SUPPORT_QNNA=ON",     # 启用 QNN 加速
            "-DWHISPER_SUPPORT_ARMNN=ON",    # 启用 ArmNN 支持
            "-DWHISPER_SUPPORT_XNNPACK=ON",  # 启用 XNNPACK 支持
            "-DWHISPER_ENABLE_NEON=ON"       # 启用 NEON 指令集
        ])
    
    # 运行 CMake 配置
    if not run_command(cmake_args, cwd=build_dir):
        return False
    
    # 运行 CMake 构建
    build_cmd = ["cmake", "--build", ".", "--config", "Release"]
    return run_command(build_cmd, cwd=build_dir)

def copy_server_files(source_dir: str, target_dir: str) -> bool:
    """
    复制服务器文件
    
    Args:
        source_dir: 源目录
        target_dir: 目标目录
    
    Returns:
        是否成功复制
    """
    try:
        # 检查源目录是否存在
        if not os.path.exists(source_dir):
            logger.error(f"源目录不存在: {source_dir}")
            return False
        
        # 创建目标目录
        os.makedirs(target_dir, exist_ok=True)
        
        # 查找服务器可执行文件
        server_exe = None
        for path in [
            os.path.join(source_dir, "bin", "Release", "whisper-server.exe"),
            os.path.join(source_dir, "bin", "whisper-server.exe"),
            os.path.join(source_dir, "bin", "Release", "whisper-server"),
            os.path.join(source_dir, "bin", "whisper-server")
        ]:
            if os.path.exists(path):
                server_exe = path
                break
        
        if not server_exe:
            logger.error("未找到服务器可执行文件")
            return False
        
        # 复制服务器可执行文件
        target_exe = os.path.join(target_dir, os.path.basename(server_exe))
        logger.info(f"复制服务器可执行文件: {server_exe} -> {target_exe}")
        shutil.copy2(server_exe, target_exe)
        
        return True
        
    except Exception as e:
        logger.error(f"复制服务器文件失败: {str(e)}")
        return False

def create_config_file(config_dir: str, model_name: str, optimize_for_xelite: bool = True) -> bool:
    """
    创建配置文件
    
    Args:
        config_dir: 配置目录
        model_name: 模型名称
        optimize_for_xelite: 是否针对 Snapdragon XElite 优化
    
    Returns:
        是否成功创建
    """
    try:
        # 创建配置目录
        os.makedirs(config_dir, exist_ok=True)
        
        # 创建配置文件
        config_file = os.path.join(config_dir, "whisper_cpp_config.json")
        
        # 配置内容
        config = {
            "model_name": model_name,
            "server_host": "127.0.0.1",
            "server_port": 8178,
            "use_xelite": optimize_for_xelite,
            "xelite_config": {
                "num_threads": 8,
                "use_gpu": True,
                "use_dsp": True,
                "use_npu": True
            }
        }
        
        # 写入配置文件
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        
        logger.info(f"配置文件已创建: {config_file}")
        return True
        
    except Exception as e:
        logger.error(f"创建配置文件失败: {str(e)}")
        return False

def update_project_config(config_file: str, model_name: str) -> bool:
    """
    更新项目配置
    
    Args:
        config_file: 配置文件路径
        model_name: 模型名称
    
    Returns:
        是否成功更新
    """
    try:
        import yaml
        
        # 检查配置文件是否存在
        if not os.path.exists(config_file):
            logger.error(f"配置文件不存在: {config_file}")
            return False
        
        # 读取配置文件
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        # 更新配置
        if "meeting" not in config:
            config["meeting"] = {}
        
        if "whisper" not in config["meeting"]:
            config["meeting"]["whisper"] = {}
        
        # 更新 Whisper 配置
        whisper_config = config["meeting"]["whisper"]
        whisper_config["use_cpp"] = True
        whisper_config["model_name"] = model_name
        whisper_config["model_path"] = str(os.path.join(ROOT_DIR, "whisper_cpp", "models"))
        whisper_config["server_host"] = "127.0.0.1"
        whisper_config["server_port"] = 8178
        whisper_config["use_xelite"] = True
        whisper_config["num_threads"] = 8
        whisper_config["use_gpu"] = True
        whisper_config["use_dsp"] = True
        whisper_config["use_npu"] = True
        
        # 写入配置文件
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"项目配置已更新: {config_file}")
        return True
        
    except Exception as e:
        logger.error(f"更新项目配置失败: {str(e)}")
        return False

def create_start_script(script_dir: str) -> bool:
    """
    创建启动脚本
    
    Args:
        script_dir: 脚本目录
    
    Returns:
        是否成功创建
    """
    try:
        # 创建脚本目录
        os.makedirs(script_dir, exist_ok=True)
        
        # 创建启动脚本
        script_file = os.path.join(script_dir, "start_whisper_cpp_server.py")
        
        # 脚本内容
        script_content = """#!/usr/bin/env python
# -*- coding: utf-8 -*-

\"\"\"
Whisper.cpp 服务启动脚本
用于启动 Whisper.cpp 服务
\"\"\"

import os
import sys
import json
import argparse
import subprocess
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
ROOT_DIR = Path(__file__).parent.parent.absolute()
sys.path.append(str(ROOT_DIR))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("start_whisper_cpp_server")

def load_config():
    \"\"\"
    加载配置
    
    Returns:
        配置信息
    \"\"\"
    config_file = os.path.join(ROOT_DIR, "whisper_cpp", "config", "whisper_cpp_config.json")
    
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载配置失败: {str(e)}")
        return {}

def start_server(config):
    \"\"\"
    启动服务
    
    Args:
        config: 配置信息
    
    Returns:
        服务进程
    \"\"\"
    try:
        # 获取服务可执行文件路径
        server_dir = os.path.join(ROOT_DIR, "whisper_cpp")
        server_exe = os.path.join(server_dir, "whisper-server.exe")
        
        if not os.path.exists(server_exe):
            server_exe = os.path.join(server_dir, "whisper-server")
            
            if not os.path.exists(server_exe):
                logger.error(f"服务可执行文件不存在")
                return None
        
        # 获取模型文件路径
        model_name = config.get("model_name", "small")
        model_dir = os.path.join(server_dir, "models")
        model_file = os.path.join(model_dir, f"ggml-{model_name}.bin")
        
        if not os.path.exists(model_file):
            logger.error(f"模型文件不存在: {model_file}")
            return None
        
        # 构建命令行参数
        cmd = [
            server_exe,
            "--model", model_file,
            "--host", config.get("server_host", "127.0.0.1"),
            "--port", str(config.get("server_port", 8178)),
            "--diarize",
            "--print-progress"
        ]
        
        # 添加 Snapdragon XElite 优化参数
        if config.get("use_xelite", True):
            xelite_config = config.get("xelite_config", {})
            cmd.extend([
                "--threads", str(xelite_config.get("num_threads", 8)),
                "--use-gpu", "1" if xelite_config.get("use_gpu", True) else "0",
                "--use-dsp", "1" if xelite_config.get("use_dsp", True) else "0",
                "--use-npu", "1" if xelite_config.get("use_npu", True) else "0"
            ])
        
        # 启动服务进程
        logger.info(f"启动 Whisper.cpp 服务: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(f"Whisper.cpp 服务已启动，进程 ID: {process.pid}")
        return process
        
    except Exception as e:
        logger.error(f"启动服务失败: {str(e)}")
        return None

def main():
    \"\"\"主函数\"\"\"
    parser = argparse.ArgumentParser(description="Whisper.cpp 服务启动脚本")
    parser.add_argument("--host", help="服务主机地址")
    parser.add_argument("--port", type=int, help="服务端口")
    parser.add_argument("--model", help="模型名称")
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config()
    
    # 更新配置
    if args.host:
        config["server_host"] = args.host
    
    if args.port:
        config["server_port"] = args.port
    
    if args.model:
        config["model_name"] = args.model
    
    # 启动服务
    process = start_server(config)
    
    if process:
        try:
            # 等待服务进程结束
            process.wait()
        except KeyboardInterrupt:
            logger.info("接收到中断信号，停止服务")
            process.terminate()
            try:
                process.wait(timeout=5)
            except:
                process.kill()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""
        
        # 写入脚本文件
        with open(script_file, "w", encoding="utf-8") as f:
            f.write(script_content)
        
        logger.info(f"启动脚本已创建: {script_file}")
        return True
        
    except Exception as e:
        logger.error(f"创建启动脚本失败: {str(e)}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Whisper.cpp 设置脚本")
    parser.add_argument("--model", default="small", choices=AVAILABLE_MODELS, help="模型名称")
    parser.add_argument("--no-xelite", action="store_true", help="不针对 Snapdragon XElite 优化")
    
    args = parser.parse_args()
    
    # 检查依赖项
    if not check_dependencies():
        logger.error("依赖项检查失败")
        return 1
    
    # 设置目录
    whisper_cpp_dir = os.path.join(ROOT_DIR, "whisper_cpp")
    source_dir = os.path.join(whisper_cpp_dir, "source")
    build_dir = os.path.join(source_dir, "build")
    model_dir = os.path.join(whisper_cpp_dir, "models")
    config_dir = os.path.join(whisper_cpp_dir, "config")
    script_dir = os.path.join(ROOT_DIR, "scripts")
    
    # 下载 Whisper.cpp 代码
    if not download_whisper_cpp(source_dir):
        logger.error("下载 Whisper.cpp 代码失败")
        return 1
    
    # 下载模型
    if not download_model(args.model, model_dir):
        logger.error(f"下载模型 {args.model} 失败")
        return 1
    
    # 编译 Whisper.cpp
    optimize_for_xelite = not args.no_xelite
    if not build_whisper_cpp(source_dir, build_dir, optimize_for_xelite):
        logger.error("编译 Whisper.cpp 失败")
        return 1
    
    # 复制服务器文件
    if not copy_server_files(build_dir, whisper_cpp_dir):
        logger.error("复制服务器文件失败")
        return 1
    
    # 创建配置文件
    if not create_config_file(config_dir, args.model, optimize_for_xelite):
        logger.error("创建配置文件失败")
        return 1
    
    # 更新项目配置
    config_file = os.path.join(ROOT_DIR, "config.yaml")
    if not update_project_config(config_file, args.model):
        logger.error("更新项目配置失败")
        return 1
    
    # 创建启动脚本
    if not create_start_script(script_dir):
        logger.error("创建启动脚本失败")
        return 1
    
    logger.info("Whisper.cpp 设置完成")
    logger.info(f"模型: {args.model}")
    logger.info(f"优化: {'已针对 Snapdragon XElite 优化' if optimize_for_xelite else '未优化'}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
