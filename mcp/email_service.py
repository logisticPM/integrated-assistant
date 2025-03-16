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
import re
from datetime import datetime
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
        self.email_dir = os.path.join(os.path.dirname(db_path), "emails")
        
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
            created_at REAL,
            project_id TEXT DEFAULT "default"
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
    
    def _detect_project(self, subject, body):
        """
        从邮件内容中检测项目
        
        Args:
            subject: 邮件主题
            body: 邮件正文
        
        Returns:
            项目ID
        """
        try:
            # 使用MCP调用项目服务获取项目列表
            from mcp.client import MCPClient
            mcp_client = MCPClient("127.0.0.1", self.config["mcp"]["server_port"])
            
            # 获取项目列表
            projects = mcp_client.call("chatbot.list_projects")
            
            if not projects or not isinstance(projects, list):
                return "default"
            
            # 按名称长度降序排序，优先匹配长名称
            projects.sort(key=lambda x: len(x.get("name", "")), reverse=True)
            
            # 合并主题和正文进行检测
            content = f"{subject}\n{body}"
            
            for project in projects:
                project_name = project.get("name", "")
                project_id = project.get("id", "")
                
                # 检查项目名称是否出现在内容中
                if project_name and project_name.lower() in content.lower():
                    return project_id
            
            return "default"
        except Exception as e:
            logger.error(f"检测项目失败: {str(e)}")
            return "default"
    
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
            # 使用MCP调用Gmail服务获取邮件
            from mcp.client import MCPClient
            mcp_client = MCPClient("127.0.0.1", self.config["mcp"]["server_port"])
            
            # 测试Gmail连接
            connection_test = mcp_client.call("gmail.test_connection")
            if not connection_test["success"]:
                return {"success": False, "message": f"Gmail连接失败: {connection_test['message']}", "count": 0}
            
            # 获取邮件列表
            emails = mcp_client.call("gmail.list_emails", {"max_results": limit, "query": f"in:{folder}"})
            if not emails:
                return {"success": True, "message": "没有新邮件", "new_emails": 0}
            
            # 同步到数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            new_count = 0
            for email in emails:
                # 检查邮件是否已存在
                cursor.execute("SELECT id FROM emails WHERE message_id = ?", (email["id"],))
                if cursor.fetchone():
                    continue
                
                # 分析邮件
                category, priority, sentiment = self._analyze_email(email["subject"], email["body"])
                
                # 检测项目
                project_id = self._detect_project(email["subject"], email["body"])
                
                # 插入邮件
                now = time.time()
                cursor.execute('''
                INSERT INTO emails (
                    id, message_id, subject, sender, recipients, date, 
                    body_text, body_html, has_attachments, folder, 
                    is_read, is_flagged, is_replied, is_forwarded, 
                    priority, category, sentiment, created_at, project_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    email["id"], email["id"], email["subject"], email["sender"], 
                    email.get("recipients", ""), email["date"], 
                    email["body"], "", 0, folder, 
                    0, 0, 0, 0, 
                    priority, category, sentiment, now, project_id
                ))
                
                new_count += 1
                
                # 如果是会议相关邮件，创建会议记录
                if category == "会议":
                    try:
                        # 提取会议信息
                        meeting_title = email["subject"]
                        meeting_description = email["body"][:500] if len(email["body"]) > 500 else email["body"]
                        
                        # 创建会议记录
                        mcp_client.call("meeting.create", {
                            "title": meeting_title,
                            "description": meeting_description,
                            "project_id": project_id,
                            "tags": ["email", f"sender:{email['sender']}"]
                        })
                        
                        logger.info(f"从邮件创建会议记录: {meeting_title}, 项目: {project_id}")
                    except Exception as e:
                        logger.error(f"从邮件创建会议记录失败: {str(e)}")
                
                # 将邮件添加到知识库
                try:
                    # 保存邮件内容到文件
                    email_content = f"# {email['subject']}\n\n"
                    email_content += f"- 发件人: {email['sender']}\n"
                    email_content += f"- 日期: {email['date']}\n"
                    email_content += f"- 类别: {category}\n"
                    email_content += f"- 优先级: {priority}\n\n"
                    email_content += f"## 正文\n\n{email['body']}\n"
                    
                    email_file_path = os.path.join(self.email_dir, f"{email['id']}.md")
                    with open(email_file_path, "w", encoding="utf-8") as f:
                        f.write(email_content)
                    
                    # 添加到知识库
                    mcp_client.call("vector.create_document", {
                        "title": f"邮件: {email['subject']}",
                        "category": "email",
                        "tags": ["email", f"sender:{email['sender']}", f"category:{category}"],
                        "file_path": email_file_path,
                        "project_id": project_id
                    })
                    
                    logger.info(f"邮件已添加到知识库: {email['subject']}, 项目: {project_id}")
                except Exception as e:
                    logger.error(f"添加邮件到知识库失败: {str(e)}")
            
            conn.commit()
            conn.close()
            
            return {
                "success": True, 
                "message": f"同步完成，新增 {new_count} 封邮件", 
                "new_emails": new_count
            }
        
        except Exception as e:
            logger.exception(f"同步邮件失败: {str(e)}")
            return {"success": False, "message": f"同步失败: {str(e)}", "new_emails": 0}
    
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
            # 使用MCP调用Gmail服务发送邮件
            from mcp.client import MCPClient
            mcp_client = MCPClient("127.0.0.1", self.config["mcp"]["server_port"])
            
            result = mcp_client.call("gmail.send_email", {
                "to": to,
                "subject": subject,
                "body": body,
                "html": html
            })
            
            return result
        except Exception as e:
            logger.error(f"发送邮件失败: {e}")
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
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM emails"
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
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY date DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            emails = []
            for row in rows:
                email_data = dict(row)
                emails.append(email_data)
            
            conn.close()
            return emails
        except Exception as e:
            logger.error(f"列出邮件失败: {e}")
            return []
    
    def get_email(self, email_id: str) -> Optional[Dict[str, Any]]:
        """
        获取邮件详情
        
        Args:
            email_id: 邮件ID
        
        Returns:
            邮件详情
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM emails WHERE id = ?", (email_id,))
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return None
            
            # 转换为字典
            email = dict(row)
            
            # 获取标签
            cursor.execute("SELECT tag FROM email_tags WHERE email_id = ?", (email_id,))
            tags = [row[0] for row in cursor.fetchall()]
            email["tags"] = tags
            
            # 获取附件
            cursor.execute("SELECT * FROM email_attachments WHERE email_id = ?", (email_id,))
            attachments = [dict(row) for row in cursor.fetchall()]
            email["attachments"] = attachments
            
            conn.close()
            return email
        
        except Exception as e:
            logger.exception(f"获取邮件详情失败: {email_id}, {str(e)}")
            return None
    
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
        try:
            # 验证状态字段
            valid_fields = ["is_read", "is_flagged", "is_replied", "is_forwarded"]
            if status_field not in valid_fields:
                logger.error(f"无效的状态字段: {status_field}")
                return False
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 更新状态
            cursor.execute(f"UPDATE emails SET {status_field} = ? WHERE id = ?", (value, email_id))
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            logger.error(f"更新邮件状态失败: {e}")
            return False
    
    def update_email_project(self, email_id: str, project_id: str) -> bool:
        """
        更新邮件所属项目
        
        Args:
            email_id: 邮件ID
            project_id: 项目ID
        
        Returns:
            是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 更新邮件项目
            cursor.execute(
                "UPDATE emails SET project_id = ? WHERE id = ?",
                (project_id, email_id)
            )
            
            if cursor.rowcount == 0:
                conn.close()
                return False
            
            conn.commit()
            conn.close()
            
            # 更新知识库中的邮件文档
            try:
                from mcp.client import MCPClient
                mcp_client = MCPClient("127.0.0.1", self.config["mcp"]["server_port"])
                
                # 查询知识库中的邮件文档
                docs = mcp_client.call("vector.search_documents", {
                    "query": "",
                    "category": "email",
                    "tags": [f"email_id:{email_id}"]
                })
                
                if docs and isinstance(docs, list) and len(docs) > 0:
                    # 更新文档项目
                    for doc in docs:
                        # 这里假设向量服务有更新文档项目的方法
                        mcp_client.call("vector.update_document_project", {
                            "document_id": doc["id"],
                            "project_id": project_id
                        })
            except Exception as e:
                logger.error(f"更新知识库中的邮件项目失败: {str(e)}")
            
            return True
        
        except Exception as e:
            logger.exception(f"更新邮件项目失败: {email_id}, {str(e)}")
            return False
    
    def delete_email(self, email_id: str) -> bool:
        """
        删除邮件
        
        Args:
            email_id: 邮件ID
        
        Returns:
            是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 删除附件
            cursor.execute("DELETE FROM email_attachments WHERE email_id = ?", (email_id,))
            
            # 删除标签
            cursor.execute("DELETE FROM email_tags WHERE email_id = ?", (email_id,))
            
            # 删除邮件
            cursor.execute("DELETE FROM emails WHERE id = ?", (email_id,))
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            logger.error(f"删除邮件失败: {e}")
            return False
    
    def analyze_emails(self, limit: int = 100) -> Dict[str, Any]:
        """
        分析邮件统计信息
        
        Args:
            limit: 分析的邮件数量
        
        Returns:
            统计结果
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取最近的邮件
            cursor.execute("SELECT * FROM emails ORDER BY date DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            
            # 统计分类
            cursor.execute("SELECT category, COUNT(*) FROM emails GROUP BY category")
            categories = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 统计优先级
            cursor.execute("SELECT priority, COUNT(*) FROM emails GROUP BY priority")
            priorities = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 统计情感
            cursor.execute("SELECT sentiment, COUNT(*) FROM emails GROUP BY sentiment")
            sentiments = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 统计发件人
            cursor.execute("SELECT sender, COUNT(*) FROM emails GROUP BY sender ORDER BY COUNT(*) DESC LIMIT 10")
            senders = {row[0]: row[1] for row in cursor.fetchall()}
            
            conn.close()
            
            return {
                "total": len(rows),
                "categories": categories,
                "priorities": priorities,
                "sentiments": sentiments,
                "top_senders": senders
            }
        except Exception as e:
            logger.error(f"分析邮件失败: {e}")
            return {"total": 0}

def register_email_service(server):
    """
    注册邮件服务
    
    Args:
        server: MCP服务器实例
    """
    config = server.config
    db_path = config["db"]["sqlite_path"]
    email_service = EmailService(config, db_path)
    
    # 注册服务方法
    server.register_method("email.sync", email_service.sync_emails)
    server.register_method("email.send", email_service.send_email)
    server.register_method("email.list", email_service.list_emails)
    server.register_method("email.get", email_service.get_email)
    server.register_method("email.update_status", email_service.update_email_status)
    server.register_method("email.update_project", email_service.update_email_project)
    server.register_method("email.delete", email_service.delete_email)
    server.register_method("email.analyze", email_service.analyze_emails)
    
    logger.info("Email Service registered")
