#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
邮件助手界面模块 - 提供邮件查看、分析和回复建议功能
"""

import gradio as gr
from datetime import datetime

class EmailInterface:
    """邮件助手界面类"""
    
    def __init__(self, mcp_client, config):
        """
        初始化邮件助手界面
        
        Args:
            mcp_client: MCP客户端实例
            config: 应用配置
        """
        self.mcp_client = mcp_client
        self.config = config
    
    def render(self):
        """渲染邮件助手界面"""
        with gr.Blocks() as interface:
            gr.Markdown("## 邮件AI助手")
            
            with gr.Tabs() as tabs:
                with gr.TabItem("收件箱"):
                    self._create_inbox_interface()
                
                with gr.TabItem("邮件详情"):
                    self._create_email_detail_interface()
                
                with gr.TabItem("邮件分析"):
                    self._create_email_analysis_interface()
                
                with gr.TabItem("邮件搜索"):
                    self._create_email_search_interface()
            
            return interface
    
    def _create_inbox_interface(self):
        """创建收件箱界面"""
        with gr.Group():
            gr.Markdown("### 收件箱")
            
            with gr.Row():
                refresh_btn = gr.Button("刷新邮件")
                sync_btn = gr.Button("同步邮件")
                filter_dropdown = gr.Dropdown(
                    choices=["全部", "未读", "重要", "已标记", "有附件"],
                    value="全部",
                    label="筛选"
                )
            
            emails_table = gr.Dataframe(
                headers=["ID", "发件人", "主题", "日期", "状态"],
                datatype=["str", "str", "str", "str", "str"],
                label="邮件列表"
            )
            
            sync_status = gr.Textbox(label="同步状态", interactive=False)
            
            # 获取邮件列表
            def get_emails(filter_type="全部"):
                try:
                    emails = self.mcp_client.call("email.list_emails", {
                        "filter_type": filter_type
                    })
                    
                    # 格式化邮件列表数据
                    formatted_emails = []
                    for email in emails:
                        formatted_emails.append([
                            email["id"],
                            email["sender"],
                            email["subject"],
                            email["date"],
                            email["status"]
                        ])
                    
                    return formatted_emails
                except Exception as e:
                    return []
            
            # 同步邮件
            def sync_emails():
                try:
                    result = self.mcp_client.call("email.sync", {})
                    return f"邮件同步完成，新增 {result['new_emails']} 封邮件"
                except Exception as e:
                    return f"邮件同步失败: {str(e)}"
            
            # 绑定事件
            refresh_btn.click(
                fn=get_emails,
                inputs=filter_dropdown,
                outputs=emails_table
            )
            
            filter_dropdown.change(
                fn=get_emails,
                inputs=filter_dropdown,
                outputs=emails_table
            )
            
            sync_btn.click(
                fn=sync_emails,
                outputs=sync_status
            )
    
    def _create_email_detail_interface(self):
        """创建邮件详情界面"""
        with gr.Group():
            gr.Markdown("### 邮件详情")
            
            email_id_input = gr.Textbox(label="邮件ID", placeholder="输入邮件ID查看详情")
            load_btn = gr.Button("加载邮件")
            
            with gr.Tabs() as detail_tabs:
                with gr.TabItem("基本信息"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            email_sender = gr.Textbox(label="发件人", interactive=False)
                            email_recipients = gr.Textbox(label="收件人", interactive=False)
                            email_date = gr.Textbox(label="日期", interactive=False)
                        
                        with gr.Column(scale=2):
                            email_subject = gr.Textbox(label="主题", interactive=False)
                            email_attachments = gr.Dataframe(
                                headers=["文件名", "大小", "类型"],
                                datatype=["str", "str", "str"],
                                label="附件"
                            )
                
                with gr.TabItem("邮件内容"):
                    email_content = gr.Textbox(
                        label="内容",
                        lines=20,
                        interactive=False
                    )
                
                with gr.TabItem("回复建议"):
                    reply_type = gr.Radio(
                        choices=["简短回复", "详细回复", "正式回复", "婉拒回复"],
                        label="回复类型",
                        value="简短回复"
                    )
                    generate_reply_btn = gr.Button("生成回复建议")
                    reply_content = gr.Textbox(
                        label="回复内容",
                        lines=10,
                        interactive=True
                    )
                    copy_btn = gr.Button("复制到剪贴板")
            
            # 加载邮件详情
            def load_email_details(email_id):
                if not email_id:
                    return "", "", "", "", "", [], ""
                
                try:
                    # 获取邮件详情
                    email_details = self.mcp_client.call("email.get_email", {
                        "email_id": email_id
                    })
                    
                    # 格式化附件数据
                    formatted_attachments = []
                    for attachment in email_details.get("attachments", []):
                        formatted_attachments.append([
                            attachment["filename"],
                            attachment["size"],
                            attachment["type"]
                        ])
                    
                    return (
                        email_details.get("sender", ""),
                        email_details.get("recipients", ""),
                        email_details.get("date", ""),
                        email_details.get("subject", ""),
                        formatted_attachments,
                        email_details.get("content", "")
                    )
                except Exception as e:
                    return "", "", "", "", [], f"加载失败: {str(e)}"
            
            # 生成回复建议
            def generate_reply_suggestion(email_id, reply_type):
                if not email_id:
                    return "请输入有效的邮件ID"
                
                try:
                    # 调用生成回复API
                    reply = self.mcp_client.call("email.generate_reply", {
                        "email_id": email_id,
                        "reply_type": reply_type
                    })
                    
                    return reply
                except Exception as e:
                    return f"生成回复建议失败: {str(e)}"
            
            # 绑定事件
            load_btn.click(
                fn=load_email_details,
                inputs=email_id_input,
                outputs=[
                    email_sender,
                    email_recipients,
                    email_date,
                    email_subject,
                    email_attachments,
                    email_content
                ]
            )
            
            generate_reply_btn.click(
                fn=generate_reply_suggestion,
                inputs=[email_id_input, reply_type],
                outputs=reply_content
            )
    
    def _create_email_analysis_interface(self):
        """创建邮件分析界面"""
        with gr.Group():
            gr.Markdown("### 邮件分析")
            
            with gr.Row():
                with gr.Column(scale=1):
                    analysis_period = gr.Dropdown(
                        choices=["今天", "本周", "本月", "全部"],
                        value="本周",
                        label="分析周期"
                    )
                    run_analysis_btn = gr.Button("运行分析")
                
                with gr.Column(scale=2):
                    email_count = gr.Number(label="邮件总数", interactive=False)
                    unread_count = gr.Number(label="未读邮件数", interactive=False)
                    important_count = gr.Number(label="重要邮件数", interactive=False)
            
            with gr.Tabs() as analysis_tabs:
                with gr.TabItem("邮件类别分布"):
                    category_chart = gr.Plot(label="邮件类别分布")
                
                with gr.TabItem("发件人分析"):
                    sender_chart = gr.Plot(label="发件人分析")
                
                with gr.TabItem("时间分布"):
                    time_chart = gr.Plot(label="时间分布")
                
                with gr.TabItem("关键主题"):
                    topics_table = gr.Dataframe(
                        headers=["主题", "邮件数", "重要性"],
                        datatype=["str", "number", "str"],
                        label="关键主题"
                    )
            
            # 运行邮件分析
            def run_email_analysis(period):
                try:
                    # 调用邮件分析API
                    analysis_result = self.mcp_client.call("email.analyze", {
                        "period": period
                    })
                    
                    # 提取分析结果
                    email_stats = analysis_result.get("stats", {})
                    category_plot = analysis_result.get("category_plot", None)
                    sender_plot = analysis_result.get("sender_plot", None)
                    time_plot = analysis_result.get("time_plot", None)
                    topics = analysis_result.get("topics", [])
                    
                    # 格式化主题数据
                    formatted_topics = []
                    for topic in topics:
                        formatted_topics.append([
                            topic["name"],
                            topic["count"],
                            topic["importance"]
                        ])
                    
                    return (
                        email_stats.get("total", 0),
                        email_stats.get("unread", 0),
                        email_stats.get("important", 0),
                        category_plot,
                        sender_plot,
                        time_plot,
                        formatted_topics
                    )
                except Exception as e:
                    return 0, 0, 0, None, None, None, []
            
            # 绑定事件
            run_analysis_btn.click(
                fn=run_email_analysis,
                inputs=analysis_period,
                outputs=[
                    email_count,
                    unread_count,
                    important_count,
                    category_chart,
                    sender_chart,
                    time_chart,
                    topics_table
                ]
            )
    
    def _create_email_search_interface(self):
        """创建邮件搜索界面"""
        with gr.Group():
            gr.Markdown("### 邮件搜索")
            
            with gr.Row():
                search_input = gr.Textbox(
                    label="搜索关键词",
                    placeholder="输入关键词或自然语言查询"
                )
                search_type = gr.Radio(
                    choices=["关键词搜索", "语义搜索"],
                    label="搜索类型",
                    value="语义搜索"
                )
                search_btn = gr.Button("搜索")
            
            search_results = gr.Dataframe(
                headers=["ID", "发件人", "主题", "日期", "相关度"],
                datatype=["str", "str", "str", "str", "number"],
                label="搜索结果"
            )
            
            # 搜索邮件
            def search_emails(query, search_type):
                if not query:
                    return []
                
                try:
                    # 调用邮件搜索API
                    search_results = self.mcp_client.call("email.search", {
                        "query": query,
                        "search_type": search_type
                    })
                    
                    # 格式化搜索结果
                    formatted_results = []
                    for result in search_results:
                        formatted_results.append([
                            result["id"],
                            result["sender"],
                            result["subject"],
                            result["date"],
                            result["relevance"]
                        ])
                    
                    return formatted_results
                except Exception as e:
                    return []
            
            # 绑定事件
            search_btn.click(
                fn=search_emails,
                inputs=[search_input, search_type],
                outputs=search_results
            )

def create_email_interface(mcp_client, config):
    """
    创建邮件助手界面
    
    Args:
        mcp_client: MCP客户端实例
        config: 应用配置
    
    Returns:
        邮件助手界面实例
    """
    return EmailInterface(mcp_client, config)
