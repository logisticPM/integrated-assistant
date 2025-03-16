#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Integrated Assistant Startup Script
One-click startup for the integrated assistant service
"""

import os
import sys
import subprocess
import logging
import argparse
import webbrowser
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("start")

# Project root directory
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))

def check_whisper_installation():
    """Check if Whisper is installed"""
    try:
        import whisper
        return True
    except ImportError:
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Integrated Assistant Startup Script")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Server host address")
    parser.add_argument("--port", type=int, default=7860, help="Server port")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    parser.add_argument("--setup", action="store_true", help="Run setup script before starting")
    
    args = parser.parse_args()
    
    # Run setup script if needed
    if args.setup:
        logger.info("Running setup script...")
        setup_script = os.path.join(ROOT_DIR, "scripts", "setup_all.py")
        try:
            subprocess.run([sys.executable, setup_script], check=True, shell=True)
        except subprocess.CalledProcessError:
            logger.warning("Setup script failed, attempting to continue with startup")
    
    # Check Whisper installation
    if not check_whisper_installation():
        logger.warning("Whisper not installed, speech transcription may be limited")
        print("\nNote: Whisper is not installed, speech transcription will use simulated implementation")
        print("For full speech transcription functionality, run: python scripts\\setup_whisper.py\n")
    
    # Start server
    logger.info(f"Starting integrated assistant service at: {args.host}:{args.port}")
    
    # Build startup command
    env = os.environ.copy()
    env["PYTHONPATH"] = ROOT_DIR
    
    # Use shell=True for Windows compatibility
    server_process = subprocess.Popen(
        f"{sys.executable} -m mcp.server",
        cwd=ROOT_DIR,
        env=env,
        shell=True
    )
    
    # Wait for server to start
    time.sleep(2)
    
    # Check if server started successfully
    if server_process.poll() is not None:
        logger.error("Server failed to start")
        return 1
    
    # Start frontend UI
    ui_url = f"http://localhost:{args.port}"
    ui_process = subprocess.Popen(
        f"{sys.executable} -m frontend.app --host {args.host} --port {str(args.port)}",
        cwd=ROOT_DIR,
        env=env,
        shell=True
    )
    
    # Wait for UI to start
    time.sleep(2)
    
    # Open browser automatically
    if not args.no_browser:
        logger.info(f"Opening UI in browser: {ui_url}")
        webbrowser.open(ui_url)
    
    print("\n" + "=" * 50)
    print(f"Integrated Assistant started successfully!")
    print(f"Access URL: {ui_url}")
    print("Press Ctrl+C to stop the service")
    print("=" * 50 + "\n")
    
    try:
        # Wait for UI process to end
        ui_process.wait()
    except KeyboardInterrupt:
        logger.info("Received stop signal, shutting down services...")
    finally:
        # Ensure both processes are terminated
        if ui_process.poll() is None:
            ui_process.terminate()
        
        if server_process.poll() is None:
            server_process.terminate()
    
    logger.info("Integrated Assistant service stopped")
    return 0

if __name__ == "__main__":
    sys.exit(main())
