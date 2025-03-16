#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文本分块模块 - 提供智能文本分块功能
"""

import re
import logging
from typing import List, Dict, Any, Optional
import importlib.util

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("text_splitter")

class TextSplitter:
    """文本分块器基类"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        初始化文本分块器
        
        Args:
            chunk_size: 块大小（字符数）
            chunk_overlap: 块重叠大小（字符数）
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def split_text(self, text: str) -> List[str]:
        """
        将文本分块
        
        Args:
            text: 输入文本
        
        Returns:
            文本块列表
        """
        raise NotImplementedError("子类必须实现split_text方法")

class SimpleTextSplitter(TextSplitter):
    """简单文本分块器，按段落和句子分块"""
    
    def split_text(self, text: str) -> List[str]:
        """
        将文本分块
        
        Args:
            text: 输入文本
        
        Returns:
            文本块列表
        """
        # 按段落分割
        paragraphs = text.split('\n\n')
        
        chunks = []
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
                            
                            # 如果句子太长，直接截断
                            if len(sentence) > self.chunk_size:
                                # 按词分割
                                words = sentence.split(' ')
                                current_chunk = ""
                                for word in words:
                                    if len(current_chunk) + len(word) + 1 < self.chunk_size:
                                        if current_chunk:
                                            current_chunk += " "
                                        current_chunk += word
                                    else:
                                        chunks.append(current_chunk)
                                        current_chunk = word
                            else:
                                current_chunk = sentence
                else:
                    current_chunk = paragraph
        
        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks

class MarkdownTextSplitter(TextSplitter):
    """Markdown文本分块器，考虑Markdown结构"""
    
    def split_text(self, text: str) -> List[str]:
        """
        将Markdown文本分块，考虑标题、列表等结构
        
        Args:
            text: 输入文本
        
        Returns:
            文本块列表
        """
        # 定义Markdown结构的正则表达式
        header_pattern = r'^#{1,6}\s+.+$'
        list_pattern = r'^(\s*[-*+]|\s*\d+\.)\s+.+$'
        code_block_pattern = r'^```[\s\S]*?```$'
        
        # 尝试使用langchain的分块器
        try:
            from langchain_text_splitters import MarkdownHeaderTextSplitter
            
            headers_to_split_on = [
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
                ("####", "Header 4"),
                ("#####", "Header 5"),
                ("######", "Header 6"),
            ]
            
            markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
            docs = markdown_splitter.split_text(text)
            
            # 进一步分块，确保每个块不超过最大大小
            chunks = []
            for doc in docs:
                if len(doc) <= self.chunk_size:
                    chunks.append(doc)
                else:
                    # 使用简单分块器进一步分割
                    simple_splitter = SimpleTextSplitter(self.chunk_size, self.chunk_overlap)
                    chunks.extend(simple_splitter.split_text(doc))
            
            return chunks
        except ImportError:
            logger.warning("未安装langchain_text_splitters，将使用简单分块器")
            return SimpleTextSplitter(self.chunk_size, self.chunk_overlap).split_text(text)

class SmartTextSplitter(TextSplitter):
    """智能文本分块器，使用复杂的分块策略"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        super().__init__(chunk_size, chunk_overlap)
        
        # 定义复杂的分块正则表达式，参考5ire的实现
        self.chunk_regex = re.compile(
            r"("
            # 1. 标题
            r"(?:^(?:[#*=-]{1,6}|\w[^\r\n]{0,200}\r?\n[-=]{2,200}|<h[1-6][^>]{0,100}>)[^\r\n]{1,200}(?:</h[1-6]>)?(?:\r?\n|$))"
            r"|"
            # 2. 列表项
            r"(?:(?:^|\r?\n)[ \t]{0,3}(?:[-*+•]|\d{1,3}\.\w\.|\[[ xX]\])[ \t]+[^\r\n]{1,200}"
            r"(?:(?:\r?\n[ \t]{2,5}(?:[-*+•]|\d{1,3}\.\w\.|\[[ xX]\])[ \t]+[^\r\n]{1,200}){0,5}"
            r"(?:\r?\n[ \t]{4,7}(?:[-*+•]|\d{1,3}\.\w\.|\[[ xX]\])[ \t]+[^\r\n]{1,200}){0,5})?)"
            r"|"
            # 3. 引用块
            r"(?:(?:^>(?:>|\s{2,}){0,2}[^\r\n]{0,200}\r?\n?){1,10})"
            r"|"
            # 4. 代码块
            r"(?:(?:^|\r?\n)(?:```|~~~)(?:\w{0,20})?\r?\n[\s\S]{0,1000}?(?:```|~~~)\r?\n?"
            r"|(?:(?:^|\r?\n)(?: {4}|\t)[^\r\n]{0,200}(?:\r?\n(?: {4}|\t)[^\r\n]{0,200}){0,20}\r?\n?)"
            r"|(?:<pre>(?:<code>)?[\s\S]{0,1000}?(?:</code>)?</pre>))"
            r"|"
            # 5. 表格
            r"(?:(?:^|\r?\n)(?:\|[^\r\n]{0,200}\|(?:\r?\n\|[-:]{1,200}\|){0,1}(?:\r?\n\|[^\r\n]{0,200}\|){0,20}"
            r"|<table>[\s\S]{0,2000}?</table>))"
            r"|"
            # 6. 水平线
            r"(?:^(?:[-*_]){3,}\s*$|<hr\s*/?>)"
            r"|"
            # 7. 段落
            r"(?:(?:^|\r?\n)[^\r\n]{1,1000}(?:\r?\n|$))"
            r")",
            re.MULTILINE
        )
    
    def split_text(self, text: str) -> List[str]:
        """
        使用智能分块策略将文本分块
        
        Args:
            text: 输入文本
        
        Returns:
            文本块列表
        """
        try:
            # 使用正则表达式匹配文本块
            chunks = self.chunk_regex.findall(text)
            
            # 过滤空块
            chunks = [chunk for chunk in chunks if chunk.strip()]
            
            # 如果没有找到块，使用简单分块器
            if not chunks:
                logger.warning("智能分块未找到任何块，使用简单分块器")
                return SimpleTextSplitter(self.chunk_size, self.chunk_overlap).split_text(text)
            
            # 处理过大的块
            result_chunks = []
            for chunk in chunks:
                if len(chunk) <= self.chunk_size:
                    result_chunks.append(chunk)
                else:
                    # 使用简单分块器进一步分割
                    simple_splitter = SimpleTextSplitter(self.chunk_size, self.chunk_overlap)
                    result_chunks.extend(simple_splitter.split_text(chunk))
            
            return result_chunks
        except Exception as e:
            logger.exception(f"智能分块失败: {str(e)}")
            return SimpleTextSplitter(self.chunk_size, self.chunk_overlap).split_text(text)

def get_text_splitter(splitter_type: str = "smart", chunk_size: int = 1000, chunk_overlap: int = 200) -> TextSplitter:
    """
    获取文本分块器
    
    Args:
        splitter_type: 分块器类型，可选值：simple, markdown, smart
        chunk_size: 块大小
        chunk_overlap: 块重叠大小
    
    Returns:
        文本分块器实例
    """
    if splitter_type == "simple":
        return SimpleTextSplitter(chunk_size, chunk_overlap)
    elif splitter_type == "markdown":
        return MarkdownTextSplitter(chunk_size, chunk_overlap)
    elif splitter_type == "smart":
        return SmartTextSplitter(chunk_size, chunk_overlap)
    else:
        logger.warning(f"未知的分块器类型: {splitter_type}，使用智能分块器")
        return SmartTextSplitter(chunk_size, chunk_overlap)
