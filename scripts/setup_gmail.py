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
    config_path = os.path.join(project_root, "config.yaml")
    try:
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
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
    parser.add_argument('--client-secret-content', type=str, help='Google API客户端密钥内容（JSON格式）')
    parser.add_argument('--token-content', type=str, help='Gmail令牌内容（JSON格式）')
    parser.add_argument('--credentials-dir', type=str, help='凭证目录路径')
    parser.add_argument('--port', type=int, help='OAuth认证服务器端口')
    args = parser.parse_args()
    
    # 加载配置
    config = load_config()
    
    # 确保Gmail配置存在
    if "gmail" not in config:
        config["gmail"] = {
            "credentials_dir": "data/credentials",
            "auth_port": 54191
        }
    
    # 应用命令行参数
    if args.credentials_dir:
        config["gmail"]["credentials_dir"] = args.credentials_dir
    
    if args.port:
        config["gmail"]["auth_port"] = args.port
    
    # 创建Gmail服务实例
    gmail_service = GmailService(config)
    
    # 设置客户端密钥
    client_secret_content = None
    
    # 优先使用命令行参数提供的密钥内容
    if args.client_secret_content:
        client_secret_content = args.client_secret_content
    # 其次使用环境变量
    elif os.getenv("GMAIL_SECRET"):
        client_secret_content = os.getenv("GMAIL_SECRET")
    # 最后使用指定的文件路径
    elif args.client_secret:
        client_secret_path = os.path.abspath(args.client_secret)
        if not os.path.exists(client_secret_path):
            logger.error(f"客户端密钥文件不存在: {client_secret_path}")
            return
        
        try:
            with open(client_secret_path, "r", encoding="utf-8") as f:
                client_secret_content = f.read()
        except Exception as e:
            logger.error(f"读取客户端密钥文件失败: {str(e)}")
            return
    
    # 如果有客户端密钥内容，保存到目标路径
    if client_secret_content:
        # 确保凭证目录存在
        os.makedirs(os.path.dirname(gmail_service.secrets_path), exist_ok=True)
        
        # 保存客户端密钥
        with open(gmail_service.secrets_path, "w", encoding="utf-8") as f:
            f.write(client_secret_content)
        logger.info(f"已保存客户端密钥到: {gmail_service.secrets_path}")
    
    # 设置令牌内容
    token_content = None
    if args.token_content:
        token_content = args.token_content
    elif os.getenv("GMAIL_TOKEN"):
        token_content = os.getenv("GMAIL_TOKEN")
    
    # 初始化Gmail认证
    logger.info("正在启动Gmail认证流程...")
    logger.info("将会打开浏览器窗口，请按照提示完成授权")
    
    try:
        # 获取凭证
        creds = gmail_service.get_credentials(
            gmail_token=token_content,
            gmail_secret=client_secret_content
        )
        
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
    except FileNotFoundError as e:
        logger.error(str(e))
        logger.info("请确保提供了有效的客户端密钥文件或内容")
    except Exception as e:
        logger.error(f"Gmail认证过程中发生错误: {str(e)}")

if __name__ == "__main__":
    main()
