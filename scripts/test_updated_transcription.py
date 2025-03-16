#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Updated AnythingLLM Transcription
测试更新后的 AnythingLLM 转录功能
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_updated_transcription")

# Add project root to path
ROOT_DIR = Path(__file__).parent.joinpath("integrated-assistant").absolute()
sys.path.append(str(ROOT_DIR))

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Test updated AnythingLLM transcription")
    parser.add_argument("--audio", type=str, default="C:\\Users\\qc_de\\miniconda3\\envs\\qai_hub\\Lib\\site-packages\\IPython\\lib\\tests\\test.wav", help="Path to audio file")
    parser.add_argument("--api-key", default="YM549NQ-R1R44WX-QHAPNKK-59X6VDG", help="AnythingLLM API key")
    parser.add_argument("--base-url", default="http://localhost:3001/api", help="AnythingLLM API base URL")
    args = parser.parse_args()
    
    # Check if audio file exists
    if not os.path.exists(args.audio):
        logger.error(f"Audio file does not exist: {args.audio}")
        return 1
    
    logger.info(f"Testing transcription with audio file: {args.audio}")
    
    # Test using AnythingLLMSTTClient
    try:
        from stt_preferences import AnythingLLMSTTClient
        
        logger.info("Testing with AnythingLLMSTTClient...")
        client = AnythingLLMSTTClient(api_key=args.api_key, base_url=args.base_url)
        
        # Test connection
        if not client.test_connection():
            logger.error("Cannot connect to AnythingLLM API")
            return 1
        
        logger.info("Successfully connected to AnythingLLM API")
        
        # Get current STT settings
        stt_settings = client.get_stt_settings()
        if stt_settings:
            logger.info("Current STT settings:")
            for key, value in stt_settings.items():
                logger.info(f"  {key}: {value}")
        
        # Try transcription
        logger.info("Attempting transcription...")
        result = client.transcribe_audio(args.audio)
        
        if result:
            logger.info("Transcription successful!")
            logger.info(f"Transcribed text: {result.get('text', '')}")
            return 0
        else:
            logger.error("Transcription failed with AnythingLLMSTTClient")
    except ImportError as e:
        logger.error(f"Import error with AnythingLLMSTTClient: {str(e)}")
    except Exception as e:
        logger.error(f"Error with AnythingLLMSTTClient: {str(e)}")
    
    # Test using AnythingLLMService directly
    try:
        from mcp.langraph.anythingllm_service import AnythingLLMService
        
        logger.info("Testing with AnythingLLMService directly...")
        config = {
            "api_key": args.api_key,
            "base_url": args.base_url
        }
        service = AnythingLLMService(config)
        
        # Test connection
        if not service.test_connection():
            logger.error("Cannot connect to AnythingLLM API")
            return 1
        
        logger.info("Successfully connected to AnythingLLM API")
        
        # Try transcription
        logger.info("Attempting transcription...")
        result = service.transcribe_audio(args.audio)
        
        if result:
            logger.info("Transcription successful!")
            logger.info(f"Transcribed text: {result.get('text', '')}")
            return 0
        else:
            logger.error("Transcription failed with AnythingLLMService")
    except ImportError as e:
        logger.error(f"Import error with AnythingLLMService: {str(e)}")
    except Exception as e:
        logger.error(f"Error with AnythingLLMService: {str(e)}")
    
    logger.error("All transcription attempts failed")
    return 1

if __name__ == "__main__":
    sys.exit(main())
