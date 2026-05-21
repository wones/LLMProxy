# LLM Proxy Service - 版本说明

## 当前版本
**版本**: 2.2.0
**构建时间**: 2026-05-19

---

## 2.2.0 - 功能增强 (2026-05-19)

### ✨ 新增功能
1. **请求头记录** - 在日志详情中显示完整的请求头信息
2. **配置优先级优化** - 配置中的 stream 字段优先，请求中的值可以覆盖配置

### 🔧 技术改进
1. **日志模型增强** - 添加 request_headers 字段存储请求头
2. **日志详情优化** - 显示请求头、请求内容、响应内容的完整信息
3. **流式响应判断优化** - 配置优先，可被请求覆盖

### 🐛 问题修复
1. **Anthropic 路由日志修复** - 修复流式响应中 response_status 变量问题
2. **OpenAI 路由日志修复** - 添加 nonlocal response_status 声明
3. **时区显示修复** - 修复日志时间与系统时间不一致问题

---

## 2.1.0 - 功能增强 (2026-05-19)

### ✨ 新增功能
1. **配置自动选择** - 支持根据模型名称自动匹配配置，无需手动指定 config_id
2. **默认配置优化** - 配置选择时默认选择最早添加的配置
3. **工具调用支持** - 完整透传 OpenAI/Claude 工具调用响应，支持 opencode 等外围工具对接
4. **Claude Code 兼容** - 添加 anthropic-version 头和标准认证方式支持

### 🔧 技术改进
1. **响应透传优化** - 完整保留后端响应结构，不再重新构造
2. **端口统一** - 默认端口统一为 8000，文档与代码保持一致
3. **流式响应优化** - 真实流式传输，支持工具调用的流式响应
4. **HTTP 头增强** - 添加 x-api-key、Authorization、anthropic-version 等标准头

### 🔐 认证支持
- ✅ App-Key / App-Sign 自定义认证
- ✅ x-api-key 标准 Anthropic 认证
- ✅ Authorization Bearer 认证

---

## 2.0.0 - 重大更新 (2026-05-19)

### ✨ 核心改进
1. **移除 Node.js 依赖** - 纯 HTML + JavaScript 前端
2. **单端口架构** - 所有服务运行在 8000 端口
3. **完整请求/响应保存** - 数据库记录完整内容
4. **大数字格式化** - Token 统计显示万、百万、千万、亿
5. **详情弹窗** - 点击时间查看完整请求和响应

### 🔧 技术改进
1. **移除 EJS 模板** - 直接使用 HTML
2. **移除前端服务** - FastAPI 直接托管静态文件
3. **Stream 模式优化** - 请求参数优先于配置
4. **数据库迁移** - 添加 request_body 和 response_body 字段

---

## 1.2.0 - 之前版本

### ✨ 主要功能
1. 添加了 /v1/models 端点 - 支持模型列表
2. 改进了响应格式兼容层 - 支持各种响应格式
3. 修复了 Detection-Type 默认值问题
4. 使用 json.dumps() + content 发送请求
5. 更健壮的配置获取逻辑
6. 调试模式完整显示请求/响应

---

## 📋 完整功能列表

### API 兼容
- ✅ OpenAI 兼容 API - `/v1/chat/completions`
- ✅ Anthropic 兼容 API - `/v1/messages`
- ✅ 模型列表 API - `/v1/models`
- ✅ 流式和非流式响应
- ✅ 工具调用支持 - 完整透传 tool_calls/tool_use
- ✅ Claude Code 接入支持
- ✅ OpenAI Codex 接入支持

### 配置管理
- ✅ 多配置管理 - 支持多个配置切换
- ✅ 模型名称匹配 - 根据 model 参数自动选择配置
- ✅ 默认配置选择 - 自动选择最早添加的配置
- ✅ 配置 stream 优先 - stream 字段优先，请求可覆盖
- ✅ CURL 自动解析 - 一键导入配置
- ✅ 配置激活/禁用
- ✅ 默认模型和流式配置

### 认证方式
- ✅ App-Key / App-Sign 自定义认证
- ✅ x-api-key 标准 Anthropic 认证
- ✅ Authorization Bearer 认证
- ✅ anthropic-version 头支持

### 日志和统计
- ✅ 完整调用日志
- ✅ 请求头、请求内容、响应内容保存
- ✅ Token 统计（tiktoken）
- ✅ 统计分析页面
- ✅ 大数字格式化显示
- ✅ 时区显示修复

### 用户界面
- ✅ 纯 HTML + JavaScript 前端
- ✅ 像素风格设计
- ✅ 中文界面
- ✅ 详情弹窗查看（包含请求头）
- ✅ 对话测试页面

### 部署
- ✅ PyInstaller 打包为 EXE
- ✅ 零依赖运行
- ✅ Windows 平台支持

---

## 🚀 使用说明

### 运行方式
1. **EXE 方式**: 运行 `backend/dist/LLMProxy.exe`
2. **源码方式**: `cd backend && python app.py`
3. **指定端口**: `LLMProxy.exe --port 9000`
4. **不打开浏览器**: `LLMProxy.exe --no-browser`

### 访问地址
- **主页**: http://localhost:8000
- **配置管理**: http://localhost:8000/config
- **调用日志**: http://localhost:8000/logs
- **统计分析**: http://localhost:8000/statistics
- **API 文档**: http://localhost:8000/docs

### 配置步骤
1. 打开配置管理页面
2. 手动创建或通过 CURL 导入配置
3. 激活配置后即可使用
4. 支持通过模型名称自动匹配配置

### Claude Code 接入配置
```bash
# Claude Code 配置示例
ANTHROPIC_API_KEY=任意值
ANTHROPIC_BASE_URL=http://localhost:8000/v1
```

### OpenAI 格式调用
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dummy" \
  -d '{
    "model": "your-model-name",
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

### Anthropic 格式调用
```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: dummy" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "your-model-name",
    "messages": [{"role": "user", "content": "你好"}],
    "max_tokens": 1024
  }'
```

### 流式响应说明
流式响应由配置中的 "是否流式响应" 字段决定：
- 配置中设置 stream=true 时，使用流式响应
- 请求中可以包含 stream 字段来覆盖配置
- 流式响应和非流式响应都会完整记录在日志中

---

## 📁 文件位置

- **主程序**: `backend/app.py`
- **打包配置**: `backend/LLMProxy.spec`
- **可执行文件**: `backend/dist/LLMProxy.exe`
- **前端页面**: `backend/views/*.html`
- **数据库**: `backend/database.sqlite`（运行后生成）
- **版本说明**: `backend/VERSION.md`
