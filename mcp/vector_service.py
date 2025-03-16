#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
向量数据库服务模块 - 提供文档向量化和检索服务
"""

import os
import json
import time
import logging
import sqlite3
from typing import Dict, Any, List, Optional
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("vector_service")

class VectorDatabaseService:
    """向量数据库服务类，处理文档向量化和检索"""
    
    def __init__(self, config: Dict[str, Any], db_path: str, vector_db_path: str):
        """
        初始化向量数据库服务
        
        Args:
            config: 服务配置
            db_path: SQLite数据库路径
            vector_db_path: 向量数据库路径
        """
        self.config = config
        self.db_path = db_path
        self.vector_db_path = vector_db_path
        self.docs_dir = config["knowledge"]["docs_dir"]
        self.chunk_size = config["knowledge"]["chunk_size"]
        self.chunk_overlap = config["knowledge"]["chunk_overlap"]
        
        # 确保目录存在
        os.makedirs(self.docs_dir, exist_ok=True)
        os.makedirs(self.vector_db_path, exist_ok=True)
        
        # 初始化数据库
        self._init_db()
        
        # 初始化LanceDB（模拟）
        self._init_lancedb()
    
    def _init_db(self):
        """初始化SQLite数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建文档表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            category TEXT,
            file_path TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at REAL NOT NULL,
            processed_at REAL
        )
        ''')
        
        # 创建文档标签表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS document_tags (
            document_id TEXT,
            tag TEXT,
            PRIMARY KEY (document_id, tag),
            FOREIGN KEY (document_id) REFERENCES documents (id)
        )
        ''')
        
        # 创建文档块表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS document_chunks (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            content TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            vector_id TEXT,
            created_at REAL NOT NULL,
            FOREIGN KEY (document_id) REFERENCES documents (id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def _init_lancedb(self):
        """初始化LanceDB（模拟）"""
        # 实际项目中，这里应该初始化LanceDB连接
        # 由于这是一个模拟实现，我们只记录日志
        logger.info("初始化LanceDB向量数据库（模拟）")
    
    def create_document(self, title: str, category: str, tags: List[str], file_path: str) -> str:
        """
        创建文档记录
        
        Args:
            title: 文档标题
            category: 文档类别
            tags: 文档标签
            file_path: 文件路径
        
        Returns:
            文档ID
        """
        # 生成文档ID
        document_id = f"doc_{int(time.time())}_{title.replace(' ', '_')}"
        
        # 确保文件存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 将文件复制到文档目录
        target_path = os.path.join(self.docs_dir, os.path.basename(file_path))
        
        # 如果文件路径不同，则复制文件
        if file_path != target_path:
            import shutil
            shutil.copy2(file_path, target_path)
        
        # 保存文档信息到数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO documents (id, title, category, file_path, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (document_id, title, category, target_path, "pending", time.time())
        )
        
        # 保存文档标签
        for tag in tags:
            cursor.execute(
                "INSERT INTO document_tags (document_id, tag) VALUES (?, ?)",
                (document_id, tag)
            )
        
        conn.commit()
        conn.close()
        
        return document_id
    
    def process_document(self, document_id: str) -> bool:
        """
        处理文档（分块和向量化）
        
        Args:
            document_id: 文档ID
        
        Returns:
            是否成功
        """
        # 获取文档信息
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT title, file_path FROM documents WHERE id = ?", (document_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise ValueError(f"文档不存在: {document_id}")
        
        title, file_path = result
        
        # 更新文档状态为处理中
        cursor.execute(
            "UPDATE documents SET status = ? WHERE id = ?",
            ("processing", document_id)
        )
        conn.commit()
        
        try:
            # 读取文档内容
            file_content = self._read_file_content(file_path)
            
            # 分块
            chunks = self._split_text(file_content)
            
            # 保存分块
            for i, chunk in enumerate(chunks):
                chunk_id = f"{document_id}_chunk_{i}"
                
                cursor.execute(
                    "INSERT INTO document_chunks (id, document_id, content, chunk_index, created_at) VALUES (?, ?, ?, ?, ?)",
                    (chunk_id, document_id, chunk, i, time.time())
                )
            
            # 更新文档状态为已处理
            cursor.execute(
                "UPDATE documents SET status = ?, processed_at = ? WHERE id = ?",
                ("processed", time.time(), document_id)
            )
            conn.commit()
            
            # 向量化分块（实际项目中应该调用LLM服务获取嵌入向量）
            self._vectorize_chunks(document_id)
            
            logger.info(f"文档处理完成: {document_id}, 分块数: {len(chunks)}")
            return True
        
        except Exception as e:
            logger.exception(f"文档处理失败: {document_id}")
            
            # 更新文档状态为失败
            cursor.execute(
                "UPDATE documents SET status = ? WHERE id = ?",
                ("failed", document_id)
            )
            conn.commit()
            
            return False
        
        finally:
            conn.close()
    
    def _read_file_content(self, file_path: str) -> str:
        """
        读取文件内容
        
        Args:
            file_path: 文件路径
        
        Returns:
            文件内容
        """
        # 根据文件类型选择不同的读取方法
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.java', '.c', '.cpp']:
            # 文本文件
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        
        elif file_ext in ['.pdf']:
            # PDF文件（模拟）
            return f"这是从PDF文件 {os.path.basename(file_path)} 中提取的文本内容。实际项目中应该使用PyPDF2或pdfplumber等库提取文本。"
        
        elif file_ext in ['.docx', '.doc']:
            # Word文件（模拟）
            return f"这是从Word文件 {os.path.basename(file_path)} 中提取的文本内容。实际项目中应该使用python-docx等库提取文本。"
        
        else:
            # 不支持的文件类型
            return f"不支持的文件类型: {file_ext}"
    
    def _split_text(self, text: str) -> List[str]:
        """
        将文本分块
        
        Args:
            text: 输入文本
        
        Returns:
            文本块列表
        """
        # 简单的分块实现，实际项目中应该使用更复杂的分块策略
        chunks = []
        
        # 按段落分割
        paragraphs = text.split('\n\n')
        
        current_chunk = ""
        for paragraph in paragraphs:
            # 如果段落加上当前块不超过块大小，则添加到当前块
            if len(current_chunk) + len(paragraph) < self.chunk_size:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += paragraph
            else:
                # 如果当前块不为空，则添加到块列表
                if current_chunk:
                    chunks.append(current_chunk)
                
                # 如果段落大小超过块大小，则进一步分割
                if len(paragraph) > self.chunk_size:
                    # 按句子分割
                    sentences = paragraph.replace('. ', '.\n').split('\n')
                    
                    current_chunk = ""
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) < self.chunk_size:
                            if current_chunk:
                                current_chunk += " "
                            current_chunk += sentence
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                            current_chunk = sentence
                else:
                    current_chunk = paragraph
        
        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _vectorize_chunks(self, document_id: str):
        """
        向量化文档块
        
        Args:
            document_id: 文档ID
        """
        # 获取文档块
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, content FROM document_chunks WHERE document_id = ? ORDER BY chunk_index", (document_id,))
        chunks = cursor.fetchall()
        
        # 模拟向量化过程
        for chunk_id, content in chunks:
            # 生成向量ID
            vector_id = f"vector_{chunk_id}"
            
            # 更新向量ID
            cursor.execute(
                "UPDATE document_chunks SET vector_id = ? WHERE id = ?",
                (vector_id, chunk_id)
            )
            
            # 实际项目中，这里应该调用LLM服务获取嵌入向量，并存储到LanceDB
            # 这里只是模拟
            logger.info(f"向量化文档块: {chunk_id}")
        
        conn.commit()
        conn.close()
    
    def search(self, query: str, category: str = None, tags: List[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索知识库
        
        Args:
            query: 搜索查询
            category: 文档类别过滤
            tags: 标签过滤
            limit: 最大返回数量
        
        Returns:
            搜索结果列表
        """
        # 实际项目中，这里应该调用LLM服务获取查询的嵌入向量，然后在LanceDB中进行相似度搜索
        # 这里使用模拟的搜索结果
        
        # 构建SQL查询
        sql = """
        SELECT dc.id, d.id as document_id, d.title, d.category, dc.content, dc.chunk_index
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE d.status = 'processed'
        """
        
        params = []
        
        if category:
            sql += " AND d.category = ?"
            params.append(category)
        
        if tags and len(tags) > 0:
            placeholders = ", ".join(["?"] * len(tags))
            sql += f" AND d.id IN (SELECT document_id FROM document_tags WHERE tag IN ({placeholders}) GROUP BY document_id HAVING COUNT(DISTINCT tag) = ?)"
            params.extend(tags)
            params.append(len(tags))
        
        sql += " ORDER BY dc.created_at DESC LIMIT ?"
        params.append(limit)
        
        # 执行查询
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(sql, params)
        results = cursor.fetchall()
        conn.close()
        
        # 格式化搜索结果
        search_results = []
        for row in results:
            chunk_id, document_id, title, category, content, chunk_index = row
            
            # 计算相关度分数（模拟）
            # 实际项目中，这应该是向量相似度分数
            import random
            relevance = random.uniform(0.5, 0.95)
            
            # 提取相关段落
            snippet = self._extract_snippet(content, query)
            
            search_results.append({
                "chunk_id": chunk_id,
                "document_id": document_id,
                "title": title,
                "category": category,
                "snippet": snippet,
                "relevance": relevance
            })
        
        # 按相关度排序
        search_results.sort(key=lambda x: x["relevance"], reverse=True)
        
        return search_results
    
    def _extract_snippet(self, content: str, query: str) -> str:
        """
        从内容中提取与查询相关的片段
        
        Args:
            content: 文档内容
            query: 搜索查询
        
        Returns:
            相关片段
        """
        # 简单的片段提取实现
        # 实际项目中应该使用更复杂的算法
        
        # 如果内容较短，直接返回
        if len(content) < 200:
            return content
        
        # 查找查询词在内容中的位置
        query_words = query.lower().split()
        content_lower = content.lower()
        
        best_pos = 0
        best_score = 0
        
        # 遍历内容，找到最相关的位置
        for i in range(0, len(content) - 100, 50):
            window = content_lower[i:i+200]
            score = sum(1 for word in query_words if word in window)
            
            if score > best_score:
                best_score = score
                best_pos = i
        
        # 提取片段
        start = max(0, best_pos)
        end = min(len(content), start + 200)
        
        # 调整开始位置到句子边界
        if start > 0:
            sentence_start = content.rfind('. ', 0, start)
            if sentence_start != -1:
                start = sentence_start + 2
        
        # 调整结束位置到句子边界
        if end < len(content):
            sentence_end = content.find('. ', end)
            if sentence_end != -1:
                end = sentence_end + 1
        
        snippet = content[start:end].strip()
        
        # 如果片段不是以句号结尾，添加省略号
        if not snippet.endswith('.'):
            snippet += '...'
        
        # 如果片段不是以大写字母开头，添加省略号
        if not snippet[0].isupper():
            snippet = '...' + snippet
        
        return snippet
    
    def get_chunk(self, chunk_id: str) -> Dict[str, Any]:
        """
        获取文档块内容
        
        Args:
            chunk_id: 块ID
        
        Returns:
            块内容
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT dc.content, dc.chunk_index, d.id, d.title, d.category
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE dc.id = ?
        """, (chunk_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            raise ValueError(f"文档块不存在: {chunk_id}")
        
        content, chunk_index, document_id, title, category = result
        
        return {
            "id": chunk_id,
            "document_id": document_id,
            "title": title,
            "category": category,
            "content": content,
            "chunk_index": chunk_index
        }
    
    def list_documents(self, category: str = None, status: str = None) -> List[Dict[str, Any]]:
        """
        列出文档
        
        Args:
            category: 类别过滤
            status: 状态过滤
        
        Returns:
            文档列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        sql = "SELECT id, title, category, file_path, status, created_at, processed_at FROM documents"
        params = []
        
        conditions = []
        if category:
            conditions.append("category = ?")
            params.append(category)
        
        if status:
            conditions.append("status = ?")
            params.append(status)
        
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        
        sql += " ORDER BY created_at DESC"
        
        cursor.execute(sql, params)
        results = cursor.fetchall()
        
        documents = []
        for row in results:
            doc_id, title, category, file_path, status, created_at, processed_at = row
            
            # 获取文档标签
            cursor.execute("SELECT tag FROM document_tags WHERE document_id = ?", (doc_id,))
            tags = [tag[0] for tag in cursor.fetchall()]
            
            documents.append({
                "id": doc_id,
                "title": title,
                "category": category,
                "file_path": file_path,
                "status": status,
                "tags": tags,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at)),
                "processed_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(processed_at)) if processed_at else None
            })
        
        conn.close()
        return documents
    
    def get_document(self, document_id: str) -> Dict[str, Any]:
        """
        获取文档详情
        
        Args:
            document_id: 文档ID
        
        Returns:
            文档详情
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, title, category, file_path, status, created_at, processed_at FROM documents WHERE id = ?",
            (document_id,)
        )
        
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise ValueError(f"文档不存在: {document_id}")
        
        doc_id, title, category, file_path, status, created_at, processed_at = result
        
        # 获取文档标签
        cursor.execute("SELECT tag FROM document_tags WHERE document_id = ?", (doc_id,))
        tags = [tag[0] for tag in cursor.fetchall()]
        
        # 获取文档块数量
        cursor.execute("SELECT COUNT(*) FROM document_chunks WHERE document_id = ?", (doc_id,))
        chunk_count = cursor.fetchone()[0]
        
        document = {
            "id": doc_id,
            "title": title,
            "category": category,
            "file_path": file_path,
            "status": status,
            "tags": tags,
            "chunk_count": chunk_count,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at)),
            "processed_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(processed_at)) if processed_at else None
        }
        
        conn.close()
        return document
    
    def delete_document(self, document_id: str) -> bool:
        """
        删除文档
        
        Args:
            document_id: 文档ID
        
        Returns:
            是否成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取文档信息
        cursor.execute("SELECT file_path FROM documents WHERE id = ?", (document_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise ValueError(f"文档不存在: {document_id}")
        
        file_path = result[0]
        
        try:
            # 删除文档块
            cursor.execute("DELETE FROM document_chunks WHERE document_id = ?", (document_id,))
            
            # 删除文档标签
            cursor.execute("DELETE FROM document_tags WHERE document_id = ?", (document_id,))
            
            # 删除文档
            cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            
            conn.commit()
            
            # 删除文件
            if os.path.exists(file_path) and os.path.isfile(file_path):
                os.remove(file_path)
            
            # 实际项目中，这里应该从LanceDB中删除相应的向量
            
            return True
        
        except Exception as e:
            logger.exception(f"删除文档失败: {document_id}")
            conn.rollback()
            return False
        
        finally:
            conn.close()
    
    def chat(self, message: str, history: List[tuple], temperature: float = 0.7, category: str = None) -> str:
        """
        知识库聊天
        
        Args:
            message: 用户消息
            history: 聊天历史
            temperature: 温度参数
            category: 类别过滤
        
        Returns:
            回复消息
        """
        # 搜索相关文档
        search_results = self.search(message, category=category, limit=5)
        
        if not search_results:
            return "我没有找到相关的信息。请尝试其他问题或提供更多细节。"
        
        # 构建上下文
        context = ""
        for i, result in enumerate(search_results):
            context += f"[文档{i+1}] {result['title']}\n{result['snippet']}\n\n"
        
        # 调用LLM服务回答问题
        # 实际项目中，这里应该调用LLM服务
        # 这里使用模拟的回答
        if "项目" in message and "进度" in message:
            return "根据知识库中的信息，项目当前进度约为60%。测试团队已经报告了几个关键bug，团队计划在下周五前完成初步原型。"
        elif "会议" in message:
            return "根据会议记录，下一次评审会议定在周五下午3点。会议将讨论当前项目进度和解决方案评估。"
        elif "文档" in message:
            return "知识库中有多份技术文档，包括项目规格说明书、API文档和用户手册。您需要哪一类文档的具体信息？"
        else:
            return f"我已经查询了知识库，找到了一些相关信息。根据文档内容，我认为：{search_results[0]['snippet']}"

def register_vector_service(server):
    """
    注册向量数据库服务
    
    Args:
        server: MCP服务器实例
    """
    # 创建向量数据库服务实例
    service = VectorDatabaseService(
        server.config,
        server.config["db"]["sqlite_path"],
        server.config["db"]["vector_db_path"]
    )
    
    # 注册方法
    server.register_module("knowledge", {
        "create_document": service.create_document,
        "process_document": service.process_document,
        "search": service.search,
        "get_chunk": service.get_chunk,
        "list_documents": service.list_documents,
        "get_document": service.get_document,
        "delete_document": service.delete_document,
        "chat": service.chat
    })
