#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Langraph 架构会议处理示例
展示如何使用 langraph 架构处理会议录音
"""

import os
import sys
import logging
import time
import yaml
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

# 添加项目根目录到 Python 路径
ROOT_DIR = Path(__file__).parent.parent.absolute()
sys.path.append(str(ROOT_DIR))

from mcp.langraph.core import MCPComponent, MCPState, MCPGraph
from mcp.langraph.transcription import TranscriptionService
from mcp.langraph.llm_adapter import LLMService
from mcp.langraph.vector_service import VectorService
from mcp.langraph.meeting_service import MeetingServiceGraph
from mcp.langraph.anythingllm_service import AnythingLLMService
from mcp.langraph.anythingllm_component import AnythingLLMComponent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("demo_langraph_meeting")

def load_config(config_path):
    """加载配置"""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"加载配置失败: {e}")
        return {}

class MeetingProcessState(MCPState):
    """会议处理状态"""
    audio_path: Optional[str] = None
    meeting_id: Optional[str] = None
    transcription: Optional[Dict[str, Any]] = None
    summary: Optional[Dict[str, Any]] = None
    action_items: Optional[List[Dict[str, Any]]] = None
    anythingllm_workspace: Optional[str] = None
    knowledge_results: Optional[List[Dict[str, Any]]] = None
    participants: Optional[List[str]] = None
    topics: Optional[List[str]] = None
    stored: bool = False
    error: Optional[str] = None

class AudioLoaderComponent(MCPComponent):
    """音频加载组件"""
    
    def __init__(self, name="audio_loader", config=None):
        super().__init__(name=name, description="加载音频文件")
        self.config = config or {}
    
    def to_runnable(self):
        def _run(state: MeetingProcessState, config=None):
            logger.info(f"加载音频文件: {state.audio_path}")
            
            if not state.audio_path:
                return {"error": "未指定音频文件路径"}
            
            if not os.path.exists(state.audio_path):
                return {"error": f"音频文件不存在: {state.audio_path}"}
            
            # 生成会议 ID（如果未提供）
            if not state.meeting_id:
                state.meeting_id = f"meeting_{int(time.time())}"
                logger.info(f"生成会议 ID: {state.meeting_id}")
            
            return {}
        
        return _run

class TranscriptionComponent(MCPComponent):
    """转录组件"""
    
    def __init__(self, name="transcription", config=None, transcription_service=None):
        super().__init__(name=name, description="转录音频文件")
        self.config = config or {}
        self.transcription_service = transcription_service or TranscriptionService(self.config)
    
    def to_runnable(self):
        def _run(state: MeetingProcessState, config=None):
            if state.error:
                return {}
            
            logger.info(f"转录音频: {state.audio_path}")
            
            try:
                # 转录音频
                result = self.transcription_service.transcribe(state.audio_path)
                
                return {
                    "transcription": result
                }
            
            except Exception as e:
                logger.error(f"转录失败: {str(e)}")
                return {"error": f"转录失败: {str(e)}"}
        
        return _run

class SummaryComponent(MCPComponent):
    """摘要组件"""
    
    def __init__(self, name="summary", config=None, llm_service=None, anythingllm_service=None):
        super().__init__(name=name, description="生成会议摘要")
        self.config = config or {}
        self.llm_service = llm_service or LLMService(self.config)
        
        # 初始化 AnythingLLM 服务
        self.anythingllm_service = anythingllm_service
        if not self.anythingllm_service and self.config.get("anythingllm", {}).get("enabled", False):
            from mcp.langraph.anythingllm_service import AnythingLLMService
            self.anythingllm_service = AnythingLLMService(self.config)
    
    def to_runnable(self):
        def _run(state: MeetingProcessState, config=None):
            if state.error or not state.transcription:
                return {}
            
            logger.info("生成会议摘要")
            
            try:
                # 获取转录文本
                text = state.transcription.get("text", "")
                
                if not text:
                    return {"error": "转录文本为空"}
                
                # 生成摘要提示
                prompt = f"""
                请根据以下会议转录内容，生成一个结构化的会议摘要，包括：
                1. 会议主题
                2. 主要讨论点
                3. 决策和结论
                4. 行动项（包括负责人和截止日期，如有提及）
                
                会议转录：
                {text}
                
                请以 JSON 格式返回结果，包括 summary（摘要）、topics（主题列表）、action_items（行动项列表）和 participants（参与者列表）字段。
                """
                
                # 优先使用 AnythingLLM API 生成摘要
                summary_text = None
                if self.anythingllm_service:
                    try:
                        logger.info("使用 AnythingLLM API 生成摘要")
                        workspace_slug = state.anythingllm_workspace
                        
                        # 如果有工作区，使用工作区聊天
                        if workspace_slug:
                            chat_result = self.anythingllm_service.chat_with_workspace(
                                slug=workspace_slug,
                                message=prompt,
                                chat_mode="query"  # 使用查询模式以获取更精确的回答
                            )
                            if chat_result and "response" in chat_result:
                                summary_text = chat_result["response"]
                                logger.info("成功使用 AnythingLLM 工作区生成摘要")
                        
                        # 如果没有工作区或工作区聊天失败，使用聊天完成
                        if not summary_text:
                            chat_messages = [
                                {"role": "system", "content": "你是一个专业的会议摘要助手，擅长从会议转录中提取关键信息并生成结构化摘要。"},
                                {"role": "user", "content": prompt}
                            ]
                            completion_result = self.anythingllm_service.chat_completion(
                                messages=chat_messages,
                                temperature=0.3
                            )
                            if completion_result and "choices" in completion_result:
                                summary_text = completion_result["choices"][0]["message"]["content"]
                                logger.info("成功使用 AnythingLLM 聊天完成生成摘要")
                    except Exception as e:
                        logger.error(f"使用 AnythingLLM 生成摘要失败: {str(e)}")
                        # 失败后将使用本地 LLM
                
                # 如果 AnythingLLM 摘要生成失败，使用本地 LLM
                if not summary_text:
                    logger.info("使用本地 LLM 生成摘要")
                    summary_text = self.llm_service.generate(prompt)
                
                # 解析摘要
                try:
                    import json
                    summary_data = json.loads(summary_text)
                except:
                    # 如果解析失败，使用原始文本
                    summary_data = {
                        "summary": summary_text,
                        "topics": [],
                        "action_items": [],
                        "participants": []
                    }
                
                return {
                    "summary": summary_data.get("summary", summary_text),
                    "topics": summary_data.get("topics", []),
                    "action_items": summary_data.get("action_items", []),
                    "participants": summary_data.get("participants", [])
                }
            
            except Exception as e:
                logger.error(f"生成摘要失败: {str(e)}")
                return {"error": f"生成摘要失败: {str(e)}"}
        
        return _run

class StorageComponent(MCPComponent):
    """存储组件"""
    
    def __init__(self, name="storage", config=None, vector_service=None):
        super().__init__(name=name, description="存储会议信息")
        self.config = config or {}
        self.vector_service = vector_service or VectorService(self.config)
    
    def to_runnable(self):
        def _run(state: MeetingProcessState, config=None):
            if state.error or not state.transcription or not state.summary:
                return {}
            
            logger.info(f"存储会议信息: {state.meeting_id}")
            
            try:
                # 构建会议文档
                meeting_doc = {
                    "meeting_id": state.meeting_id,
                    "transcription": state.transcription.get("text", ""),
                    "summary": state.summary,
                    "topics": state.topics,
                    "action_items": state.action_items,
                    "participants": state.participants,
                    "timestamp": time.time()
                }
                
                # 存储到向量数据库
                text_to_store = f"""
                会议 ID: {meeting_doc['meeting_id']}
                摘要: {meeting_doc['summary']}
                主题: {', '.join(meeting_doc['topics']) if meeting_doc['topics'] else '无'}
                转录: {meeting_doc['transcription']}
                """
                
                metadata = {
                    "meeting_id": meeting_doc['meeting_id'],
                    "timestamp": meeting_doc['timestamp'],
                    "topics": meeting_doc['topics'],
                    "participants": meeting_doc['participants']
                }
                
                self.vector_service.add_texts([text_to_store], [metadata])
                
                # 保存会议文档到文件
                meeting_dir = os.path.join(ROOT_DIR, "data", "meetings")
                os.makedirs(meeting_dir, exist_ok=True)
                
                meeting_file = os.path.join(meeting_dir, f"{state.meeting_id}.json")
                
                with open(meeting_file, "w", encoding="utf-8") as f:
                    import json
                    json.dump(meeting_doc, f, ensure_ascii=False, indent=2)
                
                logger.info(f"会议信息已保存到: {meeting_file}")
                
                return {"stored": True}
            
            except Exception as e:
                logger.error(f"存储会议信息失败: {str(e)}")
                return {"error": f"存储会议信息失败: {str(e)}"}
        
        return _run

class ReportComponent(MCPComponent):
    """报告组件"""
    
    def __init__(self, name="report", config=None):
        super().__init__(name=name, description="生成会议报告")
        self.config = config or {}
    
    def to_runnable(self):
        def _run(state: MeetingProcessState, config=None):
            if state.error:
                logger.error(f"处理失败: {state.error}")
                return {}
            
            logger.info(f"会议处理完成: {state.meeting_id}")
            
            # 打印会议信息
            print("\n" + "="*50)
            print(f"会议 ID: {state.meeting_id}")
            print("="*50)
            
            if state.transcription:
                print("\n转录:")
                print("-"*50)
                print(state.transcription.get("text", "无转录文本"))
            
            if state.summary:
                print("\n摘要:")
                print("-"*50)
                print(state.summary)
            
            if state.topics:
                print("\n主题:")
                print("-"*50)
                for i, topic in enumerate(state.topics, 1):
                    print(f"{i}. {topic}")
            
            if state.action_items:
                print("\n行动项:")
                print("-"*50)
                for i, item in enumerate(state.action_items, 1):
                    if isinstance(item, dict):
                        action = item.get("action", "")
                        assignee = item.get("assignee", "未分配")
                        deadline = item.get("deadline", "无截止日期")
                        print(f"{i}. {action} (负责人: {assignee}, 截止日期: {deadline})")
                    else:
                        print(f"{i}. {item}")
            
            if state.participants:
                print("\n参与者:")
                print("-"*50)
                for i, participant in enumerate(state.participants, 1):
                    print(f"{i}. {participant}")
            
            print("\n" + "="*50)
            
            if state.stored:
                print("会议信息已成功存储")
            else:
                print("警告: 会议信息未存储")
            
            print("="*50 + "\n")
            
            return {}
        
        return _run

class AnythingLLMComponent(MCPComponent):
    """AnythingLLM 组件"""
    
    def __init__(self, name="anythingllm", config=None, anythingllm_service=None):
        super().__init__(name=name, description="使用 AnythingLLM 处理会议信息")
        self.config = config or {}
        self.anythingllm_service = anythingllm_service or AnythingLLMService(self.config)
    
    def to_runnable(self):
        def _run(state: MeetingProcessState, config=None):
            if state.error:
                return {}
            
            logger.info("使用 AnythingLLM 处理会议信息")
            
            try:
                # 获取会议信息
                meeting_info = {
                    "meeting_id": state.meeting_id,
                    "transcription": state.transcription.get("text", ""),
                    "summary": state.summary,
                    "topics": state.topics,
                    "action_items": state.action_items,
                    "participants": state.participants
                }
                
                # 使用 AnythingLLM 处理会议信息
                response = self.anythingllm_service.process_meeting(meeting_info)
                
                if response:
                    state.anythingllm_workspace = response.get("workspace_slug")
                    state.knowledge_results = response.get("knowledge_results", [])
                
                return {}
            
            except Exception as e:
                logger.error(f"使用 AnythingLLM 处理会议信息失败: {str(e)}")
                return {"error": f"使用 AnythingLLM 处理会议信息失败: {str(e)}"}
        
        return _run

def create_meeting_process_graph(config):
    """
    创建会议处理图
    
    Args:
        config: 配置信息
    
    Returns:
        会议处理图
    """
    # 初始化服务
    try:
        from mcp.langraph.anythingllm_service import AnythingLLMService
        anythingllm_enabled = config.get("anythingllm", {}).get("enabled", False)
        anythingllm_service = AnythingLLMService(config) if anythingllm_enabled else None
        
        if anythingllm_service and anythingllm_service.test_connection():
            logger.info("AnythingLLM 服务连接成功")
        elif anythingllm_enabled:
            logger.warning("AnythingLLM 服务连接失败，将使用本地服务")
            anythingllm_service = None
    except Exception as e:
        logger.error(f"初始化 AnythingLLM 服务失败: {str(e)}")
        anythingllm_service = None
    
    # 创建组件
    audio_loader = AudioLoaderComponent(config=config)
    
    # 优先使用 AnythingLLM 转录组件
    if anythingllm_service:
        from mcp.langraph.transcription import AnythingLLMTranscriptionComponent
        transcription = AnythingLLMTranscriptionComponent(config=config)
    else:
        from mcp.langraph.transcription import create_transcription_component
        transcription = create_transcription_component(config)
    
    # 创建摘要组件，传入 AnythingLLM 服务
    summary = SummaryComponent(config=config, anythingllm_service=anythingllm_service)
    
    # 创建存储组件
    storage = StorageComponent(config=config)
    
    # 创建报告组件
    report = ReportComponent(config=config)
    
    # 创建 AnythingLLM 组件
    anythingllm = AnythingLLMComponent(config=config, anythingllm_service=anythingllm_service)
    
    # 创建图
    graph = MCPGraph()
    
    # 添加节点
    graph.add_node(audio_loader)
    graph.add_node(transcription)
    graph.add_node(summary)
    graph.add_node(storage)
    graph.add_node(report)
    graph.add_node(anythingllm)
    
    # 添加边
    graph.add_edge(audio_loader, transcription)
    graph.add_edge(transcription, summary)
    graph.add_edge(summary, storage)
    graph.add_edge(storage, report)
    
    # 如果启用了 AnythingLLM，添加相关边
    if anythingllm_service:
        graph.add_edge(transcription, anythingllm)
        graph.add_edge(summary, anythingllm)
        graph.add_edge(anythingllm, report)
    
    return graph

def process_meeting(audio_path, meeting_id=None, config=None):
    """处理会议"""
    if config is None:
        config = {}
    
    if meeting_id is None:
        meeting_id = f"meeting_{int(time.time())}"
    
    # 创建初始状态
    state = MeetingProcessState(
        audio_path=audio_path,
        meeting_id=meeting_id
    )
    
    # 创建处理图
    graph = create_meeting_process_graph(config)
    
    # 运行图
    final_state = graph.run(state)
    
    return final_state

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="会议处理演示")
    parser.add_argument("--audio", required=True, help="音频文件路径")
    parser.add_argument("--meeting-id", help="会议 ID")
    parser.add_argument("--config", default="config/meeting_process.yaml", help="配置文件路径")
    parser.add_argument("--use-anythingllm", action="store_true", help="是否使用 AnythingLLM")
    parser.add_argument("--query", help="使用 AnythingLLM 查询会议内容")
    
    args = parser.parse_args()
    
    # 加载配置
    config_path = os.path.join(ROOT_DIR, args.config)
    config = load_config(config_path)
    
    # 如果指定使用 AnythingLLM，添加相关配置
    if args.use_anythingllm:
        if "anythingllm" not in config:
            config["anythingllm"] = {}
        config["anythingllm"]["operation"] = "process_meeting"
    
    # 处理会议
    final_state = process_meeting(args.audio, args.meeting_id, config)
    
    # 如果指定了查询，使用 AnythingLLM 查询会议内容
    if args.query and hasattr(final_state, "anythingllm_workspace"):
        anythingllm_service = AnythingLLMService(config.get("anythingllm", {}))
        workspace_slug = final_state.anythingllm_workspace
        
        print(f"\n查询: {args.query}")
        response = anythingllm_service.chat_with_workspace(workspace_slug, args.query, chat_mode="query")
        if response:
            print(f"\n回答: {response.get('textResponse', '无回答')}")
        else:
            print("\n查询失败")
    
    print(f"\n会议处理完成，会议 ID: {final_state.meeting_id}")
    if hasattr(final_state, "anythingllm_workspace"):
        print(f"AnythingLLM 工作区: {final_state.anythingllm_workspace}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
