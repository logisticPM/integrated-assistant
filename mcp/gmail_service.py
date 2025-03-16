#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Gmail服务模块 - 提供Gmail API集成功能
从executive-ai-assistant项目移植和增强
"""

import os
import json
import logging
import base64
import uuid
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Iterable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import email.utils
from dateutil import parser
import pytz

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("gmail_service")

# Gmail API权限范围
_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
]

class GmailService:
    """Gmail服务类，提供Gmail API集成功能"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化Gmail服务
        
        Args:
            config: 服务配置
        """
        self.config = config
        self.credentials_dir = config.get("gmail", {}).get("credentials_dir", "data/credentials")
        
        # 确保凭证目录存在
        os.makedirs(self.credentials_dir, exist_ok=True)
        
        # 凭证文件路径
        self.secrets_path = os.path.join(self.credentials_dir, "secrets.json")
        self.token_path = os.path.join(self.credentials_dir, "token.json")
        
        # 端口配置
        self.auth_port = config.get("gmail", {}).get("auth_port", 54191)
    
    def get_credentials(self, gmail_token: str = None, gmail_secret: str = None) -> Credentials:
        """
        获取Gmail API凭证
        
        Args:
            gmail_token: Gmail令牌内容
            gmail_secret: Gmail密钥内容
        
        Returns:
            凭证对象
        """
        creds = None
        
        # 如果提供了令牌或密钥，则保存到文件
        if gmail_token:
            with open(self.token_path, "w") as token:
                token.write(gmail_token)
        
        if gmail_secret:
            with open(self.secrets_path, "w") as secret:
                secret.write(gmail_secret)
        
        # 尝试从文件加载凭证
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path)
        
        # 检查凭证是否有效
        if not creds or not creds.valid or not creds.has_scopes(_SCOPES):
            if creds and creds.expired and creds.refresh_token and creds.has_scopes(_SCOPES):
                creds.refresh(Request())
            else:
                # 启动OAuth流程
                flow = InstalledAppFlow.from_client_secrets_file(self.secrets_path, _SCOPES)
                creds = flow.run_local_server(port=self.auth_port)
            
            # 保存凭证
            with open(self.token_path, "w") as token:
                token.write(creds.to_json())
        
        return creds
    
    def test_connection(self) -> Dict[str, Any]:
        """
        测试Gmail连接
        
        Returns:
            连接测试结果
        """
        try:
            # 尝试获取凭证
            if not os.path.exists(self.secrets_path):
                return {"success": False, "message": "未找到Gmail API密钥文件"}
            
            creds = self.get_credentials()
            
            # 尝试连接Gmail API
            service = build("gmail", "v1", credentials=creds)
            profile = service.users().getProfile(userId="me").execute()
            
            return {
                "success": True, 
                "message": "Gmail连接成功", 
                "email": profile.get("emailAddress", "")
            }
        except Exception as e:
            logger.exception("Gmail连接测试失败")
            return {"success": False, "message": f"Gmail连接失败: {str(e)}"}
    
    def extract_message_part(self, msg):
        """
        递归提取邮件内容
        
        Args:
            msg: 邮件部分
        
        Returns:
            提取的文本内容
        """
        if msg["mimeType"] == "text/plain":
            body_data = msg.get("body", {}).get("data")
            if body_data:
                return base64.urlsafe_b64decode(body_data).decode("utf-8")
        elif msg["mimeType"] == "text/html":
            body_data = msg.get("body", {}).get("data")
            if body_data:
                return base64.urlsafe_b64decode(body_data).decode("utf-8")
        
        if "parts" in msg:
            for part in msg["parts"]:
                body = self.extract_message_part(part)
                if body:
                    return body
        
        return "No message body available."
    
    def parse_time(self, send_time: str):
        """
        解析时间字符串
        
        Args:
            send_time: 时间字符串
        
        Returns:
            解析后的时间对象
        """
        try:
            parsed_time = parser.parse(send_time)
            return parsed_time
        except (ValueError, TypeError) as e:
            raise ValueError(f"Error parsing time: {send_time} - {e}")
    
    def create_message(self, sender, to, subject, message_text, thread_id=None, original_message_id=None):
        """
        创建邮件消息
        
        Args:
            sender: 发件人
            to: 收件人列表
            subject: 主题
            message_text: 消息内容
            thread_id: 会话ID
            original_message_id: 原始消息ID
        
        Returns:
            创建的消息
        """
        message = MIMEMultipart()
        message["to"] = ", ".join(to) if isinstance(to, list) else to
        message["from"] = sender
        message["subject"] = subject
        
        if original_message_id:
            message["In-Reply-To"] = original_message_id
            message["References"] = original_message_id
        
        message["Message-ID"] = email.utils.make_msgid()
        msg = MIMEText(message_text)
        message.attach(msg)
        
        raw = base64.urlsafe_b64encode(message.as_bytes())
        raw = raw.decode()
        
        result = {"raw": raw}
        if thread_id:
            result["threadId"] = thread_id
        
        return result
    
    def get_recipients(self, headers, email_address, addn_receipients=None):
        """
        获取收件人列表
        
        Args:
            headers: 邮件头
            email_address: 当前邮箱地址
            addn_receipients: 额外收件人
        
        Returns:
            收件人列表
        """
        recipients = set(addn_receipients or [])
        sender = None
        
        for header in headers:
            if header["name"].lower() in ["to", "cc"]:
                recipients.update(header["value"].replace(" ", "").split(","))
            if header["name"].lower() == "from":
                sender = header["value"]
        
        if sender:
            recipients.add(sender)  # 确保原始发件人包含在回复中
        
        # 移除自己的邮箱地址
        for r in list(recipients):
            if email_address in r:
                recipients.remove(r)
        
        return list(recipients)
    
    def send_message(self, service, user_id, message):
        """
        发送邮件
        
        Args:
            service: Gmail服务对象
            user_id: 用户ID
            message: 消息内容
        
        Returns:
            发送结果
        """
        message = service.users().messages().send(userId=user_id, body=message).execute()
        return message
    
    def send_email(self, to, subject, body, reply_to=None):
        """
        发送邮件
        
        Args:
            to: 收件人
            subject: 主题
            body: 内容
            reply_to: 回复邮件ID
        
        Returns:
            发送结果
        """
        try:
            creds = self.get_credentials()
            service = build("gmail", "v1", credentials=creds)
            
            thread_id = None
            original_message_id = None
            
            # 如果是回复邮件
            if reply_to:
                message = service.users().messages().get(userId="me", id=reply_to).execute()
                headers = message["payload"]["headers"]
                
                # 获取原始消息ID
                original_message_id = next(
                    (header["value"] for header in headers if header["name"].lower() == "message-id"),
                    None
                )
                
                thread_id = message["threadId"]
                
                # 获取主题（如果未提供）
                if not subject:
                    subject = next(
                        (header["value"] for header in headers if header["name"].lower() == "subject"),
                        "Re: No Subject"
                    )
                    if not subject.startswith("Re:"):
                        subject = f"Re: {subject}"
            
            # 创建消息
            message = self.create_message(
                "me", 
                to, 
                subject, 
                body, 
                thread_id, 
                original_message_id
            )
            
            # 发送消息
            result = self.send_message(service, "me", message)
            
            return {
                "success": True, 
                "message": "邮件发送成功", 
                "id": result["id"],
                "thread_id": result.get("threadId", "")
            }
        
        except Exception as e:
            logger.exception("发送邮件失败")
            return {"success": False, "message": f"发送邮件失败: {str(e)}"}
    
    def list_emails(self, max_results=50, query=None, include_body=True):
        """
        获取邮件列表
        
        Args:
            max_results: 最大结果数
            query: 查询条件
            include_body: 是否包含邮件内容
        
        Returns:
            邮件列表
        """
        try:
            creds = self.get_credentials()
            service = build("gmail", "v1", credentials=creds)
            
            # 构建查询
            if not query:
                query = ""
            
            # 获取邮件列表
            messages = []
            next_page_token = None
            
            while True:
                results = service.users().messages().list(
                    userId="me", 
                    q=query, 
                    maxResults=min(max_results - len(messages), 100),
                    pageToken=next_page_token
                ).execute()
                
                if "messages" in results:
                    message_ids = [msg["id"] for msg in results["messages"]]
                    
                    # 获取邮件详情
                    for msg_id in message_ids:
                        try:
                            msg = service.users().messages().get(
                                userId="me", 
                                id=msg_id,
                                format="full" if include_body else "metadata"
                            ).execute()
                            
                            # 提取邮件信息
                            headers = msg["payload"]["headers"]
                            
                            # 提取基本信息
                            subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No Subject")
                            sender = next((h["value"] for h in headers if h["name"].lower() == "from"), "")
                            date = next((h["value"] for h in headers if h["name"].lower() == "date"), "")
                            to = next((h["value"] for h in headers if h["name"].lower() == "to"), "")
                            
                            # 提取邮件内容
                            body = ""
                            if include_body:
                                body = self.extract_message_part(msg["payload"])
                            
                            # 构建邮件对象
                            email_obj = {
                                "id": msg["id"],
                                "thread_id": msg["threadId"],
                                "subject": subject,
                                "sender": sender,
                                "recipients": to,
                                "date": date,
                                "labels": msg["labelIds"],
                                "is_read": "UNREAD" not in msg["labelIds"],
                                "snippet": msg["snippet"]
                            }
                            
                            if include_body:
                                email_obj["body"] = body
                            
                            messages.append(email_obj)
                            
                            # 检查是否达到最大结果数
                            if len(messages) >= max_results:
                                break
                        
                        except Exception as e:
                            logger.error(f"获取邮件详情失败: {str(e)}")
                
                # 检查是否有下一页
                next_page_token = results.get("nextPageToken")
                if not next_page_token or len(messages) >= max_results:
                    break
            
            return messages
        
        except Exception as e:
            logger.exception("获取邮件列表失败")
            return []
    
    def mark_as_read(self, message_id):
        """
        将邮件标记为已读
        
        Args:
            message_id: 邮件ID
        
        Returns:
            操作结果
        """
        try:
            creds = self.get_credentials()
            service = build("gmail", "v1", credentials=creds)
            
            # 移除UNREAD标签
            service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            
            return {"success": True, "message": "邮件已标记为已读"}
        
        except Exception as e:
            logger.exception("标记邮件为已读失败")
            return {"success": False, "message": f"标记邮件为已读失败: {str(e)}"}
    
    def get_events_for_days(self, date_strs):
        """
        获取指定日期的日历事件
        
        Args:
            date_strs: 日期字符串列表，格式为 dd-mm-yyyy
        
        Returns:
            日历事件列表
        """
        try:
            creds = self.get_credentials()
            service = build("calendar", "v3", credentials=creds)
            
            events_by_day = {}
            
            for date_str in date_strs:
                try:
                    # 解析日期
                    day, month, year = map(int, date_str.split('-'))
                    
                    # 创建时间范围
                    start_time = datetime(year, month, day, 0, 0, 0).isoformat() + 'Z'
                    end_time = datetime(year, month, day, 23, 59, 59).isoformat() + 'Z'
                    
                    # 获取事件
                    events_result = service.events().list(
                        calendarId='primary',
                        timeMin=start_time,
                        timeMax=end_time,
                        singleEvents=True,
                        orderBy='startTime'
                    ).execute()
                    
                    events = events_result.get('items', [])
                    
                    # 格式化事件
                    formatted_events = []
                    for event in events:
                        start = event['start'].get('dateTime', event['start'].get('date'))
                        end = event['end'].get('dateTime', event['end'].get('date'))
                        
                        formatted_events.append({
                            'summary': event.get('summary', 'No Title'),
                            'start': start,
                            'end': end,
                            'location': event.get('location', ''),
                            'description': event.get('description', ''),
                            'attendees': [
                                attendee.get('email', '') 
                                for attendee in event.get('attendees', [])
                            ]
                        })
                    
                    events_by_day[date_str] = formatted_events
                
                except Exception as e:
                    logger.error(f"获取日期 {date_str} 的事件失败: {str(e)}")
                    events_by_day[date_str] = []
            
            return {
                "success": True,
                "events": events_by_day
            }
        
        except Exception as e:
            logger.exception("获取日历事件失败")
            return {"success": False, "message": f"获取日历事件失败: {str(e)}"}
    
    def send_calendar_invite(self, emails, title, start_time, end_time, description="", location="", timezone="Asia/Shanghai"):
        """
        发送日历邀请
        
        Args:
            emails: 收件人列表
            title: 事件标题
            start_time: 开始时间
            end_time: 结束时间
            description: 事件描述
            location: 事件地点
            timezone: 时区
        
        Returns:
            操作结果
        """
        try:
            creds = self.get_credentials()
            service = build("calendar", "v3", credentials=creds)
            
            # 解析时间
            start_dt = parser.parse(start_time)
            end_dt = parser.parse(end_time)
            
            # 创建事件
            event = {
                'summary': title,
                'location': location,
                'description': description,
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': timezone,
                },
                'end': {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': timezone,
                },
                'attendees': [{'email': email} for email in emails],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},
                        {'method': 'popup', 'minutes': 10},
                    ],
                },
            }
            
            # 创建事件并发送邀请
            event = service.events().insert(
                calendarId='primary',
                body=event,
                sendUpdates='all'
            ).execute()
            
            return {
                "success": True,
                "message": "日历邀请已发送",
                "event_id": event['id'],
                "html_link": event['htmlLink']
            }
        
        except Exception as e:
            logger.exception("发送日历邀请失败")
            return {"success": False, "message": f"发送日历邀请失败: {str(e)}"}

def register_gmail_service(server):
    """
    注册Gmail服务
    
    Args:
        server: MCP服务器实例
    """
    # 创建Gmail服务实例
    gmail_service = GmailService(server.config)
    
    # 注册服务方法
    server.register_service("gmail.test_connection", gmail_service.test_connection)
    server.register_service("gmail.list_emails", gmail_service.list_emails)
    server.register_service("gmail.send_email", gmail_service.send_email)
    server.register_service("gmail.mark_as_read", gmail_service.mark_as_read)
    server.register_service("gmail.get_events_for_days", gmail_service.get_events_for_days)
    server.register_service("gmail.send_calendar_invite", gmail_service.send_calendar_invite)
    
    logger.info("Gmail服务已注册")
