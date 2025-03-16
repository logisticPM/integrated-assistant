#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基于 langraph 的 MCP 服务器主入口
提供 MCP 服务功能
"""

import os
import sys
import logging
import time
import json
import yaml
import argparse
import asyncio
from typing import Dict, Any, List, Optional, Union, Callable
from aiohttp import web

from mcp.langraph.mcp_server import create_mcp_server

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("langraph.main")

def load_config(config_path: str) -> Dict[str, Any]:
    """
    加载配置
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        配置
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        logger.info(f"已加载配置: {config_path}")
        return config
    
    except Exception as e:
        logger.error(f"加载配置失败: {str(e)}")
        return {}

async def handle_jsonrpc(request, mcp_server):
    """
    处理 JSON-RPC 请求
    
    Args:
        request: HTTP 请求
        mcp_server: MCP 服务器
    
    Returns:
        HTTP 响应
    """
    try:
        # 解析请求
        request_data = await request.json()
        
        # 处理批量请求
        if isinstance(request_data, list):
            responses = []
            for req in request_data:
                response = await mcp_server.handle_request(req)
                responses.append(response)
            
            return web.json_response(responses)
        
        # 处理单个请求
        response = await mcp_server.handle_request(request_data)
        
        return web.json_response(response)
    
    except Exception as e:
        logger.error(f"处理请求失败: {str(e)}")
        
        return web.json_response({
            "jsonrpc": "2.0",
            "error": {
                "code": -32700,
                "message": f"解析错误: {str(e)}"
            },
            "id": None
        })

def create_app(config: Dict[str, Any]) -> web.Application:
    """
    创建 Web 应用
    
    Args:
        config: 配置
    
    Returns:
        Web 应用
    """
    # 创建 MCP 服务器
    mcp_server = create_mcp_server(config)
    
    # 创建 Web 应用
    app = web.Application()
    
    # 添加路由
    app.router.add_post("/jsonrpc", lambda request: handle_jsonrpc(request, mcp_server))
    
    # 添加关闭处理程序
    async def on_shutdown(app):
        mcp_server.stop()
    
    app.on_shutdown.append(on_shutdown)
    
    return app

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="基于 langraph 的 MCP 服务器")
    parser.add_argument("--config", type=str, default="config.yaml", help="配置文件路径")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="主机地址")
    parser.add_argument("--port", type=int, default=8000, help="端口")
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config(args.config)
    
    # 创建 Web 应用
    app = create_app(config)
    
    # 运行服务器
    web.run_app(app, host=args.host, port=args.port)
    
    logger.info(f"服务器已启动: http://{args.host}:{args.port}")

if __name__ == "__main__":
    main()
