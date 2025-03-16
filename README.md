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

## Troubleshooting

### Common Installation Issues

#### Missing Dependencies
If you encounter errors like `ModuleNotFoundError: No module named 'flask'`, ensure you've installed all required dependencies:

```powershell
pip install -r requirements.txt
```

#### Windows-Specific Issues
- **Path Separators**: Make sure to use backslashes (`\`) in file paths when running commands on Windows.
- **Permission Issues**: Try running PowerShell or Command Prompt as Administrator if you encounter permission errors.
- **Long Path Errors**: Windows has a default path length limit. If you encounter path-related errors, consider installing the project in a directory with a shorter path.

#### Whisper Installation Issues
If you encounter issues with Whisper installation:

```powershell
# Install Whisper dependencies separately
pip install torch
pip install openai-whisper
pip install ffmpeg-python

# Make sure ffmpeg is installed and in your PATH
# You can download it from: https://ffmpeg.org/download.html
```

#### Server Startup Errors
If the server fails to start:
1. Check if the port is already in use by another application
2. Verify that all dependencies are installed
3. Check the logs for specific error messages

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
    api_url: "http://localhost:3001"  # AnythingLLM API URL
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

## 语音转录功能

集成助手支持语音转录功能，可以将会议录音转换为文本。系统提供两种转录方式：

### 方式一：使用 AnythingLLM API（推荐）

这种方式不需要在本地安装 Whisper，而是通过 AnythingLLM 的 API 进行转录，更适合 Windows 用户。

1. 确保您已经在 `config.yaml` 中配置了 AnythingLLM API：

```yaml
llm:
  anything_llm:
    enabled: true
    api_url: "http://localhost:3001"  # AnythingLLM API 地址
    api_key: "your_api_key_here"          # 如果需要，添加您的 API 密钥
```

2. 确保 AnythingLLM 服务正在运行，并且可以访问 Whisper API。

### 方式二：Whisper ONNX 本地转录

使用基于 ONNX 运行时的 Whisper 模型进行本地转录，性能更好，安装更简单。

在 `config.yaml` 中配置：

```yaml
meeting:
  whisper:
    model: "base"  # 目前仅支持 base 模型
    language: "auto"  # 或指定语言代码
    use_onnx: true  # 启用 ONNX 运行时版本
```

安装 Whisper ONNX：

```bash
python scripts/setup_whisper_onnx.py
```

此脚本会自动安装必要的依赖并下载 ONNX 模型文件。

### 转录优先级

系统会按以下优先级选择转录方式：

1. AnythingLLM API（如果可用）
2. Whisper ONNX 本地转录（如果可用）
3. 模拟转录（当以上方法都不可用时）

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
│   ├── langraph/         # Langraph 架构实现
│   │   ├── core.py       # 核心组件和接口
│   │   ├── transcription.py # 转录服务组件
│   │   ├── llm_adapter.py # LLM 服务组件
│   │   ├── vector_service.py # 向量存储组件
│   │   ├── tool_service.py # 工具服务组件
│   │   ├── agent_service.py # 代理服务组件
│   │   ├── meeting_service.py # 会议服务组件
│   │   ├── mcp_server.py # MCP 服务器组件
│   │   ├── integration.py # 与现有服务器集成
│   │   └── main.py       # 独立运行入口
│   └── ...
├── frontend/             # Frontend UI
├── scripts/              # Setup and utility scripts
├── data/                 # Data storage
├── models/               # Model storage
├── config.yaml           # Configuration file
└── README.md             # This file
```

### Langraph 架构

集成助手支持基于 langraph 的模块化架构，提供更灵活的组件化设计和扩展能力。

### 什么是 Langraph

Langraph 是一个基于 LangChain 的图形化组件框架，允许开发者以模块化、可组合的方式构建复杂的 AI 应用。在集成助手中，我们使用 Langraph 实现了各种服务组件，包括转录服务、LLM 服务、向量存储、工具服务、代理服务和会议服务等。

### 安装 Langraph

使用以下命令安装 Langraph 及其依赖：

```bash
python scripts/setup_langraph.py
```

此脚本会自动安装必要的依赖并创建所需的目录结构。

### 使用 Langraph 架构启动服务

集成助手提供了两种启动方式：

1. 使用原始 MCP 服务器（默认）
2. 使用基于 Langraph 的新架构

要使用 Langraph 架构启动服务，请运行：

```bash
python scripts/start_with_langraph.py
```

可用的命令行参数：

```
--host HOST          # 设置服务器主机地址（默认为 127.0.0.1）
--port PORT          # 设置服务器端口（默认为 8000）
--ui-port PORT       # 设置 UI 端口（默认为 3000）
--config PATH        # 配置文件路径
--run-setup          # 在启动前运行安装脚本
--no-browser         # 不自动打开浏览器
--use-original       # 使用原始 MCP 服务器而不是 Langraph 架构
```

### Langraph 架构的优势

1. **模块化设计**：各个组件可以独立开发、测试和部署
2. **可扩展性**：轻松添加新的服务组件和功能
3. **插件系统**：支持动态加载和使用插件
4. **灵活的组件组合**：可以根据需要组合不同的组件
5. **更好的错误处理**：每个组件都有独立的错误处理机制
6. **更清晰的代码结构**：基于图形的组件结构使代码更易于理解和维护

### 开发新组件

要在 Langraph 架构中添加新组件，请按照以下步骤操作：

1. 在 `mcp/langraph/` 目录下创建新的组件文件
2. 继承 `MCPComponent` 类并实现必要的方法
3. 在 `mcp/langraph/mcp_server.py` 中注册新组件
4. 更新 `mcp/langraph/integration.py` 以集成新组件

示例组件实现：

```python
from mcp.langraph.core import MCPComponent, MCPState

class MyCustomComponent(MCPComponent):
    def __init__(self, name="my_component", config=None):
        super().__init__(name=name, description="My custom component")
        self.config = config or {}
    
    def to_runnable(self):
        def _run(state: MCPState, config=None):
            # 实现组件逻辑
            return {"result": "处理结果"}
        return _run
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
