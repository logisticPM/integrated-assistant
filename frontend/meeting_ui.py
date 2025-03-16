#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
会议记录界面模块 - 提供会议录音上传、转录和摘要功能
"""

import os
import gradio as gr
from datetime import datetime

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
                
                with gr.Column(scale=3):
                    audio_file = gr.Audio(
                        label="会议录音", 
                        type="filepath",
                        format="mp3"
                    )
                    
                    with gr.Row():
                        transcribe_btn = gr.Button("上传并转录")
                        clear_btn = gr.Button("清除")
            
            upload_status = gr.Textbox(label="上传状态", interactive=False)
            
            # 上传并转录功能
            def upload_and_transcribe(title, date, participants, audio_path):
                if not title or not audio_path:
                    return "请提供会议标题和录音文件"
                
                try:
                    # 创建会议记录
                    meeting_id = self.mcp_client.call("meeting.create_meeting", {
                        "title": title,
                        "date": date,
                        "participants": participants,
                        "audio_path": audio_path
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
                    None,
                    ""
                ]
            
            # 绑定事件
            transcribe_btn.click(
                fn=upload_and_transcribe,
                inputs=[meeting_title, meeting_date, meeting_participants, audio_file],
                outputs=upload_status
            )
            
            clear_btn.click(
                fn=clear_form,
                outputs=[meeting_title, meeting_date, meeting_participants, audio_file, upload_status]
            )
    
    def _create_meeting_list_interface(self):
        """创建会议列表界面"""
        with gr.Group():
            gr.Markdown("### 会议记录列表")
            
            with gr.Row():
                refresh_btn = gr.Button("刷新列表")
                search_input = gr.Textbox(label="搜索", placeholder="输入关键词搜索")
            
            meetings_table = gr.Dataframe(
                headers=["ID", "标题", "日期", "状态", "时长"],
                datatype=["str", "str", "str", "str", "str"],
                label="会议列表"
            )
            
            # 获取会议列表
            def get_meetings(search_term=""):
                try:
                    meetings = self.mcp_client.call("meeting.list_meetings", {
                        "search_term": search_term
                    })
                    
                    # 格式化会议列表数据
                    formatted_meetings = []
                    for meeting in meetings:
                        formatted_meetings.append([
                            meeting["id"],
                            meeting["title"],
                            meeting["date"],
                            meeting["status"],
                            meeting["duration"]
                        ])
                    
                    return formatted_meetings
                except Exception as e:
                    return []
            
            # 绑定事件
            refresh_btn.click(fn=get_meetings, outputs=meetings_table)
            search_input.change(
                fn=get_meetings,
                inputs=search_input,
                outputs=meetings_table
            )
    
    def _create_meeting_detail_interface(self):
        """创建会议详情界面"""
        with gr.Group():
            gr.Markdown("### 会议详情")
            
            meeting_id_input = gr.Textbox(label="会议ID", placeholder="输入会议ID查看详情")
            load_btn = gr.Button("加载会议")
            
            with gr.Tabs() as detail_tabs:
                with gr.TabItem("基本信息"):
                    meeting_info = gr.JSON(label="会议信息")
                
                with gr.TabItem("转录文本"):
                    transcription_text = gr.Textbox(
                        label="转录文本",
                        lines=20,
                        interactive=False
                    )
                
                with gr.TabItem("会议摘要"):
                    summary_text = gr.Textbox(
                        label="会议摘要",
                        lines=10,
                        interactive=False
                    )
                    generate_summary_btn = gr.Button("生成摘要")
                
                with gr.TabItem("关键点"):
                    key_points = gr.Dataframe(
                        headers=["时间点", "内容"],
                        datatype=["str", "str"],
                        label="关键点列表"
                    )
            
            # 加载会议详情
            def load_meeting_details(meeting_id):
                if not meeting_id:
                    return {}, "请输入有效的会议ID", "", []
                
                try:
                    # 获取会议信息
                    meeting_info = self.mcp_client.call("meeting.get_meeting", {
                        "meeting_id": meeting_id
                    })
                    
                    # 获取转录文本
                    transcription = self.mcp_client.call("transcription.get", {
                        "meeting_id": meeting_id
                    })
                    
                    # 获取摘要
                    summary = self.mcp_client.call("meeting.get_summary", {
                        "meeting_id": meeting_id
                    })
                    
                    # 获取关键点
                    key_points_data = self.mcp_client.call("meeting.get_key_points", {
                        "meeting_id": meeting_id
                    })
                    
                    # 格式化关键点数据
                    formatted_key_points = []
                    for point in key_points_data:
                        formatted_key_points.append([
                            point["timestamp"],
                            point["content"]
                        ])
                    
                    return meeting_info, transcription, summary, formatted_key_points
                except Exception as e:
                    return {}, f"加载失败: {str(e)}", "", []
            
            # 生成摘要
            def generate_meeting_summary(meeting_id):
                if not meeting_id:
                    return "请输入有效的会议ID"
                
                try:
                    # 调用生成摘要API
                    summary = self.mcp_client.call("meeting.generate_summary", {
                        "meeting_id": meeting_id
                    })
                    
                    return summary
                except Exception as e:
                    return f"生成摘要失败: {str(e)}"
            
            # 绑定事件
            load_btn.click(
                fn=load_meeting_details,
                inputs=meeting_id_input,
                outputs=[meeting_info, transcription_text, summary_text, key_points]
            )
            
            generate_summary_btn.click(
                fn=generate_meeting_summary,
                inputs=meeting_id_input,
                outputs=summary_text
            )

def create_meeting_interface(mcp_client, config):
    """
    创建会议记录界面
    
    Args:
        mcp_client: MCP客户端实例
        config: 应用配置
    
    Returns:
        会议记录界面实例
    """
    return MeetingInterface(mcp_client, config)
