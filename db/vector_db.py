#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
向量数据库管理模块 - 提供向量数据库管理功能
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
import numpy as np

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("vector_db")

class VectorDatabaseManager:
    """向量数据库管理类，模拟LanceDB功能"""
    
    def __init__(self, db_path: str):
        """
        初始化向量数据库管理器
        
        Args:
            db_path: 数据库目录路径
        """
        self.db_path = db_path
        
        # 确保数据库目录存在
        os.makedirs(db_path, exist_ok=True)
        
        # 表映射
        self.tables = {}
    
    def init_db(self):
        """初始化向量数据库"""
        # 创建默认表
        self._create_table("documents")
        self._create_table("chunks")
        self._create_table("meetings")
        self._create_table("emails")
        
        logger.info("向量数据库初始化完成")
    
    def _create_table(self, table_name: str):
        """
        创建表
        
        Args:
            table_name: 表名
        """
        table_path = os.path.join(self.db_path, f"{table_name}.json")
        
        if not os.path.exists(table_path):
            # 创建空表
            with open(table_path, "w", encoding="utf-8") as f:
                json.dump({"vectors": []}, f)
            
            logger.info(f"创建向量表: {table_name}")
        
        # 加载表
        self.tables[table_name] = table_path
    
    def _load_table(self, table_name: str) -> Dict[str, Any]:
        """
        加载表
        
        Args:
            table_name: 表名
        
        Returns:
            表数据
        """
        if table_name not in self.tables:
            self._create_table(table_name)
        
        table_path = self.tables[table_name]
        
        with open(table_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _save_table(self, table_name: str, data: Dict[str, Any]):
        """
        保存表
        
        Args:
            table_name: 表名
            data: 表数据
        """
        if table_name not in self.tables:
            self._create_table(table_name)
        
        table_path = self.tables[table_name]
        
        with open(table_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_vector(self, table_name: str, vector_id: str, vector: List[float], metadata: Dict[str, Any] = None) -> bool:
        """
        添加向量
        
        Args:
            table_name: 表名
            vector_id: 向量ID
            vector: 向量数据
            metadata: 元数据
        
        Returns:
            是否成功
        """
        try:
            # 加载表
            table = self._load_table(table_name)
            
            # 检查向量是否已存在
            for i, item in enumerate(table["vectors"]):
                if item["id"] == vector_id:
                    # 更新向量
                    table["vectors"][i] = {
                        "id": vector_id,
                        "vector": vector,
                        "metadata": metadata or {}
                    }
                    self._save_table(table_name, table)
                    return True
            
            # 添加新向量
            table["vectors"].append({
                "id": vector_id,
                "vector": vector,
                "metadata": metadata or {}
            })
            
            # 保存表
            self._save_table(table_name, table)
            
            return True
        
        except Exception as e:
            logger.exception(f"添加向量失败: {table_name}/{vector_id}")
            return False
    
    def get_vector(self, table_name: str, vector_id: str) -> Optional[Dict[str, Any]]:
        """
        获取向量
        
        Args:
            table_name: 表名
            vector_id: 向量ID
        
        Returns:
            向量数据
        """
        try:
            # 加载表
            table = self._load_table(table_name)
            
            # 查找向量
            for item in table["vectors"]:
                if item["id"] == vector_id:
                    return item
            
            return None
        
        except Exception as e:
            logger.exception(f"获取向量失败: {table_name}/{vector_id}")
            return None
    
    def delete_vector(self, table_name: str, vector_id: str) -> bool:
        """
        删除向量
        
        Args:
            table_name: 表名
            vector_id: 向量ID
        
        Returns:
            是否成功
        """
        try:
            # 加载表
            table = self._load_table(table_name)
            
            # 查找并删除向量
            for i, item in enumerate(table["vectors"]):
                if item["id"] == vector_id:
                    table["vectors"].pop(i)
                    self._save_table(table_name, table)
                    return True
            
            return False
        
        except Exception as e:
            logger.exception(f"删除向量失败: {table_name}/{vector_id}")
            return False
    
    def search(self, table_name: str, query_vector: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索向量
        
        Args:
            table_name: 表名
            query_vector: 查询向量
            limit: 最大返回数量
        
        Returns:
            搜索结果
        """
        try:
            # 加载表
            table = self._load_table(table_name)
            
            # 如果表为空，返回空结果
            if not table["vectors"]:
                return []
            
            # 计算余弦相似度
            results = []
            query_vector_np = np.array(query_vector)
            
            for item in table["vectors"]:
                vector_np = np.array(item["vector"])
                
                # 计算余弦相似度
                similarity = np.dot(query_vector_np, vector_np) / (
                    np.linalg.norm(query_vector_np) * np.linalg.norm(vector_np)
                )
                
                results.append({
                    "id": item["id"],
                    "similarity": float(similarity),
                    "metadata": item["metadata"]
                })
            
            # 按相似度排序
            results.sort(key=lambda x: x["similarity"], reverse=True)
            
            # 限制返回数量
            return results[:limit]
        
        except Exception as e:
            logger.exception(f"搜索向量失败: {table_name}")
            return []
    
    def filter_search(self, table_name: str, query_vector: List[float], 
                     filter_func: callable, limit: int = 10) -> List[Dict[str, Any]]:
        """
        过滤搜索向量
        
        Args:
            table_name: 表名
            query_vector: 查询向量
            filter_func: 过滤函数，接受metadata参数，返回布尔值
            limit: 最大返回数量
        
        Returns:
            搜索结果
        """
        try:
            # 加载表
            table = self._load_table(table_name)
            
            # 如果表为空，返回空结果
            if not table["vectors"]:
                return []
            
            # 计算余弦相似度并过滤
            results = []
            query_vector_np = np.array(query_vector)
            
            for item in table["vectors"]:
                # 应用过滤函数
                if not filter_func(item["metadata"]):
                    continue
                
                vector_np = np.array(item["vector"])
                
                # 计算余弦相似度
                similarity = np.dot(query_vector_np, vector_np) / (
                    np.linalg.norm(query_vector_np) * np.linalg.norm(vector_np)
                )
                
                results.append({
                    "id": item["id"],
                    "similarity": float(similarity),
                    "metadata": item["metadata"]
                })
            
            # 按相似度排序
            results.sort(key=lambda x: x["similarity"], reverse=True)
            
            # 限制返回数量
            return results[:limit]
        
        except Exception as e:
            logger.exception(f"过滤搜索向量失败: {table_name}")
            return []
    
    def list_tables(self) -> List[str]:
        """
        列出所有表
        
        Returns:
            表名列表
        """
        return list(self.tables.keys())
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        获取表信息
        
        Args:
            table_name: 表名
        
        Returns:
            表信息
        """
        if table_name not in self.tables:
            return {"name": table_name, "exists": False, "vector_count": 0}
        
        # 加载表
        table = self._load_table(table_name)
        
        return {
            "name": table_name,
            "exists": True,
            "vector_count": len(table["vectors"])
        }
    
    def clear_table(self, table_name: str) -> bool:
        """
        清空表
        
        Args:
            table_name: 表名
        
        Returns:
            是否成功
        """
        try:
            # 创建空表
            self._save_table(table_name, {"vectors": []})
            return True
        
        except Exception as e:
            logger.exception(f"清空表失败: {table_name}")
            return False
