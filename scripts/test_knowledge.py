#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
知识库测试脚本
用于测试知识库的文档加载、分块、向量化和搜索功能
"""

import os
import sys
import time
import logging
import argparse
import yaml
from pathlib import Path

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
sys.path.insert(0, project_root)

# 导入知识库相关模块
from mcp.docloader import load_document
from mcp.text_splitter import get_text_splitter
from mcp.embedder import get_embedder
from mcp.vector_service import VectorDatabaseService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_knowledge")

def load_config(config_path):
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def create_test_document(content, file_path):
    """创建测试文档"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    logger.info(f"创建测试文档: {file_path}")
    return file_path

def test_document_loading(file_path):
    """测试文档加载"""
    logger.info("测试文档加载...")
    start_time = time.time()
    
    try:
        content = load_document(file_path)
        logger.info(f"文档加载成功，内容长度: {len(content)} 字符")
        logger.info(f"文档前100个字符: {content[:100]}...")
        logger.info(f"文档加载耗时: {time.time() - start_time:.2f}秒")
        return content
    except Exception as e:
        logger.error(f"文档加载失败: {str(e)}")
        return None

def test_text_splitting(content, splitter_type="smart", chunk_size=1000, chunk_overlap=200):
    """测试文本分块"""
    logger.info(f"测试文本分块 (类型: {splitter_type}, 块大小: {chunk_size}, 重叠: {chunk_overlap})...")
    start_time = time.time()
    
    try:
        splitter = get_text_splitter(splitter_type, chunk_size, chunk_overlap)
        chunks = splitter.split_text(content)
        
        logger.info(f"文本分块成功，共 {len(chunks)} 个块")
        for i, chunk in enumerate(chunks[:3]):
            logger.info(f"块 {i+1} 示例 (长度: {len(chunk)}): {chunk[:100]}...")
        
        if len(chunks) > 3:
            logger.info(f"... 还有 {len(chunks) - 3} 个块未显示")
        
        logger.info(f"文本分块耗时: {time.time() - start_time:.2f}秒")
        return chunks
    except Exception as e:
        logger.error(f"文本分块失败: {str(e)}")
        return None

def test_embedding(chunks, model_name="all-MiniLM-L6-v2", use_mock=False):
    """测试文本嵌入"""
    logger.info(f"测试文本嵌入 (模型: {model_name}, 使用模拟: {use_mock})...")
    start_time = time.time()
    
    try:
        embedder = get_embedder(model_name, use_mock)
        
        # 只嵌入前3个块作为示例
        test_chunks = chunks[:min(3, len(chunks))]
        embeddings = embedder.embed(test_chunks)
        
        logger.info(f"文本嵌入成功，嵌入维度: {len(embeddings[0])}")
        logger.info(f"嵌入示例: {embeddings[0][:5]}...")
        logger.info(f"文本嵌入耗时: {time.time() - start_time:.2f}秒")
        return embeddings
    except Exception as e:
        logger.error(f"文本嵌入失败: {str(e)}")
        return None

def test_vector_service(config, test_doc_path):
    """测试向量数据库服务"""
    logger.info("测试向量数据库服务...")
    
    try:
        # 初始化向量数据库服务
        db_path = config["db"]["sqlite_path"]
        vector_db_path = config["db"]["vector_db_path"]
        
        # 确保目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        os.makedirs(vector_db_path, exist_ok=True)
        
        vector_service = VectorDatabaseService(config, db_path, vector_db_path)
        
        # 创建文档
        doc_id = vector_service.create_document(
            title="测试文档",
            category="测试",
            tags=["测试", "知识库"],
            file_path=test_doc_path
        )
        
        logger.info(f"文档创建成功，ID: {doc_id}")
        
        # 处理文档
        logger.info("开始处理文档...")
        success = vector_service.process_document(doc_id)
        
        if success:
            logger.info("文档处理成功")
            
            # 测试搜索
            logger.info("测试搜索...")
            search_results = vector_service.search("测试查询", limit=3)
            
            logger.info(f"搜索结果数量: {len(search_results)}")
            for i, result in enumerate(search_results):
                logger.info(f"结果 {i+1}:")
                logger.info(f"  标题: {result['title']}")
                logger.info(f"  相关度: {result['relevance']:.4f}")
                logger.info(f"  片段: {result['snippet'][:100]}...")
            
            return True
        else:
            logger.error("文档处理失败")
            return False
    except Exception as e:
        logger.error(f"向量数据库服务测试失败: {str(e)}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="测试知识库功能")
    parser.add_argument("--config", type=str, default="../config.yaml", 
                        help="配置文件路径 (默认: ../config.yaml)")
    parser.add_argument("--use-mock", action="store_true", 
                        help="使用模拟嵌入器")
    parser.add_argument("--test-file", type=str, 
                        help="测试文件路径，如果不指定则创建测试文件")
    
    args = parser.parse_args()
    
    # 获取配置文件的绝对路径
    if not os.path.isabs(args.config):
        args.config = os.path.abspath(os.path.join(os.path.dirname(__file__), args.config))
    
    logger.info(f"使用配置文件: {args.config}")
    
    # 加载配置
    config = load_config(args.config)
    
    # 准备测试文档
    if args.test_file and os.path.exists(args.test_file):
        test_doc_path = args.test_file
        logger.info(f"使用现有测试文件: {test_doc_path}")
    else:
        # 创建测试文档
        test_content = """
# 知识库测试文档

这是一个用于测试知识库功能的文档。它包含多个段落，用于测试文本分块功能。

## 第一部分：文本分块

文本分块是知识库的核心功能之一。它将长文本分割成较小的块，以便于向量化和检索。
一个好的分块策略应该考虑语义完整性，避免将相关内容分割到不同的块中。

## 第二部分：向量嵌入

向量嵌入是将文本转换为数值向量的过程。这些向量捕获了文本的语义信息，使得语义相似的文本在向量空间中彼此接近。
常用的嵌入模型包括：
- Word2Vec
- GloVe
- BERT
- Sentence-BERT

## 第三部分：向量检索

向量检索是通过计算查询向量与文档向量之间的相似度来找到最相关的文档。
常用的相似度度量包括：
- 余弦相似度
- 欧氏距离
- 点积

## 结论

知识库系统结合了文本处理、向量嵌入和向量检索等技术，为用户提供高效的信息检索服务。
通过不断优化这些组件，可以提高检索的准确性和效率。
"""
        test_doc_path = os.path.join(project_root, "data", "test_document.md")
        create_test_document(test_content, test_doc_path)
    
    # 测试文档加载
    content = test_document_loading(test_doc_path)
    if content is None:
        return
    
    # 测试文本分块
    chunks = test_text_splitting(
        content, 
        config["knowledge"]["splitter_type"],
        config["knowledge"]["chunk_size"],
        config["knowledge"]["chunk_overlap"]
    )
    if chunks is None:
        return
    
    # 测试文本嵌入
    embeddings = test_embedding(
        chunks,
        config["knowledge"]["embedding_model"],
        args.use_mock
    )
    if embeddings is None:
        return
    
    # 测试向量数据库服务
    success = test_vector_service(config, test_doc_path)
    
    if success:
        logger.info("知识库功能测试完成，所有测试通过！")
    else:
        logger.error("知识库功能测试失败")

if __name__ == "__main__":
    main()
