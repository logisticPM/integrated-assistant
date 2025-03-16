# 集成助手 (Integrated Assistant)

集成助手是一个多功能AI辅助工具，结合了会议记录处理、邮件AI助手和本地知识库功能，通过MCP（消息通信协议）服务实现模块间的高效通信。

## 功能特点

### 会议记录处理
- 上传和管理会议音频文件
- 自动转录会议内容
- 生成会议摘要和提取关键点
- 按主题和参与者组织会议记录

### 邮件AI助手
- 邮件同步和管理
- 智能邮件分类和优先级排序
- 情感分析和关键信息提取
- 自动生成邮件回复建议

### 本地知识库
- 文档上传和管理
- 文本向量化和语义搜索
- 基于知识库的问答功能
- 支持多种文档格式

### MCP服务
- 模块间的统一通信接口
- 支持同步和异步调用
- 任务状态跟踪和管理
- 可扩展的服务注册机制

## 项目结构

```
integrated-assistant/
├── app.py                  # 主应用入口
├── config.yaml             # 全局配置
├── frontend/               # Gradio前端
│   ├── main_ui.py          # 主界面
│   ├── meeting_ui.py       # 会议模块UI
│   ├── email_ui.py         # 邮件模块UI
│   └── knowledge_ui.py     # 知识库模块UI
├── modules/                # 功能模块
│   ├── meeting/            # 会议记录模块
│   ├── email/              # 邮件助手模块
│   └── knowledge/          # 知识库模块
├── mcp/                    # MCP服务
│   ├── client.py           # MCP客户端
│   ├── server.py           # MCP服务器
│   ├── transcription.py    # 转录服务
│   ├── llm_adapter.py      # LLM适配服务
│   ├── vector_service.py   # 向量数据库服务
│   ├── docloader.py        # 文档加载器
│   ├── text_splitter.py    # 文本分块器
│   ├── embedder.py         # 向量嵌入器
│   └── email_service.py    # 邮件服务
├── db/                     # 数据库管理
│   ├── db_manager.py       # SQLite数据库管理
│   └── vector_db.py        # 向量数据库管理
└── utils/                  # 工具函数
```

## 安装与配置

### 系统要求
- Python 3.8+
- 足够的磁盘空间用于存储文档和向量数据库
- 互联网连接（用于邮件同步和可选的远程LLM服务）
- 对于语音转录功能，建议有GPU加速（非必须）

### 一键部署

项目提供了一键部署脚本，可以自动完成所有必要组件的安装和配置：

```bash
python scripts/setup_all.py
```

部署过程中，您可以：
- 输入AnythingLLM的API密钥（如果有）
- 选择Whisper模型大小（默认为base）
- 配置其他集成服务

可用的命令行参数：
```
--whisper-model [tiny/base/small/medium/large]  # 选择Whisper模型大小
--anything-llm-url URL                          # 设置AnythingLLM API URL
--skip-whisper                                  # 跳过Whisper安装
--skip-knowledge                                # 跳过知识库设置
--skip-gmail                                    # 跳过Gmail设置
```

### 单独组件安装

如果您只需要安装特定组件，可以使用以下脚本：

1. 克隆仓库
```bash
git clone https://github.com/yourusername/integrated-assistant.git
cd integrated-assistant
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 安装Whisper（用于语音转录）
```bash
# 运行Whisper安装脚本
python scripts/setup_whisper.py --model base
```

4. 安装知识库组件
```bash
# 运行知识库安装脚本
python scripts/setup_knowledge.py --model all-MiniLM-L6-v2
```

5. 配置应用
编辑 `config.yaml` 文件，设置LLM模型路径、邮件服务器信息等。

6. 运行应用
```bash
python app.py
```

应用将在 http://localhost:7860 启动。

## 启动服务

### 一键启动

使用一键启动脚本可以同时启动后端服务和前端UI：

```bash
python start.py
```

启动脚本会自动打开浏览器访问集成助手界面。

可用的命令行参数：
```
--host HOST          # 设置服务器主机地址（默认为0.0.0.0）
--port PORT          # 设置服务器端口（默认为7860）
--no-browser         # 不自动打开浏览器
--setup              # 在启动前运行安装脚本
```

### 手动启动

1. 启动后端服务
```bash
python app.py
```

2. 启动前端UI
```bash
python frontend/main_ui.py
```

## 配置说明

### Whisper语音转录配置
```yaml
meeting:
  audio_dir: "./data/audio"
  transcription_dir: "./data/transcriptions"
  whisper:
    model: "base"  # tiny, base, small, medium, large
    language: "auto"  # 设置为auto自动检测语言，或指定语言代码如zh、en
