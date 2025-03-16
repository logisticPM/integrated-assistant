# Gmail 集成设置指南

本指南将帮助你为集成助手配置 Gmail 集成，使应用能够访问和管理你的 Gmail 邮件。

## 前提条件

1. 拥有 Google 账户
2. 创建 Google Cloud 项目并启用 Gmail API
3. 获取 OAuth 2.0 客户端 ID 和密钥

## 步骤 1: 创建 Google Cloud 项目

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 点击页面顶部的项目下拉菜单，然后点击"新建项目"
3. 输入项目名称（例如"集成助手"），然后点击"创建"
4. 等待项目创建完成，然后切换到新项目

## 步骤 2: 启用 Gmail API

1. 在 Google Cloud Console 的左侧导航菜单中，选择"API 和服务" > "库"
2. 在搜索框中输入"Gmail"，然后点击"Gmail API"
3. 点击"启用"按钮

## 步骤 3: 创建 OAuth 凭证

1. 在 Google Cloud Console 的左侧导航菜单中，选择"API 和服务" > "凭证"
2. 点击页面顶部的"创建凭证"，然后选择"OAuth 客户端 ID"
3. 如果这是你第一次创建 OAuth 凭证，你需要先配置同意屏幕：
   - 选择"外部"用户类型（除非你有 Google Workspace 账户）
   - 填写应用名称、用户支持电子邮件和开发者联系信息
   - 添加授权域（如果你有域名）
   - 保存并继续
4. 返回到创建 OAuth 客户端 ID 页面：
   - 应用类型选择"桌面应用"
   - 输入名称（例如"集成助手桌面客户端"）
   - 点击"创建"

## 步骤 4: 下载客户端密钥

1. 创建凭证后，会弹出一个窗口显示你的客户端 ID 和客户端密钥
2. 点击"下载 JSON"按钮
3. 将下载的 JSON 文件保存到安全的位置

## 步骤 5: 配置集成助手

集成助手现在提供多种方式配置 Gmail 凭证，选择以下任一方式：

### 方式一：使用客户端密钥文件

```bash
python scripts/setup_gmail.py --client-secret /path/to/your/client_secret.json
```

### 方式二：使用环境变量

设置以下环境变量，然后运行设置脚本：

```bash
# Windows PowerShell
$env:GMAIL_SECRET = '{"installed":{"client_id":"YOUR_CLIENT_ID.apps.googleusercontent.com","project_id":"your-project-id","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_secret":"YOUR_CLIENT_SECRET","redirect_uris":["http://localhost"]}}'

# 然后运行
python scripts/setup_gmail.py
```

```bash
# Linux/macOS
export GMAIL_SECRET='{"installed":{"client_id":"YOUR_CLIENT_ID.apps.googleusercontent.com","project_id":"your-project-id","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_secret":"YOUR_CLIENT_SECRET","redirect_uris":["http://localhost"]}}'

# 然后运行
python scripts/setup_gmail.py
```

### 方式三：直接传递密钥内容

```bash
python scripts/setup_gmail.py --client-secret-content '{"installed":{"client_id":"YOUR_CLIENT_ID.apps.googleusercontent.com","project_id":"your-project-id","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_secret":"YOUR_CLIENT_SECRET","redirect_uris":["http://localhost"]}}'
```

## 客户端密钥格式说明

无论使用哪种方式，确保你的客户端密钥 JSON 格式正确：

```json
{
  "installed": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "project_id": "your-project-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uris": ["http://localhost"]
  }
}
```

**重要提示**：密钥必须包含 `"installed"` 对象，这表明它是一个已安装应用程序的凭证。如果格式不正确，会出现 "Client secrets must be for a web or installed app" 错误。

## 在其他电脑上配置

如果你需要在其他电脑上配置 Gmail 集成，可以：

1. 将你的客户端密钥文件复制到新电脑的 `data/credentials/secrets.json` 路径
2. 或者使用环境变量 `GMAIL_SECRET` 设置密钥内容
3. 或者使用命令行参数 `--client-secret` 或 `--client-secret-content` 指定密钥

首次运行时，会打开浏览器窗口要求授权访问你的 Gmail 账户。授权后，令牌会保存到 `data/credentials/token.json` 文件中。

## 其他命令行选项

```bash
# 指定凭证目录
python scripts/setup_gmail.py --credentials-dir /custom/path/to/credentials

# 指定OAuth端口
python scripts/setup_gmail.py --port 8080

# 直接提供令牌内容（适用于已有令牌的情况）
python scripts/setup_gmail.py --token-content '{"token":"your-token-content",...}'
```

## 在部署脚本中跳过 Gmail 设置

如果你不需要 Gmail 集成，可以在运行部署脚本时添加 `--skip-gmail` 参数：

```bash
python scripts/setup_all_with_langraph.py --use-langraph --skip-gmail
```

## 步骤 6: 验证设置

1. 启动集成助手应用：

```bash
python app.py
```

2. 在应用的"设置"标签页中，检查 Gmail 集成状态是否显示为"已连接"
3. 在"邮件助手"标签页中，点击"同步邮件"按钮测试邮件同步功能

## 故障排除

如果你遇到问题，请检查以下几点：

1. 确保 Google Cloud 项目中已启用 Gmail API
2. 确保客户端密钥文件正确无误
3. 检查 `credentials` 目录中的权限，确保应用有读写权限
4. 查看应用日志文件获取详细错误信息

## 安全注意事项

1. 客户端密钥文件包含敏感信息，请妥善保管
2. 令牌文件 (`gmail_token.json`) 包含访问你 Gmail 账户的凭证，请确保其安全
3. 如果你怀疑凭证被泄露，请立即在 Google 账户设置中撤销应用的访问权限

## 更多信息

- [Gmail API 文档](https://developers.google.com/gmail/api)
- [Google OAuth 2.0 文档](https://developers.google.com/identity/protocols/oauth2)
