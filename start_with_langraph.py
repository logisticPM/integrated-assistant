#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Integrated Assistant Startup Script with Langraph Architecture
Provides one-click startup for the Integrated Assistant with Langraph architecture
"""

import os
import sys
import argparse
import subprocess
import logging
import webbrowser
import time
import yaml
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("start_with_langraph")

# Project root directory
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))

def load_config(config_path="config.yaml"):
    """
    Load configuration from YAML file
    
    Args:
        config_path: Path to configuration file
    
    Returns:
        Configuration dictionary
    """
    try:
        with open(os.path.join(ROOT_DIR, config_path), "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        return {}

def run_setup(setup_all=False):
    """
    Run setup scripts
    
    Args:
        setup_all: Whether to run the full setup
    
    Returns:
        Success status
    """
    try:
        if setup_all:
            setup_script = os.path.join(ROOT_DIR, "scripts", "setup_all_with_langraph.py")
            logger.info("Running full setup with Langraph support...")
            subprocess.run([sys.executable, setup_script, "--use-langraph"], check=True)
        else:
            setup_script = os.path.join(ROOT_DIR, "scripts", "setup_langraph.py")
            logger.info("Running Langraph setup...")
            subprocess.run([sys.executable, setup_script], check=True)
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Setup failed: {str(e)}")
        return False

def start_server(host="127.0.0.1", port=8000, config_path="config.yaml"):
    """
    Start the MCP server with Langraph architecture
    
    Args:
        host: Host address
        port: Port number
        config_path: Path to configuration file
    
    Returns:
        Server process
    """
    server_script = os.path.join(ROOT_DIR, "scripts", "langraph_server.py")
    cmd = [
        sys.executable,
        server_script,
        "--host", host,
        "--port", str(port),
        "--config", config_path
    ]
    
    logger.info(f"Starting MCP server with Langraph architecture on {host}:{port}...")
    
    # Start server process
    server_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    
    # Wait for server to start
    started = False
    for line in iter(server_process.stdout.readline, ""):
        print(line, end="")
        if "Server started" in line:
            started = True
            break
        if "Error" in line or "Failed" in line:
            logger.error("Server failed to start")
            return None
    
    if not started:
        logger.warning("Server may not have started properly")
    
    return server_process

def start_ui(host="127.0.0.1", port=8501):
    """
    Start the UI
    
    Args:
        host: Host address
        port: Port number
    
    Returns:
        UI process
    """
    ui_script = os.path.join(ROOT_DIR, "ui", "app.py")
    cmd = [
        sys.executable,
        ui_script,
        "--server-url", f"http://{host}:8000",
        "--host", host,
        "--port", str(port)
    ]
    
    logger.info(f"Starting UI on {host}:{port}...")
    
    # Start UI process
    ui_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    
    # Wait for UI to start
    started = False
    for line in iter(ui_process.stdout.readline, ""):
        print(line, end="")
        if "Streamlit app running" in line:
            started = True
            break
        if "Error" in line or "Failed" in line:
            logger.error("UI failed to start")
            return None
    
    if not started:
        logger.warning("UI may not have started properly")
    
    return ui_process

def open_browser(host="127.0.0.1", port=8501):
    """
    Open browser to access the UI
    
    Args:
        host: Host address
        port: Port number
    """
    url = f"http://{host}:{port}"
    logger.info(f"Opening browser at {url}...")
    webbrowser.open(url)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Integrated Assistant Startup with Langraph Architecture")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--ui-port", type=int, default=8501, help="UI port")
    parser.add_argument("--config", type=str, default="config.yaml", help="Configuration file path")
    parser.add_argument("--setup", action="store_true", help="Run Langraph setup before starting")
    parser.add_argument("--setup-all", action="store_true", help="Run full setup with Langraph support before starting")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    
    args = parser.parse_args()
    
    logger.info("Starting Integrated Assistant with Langraph Architecture")
    logger.info("=" * 50)
    
    # Run setup if requested
    if args.setup_all:
        if not run_setup(setup_all=True):
            logger.error("Full setup failed, but attempting to continue...")
    elif args.setup:
        if not run_setup():
            logger.error("Langraph setup failed, but attempting to continue...")
    
    # Load configuration
    config = load_config(args.config)
    
    # Start server
    server_process = start_server(args.host, args.port, args.config)
    if not server_process:
        logger.error("Failed to start server, exiting...")
        return 1
    
    # Start UI
    ui_process = start_ui(args.host, args.ui_port)
    if not ui_process:
        logger.error("Failed to start UI, terminating server...")
        server_process.terminate()
        return 1
    
    # Open browser
    if not args.no_browser:
        # Wait a moment for the UI to fully initialize
        time.sleep(2)
        open_browser(args.host, args.ui_port)
    
    logger.info("\n" + "=" * 50)
    logger.info(f"Integrated Assistant is running!")
    logger.info(f"Server: http://{args.host}:{args.port}")
    logger.info(f"UI: http://{args.host}:{args.ui_port}")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 50)
    
    try:
        # Keep the main process running
        while True:
            # Check if processes are still running
            if server_process.poll() is not None:
                logger.error("Server process terminated unexpectedly")
                if ui_process.poll() is None:
                    ui_process.terminate()
                return 1
            
            if ui_process.poll() is not None:
                logger.error("UI process terminated unexpectedly")
                if server_process.poll() is None:
                    server_process.terminate()
                return 1
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("Stopping Integrated Assistant...")
        
        # Terminate processes
        if ui_process.poll() is None:
            ui_process.terminate()
        
        if server_process.poll() is None:
            server_process.terminate()
        
        logger.info("Integrated Assistant stopped")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
