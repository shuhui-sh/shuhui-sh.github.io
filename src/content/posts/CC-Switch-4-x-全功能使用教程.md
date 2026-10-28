---
title: "CC Switch 4.x 全功能使用教程"
date: 2026-10-23
description: "1. 认识 CC Switch 2. 三种连接模式：直连 / 路由 / 聚合 3. 供应商管理（核心） 4. 本地路由与高可用 5."
tags: ['工具', 'Claude Code']
category: "技术"
---
> **适用版本**：CC Switch 4.0.x（本机实测 4.0.18）
> **平台**：Windows 11（macOS / Linux 操作基本一致）
> **依据**：官方用户手册 v4.0.4（中文）逐章整理，并结合本机界面核对
> **说明**：4.x 改版后顶部导航变为左侧栏；网上大量 3.x 教程的菜单路径已过时，以本文为准。
> **图解版（含 4.0.18 实拍截图）**：[CC-Switch-4.x-全功能图解教程.md](./CC-Switch-4.x-全功能图解教程.md)

---

## 目录

1. 认识 CC Switch
2. 三种连接模式：直连 / 路由 / 聚合
3. 供应商管理（核心）
4. 本地路由与高可用
5. 扩展功能：MCP / 提示词 / Skills / 会话 / 工作区 / 项目 / 授权中心
6. 用量与成本
7. 数据、备份与云同步
8. 设置全解
9. 高级功能与集成
10. 应用页：CLI 的安装与升级
11. 故障排查
12. 最佳实践与安全
附录 A 路径速查
附录 B 功能支持矩阵
附录 C 官方文档索引
附录 D 用脚本 / AI 助手辅助操作的边界

---

## 1. 认识 CC Switch

### 1.1 它管理什么

CC Switch 是一个跨平台桌面应用（Tauri + Rust + React），统一管理 10 个 AI 编程工具的**供应商凭据与配置文件**，并提供 MCP、提示词、Skills、会话、用量、路由等高阶功能。

| 应用 | 管理方式 | 配置文件 | 托盘切换 |
|------|----------|----------|----------|
| Claude Code | 切换式 | `~/.claude/settings.json` | ✅ |
| Claude Desktop | 切换式（直连 / 模型映射） | `%LOCALAPPDATA%\Claude-3p\` | ✅ |
| Codex | 切换式 | `~/.codex/config.toml` | ✅ |
| Gemini CLI | 切换式 | `~/.gemini/.env` + `settings.json` | ✅ |
| Grok Build | 切换式 | `~/.grok/config.toml` | ✅ |
| OpenCode | 共存式 | `~/.config/opencode/opencode.json` | ❌ |
| OpenClaw | 共存式 | `~/.openclaw/openclaw.json` | ❌ |
| Hermes | 共存式 | `~/.hermes/config.yaml` | ❌ |
| Pi | 共存式 | `~/.pi/agent/models.json` | ❌ |
| MiniMax Code | 共存式 | `~/.minimax/config.yaml` | ❌ |

- **切换式**：同一时间只启用一个供应商，切换时改写配置文件里的关键字段。
- **共存式**：多个供应商同时写进工具自己的配置，你在工具里选一个用。

### 1.2 安装要点

- **只从官方渠道下载**：<https://ccswitch.io> 或 GitHub Releases（`farion1231/cc-switch`）。任何要你付费/充值/交账号的"CC Switch"都不是官方。
- Windows：`.msi` 安装包或 Portable 绿色版；macOS：`brew install --cask cc-switch`；Linux：deb/rpm/AppImage。
- 首次启动会自动：
  1. 把各工具现有配置导入为名为 `default` 的供应商；
  2. 为各工具创建官方供应商（Claude Official / OpenAI Official / Google Official / Grok Official）；
  3. 导入你已有的 MCP、提示词（如 `CLAUDE.md`）；
  4. 备份原配置文件到 `~/.cc-switch/backups/live-first-write/`。

### 1.3 界面地图

**左侧栏**分三块：

| 区域 | 内容 |
|------|------|
| 应用列表 | Claude Code、Claude Desktop、Codex、Gemini CLI、Grok Build、OpenCode、OpenClaw、Hermes、Pi、MiniMax Code（最多 10 个，可在「应用」页隐藏） |
| 全局页 | MCP、Skills、提示词、会话、授权中心、用量统计 |
| 底部 | 「应用」（安装/升级 CLI、选择侧栏显示）与「设置」 |

**应用页**：页头有「添加供应商」、项目切换（默认隐藏）、`⋯` 菜单（查看会话、配置目录、安装升级、在侧栏隐藏、查看用量）；下方是供应商卡片列表。

**连接模式标签**：Claude Code / Codex / Gemini CLI / Grok Build 顶部有「直连 / 路由 / 聚合」（聚合仅前两者）。**点标签只是查看，不改配置**，真正切换要点下方带后果说明的按钮。

**供应商卡片**：从左到右依次是拖拽手柄、图标、名称/备注/地址、额度信息、状态或主操作、编辑按钮、`⋯` 更多菜单。

**系统托盘**：打开主界面、五个切换式应用的子菜单、项目、轻量模式、官网、退出。

### 1.4 快捷键与搜索

| 快捷键 | 功能 |
|--------|------|
| `Ctrl + ,` | 打开设置 |
| `Ctrl + F` | 供应商页搜索（名称、备注、网址） |
| `Esc` | 关闭搜索 / 设置页返回 |

### 1.5 轻量模式

托盘菜单勾选「轻量模式」：主窗口被销毁（不是隐藏），只留托盘，内存占用接近零；从托盘「打开主界面」或深链接可重建窗口。状态不持久，下次正常启动回到普通模式。

---

## 2. 三种连接模式：直连 / 路由 / 聚合

| | 直连 | 路由 | 聚合 |
|---|---|---|---|
| 请求路径 | 客户端 → 供应商 | 客户端 → 本机 `127.0.0.1:15721` → 供应商 | 客户端 → 本机路由 → 按模型分流 |
| 同时用几家 | 1 家 | 1 家（或按队列轮换） | 多家 |
| 协议转换 | ❌ | ✅ | ✅ |
| 故障转移 | ❌ | ✅ | ❌ |
| 热切换 | ❌（要重启客户端） | ✅（配置不变时） | 在 `/model` 里选模型 |
| 逐请求日志 | 靠会话日志 | ✅ 精确 | ✅ |
| 官方订阅 | ✅ | ❌（Codex OpenAI Official 例外） | Claude 官方不支持 |
| 适用应用 | 全部 | Claude Code / Codex / Gemini / Grok | 仅 Claude Code / Codex |

**选择建议**

- 日常只用一家、协议匹配 → **直连**，最简单；
- 上游协议与客户端不一致，或需要故障转移/热切换 → **路由**；
- 想在一个会话里按模型混用多家 → **聚合**。

---

## 3. 供应商管理（核心）

### 3.1 添加供应商

入口：选中应用 → 页头右侧 **「添加供应商」**（`+`）。

步骤分两步：**选预设 → 填写**。

#### 3.1.1 选预设

- 顶部搜索框可搜名称、网址、常见叫法（kimi、智谱、openrouter…）；
- 左侧分类：**全部 / 账号登录 / 模型厂商 / 第三方平台 / 云服务商**（OpenCode 另有「插件配置」）；
- 「自定义配置」固定在「全部」最上面；
- 同一厂商的国内/海外站、不同套餐合并成一行，选中后可切换「套餐 / 地区 / 版本」；
- 带 **「需要路由」** 徽章的预设，必须开本地路由才能用。

**账号登录类**（不用 API Key）：Claude 官方、ChatGPT（Codex）、GitHub Copilot、xAI、Google 官方。除 Claude 外都需要路由。

#### 3.1.2 填写

大多数预设只需填 **API Key**；端点、协议、模型映射已预置。

自定义配置时需要：

| 字段 | 说明 |
|------|------|
| 名称 / 备注 / 网站链接 | 备注可搜索；网站用于卡片跳转 |
| 请求地址 | 根地址，不带结尾 `/` |
| API Key | 真实 Key，只存 CC Switch |
| 完整 URL（可选） | 网关路径特殊时打开，直接填完整端点；开启后必须走路由 |
| 上游格式（高级选项） | Anthropic Messages / OpenAI Chat Completions / OpenAI Responses / Gemini Native |
| 认证字段 | 默认 `ANTHROPIC_AUTH_TOKEN`（Bearer）；要求 `x-api-key` 时才换 |
| 模型映射 | Claude：Sonnet/Opus/Haiku → 真实模型，**默认兜底必填**；Codex：菜单显示名 / 实际请求模型 / 上下文窗口 / 思考等级 |
| 1M 上下文 | 仅当上游真支持 ≥100 万 token 时勾选 |
| 模型列表（聚合用） | 可「获取模型列表」自动拉取 `/v1/models` |

**自动获取模型**：填好 Key 与地址 → 点模型输入框旁的「获取模型列表」→ 按分组勾选。报 401/403 是 Key 问题，404/405 是该端点不支持 `/v1/models`。

**端点测速**：编辑供应商 → 请求地址旁「管理与测速」→ 添加多个端点 → 测速（绿 <300ms，黄 300–500，橙 500–800，红 ≥800）→ 选最快的。

#### 3.1.3 统一供应商（跨应用共享）

Claude Code / Codex / Gemini CLI 的添加页 → 左侧「统一供应商」：

1. 选预设 → 填名称、Key、地址；
2. 勾选要同步的应用；
3. 保存。修改会同步到所有关联应用；删除会连带删除关联配置。

适合支持多种 API 格式的中转站，一处改、三处生效。

#### 3.1.4 导入供应商

- **深度链接**：`ccswitch://v1/import?resource=provider&...`，见第 9.1 节；
- **SQL 备份导入**：设置 → 数据 → 数据管理 → 选择 SQL 文件 → 导入（覆盖现有数据库，先备份）。

