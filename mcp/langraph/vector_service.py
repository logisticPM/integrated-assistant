#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基于 langraph 的向量存储组件
支持多种向量存储服务
"""

import os
import sys
import logging
import time
import json
from typing import Dict, Any, List, Optional, Union, Callable
from pydantic import BaseModel, Field

from mcp.langraph.core import MCPComponent, VectorStoreComponent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("langraph.vector_service")

class LocalVectorStoreComponent(VectorStoreComponent):
    """本地向量存储组件"""
    
    def __init__(
        self,
        name: str = "local_vector_store",
        data_dir: Optional[str] = None,
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        """
        初始化本地向量存储组件
        
        Args:
            name: 组件名称
            data_dir: 数据目录，默认为 "data/vector_store"
            embedding_model: 嵌入模型名称
        """
        super().__init__(
            name=name,
            description=f"本地向量存储组件 (model={embedding_model})"
        )
        
        # 获取项目根目录
        if data_dir is None:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            data_dir = os.path.join(root_dir, "data", "vector_store")
        
        self.data_dir = data_dir
        self.embedding_model = embedding_model
        self.vector_store = None
        
        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 初始化向量存储
        self._init_vector_store()
    
    def _init_vector_store(self):
        """初始化向量存储"""
        try:
            from langchain_community.vectorstores import FAISS
            from langchain_community.embeddings import HuggingFaceEmbeddings
            
            # 初始化嵌入模型
            self.embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model)
            
            # 检查是否存在向量存储
            index_path = os.path.join(self.data_dir, "index.faiss")
            if os.path.exists(index_path):
                # 加载现有向量存储
                self.vector_store = FAISS.load_local(
                    folder_path=self.data_dir,
                    embeddings=self.embeddings,
                    index_name="index"
                )
                logger.info(f"加载现有向量存储: {self.data_dir}")
            else:
                # 创建空向量存储
                self.vector_store = FAISS.from_texts(
                    texts=["初始化向量存储"],
                    embedding=self.embeddings
                )
                # 保存向量存储
                self.vector_store.save_local(self.data_dir, index_name="index")
                logger.info(f"创建新向量存储: {self.data_dir}")
        
        except ImportError as e:
            logger.error(f"初始化向量存储失败，缺少依赖: {str(e)}")
        
        except Exception as e:
            logger.error(f"初始化向量存储失败: {str(e)}")
    
    def is_available(self) -> bool:
        """
        检查组件是否可用
        
        Returns:
            是否可用
        """
        return self.vector_store is not None
    
    def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        搜索向量存储
        
        Args:
            query: 查询文本
            **kwargs: 其他参数，如 k (结果数量)
        
        Returns:
            搜索结果
        """
        if not self.is_available():
            raise RuntimeError("向量存储不可用")
        
        try:
            logger.info(f"开始搜索: {query[:50]}...")
            start_time = time.time()
            
            # 获取结果数量
            k = kwargs.get("k", 5)
            
            # 执行搜索
            results = self.vector_store.similarity_search_with_score(query, k=k)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            logger.info(f"搜索完成，耗时: {processing_time:.2f}秒，找到 {len(results)} 个结果")
            
            # 格式化结果
            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)
                })
            
            return formatted_results
        
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            raise
    
    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """
        添加文本到向量存储
        
        Args:
            texts: 文本列表
            metadatas: 元数据列表
        
        Returns:
            文档 ID 列表
        """
        if not self.is_available():
            raise RuntimeError("向量存储不可用")
        
        try:
            logger.info(f"开始添加 {len(texts)} 个文本到向量存储")
            start_time = time.time()
            
            # 添加文本
            ids = self.vector_store.add_texts(texts, metadatas=metadatas)
            
            # 保存向量存储
            self.vector_store.save_local(self.data_dir, index_name="index")
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            logger.info(f"添加完成，耗时: {processing_time:.2f}秒")
            
            return ids
        
        except Exception as e:
            logger.error(f"添加文本失败: {str(e)}")
            raise
    
    def delete(self, ids: List[str]) -> None:
        """
        删除文档
        
        Args:
            ids: 文档 ID 列表
        """
        if not self.is_available():
            raise RuntimeError("向量存储不可用")
        
        try:
            logger.info(f"开始删除 {len(ids)} 个文档")
            start_time = time.time()
            
            # 删除文档
            self.vector_store.delete(ids)
            
            # 保存向量存储
            self.vector_store.save_local(self.data_dir, index_name="index")
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            logger.info(f"删除完成，耗时: {processing_time:.2f}秒")
        
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            raise

