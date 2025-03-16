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
        
        # 本地LLM配置
        self.local_llm = None
        self.local_llm_available = self._check_local_llm()
        
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
            "structured_meeting_summary": """请根据以下会议记录生成一个结构化的会议摘要，包括以下部分：
1. 总体摘要：简要概述会议的主要内容和目的（200字以内）
2. 议程：列出会议讨论的主要议题（以markdown列表格式）
3. 决策事项：列出会议中做出的所有决定（以markdown列表格式）
4. 行动项：列出会议中分配的任务，包括负责人、任务描述、截止日期和状态（以JSON格式返回）
5. 关键点：提取会议中的关键讨论点，包括时间戳、发言人和内容（以JSON格式返回）

会议标题：{meeting_title}
参与者：{participants}

会议记录：
{transcription}

请以JSON格式返回结果，包含以下字段：summary, agenda, decisions, action_items, key_points
其中action_items应为包含assignee, task, due_date, status字段的对象数组
key_points应为包含timestamp, speaker, point字段的对象数组
""",
            "email_reply": "请根据以下邮件内容，生成一个{style}的回复：\n\n{email_content}",
            "email_analysis": "请分析以下邮件内容，提取主题、情感和优先级：\n\n{email_content}",
            "knowledge_query": "基于以下背景信息，请回答问题：\n\n背景信息：{context}\n\n问题：{query}"
        }
    
    def _check_local_llm(self) -> bool:
        """检查本地LLM是否可用"""
        if self.model_type != "local":
            return False
            
        try:
            # 检查本地LLM模块是否可用
            from mcp.local_llm import is_local_llm_available
            return is_local_llm_available()
        except ImportError:
            logger.warning("本地LLM模块不可用")
            return False
        except Exception as e:
            logger.warning(f"检查本地LLM时出错: {str(e)}")
            return False
    
    def _init_local_llm(self):
        """初始化本地LLM"""
        if self.local_llm is None and self.local_llm_available:
            try:
                from mcp.local_llm import LocalLLM
                self.local_llm = LocalLLM(
                    model_dir=self.model_path
                )
                logger.info("本地LLM模型初始化成功")
            except Exception as e:
                logger.error(f"初始化本地LLM模型失败: {str(e)}")
                self.local_llm_available = False
    
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
        models = []
        
        # 检查AnythingLLM API
        if self.anything_llm_enabled:
            try:
                # 调用AnythingLLM API获取模型列表
                response = self._call_anything_llm("models", {})
                models.extend(response.get("models", []))
            except Exception as e:
                logger.error(f"获取AnythingLLM模型列表失败: {str(e)}")
        
        # 检查本地模型
        if self.local_llm_available:
            models.append({
                "id": "local-model",
                "name": "本地模型",
                "type": self.model_type,
                "path": self.model_path
            })
        
        # 如果没有可用模型，返回模拟数据
        if not models:
            models.append({
                "id": "mock-model",
                "name": "模拟模型",
                "type": "mock",
                "path": ""
            })
        
        return models
    
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
        
        # TODO: 实现本地嵌入模型
        
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
        # 尝试使用AnythingLLM API
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
        
        # 尝试使用本地LLM
        if self.local_llm_available:
            try:
                self._init_local_llm()
                if self.local_llm:
                    return self.local_llm.generate(
                        prompt=prompt,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
            except Exception as e:
                logger.error(f"本地LLM生成文本失败: {str(e)}")
        
        # 返回模拟的生成文本（实际项目中应该使用真实的LLM模型）
        # 这里根据不同的提示词模拟不同的响应
        if "会议记录" in prompt and "摘要" in prompt and "结构化" in prompt:
            # 模拟结构化会议摘要的JSON响应
            return json.dumps({
                "summary": "会议主要讨论了项目进度和下一步计划。团队报告了当前的开发状态，并确定了需要解决的关键问题。会议决定在下周五前完成初步原型，并安排了下一次评审会议的时间。",
                "agenda": "1. 项目进度回顾\n2. 问题讨论\n3. 下一步计划\n4. 任务分配",
                "decisions": "1. 决定将发布日期推迟一周\n2. 同意增加两名开发人员到团队\n3. 批准了新的UI设计方案",
                "action_items": [
                    {"assignee": "张三", "task": "完成前端界面开发", "due_date": "2023-10-15", "status": "进行中"},
                    {"assignee": "李四", "task": "修复已知的3个关键bug", "due_date": "2023-10-10", "status": "待处理"},
                    {"assignee": "王五", "task": "准备下周的演示文稿", "due_date": "2023-10-12", "status": "未开始"}
                ],
                "key_points": [
                    {"timestamp": "00:05:23", "speaker": "张三", "point": "报告了前端开发的当前进度，完成了约70%的计划功能"},
                    {"timestamp": "00:12:45", "speaker": "李四", "point": "提出了后端API的性能问题，需要优化数据库查询"},
                    {"timestamp": "00:25:30", "speaker": "王五", "point": "建议增加用户反馈收集功能，以便及时调整产品方向"}
                ]
            }, ensure_ascii=False)
        elif "会议记录" in prompt and "摘要" in prompt:
            # 模拟会议摘要
            return "会议主要讨论了项目进度和下一步计划。团队报告了当前的开发状态，并确定了需要解决的关键问题。会议决定在下周五前完成初步原型，并安排了下一次评审会议的时间。"
        elif "会议记录" in prompt and "关键点" in prompt:
            # 模拟会议关键点
            return "1. [00:05:23] 张三报告了前端开发的当前进度，完成了约70%的计划功能\n2. [00:12:45] 李四提出了后端API的性能问题，需要优化数据库查询\n3. [00:25:30] 王五建议增加用户反馈收集功能，以便及时调整产品方向"
        elif "邮件" in prompt and "回复" in prompt:
            # 模拟邮件回复
            return "感谢您的邮件。我已收到您的请求，并会尽快处理。如有任何疑问，请随时联系我。"
        elif "邮件" in prompt and "分析" in prompt:
            # 模拟邮件分析
            return json.dumps({
                "subject": "项目进度汇报",
                "sentiment": "积极",
                "priority": "中等",
                "key_points": ["项目按计划进行", "需要解决一些技术问题", "请求下周安排会议讨论"]
            }, ensure_ascii=False)
        elif "背景信息" in prompt and "问题" in prompt:
            # 模拟知识库查询
            return "根据提供的背景信息，您的问题的答案是：这个项目使用了React和Node.js技术栈，主要功能包括用户认证、数据可视化和报表生成。部署需要使用Docker容器，并且需要配置MongoDB数据库。"
        else:
            # 通用回复
            return f"这是对您提问的回复。您的提问内容涉及到了{prompt[:20]}...等方面的内容。由于当前没有可用的LLM服务，这是一个模拟的回复。在实际部署中，您需要配置AnythingLLM API或者本地LLM模型来获取真实的AI回复。"
    
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
    
    def generate_structured_meeting_summary(self, transcription: str, meeting_title: str = "", participants: List[str] = None) -> Dict[str, Any]:
        """
        生成结构化的会议摘要，包括议程、决策、行动项等
        
        Args:
            transcription: 会议转录文本
            meeting_title: 会议标题
            participants: 参与者列表
        
        Returns:
            结构化摘要结果
        """
        if participants is None:
            participants = []
        
        template = self.templates["structured_meeting_summary"]
        prompt = template.format(
            transcription=transcription,
            meeting_title=meeting_title,
            participants=", ".join(participants)
        )
        
        result = self.generate_text(prompt, temperature=0.3)
        
        try:
            # 尝试解析JSON结果
            structured_summary = json.loads(result)
            
            # 确保返回结果包含所有必要字段
            required_fields = ["summary", "agenda", "decisions", "action_items", "key_points"]
            for field in required_fields:
                if field not in structured_summary:
                    structured_summary[field] = "" if field in ["summary", "agenda", "decisions"] else []
            
            return structured_summary
        
        except json.JSONDecodeError:
            # 如果无法解析JSON，返回一个基本的结构
            logger.error(f"无法解析结构化会议摘要JSON: {result[:100]}...")
            return {
                "summary": "无法生成结构化摘要。",
                "agenda": "",
                "decisions": "",
                "action_items": [],
                "key_points": []
            }

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
        "list_templates": service.list_templates,
        "generate_structured_meeting_summary": service.generate_structured_meeting_summary
    })