### 3.2 编辑供应商

入口：卡片右侧铅笔图标 → 整页编辑器。

#### 3.2.1 基本信息与图标

- 名称、备注、网站链接、图标；
- 图标：内置图标，或「我的图标」上传 PNG/JPG/WebP/SVG（≤2MB，自动缩为 96×96），图标随云同步；
- 「清除图标」恢复首字母。

#### 3.2.2 配置编辑框（重点）

编辑框显示「切到这个供应商后，配置文件的样子」，内容分两类：

| 类型 | 包括 | 保存位置 | 生效范围 |
|------|------|----------|----------|
| **随供应商切换** | 请求地址、Key、模型名、接口协议、少数兼容选项（如上下文窗口、`CLAUDE_CODE_DISABLE_ARTIFACT`） | 该供应商记录 | 仅这个供应商 |
| **全局设置** | 插件、Hook、权限、MCP、你自己加的环境变量、注释 | 工具配置文件本身 | 所有供应商 |

规则：

- 改全局设置 → **立即写进配置文件**，不管编辑的是哪家；
- 改关键字段 → 存进该供应商；若编辑的是当前使用中的供应商，同时写入配置文件；
- 工具里临时 `/model` 换的模型**不会**存回供应商，切走再切回会恢复供应商保存的值；
- 编辑期间若配置文件被外部改动，保存时会逐项提示「保留外部修改 / 用我的修改覆盖」；
- 配置文件语法错误时，编辑框改为显示供应商里存的内容，并提示原因；CC Switch 会拒绝写入以保护原文件。

Codex 的 Key 不在编辑框里，而是上方单独的 API Key 输入框。

#### 3.2.3 快捷开关（Claude）

JSON 编辑器上方：

| 开关 | 作用范围 | 效果 |
|------|----------|------|
| 隐藏 AI 署名 | 全局 | `attribution` 清空 |
| 启用 Tool Search | 跟随供应商 | `ENABLE_TOOL_SEARCH=true` |
| 禁用自动升级 | 全局 | `DISABLE_AUTOUPDATER=1` |
| 禁用 Artifact 工具 | 跟随供应商 | `CLAUDE_CODE_DISABLE_ARTIFACT=1`，网关 schema 校验失败时有用 |
| 关闭 auto mode 服务端检查 | 跟随供应商 | `CLAUDE_CODE_AUTO_MODE_SERVER=0` |

#### 3.2.4 修改 Key / 地址

直接改 API Key 输入框（眼睛图标可显隐）或端点地址，保存即可。改完按第 3.3.3 节决定是否重启客户端。

