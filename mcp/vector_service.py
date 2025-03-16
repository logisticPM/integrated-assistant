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
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import importlib.util

# 导入知识库相关模块
from mcp.docloader import load_document
from mcp.text_splitter import get_text_splitter
from mcp.embedder import get_embedder

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
        
        # 知识库配置
        knowledge_config = config.get("knowledge", {})
        self.docs_dir = knowledge_config.get("docs_dir", "./data/documents")
        self.chunk_size = knowledge_config.get("chunk_size", 1000)
        self.chunk_overlap = knowledge_config.get("chunk_overlap", 200)
        self.embedding_model = knowledge_config.get("embedding_model", "all-MiniLM-L6-v2")
        self.splitter_type = knowledge_config.get("splitter_type", "smart")
        self.supported_extensions = knowledge_config.get("supported_extensions", 
                                                        [".txt", ".md", ".pdf", ".docx", ".html", ".csv"])
        self.use_mock_embedder = knowledge_config.get("use_mock_embedder", False)
        self.vector_search_top_k = knowledge_config.get("vector_search_top_k", 5)
        
        # 确保目录存在
        os.makedirs(self.docs_dir, exist_ok=True)
        os.makedirs(self.vector_db_path, exist_ok=True)
        
        # 初始化数据库
        self._init_db()
        
        # 初始化向量数据库
        self._init_vector_db()
        
        # 初始化文本分块器
        self.text_splitter = get_text_splitter(
            splitter_type=self.splitter_type,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        
        # 初始化嵌入器
        self.embedder = get_embedder(
            model_name=self.embedding_model,
            use_mock=self.use_mock_embedder
        )
        
        logger.info(f"向量数据库服务初始化完成，使用嵌入模型: {self.embedding_model}")
    
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
            processed_at REAL,
            project_id TEXT DEFAULT "default"
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
    
    def _init_vector_db(self):
        """初始化向量数据库"""
        # 实际项目中，这里应该初始化向量数据库连接
        # 由于这是一个模拟实现，我们只记录日志
        logger.info("初始化向量数据库（模拟）")
    
    def create_document(self, title: str, category: str, tags: List[str], file_path: str, project_id: str = "default") -> str:
        """
        创建文档记录
        
        Args:
            title: 文档标题
            category: 文档类别
            tags: 文档标签
            file_path: 文件路径
            project_id: 项目ID
        
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
            "INSERT INTO documents (id, title, category, file_path, status, created_at, project_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (document_id, title, category, target_path, "pending", time.time(), project_id)
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
            # 使用文档加载器读取文档内容
            logger.info(f"开始处理文档: {title} ({file_path})")
            file_content = load_document(file_path)
            
            # 使用文本分块器分块
            logger.info(f"使用 {self.splitter_type} 分块器进行文本分块")
            chunks = self.text_splitter.split_text(file_content)
            
            # 保存分块
            logger.info(f"保存 {len(chunks)} 个文本块")
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
            
            # 向量化分块
            self._vectorize_chunks(document_id)
            
            logger.info(f"文档处理完成: {document_id}, 分块数: {len(chunks)}")
            return True
        
        except Exception as e:
            logger.exception(f"文档处理失败: {document_id}, 错误: {str(e)}")
            
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
        读取文件内容（已弃用，使用docloader模块代替）
        
        Args:
            file_path: 文件路径
        
        Returns:
            文件内容
        """
        # 使用文档加载器读取文件内容
        return load_document(file_path)
    
    def _split_text(self, text: str) -> List[str]:
        """
        将文本分块（已弃用，使用text_splitter模块代替）
        
        Args:
            text: 输入文本
        
        Returns:
            文本块列表
        """
        # 使用文本分块器分块
        return self.text_splitter.split_text(text)
    
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
        
        if not chunks:
            logger.warning(f"未找到文档块: {document_id}")
            conn.close()
            return
        
        try:
            # 提取文本内容
            chunk_ids = [chunk_id for chunk_id, _ in chunks]
            texts = [content for _, content in chunks]
            
            # 使用嵌入器生成向量
            logger.info(f"开始向量化 {len(texts)} 个文本块")
            embeddings = self.embedder.embed(texts)
            
            # 保存向量到数据库
            for i, (chunk_id, embedding) in enumerate(zip(chunk_ids, embeddings)):
                # 生成向量ID
                vector_id = f"vector_{chunk_id}"
                
                # 更新向量ID
                cursor.execute(
                    "UPDATE document_chunks SET vector_id = ? WHERE id = ?",
                    (vector_id, chunk_id)
                )
                
                # 实际项目中，这里应该将向量存储到向量数据库中
                # 这里我们仅记录日志
                logger.info(f"向量化文档块 ({i+1}/{len(texts)}): {chunk_id}")
            
            conn.commit()
            logger.info(f"文档块向量化完成: {document_id}")
            
        except Exception as e:
            logger.exception(f"向量化文档块时出错: {str(e)}")
        finally:
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
        if not query.strip():
            logger.warning("搜索查询为空")
            return []
        
        try:
            # 获取查询的嵌入向量
            logger.info(f"生成查询的嵌入向量: {query}")
            query_embedding = self.embedder.embed([query])[0]
            
            # 构建SQL查询获取所有文档块
            sql = """
            SELECT dc.id, d.id as document_id, d.title, d.category, dc.content, dc.chunk_index, dc.vector_id
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
            
            # 执行查询
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(sql, params)
            results = cursor.fetchall()
            
            if not results:
                logger.info("未找到匹配的文档块")
                conn.close()
                return []
            
            # 计算向量相似度并排序
            search_results = []
            for row in results:
                chunk_id, document_id, title, category, content, chunk_index, vector_id = row
                
                # 提取相关段落
                snippet = self._extract_snippet(content, query)
                
                # 计算相似度分数
                relevance = self._calculate_similarity(query_embedding, chunk_id)
                
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
            
            # 限制返回数量
            search_results = search_results[:limit]
            
            logger.info(f"搜索完成，找到 {len(search_results)} 个结果")
            conn.close()
            return search_results
            
        except Exception as e:
            logger.exception(f"搜索时出错: {str(e)}")
            return []
    
    def _calculate_similarity(self, query_embedding: List[float], chunk_id: str) -> float:
        """
        计算查询向量与文档块向量的相似度
        
        Args:
            query_embedding: 查询嵌入向量
            chunk_id: 文档块ID
        
        Returns:
            相似度分数
        """
        try:
            # 实际项目中，这里应该从向量数据库中检索向量并计算相似度
            # 由于这是一个模拟实现，我们使用基于chunk_id的伪随机相似度
            import numpy as np
            import hashlib
            
            # 使用chunk_id的哈希值作为随机种子
            seed = int(hashlib.md5(chunk_id.encode()).hexdigest(), 16) % (2**32)
            np.random.seed(seed)
            
            # 生成一个0.5到0.95之间的随机相似度
            similarity = np.random.uniform(0.5, 0.95)
            
            return float(similarity)
        except Exception as e:
            logger.exception(f"计算相似度时出错: {str(e)}")
            return 0.0
    
    def _extract_snippet(self, content: str, query: str) -> str:
        """
        从内容中提取与查询相关的片段
        
        Args:
            content: 文档内容
            query: 搜索查询
        
        Returns:
            相关片段
        """
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
            # 尝试找到前一个句号或换行符
            for i in range(start, max(0, start-50), -1):
                if content[i] in ['.', '!', '?', '\n']:
                    start = i + 1
                    break
        
        # 调整结束位置到句子边界
        if end < len(content):
            # 尝试找到下一个句号或换行符
            for i in range(end, min(len(content), end+50)):
                if content[i] in ['.', '!', '?', '\n']:
                    end = i + 1
                    break
        
        snippet = content[start:end].strip()
        
        # 如果片段太短，返回原始内容的前200个字符
        if len(snippet) < 50:
            return content[:200] + "..."
        
        return snippet + ("..." if end < len(content) else "")
    
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
    
    def search_documents(self, query: str, project_id: str = None, category: str = None, 
                        tags: List[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索文档
        
        Args:
            query: 搜索查询
            project_id: 项目ID过滤
            category: 类别过滤
            tags: 标签过滤
            limit: 最大返回数量
        
        Returns:
            文档列表
        """
        try:
            # 获取文档列表
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 构建查询条件
            conditions = ["status = 'processed'"]
            params = []
            
            if project_id:
                conditions.append("project_id = ?")
                params.append(project_id)
            
            if category:
                conditions.append("category = ?")
                params.append(category)
            
            # 执行查询
            query_sql = f"SELECT * FROM documents WHERE {' AND '.join(conditions)} ORDER BY created_at DESC"
            cursor.execute(query_sql, params)
            
            documents = []
            for row in cursor.fetchall():
                document = dict(row)
                
                # 如果有标签过滤，检查文档是否包含所有指定标签
                if tags:
                    cursor.execute(
                        f"SELECT COUNT(*) FROM document_tags WHERE document_id = ? AND tag IN ({','.join(['?'] * len(tags))})",
                        [document['id']] + tags
                    )
                    tag_count = cursor.fetchone()[0]
                    if tag_count < len(tags):
                        continue
                
                # 获取文档标签
                cursor.execute("SELECT tag FROM document_tags WHERE document_id = ?", (document['id'],))
                document['tags'] = [row[0] for row in cursor.fetchall()]
                
                documents.append(document)
            
            # 如果没有查询词，直接返回文档列表
            if not query or query.strip() == "":
                return documents[:limit]
            
            # 使用向量搜索查询相关文档
            results = self.vector_search(query, project_id=project_id, limit=limit)
            
            # 合并结果
            result_docs = []
            doc_ids = set()
            
            # 首先添加向量搜索结果
            for result in results:
                doc_id = result["document_id"]
                if doc_id not in doc_ids:
                    # 查找文档信息
                    for doc in documents:
                        if doc["id"] == doc_id:
                            result_docs.append(doc)
                            doc_ids.add(doc_id)
                            break
            
            # 如果结果不足，添加其他文档
            for doc in documents:
                if len(result_docs) >= limit:
                    break
                if doc["id"] not in doc_ids:
                    result_docs.append(doc)
                    doc_ids.add(doc["id"])
            
            return result_docs
        
        except Exception as e:
            logger.exception(f"搜索文档失败: {str(e)}")
            return []
    
    def vector_search(self, query: str, project_id: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        向量搜索
        
        Args:
            query: 搜索查询
            project_id: 项目ID过滤
            limit: 最大返回数量
        
        Returns:
            搜索结果
        """
        try:
            # 对查询文本进行向量化
            query_embedding = self.embedder.embed_query(query)
            
            # 获取文档块
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 构建查询条件
            if project_id:
                # 获取特定项目的文档块
                cursor.execute('''
                SELECT c.id, c.document_id, c.content, c.chunk_index
                FROM document_chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE d.status = 'processed' AND d.project_id = ?
                ''', (project_id,))
            else:
                # 获取所有文档块
                cursor.execute('''
                SELECT c.id, c.document_id, c.content, c.chunk_index
                FROM document_chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE d.status = 'processed'
                ''')
            
            chunks = []
            for row in cursor.fetchall():
                chunks.append(dict(row))
            
            # 如果没有文档块，返回空结果
            if not chunks:
                return []
            
            # 计算相似度
            chunk_contents = [chunk["content"] for chunk in chunks]
            chunk_embeddings = self.embedder.embed_documents(chunk_contents)
            
            # 计算余弦相似度
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity
            
            similarities = cosine_similarity(
                np.array(query_embedding).reshape(1, -1),
                np.array(chunk_embeddings)
            )[0]
            
            # 添加相似度到结果
            for i, chunk in enumerate(chunks):
                chunk["similarity"] = float(similarities[i])
            
            # 按相似度排序
            chunks.sort(key=lambda x: x["similarity"], reverse=True)
            
            # 获取文档信息
            results = []
            for chunk in chunks[:limit]:
                # 获取文档信息
                cursor.execute("SELECT title FROM documents WHERE id = ?", (chunk["document_id"],))
                doc_row = cursor.fetchone()
                
                if doc_row:
                    results.append({
                        "id": chunk["id"],
                        "document_id": chunk["document_id"],
                        "title": doc_row["title"],
                        "content": chunk["content"],
                        "chunk_index": chunk["chunk_index"],
                        "similarity": chunk["similarity"]
                    })
            
            conn.close()
            return results
        
        except Exception as e:
            logger.exception(f"向量搜索失败: {str(e)}")
            return []

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
