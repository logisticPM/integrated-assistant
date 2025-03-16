#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
聊天机器人服务模块 - 提供基于知识库的智能问答功能
支持选择不同项目的知识库
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
import uuid

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("chatbot_service")

class ChatbotService:
    """聊天机器人服务类，提供基于知识库的智能问答功能"""
    
    def __init__(self, config: Dict[str, Any], mcp_client):
        """
        初始化聊天机器人服务
        
        Args:
            config: 服务配置
            mcp_client: MCP客户端实例
        """
        self.config = config
        self.mcp_client = mcp_client
        self.projects_dir = config.get("chatbot", {}).get("projects_dir", "data/projects")
        
        # 确保项目目录存在
        os.makedirs(self.projects_dir, exist_ok=True)
        
        # 初始化默认项目
        self._init_default_project()
    
    def _init_default_project(self):
        """初始化默认项目"""
        default_project_dir = os.path.join(self.projects_dir, "default")
        os.makedirs(default_project_dir, exist_ok=True)
        
        # 创建项目配置文件
        config_file = os.path.join(default_project_dir, "config.json")
        if not os.path.exists(config_file):
            default_config = {
                "name": "默认项目",
                "description": "默认知识库项目",
                "created_at": "2025-03-15T00:00:00Z",
                "tables": ["documents", "chunks", "meetings", "emails"]
            }
            
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """
        获取项目列表
        
        Returns:
            项目列表
        """
        projects = []
        
        # 遍历项目目录
        for project_name in os.listdir(self.projects_dir):
            project_dir = os.path.join(self.projects_dir, project_name)
            
            # 检查是否是目录
            if not os.path.isdir(project_dir):
                continue
            
            # 读取项目配置
            config_file = os.path.join(project_dir, "config.json")
            if os.path.exists(config_file):
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    
                    projects.append({
                        "id": project_name,
                        "name": config.get("name", project_name),
                        "description": config.get("description", ""),
                        "created_at": config.get("created_at", "")
                    })
                except Exception as e:
                    logger.error(f"读取项目配置失败: {project_name}, {str(e)}")
        
        # 按名称排序
        projects.sort(key=lambda x: x["name"])
        
        return projects
    
    def create_project(self, name: str, description: str = "") -> str:
        """
        创建新项目
        
        Args:
            name: 项目名称
            description: 项目描述
        
        Returns:
            项目ID
        """
        # 生成项目ID
        project_id = str(uuid.uuid4())
        
        # 创建项目目录
        project_dir = os.path.join(self.projects_dir, project_id)
        os.makedirs(project_dir, exist_ok=True)
        
        # 创建项目配置
        config = {
            "name": name,
            "description": description,
            "created_at": "2025-03-15T00:00:00Z",
            "tables": ["documents", "chunks"]
        }
        
        # 保存项目配置
        config_file = os.path.join(project_dir, "config.json")
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        return project_id
    
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        获取项目信息
        
        Args:
            project_id: 项目ID
        
        Returns:
            项目信息
        """
        project_dir = os.path.join(self.projects_dir, project_id)
        
        # 检查项目是否存在
        if not os.path.isdir(project_dir):
            return None
        
        # 读取项目配置
        config_file = os.path.join(project_dir, "config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                return {
                    "id": project_id,
                    "name": config.get("name", project_id),
                    "description": config.get("description", ""),
                    "created_at": config.get("created_at", ""),
                    "tables": config.get("tables", [])
                }
            except Exception as e:
                logger.error(f"读取项目配置失败: {project_id}, {str(e)}")
        
        return None
    
    def delete_project(self, project_id: str) -> bool:
        """
        删除项目
        
        Args:
            project_id: 项目ID
        
        Returns:
            是否成功
        """
        # 不允许删除默认项目
        if project_id == "default":
            return False
        
        project_dir = os.path.join(self.projects_dir, project_id)
        
        # 检查项目是否存在
        if not os.path.isdir(project_dir):
            return False
        
        try:
            # 删除项目目录
            import shutil
            shutil.rmtree(project_dir)
            return True
        except Exception as e:
            logger.error(f"删除项目失败: {project_id}, {str(e)}")
            return False
    
    def chat(self, message: str, history: List[List[str]], project_id: str = "default", 
             category: str = None, temperature: float = 0.7, context_length: int = 5) -> str:
        """
        与聊天机器人对话
        
        Args:
            message: 用户消息
            history: 对话历史
            project_id: 项目ID
            category: 知识库类别
            temperature: 温度参数
            context_length: 上下文长度
        
        Returns:
            机器人回复
        """
        try:
            # 获取项目信息
            project = self.get_project(project_id)
            if not project:
                return f"错误: 项目 {project_id} 不存在"
            
            # 限制历史记录长度
            if len(history) > context_length:
                history = history[-context_length:]
            
            # 准备查询上下文
            context = []
            
            # 如果消息不为空，从知识库中搜索相关内容
            if message:
                # 获取嵌入向量
                embedding = self.mcp_client.call("llm.get_embedding", {
                    "text": message
                })
                
                # 搜索知识库
                search_params = {
                    "query_vector": embedding,
                    "limit": 5
                }
                
                # 如果指定了类别，添加过滤条件
                if category and category != "全部":
                    search_params["filter"] = {
                        "category": category
                    }
                
                # 从项目表中搜索
                for table_name in project["tables"]:
                    try:
                        results = self.mcp_client.call("vector_db.search", {
                            "table_name": table_name,
                            **search_params
                        })
                        
                        # 添加到上下文
                        for result in results:
                            if result["similarity"] > 0.7:  # 相似度阈值
                                context.append({
                                    "content": result["metadata"].get("content", ""),
                                    "source": result["metadata"].get("source", ""),
                                    "similarity": result["similarity"]
                                })
                    except Exception as e:
                        logger.error(f"搜索知识库失败: {table_name}, {str(e)}")
            
            # 准备提示词
            prompt = self._prepare_prompt(message, history, context)
            
            # 调用LLM生成回复
            response = self.mcp_client.call("llm.generate_text", {
                "prompt": prompt,
                "temperature": temperature,
                "max_tokens": 1000
            })
            
            return response
        
        except Exception as e:
            logger.exception(f"聊天失败: {str(e)}")
            return f"系统错误: {str(e)}"
    
    def _prepare_prompt(self, message: str, history: List[List[str]], context: List[Dict[str, Any]]) -> str:
        """
        准备提示词
        
        Args:
            message: 用户消息
            history: 对话历史
            context: 知识库上下文
        
        Returns:
            提示词
        """
        prompt = "你是一个智能助手，请根据提供的上下文信息回答用户的问题。\n\n"
        
        # 添加知识库上下文
        if context:
            prompt += "### 参考信息:\n"
            for i, item in enumerate(context):
                prompt += f"{i+1}. {item['content']}\n"
                if item.get("source"):
                    prompt += f"   来源: {item['source']}\n"
            prompt += "\n"
        
        # 添加对话历史
        if history:
            prompt += "### 对话历史:\n"
            for h in history:
                prompt += f"用户: {h[0]}\n"
                prompt += f"助手: {h[1]}\n"
            prompt += "\n"
        
        # 添加当前问题
        prompt += f"### 当前问题:\n{message}\n\n"
        prompt += "### 回答:"
        
        return prompt

def register_chatbot_service(server):
    """
    注册聊天机器人服务
    
    Args:
        server: MCP服务器实例
    """
    # 创建聊天机器人服务实例
    chatbot_service = ChatbotService(server.config, server.mcp_client)
    
    # 注册服务方法
    server.register_service("chatbot.list_projects", chatbot_service.list_projects)
    server.register_service("chatbot.create_project", chatbot_service.create_project)
    server.register_service("chatbot.get_project", chatbot_service.get_project)
    server.register_service("chatbot.delete_project", chatbot_service.delete_project)
    server.register_service("chatbot.chat", chatbot_service.chat)
    
    logger.info("聊天机器人服务已注册")
