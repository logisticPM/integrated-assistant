#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
邮件助手界面模块 - 提供邮件查看、分析、回复建议和日历管理功能
"""

import gradio as gr
from datetime import datetime, timedelta
import pytz

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
                
                with gr.TabItem("日历"):
                    self._create_calendar_interface()
                
                with gr.TabItem("Gmail设置"):
                    self._create_gmail_settings_interface()
            
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
                    # 使用Gmail服务获取邮件列表
                    query = ""
                    if filter_type == "未读":
                        query = "is:unread"
                    elif filter_type == "重要":
                        query = "is:important"
                    elif filter_type == "已标记":
                        query = "is:starred"
                    elif filter_type == "有附件":
                        query = "has:attachment"
                    
                    emails = self.mcp_client.call("gmail.list_emails", {
                        "max_results": 50,
                        "query": query
                    })
                    
                    # 格式化邮件列表数据
                    formatted_emails = []
                    for email in emails:
                        formatted_emails.append([
                            email["id"],
                            email["sender"],
                            email["subject"],
                            email["date"],
                            "未读" if email.get("unread", False) else "已读"
                        ])
                    
                    return formatted_emails
                except Exception as e:
                    return []
            
            # 同步邮件
            def sync_emails():
                try:
                    # 调用邮件处理脚本
                    result = self.mcp_client.call("system.run_script", {
                        "script_name": "email_processor.py",
                        "args": ["--auto-categorize"]
                    })
                    
                    return f"邮件同步完成: {result.get('message', '成功')}"
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
                    send_reply_btn = gr.Button("发送回复")
                    reply_status = gr.Textbox(label="回复状态", interactive=False)
            
            # 加载邮件详情
            def load_email_details(email_id):
                if not email_id:
                    return "", "", "", "", [], ""
                
                try:
                    # 使用Gmail服务获取邮件详情
                    email_details = self.mcp_client.call("gmail.get_email", {
                        "message_id": email_id,
                        "include_body": True
                    })
                    
                    if not email_details:
                        return "", "", "", "", [], "未找到邮件"
                    
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
                        email_details.get("body", "")
                    )
                except Exception as e:
                    return "", "", "", "", [], f"加载失败: {str(e)}"
            
            # 生成回复建议
            def generate_reply_suggestion(email_id, reply_type):
                if not email_id:
                    return "请输入有效的邮件ID"
                
                try:
                    # 获取邮件详情
                    email_details = self.mcp_client.call("gmail.get_email", {
                        "message_id": email_id,
                        "include_body": True
                    })
                    
                    if not email_details:
                        return "未找到邮件"
                    
                    # 调用LLM生成回复
                    reply = self.mcp_client.call("llm.generate", {
                        "prompt": f"""
                        你是一位专业的邮件助手。请根据以下邮件内容，生成一个{reply_type}。
                        
                        发件人: {email_details.get('sender', '')}
                        主题: {email_details.get('subject', '')}
                        内容: {email_details.get('body', '')}
                        
                        请直接给出回复内容，不要包含解释。
                        """,
                        "max_tokens": 500
                    })
                    
                    return reply.get("text", "生成回复失败")
                except Exception as e:
                    return f"生成回复建议失败: {str(e)}"
            
            # 发送回复
            def send_reply(email_id, subject, reply_content):
                if not email_id or not reply_content:
                    return "请输入有效的邮件ID和回复内容"
                
                try:
                    # 获取邮件详情
                    email_details = self.mcp_client.call("gmail.get_email", {
                        "message_id": email_id
                    })
                    
                    if not email_details:
                        return "未找到邮件"
                    
                    # 发送回复
                    result = self.mcp_client.call("gmail.send_email", {
                        "to": email_details.get("sender", ""),
                        "subject": f"Re: {subject}",
                        "body": reply_content,
                        "reply_to": email_id
                    })
                    
                    if result.get("success", False):
                        return "回复已发送"
                    else:
                        return f"发送回复失败: {result.get('message', '')}"
                except Exception as e:
                    return f"发送回复失败: {str(e)}"
            
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
            
            send_reply_btn.click(
                fn=send_reply,
                inputs=[email_id_input, email_subject, reply_content],
                outputs=reply_status
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
                    # 构建查询
                    query = ""
                    if period == "今天":
                        today = datetime.now().strftime("%Y/%m/%d")
                        query = f"after:{today}"
                    elif period == "本周":
                        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y/%m/%d")
                        query = f"after:{week_ago}"
                    elif period == "本月":
                        month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y/%m/%d")
                        query = f"after:{month_ago}"
                    
                    # 获取邮件列表
                    emails = self.mcp_client.call("gmail.list_emails", {
                        "max_results": 100,
                        "query": query,
                        "include_body": False
                    })
                    
                    if not emails:
                        return 0, 0, 0, None, None, None, []
                    
                    # 基本统计
                    total = len(emails)
                    unread = sum(1 for email in emails if email.get("unread", False))
                    important = sum(1 for email in emails if email.get("important", False))
                    
                    # 调用分析服务
                    analysis_result = self.mcp_client.call("email.analyze_batch", {
                        "emails": emails
                    })
                    
                    # 提取分析结果
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
                        total,
                        unread,
                        important,
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
                    if search_type == "关键词搜索":
                        # 直接使用Gmail搜索
                        emails = self.mcp_client.call("gmail.list_emails", {
                            "max_results": 50,
                            "query": query
                        })
                        
                        # 格式化搜索结果
                        formatted_results = []
                        for email in emails:
                            formatted_results.append([
                                email["id"],
                                email["sender"],
                                email["subject"],
                                email["date"],
                                1.0  # 关键词搜索不提供相关度
                            ])
                    else:
                        # 语义搜索
                        search_results = self.mcp_client.call("email.semantic_search", {
                            "query": query,
                            "max_results": 50
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
    
    def _create_calendar_interface(self):
        """创建日历界面"""
        with gr.Group():
            gr.Markdown("### 日历管理")
            
            with gr.Tabs() as calendar_tabs:
                with gr.TabItem("查看日程"):
                    with gr.Row():
                        date_picker = gr.Textbox(
                            label="日期范围",
                            placeholder="例如: 2023-06-01 或 2023-06-01,2023-06-07",
                            value=datetime.now().strftime("%Y-%m-%d")
                        )
                        load_events_btn = gr.Button("加载日程")
                    
                    events_table = gr.Dataframe(
                        headers=["ID", "标题", "开始时间", "结束时间", "地点", "参与者"],
                        datatype=["str", "str", "str", "str", "str", "str"],
                        label="日程列表"
                    )
                
                with gr.TabItem("创建日程"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            event_title = gr.Textbox(label="标题", placeholder="会议标题")
                            event_location = gr.Textbox(label="地点", placeholder="会议地点")
                            event_participants = gr.Textbox(
                                label="参与者",
                                placeholder="用逗号分隔的邮箱地址"
                            )
                        
                        with gr.Column(scale=1):
                            event_start = gr.Textbox(
                                label="开始时间",
                                placeholder="格式: YYYY-MM-DD HH:MM",
                                value=(datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
                            )
                            event_end = gr.Textbox(
                                label="结束时间",
                                placeholder="格式: YYYY-MM-DD HH:MM",
                                value=(datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
                            )
                            timezone = gr.Dropdown(
                                choices=["Asia/Shanghai", "America/New_York", "Europe/London", "UTC"],
                                value="Asia/Shanghai",
                                label="时区"
                            )
                    
                    event_description = gr.Textbox(
                        label="描述",
                        placeholder="会议描述",
                        lines=5
                    )
                    
                    create_event_btn = gr.Button("创建日程")
                    event_status = gr.Textbox(label="创建状态", interactive=False)
            
            # 加载日程
            def load_calendar_events(date_range):
                try:
                    # 解析日期范围
                    dates = [d.strip() for d in date_range.split(",")]
                    
                    # 获取日程
                    events = self.mcp_client.call("gmail.get_events_for_days", {
                        "date_strs": dates
                    })
                    
                    # 格式化日程数据
                    formatted_events = []
                    for event in events:
                        # 格式化参与者
                        participants = ", ".join([p.get("email", "") for p in event.get("attendees", [])])
                        
                        formatted_events.append([
                            event.get("id", ""),
                            event.get("summary", ""),
                            event.get("start", {}).get("dateTime", ""),
                            event.get("end", {}).get("dateTime", ""),
                            event.get("location", ""),
                            participants
                        ])
                    
                    return formatted_events
                except Exception as e:
                    return []
            
            # 创建日程
            def create_calendar_event(title, start, end, description, location, participants, timezone):
                if not title or not start or not end:
                    return "请填写必要的日程信息"
                
                try:
                    # 解析参与者
                    emails = [email.strip() for email in participants.split(",") if email.strip()]
                    
                    # 创建日程
                    result = self.mcp_client.call("gmail.send_calendar_invite", {
                        "emails": emails,
                        "title": title,
                        "start_time": start,
                        "end_time": end,
                        "description": description,
                        "location": location,
                        "timezone": timezone
                    })
                    
                    if result.get("success", False):
                        return "日程创建成功"
                    else:
                        return f"日程创建失败: {result.get('message', '')}"
                except Exception as e:
                    return f"日程创建失败: {str(e)}"
            
            # 绑定事件
            load_events_btn.click(
                fn=load_calendar_events,
                inputs=date_picker,
                outputs=events_table
            )
            
            create_event_btn.click(
                fn=create_calendar_event,
                inputs=[
                    event_title,
                    event_start,
                    event_end,
                    event_description,
                    event_location,
                    event_participants,
                    timezone
                ],
                outputs=event_status
            )
    
    def _create_gmail_settings_interface(self):
        """创建Gmail设置界面"""
        with gr.Group():
            gr.Markdown("### Gmail设置")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("#### 认证状态")
                    check_auth_btn = gr.Button("检查认证状态")
                    auth_status = gr.Textbox(label="认证状态", interactive=False)
                    
                    gr.Markdown("#### 自动处理设置")
                    auto_check_interval = gr.Slider(
                        minimum=5,
                        maximum=60,
                        value=10,
                        step=5,
                        label="自动检查间隔（分钟）"
                    )
                    auto_categorize = gr.Checkbox(label="自动分类邮件", value=True)
                    auto_reply = gr.Checkbox(label="启用自动回复", value=False)
                    auto_mark_read = gr.Checkbox(label="自动标记为已读", value=False)
                
                with gr.Column(scale=1):
                    gr.Markdown("#### 认证操作")
                    client_secret_path = gr.Textbox(
                        label="客户端密钥文件路径",
                        placeholder="输入客户端密钥文件的完整路径"
                    )
                    setup_auth_btn = gr.Button("设置认证")
                    
                    gr.Markdown("#### 定时任务")
                    setup_cron_btn = gr.Button("设置定时任务")
                    cron_status = gr.Textbox(label="定时任务状态", interactive=False)
            
            # 检查认证状态
            def check_gmail_auth():
                try:
                    # 测试Gmail连接
                    result = self.mcp_client.call("gmail.test_connection")
                    
                    if result.get("success", False):
                        return f"认证状态: 已认证\n关联邮箱: {result.get('email', '未知')}"
                    else:
                        return f"认证状态: 未认证\n错误信息: {result.get('message', '')}"
                except Exception as e:
                    return f"检查认证状态失败: {str(e)}"
            
            # 设置认证
            def setup_gmail_auth(client_secret_path):
                if not client_secret_path:
                    return "请输入客户端密钥文件路径"
                
                try:
                    # 调用设置脚本
                    result = self.mcp_client.call("system.run_script", {
                        "script_name": "setup_gmail.py",
                        "args": [f"--client-secret={client_secret_path}"]
                    })
                    
                    return f"设置认证结果: {result.get('message', '成功')}"
                except Exception as e:
                    return f"设置认证失败: {str(e)}"
            
            # 设置定时任务
            def setup_cron_job(interval, auto_categorize, auto_reply, auto_mark_read):
                try:
                    # 构建参数
                    args = [f"--interval={interval}", f"--minutes-since={interval}"]
                    
                    if auto_categorize:
                        args.append("--auto-categorize")
                    
                    if auto_reply:
                        args.append("--auto-reply")
                    
                    if auto_mark_read:
                        args.append("--auto-mark-read")
                    
                    # 调用设置脚本
                    result = self.mcp_client.call("system.run_script", {
                        "script_name": "setup_cron.py",
                        "args": args
                    })
                    
                    return f"设置定时任务结果: {result.get('message', '成功')}"
                except Exception as e:
                    return f"设置定时任务失败: {str(e)}"
            
            # 绑定事件
            check_auth_btn.click(
                fn=check_gmail_auth,
                outputs=auth_status
            )
            
            setup_auth_btn.click(
                fn=setup_gmail_auth,
                inputs=client_secret_path,
                outputs=auth_status
            )
            
            setup_cron_btn.click(
                fn=setup_cron_job,
                inputs=[
                    auto_check_interval,
                    auto_categorize,
                    auto_reply,
                    auto_mark_read
                ],
                outputs=cron_status
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