### 3.3 切换供应商

#### 3.3.1 主界面

直连页点卡片上的 **「切换」**；卡片变为「使用中」。路由页点 **「路由到此」**；聚合页点「设为默认」或「添加」。

#### 3.3.2 托盘

右键托盘图标 → 应用子菜单 → 点供应商名。子菜单标题显示当前模式、在用供应商、额度摘要。路由 + 故障转移开启时托盘为只读。

#### 3.3.3 生效方式（重要）

| 应用 | 切换后 |
|------|--------|
| Claude Code | **即时生效**（热重载） |
| Claude Desktop | 完全退出并重启 |
| Codex | 重启 Codex（CLI 重开终端；桌面版彻底退出） |
| Gemini CLI | 重启 |
| Grok Build | 重启 |
| OpenCode / OpenClaw | 重开终端 |
| Hermes | 点卡片「启用」后生效 |
| Pi / MiniMax Code | 在工具里选模型 |

**路由模式下**：换上游对后续请求立即生效、无需重启；但如果新供应商改了模型名，Codex / Gemini / Grok 仍需重启加载配置。

#### 3.3.4 切换失败

- 配置文件被锁定 → 关闭正在运行的 CLI；
- 权限不足 → 检查目录权限；
- JSON/TOML 格式错误 → 编辑供应商修复（CC Switch 会提示行列号）。

### 3.4 排序、复制、删除

- **排序**：悬停卡片左侧出现 `⋮⋮`，拖拽；顺序同时决定托盘顺序与故障转移队列默认顺序；
- **复制**：`⋯` → 复制，生成带 `copy` 后缀的副本（备注不复制，其余复制）；
- **删除**：`⋯` → 删除；**使用中的供应商不能删**，先切到别家；统一供应商删除会连带删除关联配置。

### 3.5 用量查询（卡片额度/余额）

分两类：

| 类别 | 覆盖 | 是否需启用 |
|------|------|-----------|
| 自动显示 | GitHub Copilot、Codex OAuth、xAI OAuth | 否 |
| 内置模板 | 官方订阅（Claude/Codex/Gemini/Grok）、Token Plan（Kimi/GLM/MiniMax/火山/OpenCode Go/Command Code）、第三方余额（DeepSeek/StepFun/SiliconFlow/OpenRouter/Novita） | 是 |
| 自定义脚本 | 其他中转/私有部署 | 是 |

**启用步骤**：卡片 `⋯` →「配置用量查询」→ 打开「启用用量查询」→ 选模板 →（可选）填 Key/Base URL/Access Token/User ID →「测试脚本」→ 保存。

**自动查询间隔**：0–1440 分钟，`0` 关闭；仅「使用中」的供应商会后台查询。

**自定义脚本结构**：

```javascript
({
  request: {
    url: "{{baseUrl}}/user/balance",
    method: "GET",
    headers: { "Authorization": "Bearer {{apiKey}}" }
  },
  extractor: function (response) {
    return {
      isValid: true,
      remaining: response.balance,
      unit: "USD",
      planName: "默认套餐",
      total: 100,
      used: 20
    };
  }
})
```

**占位符**：`{{apiKey}}`、`{{baseUrl}}`、`{{accessToken}}`、`{{userId}}`。

**提取器字段**：`isValid`、`invalidMessage`、`remaining`、`unit`、`planName`、`total`、`used`、`extra`。

**显示规则**：剩余 <10% 时加深加粗；用完显示「已用完」；查询失败显示「额度没查到」；点击额度可手动刷新。

### 3.6 Claude Desktop 专属

Claude Desktop 没有直连/路由/聚合标签，而是每个供应商单独选 **直连** 或 **模型映射**。

#### 一键从 Claude Code 导入

首次进入且列表为空时，点 **「将 Claude Code 中已有的供应商导入」**：

- 三档角色 ID 且能直连的 → 导入为直连；
- 非三档角色 ID → 尝试导入为模型映射；
- `ANTHROPIC_DEFAULT_*_MODEL` 转为 Desktop 映射；`[1M]` 转为 `supports1m`；
- 无法判断的会跳过。

#### 直连模式

适合原生 Anthropic Messages 且模型名是 `claude-sonnet-*` / `claude-opus-*` / `claude-haiku-*` 的供应商。写入 3P profile：

```json
{
  "inferenceProvider": "gateway",
  "inferenceGatewayBaseUrl": "https://api.example.com",
  "inferenceGatewayAuthScheme": "bearer",
  "inferenceGatewayApiKey": "sk-..."
}
```

#### 模型映射模式

适合 DeepSeek / Kimi / GPT / Gemini 等非 Claude 模型，或需要协议转换。Desktop 连接 `http://127.0.0.1:15721/claude-desktop`，由本地路由把角色映射到真实模型。**必须保持 CC Switch 运行**（服务自动启动）。

模型映射表：

| 模型角色 | 菜单显示名 | 实际请求模型 | 1M |
|----------|-----------|--------------|----|
| Sonnet | DeepSeek V4 Pro | `deepseek-v4-pro` | 按上游能力 |
| Opus | … | … | … |
| Haiku | … | … | … |

至少填一行；留空角色会沿用第一个已填模型（Sonnet 优先）。

#### 恢复官方

选 **Claude Desktop Official** → 切换 → 重启 Desktop，CC Switch 会恢复官方 1P 模式。

配置文件位置（Windows）：

```
%LOCALAPPDATA%\Claude\claude_desktop_config.json
%LOCALAPPDATA%\Claude-3p\claude_desktop_config.json
%LOCALAPPDATA%\Claude-3p\configLibrary\_meta.json
%LOCALAPPDATA%\Claude-3p\configLibrary\00000000-0000-4000-8000-000000157210.json
```

### 3.7 共存式应用

| 应用 | 按钮 | 写入位置 |
|------|------|----------|
| OpenCode | 添加 / 移除 | `opencode.json` |
| OpenClaw | 添加 / 移除 + 设为默认 | `openclaw.json` |
| Hermes | 添加 / 移除 + 启用 | `config.yaml` → `custom_providers` |
| Pi | 启用 / 移除 | `models.json` |
| MiniMax Code | 添加 / 移除 | `config.yaml` → `custom_provider` |

