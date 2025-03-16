#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试 langraph 架构功能
"""

import os
import sys
import logging
import json
import argparse
from pathlib import Path

# 添加项目根目录到 Python 路径
ROOT_DIR = Path(__file__).parent.parent.absolute()
sys.path.append(str(ROOT_DIR))

from mcp.langraph.core import MCPComponent, MCPState, MCPGraph
from mcp.langraph.transcription import TranscriptionService
from mcp.langraph.llm_adapter import LLMService
from mcp.langraph.vector_service import VectorService
from mcp.langraph.tool_service import ToolService
from mcp.langraph.agent_service import AgentServiceGraph
from mcp.langraph.meeting_service import MeetingServiceGraph
from mcp.langraph.mcp_server import MCPServer, create_mcp_server
from mcp.langraph.integration import LangraphIntegration

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_langraph")

def load_config(config_path):
    """加载配置"""
    import yaml
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"加载配置失败: {e}")
        return {}

def test_transcription(config):
    """测试转录服务"""
    logger.info("测试转录服务...")
    
    # 创建转录服务
    transcription_service = TranscriptionService(config)
    
    # 测试音频文件路径
    audio_dir = os.path.join(ROOT_DIR, "tests", "data")
    os.makedirs(audio_dir, exist_ok=True)
    
    # 检查是否有测试音频文件
    audio_files = [f for f in os.listdir(audio_dir) if f.endswith((".wav", ".mp3", ".m4a"))]
    
    if not audio_files:
        logger.warning(f"未找到测试音频文件，请将测试音频文件放置在 {audio_dir} 目录下")
        return False
    
    # 测试转录
    for audio_file in audio_files:
        audio_path = os.path.join(audio_dir, audio_file)
        logger.info(f"转录音频: {audio_path}")
        
        try:
            result = transcription_service.transcribe(audio_path)
            logger.info(f"转录结果: {result}")
            
            if "text" in result:
                logger.info("转录服务测试成功")
                return True
            else:
                logger.error("转录结果中缺少 text 字段")
                return False
        
        except Exception as e:
            logger.error(f"转录失败: {e}")
            return False
    
    return False

def test_llm_service(config):
    """测试 LLM 服务"""
    logger.info("测试 LLM 服务...")
    
    # 创建 LLM 服务
    llm_service = LLMService(config)
    
    # 测试查询
    query = "你好，请介绍一下自己。"
    logger.info(f"查询: {query}")
    
    try:
        result = llm_service.generate(query)
        logger.info(f"生成结果: {result}")
        
        if result:
            logger.info("LLM 服务测试成功")
            return True
        else:
            logger.error("生成结果为空")
            return False
    
    except Exception as e:
        logger.error(f"生成失败: {e}")
        return False

def test_vector_service(config):
    """测试向量服务"""
    logger.info("测试向量服务...")
    
    # 创建向量服务
    vector_service = VectorService(config)
    
    # 测试文档
    documents = [
        "这是第一个测试文档，用于测试向量服务。",
        "这是第二个测试文档，包含一些不同的内容。",
        "这是第三个测试文档，与前两个有一些相似之处。"
    ]
    
    # 添加文档
    try:
        logger.info("添加文档...")
        vector_service.add_texts(documents)
        
        # 测试搜索
        query = "测试文档"
        logger.info(f"搜索: {query}")
        
        results = vector_service.search(query)
        logger.info(f"搜索结果: {results}")
        
        if results:
            logger.info("向量服务测试成功")
            return True
        else:
            logger.error("搜索结果为空")
            return False
    
    except Exception as e:
        logger.error(f"向量服务测试失败: {e}")
        return False

def test_tool_service(config):
    """测试工具服务"""
    logger.info("测试工具服务...")
    
    # 创建工具服务
    tool_service = ToolService(config)
    
    # 测试搜索工具
    tool_name = "web_search"
    action = "search"
    parameters = {"query": "langraph python"}
    
    logger.info(f"执行工具: {tool_name}.{action}({parameters})")
    
    try:
        result = tool_service.execute_tool(tool_name, action, parameters)
        logger.info(f"工具执行结果: {result}")
        
        if result:
            logger.info("工具服务测试成功")
            return True
        else:
            logger.error("工具执行结果为空")
            return False
    
    except Exception as e:
        logger.error(f"工具执行失败: {e}")
        return False

def test_agent_service(config):
    """测试代理服务"""
    logger.info("测试代理服务...")
    
    # 创建代理服务
    agent_service = AgentServiceGraph(config)
    
    # 测试输入
    input_text = "你好，请告诉我今天的天气。"
    agent_type = "simple"
    history = []
    
    logger.info(f"代理输入: {input_text}")
    
    try:
        result = agent_service.process_input(input_text, agent_type, history)
        logger.info(f"代理处理结果: {result}")
        
        if "response" in result:
            logger.info("代理服务测试成功")
            return True
        else:
            logger.error("代理处理结果中缺少 response 字段")
            return False
    
    except Exception as e:
        logger.error(f"代理处理失败: {e}")
        return False

def test_meeting_service(config):
    """测试会议服务"""
    logger.info("测试会议服务...")
    
    # 创建会议服务
    meeting_service = MeetingServiceGraph(config)
    
    # 测试音频文件路径
    audio_dir = os.path.join(ROOT_DIR, "tests", "data")
    os.makedirs(audio_dir, exist_ok=True)
    
    # 检查是否有测试音频文件
    audio_files = [f for f in os.listdir(audio_dir) if f.endswith((".wav", ".mp3", ".m4a"))]
    
    if not audio_files:
        logger.warning(f"未找到测试音频文件，请将测试音频文件放置在 {audio_dir} 目录下")
        return False
    
    # 测试处理会议
    audio_path = os.path.join(audio_dir, audio_files[0])
    meeting_id = "test_meeting_001"
    
    logger.info(f"处理会议: {audio_path} (ID: {meeting_id})")
    
    try:
        result = meeting_service.process_meeting(audio_path, meeting_id)
        logger.info(f"会议处理结果: {result}")
        
        if "summary" in result:
            logger.info("会议服务测试成功")
            return True
        else:
            logger.error("会议处理结果中缺少 summary 字段")
            return False
    
    except Exception as e:
        logger.error(f"会议处理失败: {e}")
        return False

def test_mcp_server(config):
    """测试 MCP 服务器"""
    logger.info("测试 MCP 服务器...")
    
    # 创建 MCP 服务器
    mcp_server = create_mcp_server(config)
    
    # 测试请求
    request = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {
            "input": "你好，请介绍一下自己。",
            "agent_type": "simple",
            "history": []
        },
        "id": "test_001"
    }
    
    logger.info(f"发送请求: {request}")
    
    try:
        response = mcp_server.handle_request_sync(request)
        logger.info(f"响应: {response}")
        
        if "result" in response:
            logger.info("MCP 服务器测试成功")
            return True
        elif "error" in response:
            logger.error(f"MCP 服务器返回错误: {response['error']}")
            return False
        else:
            logger.error("MCP 服务器响应中既没有 result 也没有 error")
            return False
    
    except Exception as e:
        logger.error(f"MCP 服务器处理请求失败: {e}")
        return False

def test_integration(config):
    """测试集成"""
    logger.info("测试集成...")
    
    # 创建 Langraph 集成
    integration = LangraphIntegration()
    integration.initialize()
    
    # 测试集成
    try:
        result = integration.integrate_with_server()
        
        if result:
            logger.info("集成测试成功")
            return True
        else:
            logger.error("集成失败")
            return False
    
    except Exception as e:
        logger.error(f"集成测试失败: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="测试 langraph 架构功能")
    parser.add_argument("--config", type=str, default=os.path.join(ROOT_DIR, "config.yaml"), help="配置文件路径")
    parser.add_argument("--test", type=str, choices=["all", "transcription", "llm", "vector", "tool", "agent", "meeting", "server", "integration"], default="all", help="要测试的组件")
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config(args.config)
    
    # 测试结果
    results = {}
    
    # 运行测试
    if args.test == "all" or args.test == "transcription":
        results["transcription"] = test_transcription(config)
    
    if args.test == "all" or args.test == "llm":
        results["llm"] = test_llm_service(config)
    
    if args.test == "all" or args.test == "vector":
        results["vector"] = test_vector_service(config)
    
    if args.test == "all" or args.test == "tool":
        results["tool"] = test_tool_service(config)
    
    if args.test == "all" or args.test == "agent":
        results["agent"] = test_agent_service(config)
    
    if args.test == "all" or args.test == "meeting":
        results["meeting"] = test_meeting_service(config)
    
    if args.test == "all" or args.test == "server":
        results["server"] = test_mcp_server(config)
    
    if args.test == "all" or args.test == "integration":
        results["integration"] = test_integration(config)
    
    # 输出测试结果
    logger.info("测试结果:")
    for component, result in results.items():
        logger.info(f"- {component}: {'成功' if result else '失败'}")
    
    # 检查是否所有测试都成功
    if all(results.values()):
        logger.info("所有测试都成功")
        return 0
    else:
        logger.error("部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
