#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Integrated Assistant - 主应用入口
结合会议记录、邮件AI助手和本地知识库的统一应用
"""

import os
import sys
import yaml
import gradio as gr
from pathlib import Path

# 添加项目根目录到系统路径
ROOT_DIR = Path(__file__).parent.absolute()
sys.path.append(str(ROOT_DIR))

# 导入前端UI模块
from frontend.main_ui import create_main_interface
from frontend.meeting_ui import create_meeting_interface
from frontend.email_ui import create_email_interface
from frontend.knowledge_ui import create_knowledge_interface

# 导入MCP服务
from mcp.client import MCPClient
from mcp.server import start_mcp_server

# 导入数据库管理
from db.db_manager import DatabaseManager
from db.vector_db import VectorDatabaseManager

def load_config():
    """加载配置文件"""
    config_path = os.path.join(ROOT_DIR, "config.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    else:
        # 默认配置
        default_config = {
            "app": {
                "title": "集成助手",
                "theme": "default",
                "debug": False
            },
            "llm": {
                "model": "local",  # local, openai, etc.
                "model_path": "./models/llm",
                "embedding_model": "local",
                "embedding_model_path": "./models/embedding",
                "anything_llm": {
                    "enabled": False,
                    "api_url": "http://localhost:3000/api",
                    "api_key": ""
                }
            },
            "meeting": {
                "audio_dir": "./data/audio",
                "transcription_dir": "./data/transcriptions",
                "whisper": {
                    "model": "medium",
                    "language": "zh"
                }
            },
            "email": {
                "email_dir": "./data/emails",
                "sync_interval": 300,  # 秒
                "max_emails": 1000,
                "imap_server": "",
                "imap_port": 993,
                "smtp_server": "",
                "smtp_port": 587,
                "email_address": "",
                "email_password": "",
                "use_ssl": True
            },
            "knowledge": {
                "docs_dir": "./data/documents",
                "chunk_size": 1000,
                "chunk_overlap": 200
            },
            "db": {
                "sqlite_path": "./data/app.db",
                "vector_db_path": "./data/vector_db"
            },
            "mcp": {
                "server_host": "localhost",
                "server_port": 5000,
                "client_url": "http://localhost:5000",
                "max_workers": 10
            }
        }
        # 保存默认配置
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
        return default_config

def init_directories(config):
    """初始化必要的目录结构"""
    dirs = [
        os.path.join(ROOT_DIR, "data"),
        os.path.join(ROOT_DIR, "data/audio"),
        os.path.join(ROOT_DIR, "data/transcriptions"),
        os.path.join(ROOT_DIR, "data/documents"),
        os.path.join(ROOT_DIR, "data/emails"),
        os.path.join(ROOT_DIR, "data/emails/attachments"),
        os.path.join(ROOT_DIR, "data/vector_db"),
        os.path.join(ROOT_DIR, "models"),
        os.path.join(ROOT_DIR, "models/llm"),
        os.path.join(ROOT_DIR, "models/embedding"),
    ]
    
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)

def main():
    """主函数"""
    # 加载配置
    config = load_config()
    
    # 初始化目录
    init_directories(config)
    
    # 初始化数据库
    db_manager = DatabaseManager(config["db"]["sqlite_path"])
    db_manager.init_db()
    
    vector_db = VectorDatabaseManager(config["db"]["vector_db_path"])
    vector_db.init_db()
    
    # 启动MCP服务器
    server_thread = start_mcp_server(config)
    
    # 创建MCP客户端
    mcp_client = MCPClient(config["mcp"]["client_url"])
    
    # 创建Gradio界面
    with gr.Blocks(title=config["app"]["title"], theme=gr.themes.Soft()) as app:
        # 创建各模块界面
        meeting_interface = create_meeting_interface(mcp_client)
        email_interface = create_email_interface(mcp_client)
        knowledge_interface = create_knowledge_interface(mcp_client)
        
        # 创建主界面（整合所有模块）
        create_main_interface(
            app,
            meeting_interface,
            email_interface,
            knowledge_interface,
            config
        )
    
    # 启动Gradio应用
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        debug=config["app"]["debug"]
    )

if __name__ == "__main__":
    main()