删除限制：Hermes 当前使用中的、OpenClaw 默认模型引用的、MiniMax 默认模型引用的不能删。

---

## 4. 本地路由与高可用

### 4.1 路由服务

**启动方式**

- 自动：应用页「路由」标签 →「开始路由」（服务未运行会自动启动）；
- 手动：设置 → 本地路由 → 服务 →「启动」。

**基础配置**

| 设置 | 说明 | 默认 |
|------|------|------|
| 监听地址 | `127.0.0.1` 仅本机；`0.0.0.0` 允许局域网 | `127.0.0.1` |
| 监听端口 | 1024–65535 | `15721` |
| 连接地址 | 写进客户端配置的地址；WSL/远程时改这里 | 随监听地址推导 |
| 记录请求用量 | 记录逐请求明细 | 开启 |

修改后点「保存并重启服务」。

**WSL2 场景**：监听设 `0.0.0.0`，连接地址填 WSL 能访问的 Windows IP（如 `vEthernet (WSL)`），防火墙放行端口。

**停止**：有应用在用路由/聚合时「停止」是灰的；先「全部回到直连」。

**退出 CC Switch**：先写回直连，下次启动自动重连；重连失败会回退直连并提示。

### 4.2 应用路由

**进入**：应用页「路由」标签 →「开始路由」→ 选「路由到」哪家 → 确认。

确认框会说明：改写客户端地址与密钥、真实 Key 留在 CC Switch、需要保持运行、退出时写回直连。

**配置变更**

| 应用 | 路由后 |
|------|--------|
| Claude Code | `ANTHROPIC_BASE_URL=http://127.0.0.1:15721`，Key=`PROXY_MANAGED` |
| Codex | `base_url=http://127.0.0.1:15721/v1` |
| Gemini | `GOOGLE_GEMINI_BASE_URL=http://127.0.0.1:15721` |
| Grok Build | `http://127.0.0.1:15721/grokbuild/v1` |

**请求流程**：识别来源 → 查当前目标（或队列）→ 按需转换格式 → 转发 → 记录日志 → 返回。

**格式转换矩阵**

Claude 侧（发 Anthropic Messages）：

| 上游格式 | 行为 |
|----------|------|
| Anthropic Messages | 透传 |
| OpenAI Chat Completions | Chat 互转 |
| OpenAI Responses | Responses 互转 |
| Gemini Native | Gemini 互转 |

Codex / Grok 侧（发 Responses）：

| 上游格式 | 行为 |
|----------|------|
| Responses（原生） | 透传 |
| Chat Completions | Chat 互转 |
| Anthropic Messages | Messages 互转 |

**热切换**：路由页「路由到此」，后续请求立即生效；正在进行的请求不变。

**状态**：`路由中`（实际在用）、`直连`（退出路由后恢复）、`路由到此`（按钮）、`需要路由`（不能直连）。

**退出**：应用页「回到直连」，或设置 → 本地路由「全部回到直连」。

### 4.3 故障转移

**前提**：应用在路由模式 + 故障转移开关打开 + 队列有备用。

**开启**：路由标签栏右侧交叉箭头开关 → 首次确认「我已了解，继续启用」。

**队列**：开启后分「队列 · 按优先级」与「不在队列」；点「加入队列」，上移/下移/拖拽排序，`P1` 优先。

**熔断参数**

| 配置 | 通用默认 | Claude 默认 | 范围 |
|------|----------|-------------|------|
| 失败阈值 | 4 | 8 | 1–20 |
| 恢复成功阈值 | 2 | 3 | 1–10 |
| 恢复等待 | 60s | 90s | 0–300 |
| 错误率阈值 | 60% | 70% | 0–100% |
| 最小请求数 | 10 | 15 | 5–100 |

**超时**：首字节 60/90s；流式静默 120/180s（0 关闭）；非流式 600s。

**重试**：通用 3 次，Claude 6 次，Gemini 5 次。

**熔断状态**：闭合（放行）→ 打开（跳过）→ 半开（探测）。卡片健康：🟢 正常 / 🟡 降级 / 🔴 熔断。

**日志**：用量统计 → 请求日志，记录原供应商、新供应商、失败原因。

### 4.4 聚合模式

仅 Claude Code / Codex。把多家供应商的模型放进客户端 `/model`。

**进入**：应用页「聚合」标签 → 配置模型列表 →「切换到聚合模式」→ 确认（确认框会列出默认供应商与模型）。

**添加/移除**：「可添加」点「添加」；「已添加」点「移除」；默认供应商不能移除。

**模型列表**：编辑供应商 → 「获取模型列表」自动拉取 → 勾选 →「添加所选模型」；也可手动添加；context/能力可从 models.dev 自动补全。

**默认供应商**：承接不带前缀的请求；Codex 的 OpenAI Official 只能作默认。

**`ccs-` 前缀**：非默认供应商的模型在 `/model` 里带 `ccs-` 前缀；不带前缀走默认。

**重启规则**：Claude Code 立即生效；Codex 必须重启（CLI 需「重启 Codex 守护进程」，会中断任务；桌面版彻底退出）。

**Codex 子 agent 模型**：聚合设置（页签右上齿轮）→ 子代理模型/推理强度 → 写入 `config.toml [agents]`；跨供应商时必须开「聚合模式下子 agent 用经典工具」。

**Codex 自动审批模型**：聚合设置 → 自动审批模型 → 写入模型目录 `auto_review_model_override`；改完要重启 Codex。

**限制**：不做故障转移；Claude 官方订阅不支持；需保持 CC Switch 运行。

### 4.5 整流器

设置 → 本地路由 → 整流器。自动修复上游不兼容请求，例如 Thinking 签名不兼容时移除相关字段后重试、图片不支持时降级。

### 4.6 连通检测

卡片 `⋯` →「检测连通」：向 base URL 发轻量请求，收到任意 HTTP 响应（含 401/403/404/5xx）即「可达」；只验证网络层，**不验证 Key 与模型**。参数固定：超时 8s、重试 1 次、>6000ms 标「较慢」。不影响熔断判定。

---

## 5. 扩展功能

### 5.1 MCP 服务器

入口：左侧栏 **MCP**（全局页）。矩阵表：每行一个 MCP，每列一个应用，格子开关控制该应用是否启用。

