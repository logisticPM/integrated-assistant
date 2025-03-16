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
    
    def __init__(self, name="summary", config=None, llm_service=None):
        super().__init__(name=name, description="生成会议摘要")
        self.config = config or {}
        self.llm_service = llm_service or LLMService(self.config)
    
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
                
                # 生成摘要
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

def create_meeting_process_graph(config):
    """创建会议处理图"""
    # 创建服务
    transcription_service = TranscriptionService(config)
    llm_service = LLMService(config)
    vector_service = VectorService(config)
    
    # 创建组件
    audio_loader = AudioLoaderComponent(config=config)
    transcription = TranscriptionComponent(config=config, transcription_service=transcription_service)
    summary = SummaryComponent(config=config, llm_service=llm_service)
    storage = StorageComponent(config=config, vector_service=vector_service)
    report = ReportComponent(config=config)
    
    # 创建图
    graph = MCPGraph("meeting_process", "会议处理流程")
    
    # 添加组件
    graph.add_component(audio_loader)
    graph.add_component(transcription)
    graph.add_component(summary)
    graph.add_component(storage)
    graph.add_component(report)
    
    # 定义边
    graph.add_edge(audio_loader, transcription)
    graph.add_edge(transcription, summary)
    graph.add_edge(summary, storage)
    graph.add_edge(storage, report)
    
    return graph

def process_meeting(audio_path, meeting_id=None, config=None):
    """处理会议"""
    # 创建会议处理图
    graph = create_meeting_process_graph(config)
    
    # 创建初始状态
    state = MeetingProcessState(
        audio_path=audio_path,
        meeting_id=meeting_id
    )
    
    # 运行图
    try:
        result = graph.run(state)
        return result
    except Exception as e:
        logger.error(f"运行会议处理图失败: {str(e)}")
        return MeetingProcessState(error=f"运行会议处理图失败: {str(e)}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Langraph 架构会议处理示例")
    parser.add_argument("--audio", type=str, required=True, help="音频文件路径")
    parser.add_argument("--meeting-id", type=str, help="会议 ID")
    parser.add_argument("--config", type=str, default=os.path.join(ROOT_DIR, "config.yaml"), help="配置文件路径")
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config(args.config)
    
    # 处理会议
    result = process_meeting(args.audio, args.meeting_id, config)
    
    # 检查结果
    if result.error:
        logger.error(f"会议处理失败: {result.error}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
