#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
自动下载和安装 FFmpeg 的脚本
"""

import os
import sys
import subprocess
import logging
import tempfile
import zipfile
import shutil
import platform
import ctypes
from pathlib import Path
import urllib.request

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("setup_ffmpeg")

def is_admin():
    """检查是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def download_file(url, dest_path):
    """下载文件"""
    try:
        logger.info(f"正在下载 {url} 到 {dest_path}")
        urllib.request.urlretrieve(url, dest_path)
        return True
    except Exception as e:
        logger.error(f"下载失败: {str(e)}")
        return False

def extract_zip(zip_path, extract_path):
    """解压 ZIP 文件"""
    try:
        logger.info(f"正在解压 {zip_path} 到 {extract_path}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        return True
    except Exception as e:
        logger.error(f"解压失败: {str(e)}")
        return False

def setup_ffmpeg():
    """安装 FFmpeg"""
    if platform.system() != "Windows":
        logger.info("非 Windows 系统，跳过 FFmpeg 安装")
        return True
    
    # 检查 FFmpeg 是否已安装
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("FFmpeg 已安装，跳过安装步骤")
            return True
    except:
        pass
    
    # 如果不是管理员权限，则提示用户手动运行
    if not is_admin():
        logger.warning("需要管理员权限来安装 FFmpeg")
        logger.warning("请右键点击 scripts/install_ffmpeg.bat 并选择'以管理员身份运行'")
        return False
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    ffmpeg_zip = os.path.join(temp_dir, "ffmpeg.zip")
    extract_path = os.path.join(temp_dir, "extract")
    install_path = "C:\\ffmpeg"
    
    try:
        # 下载 FFmpeg
        ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        if not download_file(ffmpeg_url, ffmpeg_zip):
            return False
        
        # 创建解压目录
        os.makedirs(extract_path, exist_ok=True)
        
        # 解压文件
        if not extract_zip(ffmpeg_zip, extract_path):
            return False
        
        # 获取解压后的 FFmpeg 目录名称
        extracted_dir = next(Path(extract_path).glob("*"))
        
        # 创建安装目录
        if os.path.exists(install_path):
            logger.warning(f"FFmpeg 目录已存在，正在删除 {install_path}")
            shutil.rmtree(install_path)
        
        # 移动文件到安装目录
        logger.info(f"正在安装 FFmpeg 到 {install_path}")
        os.makedirs(install_path, exist_ok=True)
        
        # 复制文件
        for item in os.listdir(extracted_dir):
            s = os.path.join(extracted_dir, item)
            d = os.path.join(install_path, item)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
        
        # 设置环境变量
        logger.info("正在设置环境变量")
        bin_path = os.path.join(install_path, "bin")
        
        # 获取当前 PATH
        env_path = os.environ.get('PATH', '')
        
        # 检查是否已在 PATH 中
        if bin_path not in env_path:
            # 使用 PowerShell 设置系统环境变量
            ps_command = f'[Environment]::SetEnvironmentVariable("Path", "$env:Path;{bin_path}", "Machine")'
            subprocess.run(["powershell", "-Command", ps_command], check=True)
            logger.info(f"已将 {bin_path} 添加到系统 PATH 环境变量")
            
            # 更新当前会话的 PATH
            os.environ['PATH'] = f"{env_path};{bin_path}"
        
        # 验证安装
        logger.info("正在验证 FFmpeg 安装")
        try:
            result = subprocess.run([os.path.join(bin_path, "ffmpeg"), "-version"], 
                                   capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("FFmpeg 安装成功！")
                logger.info(f"版本信息: {result.stdout.splitlines()[0]}")
            else:
                logger.warning("无法验证 FFmpeg 安装，请重启终端后再次尝试")
        except Exception as e:
            logger.warning(f"验证 FFmpeg 安装时出错: {str(e)}")
        
        return True
        
    except Exception as e:
        logger.error(f"安装过程中发生错误: {str(e)}")
        return False
    finally:
        # 清理临时文件
        logger.info("正在清理临时文件")
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

def main():
    """主函数"""
    logger.info("开始安装 FFmpeg")
    if setup_ffmpeg():
        logger.info("FFmpeg 安装完成！")
        return 0
    else:
        logger.error("FFmpeg 安装失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
