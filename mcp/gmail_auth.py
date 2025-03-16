#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Gmail认证模块 - 提供Gmail API认证和操作功能
"""

import os
import json
import logging
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import email.utils

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("gmail_auth")

# Gmail API 权限范围
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send"
]

# 默认端口
DEFAULT_PORT = 54191

class GmailAuthService:
    """Gmail认证服务类，处理OAuth认证和令牌管理"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化Gmail认证服务
        
        Args:
            config: 服务配置
        """
        self.config = config
        
        # 获取Gmail提供商配置
        gmail_config = None
        for provider in config["email"]["providers"]:
            if provider["name"] == "gmail":
                gmail_config = provider
                break
        
        if not gmail_config:
            raise ValueError("Gmail provider configuration not found")
        
        self.enabled = gmail_config["enabled"]
        self.credentials_file = gmail_config["credentials_file"]
        
        # 确保凭证目录存在
        credentials_dir = os.path.dirname(self.credentials_file)
        os.makedirs(credentials_dir, exist_ok=True)
        
        # 设置令牌路径
        self.token_file = os.path.join(credentials_dir, "gmail_token.json")
    
    def get_credentials(self) -> Optional[Credentials]:
        """
        获取Gmail API凭证
        
        Returns:
            Gmail API凭证对象，如果认证失败则返回None
        """
        if not self.enabled:
            logger.warning("Gmail integration is disabled")
            return None
        
        creds = None
        
        # 尝试从令牌文件加载凭证
        if os.path.exists(self.token_file):
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            except Exception as e:
                logger.error(f"Error loading credentials from token file: {e}")
        
        # 如果没有有效凭证，则进行认证流程
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Error refreshing credentials: {e}")
                    creds = None
            else:
                try:
                    # 检查客户端密钥文件是否存在
                    if not os.path.exists(self.credentials_file):
                        logger.error(f"Client secrets file not found: {self.credentials_file}")
                        return None
                    
                    # 启动认证流程
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES)
                    creds = flow.run_local_server(port=DEFAULT_PORT)
                    
                    # 保存令牌到文件
                    with open(self.token_file, "w") as token:
                        token.write(creds.to_json())
                except Exception as e:
                    logger.error(f"Error during authentication flow: {e}")
                    return None
        
        return creds
    
    def build_service(self) -> Optional[Any]:
        """
        构建Gmail API服务
        
        Returns:
            Gmail API服务对象，如果创建失败则返回None
        """
        creds = self.get_credentials()
        if not creds:
            return None
        
        try:
            service = build("gmail", "v1", credentials=creds)
            return service
        except Exception as e:
            logger.error(f"Error building Gmail service: {e}")
            return None
    
    def test_connection(self) -> Dict[str, Any]:
        """
        测试Gmail连接
        
        Returns:
            测试结果，包括成功状态和消息
        """
        service = self.build_service()
        if not service:
            return {"success": False, "message": "Failed to build Gmail service"}
        
        try:
            # 尝试获取用户信息
            profile = service.users().getProfile(userId="me").execute()
            email_address = profile.get("emailAddress", "Unknown")
            return {
                "success": True, 
                "message": f"Successfully connected to Gmail as {email_address}",
                "email_address": email_address
            }
        except Exception as e:
            logger.error(f"Error testing Gmail connection: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def list_emails(self, max_results: int = 10, query: str = "") -> List[Dict[str, Any]]:
        """
        列出Gmail邮件
        
        Args:
            max_results: 最大返回结果数
            query: Gmail查询字符串
        
        Returns:
            邮件列表
        """
        service = self.build_service()
        if not service:
            logger.error("Failed to build Gmail service")
            return []
        
        try:
            # 获取邮件列表
            results = service.users().messages().list(
                userId="me", q=query, maxResults=max_results).execute()
            
            messages = results.get("messages", [])
            emails = []
            
            for message in messages:
                msg = service.users().messages().get(userId="me", id=message["id"]).execute()
                
                # 解析邮件头
                headers = msg["payload"]["headers"]
                subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "")
                sender = next((h["value"] for h in headers if h["name"].lower() == "from"), "")
                date = next((h["value"] for h in headers if h["name"].lower() == "date"), "")
                
                # 解析邮件内容
                body = self._extract_message_body(msg["payload"])
                
                emails.append({
                    "id": message["id"],
                    "thread_id": msg["threadId"],
                    "subject": subject,
                    "sender": sender,
                    "date": date,
                    "snippet": msg.get("snippet", ""),
                    "body": body,
                    "labels": msg.get("labelIds", [])
                })
            
            return emails
        except Exception as e:
            logger.error(f"Error listing emails: {e}")
            return []
    
    def _extract_message_body(self, payload):
        """
        递归提取邮件正文
        
        Args:
            payload: 邮件负载部分
        
        Returns:
            邮件正文
        """
        if "body" in payload and payload["body"].get("data"):
            data = payload["body"]["data"]
            return base64.urlsafe_b64decode(data).decode("utf-8")
        
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    if "body" in part and part["body"].get("data"):
                        data = part["body"]["data"]
                        return base64.urlsafe_b64decode(data).decode("utf-8")
            
            # 如果没有找到text/plain部分，尝试html部分
            for part in payload["parts"]:
                if part["mimeType"] == "text/html":
                    if "body" in part and part["body"].get("data"):
                        data = part["body"]["data"]
                        return base64.urlsafe_b64decode(data).decode("utf-8")
            
            # 递归检查多部分邮件
            for part in payload["parts"]:
                body = self._extract_message_body(part)
                if body:
                    return body
        
        return "No message body found"
    
    def send_email(self, to: str, subject: str, body: str, html: bool = False) -> Dict[str, Any]:
        """
        发送邮件
        
        Args:
            to: 收件人
            subject: 主题
            body: 邮件正文
            html: 是否HTML格式
        
        Returns:
            发送结果
        """
        service = self.build_service()
        if not service:
            return {"success": False, "message": "Failed to build Gmail service"}
        
        try:
            # 创建邮件
            message = MIMEMultipart()
            message["to"] = to
            message["subject"] = subject
            
            # 设置邮件内容
            if html:
                msg = MIMEText(body, "html")
            else:
                msg = MIMEText(body, "plain")
            
            message.attach(msg)
            
            # 编码邮件
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            
            # 发送邮件
            sent_message = service.users().messages().send(
                userId="me", body={"raw": raw_message}).execute()
            
            return {
                "success": True, 
                "message": "Email sent successfully", 
                "message_id": sent_message["id"]
            }
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}

def register_gmail_auth_service(server):
    """
    注册Gmail认证服务
    
    Args:
        server: MCP服务器实例
    """
    config = server.config
    gmail_auth_service = GmailAuthService(config)
    
    # 注册服务方法
    server.register_method("gmail.get_credentials", gmail_auth_service.get_credentials)
    server.register_method("gmail.test_connection", gmail_auth_service.test_connection)
    server.register_method("gmail.list_emails", gmail_auth_service.list_emails)
    server.register_method("gmail.send_email", gmail_auth_service.send_email)
    
    logger.info("Gmail Auth Service registered")
