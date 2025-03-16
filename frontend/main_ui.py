#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
主界面模块 - 提供统一的导航和控制面板
"""

import gradio as gr

def create_main_interface(meeting_interface, email_interface, knowledge_interface, config):
    """
    创建主界面
    
    Args:
        meeting_interface: 会议记录界面
        email_interface: 邮件助手界面
        knowledge_interface: 知识库界面
        config: 应用配置
    
    Returns:
        主界面组件
    """
    with gr.Blocks() as main_interface:
        gr.Markdown(f"# {config['app']['title']}")
        
        with gr.Tabs() as tabs:
            with gr.TabItem("会议记录"):
                meeting_interface.render()
            
            with gr.TabItem("邮件助手"):
                email_interface.render()
            
            with gr.TabItem("知识库"):
                knowledge_interface.render()
            
            with gr.TabItem("设置"):
                create_settings_interface(config)
        
        gr.Markdown("### 系统状态")
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("LLM 模型")
                llm_status = gr.Textbox(value=f"{config['llm']['model']}", label="模型状态", interactive=False)
            
            with gr.Column(scale=1):
                gr.Markdown("MCP 服务")
                mcp_status = gr.Textbox(value="运行中", label="服务状态", interactive=False)
            
            with gr.Column(scale=1):
                gr.Markdown("数据库")
                db_status = gr.Textbox(value="已连接", label="连接状态", interactive=False)
    
    return main_interface

def create_settings_interface(config):
    """
    创建设置界面
    
    Args:
        config: 应用配置
    
    Returns:
        设置界面组件
    """
    with gr.Blocks() as settings_interface:
        gr.Markdown("## 应用设置")
        
        with gr.Tabs() as settings_tabs:
            with gr.TabItem("LLM 设置"):
                with gr.Group():
                    gr.Markdown("### LLM 模型设置")
                    llm_model = gr.Dropdown(
                        choices=["local", "openai", "anthropic", "anything_llm"],
                        value=config["llm"]["model"],
                        label="LLM 模型"
                    )
                    llm_path = gr.Textbox(
                        value=config["llm"]["model_path"],
                        label="本地模型路径",
                        visible=config["llm"]["model"] == "local"
                    )
                    
                    gr.Markdown("### Embedding 模型设置")
                    embedding_model = gr.Dropdown(
                        choices=["local", "openai", "anything_llm"],
                        value=config["llm"]["embedding_model"],
                        label="Embedding 模型"
                    )
                    embedding_path = gr.Textbox(
                        value=config["llm"]["embedding_model_path"],
                        label="本地Embedding模型路径",
                        visible=config["llm"]["embedding_model"] == "local"
                    )
                    
                    # AnythingLLM 集成设置
                    gr.Markdown("### AnythingLLM 集成")
                    anything_llm_enabled = gr.Checkbox(
                        value=config["llm"]["anything_llm"]["enabled"],
                        label="启用 AnythingLLM 集成"
                    )
                    anything_llm_url = gr.Textbox(
                        value=config["llm"]["anything_llm"]["api_url"],
                        label="AnythingLLM API URL"
                    )
                    anything_llm_key = gr.Textbox(
                        value=config["llm"]["anything_llm"]["api_key"],
                        label="AnythingLLM API Key",
                        type="password"
                    )
            
            with gr.TabItem("会议记录设置"):
                with gr.Group():
                    gr.Markdown("### 会议记录设置")
                    audio_dir = gr.Textbox(
                        value=config["meeting"]["audio_dir"],
                        label="音频文件目录"
                    )
                    transcription_dir = gr.Textbox(
                        value=config["meeting"]["transcription_dir"],
                        label="转录文件目录"
                    )
                    
                    gr.Markdown("### Whisper 设置")
                    whisper_model = gr.Dropdown(
                        choices=["tiny", "base", "small", "medium", "large"],
                        value=config["meeting"]["whisper"]["model"],
                        label="Whisper 模型"
                    )
                    whisper_language = gr.Textbox(
                        value=config["meeting"]["whisper"]["language"],
                        label="默认语言 (使用'auto'自动检测)"
                    )
            
            with gr.TabItem("邮件设置"):
                with gr.Group():
                    gr.Markdown("### 邮件同步设置")
                    sync_interval = gr.Number(
                        value=config["email"]["sync_interval"],
                        label="同步间隔 (秒)"
                    )
                    max_emails = gr.Number(
                        value=config["email"]["max_emails"],
                        label="最大邮件数量"
                    )
                    
                    gr.Markdown("### 邮件提供商设置")
                    # Gmail 设置
                    gmail_enabled = gr.Checkbox(
                        value=config["email"]["providers"][0]["enabled"],
                        label="启用 Gmail"
                    )
                    gmail_creds = gr.Textbox(
                        value=config["email"]["providers"][0]["credentials_file"],
                        label="Gmail 凭证文件路径"
                    )
                    
                    # Outlook 设置
                    outlook_enabled = gr.Checkbox(
                        value=config["email"]["providers"][1]["enabled"],
                        label="启用 Outlook"
                    )
                    outlook_creds = gr.Textbox(
                        value=config["email"]["providers"][1]["credentials_file"],
                        label="Outlook 凭证文件路径"
                    )
            
            with gr.TabItem("知识库设置"):
                with gr.Group():
                    gr.Markdown("### 知识库设置")
                    docs_dir = gr.Textbox(
                        value=config["knowledge"]["docs_dir"],
                        label="文档目录"
                    )
                    chunk_size = gr.Number(
                        value=config["knowledge"]["chunk_size"],
                        label="文档分块大小"
                    )
                    chunk_overlap = gr.Number(
                        value=config["knowledge"]["chunk_overlap"],
                        label="分块重叠大小"
                    )
            
            with gr.TabItem("系统设置"):
                with gr.Group():
                    gr.Markdown("### 数据库设置")
                    sqlite_path = gr.Textbox(
                        value=config["db"]["sqlite_path"],
                        label="SQLite 数据库路径"
                    )
                    vector_db_path = gr.Textbox(
                        value=config["db"]["vector_db_path"],
                        label="向量数据库路径"
                    )
                    
                    gr.Markdown("### MCP 服务设置")
                    mcp_host = gr.Textbox(
                        value=config["mcp"]["server_host"],
                        label="MCP 服务器地址"
                    )
                    mcp_port = gr.Number(
                        value=config["mcp"]["server_port"],
                        label="MCP 服务器端口"
                    )
                    mcp_workers = gr.Number(
                        value=config["mcp"]["max_workers"],
                        label="最大工作线程数"
                    )
        
        # 保存按钮
        save_btn = gr.Button("保存设置")
        save_status = gr.Textbox(label="保存状态", interactive=False)
        
        # 保存设置的事件处理
        def save_settings():
            # 实际项目中这里应该保存设置到配置文件
            return "设置已保存"
        
        save_btn.click(fn=save_settings, outputs=save_status)
    
    return settings_interface
