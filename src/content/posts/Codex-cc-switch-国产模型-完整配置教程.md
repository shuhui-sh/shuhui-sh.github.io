---
title: "Codex + cc-switch + 国产模型 完整配置教程"
date: 2026-06-01
description: "1. 背景知识 2. 架构总览 3. 环境准备 4. 安装 Codex CLI 5. 安装并配置 cc-switch"
tags: []
category: "技术"
---
> 适用环境：Windows 10/11 · Codex CLI v0.135.0 · cc-switch v3.16.0 · DeepSeek V4 Pro
> 最后更新：2026-06-01

---

## 目录

1. [背景知识](#1-背景知识)
2. [架构总览](#2-架构总览)
3. [环境准备](#3-环境准备)
4. [安装 Codex CLI](#4-安装-codex-cli)
5. [安装并配置 cc-switch](#5-安装并配置-cc-switch)
6. [手动配置文件](#6-手动配置文件)
7. [启动与验证](#7-启动与验证)
8. [切换供应商与模型](#8-切换供应商与模型)
9. [已知问题与故障排查](#9-已知问题与故障排查)
10. [总结](#10-总结)

---

## 1. 背景知识

### 1.1 Codex CLI 是什么

**Codex CLI** 是 OpenAI 推出的开源命令行 AI 编程助手（Apache 2.0 协议，Rust 编写），定位与 Anthropic 的 Claude Code 同赛道。它的核心能力：

- 在终端中用自然语言描述任务，AI 自动读取项目代码、生成修改、执行命令
- 支持三种安全模式：Suggest（只读建议）、Auto Edit（自动改文件，命令需确认）、Full Auto（完全自动）
- 内置沙箱机制，限制文件系统和网络访问
- 底层调用 OpenAI 的 Responses API，默认模型为 GPT-5.5
- 支持自定义模型供应商，可接入任意 OpenAI 兼容 API

与 Claude Code 的核心区别：Codex 使用 OpenAI 的 Responses API 协议，而非通用的 Chat Completions API。这意味着直接接入只支持 Chat API 的国产模型（DeepSeek、通义千问等）时，需要一层**协议转换**。

### 1.2 cc-switch 是什么

**CC Switch**（[ccswitch.io](https://ccswitch.ai/zh/)，GitHub [farion1231/cc-switch](https://github.com/farion1231/cc-switch)）是一个跨平台桌面工具，用于统一管理 AI 编程 CLI 的供应商、模型和代理配置。它支持 5 大工具：

| 工具 | 厂商 |
|------|------|
| Claude Code | Anthropic |
| Codex | OpenAI |
| Gemini CLI | Google |
| OpenCode | 社区 |
| OpenClaw | 社区 |

核心功能：

- **供应商一键切换**：50+ 内置预设（DeepSeek、通义千问、智谱、Moonshot、SiliconFlow 等），GUI 切换，无需手改配置文件
- **本地路由桥接**：启动本地代理服务，在 Codex 的 Responses API 和国产模型的 Chat Completions API 之间做协议转换
- **MCP / Skills 集中管理**：多工具共享 MCP 服务器和技能配置
- **系统托盘切换**：右键点图标即可切模型，无需打开主界面

### 1.3 为什么要用 cc-switch 接国产模型

Codex CLI 原生只支持 OpenAI 的 Responses API，而国内市场主流的模型服务（DeepSeek、通义千问、智谱等）提供的是 Chat Completions API。两者的请求体、流式事件和返回结构完全不同。

cc-switch 的本地路由功能解决了这个协议断层：

```
Codex (Responses API) → cc-switch 路由桥接 → DeepSeek (Chat API)
                            ↑
                   自动做 Responses ↔ Chat 协议转换
```

---

## 2. 架构总览

```
┌──────────────┐      Responses API       ┌─────────────────────┐      Chat API       ┌────────────────┐
│              │ ─────────────────────────→│                     │ ──────────────────→│                │
│  Codex CLI   │                           │  cc-switch 本地路由  │                     │  DeepSeek API  │
│  v0.135.0    │←─────────────────────────│  127.0.0.1:15723     │←──────────────────│  (厂商真实地址) │
│              │      Responses SSE        │                     │      Chat SSE       │                │
└──────────────┘                           └─────────────────────┘                     └────────────────┘
```

关键设计：

- Codex **始终只跟本机 15723 端口通信**，使用 Responses API 格式
- cc-switch 路由桥接负责：协议转换 + API Key 注入 + 流式响应翻译
- 切换厂商只需改 cc-switch 供应商选择 + 手动更新配置文件

---

## 3. 环境准备

| 依赖 | 版本要求 | 说明 |
|------|----------|------|
| Node.js | 22+ | Codex CLI 运行环境 |
| npm | 随 Node.js | 安装 Codex 用 |
| Git | 2.x+ | Codex 依赖 Git 识别仓库 |
| cc-switch | 3.16.0+ | 供应商管理 + 路由桥接 |
| DeepSeek API Key | — | 从 [platform.deepseek.com](https://platform.deepseek.com) 获取 |

---

## 4. 安装 Codex CLI

```powershell
# 确认 Node.js 版本 (需 22+)
node --version

# 全局安装
npm install -g @openai/codex

# 验证
codex --version   # 应输出 v0.135.0
```

> **不要立即运行 `codex`**，先完成 cc-switch 和配置文件设置。

---

## 5. 安装并配置 cc-switch

### 5.1 安装

从 [GitHub Releases](https://github.com/farion1231/cc-switch/releases) 下载 Windows 安装包（MSI 或便携版），安装后启动。

### 5.2 添加 DeepSeek 供应商

1. 打开 cc-switch → 切到顶部 **Codex** 标签
2. 点击 **+** 添加供应商
3. 选择内置预设 **DeepSeek**
4. 填入 DeepSeek API Key → 保存
5. 点击 DeepSeek 的 **启用** 按钮

### 5.3 配置本地路由

1. **设置 → 路由 → 本地路由**
2. 将地址改为 `127.0.0.1:15723`（避开其他工具可能占用的 15721 端口）
3. 打开 **路由总开关**
4. 在 **路由启用** 中打开 **Codex**

> **注意**：cc-switch 的"Codex 接管"开关在 v3.16.0 中实际上不会自动写入 `config.toml`，需要手动完成下一步。

---

## 6. 手动配置文件

以下配置需要手动写入，cc-switch 目前不会自动生成。

### 6.1 设置环境变量

**必须以管理员身份**打开 PowerShell，执行：

```powershell
[System.Environment]::SetEnvironmentVariable('CODEX_API_KEY', 'sk-你的DeepSeekKey', 'User')
```

> 必须用 `CODEX_API_KEY`，不能用 `OPENAI_API_KEY` 或 `DEEPSEEK_API_KEY`。

### 6.2 config.toml

**路径**：`C:\Users\<用户名>\.codex\config.toml`

```toml
base_url = "http://127.0.0.1:15723/v1"
wire_api = "responses"
model = "deepseek-v4-pro"
model_reasoning_effort = "high"
model_provider = "deepseek"

[model_providers.deepseek]
name = "DeepSeek"
base_url = "http://127.0.0.1:15723/v1"
wire_api = "responses"
requires_openai_auth = true
api_key = "sk-你的DeepSeekKey"
```

配置要点：

| 字段 | 值 | 说明 |
|------|-----|------|
| `base_url` | `http://127.0.0.1:15723/v1` | **始终指向路由桥接**，不是 15722（主代理），不是厂商地址 |
| `wire_api` | `responses` | 保持不变，由路由桥接做协议转换 |
| `model` | `deepseek-v4-pro` | 可选 `deepseek-v4-flash` |

### 6.3 auth.json

**路径**：`C:\Users\<用户名>\.codex\auth.json`

```json
{
  "auth_mode": "apikey",
  "api_key": "sk-你的DeepSeekKey"
}
```

---

## 7. 启动与验证

### 7.1 首次启动

```powershell
codex
```

首次启动会弹出引导界面：

```
1. Sign in with ChatGPT
2. Sign in with Device Code
3. Provide your own API key    ← 选这个
```

选 **3**，粘贴 DeepSeek API Key。此后 `auth.json` 持久化，不再弹引导。

### 7.2 验证模型

启动成功后应看到：

```
╭──────────────────────────────────────────────╮
│ >_ OpenAI Codex (v0.135.0)                   │
│                                              │
│ model:     deepseek-v4-pro high              │
│ directory: J:\YourProject                    │
╰──────────────────────────────────────────────╯
```

在 Codex 中输入 `/model` 确认当前模型。

### 7.3 诊断

```powershell
codex doctor
```

正常情况应显示 `model: deepseek-v4-pro · deepseek`，`reachability` 通过。

### 7.4 测试路由桥接

```powershell
curl -X POST "http://127.0.0.1:15723/v1/responses" `
  -H "Authorization: Bearer sk-你的Key" `
  -H "Content-Type: application/json" `
  -d '{"model":"deepseek-v4-pro","input":"hello"}'
```

返回 HTTP 200 且包含正常响应内容即为桥接正常。

---

## 8. 切换供应商与模型

### 8.1 同厂商切换模型

只改 `config.toml` 一行：

```toml
model = "deepseek-v4-flash"
```

重启 Codex 生效。

### 8.2 切换厂商（如切到百炼）

假设已在 cc-switch 中添加并启用了百炼供应商，手动改 **4 处**：

**第 1 步：更新 config.toml**

```toml
model = "qwen-plus"                  # 改模型名
model_provider = "bailian"           # 改供应商 ID

[model_providers.bailian]            # 改供应商段
name = "Bailian for coding"
base_url = "http://127.0.0.1:15723/v1"     # 不变！
wire_api = "responses"                     # 不变！
requires_openai_auth = true
api_key = "sk-百炼的Key"                    # 换 Key
```

**第 2 步：更新 auth.json**

```json
{ "auth_mode": "apikey", "api_key": "sk-百炼的Key" }
```

**第 3 步：更新环境变量**

```powershell
[System.Environment]::SetEnvironmentVariable('CODEX_API_KEY', 'sk-百炼的Key', 'User')
```

**第 4 步：删除 auth.json 强制重新引导**

```powershell
del C:\Users\<用户名>\.codex\auth.json
codex
```

选 **3** 输入新 Key 确认。

> `base_url` 永远保持 `127.0.0.1:15723` 不变，厂商切换由 cc-switch 路由桥接内部转发。

---

## 9. 已知问题与故障排查

### 9.1 已知问题

| 问题 | 严重程度 | 说明 |
|------|:---:|------|
| cc-switch Codex 接管不生效 | 中 | v3.16.0 不会自动写入 config.toml 和 auth.json，需手动维护 |
| 百炼 reasoning 模型流式中断 | 高 | `qwen3.6-plus` 等带思考的模型，cc-switch 的 Chat→Responses 流式转换会丢失 `reasoning_tokens` 字段，报错 `stream disconnected: missing field reasoning_tokens`。解决方案：用 `qwen-plus`/`qwen-max`，或切回 DeepSeek |
| `Model metadata not found` 警告 | 低 | Codex 无第三方模型元数据，用默认值，不影响功能 |
| 端口冲突 | 低 | CodeMaker 等工具可能占用 15721，路由桥接改为 15723 即可 |
| 切换厂商必须删 auth.json | 中 | Codex 换 Key 后不会自动识别，必须删除 auth.json 重新走引导 |

### 9.2 故障排查速查表

| 现象 | 排查步骤 |
|------|----------|
| `API key auth is missing a key` | ① 检查 auth.json 是否存在且格式正确 ② 检查 `CODEX_API_KEY` 环境变量 ③ 删除 auth.json 重新引导选 3 |
| `stream disconnected: missing field reasoning_tokens` | 换不带 reasoning 的模型，或切回 DeepSeek |
| 路由桥接无响应 | 检查 cc-switch 是否在运行、路由总开关是否打开、端口是否冲突 |
| `provider base URL route returned 404` | 检查 `base_url` 是否指向正确端口 (15723) |
| 聊天无回应 | `curl` 测试路由桥接是否正常，确认 cc-switch 当前供应商已启用 |

---

## 10. 总结

这套方案的代价是首次配置较繁琐（cc-switch 接管不完善导致的），但一旦配好，日常使用只需一行 `codex`。

**三个核心文件**（故障恢复时优先检查）：

| 文件 | 路径 | 作用 |
|------|------|------|
| config.toml | `~/.codex/config.toml` | 模型、供应商、路由地址 |
| auth.json | `~/.codex/auth.json` | API Key 持久化 |
| 环境变量 | `CODEX_API_KEY` | 非交互模式 Key |

**一个不变原则**：`base_url` 永远指向 `http://127.0.0.1:15723/v1`，改厂商改模型都不动它。