**支持 8 个应用**：Claude Code、Codex、Gemini CLI、Grok Build、OpenCode、Hermes、Pi、MiniMax Code（Claude Desktop、OpenClaw 不支持）。

**添加**：

- 页头「添加 MCP」→「从模板开始」（fetch / time / memory / sequential-thinking / context7）或自定义；
- 「粘贴配置」可识别 JSON、Codex `[mcp_servers.x]`、OpenCode local/remote 写法；
- 填写：名称（不能有空格，保存后不可改名）、连接方式（stdio / http / sse）、命令或地址、参数、环境变量、工作目录、请求头；
- 「写入到」勾选应用 → 添加。

**应用绑定**：点格子开关；列头可批量「全部启用/关闭」，行 `⋯` 可「在所有应用启用/全部关闭」。

**导入**：页头「从应用导入」，读取各工具用户级配置；项目级 MCP（`claude mcp add` 默认写项目）不会导入。

**写入位置**：Claude `~/.claude.json`、Codex `config.toml [mcp_servers]`、Gemini `settings.json`、Grok `config.toml`、OpenCode `opencode.json`、Hermes `config.yaml`、Pi `mcp.json`、MiniMax `mcp.json`。

**注意**：CC Switch 只管理库内服务器；同名条目以 CC Switch 为准。

### 5.2 提示词（Prompts）

入口：左侧栏 **提示词**。页头下拉选应用（Claude Code / Codex / Gemini / Grok / OpenCode / Hermes / Pi / MiniMax Code）。

**目标文件**

| 应用 | 文件 |
|------|------|
| Claude Code | `~/.claude/CLAUDE.md` |
| Codex | `~/.codex/AGENTS.md` |
| Gemini CLI | `~/.gemini/GEMINI.md` |
| Grok Build | `~/.grok/AGENTS.md` |
| OpenCode | `AGENTS.md` |
| Hermes | `~/.hermes/SOUL.md` |
| Pi | `~/.pi/agent/AGENTS.md` |
| MiniMax Code | `~/.minimax/AGENTS.md`（≤32KiB） |

**规则**：同一应用同时只启用一条；启用会覆盖目标文件，停用会清空（Pi 删除 `AGENTS.md`）。

**操作**：添加（名称/说明/Markdown 正文）→ 启用 → 编辑 → 停用；`⋯` 可「复制到其他应用」「复制正文」「删除」。启用中的不能删除。

**手动改文件**：CC Switch 不会丢——下次打开页面会把改动收进启用中的那条；若列表为空可「导入现有内容」。

**Pi 特别**：三个标签——提示库（AGENTS.md）、系统提示（`APPEND_SYSTEM.md` 追加 / `SYSTEM.md` 替换，存在即生效）、模板（`/命令名` 调用）。已打开的 Pi 需 `/reload`。

### 5.3 Skills

入口：左侧栏 **Skills**（全局页）。两个视图：**已安装 / 发现**。

**支持**：Claude Code、Codex、Gemini、Grok、OpenCode、Hermes、Pi、MiniMax Code（OpenClaw 不支持）。

**发现**：来源可选「仓库」（预置 anthropics/skills、ComposioHQ/awesome-claude-skills 等）或「skills.sh」；先在「安装到」选应用，再点「安装」。

**其他安装方式**：`⋯` →「从 ZIP 安装」（需含 `SKILL.md`）、「导入本机已有」。

**安装目录**：各应用的 `skills/`；主副本默认 `~/.cc-switch/skills/`，通过软链接或复制同步。

**更新**：基于 SHA-256 内容哈希检测；`⋯` →「检查更新」→「更新」/「全部更新」；更新会覆盖本地改动（只留备份）。

**卸载**：`⋯` →「卸载」，自动备份到 `~/.cc-switch/skill-backups/`；可「从备份恢复」。

**存储与同步**（`⋯` 菜单）：

| 主副本位置 | 说明 |
|------------|------|
| CC Switch 目录 `~/.cc-switch/skills/` | 默认，统一管理 |
| 通用目录 `~/.agents/skills` | 社区共享约定；Codex/Gemini/OpenCode 会直接读，开关不再完全生效 |

同步方式：自动（优先软链接）/ 只用软链接（Windows 需开发者模式）/ 只用复制；改完可「立即重新同步」。

**仓库管理**：添加 `owner/name`（或完整 URL）+ 分支 + 子目录。

### 5.4 会话管理器

入口：左侧栏 **会话**（全局页）。默认显示当前应用，可切「全部应用」。

**支持**：Claude Code、Codex、Gemini CLI、Grok Build、OpenCode、OpenClaw、Hermes、Pi、MiniMax Code（Hermes 只显示最近 500 个）。

**功能**：

- 搜索：标题、项目目录、首末消息、会话 ID；
- 分组：按时间（今天/昨天/本周/更早）或按项目；
- 详情：按提问/回复分轮，执行过程折叠可展开；视图「全部 / 对话 / 改动」；对话目录跳转；会话内查找；复制/导出 Markdown；
- 恢复：点「恢复」；macOS 用首选终端直接打开，其他平台复制命令到剪贴板；
- 删除：`⋯` → 删除（永久、不进回收站）；
- 批量：`⋯` →「选择多个…」→ 全选匹配结果 → 删除。

**不支持恢复**：OpenClaw（网关管理）、Hermes（暂不支持 CLI 恢复）；Codex 切过供应商的旧会话可能无法继续。

### 5.5 OpenClaw 工作区与每日记忆

入口：侧栏 OpenClaw → 页签「工作区」。

- 管理 9 个文件：`AGENTS.md`、`SOUL.md`、`USER.md`、`IDENTITY.md`、`TOOLS.md`、`MEMORY.md`、`HEARTBEAT.md`、`BOOTSTRAP.md`、`BOOT.md`；
- 文件存在显示绿勾，不存在首次保存时创建；
- 「每日记忆文件」→ 按日期管理 `~/.openclaw/workspace/memory/YYYY-MM-DD.md`，支持创建、搜索、编辑、删除；「添加记忆」打开今日笔记。

### 5.6 项目（Profiles）

把 Claude Code / Codex 的**当前供应商 + MCP + Skills + 提示词**保存为一套「项目」（Claude Desktop 只存供应商），一键整体切换。