class MockVectorStoreComponent(VectorStoreComponent):
    """模拟向量存储组件，用于测试和开发"""
    
    def __init__(self, name: str = "mock_vector_store"):
        """
        初始化模拟向量存储组件
        
        Args:
            name: 组件名称
        """
        super().__init__(
            name=name,
            description="模拟向量存储组件"
        )
    
    def is_available(self) -> bool:
        """
        检查组件是否可用
        
        Returns:
            是否可用
        """
        return True
    
    def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        搜索向量存储
        
        Args:
            query: 查询文本
            **kwargs: 其他参数
        
        Returns:
            搜索结果
        """
        logger.info(f"模拟搜索: {query[:50]}...")
        
        # 模拟处理时间
        time.sleep(1)
        
        # 返回模拟结果
        return [
            {
                "content": f"这是与查询 '{query[:20]}...' 相关的模拟结果 1。",
                "metadata": {"source": "mock_doc_1", "page": 1},
                "score": 0.95
            },
            {
                "content": f"这是与查询 '{query[:20]}...' 相关的模拟结果 2。",
                "metadata": {"source": "mock_doc_2", "page": 5},
                "score": 0.85
            },
            {
                "content": f"这是与查询 '{query[:20]}...' 相关的模拟结果 3。",
                "metadata": {"source": "mock_doc_3", "page": 10},
                "score": 0.75
            }
        ]

class VectorService:
    """向量服务，管理多个向量存储组件"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化向量服务
        
        Args:
            config: 配置
        """
        self.config = config
        self.components: Dict[str, VectorStoreComponent] = {}
        
        # 初始化组件
        self._init_components()
    
    def _init_components(self):
        """初始化组件"""
        # 添加本地向量存储组件
        if self.config.get("vector_store", {}).get("local", {}).get("enabled", True):
            embedding_model = self.config.get("vector_store", {}).get("local", {}).get("embedding_model", "all-MiniLM-L6-v2")
            
            component = LocalVectorStoreComponent(
                embedding_model=embedding_model
            )
            
            self.add_component(component)
        
        # 添加模拟组件
        self.add_component(MockVectorStoreComponent())
    
    def add_component(self, component: VectorStoreComponent):
        """
        添加组件
        
        Args:
            component: 要添加的组件
        """
        self.components[component.name] = component
        logger.info(f"添加向量存储组件: {component.name}")
    
    def get_available_component(self) -> Optional[VectorStoreComponent]:
        """
        获取可用的组件
        
        Returns:
            可用的组件，如果没有则返回 None
        """
        # 优先级：本地向量存储 > 模拟
        for name in ["local_vector_store", "mock_vector_store"]:
            if name in self.components and self.components[name].is_available():
                return self.components[name]
        
        return None
    
    def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        搜索向量存储
        
        Args:
            query: 查询文本
            **kwargs: 其他参数
        
        Returns:
            搜索结果
        
        Raises:
            RuntimeError: 没有可用的向量存储组件时抛出
        """
        component = self.get_available_component()
        
        if component is None:
            raise RuntimeError("没有可用的向量存储组件")
        
        logger.info(f"使用组件 {component.name} 搜索")
        
        return component.search(query, **kwargs)
    
    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """
        添加文本到向量存储
        
        Args:
            texts: 文本列表
            metadatas: 元数据列表
        
        Returns:
            文档 ID 列表
        
        Raises:
            RuntimeError: 没有可用的向量存储组件时抛出
        """
        component = self.get_available_component()
        
        if component is None:
            raise RuntimeError("没有可用的向量存储组件")
        
        if not hasattr(component, "add_texts"):
            raise RuntimeError(f"组件 {component.name} 不支持添加文本")
        
        logger.info(f"使用组件 {component.name} 添加文本")
        
        return component.add_texts(texts, metadatas)
