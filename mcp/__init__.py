#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MCP模块 - 提供模块间通信服务
"""

from mcp.client import MCPClient
from mcp.server import MCPServer, start_mcp_server

__all__ = ["MCPClient", "MCPServer", "start_mcp_server"]
