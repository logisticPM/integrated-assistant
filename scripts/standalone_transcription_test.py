#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Standalone AnythingLLM Transcription Test
独立的 AnythingLLM 转录测试
"""

import os
import sys
import json
import requests
import logging
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("standalone_transcription_test")

def test_connection(api_key, base_url):
    """Test connection to AnythingLLM API"""
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(
            f"{base_url}/v1/auth",
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            logger.info("Successfully connected to AnythingLLM API")
            return True
        else:
            logger.error(f"Error connecting to AnythingLLM API: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error connecting to AnythingLLM API: {str(e)}")
        return False

def get_system_info(api_key, base_url):
    """Get system information from AnythingLLM API"""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        response = requests.get(
            f"{base_url}/v1/system",
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json().get("settings", {})
        else:
            logger.error(f"Error getting system info: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        return None

def try_transcription(api_key, base_url, audio_path, workspace_slug=None):
    """Try transcribing audio with multiple endpoint patterns"""
    try:
        # Prepare the file for upload
        with open(audio_path, "rb") as audio_file:
            file_content = audio_file.read()
        
        # Define endpoints to try
        endpoints = [
            # Standard endpoints
            f"{base_url}/v1/audio/transcriptions",
            f"{base_url}/audio/transcriptions",
            f"{base_url}/v1/transcribe",
            f"{base_url}/transcribe",
            f"{base_url}/v1/whisper/transcribe",
            f"{base_url}/whisper/transcribe",
            f"{base_url}/v1/audio/transcribe",
            f"{base_url}/audio/transcribe",
            # Try without /api in the path
            f"{base_url.replace('/api', '')}/v1/audio/transcriptions",
            f"{base_url.replace('/api', '')}/audio/transcriptions",
            f"{base_url.replace('/api', '')}/v1/transcribe",
            f"{base_url.replace('/api', '')}/transcribe",
            f"{base_url.replace('/api', '')}/v1/whisper/transcribe",
            f"{base_url.replace('/api', '')}/whisper/transcribe",
            f"{base_url.replace('/api', '')}/v1/audio/transcribe",
            f"{base_url.replace('/api', '')}/audio/transcribe",
        ]
        
        # If workspace_slug is provided, also try workspace-specific endpoints
        if workspace_slug:
            workspace_endpoints = [
                f"{base_url}/v1/workspace/{workspace_slug}/transcribe",
                f"{base_url}/workspace/{workspace_slug}/transcribe",
                f"{base_url}/v1/audio/transcribe/{workspace_slug}",
                f"{base_url}/audio/transcribe/{workspace_slug}",
                f"{base_url.replace('/api', '')}/v1/workspace/{workspace_slug}/transcribe",
                f"{base_url.replace('/api', '')}/workspace/{workspace_slug}/transcribe",
                f"{base_url.replace('/api', '')}/v1/audio/transcribe/{workspace_slug}",
                f"{base_url.replace('/api', '')}/audio/transcribe/{workspace_slug}",
            ]
            endpoints.extend(workspace_endpoints)
        
        # Try each endpoint
        for endpoint in endpoints:
            try:
                logger.info(f"Trying endpoint: {endpoint}")
                
                # Prepare the file for upload
                with open(audio_path, "rb") as audio_file:
                    files = {"file": (os.path.basename(audio_path), audio_file)}
                    
                    # Prepare data payload
                    data = {}
                    if workspace_slug and "workspace" not in endpoint:
                        data["workspace"] = workspace_slug
                    
                    # Try with different header combinations
                    headers_options = [
                        {"Authorization": f"Bearer {api_key}"},
                        {"Authorization": f"Bearer {api_key}", "Content-Type": "multipart/form-data"},
                        {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
                    ]
                    
                    for headers in headers_options:
                        try:
                            logger.info(f"Trying headers: {headers}")
                            response = requests.post(
                                endpoint,
                                headers=headers,
                                files=files,
                                data=data
                            )
                            
                            if response.status_code == 200:
                                logger.info(f"Successful transcription with endpoint: {endpoint}")
                                return response.json()
                            else:
                                logger.warning(f"Error with endpoint {endpoint}: {response.status_code} - {response.text}")
                        except Exception as e:
                            logger.warning(f"Error with endpoint {endpoint} and headers {headers}: {str(e)}")
            except Exception as e:
                logger.warning(f"Error with endpoint {endpoint}: {str(e)}")
        
        logger.error("All transcription endpoints failed")
        return None
    except Exception as e:
        logger.error(f"Error in transcription test: {str(e)}")
        return None

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Standalone test for AnythingLLM transcription")
    parser.add_argument("--audio", type=str, default="C:\\Users\\qc_de\\miniconda3\\envs\\qai_hub\\Lib\\site-packages\\IPython\\lib\\tests\\test.wav", help="Path to audio file")
    parser.add_argument("--api-key", default="YM549NQ-R1R44WX-QHAPNKK-59X6VDG", help="AnythingLLM API key")
    parser.add_argument("--base-url", default="http://localhost:3001/api", help="AnythingLLM API base URL")
    parser.add_argument("--workspace", help="Optional workspace slug")
    args = parser.parse_args()
    
    # Ensure base_url is using port 3001
    if "localhost" in args.base_url and ":3001" not in args.base_url:
        args.base_url = args.base_url.replace("localhost", "localhost:3001")
    
    # Check if audio file exists
    if not os.path.exists(args.audio):
        logger.error(f"Audio file does not exist: {args.audio}")
        return 1
    
    logger.info(f"Testing transcription with audio file: {args.audio}")
    logger.info(f"Using API base URL: {args.base_url}")
    
    # Test connection
    if not test_connection(args.api_key, args.base_url):
        logger.error("Failed to connect to AnythingLLM API")
        return 1
    
    # Get system info
    system_info = get_system_info(args.api_key, args.base_url)
    if system_info:
        logger.info("System info retrieved successfully")
        logger.info("STT settings:")
        for key, value in system_info.items():
            if key.startswith("SpeechToText") or key.startswith("Whisper"):
                logger.info(f"  {key}: {value}")
    
    # Try transcription
    result = try_transcription(args.api_key, args.base_url, args.audio, args.workspace)
    
    if result:
        logger.info("Transcription successful!")
        logger.info(f"Transcribed text: {result.get('text', '')}")
        return 0
    else:
        logger.error("All transcription attempts failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
