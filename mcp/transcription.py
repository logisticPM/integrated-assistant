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
import subprocess
import importlib.util

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
        
        # 检查Whisper是否已安装
        self.whisper_available = self._check_whisper()
        if not self.whisper_available:
            logger.warning("Whisper未安装，将使用模拟转录。请运行scripts/setup_whisper.py安装Whisper")
    
    def _check_whisper(self):
        """检查Whisper是否已安装"""
        try:
            # 检查whisper模块是否可用
            whisper_spec = importlib.util.find_spec("whisper")
            if whisper_spec is None:
                return False
            
            # 尝试导入whisper
            import whisper
            return True
        except ImportError:
            return False
    
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
            logger.info(f"开始转录任务: {task_id}, 音频: {audio_path}")
            
            # 检查是否可以使用Whisper
            if self.whisper_available:
                # 使用Whisper进行转录
                transcription_result = self._transcribe_with_whisper(audio_path)
            else:
                # 使用模拟转录
                logger.warning("使用模拟转录（Whisper未安装）")
                transcription_result = self._mock_transcription(task_id, meeting_id, audio_path)
            
            # 添加任务和会议信息
            transcription_result["task_id"] = task_id
            transcription_result["meeting_id"] = meeting_id
            transcription_result["audio_path"] = audio_path
            
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
            
            logger.info(f"转录任务完成: {task_id}")
            
            # 处理转录结果，生成摘要和关键点，并存储到对应的项目工作空间
            self._process_transcription_result(meeting_id, transcription_result)
            
        except Exception as e:
            logger.exception(f"转录任务失败: {task_id}, 错误: {str(e)}")
            
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
    
    def _transcribe_with_whisper(self, audio_path: str) -> Dict[str, Any]:
        """
        使用Whisper进行转录
        
        Args:
            audio_path: 音频文件路径
        
        Returns:
            转录结果
        """
        import whisper
        
        # 加载模型
        logger.info(f"加载Whisper模型: {self.whisper_model}")
        model = whisper.load_model(self.whisper_model)
        
        # 设置语言参数
        language = None if self.whisper_language == "auto" else self.whisper_language
        
        # 执行转录
        logger.info(f"开始转录音频: {audio_path}")
        start_time = time.time()
        
        # 使用Whisper进行转录
        result = model.transcribe(
            audio_path,
            language=language,
            verbose=True
        )
        
        end_time = time.time()
        logger.info(f"转录完成，耗时: {end_time - start_time:.2f}秒")
        
        # 格式化结果
        transcription_result = {
            "model": self.whisper_model,
            "language": self.whisper_language,
            "duration": result.get("duration", 0),
            "segments": result.get("segments", []),
            "text": result.get("text", ""),
            "processing_time": end_time - start_time
        }
        
        return transcription_result
    
    def _mock_transcription(self, task_id: str, meeting_id: str, audio_path: str) -> Dict[str, Any]:
        """
        模拟转录（当Whisper不可用时使用）
        
        Args:
            task_id: 任务ID
            meeting_id: 会议ID
            audio_path: 音频文件路径
        
        Returns:
            模拟的转录结果
        """
        # 模拟处理时间
        time.sleep(2)
        
        # 生成模拟的转录结果
        return {
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
    
    def _process_transcription_result(self, meeting_id: str, transcription_result: Dict[str, Any]):
        """
        处理转录结果，生成摘要和关键点，并存储到对应的项目工作空间
        
        Args:
            meeting_id: 会议ID
            transcription_result: 转录结果
        """
        try:
            # 使用MCP客户端调用会议服务
            from mcp.client import MCPClient
            mcp_client = MCPClient("127.0.0.1", self.config["mcp"]["server_port"])
            
            # 调用会议服务处理转录结果
            result = mcp_client.call("meeting.process_transcription", {
                "meeting_id": meeting_id,
                "transcription_result": transcription_result
            })
            
            if result:
                logger.info(f"会议转录结果处理成功: {meeting_id}")
            else:
                logger.error(f"会议转录结果处理失败: {meeting_id}")
                
        except Exception as e:
            logger.exception(f"处理转录结果失败: {meeting_id}, 错误: {str(e)}")
    
    def get_transcription_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取转录任务状态
        
        Args:
            task_id: 任务ID
        
        Returns:
            任务状态信息
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT meeting_id, audio_path, output_path, status, error, created_at, started_at, completed_at FROM transcription_tasks WHERE id = ?",
            (task_id,)
        )
        result = cursor.fetchone()
        
        conn.close()
        
        if not result:
            return {"error": "任务不存在"}
        
        meeting_id, audio_path, output_path, status, error, created_at, started_at, completed_at = result
        
        return {
            "task_id": task_id,
            "meeting_id": meeting_id,
            "audio_path": audio_path,
            "output_path": output_path,
            "status": status,
            "error": error,
            "created_at": created_at,
            "started_at": started_at,
            "completed_at": completed_at
        }
    
    def get_transcription_result(self, task_id: str) -> Dict[str, Any]:
        """
        获取转录结果
        
        Args:
            task_id: 任务ID
        
        Returns:
            转录结果
        """
        # 获取任务状态
        status = self.get_transcription_status(task_id)
        
        if "error" in status:
            return status
        
        if status["status"] != "completed":
            return {
                "error": f"任务尚未完成，当前状态: {status['status']}"
            }
        
        # 读取转录结果文件
        try:
            with open(status["output_path"], "r", encoding="utf-8") as f:
                result = json.load(f)
            
            return result
        except Exception as e:
            return {
                "error": f"读取转录结果失败: {str(e)}"
            }

def register_transcription_service(server):
    """
    注册转录服务
    
    Args:
        server: MCP服务器实例
    """
    # 创建转录服务实例
    transcription_service = TranscriptionService(
        server.config, 
        server.db_path
    )
    
    # 注册服务方法
    server.register_method("transcription.start", transcription_service.start_transcription)
    server.register_method("transcription.get_status", transcription_service.get_transcription_status)
    server.register_method("transcription.get_result", transcription_service.get_transcription_result)
    server.register_method("transcription.process_result", transcription_service._process_transcription_result)
    
    logger.info("转录服务已注册")