- 开启入口：设置 → 通用 →「显示项目切换」；
- 切换位置：应用页顶部项目切换器、托盘「项目」；
- 切到另一个项目时，当前状态会自动保存回上一个项目。

适合「公司项目 / 个人项目」两套完全不同的配置。

### 5.7 授权中心（Beta）

入口：左侧栏 **授权中心**。

| 账号 | 用途 |
|------|------|
| GitHub Copilot | Copilot 反向代理 |
| ChatGPT（Codex OAuth） | Codex OAuth 反向代理，在 Claude Code 中用 ChatGPT 订阅 |
| xAI（Grok OAuth） | xAI Responses 反向代理 |

能力：Device Code 登录、查看账号与状态、设默认账号、移除账号。

**风险**：账号型反向代理使用逆向 OAuth 流程，可能违反服务条款、导致账号受限，自行评估。

---

## 6. 用量与成本

入口：左侧栏 **用量统计**（全局页）。

### 6.1 数据来源

| 来源 | 覆盖 | 需要路由 |
|------|------|----------|
| 路由请求日志 | 经路由/聚合的请求 | 是 |
| CLI 会话日志 | Claude Code、Codex、Gemini、Grok、OpenCode、Pi、MiniMax | 否 |

- 会话日志默认自动扫描：启动时一次 + 后台每 10 分钟；打开页面立即扫描，并按「扫描间隔」（5/10/30/60 秒）刷新；
- 会话日志分不清供应商，供应商列显示「{应用} · 会话日志」；
- OpenClaw / Hermes 不支持；Claude Desktop 只统计模型映射请求，计入 Claude Code。

### 6.2 看板

- 汇总：总成本、总请求、真实消耗 Tokens（新增输入 + 输出 + 缓存写入 + 缓存命中）、缓存命中率；
- 时间范围：当天 / 24h / 7d / 14d / 30d / 全部 / 自定义；
- 筛选：应用、供应商、模型；
- 热力图：最近 53 周；
- 趋势图：Tokens / 请求 / 成本，按小时或按天。

### 6.3 明细

四个 Tab：

- **请求日志**：时间、应用、供应商、模型、新增输入、输出、缓存命中、成本、速度；状态码筛选；点行看详情（来源、tokens、成本、耗时、首字）；
- **供应商**：请求数、Tokens、成本、成功率、速度；
- **模型**：同上 + 平均成本；
- **定价**：见 6.4。

### 6.4 定价

- 计费默认配置：按「请求模型」或「返回模型」匹配（仅路由请求生效）；
- 模型定价：输入/输出/缓存读取/缓存创建（每百万 token）；
- 「从 models.dev 导入」；「自动同步 models.dev 定价」（最多每 6 小时）；
- 模型 ID 会先标准化：去前缀、小写、去 `:后缀`、去 `[1m]`、`@`→`-`、去版本/日期后缀。**填清洗后的 ID**；
- 金额是估算，以供应商账单为准。

---

## 7. 数据、备份与云同步

### 7.1 存储结构

```
~/.cc-switch/
├── cc-switch.db            # SQLite：供应商/MCP/Prompts/Skills/项目/路由配置/用量/定价
├── settings.json           # 设备级设置
├── live-state.json         # 各应用模式与上次写入内容（勿手改）
├── codex-login-stash.json  # 暂存的 Codex 官方登录
├── copilot_auth.json
├── codex_oauth_auth.json
├── xai_oauth_auth.json
├── skills/                 # 技能主副本
├── skill-backups/          # 技能卸载备份
├── backups/                # 数据库/环境变量备份
│   └── live-first-write/   # 配置文件首次改写前原件
└── logs/cc-switch.log
```

> `settings.json`、`live-state.json`、`codex-login-stash.json`、`live-first-write/` 只在本机，不随云同步。

### 7.2 导入导出

设置 → 数据 → 数据管理：

- **导出 SQL 备份**：供应商、MCP、Prompts、用量日志、设置；文件名 `cc-switch-export-{时间戳}.sql`；
- **导入 SQL**：只支持 CC Switch 导出的备份；导入前自动备份，导入会覆盖现有配置。

### 7.3 备份与恢复

- 自动备份：间隔 6h/12h/24h/48h/7d（默认 24h），保留 3–50 个（默认 10）；
- 操作：立即备份 / 恢复（恢复前自动安全备份）/ 重命名 / 删除；
- 「其他备份」列出技能备份、配置文件原件、会话迁移备份、环境变量备份等，可逐项显示或删除。

### 7.4 云同步

WebDAV 或 S3 兼容存储（二选一）：

- WebDAV：坚果云 / Nextcloud / 群晖 / 自定义；
- S3：AWS / MinIO / R2 / 阿里 OSS / 腾讯 COS / 华为 OBS / 自定义；
- 远程根目录默认 `cc-switch-sync`，同步配置名默认 `default`；
- 「测试连接」→「上传 / 下载」；下载前显示远程快照（协议版本、数据库版本、时间、大小、兼容性），覆盖前自动备份；
- 「自动同步」：每次数据库变更自动上传。

### 7.5 诊断日志

设置 → 数据 → 应用诊断日志：开关 + 级别（error/warn/info/debug/trace）。日志在 `~/.cc-switch/logs/`，崩溃在 `~/.cc-switch/crash.log`。

---

## 8. 设置全解

快捷键 `Ctrl + ,`，或侧栏底部「设置」。六组：

### 8.1 通用

| 项 | 说明 |
|----|------|
| 界面语言 | 简中/繁中/English/日本語，立即生效 |
| 明暗 | 跟随系统/浅色/深色 |
| 侧栏显示哪些应用 | 跳到「应用」页设置（至少保留一个） |
| 显示项目切换 | 应用页顶部出现项目切换器 |
| 启动时检查各应用新版本 | 只提示，不自动升级 |
| 开机自启 | Windows 注册表 / macOS LaunchAgent / Linux XDG |
| 静默启动 | 自启时不显示主窗口 |
| 关闭时最小化到托盘 | 默认开；关掉则关闭即退出 |
| 首选终端 | 打开终端按钮用哪个终端 |
| 轻量模式 | 托盘菜单启用 |

### 8.2 应用配置

