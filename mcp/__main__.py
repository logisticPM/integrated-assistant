#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MCP Server Entry Point
This module serves as the main entry point when running 'python -m mcp.server'
"""

import os
import sys
import yaml
import logging
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_main")

def main():
    """Main entry point for the MCP server"""
    parser = argparse.ArgumentParser(description="MCP Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Server host address")
    parser.add_argument("--port", type=int, default=7860, help="Server port")
    
    args = parser.parse_args()
    
    # Get project root directory
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    # Load configuration
    config_path = os.path.join(root_dir, "config.yaml")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        return 1
    
    # Override configuration with command line arguments
    if "mcp" not in config:
        config["mcp"] = {}
    
    config["mcp"]["server_host"] = args.host
    config["mcp"]["server_port"] = args.port
    
    if "max_workers" not in config["mcp"]:
        config["mcp"]["max_workers"] = 10
    
    # Import server module and start server
    from mcp.server import MCPServer
    
    # Create and start server
    server = MCPServer(config)
    
    # Register services
    from mcp.transcription import register_transcription_service
    from mcp.llm_adapter import register_llm_service
    from mcp.vector_service import register_vector_service
    from mcp.email_service import register_email_service
    from mcp.gmail_auth import register_gmail_auth_service
    from mcp.chatbot_service import register_chatbot_service
    from mcp.gmail_service import register_gmail_service
    from mcp.email_analysis import register_email_analysis_service
    from mcp.meeting_service import register_meeting_service
    
    # Register all services
    register_transcription_service(server)
    register_llm_service(server)
    register_vector_service(server)
    register_email_service(server)
    register_gmail_auth_service(server)
    register_chatbot_service(server)
    register_gmail_service(server)
    
    try:
        register_email_analysis_service(server)
    except ImportError as e:
        logger.warning(f"Email analysis service not available: {str(e)}")
        logger.warning("Some email analysis features may not be available")
    
    register_meeting_service(server)
    
    # Start the server (this will block until the server is stopped)
    logger.info(f"Starting MCP server at {args.host}:{args.port}")
    server.start(args.host, args.port)

if __name__ == "__main__":
    sys.exit(main())
