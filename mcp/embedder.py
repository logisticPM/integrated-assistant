#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
向量嵌入模块 - 提供文本向量化功能
"""

import os
import logging
import importlib.util
import numpy as np
from typing import List, Dict, Any, Optional, Union, Tuple
from pathlib import Path
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("embedder")

class Embedder:
    """文本向量嵌入器基类"""
    
    def __init__(self):
        """初始化嵌入器"""
        pass
    
    def embed(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        将文本转换为向量
        
        Args:
            texts: 文本列表
            batch_size: 批处理大小
        
        Returns:
            向量列表
        """
        raise NotImplementedError("子类必须实现embed方法")
    
    def get_embedding_dimension(self) -> int:
        """
        获取嵌入向量维度
        
        Returns:
            嵌入向量维度
        """
        raise NotImplementedError("子类必须实现get_embedding_dimension方法")

class SentenceTransformerEmbedder(Embedder):
    """使用sentence-transformers的嵌入器"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        初始化sentence-transformers嵌入器
        
        Args:
            model_name: 模型名称
        """
        super().__init__()
        self.model_name = model_name
        self.model = None
        self._check_dependencies()
    
    def _check_dependencies(self):
        """检查依赖项"""
        if not importlib.util.find_spec("sentence_transformers"):
            logger.warning("未安装sentence-transformers库，无法使用向量嵌入功能。请运行 pip install sentence-transformers")
    
    def _load_model(self):
        """加载模型"""
        if self.model is not None:
            return
        
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"加载嵌入模型: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"模型加载完成，嵌入维度: {self.get_embedding_dimension()}")
        except ImportError:
            logger.error("未安装sentence-transformers库，无法使用向量嵌入功能")
            raise ImportError("未安装sentence-transformers库，请运行 pip install sentence-transformers")
        except Exception as e:
            logger.exception(f"加载模型时出错: {str(e)}")
            raise RuntimeError(f"加载模型时出错: {str(e)}")
    
    def embed(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        将文本转换为向量
        
        Args:
            texts: 文本列表
            batch_size: 批处理大小
        
        Returns:
            向量列表
        """
        if not texts:
            return []
        
        self._load_model()
        
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 使用sentence-transformers进行嵌入
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=len(texts) > 10,
                convert_to_numpy=True
            )
            
            # 转换为Python列表
            embeddings_list = embeddings.tolist()
            
            # 记录结束时间
            end_time = time.time()
            logger.info(f"嵌入 {len(texts)} 个文本，耗时: {end_time - start_time:.2f}秒")
            
            return embeddings_list
        except Exception as e:
            logger.exception(f"嵌入文本时出错: {str(e)}")
            # 返回零向量作为回退方案
            dim = self.get_embedding_dimension()
            return [[0.0] * dim for _ in range(len(texts))]
    
    def get_embedding_dimension(self) -> int:
        """
        获取嵌入向量维度
        
        Returns:
            嵌入向量维度
        """
        self._load_model()
        return self.model.get_sentence_embedding_dimension()

class MockEmbedder(Embedder):
    """模拟嵌入器，用于测试"""
    
    def __init__(self, dimension: int = 384):
        """
        初始化模拟嵌入器
        
        Args:
            dimension: 向量维度
        """
        super().__init__()
        self.dimension = dimension
    
    def embed(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        将文本转换为向量（模拟）
        
        Args:
            texts: 文本列表
            batch_size: 批处理大小
        
        Returns:
            向量列表
        """
        # 使用文本的哈希值生成伪随机向量
        embeddings = []
        for text in texts:
            # 使用文本的哈希值作为随机种子
            np.random.seed(hash(text) % 2**32)
            # 生成随机向量并归一化
            vector = np.random.randn(self.dimension)
            vector = vector / np.linalg.norm(vector)
            embeddings.append(vector.tolist())
        
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """
        获取嵌入向量维度
        
        Returns:
            嵌入向量维度
        """
        return self.dimension

def get_embedder(model_name: str = "all-MiniLM-L6-v2", use_mock: bool = False) -> Embedder:
    """
    获取嵌入器实例
    
    Args:
        model_name: 模型名称
        use_mock: 是否使用模拟嵌入器
    
    Returns:
        嵌入器实例
    """
    if use_mock:
        logger.warning("使用模拟嵌入器，不会生成真实的向量表示")
        return MockEmbedder()
    
    try:
        return SentenceTransformerEmbedder(model_name)
    except Exception as e:
        logger.exception(f"创建嵌入器时出错: {str(e)}")
        logger.warning("回退到模拟嵌入器")
        return MockEmbedder()