- **Claude Code**：应用到 VS Code 插件（写 `primaryApiKey`）；跳过初次安装确认（写 `hasCompletedOnboarding`）。
- **Codex**：
  - 非接管切换时保留官方登录（关闭=切第三方时删除并暂存 `auth.json`，切回还原；开启=直接保留）；
  - 统一 Codex 会话历史（官方与第三方会话合并显示，可迁移，自动备份）。
- **配置目录覆盖**：Claude Code、Codex、Gemini、Grok、OpenCode、OpenClaw、Hermes、Pi 八项，留空用默认；Claude Desktop、MiniMax Code 不支持。
- **WSL**：可把目录指向 `\\wsl.localhost\Ubuntu\home\<user>\.claude`。

### 8.3 本地路由

服务 / 正在使用路由的应用 / 自动故障转移 / 整流器 / 全部回到直连（详见第 4 章）。

### 8.4 网络

**全局出站代理**：HTTP/HTTPS 代理，用于访问外部 API、技能下载等。

### 8.5 数据

存储位置、SQL 导入导出、备份恢复、云同步、诊断日志（详见第 7 章）。

### 8.6 关于

版本、检查更新、GitHub/官网/更新日志、「近期更新」。

---

## 9. 高级功能与集成

### 9.1 深度链接 `ccswitch://`

在线生成器：<https://ccswitch.io/deplink.html>

**通用格式**

```
ccswitch://v1/import?resource={provider|mcp|prompt|skill}&app={app}&name={name}&...
```

`app` 取值：`claude` / `codex` / `gemini` / `grokbuild` / `opencode` / `openclaw` / `hermes` / `pi`；prompt 另支持 `mcode`。

**供应商关键参数**

| 参数 | 说明 |
|------|------|
| `endpoint` | 端点（逗号分隔多个） |
| `apiKey` | 密钥 |
| `apiFormat` | `anthropic` / `openai_chat` / `openai_responses` / `gemini_native` |
| `model` / `sonnetModel` / `opusModel` / `haikuModel` | 模型 |
| `config` + `configFormat` | Base64 配置（json/toml） |
| `enabled` | 导入后是否立即切换 |
| `usageScript` / `usageEnabled` | 用量查询脚本 |

**示例**

```
ccswitch://v1/import?resource=provider&app=claude&name=My%20Provider&endpoint=https%3A%2F%2Fapi.example.com&apiKey=sk-xxx
```

**MCP**：`apps=claude,codex,...` + `config`（Base64 的 `{"mcpServers":{...}}`）。

**提示词**：`content`（Base64 + URL 转义，必填）。

**Skill**：`repo=owner/name`，添加的是仓库，不是直接安装技能。

**安全**：深链接可能含 Key，不要公开分享；导入前会显示确认与风险提示（内网地址、可疑环境变量、shell 命令等）。

### 9.2 环境变量冲突

CC Switch 自动检测：

| 应用 | 检测前缀 |
|------|----------|
| Claude Code | `ANTHROPIC*` |
| Codex | `OPENAI*` |
| Gemini | `GEMINI*`、`GOOGLE_GEMINI*` |
| Grok Build | `XAI_API_KEY`、`GROK_DEFAULT_MODEL` |

顶部黄色横幅 →「查看详情」→ 勾选 →「删除选中」；删除前自动备份到 `~/.cc-switch/backups/env-backup-<时间戳>.json`。

**为什么要管**：环境变量优先级高于配置文件，会导致请求打到错误端点或用错 Key。建议不要在系统环境变量里放 API Key。

### 9.3 配置目录覆盖

设置 → 应用配置；改完重启 CC Switch，且 CLI 也要使用同一目录。MCP / Skills / 提示词路径随之变化。

### 9.4 手动编辑规则

| 位置 | 能否手改 |
|------|----------|
| 工具配置里的全局设置（插件、hooks、MCP…） | ✅ 随便改，切换不会动 |
| 工具配置里的关键字段（地址、Key、模型） | ⚠️ 改了只生效到下次切换 |
| `settings.json` | ✅ |
| `cc-switch.db`、`live-state.json`、`codex-login-stash.json`、备份 | ❌ 不建议 |

**保护机制**：配置文件语法错误时 CC Switch 拒绝写入；首次改写的原文件在 `backups/live-first-write/`。

---

## 10. 应用页：CLI 的安装与升级

侧栏底部 **应用**：

- 查看各工具当前版本 / 最新版本；
- 未安装 → 安装；已安装 → 单独升级或「全部升级」；
- 选择侧栏显示哪些应用；
- 「手动安装命令」可复制；
- Claude Desktop 只显示是否接入，不能在这里装；
- 若配置目录指向 WSL，会在对应发行版里检测和升级。

**自动检查**：设置 → 通用 →「启动时检查各应用的新版本」，只提示不自动升级。

---

## 11. 故障排查

### 11.1 通用排查顺序

1. 设置 → 本地路由：服务是否运行、端口是否被占；
2. 应用页：当前是直连/路由/聚合，卡片是否「使用中/路由中」；
3. 客户端是否重启（按第 3.3.3 节）；
4. 看「用量统计 → 请求日志」里的状态码与错误；
5. 看 `~/.cc-switch/logs/cc-switch.log`。

### 11.2 常见问题

| 现象 | 原因 | 处理 |
|------|------|------|
| 切换后不生效 | 客户端没重载 | Claude Code 重开终端；其余重启工具 |
| `/model` 看不到聚合模型 | Codex 用旧模型列表 | CLI「重启 Codex 守护进程」；桌面版彻底退出；插件重开窗口 |
| 路由后全部失败 | 服务没起 / 端口占用 / 没重开会话 | 查服务；换端口；重开会话 |
| 401/403 | 认证字段或 Key 错 | 认证字段用 `ANTHROPIC_AUTH_TOKEN`；核对 Key |
| 404/405 | 上游格式选错 / 模型名错 / 路径不对 | 改上游格式；核对模型；试「完整 URL」 |
| 请求超时 | 网络 / 上游慢 / 超时太宽 | 调路由设置；检查代理；直连测试 |
| 端口被占用 `Address already in use` | 15721 被其他程序占用 | 换端口或关闭占用程序 |
| 回到直连配置没恢复 | 异常退出 / 外部修改 | 重进再退出；手动保存供应商；用备份 |
| 官方供应商路由页变灰 | 官方订阅不经路由 | 回直连 |
| Grok 官方无法开始路由 | 同上 | 先切第三方 |
| 全部供应商熔断 | 连续失败 | 等恢复；或全部回直连→停服务→重新路由 |
| 额度不显示 | 未启用查询 / 非使用中 / Token 过期 | 配置用量查询；切到使用中；重新登录 |
| 环境变量冲突横幅 | 系统里有 `ANTHROPIC_*` 等 | 查看详情并删除，或手动清理 |
| 技能无法更新 | 网络 / 仓库分支错误 | 检查网络；重新读取仓库 |
| 会话恢复按钮灰 | 无恢复命令 / OpenClaw/Hermes | 手动在项目目录恢复 |
| 启动失败（Windows） | 缺 WebView2 / 杀软拦截 | 安装 WebView2；放行 |

