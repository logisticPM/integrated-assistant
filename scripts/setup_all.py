#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Integrated Assistant One-Click Deployment Script
For installing and configuring all necessary components, including Whisper, knowledge base, and AnythingLLM integration
"""

import os
import sys
import argparse
import subprocess
import logging
import yaml
import time
import getpass
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("setup_all")

# Project root directory
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def run_script(script_name, args=None):
    """
    Run the specified Python script
    
    Args:
        script_name: Script name
        args: Command line arguments
    
    Returns:
        Success status
    """
    script_path = os.path.join(ROOT_DIR, "scripts", script_name)
    cmd = [sys.executable, script_path]
    
    if args:
        cmd.extend(args)
    
    logger.info(f"Running script: {script_name} {' '.join(args) if args else ''}")
    
    try:
        # Use shell=True for Windows compatibility
        result = subprocess.run(" ".join(cmd), check=True, shell=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to run script {script_name}: {str(e)}")
        return False

def update_config_anything_llm(api_key=None, api_url=None):
    """
    Update AnythingLLM settings in the configuration file
    
    Args:
        api_key: AnythingLLM API key
        api_url: AnythingLLM API URL
    
    Returns:
        Success status
    """
    config_path = os.path.join(ROOT_DIR, "config.yaml")
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        # Update AnythingLLM configuration
        if "llm" not in config:
            config["llm"] = {}
        
        if "anything_llm" not in config["llm"]:
            config["llm"]["anything_llm"] = {}
        
        config["llm"]["anything_llm"]["enabled"] = True
        
        if api_key:
            config["llm"]["anything_llm"]["api_key"] = api_key
        
        if api_url:
            config["llm"]["anything_llm"]["api_url"] = api_url
        
        # Write back to configuration file
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        logger.info("AnythingLLM configuration updated")
        return True
    
    except Exception as e:
        logger.error(f"Failed to update AnythingLLM configuration: {str(e)}")
        return False

def create_directories():
    """
    Create necessary directory structure
    
    Returns:
        Success status
    """
    try:
        # Create directories
        directories = [
            os.path.join(ROOT_DIR, "data"),
            os.path.join(ROOT_DIR, "data", "audio"),
            os.path.join(ROOT_DIR, "data", "transcriptions"),
            os.path.join(ROOT_DIR, "data", "knowledge"),
            os.path.join(ROOT_DIR, "data", "emails"),
            os.path.join(ROOT_DIR, "models"),
            os.path.join(ROOT_DIR, "models", "llm"),
            os.path.join(ROOT_DIR, "models", "embedding"),
            os.path.join(ROOT_DIR, "logs")
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Created directory: {directory}")
        
        return True
    
    except Exception as e:
        logger.error(f"Failed to create directories: {str(e)}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Integrated Assistant One-Click Deployment Script")
    parser.add_argument("--whisper-model", type=str, choices=["tiny", "base", "small", "medium", "large"], 
                        default="base", help="Whisper model size (default: base)")
    parser.add_argument("--anything-llm-url", type=str, 
                        default="http://localhost:3001/api", help="AnythingLLM API URL")
    parser.add_argument("--skip-whisper", action="store_true", help="Skip Whisper installation")
    parser.add_argument("--skip-knowledge", action="store_true", help="Skip knowledge base setup")
    # Gmail argument removed
    
    args = parser.parse_args()
    
    logger.info("Starting Integrated Assistant One-Click Deployment")
    logger.info("=" * 50)
    
    # Create necessary directory structure
    logger.info("Step 1: Creating necessary directory structure")
    if not create_directories():
        logger.error("Failed to create directories, deployment terminated")
        return 1
    
    # Ask for AnythingLLM API key
    print("\n" + "=" * 50)
    print("AnythingLLM Integration Setup")
    print("=" * 50)
    print("Please enter your AnythingLLM API key (leave empty if you don't have one):")
    api_key = getpass.getpass("API Key: ")
    
    # Update AnythingLLM configuration
    if not update_config_anything_llm(api_key=api_key, api_url=args.anything_llm_url):
        logger.warning("Failed to update AnythingLLM configuration, will use default settings")
    
    # Install and set up Whisper
    if not args.skip_whisper:
        logger.info("\nStep 2: Installing and setting up Whisper")
        whisper_args = ["--model", args.whisper_model]
        if not run_script("setup_whisper.py", whisper_args):
            logger.error("Whisper installation failed, deployment continues but speech transcription may not be available")

        logger.info("Skipping Whisper installation")
    
    # Set up knowledge base
    if not args.skip_knowledge:
        logger.info("\nStep 3: Setting up knowledge base")
        if not run_script("setup_knowledge.py"):
            logger.error("Knowledge base setup failed, deployment continues but knowledge base features may not be available")

        logger.info("Skipping knowledge base setup")
    
    # Gmail integration has been removed
    # Gmail integration has been removed
    logger.info("\nStep 4: Gmail integration has been removed")
    # Gmail setup script has been removed
    # Email integration is no longer available


    
    # Set up scheduled tasks
    logger.info("\nStep 5: Setting up scheduled tasks")
    if not run_script("setup_cron.py"):
        logger.warning("Scheduled tasks setup failed, deployment continues but automation features may not be available")
    
    logger.info("\n" + "=" * 50)
    logger.info("Integrated Assistant deployment completed!")
    logger.info("You can start the service by running the following command:")
    logger.info(f"python {os.path.join(ROOT_DIR, 'start.py')}")
    logger.info("=" * 50)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
