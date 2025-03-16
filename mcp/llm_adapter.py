#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
LLM适配服务模块 - 提供本地LLM模型管理和推理服务
集成AnythingLLM的本地LLM能力
"""

import os
import json
import time
import logging
import requests
from typing import Dict, Any, List, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("llm_adapter_service")

class LLMAdapterService:
    """LLM适配服务类，处理模型管理和推理请求"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化LLM适配服务
        
        Args:
            config: 服务配置
        """
        self.config = config
        self.model_type = config["llm"]["model"]
        self.model_path = config["llm"]["model_path"]
        self.embedding_model_type = config["llm"]["embedding_model"]
        self.embedding_model_path = config["llm"]["embedding_model_path"]
        
        # AnythingLLM集成配置
        self.anything_llm_enabled = config["llm"]["anything_llm"]["enabled"]
        self.anything_llm_api_url = config["llm"]["anything_llm"]["api_url"]
        self.anything_llm_api_key = config["llm"]["anything_llm"]["api_key"]
        
        # 模板缓存
        self.templates = self._load_default_templates()
    
    def _load_default_templates(self) -> Dict[str, str]:
        """
        加载默认提示词模板
        
        Returns:
            模板字典
        """
        return {
            "meeting_summary": "请根据以下会议记录生成一个简洁的摘要，包括主要讨论的话题、达成的决定和后续行动项：\n\n{transcription}",
            "meeting_key_points": "请从以下会议记录中提取关键点，并标注每个关键点的时间戳：\n\n{transcription}",
            "email_reply": "请根据以下邮件内容，生成一个{style}的回复：\n\n{email_content}",
            "email_analysis": "请分析以下邮件内容，提取主题、情感和优先级：\n\n{email_content}",
            "knowledge_query": "基于以下背景信息，请回答问题：\n\n背景信息：{context}\n\n问题：{query}"
        }
    
    def _call_anything_llm(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用AnythingLLM API
        
        Args:
            endpoint: API端点
            data: 请求数据
        
        Returns:
            API响应
        
        Raises:
            Exception: API调用失败时抛出异常
        """
        if not self.anything_llm_enabled:
            raise Exception("AnythingLLM集成未启用")
        
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.anything_llm_api_key:
            headers["Authorization"] = f"Bearer {self.anything_llm_api_key}"
        
        try:
            response = requests.post(
                f"{self.anything_llm_api_url}/{endpoint}",
                headers=headers,
                json=data,
                timeout=60
            )
            
            response.raise_for_status()
            return response.json()
        
        except requests.RequestException as e:
            logger.exception(f"AnythingLLM API调用失败: {endpoint}")
            raise Exception(f"AnythingLLM API调用失败: {str(e)}")
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        获取可用的LLM模型列表
        
        Returns:
            模型列表
        """
        if self.anything_llm_enabled:
            try:
                # 调用AnythingLLM API获取模型列表
                response = self._call_anything_llm("models", {})
                return response.get("models", [])
            except Exception as e:
                logger.error(f"获取AnythingLLM模型列表失败: {str(e)}")
        
        # 返回本地模型列表（模拟数据）
        return [
            {
                "id": "local-model",
                "name": "本地模型",
                "type": self.model_type,
                "path": self.model_path
            }
        ]
    
    def get_embedding(self, text: str) -> List[float]:
        """
        获取文本的嵌入向量
        
        Args:
            text: 输入文本
        
        Returns:
            嵌入向量
        """
        if self.anything_llm_enabled:
            try:
                # 调用AnythingLLM API获取嵌入向量
                response = self._call_anything_llm("embeddings", {
                    "text": text
                })
                return response.get("embedding", [])
            except Exception as e:
                logger.error(f"获取AnythingLLM嵌入向量失败: {str(e)}")
        
        # 返回模拟的嵌入向量（实际项目中应该使用真实的嵌入模型）
        import random
        return [random.random() for _ in range(384)]
    
    def generate_text(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """
        生成文本
        
        Args:
            prompt: 提示词
            max_tokens: 最大生成标记数
            temperature: 温度参数
        
        Returns:
            生成的文本
        """
        if self.anything_llm_enabled:
            try:
                # 调用AnythingLLM API生成文本
                response = self._call_anything_llm("completions", {
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                })
                return response.get("text", "")
            except Exception as e:
                logger.error(f"AnythingLLM生成文本失败: {str(e)}")
        
        # 返回模拟的生成文本（实际项目中应该使用真实的LLM模型）
        # 这里根据不同的提示词模拟不同的响应
        if "会议记录" in prompt and "摘要" in prompt:
            return "会议主要讨论了项目进度和下一步计划。团队报告了当前的开发状态，并确定了需要解决的关键问题。会议决定在下周五前完成初步原型，并安排了下一次评审会议的时间。"
        elif "会议记录" in prompt and "关键点" in prompt:
            return "1. [00:01:15] 项目当前完成度约为60%\n2. [00:05:30] 测试团队报告了3个关键bug\n3. [00:12:45] 决定增加两名开发人员加速进度\n4. [00:20:10] 下一次评审会议定在周五下午3点"
        elif "邮件" in prompt and "回复" in prompt:
            return "感谢您的邮件。我已收到您的请求，并会尽快处理。如有任何疑问，请随时联系我。\n\n祝好，\n[您的名字]"
        elif "邮件" in prompt and "分析" in prompt:
            return "主题：项目合作请求\n情感：积极\n优先级：中等\n关键点：对方希望探讨潜在的合作机会，建议安排会议讨论细节。"
        elif "背景信息" in prompt and "问题" in prompt:
            return "根据提供的背景信息，我认为最佳解决方案是采用分布式架构来处理大规模数据处理需求。这种方法可以提高系统的可扩展性和容错能力，同时减少单点故障的风险。"
        else:
            return "我是一个AI助手，很高兴能帮助您解决问题。请提供更多具体信息，以便我能更好地为您服务。"
    
    def generate_meeting_summary(self, transcription: str) -> str:
        """
        生成会议摘要
        
        Args:
            transcription: 会议转录文本
        
        Returns:
            会议摘要
        """
        template = self.templates["meeting_summary"]
        prompt = template.format(transcription=transcription)
        return self.generate_text(prompt)
    
    def extract_meeting_key_points(self, transcription: str) -> List[Dict[str, str]]:
        """
        提取会议关键点
        
        Args:
            transcription: 会议转录文本
        
        Returns:
            关键点列表
        """
        template = self.templates["meeting_key_points"]
        prompt = template.format(transcription=transcription)
        result = self.generate_text(prompt)
        
        # 解析关键点
        key_points = []
        for line in result.strip().split("\n"):
            if not line.strip():
                continue
            
            # 尝试解析时间戳和内容
            try:
                # 假设格式为: "1. [00:01:15] 项目当前完成度约为60%"
                parts = line.split("]", 1)
                if len(parts) < 2:
                    continue
                
                timestamp_part = parts[0].strip()
                content_part = parts[1].strip()
                
                # 提取时间戳
                timestamp = timestamp_part.split("[")[-1].strip()
                
                key_points.append({
                    "timestamp": timestamp,
                    "content": content_part
                })
            except Exception:
                # 如果解析失败，添加没有时间戳的关键点
                key_points.append({
                    "timestamp": "",
                    "content": line.strip()
                })
        
        return key_points
    
    def generate_email_reply(self, email_content: str, reply_type: str = "简短回复") -> str:
        """
        生成邮件回复
        
        Args:
            email_content: 邮件内容
            reply_type: 回复类型
        
        Returns:
            邮件回复
        """
        template = self.templates["email_reply"]
        prompt = template.format(style=reply_type, email_content=email_content)
        return self.generate_text(prompt)
    
    def analyze_email(self, email_content: str) -> Dict[str, Any]:
        """
        分析邮件内容
        
        Args:
            email_content: 邮件内容
        
        Returns:
            分析结果
        """
        template = self.templates["email_analysis"]
        prompt = template.format(email_content=email_content)
        result = self.generate_text(prompt)
        
        # 解析分析结果
        analysis = {}
        for line in result.strip().split("\n"):
            if not line.strip():
                continue
            
            # 尝试解析键值对
            try:
                key, value = line.split("：", 1)
                analysis[key.strip()] = value.strip()
            except Exception:
                continue
        
        return analysis
    
    def answer_knowledge_query(self, query: str, context: str) -> str:
        """
        回答知识库查询
        
        Args:
            query: 查询问题
            context: 上下文信息
        
        Returns:
            回答
        """
        template = self.templates["knowledge_query"]
        prompt = template.format(query=query, context=context)
        return self.generate_text(prompt, temperature=0.3)
    
    def get_template(self, template_name: str) -> str:
        """
        获取提示词模板
        
        Args:
            template_name: 模板名称
        
        Returns:
            模板内容
        
        Raises:
            Exception: 模板不存在时抛出异常
        """
        if template_name not in self.templates:
            raise Exception(f"模板不存在: {template_name}")
        
        return self.templates[template_name]
    
    def set_template(self, template_name: str, template_content: str) -> bool:
        """
        设置提示词模板
        
        Args:
            template_name: 模板名称
            template_content: 模板内容
        
        Returns:
            是否成功
        """
        self.templates[template_name] = template_content
        return True
    
    def list_templates(self) -> Dict[str, str]:
        """
        列出所有提示词模板
        
        Returns:
            模板字典
        """
        return self.templates

def register_llm_service(server):
    """
    注册LLM适配服务
    
    Args:
        server: MCP服务器实例
    """
    # 创建LLM适配服务实例
    service = LLMAdapterService(server.config)
    
    # 注册方法
    server.register_module("llm", {
        "get_models": service.get_available_models,
        "get_embedding": service.get_embedding,
        "generate_text": service.generate_text,
        "generate_meeting_summary": service.generate_meeting_summary,
        "extract_meeting_key_points": service.extract_meeting_key_points,
        "generate_email_reply": service.generate_email_reply,
        "analyze_email": service.analyze_email,
        "answer_knowledge_query": service.answer_knowledge_query,
        "get_template": service.get_template,
        "set_template": service.set_template,
        "list_templates": service.list_templates
    })
