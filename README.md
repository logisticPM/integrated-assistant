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

### 安装步骤

1. 克隆仓库
```bash
git clone https://github.com/yourusername/integrated-assistant.git
cd integrated-assistant
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置应用
编辑 `config.yaml` 文件，设置LLM模型路径、邮件服务器信息等。

4. 运行应用
```bash
python app.py
```

应用将在 http://localhost:7860 启动。

## 配置说明

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
  email_dir: "./data/emails"
  sync_interval: 300  # 秒
  max_emails: 1000
  imap_server: "imap.example.com"
  imap_port: 993
  smtp_server: "smtp.example.com"
  smtp_port: 587
  email_address: "your-email@example.com"
  email_password: "your-password"
  use_ssl: true
```

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
2. 使用搜索功能查找信息
3. 通过聊天界面提问相关问题

## 开发者指南

### 添加新服务
1. 在 `mcp/` 目录下创建新的服务模块
2. 实现服务类和注册函数
3. 在 `mcp/server.py` 中导入并注册新服务

### 扩展前端界面
1. 在 `frontend/` 目录下创建新的UI组件
2. 在 `frontend/main_ui.py` 中集成新组件
3. 通过MCP客户端连接后端服务

## 许可证

MIT License

## 贡献

欢迎提交问题和功能请求！
