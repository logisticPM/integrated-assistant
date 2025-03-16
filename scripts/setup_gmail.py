#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Gmail设置脚本 - 用于初始化Gmail认证
"""

import os
import sys
import argparse
import logging
import json

# 添加项目根目录到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from mcp.gmail_service import GmailService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("setup_gmail")

def load_config():
    """加载配置"""
    config_path = os.path.join(project_root, "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载配置失败: {str(e)}")
        return {
            "gmail": {
                "credentials_dir": "data/credentials",
                "auth_port": 54191
            }
        }

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='设置Gmail认证')
    parser.add_argument('--client-secret', type=str, help='Google API客户端密钥文件路径')
    args = parser.parse_args()
    
    # 加载配置
    config = load_config()
    
    # 确保Gmail配置存在
    if "gmail" not in config:
        config["gmail"] = {
            "credentials_dir": "data/credentials",
            "auth_port": 54191
        }
    
    # 创建Gmail服务实例
    gmail_service = GmailService(config)
    
    # 设置客户端密钥文件路径
    if args.client_secret:
        client_secret_path = os.path.abspath(args.client_secret)
        if not os.path.exists(client_secret_path):
            logger.error(f"客户端密钥文件不存在: {client_secret_path}")
            return
        
        # 确保凭证目录存在
        os.makedirs(gmail_service.credentials_dir, exist_ok=True)
        
        # 复制客户端密钥文件
        import shutil
        shutil.copy2(client_secret_path, gmail_service.secrets_path)
        logger.info(f"已复制客户端密钥文件到: {gmail_service.secrets_path}")
    
    # 初始化Gmail认证
    logger.info("正在启动Gmail认证流程...")
    logger.info("将会打开浏览器窗口，请按照提示完成授权")
    
    # 获取凭证
    creds = gmail_service.get_credentials()
    
    if creds and creds.valid:
        logger.info("Gmail认证成功！")
        
        # 测试连接
        result = gmail_service.test_connection()
        if result["success"]:
            logger.info(f"Gmail连接测试成功: {result['message']}")
            logger.info(f"关联的邮箱地址: {result.get('email', '未知')}")
        else:
            logger.error(f"Gmail连接测试失败: {result['message']}")
    else:
        logger.error("Gmail认证失败")

if __name__ == "__main__":
    main()
