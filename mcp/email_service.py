#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
邮件服务模块 - 提供邮件同步、发送和分析服务
"""

import os
import json
import time
import logging
import sqlite3
import email
import imaplib
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from typing import Dict, Any, List, Optional, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("email_service")

class EmailService:
    """邮件服务类，处理邮件同步、发送和分析"""
    
    def __init__(self, config: Dict[str, Any], db_path: str):
        """
        初始化邮件服务
        
        Args:
            config: 服务配置
            db_path: 数据库路径
        """
        self.config = config
        self.db_path = db_path
        self.email_dir = config["email"]["email_dir"]
        
        # 邮件服务器配置
        self.imap_server = config["email"]["imap_server"]
        self.imap_port = config["email"]["imap_port"]
        self.smtp_server = config["email"]["smtp_server"]
        self.smtp_port = config["email"]["smtp_port"]
        self.email_address = config["email"]["email_address"]
        self.email_password = config["email"]["email_password"]
        self.use_ssl = config["email"]["use_ssl"]
        
        # 确保目录存在
        os.makedirs(self.email_dir, exist_ok=True)
        
        # 初始化数据库
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建邮件表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id TEXT PRIMARY KEY,
            message_id TEXT,
            subject TEXT,
            sender TEXT,
            recipients TEXT,
            date TEXT,
            body_text TEXT,
            body_html TEXT,
            has_attachments INTEGER,
            folder TEXT,
            is_read INTEGER,
            is_flagged INTEGER,
            is_replied INTEGER,
            is_forwarded INTEGER,
            priority TEXT,
            category TEXT,
            sentiment TEXT,
            created_at REAL
        )
        ''')
        
        # 创建邮件标签表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_tags (
            email_id TEXT,
            tag TEXT,
            PRIMARY KEY (email_id, tag),
            FOREIGN KEY (email_id) REFERENCES emails (id)
        )
        ''')
        
        # 创建邮件附件表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_attachments (
            id TEXT PRIMARY KEY,
            email_id TEXT,
            filename TEXT,
            content_type TEXT,
            size INTEGER,
            local_path TEXT,
            created_at REAL,
            FOREIGN KEY (email_id) REFERENCES emails (id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def _decode_str(self, s):
        """解码邮件主题等字符串"""
        if not s:
            return ""
        
        decoded_parts = []
        for part, encoding in decode_header(s):
            if isinstance(part, bytes):
                if encoding:
                    try:
                        decoded_parts.append(part.decode(encoding))
                    except:
                        decoded_parts.append(part.decode('utf-8', errors='replace'))
                else:
                    decoded_parts.append(part.decode('utf-8', errors='replace'))
            else:
                decoded_parts.append(part)
        
        return ''.join(decoded_parts)
    
    def _get_email_body(self, msg):
        """获取邮件正文"""
        text_body = ""
        html_body = ""
        attachments = []
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # 跳过邮件签名等部分
                if content_type == "multipart/alternative":
                    continue
                
                # 处理附件
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        filename = self._decode_str(filename)
                        attachments.append({
                            "filename": filename,
                            "content_type": content_type,
                            "size": len(part.get_payload(decode=True)),
                            "data": part.get_payload(decode=True)
                        })
                    continue
                
                # 处理正文
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        try:
                            decoded_payload = payload.decode(charset, errors='replace')
                        except:
                            decoded_payload = payload.decode('utf-8', errors='replace')
                        
                        if content_type == "text/plain":
                            text_body += decoded_payload
                        elif content_type == "text/html":
                            html_body += decoded_payload
                except:
                    continue
        else:
            # 非多部分邮件
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                try:
                    decoded_payload = payload.decode(charset, errors='replace')
                except:
                    decoded_payload = payload.decode('utf-8', errors='replace')
                
                if content_type == "text/plain":
                    text_body = decoded_payload
                elif content_type == "text/html":
                    html_body = decoded_payload
        
        return text_body, html_body, attachments
    
    def _save_attachment(self, email_id, attachment):
        """保存邮件附件"""
        filename = attachment["filename"]
        safe_filename = re.sub(r'[\\/*?:"<>|]', "_", filename)
        
        # 创建附件目录
        attachment_dir = os.path.join(self.email_dir, "attachments", email_id)
        os.makedirs(attachment_dir, exist_ok=True)
        
        # 保存附件
        local_path = os.path.join(attachment_dir, safe_filename)
        with open(local_path, "wb") as f:
            f.write(attachment["data"])
        
        return local_path
    
    def _analyze_email(self, subject, body):
        """分析邮件内容（分类、优先级、情感）"""
        # 实际项目中应该调用LLM服务进行分析
        # 这里使用简单的规则进行模拟分析
        
        # 分类
        category = "其他"
        if any(kw in subject.lower() for kw in ["会议", "meeting", "讨论"]):
            category = "会议"
        elif any(kw in subject.lower() for kw in ["报告", "report", "周报", "月报"]):
            category = "报告"
        elif any(kw in subject.lower() for kw in ["任务", "task", "工作", "安排"]):
            category = "任务"
        
        # 优先级
        priority = "中"
        if any(kw in subject.lower() for kw in ["紧急", "urgent", "立即", "immediately"]):
            priority = "高"
        elif any(kw in subject.lower() for kw in ["低优先级", "low priority", "参考", "fyi"]):
            priority = "低"
        
        # 情感
        sentiment = "中性"
        positive_words = ["感谢", "谢谢", "好", "优秀", "出色", "满意"]
        negative_words = ["问题", "错误", "失败", "不满", "差", "投诉"]
        
        positive_count = sum(1 for word in positive_words if word in body)
        negative_count = sum(1 for word in negative_words if word in body)
        
        if positive_count > negative_count:
            sentiment = "积极"
        elif negative_count > positive_count:
            sentiment = "消极"
        
        return category, priority, sentiment
    
    def sync_emails(self, folder: str = "INBOX", limit: int = 50) -> Dict[str, Any]:
        """
        同步邮件
        
        Args:
            folder: 邮件文件夹
            limit: 最大同步数量
        
        Returns:
            同步结果
        """
        try:
            # 连接IMAP服务器
            if self.use_ssl:
                mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            else:
                mail = imaplib.IMAP4(self.imap_server, self.imap_port)
            
            # 登录
            mail.login(self.email_address, self.email_password)
            
            # 选择文件夹
            mail.select(folder)
            
            # 搜索邮件
            status, data = mail.search(None, "ALL")
            if status != "OK":
                return {"success": False, "message": "搜索邮件失败", "count": 0}
            
            # 获取邮件ID列表
            email_ids = data[0].split()
            
            # 限制同步数量
            if limit > 0 and len(email_ids) > limit:
                email_ids = email_ids[-limit:]
            
            # 同步邮件
            synced_count = 0
            for email_id in email_ids:
                status, data = mail.fetch(email_id, "(RFC822)")
                if status != "OK":
                    continue
                
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # 解析邮件
                message_id = msg.get("Message-ID", "")
                subject = self._decode_str(msg.get("Subject", ""))
                sender = self._decode_str(msg.get("From", ""))
                recipients = self._decode_str(msg.get("To", ""))
                date = msg.get("Date", "")
                
                # 获取邮件正文和附件
                text_body, html_body, attachments = self._get_email_body(msg)
                
                # 分析邮件
                category, priority, sentiment = self._analyze_email(subject, text_body)
                
                # 生成唯一ID
                unique_id = f"email_{int(time.time())}_{message_id.replace('<', '').replace('>', '')}"
                
                # 保存到数据库
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # 检查邮件是否已存在
                cursor.execute("SELECT id FROM emails WHERE message_id = ?", (message_id,))
                existing = cursor.fetchone()
                
                if existing:
                    # 邮件已存在，跳过
                    conn.close()
                    continue
                
                # 插入邮件记录
                cursor.execute(
                    """
                    INSERT INTO emails (
                        id, message_id, subject, sender, recipients, date, 
                        body_text, body_html, has_attachments, folder, 
                        is_read, is_flagged, is_replied, is_forwarded, 
                        priority, category, sentiment, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        unique_id, message_id, subject, sender, recipients, date,
                        text_body, html_body, 1 if attachments else 0, folder,
                        0, 0, 0, 0,
                        priority, category, sentiment, time.time()
                    )
                )
                
                # 保存附件
                for attachment in attachments:
                    local_path = self._save_attachment(unique_id, attachment)
                    
                    attachment_id = f"attachment_{int(time.time())}_{attachment['filename']}"
                    cursor.execute(
                        """
                        INSERT INTO email_attachments (
                            id, email_id, filename, content_type, size, local_path, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            attachment_id, unique_id, attachment["filename"],
                            attachment["content_type"], attachment["size"],
                            local_path, time.time()
                        )
                    )
                
                conn.commit()
                conn.close()
                
                synced_count += 1
            
            # 关闭连接
            mail.close()
            mail.logout()
            
            return {"success": True, "message": f"成功同步 {synced_count} 封邮件", "count": synced_count}
        
        except Exception as e:
            logger.exception("同步邮件失败")
            return {"success": False, "message": f"同步邮件失败: {str(e)}", "count": 0}
    
    def send_email(self, to: str, subject: str, body: str, html: bool = False) -> Dict[str, Any]:
        """
        发送邮件
        
        Args:
            to: 收件人
            subject: 主题
            body: 正文
            html: 是否HTML格式
        
        Returns:
            发送结果
        """
        try:
            # 创建邮件
            msg = MIMEMultipart()
            msg["From"] = self.email_address
            msg["To"] = to
            msg["Subject"] = subject
            
            # 添加正文
            if html:
                msg.attach(MIMEText(body, "html", "utf-8"))
            else:
                msg.attach(MIMEText(body, "plain", "utf-8"))
            
            # 连接SMTP服务器
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
            
            # 登录
            server.login(self.email_address, self.email_password)
            
            # 发送邮件
            server.send_message(msg)
            
            # 关闭连接
            server.quit()
            
            return {"success": True, "message": "邮件发送成功"}
        
        except Exception as e:
            logger.exception("发送邮件失败")
            return {"success": False, "message": f"发送邮件失败: {str(e)}"}
    
    def list_emails(self, folder: str = None, category: str = None, 
                   priority: str = None, is_read: int = None, 
                   search_query: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        列出邮件
        
        Args:
            folder: 文件夹过滤
            category: 类别过滤
            priority: 优先级过滤
            is_read: 是否已读过滤
            search_query: 搜索关键词
            limit: 最大返回数量
        
        Returns:
            邮件列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        sql = """
        SELECT id, subject, sender, recipients, date, 
               has_attachments, folder, is_read, is_flagged, 
               priority, category, sentiment, created_at
        FROM emails
        """
        
        conditions = []
        params = []
        
        if folder:
            conditions.append("folder = ?")
            params.append(folder)
        
        if category:
            conditions.append("category = ?")
            params.append(category)
        
        if priority:
            conditions.append("priority = ?")
            params.append(priority)
        
        if is_read is not None:
            conditions.append("is_read = ?")
            params.append(is_read)
        
        if search_query:
            conditions.append("(subject LIKE ? OR body_text LIKE ? OR sender LIKE ?)")
            search_term = f"%{search_query}%"
            params.extend([search_term, search_term, search_term])
        
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        results = cursor.fetchall()
        
        emails = []
        for row in results:
            (email_id, subject, sender, recipients, date, 
             has_attachments, folder, is_read, is_flagged, 
             priority, category, sentiment, created_at) = row
            
            emails.append({
                "id": email_id,
                "subject": subject,
                "sender": sender,
                "recipients": recipients,
                "date": date,
                "has_attachments": bool(has_attachments),
                "folder": folder,
                "is_read": bool(is_read),
                "is_flagged": bool(is_flagged),
                "priority": priority,
                "category": category,
                "sentiment": sentiment,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at))
            })
        
        conn.close()
        return emails
    
    def get_email(self, email_id: str) -> Dict[str, Any]:
        """
        获取邮件详情
        
        Args:
            email_id: 邮件ID
        
        Returns:
            邮件详情
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取邮件基本信息
        cursor.execute(
            """
            SELECT id, message_id, subject, sender, recipients, date, 
                   body_text, body_html, has_attachments, folder, 
                   is_read, is_flagged, is_replied, is_forwarded, 
                   priority, category, sentiment, created_at
            FROM emails WHERE id = ?
            """,
            (email_id,)
        )
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            raise ValueError(f"邮件不存在: {email_id}")
        
        (email_id, message_id, subject, sender, recipients, date, 
         body_text, body_html, has_attachments, folder, 
         is_read, is_flagged, is_replied, is_forwarded, 
         priority, category, sentiment, created_at) = result
        
        # 获取附件信息
        cursor.execute(
            """
            SELECT id, filename, content_type, size, local_path
            FROM email_attachments WHERE email_id = ?
            """,
            (email_id,)
        )
        
        attachments = []
        for row in cursor.fetchall():
            attachment_id, filename, content_type, size, local_path = row
            attachments.append({
                "id": attachment_id,
                "filename": filename,
                "content_type": content_type,
                "size": size,
                "local_path": local_path
            })
        
        # 标记为已读
        if not is_read:
            cursor.execute("UPDATE emails SET is_read = 1 WHERE id = ?", (email_id,))
            conn.commit()
        
        conn.close()
        
        return {
            "id": email_id,
            "message_id": message_id,
            "subject": subject,
            "sender": sender,
            "recipients": recipients,
            "date": date,
            "body_text": body_text,
            "body_html": body_html,
            "has_attachments": bool(has_attachments),
            "attachments": attachments,
            "folder": folder,
            "is_read": bool(is_read),
            "is_flagged": bool(is_flagged),
            "is_replied": bool(is_replied),
            "is_forwarded": bool(is_forwarded),
            "priority": priority,
            "category": category,
            "sentiment": sentiment,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at))
        }
    
    def update_email_status(self, email_id: str, status_field: str, value: int) -> bool:
        """
        更新邮件状态
        
        Args:
            email_id: 邮件ID
            status_field: 状态字段（is_read, is_flagged, is_replied, is_forwarded）
            value: 状态值
        
        Returns:
            是否成功
        """
        valid_fields = ["is_read", "is_flagged", "is_replied", "is_forwarded"]
        if status_field not in valid_fields:
            raise ValueError(f"无效的状态字段: {status_field}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(f"UPDATE emails SET {status_field} = ? WHERE id = ?", (value, email_id))
        conn.commit()
        conn.close()
        
        return True
    
    def delete_email(self, email_id: str) -> bool:
        """
        删除邮件
        
        Args:
            email_id: 邮件ID
        
        Returns:
            是否成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 删除附件
        cursor.execute("SELECT local_path FROM email_attachments WHERE email_id = ?", (email_id,))
        for row in cursor.fetchall():
            local_path = row[0]
            if os.path.exists(local_path):
                os.remove(local_path)
        
        # 删除附件记录
        cursor.execute("DELETE FROM email_attachments WHERE email_id = ?", (email_id,))
        
        # 删除标签
        cursor.execute("DELETE FROM email_tags WHERE email_id = ?", (email_id,))
        
        # 删除邮件
        cursor.execute("DELETE FROM emails WHERE id = ?", (email_id,))
        
        conn.commit()
        conn.close()
        
        return True
    
    def analyze_emails(self, limit: int = 100) -> Dict[str, Any]:
        """
        分析邮件统计信息
        
        Args:
            limit: 分析的邮件数量
        
        Returns:
            统计结果
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取总邮件数
        cursor.execute("SELECT COUNT(*) FROM emails")
        total_count = cursor.fetchone()[0]
        
        # 获取未读邮件数
        cursor.execute("SELECT COUNT(*) FROM emails WHERE is_read = 0")
        unread_count = cursor.fetchone()[0]
        
        # 获取类别分布
        cursor.execute("SELECT category, COUNT(*) FROM emails GROUP BY category")
        categories = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 获取优先级分布
        cursor.execute("SELECT priority, COUNT(*) FROM emails GROUP BY priority")
        priorities = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 获取情感分布
        cursor.execute("SELECT sentiment, COUNT(*) FROM emails GROUP BY sentiment")
        sentiments = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 获取发件人分布
        cursor.execute("SELECT sender, COUNT(*) FROM emails GROUP BY sender ORDER BY COUNT(*) DESC LIMIT 10")
        senders = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            "total_count": total_count,
            "unread_count": unread_count,
            "categories": categories,
            "priorities": priorities,
            "sentiments": sentiments,
            "top_senders": senders
        }

def register_email_service(server):
    """
    注册邮件服务
    
    Args:
        server: MCP服务器实例
    """
    # 创建邮件服务实例
    service = EmailService(server.config, server.config["db"]["sqlite_path"])
    
    # 注册方法
    server.register_module("email", {
        "sync": service.sync_emails,
        "send": service.send_email,
        "list": service.list_emails,
        "get": service.get_email,
        "update_status": service.update_email_status,
        "delete": service.delete_email,
        "analyze": service.analyze_emails
    })
