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

1. 确保集成助手已正确安装
2. 运行 Gmail 设置脚本，指定客户端密钥文件的路径：

```bash
python scripts/setup_gmail.py --client-secret /path/to/your/client_secret.json
```

3. 脚本将启动浏览器窗口，引导你完成 Google 授权流程
4. 按照浏览器中的提示登录你的 Google 账户并授权应用访问你的 Gmail
5. 授权成功后，浏览器将显示"授权成功"页面，你可以关闭该页面

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
