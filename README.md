# Integrated Assistant

An intelligent assistant that integrates meeting recording transcription, summarization, knowledge base, and email management capabilities.

## Features

- **Speech Transcription**: Automatically transcribe meeting recordings using Whisper
- **Meeting Summarization**: Generate structured meeting summaries with key points and action items
- **Knowledge Base**: Build and query a knowledge base for your organization
- **Email Integration**: Synchronize and manage emails, with automatic analysis and response suggestions
- **Scheduled Tasks**: Automatically process new recordings and emails

## Installation and Configuration

### System Requirements
- Python 3.8+
- Sufficient disk space for documents and vector database
- Internet connection (for email synchronization and optional remote LLM services)
- GPU acceleration recommended for speech transcription (not required)

### One-Click Deployment

The project provides a one-click deployment script that automatically installs and configures all necessary components:

```powershell
python scripts\setup_all.py
```

During deployment, you can:
- Enter your AnythingLLM API key (if you have one)
- Select Whisper model size (default is base)
- Configure other integration services

Available command line arguments:
```
--whisper-model [tiny/base/small/medium/large]  # Select Whisper model size
--anything-llm-url URL                          # Set AnythingLLM API URL
--skip-whisper                                  # Skip Whisper installation
--skip-knowledge                                # Skip knowledge base setup
--skip-gmail                                    # Skip Gmail setup
```

### Individual Component Installation

If you only need to install specific components, you can use the following scripts:

1. Clone the repository
```powershell
git clone https://github.com/yourusername/integrated-assistant.git
cd integrated-assistant
```

2. Install dependencies
```powershell
pip install -r requirements.txt
```

3. Install Whisper (for speech transcription)
```powershell
# Run Whisper installation script
python scripts\setup_whisper.py --model base
```

4. Install knowledge base components
```powershell
# Run knowledge base setup script
python scripts\setup_knowledge.py --model all-MiniLM-L6-v2
```

5. Configure the application
Edit the `config.yaml` file to set LLM model paths, email server information, etc.

6. Run the application
```powershell
python app.py
```

The application will start at http://localhost:7860.

## Starting the Service

### One-Click Startup

Use the one-click startup script to start both the backend service and frontend UI:

```powershell
python start.py
```

The startup script will automatically open a browser to access the Integrated Assistant interface.

Available command line arguments:
```
--host HOST          # Set server host address (default is 0.0.0.0)
--port PORT          # Set server port (default is 7860)
--no-browser         # Don't automatically open browser
--setup              # Run setup script before starting
```

### Manual Startup

1. Start the backend service
```powershell
python -m mcp.server
```

2. Start the frontend UI
```powershell
python -m frontend.app
```

## Configuration Guide

### Whisper Speech Transcription Configuration

Whisper is used for speech transcription. You can configure it in the `config.yaml` file:

```yaml
whisper:
  model: "base"  # Options: tiny, base, small, medium, large
  language: "auto"  # Language code or "auto" for automatic detection
  device: "cuda"  # Use "cpu" if no GPU is available
```

Different model sizes have different resource requirements:
- tiny: ~1GB disk space, minimal RAM
- base: ~1GB disk space, ~2GB RAM
- small: ~2GB disk space, ~4GB RAM
- medium: ~5GB disk space, ~8GB RAM
- large: ~10GB disk space, ~16GB RAM

### LLM Configuration

The system supports both local LLM models and AnythingLLM integration:

```yaml
llm:
  model: "local"  # local, openai, etc.
  model_path: "./models/llm"
  embedding_model: "local"
  embedding_model_path: "./models/embedding"
  # AnythingLLM integration
  anything_llm:
    enabled: true
    api_url: "http://localhost:3001/api"
    api_key: ""  # Enter your API key here
```

### Email Integration

To configure email integration, set up the following in `config.yaml`:

```yaml
email:
  enabled: true
  sync_interval: 300  # Seconds between email syncs
  provider: "gmail"  # Currently only Gmail is supported
  credentials_file: "./credentials/gmail_token.json"
  # Email folders to monitor
  folders:
    - "INBOX"
    - "Sent"
```

For Gmail setup, follow the instructions in `docs/gmail_setup_guide.md`.

## Usage

### Meeting Management

1. Upload meeting recordings
2. View and search meeting transcriptions
3. Generate and export meeting summaries
4. Track action items from meetings

### Knowledge Base

1. Add documents to the knowledge base
2. Query the knowledge base with natural language questions
3. Get relevant information from your organization's documents

### Email Management

1. View and search emails
2. Analyze email content and sentiment
3. Generate response suggestions
4. Schedule follow-ups

## Development

### Project Structure

```
integrated-assistant/
├── mcp/                  # Main component package
│   ├── server.py         # Backend server
│   ├── transcription.py  # Speech transcription service
│   ├── llm_adapter.py    # LLM integration
│   ├── meeting_service.py # Meeting management
│   └── ...
├── frontend/             # Frontend UI
├── scripts/              # Setup and utility scripts
├── data/                 # Data storage
├── models/               # Model storage
├── config.yaml           # Configuration file
└── README.md             # This file
```

### Adding New Features

To add new features, follow these steps:
1. Add service implementation in the `mcp` package
2. Register the service in `mcp/server.py`
3. Add UI components in the `frontend` package
4. Update configuration in `config.yaml` if needed

## License

This project is licensed under the MIT License - see the LICENSE file for details.
