#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
移除电子邮件相关服务的脚本
此脚本将从集成助手项目中移除所有与Gmail和电子邮件相关的服务和依赖
"""

import os
import sys
import shutil
import logging
import yaml
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("remove_email_services")

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent.absolute()

# 需要删除的文件
FILES_TO_REMOVE = [
    # Gmail服务相关文件
    "mcp/gmail_service.py",
    "mcp/gmail_auth.py",
    "scripts/setup_gmail.py",
    "scripts/email_processor.py",
    "docs/gmail_setup_guide.md",
    "secrets.json.example"
]

# 需要修改的文件
FILES_TO_MODIFY = {
    # 设置脚本
    "scripts/setup_all.py": [
        ("    # Set up Gmail integration", "    # Gmail integration has been removed"),
        ("    if not args.skip_gmail:", "    # Gmail integration has been removed"),
        ("        logger.info(\"\\nStep 4: Setting up Gmail integration\")", "    logger.info(\"\\nStep 4: Gmail integration has been removed\")"),
        ("        if not run_script(\"setup_gmail.py\"):", "    # Gmail setup script has been removed"),
        ("            logger.error(\"Gmail setup failed, deployment continues but email integration may not be available\")", "    # Email integration is no longer available"),
        ("    else:", ""),
        ("        logger.info(\"Skipping Gmail setup\")", ""),
        ("    parser.add_argument(\"--skip-gmail\", action=\"store_true\", help=\"Skip Gmail setup\")", "    # Gmail argument removed")
    ],
    
    # Langraph设置脚本
    "scripts/setup_all_with_langraph.py": [
        ("    # Set up Gmail integration", "    # Gmail integration has been removed"),
        ("    if not args.skip_gmail:", "    # Gmail integration has been removed"),
        ("        logger.info(\"\\nStep 6: Setting up Gmail integration\")", "    logger.info(\"\\nStep 6: Gmail integration has been removed\")"),
        ("        if not run_script(\"setup_gmail.py\"):", "    # Gmail setup script has been removed"),
        ("            logger.error(\"Gmail setup failed, deployment continues but email integration may not be available\")", "    # Email integration is no longer available"),
        ("    else:", ""),
        ("        logger.info(\"Skipping Gmail setup\")", ""),
        ("    parser.add_argument(\"--skip-gmail\", action=\"store_true\", help=\"Skip Gmail setup\")", "    # Gmail argument removed")
    ],
    
    # 更新requirements.txt，移除Gmail相关依赖
    "requirements.txt": [
        ("# Gmail API", "# Gmail API dependencies removed"),
        ("google-api-python-client>=2.108.0", "# google-api-python-client removed"),
        ("google-auth-httplib2>=0.1.1", "# google-auth-httplib2 removed"),
        ("google-auth-oauthlib>=1.1.0", "# google-auth-oauthlib removed")
    ]
}

def remove_files():
    """删除Gmail相关文件"""
    for file_path in FILES_TO_REMOVE:
        full_path = os.path.join(ROOT_DIR, file_path)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                logger.info(f"已删除文件: {file_path}")
            except Exception as e:
                logger.error(f"删除文件 {file_path} 失败: {str(e)}")
        else:
            logger.warning(f"文件不存在: {file_path}")

def modify_files():
    """修改包含Gmail引用的文件"""
    for file_path, replacements in FILES_TO_MODIFY.items():
        full_path = os.path.join(ROOT_DIR, file_path)
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for old_text, new_text in replacements:
                    content = content.replace(old_text, new_text)
                
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f"已修改文件: {file_path}")
            except Exception as e:
                logger.error(f"修改文件 {file_path} 失败: {str(e)}")
        else:
            logger.warning(f"文件不存在: {file_path}")

def update_config():
    """更新配置文件，移除Gmail相关配置"""
    config_path = os.path.join(ROOT_DIR, "config.yaml")
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 移除Gmail相关配置
            if 'gmail' in config:
                del config['gmail']
                logger.info("已从配置文件中移除Gmail配置")
            
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            logger.info("已更新配置文件")
        except Exception as e:
            logger.error(f"更新配置文件失败: {str(e)}")
    else:
        logger.warning("配置文件不存在")

def remove_credentials():
    """删除Gmail凭证文件"""
    credentials_dir = os.path.join(ROOT_DIR, "data", "credentials")
    if os.path.exists(credentials_dir):
        try:
            # 只删除Gmail相关的凭证文件
            for file_name in ["secrets.json", "token.json"]:
                file_path = os.path.join(credentials_dir, file_name)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"已删除凭证文件: {file_name}")
        except Exception as e:
            logger.error(f"删除凭证文件失败: {str(e)}")
    else:
        logger.warning("凭证目录不存在")

def main():
    """主函数"""
    logger.info("开始移除电子邮件相关服务...")
    
    # 删除文件
    remove_files()
    
    # 修改文件
    modify_files()
    
    # 更新配置
    update_config()
    
    # 删除凭证
    remove_credentials()
    
    logger.info("电子邮件相关服务移除完成！")
    logger.info("注意：如果您的项目中有其他地方引用了Gmail服务，可能需要手动修改。")

if __name__ == "__main__":
    main()
