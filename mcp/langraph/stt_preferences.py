import requests
import json
import argparse
import os
import sys
from pathlib import Path

# Add project root to path to import from mcp
ROOT_DIR = Path(__file__).parent.joinpath("integrated-assistant").absolute()
sys.path.append(str(ROOT_DIR))

try:
    from mcp.langraph.anythingllm_service import AnythingLLMService
    USE_ANYTHINGLLM_SERVICE = True
except ImportError:
    USE_ANYTHINGLLM_SERVICE = False
    print("Warning: Could not import AnythingLLMService, falling back to direct API calls")

class AnythingLLMSTTClient:
    def __init__(self, api_key, base_url="http://localhost:3001/api"):
        self.api_key = api_key
        # Ensure base_url is using port 3001 as recommended by AnythingLLM
        if "localhost" in base_url and ":3001" not in base_url:
            base_url = base_url.replace("localhost", "localhost:3001")
        self.base_url = base_url
        
        if USE_ANYTHINGLLM_SERVICE:
            config = {
                "api_key": api_key,
                "base_url": base_url
            }
            self.service = AnythingLLMService(config)
        else:
            self.headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
    
    def test_connection(self):
        """Test connection to AnythingLLM API"""
        if USE_ANYTHINGLLM_SERVICE:
            try:
                return self.service.test_connection()
            except Exception as e:
                print(f"Error testing connection using AnythingLLM service: {str(e)}")
                return False
        else:
            try:
                response = requests.get(
                    f"{self.base_url}/v1/auth",
                    headers=self.headers,
                    timeout=5
                )
                
                if response.status_code == 200:
                    print("Successfully connected to AnythingLLM API")
                    return True
                else:
                    print(f"Error connecting to AnythingLLM API: {response.status_code} - {response.text}")
                    return False
            except Exception as e:
                print(f"Error connecting to AnythingLLM API: {str(e)}")
                return False
    
    def get_system_settings(self):
        """Get current system settings including STT preferences"""
        if USE_ANYTHINGLLM_SERVICE:
            try:
                return self.service.get_system_info()
            except Exception as e:
                print(f"Error getting system settings from AnythingLLM service: {str(e)}")
                return None
        else:
            try:
                response = requests.get(
                    f"{self.base_url}/v1/system",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    settings = response.json().get("settings", {})
                    return settings
                else:
                    print(f"Error getting system settings: {response.status_code} - {response.text}")
                    return None
            except Exception as e:
                print(f"Error getting system settings: {str(e)}")
                return None
    
    def get_stt_settings(self):
        """Get speech-to-text specific settings"""
        if USE_ANYTHINGLLM_SERVICE:
            try:
                return self.service.get_stt_settings()
            except Exception as e:
                print(f"Error getting STT settings from AnythingLLM service: {str(e)}")
                return None
        else:
            settings = self.get_system_settings()
            if not settings:
                return None
            
            stt_settings = {
                "SpeechToTextProvider": settings.get("SpeechToTextProvider"),
                "SpeechToTextLocalWhisperModel": settings.get("SpeechToTextLocalWhisperModel"),
                "WhisperProvider": settings.get("WhisperProvider"),
                "WhisperModelPref": settings.get("WhisperModelPref")
            }
            
            return stt_settings
    
    def update_stt_preferences(self, provider=None, model=None):
        """Update speech-to-text preferences"""
        if USE_ANYTHINGLLM_SERVICE and model:
            try:
                # Use the AnythingLLM service to update settings
                success = self.service.update_stt_settings(model)
                if success:
                    print(f"Successfully updated STT preferences to model: {model}")
                    return True
                else:
                    print("Failed to update STT preferences using AnythingLLM service")
                    return False
            except Exception as e:
                print(f"Error updating STT preferences using AnythingLLM service: {str(e)}")
                return False
        else:
            try:
                # Prepare update data
                update_data = {}
                
                if provider:
                    update_data["SpeechToTextProvider"] = provider
                
                if model:
                    # Update both model settings to ensure consistency
                    update_data["SpeechToTextLocalWhisperModel"] = model
                    update_data["WhisperModelPref"] = model
                
                # Only proceed if we have changes to make
                if not update_data:
                    print("No changes specified")
                    return False
                
                # Send update request - using the correct endpoint
                try:
                    # Try the endpoint used in AnythingLLMService
                    response = requests.post(
                        f"{self.base_url}/v1/system/update-settings",
                        headers=self.headers,
                        json=update_data
                    )
                    
                    if response.status_code == 200:
                        print("Successfully updated STT preferences")
                        return True
                    elif response.status_code == 404:
                        # If 404, try alternative endpoint structures
                        print("Trying alternative endpoint...")
                        
                        # Try with settings wrapper
                        response = requests.post(
                            f"{self.base_url}/v1/system",
                            headers=self.headers,
                            json={"settings": update_data}
                        )
                        
                        if response.status_code == 200:
                            print("Successfully updated STT preferences using alternative endpoint")
                            return True
                        else:
                            # Try another endpoint format
                            response = requests.post(
                                f"{self.base_url}/system/update-settings",
                                headers=self.headers,
                                json=update_data
                            )
                            
                            if response.status_code == 200:
                                print("Successfully updated STT preferences using second alternative endpoint")
                                return True
                            else:
                                print(f"Error updating STT preferences with all endpoints: {response.status_code} - {response.text}")
                                return False
                    else:
                        print(f"Error updating STT preferences: {response.status_code} - {response.text}")
                        return False
                except Exception as e:
                    print(f"Error sending update request: {str(e)}")
                    return False
            except Exception as e:
                print(f"Error updating STT preferences: {str(e)}")
                return False
    
    def transcribe_audio(self, audio_path, workspace_slug=None):
        """Transcribe audio file using AnythingLLM API"""
        if not os.path.exists(audio_path):
            print(f"Audio file does not exist: {audio_path}")
            return None
        
        if USE_ANYTHINGLLM_SERVICE:
            try:
                return self.service.transcribe_audio(audio_path, workspace_slug)
            except Exception as e:
                print(f"Error transcribing audio using AnythingLLM service: {str(e)}")
                return None
        else:
            try:
                # Prepare the file for upload
                with open(audio_path, "rb") as audio_file:
                    files = {"file": (os.path.basename(audio_path), audio_file)}
                    
                    # Prepare the payload
                    data = {}
                    if workspace_slug:
                        data["workspace"] = workspace_slug
                    
                    # Try different endpoints for transcription based on research
                    endpoints = [
                        f"{self.base_url}/v1/audio/transcriptions",
                        f"{self.base_url}/audio/transcriptions",
                        f"{self.base_url}/v1/transcribe",
                        f"{self.base_url}/transcribe",
                        f"{self.base_url}/v1/whisper/transcribe",
                        f"{self.base_url}/whisper/transcribe",
                        f"{self.base_url}/v1/audio/transcribe",
                        f"{self.base_url}/audio/transcribe"
                    ]
                    
                    # If workspace_slug is provided, also try workspace-specific endpoints
                    if workspace_slug:
                        workspace_endpoints = [
                            f"{self.base_url}/v1/workspace/{workspace_slug}/transcribe",
                            f"{self.base_url}/workspace/{workspace_slug}/transcribe",
                            f"{self.base_url}/v1/audio/transcribe/{workspace_slug}",
                            f"{self.base_url}/audio/transcribe/{workspace_slug}"
                        ]
                        endpoints.extend(workspace_endpoints)
                    
                    for endpoint in endpoints:
                        try:
                            print(f"Trying endpoint: {endpoint}")
                            response = requests.post(
                                endpoint,
                                headers={"Authorization": f"Bearer {self.api_key}"},
                                files=files,
                                data=data
                            )
                            
                            if response.status_code == 200:
                                print(f"Successful transcription with endpoint: {endpoint}")
                                return response.json()
                            else:
                                print(f"Error with endpoint {endpoint}: {response.status_code} - {response.text}")
                        except Exception as e:
                            print(f"Error with endpoint {endpoint}: {str(e)}")
                    
                    print("All transcription endpoints failed")
                    return None
            except Exception as e:
                print(f"Error transcribing audio: {str(e)}")
                return None
    
    def list_available_whisper_models(self):
        """List available Whisper models"""
        if USE_ANYTHINGLLM_SERVICE:
            try:
                # Use the AnythingLLM service to get available models
                return self.service.list_available_whisper_models()
            except Exception as e:
                print(f"Error getting available models from AnythingLLM service: {str(e)}")
                # Fall back to hardcoded list
        
        # Hardcoded list based on common options
        return [
            "Xenova/whisper-tiny",
            "Xenova/whisper-base",
            "Xenova/whisper-small",
            "Xenova/whisper-medium",
            "Xenova/whisper-large-v3",
            # Multilingual models
            "Xenova/whisper-tiny.en",
            "Xenova/whisper-base.en",
            "Xenova/whisper-small.en",
            "Xenova/whisper-medium.en"
        ]
    
def main():
    parser = argparse.ArgumentParser(description="AnythingLLM Speech-to-Text Preferences Manager")
    parser.add_argument("--api-key", default="YM549NQ-R1R44WX-QHAPNKK-59X6VDG", help="API key for AnythingLLM")
    parser.add_argument("--base-url", default="http://localhost:3001/api", help="Base URL for AnythingLLM API")
    parser.add_argument("command", choices=["get", "update", "list-models", "transcribe", "test-connection"], help="Command to execute")
    parser.add_argument("--provider", choices=["local_whisper", "openai_whisper"], help="STT provider to use")
    parser.add_argument("--model", help="Whisper model to use (e.g., Xenova/whisper-small)")
    parser.add_argument("--audio", help="Audio file path for transcription")
    parser.add_argument("--workspace", help="Workspace slug for transcription")
    
    args = parser.parse_args()
    
    client = AnythingLLMSTTClient(args.api_key, args.base_url)
    
    if args.command == "get":
        settings = client.get_stt_settings()
        if settings:
            print(json.dumps(settings, indent=2))
    
    elif args.command == "update":
        if not args.provider and not args.model:
            print("Error: At least one of --provider or --model must be specified for update command")
            return
        
        success = client.update_stt_preferences(args.provider, args.model)
        if success:
            # Get and display updated settings
            updated_settings = client.get_stt_settings()
            if updated_settings:
                print("\nUpdated STT settings:")
                print(json.dumps(updated_settings, indent=2))
    
    elif args.command == "list-models":
        models = client.list_available_whisper_models()
        print("Available Whisper models:")
        for model in models:
            print(f"  - {model}")
    
    elif args.command == "transcribe":
        if not args.audio:
            print("Error: --audio argument is required for transcribe command")
            return
        
        result = client.transcribe_audio(args.audio, args.workspace)
        if result:
            print("\nTranscription result:")
            print(json.dumps(result, indent=2))
    
    elif args.command == "test-connection":
        success = client.test_connection()
        if success:
            print("Connection to AnythingLLM API successful")
        else:
            print("Failed to connect to AnythingLLM API")

if __name__ == "__main__":
    main()