### 11.3 回滚手段

- 单应用：应用页「回到直连」；
- 全部：设置 → 本地路由「全部回到直连」；
- 配置：设置 → 数据 → 备份与恢复 → 恢复；
- 原文件：`~/.cc-switch/backups/live-first-write/`；
- 环境变量：`~/.cc-switch/backups/env-backup-*.json`。

---

## 12. 最佳实践与安全

1. **先备份再折腾**：设置 → 数据 → 立即备份；
2. **路由只监听 `127.0.0.1`**；改 `0.0.0.0` 前评估局域网风险并配防火墙；
3. **Key 只存 CC Switch**，不要同时放系统环境变量（会冲突）；
4. **模型映射的默认兜底必填**，否则未匹配请求会透传 Claude 模型名而报错；
5. **1M 勾选要谨慎**，超过上游真实窗口会直接报错；
6. **故障转移队列**：最稳的放 P1，次优 P2，兜底 P3；参数别调得太激进；
7. **用量金额是估算**，以账单为准；
8. **OAuth 订阅反代有账号风险**，使用前阅读条款；
9. 定期检查「其他备份」占用，避免磁盘膨胀；
10. 不要手动编辑 `cc-switch.db` 与 `live-state.json`。

---

## 附录 A：路径速查（Windows）

| 内容 | 路径 |
|------|------|
| CC Switch 数据 | `C:\Users\<用户>\.cc-switch\` |
| Claude Code | `~/.claude/settings.json`、`~/.claude.json`（MCP） |
| Codex | `~/.codex/config.toml`、`auth.json`、`cc-switch-model-catalog.json` |
| Gemini | `~/.gemini/.env`、`settings.json` |
| Grok Build | `~/.grok/config.toml` |
| OpenCode | `~/.config/opencode/opencode.json` |
| OpenClaw | `~/.openclaw/openclaw.json` |
| Hermes | `%LOCALAPPDATA%\hermes\config.yaml` |
| Pi | `~/.pi/agent/models.json` |
| MiniMax Code | `~/.minimax/config.yaml` |
| Claude Desktop 3P | `%LOCALAPPDATA%\Claude-3p\` |

---

## 附录 B：功能支持矩阵

| 功能 | CC | Desktop | Codex | Gemini | Grok | OpenCode | OpenClaw | Hermes | Pi | MiniMax |
|------|----|---------|-------|--------|------|----------|----------|--------|----|---------|
| 供应商管理 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 本地路由 | ✅ | 模型映射 | ✅ | ✅ | ✅ | – | – | – | – | – |
| 故障转移 | ✅ | – | ✅ | ✅ | ✅ | – | – | – | – | – |
| 聚合 | ✅ | – | ✅ | – | – | – | – | – | – | – |
| MCP | ✅ | – | ✅ | ✅ | ✅ | ✅ | – | ✅ | ✅ | ✅ |
| Skills | ✅ | – | ✅ | ✅ | ✅ | ✅ | – | ✅ | ✅ | ✅ |
| 提示词 | ✅ | – | ✅ | ✅ | ✅ | ✅ | 工作区 | ✅ | ✅ | ✅ |
| 会话 | ✅ | – | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 用量统计 | ✅ | 模型映射 | ✅ | ✅ | ✅ | ✅ | – | – | ✅ | ✅ |
| 托盘切换 | ✅ | ✅ | ✅ | ✅ | ✅ | – | – | – | – | – |

> CC = Claude Code；– 表示不支持。

---

## 附录 C：官方文档索引

- 用户手册总目录：`docs/user-manual/zh/README.md`
- 1.1 介绍 / 1.2 安装 / 1.3 界面 / 1.4 快速上手 / 1.5 设置
- 2.1 添加 / 2.2 切换 / 2.3 编辑 / 2.4 排序复制 / 2.5 用量查询 / 2.6 Claude Desktop
- 3.1 MCP / 3.2 Prompts / 3.3 Skills / 3.4 会话 / 3.5 工作区
- 4.1 本地路由服务 / 4.2 应用路由 / 4.3 故障转移 / 4.4 用量统计 / 4.5 连通检测 / 4.6 聚合
- 5.1 配置文件 / 5.2 FAQ / 5.3 深度链接 / 5.4 环境变量冲突

在线：<https://github.com/farion1231/cc-switch/tree/main/docs/user-manual/zh>

---

## 附录 D：用脚本 / AI 助手辅助操作的边界

**可以可靠完成**（涉及文件与数据库读取）：

- 读取 `~/.cc-switch/settings.json`、`live-state.json`、`cc-switch.db` 了解现状；
- 读取/核对各工具配置文件里的关键字段；
- 生成 `ccswitch://` 深链接供你在 CC Switch 里确认导入；
- 检查端口占用、查看日志、备份配置文件。

**不可靠/不建议**：

- 直接改 `cc-switch.db` 或 `live-state.json`（会破坏状态一致性）；
- 直接改客户端关键字段冒充切换（CC Switch 的「直连指针」不会同步，下次切换会覆盖）；
- 通过 UI Automation 点击界面：Tauri WebView 的按钮能被读取，但滚动、拖拽、下拉、弹窗时序不稳定，容易误点**删除/切换**等有副作用的操作。若确需自动化，应逐步操作并在每步后截图确认，且避开删除类按钮。

**推荐协作方式**：让助手读配置、定位问题、生成方案；界面上的切换/授权/删除由你本人点击，助手用截图核对结果。
