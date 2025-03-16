#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
会议服务模块 - 提供会议记录管理和分析功能
支持将会议记录存储到不同的项目工作空间
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
logger = logging.getLogger("meeting_service")

class MeetingService:
    """会议服务类，处理会议记录管理和分析"""
    
    def __init__(self, config: Dict[str, Any], db_path: str, mcp_client=None):
        """
        初始化会议服务
        
        Args:
            config: 服务配置
            db_path: 数据库路径
            mcp_client: MCP客户端实例
        """
        self.config = config
        self.db_path = db_path
        self.mcp_client = mcp_client
        self.meeting_dir = os.path.join(os.path.dirname(db_path), "meetings")
        
        # 确保目录存在
        os.makedirs(self.meeting_dir, exist_ok=True)
        
        # 初始化数据库
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建会议表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS meetings (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            start_time TEXT,
            end_time TEXT,
            participants TEXT,
            project_id TEXT,
            recording_path TEXT,
            transcription_path TEXT,
            transcription_status TEXT,
            summary TEXT,
            key_points TEXT,
            agenda TEXT,
            decisions TEXT,
            action_items TEXT,
            created_at REAL,
            updated_at REAL
        )
        ''')
        
        # 创建会议标签表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS meeting_tags (
            meeting_id TEXT,
            tag TEXT,
            PRIMARY KEY (meeting_id, tag),
            FOREIGN KEY (meeting_id) REFERENCES meetings (id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_meeting(self, title: str, description: str = "", participants: List[str] = None, 
                      project_id: str = "default", tags: List[str] = None) -> str:
        """
        创建会议记录
        
        Args:
            title: 会议标题
            description: 会议描述
            participants: 参会人员
            project_id: 项目ID
            tags: 标签列表
        
        Returns:
            会议ID
        """
        # 生成会议ID
        meeting_id = f"meeting_{int(time.time())}_{title.replace(' ', '_')}"
        
        # 准备参会人员
        if participants is None:
            participants = []
        
        # 准备标签
        if tags is None:
            tags = []
        
        # 保存会议信息
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = time.time()
        cursor.execute('''
        INSERT INTO meetings (
            id, title, description, participants, project_id, 
            transcription_status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            meeting_id, title, description, json.dumps(participants), project_id,
            "pending", now, now
        ))
        
        # 保存会议标签
        for tag in tags:
            cursor.execute(
                "INSERT INTO meeting_tags (meeting_id, tag) VALUES (?, ?)",
                (meeting_id, tag)
            )
        
        conn.commit()
        conn.close()
        
        logger.info(f"创建会议记录: {title} (ID: {meeting_id}, 项目: {project_id})")
        return meeting_id
    
    def update_meeting(self, meeting_id: str, **kwargs) -> bool:
        """
        更新会议信息
        
        Args:
            meeting_id: 会议ID
            **kwargs: 要更新的字段
        
        Returns:
            是否成功
        """
        try:
            # 检查会议是否存在
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM meetings WHERE id = ?", (meeting_id,))
            if not cursor.fetchone():
                logger.error(f"会议不存在: {meeting_id}")
                conn.close()
                return False
            
            # 构建更新语句
            valid_fields = [
                "title", "description", "start_time", "end_time", "participants",
                "project_id", "recording_path", "transcription_path", "transcription_status",
                "summary", "key_points", "agenda", "decisions", "action_items"
            ]
            
            update_fields = []
            params = []
            
            for key, value in kwargs.items():
                if key in valid_fields:
                    update_fields.append(f"{key} = ?")
                    # 如果是列表类型，转换为JSON字符串
                    if isinstance(value, list):
                        params.append(json.dumps(value))
                    else:
                        params.append(value)
            
            if not update_fields:
                logger.warning(f"没有有效的更新字段: {meeting_id}")
                conn.close()
                return False
            
            # 添加更新时间
            update_fields.append("updated_at = ?")
            params.append(time.time())
            
            # 添加会议ID
            params.append(meeting_id)
            
            # 执行更新
            cursor.execute(
                f"UPDATE meetings SET {', '.join(update_fields)} WHERE id = ?",
                params
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"更新会议信息: {meeting_id}")
            return True
        
        except Exception as e:
            logger.exception(f"更新会议信息失败: {meeting_id}, {str(e)}")
            return False
    
    def get_meeting(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会议信息
        
        Args:
            meeting_id: 会议ID
        
        Returns:
            会议信息
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return None
            
            # 转换为字典
            meeting = dict(row)
            
            # 解析JSON字段
            if meeting.get("participants"):
                meeting["participants"] = json.loads(meeting["participants"])
            
            # 获取标签
            cursor.execute("SELECT tag FROM meeting_tags WHERE meeting_id = ?", (meeting_id,))
            tags = [row["tag"] for row in cursor.fetchall()]
            meeting["tags"] = tags
            
            conn.close()
            return meeting
        
        except Exception as e:
            logger.exception(f"获取会议信息失败: {meeting_id}, {str(e)}")
            return None
    
    def list_meetings(self, project_id: str = None, tag: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取会议列表
        
        Args:
            project_id: 项目ID过滤
            tag: 标签过滤
            limit: 最大返回数量
        
        Returns:
            会议列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM meetings"
            conditions = []
            params = []
            
            if project_id:
                conditions.append("project_id = ?")
                params.append(project_id)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            meetings = []
            for row in rows:
                meeting = dict(row)
                
                # 解析JSON字段
                if meeting.get("participants"):
                    meeting["participants"] = json.loads(meeting["participants"])
                
                # 如果有标签过滤，检查会议是否有该标签
                if tag:
                    cursor.execute("SELECT tag FROM meeting_tags WHERE meeting_id = ? AND tag = ?", (meeting["id"], tag))
                    if not cursor.fetchone():
                        continue
                
                # 获取所有标签
                cursor.execute("SELECT tag FROM meeting_tags WHERE meeting_id = ?", (meeting["id"],))
                tags = [row["tag"] for row in cursor.fetchall()]
                meeting["tags"] = tags
                
                meetings.append(meeting)
            
            conn.close()
            return meetings
        
        except Exception as e:
            logger.exception(f"获取会议列表失败: {str(e)}")
            return []
    
    def delete_meeting(self, meeting_id: str) -> bool:
        """
        删除会议记录
        
        Args:
            meeting_id: 会议ID
        
        Returns:
            是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取会议信息
            cursor.execute("SELECT recording_path, transcription_path FROM meetings WHERE id = ?", (meeting_id,))
            result = cursor.fetchone()
            
            if not result:
                logger.error(f"会议不存在: {meeting_id}")
                conn.close()
                return False
            
            recording_path, transcription_path = result
            
            # 删除会议标签
            cursor.execute("DELETE FROM meeting_tags WHERE meeting_id = ?", (meeting_id,))
            
            # 删除会议记录
            cursor.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
            
            conn.commit()
            conn.close()
            
            # 删除相关文件
            if recording_path and os.path.exists(recording_path):
                os.remove(recording_path)
            
            if transcription_path and os.path.exists(transcription_path):
                os.remove(transcription_path)
            
            logger.info(f"删除会议记录: {meeting_id}")
            return True
        
        except Exception as e:
            logger.exception(f"删除会议记录失败: {meeting_id}, {str(e)}")
            return False
    
    def process_transcription(self, meeting_id: str, transcription_result: Dict[str, Any]) -> bool:
        """
        处理转录结果，生成摘要和关键点，并存储到知识库
        
        Args:
            meeting_id: 会议ID
            transcription_result: 转录结果
        
        Returns:
            是否成功
        """
        try:
            # 获取会议信息
            meeting = self.get_meeting(meeting_id)
            if not meeting:
                logger.error(f"会议不存在: {meeting_id}")
                return False
            
            # 提取转录文本
            transcription_text = transcription_result.get("text", "")
            if not transcription_text:
                logger.error(f"转录文本为空: {meeting_id}")
                return False
            
            # 使用LLM生成摘要和关键点
            if self.mcp_client:
                # 生成摘要
                summary_result = self.mcp_client.call("llm.generate_meeting_summary", {
                    "transcription": transcription_text
                })
                
                summary = summary_result if isinstance(summary_result, str) else summary_result.get("summary", "")
                
                # 提取关键点
                key_points_result = self.mcp_client.call("llm.extract_meeting_key_points", {
                    "transcription": transcription_text
                })
                
                key_points = json.dumps(key_points_result) if isinstance(key_points_result, list) else key_points_result
                
                # 更新会议信息
                self.update_meeting(
                    meeting_id,
                    summary=summary,
                    key_points=key_points
                )
                
                # 将会议记录存储到知识库
                project_id = meeting.get("project_id", "default")
                title = meeting.get("title", "未命名会议")
                
                # 创建会议记录文档
                document_content = f"# {title}\n\n"
                document_content += f"## 会议信息\n\n"
                document_content += f"- 日期: {datetime.now().strftime('%Y-%m-%d')}\n"
                document_content += f"- 参与者: {', '.join(meeting.get('participants', []))}\n\n"
                document_content += f"## 会议摘要\n\n{summary}\n\n"
                document_content += f"## 关键点\n\n"
                
                # 添加关键点
                try:
                    key_points_list = json.loads(key_points) if isinstance(key_points, str) else key_points
                    for point in key_points_list:
                        document_content += f"- {point.get('timestamp', '')}: {point.get('point', '')}\n"
                except:
                    document_content += f"{key_points}\n\n"
                
                document_content += f"\n## 完整转录\n\n{transcription_text}\n"
                
                # 保存会议记录文档
                meeting_doc_path = os.path.join(self.meeting_dir, f"{meeting_id}_summary.md")
                with open(meeting_doc_path, "w", encoding="utf-8") as f:
                    f.write(document_content)
                
                # 将文档添加到知识库
                try:
                    # 调用向量服务添加文档
                    doc_result = self.mcp_client.call("vector.create_document", {
                        "title": f"会议记录: {title}",
                        "category": "meeting",
                        "tags": meeting.get("tags", []) + ["meeting", f"project:{project_id}"],
                        "file_path": meeting_doc_path,
                        "project_id": project_id
                    })
                    
                    if doc_result and isinstance(doc_result, dict) and doc_result.get("id"):
                        # 处理文档（向量化）
                        self.mcp_client.call("vector.process_document", {
                            "document_id": doc_result["id"]
                        })
                        
                        logger.info(f"会议记录已添加到知识库: {meeting_id}, 项目: {project_id}")
                    else:
                        logger.error(f"添加会议记录到知识库失败: {meeting_id}")
                
                except Exception as e:
                    logger.exception(f"添加会议记录到知识库失败: {meeting_id}, {str(e)}")
            
            return True
        
        except Exception as e:
            logger.exception(f"处理转录结果失败: {meeting_id}, {str(e)}")
            return False
    
    def generate_structured_summary(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        """
        生成结构化的会议摘要，包括议程、决策、行动项等
        
        Args:
            meeting_id: 会议ID
        
        Returns:
            结构化摘要结果
        """
        try:
            # 获取会议信息
            meeting = self.get_meeting(meeting_id)
            if not meeting:
                logger.error(f"会议不存在: {meeting_id}")
                return None
            
            # 获取转录文本
            transcription = self.mcp_client.call("transcription.get", {
                "meeting_id": meeting_id
            })
            
            if not transcription:
                logger.error(f"转录文本不存在: {meeting_id}")
                return None
            
            # 使用LLM生成结构化摘要
            if self.mcp_client:
                # 生成结构化摘要
                structured_summary = self.mcp_client.call("llm.generate_structured_meeting_summary", {
                    "transcription": transcription,
                    "meeting_title": meeting.get("title", ""),
                    "participants": meeting.get("participants", [])
                })
                
                if not structured_summary or not isinstance(structured_summary, dict):
                    logger.error(f"生成结构化摘要失败: {meeting_id}")
                    return None
                
                # 更新会议信息
                self.update_meeting(
                    meeting_id,
                    summary=structured_summary.get("summary", ""),
                    agenda=structured_summary.get("agenda", ""),
                    decisions=structured_summary.get("decisions", ""),
                    action_items=json.dumps(structured_summary.get("action_items", [])),
                    key_points=json.dumps(structured_summary.get("key_points", []))
                )
                
                return structured_summary
            
            return None
        
        except Exception as e:
            logger.exception(f"生成结构化摘要失败: {meeting_id}, {str(e)}")
            return None
    
    def list_tags(self) -> List[str]:
        """
        获取所有会议标签列表
        
        Returns:
            标签列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT DISTINCT tag FROM meeting_tags")
            tags = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            return tags
        
        except Exception as e:
            logger.exception(f"获取标签列表失败: {str(e)}")
            return []
    
    def export_summary(self, meeting_id: str, format: str = "markdown") -> Optional[Dict[str, Any]]:
        """
        导出会议摘要
        
        Args:
            meeting_id: 会议ID
            format: 导出格式，支持markdown、html
        
        Returns:
            导出结果，包含文件路径
        """
        try:
            # 获取会议信息
            meeting = self.get_meeting(meeting_id)
            if not meeting:
                logger.error(f"会议不存在: {meeting_id}")
                return None
            
            # 获取转录文本
            transcription = self.mcp_client.call("transcription.get", {
                "meeting_id": meeting_id
            }) or ""
            
            # 准备导出内容
            title = meeting.get("title", "未命名会议")
            date = meeting.get("created_at", datetime.now().strftime("%Y-%m-%d"))
            participants = ", ".join(meeting.get("participants", []))
            summary = meeting.get("summary", "")
            agenda = meeting.get("agenda", "")
            decisions = meeting.get("decisions", "")
            
            # 解析行动项
            action_items_content = ""
            try:
                if meeting.get("action_items"):
                    action_items = json.loads(meeting.get("action_items"))
                    action_items_content += "| 负责人 | 任务 | 截止日期 | 状态 |\n"
                    action_items_content += "|--------|------|----------|------|\n"
                    for item in action_items:
                        action_items_content += f"| {item.get('assignee', '')} | {item.get('task', '')} | {item.get('due_date', '')} | {item.get('status', '待处理')} |\n"
            except:
                action_items_content = "无行动项"
            
            # 解析关键点
            key_points_content = ""
            try:
                if meeting.get("key_points"):
                    key_points = json.loads(meeting.get("key_points"))
                    for point in key_points:
                        timestamp = point.get("timestamp", "")
                        speaker = point.get("speaker", "")
                        content = point.get("point", "")
                        key_points_content += f"- **[{timestamp}]** {speaker}: {content}\n"
            except:
                key_points_content = "无关键点"
            
            # 创建Markdown内容
            content = f"# {title} - 会议摘要\n\n"
            content += f"## 会议信息\n\n"
            content += f"- **日期**: {date}\n"
            content += f"- **参与者**: {participants}\n"
            content += f"- **项目**: {meeting.get('project_id', 'default')}\n\n"
            
            if agenda:
                content += f"## 议程\n\n{agenda}\n\n"
            
            if summary:
                content += f"## 总体摘要\n\n{summary}\n\n"
            
            if decisions:
                content += f"## 决策事项\n\n{decisions}\n\n"
            
            content += f"## 行动项\n\n{action_items_content}\n\n"
            content += f"## 关键点\n\n{key_points_content}\n\n"
            
            if transcription:
                content += f"## 完整转录\n\n```\n{transcription}\n```\n"
            
            # 保存文件
            export_dir = os.path.join(self.meeting_dir, "exports")
            os.makedirs(export_dir, exist_ok=True)
            
            file_path = os.path.join(export_dir, f"{meeting_id}_summary.md")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            # 如果需要HTML格式，转换Markdown为HTML
            if format.lower() == "html":
                try:
                    import markdown
                    html_content = markdown.markdown(content, extensions=['tables'])
                    html_path = os.path.join(export_dir, f"{meeting_id}_summary.html")
                    
                    # 添加基本样式
                    styled_html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="utf-8">
                        <title>{title} - 会议摘要</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }}
                            h1, h2, h3 {{ color: #2c3e50; }}
                            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                            th {{ background-color: #f2f2f2; }}
                            tr:nth-child(even) {{ background-color: #f9f9f9; }}
                            code {{ background-color: #f8f8f8; padding: 2px 5px; border-radius: 3px; }}
                            pre {{ background-color: #f8f8f8; padding: 10px; border-radius: 5px; overflow-x: auto; }}
                        </style>
                    </head>
                    <body>
                    {html_content}
                    </body>
                    </html>
                    """
                    
                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write(styled_html)
                    
                    file_path = html_path
                except ImportError:
                    logger.warning("markdown模块未安装，无法导出HTML格式")
                except Exception as e:
                    logger.exception(f"转换HTML失败: {str(e)}")
            
            return {
                "file_path": file_path,
                "format": format
            }
        
        except Exception as e:
            logger.exception(f"导出会议摘要失败: {meeting_id}, {str(e)}")
            return None

    def detect_project_from_title(self, title: str) -> Optional[str]:
        """
        从会议标题中检测项目ID
        
        Args:
            title: 会议标题
        
        Returns:
            项目ID
        """
        # 获取项目列表
        if self.mcp_client:
            try:
                projects = self.mcp_client.call("chatbot.list_projects")
                
                if projects and isinstance(projects, list):
                    # 按名称长度降序排序，优先匹配长名称
                    projects.sort(key=lambda x: len(x.get("name", "")), reverse=True)
                    
                    for project in projects:
                        project_name = project.get("name", "")
                        project_id = project.get("id", "")
                        
                        # 检查项目名称是否出现在标题中
                        if project_name and project_name.lower() in title.lower():
                            return project_id
            
            except Exception as e:
                logger.error(f"检测项目失败: {str(e)}")
        
        return "default"

def register_meeting_service(server):
    """
    注册会议服务
    
    Args:
        server: MCP服务器实例
    """
    # 创建会议服务实例
    from mcp.client import MCPClient
    mcp_client = MCPClient("127.0.0.1", server.config["mcp"]["server_port"])
    
    meeting_service = MeetingService(
        server.config, 
        server.db_path,
        mcp_client
    )
    
    # 注册服务方法
    server.register_service("meeting.create", meeting_service.create_meeting)
    server.register_service("meeting.update", meeting_service.update_meeting)
    server.register_service("meeting.get", meeting_service.get_meeting)
    server.register_service("meeting.list", meeting_service.list_meetings)
    server.register_service("meeting.delete", meeting_service.delete_meeting)
    server.register_service("meeting.process_transcription", meeting_service.process_transcription)
    server.register_service("meeting.detect_project", meeting_service.detect_project_from_title)
    server.register_service("meeting.generate_structured_summary", meeting_service.generate_structured_summary)
    server.register_service("meeting.list_tags", meeting_service.list_tags)
    server.register_service("meeting.export_summary", meeting_service.export_summary)
    
    logger.info("会议服务已注册")
