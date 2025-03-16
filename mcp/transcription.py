#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
转录服务模块 - 提供音频转文本处理服务
"""

import os
import json
import time
import logging
from typing import Dict, Any, List
import sqlite3
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("transcription_service")

class TranscriptionService:
    """转录服务类，处理音频转文本"""
    
    def __init__(self, config: Dict[str, Any], db_path: str):
        """
        初始化转录服务
        
        Args:
            config: 服务配置
            db_path: 数据库路径
        """
        self.config = config
        self.db_path = db_path
        self.audio_dir = config["meeting"]["audio_dir"]
        self.transcription_dir = config["meeting"]["transcription_dir"]
        self.whisper_model = config["meeting"]["whisper"]["model"]
        self.whisper_language = config["meeting"]["whisper"]["language"]
        
        # 确保目录存在
        os.makedirs(self.audio_dir, exist_ok=True)
        os.makedirs(self.transcription_dir, exist_ok=True)
        
        # 初始化数据库
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建转录任务表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transcription_tasks (
            id TEXT PRIMARY KEY,
            meeting_id TEXT NOT NULL,
            audio_path TEXT NOT NULL,
            output_path TEXT,
            status TEXT NOT NULL,
            error TEXT,
            created_at REAL NOT NULL,
            started_at REAL,
            completed_at REAL,
            FOREIGN KEY (meeting_id) REFERENCES meetings (id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def start_transcription(self, meeting_id: str, audio_path: str) -> str:
        """
        开始转录任务
        
        Args:
            meeting_id: 会议ID
            audio_path: 音频文件路径
        
        Returns:
            任务ID
        """
        # 生成任务ID
        task_id = f"transcription_{int(time.time())}_{meeting_id}"
        
        # 确保音频文件存在
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        # 确定输出路径
        output_filename = f"{meeting_id}_transcription.json"
        output_path = os.path.join(self.transcription_dir, output_filename)
        
        # 保存任务信息到数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO transcription_tasks (id, meeting_id, audio_path, output_path, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (task_id, meeting_id, audio_path, output_path, "pending", time.time())
        )
        
        conn.commit()
        conn.close()
        
        # 启动转录处理（实际项目中应该在后台线程中执行）
        self._process_transcription(task_id)
        
        return task_id
    
    def _process_transcription(self, task_id: str):
        """
        处理转录任务
        
        Args:
            task_id: 任务ID
        """
        # 获取任务信息
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT meeting_id, audio_path, output_path FROM transcription_tasks WHERE id = ?", (task_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            logger.error(f"任务不存在: {task_id}")
            return
        
        meeting_id, audio_path, output_path = result
        
        # 更新任务状态为进行中
        cursor.execute(
            "UPDATE transcription_tasks SET status = ?, started_at = ? WHERE id = ?",
            ("processing", time.time(), task_id)
        )
        conn.commit()
        conn.close()
        
        try:
            # 实际项目中，这里应该调用Whisper API或本地Whisper模型
            # 这里使用模拟的转录结果
            logger.info(f"开始转录任务: {task_id}, 音频: {audio_path}")
            
            # 模拟转录过程
            time.sleep(2)  # 模拟处理时间
            
            # 生成模拟的转录结果
            transcription_result = {
                "task_id": task_id,
                "meeting_id": meeting_id,
                "audio_path": audio_path,
                "model": self.whisper_model,
                "language": self.whisper_language,
                "duration": 120.5,  # 模拟音频时长
                "segments": [
                    {
                        "id": 0,
                        "start": 0.0,
                        "end": 10.5,
                        "text": "这是一个模拟的转录结果，第一段。"
                    },
                    {
                        "id": 1,
                        "start": 10.5,
                        "end": 20.0,
                        "text": "这是模拟转录的第二段内容。"
                    },
                    {
                        "id": 2,
                        "start": 20.0,
                        "end": 30.5,
                        "text": "这是最后一段模拟转录内容。"
                    }
                ],
                "text": "这是一个模拟的转录结果，第一段。这是模拟转录的第二段内容。这是最后一段模拟转录内容。"
            }
            
            # 保存转录结果
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(transcription_result, f, ensure_ascii=False, indent=2)
            
            # 更新任务状态为完成
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE transcription_tasks SET status = ?, completed_at = ? WHERE id = ?",
                ("completed", time.time(), task_id)
            )
            
            # 更新会议记录的转录状态
            cursor.execute(
                "UPDATE meetings SET transcription_status = ?, transcription_path = ? WHERE id = ?",
                ("completed", output_path, meeting_id)
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"转录任务完成: {task_id}, 输出: {output_path}")
        
        except Exception as e:
            logger.exception(f"转录任务失败: {task_id}")
            
            # 更新任务状态为失败
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE transcription_tasks SET status = ?, error = ?, completed_at = ? WHERE id = ?",
                ("failed", str(e), time.time(), task_id)
            )
            
            # 更新会议记录的转录状态
            cursor.execute(
                "UPDATE meetings SET transcription_status = ? WHERE id = ?",
                ("failed", meeting_id)
            )
            
            conn.commit()
            conn.close()
    
    def get_transcription(self, meeting_id: str) -> Dict[str, Any]:
        """
        获取转录结果
        
        Args:
            meeting_id: 会议ID
        
        Returns:
            转录结果
        """
        # 查询转录任务
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT output_path, status FROM transcription_tasks WHERE meeting_id = ? ORDER BY created_at DESC LIMIT 1",
            (meeting_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            return {"status": "not_found", "text": ""}
        
        output_path, status = result
        
        if status != "completed":
            return {"status": status, "text": ""}
        
        # 读取转录结果
        if os.path.exists(output_path):
            with open(output_path, "r", encoding="utf-8") as f:
                transcription = json.load(f)
            
            return {
                "status": "completed",
                "text": transcription.get("text", ""),
                "segments": transcription.get("segments", []),
                "duration": transcription.get("duration", 0)
            }
        else:
            return {"status": "file_missing", "text": ""}
    
    def list_transcription_tasks(self, status: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        列出转录任务
        
        Args:
            status: 任务状态过滤
            limit: 最大返回数量
        
        Returns:
            任务列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT id, meeting_id, audio_path, output_path, status, error, created_at, started_at, completed_at FROM transcription_tasks"
        params = []
        
        if status:
            query += " WHERE status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        tasks = []
        for row in results:
            tasks.append({
                "id": row[0],
                "meeting_id": row[1],
                "audio_path": row[2],
                "output_path": row[3],
                "status": row[4],
                "error": row[5],
                "created_at": row[6],
                "started_at": row[7],
                "completed_at": row[8]
            })
        
        return tasks

def register_transcription_service(server):
    """
    注册转录服务
    
    Args:
        server: MCP服务器实例
    """
    # 创建转录服务实例
    service = TranscriptionService(server.config, server.config["db"]["sqlite_path"])
    
    # 注册方法
    server.register_module("transcription", {
        "start": service.start_transcription,
        "get": service.get_transcription,
        "list_tasks": service.list_transcription_tasks
    })