```

### 知识库配置
```yaml
knowledge:
  docs_dir: "./data/documents"  # 文档存储目录
  chunk_size: 1000              # 文本块大小
  chunk_overlap: 200            # 文本块重叠大小
  embedding_model: "all-MiniLM-L6-v2"  # 嵌入模型名称
  splitter_type: "smart"        # 分块器类型：simple, markdown, smart
  supported_extensions:          # 支持的文件扩展名
    - ".txt"
    - ".md"
    - ".pdf"
    - ".docx"
    - ".html"
    - ".csv"
  use_mock_embedder: false      # 是否使用模拟嵌入器（用于测试）
  vector_search_top_k: 5        # 向量搜索返回的最大结果数
```

### LLM配置
```yaml
llm:
  model: "local"  # local, openai, etc.
  model_path: "./models/llm"
  embedding_model: "local"
  embedding_model_path: "./models/embedding"
  anything_llm:
    enabled: false
    api_url: "http://localhost:3000/api"
    api_key: ""
```

### 邮件配置
```yaml
email:
  sync_interval: 300  # 秒
  max_emails: 1000
  providers:
    - name: "gmail"
      enabled: false
      credentials_file: "./credentials/gmail.json"
```

### Gmail认证设置

集成助手的邮件功能**仅支持Gmail**，通过OAuth 2.0认证访问Gmail API。要设置Gmail认证，请按照以下步骤操作：

1. 在Google Cloud Console创建项目并启用Gmail API
2. 创建OAuth 2.0客户端ID并下载客户端密钥文件
3. 运行Gmail设置脚本：
   ```bash
   python scripts/setup_gmail.py --client-secret /path/to/your/client_secret.json
   ```
4. 按照浏览器中的提示完成授权流程

详细的设置指南请参考 [Gmail设置指南](docs/gmail_setup_guide.md)。

## 使用指南

### 会议记录处理
1. 在会议模块中上传音频文件
2. 系统自动转录并生成摘要
3. 查看会议详情和关键点

### 邮件助手
1. 配置邮件账户信息
2. 同步邮件
3. 查看邮件分析和回复建议

### 知识库
1. 上传文档到知识库
   - 支持多种格式：TXT、Markdown、PDF、Word、HTML、CSV
   - 添加标签和分类以便更好地组织文档
2. 文档处理流程
   - 文档自动加载和文本提取
   - 智能分块以保留语义完整性
   - 向量化存储以支持语义搜索
3. 使用知识库
   - 通过关键词或自然语言查询搜索文档
   - 查看搜索结果和相关度评分
   - 访问原始文档和相关片段

### 测试知识库功能
可以使用测试脚本验证知识库功能是否正常工作：
```bash
# 使用默认配置测试知识库功能
python scripts/test_knowledge.py

# 使用模拟嵌入器进行测试（无需下载大型模型）
python scripts/test_knowledge.py --use-mock

# 使用自定义测试文件
python scripts/test_knowledge.py --test-file /path/to/your/test/document.pdf
```

## 开发者指南

### 添加新服务
1. 在 `mcp/` 目录下创建新的服务模块
2. 实现服务类和注册函数
3. 在 `mcp/server.py` 中导入并注册新服务

### 扩展前端界面
1. 在 `frontend/` 目录下创建新的UI组件
2. 在 `frontend/main_ui.py` 中集成新组件
3. 通过MCP客户端连接后端服务

### 扩展知识库功能
1. 添加新的文档加载器
   - 在 `mcp/docloader.py` 中创建新的加载器类
   - 在 `get_loader_for_file` 函数中注册新的文件类型
2. 改进文本分块策略
   - 在 `mcp/text_splitter.py` 中创建新的分块器类
   - 更新 `get_text_splitter` 函数以支持新的分块器
3. 集成更高级的向量数据库
   - 修改 `mcp/vector_service.py` 中的向量存储和检索逻辑
   - 更新 `_vectorize_chunks` 和 `search` 方法

## 许可证

MIT License

## 贡献

欢迎提交问题和功能请求！
