#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
本地模型测试脚本
用于测试本地 Whisper 和 LLM 模型的集成
"""

import os
import sys
import time
import logging
import argparse
import yaml
from pathlib import Path

# 添加项目根目录到 Python 路径
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_local_models")

def test_local_whisper(config, audio_path=None):
    """
    测试本地 Whisper 模型
    
    Args:
        config: 配置信息
        audio_path: 音频文件路径，如果为 None，则使用示例音频
    
    Returns:
        测试结果
    """
    try:
        # 检查是否启用了本地 Whisper 模型
        whisper_config = config.get("meeting", {}).get("whisper", {})
        use_local = whisper_config.get("use_local", False)
        
        if not use_local:
            logger.error("未启用本地 Whisper 模型")
            return False
        
        # 检查模型路径
        model_path = whisper_config.get("model_path", "")
        if not model_path or not os.path.exists(model_path):
            logger.error(f"Whisper 模型路径不存在: {model_path}")
            return False
        
        # 如果未提供音频文件，使用示例音频
        if audio_path is None:
            # 查找示例音频文件
            examples_dir = os.path.join(root_dir, "examples")
            if not os.path.exists(examples_dir):
                os.makedirs(examples_dir, exist_ok=True)
            
            # 检查是否有示例音频文件
            audio_files = [f for f in os.listdir(examples_dir) 
                          if f.endswith(".wav") or f.endswith(".mp3")]
            
            if not audio_files:
                logger.error("未找到示例音频文件")
                return False
            
            audio_path = os.path.join(examples_dir, audio_files[0])
        
        # 检查音频文件是否存在
        if not os.path.exists(audio_path):
            logger.error(f"音频文件不存在: {audio_path}")
            return False
        
        # 导入本地 Whisper 组件
        from mcp.langraph.local_whisper_component import LocalWhisperComponent
        
        # 创建本地 Whisper 组件
        logger.info("创建本地 Whisper 组件")
        whisper_component = LocalWhisperComponent(config)
        
        # 检查组件是否初始化成功
        if whisper_component.whisper_model is None:
            logger.error("Whisper 模型初始化失败")
            return False
        
        # 创建测试状态
        from mcp.langraph.core import MCPState
        state = MCPState()
        state.inputs["audio_path"] = audio_path
        
        # 执行转录
        logger.info(f"开始转录音频: {audio_path}")
        start_time = time.time()
        result_state = whisper_component.process(state)
        processing_time = time.time() - start_time
        
        # 检查转录结果
        if "error" in result_state.outputs:
            logger.error(f"转录失败: {result_state.outputs['error']}")
            return False
        
        # 输出转录结果
        transcription = result_state.outputs.get("transcription", {})
        text = transcription.get("text", "")
        
        logger.info(f"转录完成，耗时: {processing_time:.2f}秒")
        logger.info(f"转录结果: {text}")
        
        return True
    
    except Exception as e:
        logger.exception(f"测试本地 Whisper 模型失败: {str(e)}")
        return False

def test_local_llm(config, prompt=None):
    """
    测试本地 LLM 模型
    
    Args:
        config: 配置信息
        prompt: 提示文本，如果为 None，则使用默认提示
    
    Returns:
        测试结果
    """
    try:
        # 检查是否启用了本地 LLM 模型
        llm_config = config.get("llm", {})
        use_local = llm_config.get("local", {}).get("enabled", False)
        
        if not use_local:
            logger.error("未启用本地 LLM 模型")
            return False
        
        # 检查模型路径
        model_path = llm_config.get("model_path", "")
        if not model_path or not os.path.exists(model_path):
            logger.error(f"LLM 模型路径不存在: {model_path}")
            return False
        
        # 如果未提供提示文本，使用默认提示
        if prompt is None:
            prompt = "你好，请介绍一下你自己。"
        
        # 导入本地 LLM 模块
        from mcp.local_llm import LocalLLM
        
        # 创建本地 LLM 实例
        logger.info("创建本地 LLM 实例")
        local_llm = LocalLLM(model_dir=model_path)
        
        # 执行生成
        logger.info(f"开始生成文本，提示: {prompt}")
        start_time = time.time()
        result = local_llm.generate(prompt=prompt, max_tokens=512, temperature=0.7)
        processing_time = time.time() - start_time
        
        # 输出生成结果
        logger.info(f"生成完成，耗时: {processing_time:.2f}秒")
        logger.info(f"生成结果: {result}")
        
        return True
    
    except Exception as e:
        logger.exception(f"测试本地 LLM 模型失败: {str(e)}")
        return False

def test_langraph_with_local_models(config):
    """
    测试使用本地模型的 Langraph 架构
    
    Args:
        config: 配置信息
    
    Returns:
        测试结果
    """
    try:
        # 导入 Langraph 核心组件
        from mcp.langraph.core import MCPGraph
        from mcp.langraph.transcription import create_transcription_component
        from mcp.langraph.llm_adapter import create_llm_adapter_component
        
        # 创建转录组件
        logger.info("创建转录组件")
        transcription_component = create_transcription_component(config)
        
        # 创建 LLM 适配器组件
        logger.info("创建 LLM 适配器组件")
        llm_component = create_llm_adapter_component(config)
        
        # 创建 Langraph 图
        logger.info("创建 Langraph 图")
        graph = MCPGraph()
        
        # 添加组件
        graph.add_component("transcription", transcription_component)
        graph.add_component("llm", llm_component)
        
        # 添加边
        graph.add_edge("transcription", "llm")
        
        # 查找示例音频文件
        examples_dir = os.path.join(root_dir, "examples")
        audio_files = [f for f in os.listdir(examples_dir) 
                      if f.endswith(".wav") or f.endswith(".mp3")]
        
        if not audio_files:
            logger.error("未找到示例音频文件")
            return False
        
        audio_path = os.path.join(examples_dir, audio_files[0])
        
        # 创建初始状态
        from mcp.langraph.core import MCPState
        state = MCPState()
        state.inputs["audio_path"] = audio_path
        state.inputs["prompt_template"] = "请总结以下文本内容：\n{text}"
        
        # 执行图
        logger.info("执行 Langraph 图")
        start_time = time.time()
        result_state = graph.run(state)
        processing_time = time.time() - start_time
        
        # 输出结果
        logger.info(f"图执行完成，耗时: {processing_time:.2f}秒")
        
        # 检查转录结果
        if "transcription" in result_state.outputs:
            transcription = result_state.outputs["transcription"]
            logger.info(f"转录结果: {transcription.get('text', '')}")
        
        # 检查 LLM 结果
        if "llm_response" in result_state.outputs:
            llm_response = result_state.outputs["llm_response"]
            logger.info(f"LLM 响应: {llm_response}")
        
        return True
    
    except Exception as e:
        logger.exception(f"测试 Langraph 架构失败: {str(e)}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="测试本地模型")
    parser.add_argument("--whisper", action="store_true", help="测试本地 Whisper 模型")
    parser.add_argument("--llm", action="store_true", help="测试本地 LLM 模型")
    parser.add_argument("--langraph", action="store_true", help="测试 Langraph 架构")
    parser.add_argument("--audio", type=str, help="音频文件路径")
    parser.add_argument("--prompt", type=str, help="LLM 提示文本")
    
    args = parser.parse_args()
    
    # 加载配置
    config_path = os.path.join(root_dir, "config.yaml")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 测试本地 Whisper 模型
    if args.whisper:
        logger.info("测试本地 Whisper 模型")
        if test_local_whisper(config, args.audio):
            logger.info("本地 Whisper 模型测试成功")
        else:
            logger.error("本地 Whisper 模型测试失败")
    
    # 测试本地 LLM 模型
    if args.llm:
        logger.info("测试本地 LLM 模型")
        if test_local_llm(config, args.prompt):
            logger.info("本地 LLM 模型测试成功")
        else:
            logger.error("本地 LLM 模型测试失败")
    
    # 测试 Langraph 架构
    if args.langraph:
        logger.info("测试 Langraph 架构")
        if test_langraph_with_local_models(config):
            logger.info("Langraph 架构测试成功")
        else:
            logger.error("Langraph 架构测试失败")
    
    # 如果没有指定任何操作，显示帮助
    if not args.whisper and not args.llm and not args.langraph:
        parser.print_help()

if __name__ == "__main__":
    main()
