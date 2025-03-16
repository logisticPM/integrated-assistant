#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库管理模块 - 提供SQLite数据库管理功能
"""

import os
import sqlite3
import logging
from typing import Dict, Any, List, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db_manager")

class DatabaseManager:
    """SQLite数据库管理类"""
    
    def __init__(self, db_path: str):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        
        # 确保数据库目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    def init_db(self):
        """初始化数据库表结构"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 创建会议表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS meetings (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            duration INTEGER,
            participants TEXT,
            audio_path TEXT,
            transcription_path TEXT,
            summary TEXT,
            transcription_status TEXT,
            created_at REAL NOT NULL
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
        
        # 创建会议关键点表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS meeting_key_points (
            id TEXT PRIMARY KEY,
            meeting_id TEXT NOT NULL,
            timestamp TEXT,
            content TEXT NOT NULL,
            created_at REAL NOT NULL,
            FOREIGN KEY (meeting_id) REFERENCES meetings (id)
        )
        ''')
        
        # 创建设置表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at REAL NOT NULL
        )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("数据库初始化完成")
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def execute_query(self, query: str, params: tuple = ()):
        """
        执行SQL查询
        
        Args:
            query: SQL查询语句
            params: 查询参数
        
        Returns:
            查询结果
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(query, params)
        result = cursor.fetchall()
        
        conn.close()
        return result
    
    def execute_update(self, query: str, params: tuple = ()):
        """
        执行SQL更新
        
        Args:
            query: SQL更新语句
            params: 更新参数
        
        Returns:
            受影响的行数
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(query, params)
        affected_rows = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return affected_rows
    
    def execute_transaction(self, queries: List[Dict[str, Any]]):
        """
        执行事务
        
        Args:
            queries: 查询列表，每个查询为字典，包含query和params
        
        Returns:
            是否成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            for query_dict in queries:
                cursor.execute(query_dict["query"], query_dict["params"])
            
            conn.commit()
            success = True
        except Exception as e:
            conn.rollback()
            logger.exception("事务执行失败")
            success = False
        finally:
            conn.close()
        
        return success
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        获取设置
        
        Args:
            key: 设置键
            default: 默认值
        
        Returns:
            设置值
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return result[0]
        else:
            return default
    
    def set_setting(self, key: str, value: Any) -> bool:
        """
        设置设置
        
        Args:
            key: 设置键
            value: 设置值
        
        Returns:
            是否成功
        """
        import time
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                (key, str(value), time.time())
            )
            
            conn.commit()
            success = True
        except Exception as e:
            conn.rollback()
            logger.exception(f"设置设置失败: {key}")
            success = False
        finally:
            conn.close()
        
        return success
