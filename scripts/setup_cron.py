#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
设置定时任务脚本 - 用于设置自动处理邮件的定时任务
参考executive-ai-assistant项目的setup_cron.py
"""

import os
import sys
import argparse
import logging
import json
import subprocess
import platform

# 添加项目根目录到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("setup_cron")

def load_config():
    """加载配置"""
    config_path = os.path.join(project_root, "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载配置失败: {str(e)}")
        return {}

def setup_cron_linux(interval, script_path, args):
    """
    在Linux系统上设置cron任务
    
    Args:
        interval: 时间间隔（分钟）
        script_path: 脚本路径
        args: 脚本参数
    
    Returns:
        是否成功
    """
    try:
        # 构建cron表达式
        cron_expr = f"*/{interval} * * * * {sys.executable} {script_path} {args}"
        
        # 获取当前crontab内容
        process = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        current_crontab = process.stdout
        
        # 检查是否已存在相同任务
        if script_path in current_crontab:
            # 移除旧任务
            lines = current_crontab.splitlines()
            new_lines = [line for line in lines if script_path not in line]
            current_crontab = "\n".join(new_lines)
        
        # 添加新任务
        new_crontab = current_crontab + f"\n{cron_expr}\n"
        
        # 写入crontab
        process = subprocess.run(["crontab", "-"], input=new_crontab, text=True)
        
        if process.returncode == 0:
            logger.info(f"已成功设置cron任务，每{interval}分钟运行一次")
            return True
        else:
            logger.error(f"设置cron任务失败: {process.stderr}")
            return False
    
    except Exception as e:
        logger.exception(f"设置cron任务失败: {str(e)}")
        return False

def setup_scheduled_task_windows(interval, script_path, args):
    """
    在Windows系统上设置计划任务
    
    Args:
        interval: 时间间隔（分钟）
        script_path: 脚本路径
        args: 脚本参数
    
    Returns:
        是否成功
    """
    try:
        # 任务名称
        task_name = "IntegratedAssistant_EmailProcessor"
        
        # 删除已存在的任务
        subprocess.run(["schtasks", "/Delete", "/TN", task_name, "/F"], 
                      capture_output=True, text=True)
        
        # 构建命令
        command = f'"{sys.executable}" "{script_path}" {args}'
        
        # 创建新任务
        create_cmd = [
            "schtasks", "/Create", "/SC", "MINUTE", 
            "/MO", str(interval), "/TN", task_name, 
            "/TR", command
        ]
        
        process = subprocess.run(create_cmd, capture_output=True, text=True)
        
        if process.returncode == 0:
            logger.info(f"已成功设置计划任务，每{interval}分钟运行一次")
            return True
        else:
            logger.error(f"设置计划任务失败: {process.stderr}")
            return False
    
    except Exception as e:
        logger.exception(f"设置计划任务失败: {str(e)}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='设置邮件处理定时任务')
    
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="运行间隔（分钟）"
    )
    
    parser.add_argument(
        "--minutes-since",
        type=int,
        default=15,
        help="处理多少分钟前的邮件"
    )
    
    parser.add_argument(
        "--auto-reply",
        action="store_true",
        help="启用自动回复"
    )
    
    parser.add_argument(
        "--auto-categorize",
        action="store_true",
        help="启用自动分类"
    )
    
    parser.add_argument(
        "--auto-mark-read",
        action="store_true",
        help="启用自动标记为已读"
    )
    
    args = parser.parse_args()
    
    # 构建脚本参数
    script_args = f"--minutes-since {args.minutes_since}"
    
    if args.auto_reply:
        script_args += " --auto-reply"
    
    if args.auto_categorize:
        script_args += " --auto-categorize"
    
    if args.auto_mark_read:
        script_args += " --auto-mark-read"
    
    # 脚本路径
    email_processor_path = os.path.join(script_dir, "email_processor.py")
    
    # 根据操作系统设置定时任务
    system = platform.system()
    
    if system == "Linux" or system == "Darwin":
        success = setup_cron_linux(args.interval, email_processor_path, script_args)
    elif system == "Windows":
        success = setup_scheduled_task_windows(args.interval, email_processor_path, script_args)
    else:
        logger.error(f"不支持的操作系统: {system}")
        success = False
    
    if success:
        logger.info("定时任务设置成功")
    else:
        logger.error("定时任务设置失败")

if __name__ == "__main__":
    main()
