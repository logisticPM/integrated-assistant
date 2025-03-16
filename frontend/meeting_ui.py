#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
会议记录界面模块 - 提供会议录音上传、转录和结构化摘要功能
"""

import os
import json
import gradio as gr
import pandas as pd
from datetime import datetime
import markdown
import re

class MeetingInterface:
    """会议记录界面类"""
    
    def __init__(self, mcp_client, config):
        """
        初始化会议记录界面
        
        Args:
            mcp_client: MCP客户端实例
            config: 应用配置
        """
        self.mcp_client = mcp_client
        self.config = config
        self.audio_dir = config["meeting"]["audio_dir"]
        self.transcription_dir = config["meeting"]["transcription_dir"]
        self.current_meeting_id = None
    
    def render(self):
        """渲染会议记录界面"""
        with gr.Blocks() as interface:
            gr.Markdown("## 会议记录")
            
            with gr.Tabs() as tabs:
                with gr.TabItem("上传会议"):
                    self._create_upload_interface()
                
                with gr.TabItem("会议列表"):
                    self._create_meeting_list_interface()
                
                with gr.TabItem("会议详情"):
                    self._create_meeting_detail_interface()
            
            return interface
    
    def _create_upload_interface(self):
        """创建上传会议界面"""
        with gr.Group():
            gr.Markdown("### 上传会议录音")
            
            with gr.Row():
                with gr.Column(scale=2):
                    meeting_title = gr.Textbox(label="会议标题", placeholder="请输入会议标题")
                    meeting_date = gr.Textbox(
                        label="会议日期", 
                        value=datetime.now().strftime("%Y-%m-%d"),
                        placeholder="YYYY-MM-DD"
                    )
                    meeting_participants = gr.Textbox(
                        label="参会人员", 
                        placeholder="请输入参会人员，用逗号分隔"
                    )
                    project_id = gr.Dropdown(
                        label="项目",
                        choices=["default"],
                        value="default"
                    )
                    tags = gr.Textbox(
                        label="标签",
                        placeholder="输入标签，用逗号分隔"
                    )
                
                with gr.Column(scale=3):
                    audio_file = gr.Audio(
                        label="会议录音", 
                        type="filepath",
                        format="mp3"
                    )
                    
                    with gr.Row():
                        transcribe_btn = gr.Button("上传并转录", variant="primary")
                        clear_btn = gr.Button("清除")
            
            upload_status = gr.Textbox(label="上传状态", interactive=False)
            
            # 获取项目列表
            def load_projects():
                try:
                    projects = self.mcp_client.call("chatbot.list_projects")
                    project_choices = ["default"]
                    
                    if projects and isinstance(projects, list):
                        for project in projects:
                            project_id = project.get("id")
                            project_name = project.get("name")
                            if project_id and project_name:
                                project_choices.append(f"{project_name} ({project_id})")
                    
                    return gr.Dropdown.update(choices=project_choices)
                except Exception as e:
                    return gr.Dropdown.update(choices=["default"])
            
            # 上传并转录功能
            def upload_and_transcribe(title, date, participants, project_selection, tags_input, audio_path):
                if not title or not audio_path:
                    return "请提供会议标题和录音文件"
                
                try:
                    # 解析项目ID
                    if project_selection and project_selection != "default":
                        match = re.search(r"\(([^)]+)\)$", project_selection)
                        project_id = match.group(1) if match else "default"
                    else:
                        project_id = "default"
                    
                    # 解析标签
                    tags_list = [tag.strip() for tag in tags_input.split(",")] if tags_input else []
                    
                    # 解析参会人员
                    participants_list = [p.strip() for p in participants.split(",")] if participants else []
                    
                    # 创建会议记录
                    meeting_id = self.mcp_client.call("meeting.create_meeting", {
                        "title": title,
                        "description": f"会议日期: {date}",
                        "participants": participants_list,
                        "project_id": project_id,
                        "tags": tags_list
                    })
                    
                    # 开始转录任务
                    self.mcp_client.call("transcription.start", {
                        "meeting_id": meeting_id,
                        "audio_path": audio_path
                    })
                    
                    return f"会议 '{title}' 已上传，转录任务已启动。会议ID: {meeting_id}"
                except Exception as e:
                    return f"上传失败: {str(e)}"
            
            # 清除表单
            def clear_form():
                return [
                    "", 
                    datetime.now().strftime("%Y-%m-%d"),
                    "",
                    "default",
                    "",
                    None,
                    ""
                ]
            
            # 绑定事件
            gr.on(gr.components.Blocks.load, fn=load_projects, outputs=project_id)
            
            transcribe_btn.click(
                fn=upload_and_transcribe,
                inputs=[meeting_title, meeting_date, meeting_participants, project_id, tags, audio_file],
                outputs=upload_status
            )
            
            clear_btn.click(
                fn=clear_form,
                outputs=[meeting_title, meeting_date, meeting_participants, project_id, tags, audio_file, upload_status]
            )
    
    def _create_meeting_list_interface(self):
        """创建会议列表界面"""
        with gr.Group():
            gr.Markdown("### 会议记录列表")
            
            with gr.Row():
                refresh_btn = gr.Button("刷新列表", variant="primary")
                search_input = gr.Textbox(label="搜索", placeholder="输入关键词搜索")
                project_filter = gr.Dropdown(
                    label="项目筛选",
                    choices=["全部", "default"],
                    value="全部"
                )
                tag_filter = gr.Dropdown(
                    label="标签筛选",
                    choices=["全部"],
                    value="全部"
                )
            
            meetings_table = gr.Dataframe(
                headers=["ID", "标题", "项目", "标签", "日期", "状态", "参与者"],
                datatype=["str", "str", "str", "str", "str", "str", "str"],
                label="会议列表",
                interactive=False
            )
            
            selected_meeting_id = gr.Textbox(visible=False)
            view_meeting_btn = gr.Button("查看选中会议")
            
            # 获取项目和标签列表
            def load_filters():
                try:
                    # 获取项目列表
                    projects = self.mcp_client.call("chatbot.list_projects")
                    project_choices = ["全部", "default"]
                    
                    if projects and isinstance(projects, list):
                        for project in projects:
                            project_id = project.get("id")
                            if project_id and project_id not in project_choices:
                                project_choices.append(project_id)
                    
                    # 获取标签列表
                    tags = self.mcp_client.call("meeting.list_tags")
                    tag_choices = ["全部"]
                    
                    if tags and isinstance(tags, list):
                        tag_choices.extend(tags)
                    
                    return gr.Dropdown.update(choices=project_choices), gr.Dropdown.update(choices=tag_choices)
                except Exception as e:
                    return gr.Dropdown.update(choices=["全部", "default"]), gr.Dropdown.update(choices=["全部"])
            
            # 获取会议列表
            def get_meetings(search_term="", project="全部", tag="全部"):
                try:
                    # 构建过滤参数
                    filter_params = {}
                    if project != "全部":
                        filter_params["project_id"] = project
                    if tag != "全部":
                        filter_params["tag"] = tag
                    if search_term:
                        filter_params["search_term"] = search_term
                    
                    meetings = self.mcp_client.call("meeting.list_meetings", filter_params)
                    
                    # 格式化会议列表数据
                    formatted_meetings = []
                    for meeting in meetings:
                        # 格式化标签
                        tags_str = ", ".join(meeting.get("tags", []))
                        # 格式化参与者
                        participants_str = ", ".join(meeting.get("participants", []))
                        
                        formatted_meetings.append([
                            meeting["id"],
                            meeting["title"],
                            meeting.get("project_id", "default"),
                            tags_str,
                            meeting.get("created_at", ""),
                            meeting.get("transcription_status", "未知"),
                            participants_str
                        ])
                    
                    return formatted_meetings
                except Exception as e:
                    return []
            
            # 选择会议行
            def select_meeting(evt: gr.SelectData):
                return evt.value[0]  # 返回选中行的ID列
            
            # 绑定事件
            gr.on(gr.components.Blocks.load, fn=load_filters, outputs=[project_filter, tag_filter])
            
            refresh_btn.click(
                fn=get_meetings,
                inputs=[search_input, project_filter, tag_filter],
                outputs=meetings_table
            )
            
            search_input.change(
                fn=get_meetings,
                inputs=[search_input, project_filter, tag_filter],
                outputs=meetings_table
            )
            
            project_filter.change(
                fn=get_meetings,
                inputs=[search_input, project_filter, tag_filter],
                outputs=meetings_table
            )
            
            tag_filter.change(
                fn=get_meetings,
                inputs=[search_input, project_filter, tag_filter],
                outputs=meetings_table
            )
            
            meetings_table.select(
                fn=select_meeting,
                outputs=selected_meeting_id
            )
            
            # 返回选择的会议ID和切换到会议详情标签的函数
            return selected_meeting_id, view_meeting_btn
    
    def _create_meeting_detail_interface(self):
        """创建会议详情界面"""
        with gr.Group():
            gr.Markdown("### 会议详情")
            
            meeting_id_input = gr.Textbox(label="会议ID", placeholder="输入会议ID查看详情")
            load_btn = gr.Button("加载会议", variant="primary")
            
            with gr.Tabs() as detail_tabs:
                with gr.TabItem("基本信息"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            meeting_title = gr.Textbox(label="会议标题", interactive=False)
                            meeting_date = gr.Textbox(label="会议日期", interactive=False)
                            meeting_project = gr.Textbox(label="所属项目", interactive=False)
                            meeting_status = gr.Textbox(label="状态", interactive=False)
                        
                        with gr.Column(scale=1):
                            meeting_participants = gr.Textbox(label="参会人员", interactive=False)
                            meeting_tags = gr.Textbox(label="标签", interactive=False)
                            meeting_duration = gr.Textbox(label="时长", interactive=False)
                
                with gr.TabItem("转录文本"):
                    transcription_text = gr.Textbox(
                        label="转录文本",
                        lines=20,
                        interactive=False
                    )
                
                with gr.TabItem("会议摘要"):
                    with gr.Row():
                        generate_summary_btn = gr.Button("生成摘要", variant="primary")
                        export_summary_btn = gr.Button("导出摘要")
                    
                    with gr.Tabs() as summary_tabs:
                        with gr.TabItem("总体摘要"):
                            summary_text = gr.Markdown(label="会议摘要")
                        
                        with gr.TabItem("议程"):
                            agenda_text = gr.Markdown(label="会议议程")
                        
                        with gr.TabItem("决策事项"):
                            decisions_text = gr.Markdown(label="决策事项")
                        
                        with gr.TabItem("行动项"):
                            action_items = gr.Dataframe(
                                headers=["负责人", "任务", "截止日期", "状态"],
                                datatype=["str", "str", "str", "str"],
                                label="行动项列表"
                            )
                        
                        with gr.TabItem("关键点"):
                            key_points = gr.Dataframe(
                                headers=["时间点", "发言人", "内容"],
                                datatype=["str", "str", "str"],
                                label="关键点列表"
                            )
            
            # 加载会议详情
            def load_meeting_details(meeting_id):
                if not meeting_id:
                    return ["请输入有效的会议ID"] * 7, "", "", "", "", [], []
                
                try:
                    # 保存当前会议ID
                    self.current_meeting_id = meeting_id
                    
                    # 获取会议信息
                    meeting_info = self.mcp_client.call("meeting.get_meeting", {
                        "meeting_id": meeting_id
                    })
                    
                    if not meeting_info:
                        return ["会议不存在"] * 7, "", "", "", "", [], []
                    
                    # 获取转录文本
                    transcription = self.mcp_client.call("transcription.get", {
                        "meeting_id": meeting_id
                    }) or ""
                    
                    # 获取摘要信息
                    summary = meeting_info.get("summary", "")
                    agenda = meeting_info.get("agenda", "")
                    decisions = meeting_info.get("decisions", "")
                    
                    # 获取行动项
                    action_items_data = []
                    try:
                        if meeting_info.get("action_items"):
                            action_items_raw = json.loads(meeting_info.get("action_items"))
                            for item in action_items_raw:
                                action_items_data.append([
                                    item.get("assignee", ""),
                                    item.get("task", ""),
                                    item.get("due_date", ""),
                                    item.get("status", "待处理")
                                ])
                    except:
                        pass
                    
                    # 获取关键点
                    key_points_data = []
                    try:
                        if meeting_info.get("key_points"):
                            key_points_raw = json.loads(meeting_info.get("key_points"))
                            for point in key_points_raw:
                                key_points_data.append([
                                    point.get("timestamp", ""),
                                    point.get("speaker", ""),
                                    point.get("point", "")
                                ])
                    except:
                        pass
                    
                    # 格式化基本信息
                    basic_info = [
                        meeting_info.get("title", ""),
                        meeting_info.get("created_at", ""),
                        meeting_info.get("project_id", "default"),
                        meeting_info.get("transcription_status", ""),
                        ", ".join(meeting_info.get("participants", [])),
                        ", ".join(meeting_info.get("tags", [])),
                        meeting_info.get("duration", "")
                    ]
                    
                    return basic_info, transcription, summary, agenda, decisions, action_items_data, key_points_data
                except Exception as e:
                    return [f"加载失败: {str(e)}"] * 7, "", "", "", "", [], []
            
            # 生成摘要
            def generate_meeting_summary(meeting_id):
                if not meeting_id:
                    return "请输入有效的会议ID", "", "", [], []
                
                try:
                    # 调用生成结构化摘要API
                    result = self.mcp_client.call("meeting.generate_structured_summary", {
                        "meeting_id": meeting_id
                    })
                    
                    if not result or not isinstance(result, dict):
                        return "生成摘要失败", "", "", [], []
                    
                    # 提取结构化摘要内容
                    summary = result.get("summary", "")
                    agenda = result.get("agenda", "")
                    decisions = result.get("decisions", "")
                    
                    # 提取行动项
                    action_items_data = []
                    try:
                        action_items = result.get("action_items", [])
                        for item in action_items:
                            action_items_data.append([
                                item.get("assignee", ""),
                                item.get("task", ""),
                                item.get("due_date", ""),
                                item.get("status", "待处理")
                            ])
                    except:
                        pass
                    
                    # 提取关键点
                    key_points_data = []
                    try:
                        key_points = result.get("key_points", [])
                        for point in key_points:
                            key_points_data.append([
                                point.get("timestamp", ""),
                                point.get("speaker", ""),
                                point.get("point", "")
                            ])
                    except:
                        pass
                    
                    return summary, agenda, decisions, action_items_data, key_points_data
                except Exception as e:
                    return f"生成摘要失败: {str(e)}", "", "", [], []
            
            # 导出摘要
            def export_summary(meeting_id):
                if not meeting_id:
                    return "请先加载会议"
                
                try:
                    # 调用导出API
                    result = self.mcp_client.call("meeting.export_summary", {
                        "meeting_id": meeting_id,
                        "format": "markdown"
                    })
                    
                    if result and isinstance(result, dict) and result.get("file_path"):
                        return f"摘要已导出到: {result.get('file_path')}"
                    else:
                        return "导出失败: 未返回有效的文件路径"
                except Exception as e:
                    return f"导出失败: {str(e)}"
            
            # 绑定事件
            load_btn.click(
                fn=load_meeting_details,
                inputs=meeting_id_input,
                outputs=[
                    [meeting_title, meeting_date, meeting_project, meeting_status, 
                     meeting_participants, meeting_tags, meeting_duration],
                    transcription_text,
                    summary_text,
                    agenda_text,
                    decisions_text,
                    action_items,
                    key_points
                ]
            )
            
            generate_summary_btn.click(
                fn=generate_meeting_summary,
                inputs=meeting_id_input,
                outputs=[summary_text, agenda_text, decisions_text, action_items, key_points]
            )
            
            export_summary_btn.click(
                fn=export_summary,
                inputs=meeting_id_input,
                outputs=gr.Textbox(label="导出状态")
            )
            
            # 返回会议ID输入组件，用于从会议列表切换
            return meeting_id_input

def create_meeting_interface(mcp_client, config):
    """
    创建会议记录界面
    
    Args:
        mcp_client: MCP客户端实例
        config: 应用配置
    
    Returns:
        会议记录界面实例
    """
    interface = MeetingInterface(mcp_client, config)
    meeting_ui = interface.render()
    
    # 获取会议列表和详情界面的组件，用于连接两个界面
    selected_meeting_id, view_meeting_btn = interface._create_meeting_list_interface()
    meeting_id_input = interface._create_meeting_detail_interface()
    
    # 从会议列表切换到会议详情
    def view_selected_meeting(meeting_id):
        if not meeting_id:
            return meeting_id, None
        return meeting_id, 2  # 切换到索引为2的标签（会议详情）
    
    view_meeting_btn.click(
        fn=view_selected_meeting,
        inputs=selected_meeting_id,
        outputs=[meeting_id_input, gr.Tabs(elem_id=lambda: "tabs")]
    )
    
    return meeting_ui
