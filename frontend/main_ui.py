#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
主界面模块 - 提供统一的导航和控制面板
借鉴5ire的布局设计，采用侧边栏导航
"""

import gradio as gr
import os

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
    with gr.Blocks(theme=gr.themes.Soft(), css="""
        .container {
            max-width: 1200px;
            margin: auto;
        }
        .sidebar {
            border-right: 1px solid rgba(0, 0, 0, 0.1);
            padding-right: 20px;
        }
        .main-panel {
            padding-left: 20px;
        }
        .header {
            margin-bottom: 20px;
            border-bottom: 1px solid rgba(0, 0, 0, 0.1);
            padding-bottom: 10px;
        }
        .footer {
            margin-top: 20px;
            border-top: 1px solid rgba(0, 0, 0, 0.1);
            padding-top: 10px;
            text-align: center;
            font-size: 0.8em;
        }
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 5px;
        }
        .status-online {
            background-color: #4CAF50;
        }
        .status-offline {
            background-color: #F44336;
        }
        .nav-button {
            margin: 5px 0;
            border-radius: 5px;
            text-align: left;
            padding: 10px;
        }
        .nav-button-active {
            background-color: rgba(0, 0, 0, 0.05);
            border-left: 3px solid #2196F3;
        }
    """) as main_interface:
        
        # 创建状态变量来跟踪当前选中的页面
        current_page = gr.State("chatbot")
        
        with gr.Row(elem_classes="container"):
            # 侧边栏导航
            with gr.Column(scale=1, elem_classes="sidebar"):
                gr.Markdown(f"# {config['app']['title']}")
                
                with gr.Group():
                    chatbot_btn = gr.Button("💬 智能助手", elem_classes="nav-button nav-button-active")
                    meeting_btn = gr.Button("🎙️ 会议记录", elem_classes="nav-button")
                    email_btn = gr.Button("📧 邮件助手", elem_classes="nav-button")
                    knowledge_btn = gr.Button("📚 知识库", elem_classes="nav-button")
                    settings_btn = gr.Button("⚙️ 设置", elem_classes="nav-button")
                
                # 系统状态面板
                with gr.Group(elem_classes="status-panel"):
                    gr.Markdown("### 系统状态")
                    with gr.Row():
                        with gr.Column(scale=1):
                            llm_status = gr.Markdown(f"<span class='status-indicator status-online'></span> LLM: {config['llm']['model']}")
                        
                    with gr.Row():
                        with gr.Column(scale=1):
                            mcp_status = gr.Markdown("<span class='status-indicator status-online'></span> MCP: 运行中")
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            db_status = gr.Markdown("<span class='status-indicator status-online'></span> 数据库: 已连接")
            
            # 主内容区域
            with gr.Column(scale=4, elem_classes="main-panel"):
                with gr.Group(visible=True) as chatbot_panel:
                    create_chatbot_interface(config)
                
                with gr.Group(visible=False) as meeting_panel:
                    meeting_interface.render()
                
                with gr.Group(visible=False) as email_panel:
                    email_interface.render()
                
                with gr.Group(visible=False) as knowledge_panel:
                    knowledge_interface.render()
                
                with gr.Group(visible=False) as settings_panel:
                    create_settings_interface(config)
        
        # 页脚
        with gr.Row(elem_classes="footer"):
            gr.Markdown("© 2025 集成助手 | Powered by Codeium")
        
        # 导航按钮事件处理
        def switch_page(page_name):
            visibility_map = {
                "chatbot": [True, False, False, False, False],
                "meeting": [False, True, False, False, False],
                "email": [False, False, True, False, False],
                "knowledge": [False, False, False, True, False],
                "settings": [False, False, False, False, True]
            }
            return page_name, *visibility_map[page_name]
        
        chatbot_btn.click(
            fn=switch_page,
            inputs=[lambda: "chatbot"],
            outputs=[current_page, chatbot_panel, meeting_panel, email_panel, knowledge_panel, settings_panel]
        )
        
        meeting_btn.click(
            fn=switch_page,
            inputs=[lambda: "meeting"],
            outputs=[current_page, chatbot_panel, meeting_panel, email_panel, knowledge_panel, settings_panel]
        )
        
        email_btn.click(
            fn=switch_page,
            inputs=[lambda: "email"],
            outputs=[current_page, chatbot_panel, meeting_panel, email_panel, knowledge_panel, settings_panel]
        )
        
        knowledge_btn.click(
            fn=switch_page,
            inputs=[lambda: "knowledge"],
            outputs=[current_page, chatbot_panel, meeting_panel, email_panel, knowledge_panel, settings_panel]
        )
        
        settings_btn.click(
            fn=switch_page,
            inputs=[lambda: "settings"],
            outputs=[current_page, chatbot_panel, meeting_panel, email_panel, knowledge_panel, settings_panel]
        )
    
    return main_interface

def create_chatbot_interface(config):
    """
    创建聊天机器人界面
    
    Args:
        config: 应用配置
    
    Returns:
        聊天机器人界面组件
    """
    with gr.Blocks() as chatbot_interface:
        gr.Markdown("## 智能助手")
        
        # 创建MCP客户端实例
        from mcp.client import MCPClient
        mcp_client = MCPClient(config)
        
        # 获取项目列表
        try:
            projects = mcp_client.call("chatbot.list_projects", {})
            project_choices = [{"value": p["id"], "label": p["name"]} for p in projects]
            
            # 确保默认项目在列表中
            if not any(p["value"] == "default" for p in project_choices):
                project_choices.insert(0, {"value": "default", "label": "默认项目"})
        except Exception as e:
            # 如果获取失败，使用默认值
            project_choices = [{"value": "default", "label": "默认项目"}]
        
        with gr.Row():
            with gr.Column(scale=3):
                # 聊天区域
                chatbot = gr.Chatbot(height=500, elem_id="chatbot")
                
                with gr.Row():
                    with gr.Column(scale=8):
                        msg = gr.Textbox(
                            show_label=False,
                            placeholder="在这里输入您的问题...",
                            lines=2
                        )
                    
                    with gr.Column(scale=1):
                        send_btn = gr.Button("发送")
            
            with gr.Column(scale=1):
                # 知识库选择和设置
                gr.Markdown("### 知识库设置")
                
                # 项目选择
                project_selector = gr.Dropdown(
                    choices=project_choices,
                    value="default",
                    label="选择项目知识库"
                )
                
                # 项目管理按钮
                with gr.Row():
                    refresh_projects_btn = gr.Button("刷新项目")
                    create_project_btn = gr.Button("创建项目")
                
                # 创建项目对话框
                with gr.Accordion("创建新项目", open=False):
                    project_name = gr.Textbox(label="项目名称")
                    project_desc = gr.Textbox(label="项目描述", lines=3)
                    create_btn = gr.Button("创建")
                    create_status = gr.Markdown("")
                
                # 知识库过滤
                kb_category = gr.Dropdown(
                    choices=["全部", "会议记录", "技术文档", "产品规格", "市场分析", "其他"],
                    value="全部",
                    label="知识库类别"
                )
                
                # 模型设置
                temperature = gr.Slider(
                    minimum=0.1,
                    maximum=1.0,
                    value=0.7,
                    step=0.1,
                    label="Temperature"
                )
                
                # 上下文控制
                context_length = gr.Slider(
                    minimum=1,
                    maximum=10,
                    value=5,
                    step=1,
                    label="上下文长度"
                )
                
                # 清除对话按钮
                clear_btn = gr.Button("清除对话")
        
        # 聊天功能实现
        def chat_with_bot(message, history, project_id, category, temp, context_len):
            if not message:
                return history
            
            try:
                # 调用聊天机器人服务
                response = mcp_client.call("chatbot.chat", {
                    "message": message,
                    "history": history,
                    "project_id": project_id,
                    "category": category if category != "全部" else None,
                    "temperature": temp,
                    "context_length": context_len
                })
                
                history.append((message, response))
                return history
            except Exception as e:
                history.append((message, f"错误: {str(e)}"))
                return history
        
        # 清除聊天历史
        def clear_chat_history():
            return []
        
        # 刷新项目列表
        def refresh_projects():
            try:
                projects = mcp_client.call("chatbot.list_projects", {})
                return [{"value": p["id"], "label": p["name"]} for p in projects]
            except Exception as e:
                return [{"value": "default", "label": "默认项目"}]
        
        # 创建新项目
        def create_new_project(name, description):
            if not name:
                return "请输入项目名称", gr.update()
            
            try:
                project_id = mcp_client.call("chatbot.create_project", {
                    "name": name,
                    "description": description
                })
                
                # 刷新项目列表
                projects = refresh_projects()
                
                return f"项目 '{name}' 创建成功", gr.update(choices=projects, value=project_id)
            except Exception as e:
                return f"创建项目失败: {str(e)}", gr.update()
        
        # 绑定事件
        send_btn.click(
            fn=chat_with_bot,
            inputs=[msg, chatbot, project_selector, kb_category, temperature, context_length],
            outputs=chatbot
        ).then(
            fn=lambda: "",
            outputs=msg
        )
        
        msg.submit(
            fn=chat_with_bot,
            inputs=[msg, chatbot, project_selector, kb_category, temperature, context_length],
            outputs=chatbot
        ).then(
            fn=lambda: "",
            outputs=msg
        )
        
        clear_btn.click(
            fn=clear_chat_history,
            outputs=chatbot
        )
        
        refresh_projects_btn.click(
            fn=refresh_projects,
            outputs=project_selector
        )
        
        create_btn.click(
            fn=create_new_project,
            inputs=[project_name, project_desc],
            outputs=[create_status, project_selector]
        )

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
                    
                    gr.Markdown("### Gmail 设置")
                    # Gmail 设置
                    gmail_enabled = gr.Checkbox(
                        value=config["email"]["providers"][0]["enabled"],
                        label="启用 Gmail"
                    )
                    gmail_creds = gr.Textbox(
                        value=config["email"]["providers"][0]["credentials_file"],
                        label="Gmail 凭证文件路径"
                    )
                    
                    # 添加Gmail认证按钮
                    gmail_auth_btn = gr.Button("设置Gmail认证")
                    gmail_auth_status = gr.Textbox(label="Gmail认证状态", interactive=False)
                    
                    # Gmail认证按钮事件处理
                    def start_gmail_auth():
                        try:
                            import subprocess
                            result = subprocess.run(
                                ["python", "scripts/setup_gmail.py"], 
                                capture_output=True, 
                                text=True
                            )
                            if result.returncode == 0:
                                return "Gmail认证流程已启动，请在浏览器中完成授权"
                            else:
                                return f"Gmail认证启动失败: {result.stderr}"
                        except Exception as e:
                            return f"Gmail认证启动错误: {str(e)}"
                    
                    gmail_auth_btn.click(fn=start_gmail_auth, outputs=gmail_auth_status)
            
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
