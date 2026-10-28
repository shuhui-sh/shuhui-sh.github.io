---
title: "CC Switch 4.x 全功能图解教程"
date: 2026-10-23
description: "1. 界面总览 2. 三种连接模式 3. 供应商管理 4. 本地路由、故障转移与聚合 5. MCP 服务器 6. 提示词（Prompts） 7. Skills 8. 会话管理器 9. 授权中心 10."
tags: ['工具', 'Claude Code']
category: "技术"
---
> **实拍版本**：CC Switch 4.0.18（Windows 11）
> **配图**：39 张，均为本机实际操作截图，按步骤采集
> **隐私处理**：截图中的 Windows 用户名、本地项目路径、会话名称已做局部模糊
> **配套文字版**：[CC-Switch-4.x-全功能使用教程.md](./CC-Switch-4.x-全功能使用教程.md)（更详细的参数与原理说明）
>
> 说明：截图来自一台已经配置过 Claude Code 的机器（存在 `default`、`DeepSeek` 等供应商，路由服务处于停止状态）。你的界面内容可能不同，但控件位置与操作路径一致。

---

## 目录

1. 界面总览
2. 三种连接模式
3. 供应商管理
4. 本地路由、故障转移与聚合
5. MCP 服务器
6. 提示词（Prompts）
7. Skills
8. 会话管理器
9. 授权中心
10. 用量与成本
11. 应用管理
12. 设置六组
13. OpenClaw 工作区
14. 高级功能
15. 故障排查与最佳实践
附录 A 路径速查
附录 B 功能支持矩阵

---

## 1. 界面总览

![Claude Code 主界面](/images/CC-Switch-4-x-全功能图解教程/19-claude-direct.png)
*图 1：主界面。左侧栏 = 应用列表 + 全局功能页 + 底部「应用 / 设置」；右侧 = 当前应用的供应商页。顶部三个标签是「直连 / 路由 / 聚合」。*

界面分三块：

| 区域 | 内容 |
|------|------|
| 应用列表 | Claude Code、Claude Desktop、Codex、Gemini CLI、Grok Build、OpenCode、OpenClaw、Hermes、Pi、MiniMax Code |
| 全局页 | MCP、Skills、提示词、会话、授权中心、用量统计 |
| 底部 | 「应用」（安装/升级 CLI、选择侧栏显示）与「设置」 |

快捷键：`Ctrl + ,` 设置；`Ctrl + F` 搜索供应商；`Esc` 关闭搜索/返回。

---

## 2. 三种连接模式

应用页顶部有三个标签。**点标签只是切换查看，不会改配置**；真正切换要点下方写明后果的按钮。

| | 直连 | 路由 | 聚合 |
|---|---|---|---|
| 请求路径 | 客户端 → 供应商 | 客户端 → 本机 `127.0.0.1:15721` → 供应商 | 客户端 → 本机路由 → 按模型分流 |
| 协议转换 | ❌ | ✅ | ✅ |
| 故障转移 | ❌ | ✅ | ❌ |
| 热切换 | 需重启客户端 | 配置不变时立即生效 | 在 `/model` 选模型 |
| 支持应用 | 全部 | Claude Code / Codex / Gemini / Grok | 仅 Claude Code / Codex |

### 2.1 直连（默认）

![直连状态栏](/images/CC-Switch-4-x-全功能图解教程/19b-direct-header.png)
*图 2：直连生效时，顶部标签显示「直连 · 生效中」，供应商卡片右侧出现「切换」或播放按钮；左上角同时显示当前供应商（default）。*

### 2.2 路由

![路由标签](/images/CC-Switch-4-x-全功能图解教程/20-claude-routing-tab.png)
*图 3：切到「路由」标签后的视图。注意底部提示「你在查看『路由』，Claude Code 目前是直连」，此时还没生效。*

点右上角 **「开始路由」** 会弹出确认框：

![开始路由确认](/images/CC-Switch-4-x-全功能图解教程/20b-route-confirm.png)
*图 4：确认框会明确列出后果：改写 `~/.claude/settings.json` 里的地址和密钥、真实密钥留在 CC Switch、之后换供应商不再改配置文件、CC Switch 需保持运行。*

### 2.3 聚合

![聚合标签](/images/CC-Switch-4-x-全功能图解教程/21-claude-aggregation-tab.png)
*图 5：聚合视图。这里可以选默认供应商，并把其他供应商「添加」进聚合名单。*

![切换到聚合模式确认](/images/CC-Switch-4-x-全功能图解教程/21b-aggregation-confirm.png)
*图 6：聚合确认框。会显示默认供应商，以及切换后 `/model` 里会出现的模型数量。*

> ⚠️ 官方订阅不经过路由（Codex 的 OpenAI Official 例外）；Claude 官方订阅也不支持聚合。

---

## 3. 供应商管理

### 3.1 添加供应商

入口：页头右侧 **「＋ 添加供应商」**。

![选择预设](/images/CC-Switch-4-x-全功能图解教程/22-add-provider-presets.png)
*图 7：第一步选预设。左侧是分类（账号登录 / 模型厂商 / 第三方平台 / 云服务商 / 本地 / 跨应用），顶部可搜索名称或网址，右上角「自定义配置」固定在第一位。*

![自定义配置表单](/images/CC-Switch-4-x-全功能图解教程/23-add-provider-custom.png)
*图 8：第二步填写。Claude Code 的自定义表单包含：名称、备注、官网、上游格式、API Key、认证字段、请求地址、模型列表、高级选项。*

关键字段怎么填：

| 字段 | 说明 |
|------|------|
| 上游格式 | Anthropic Messages（原生）/ OpenAI Chat Completions / OpenAI Responses / Gemini Native。选错必报 404/405 |
| 认证字段 | 默认 `ANTHROPIC_AUTH_TOKEN`（Bearer）。只有网关明确要求 `x-api-key` 时才换 |
| 请求地址 | 根地址，不带结尾 `/`；网关路径特殊时打开「完整 URL」 |
| API Key | 真实 Key 只存 CC Switch，不进客户端配置 |
| 模型映射 | Claude：Sonnet/Opus/Haiku → 上游真实模型，**默认兜底必填**；Codex：菜单名 / 实际模型 / 上下文窗口 / 思考等级 |
| 1M | 仅当上游真支持 ≥100 万 token 时勾选 |

> 带「需要路由」徽章的预设（如仅提供 Chat 端点的供应商），必须开启本地路由才能使用。

### 3.2 编辑供应商

点卡片右侧铅笔图标：

![编辑供应商](/images/CC-Switch-4-x-全功能图解教程/24-edit-provider.png)
*图 9：编辑「default」。API Key 默认掩码显示；展开「高级选项」可改上游格式、完整 URL、认证字段和模型映射。*

编辑框的两类内容：

| 类型 | 包含 | 保存位置 |
|------|------|----------|
| 随供应商切换 | 地址、Key、模型名、协议、上下文窗口等 | 该供应商记录 |
| 全局设置 | 插件、Hook、权限、MCP、你加的环境变量、注释 | 工具配置文件，所有供应商共享 |

注意：在客户端里临时 `/model` 换的模型**不会**存回供应商；想长期修改要在编辑页改。

### 3.3 切换与生效

- 主界面：点卡片「切换」（直连）或「路由到此」（路由）。
- 托盘：右键托盘图标 → 应用子菜单 → 点供应商名。

| 应用 | 切换后 |
|------|--------|
| Claude Code | 即时生效（支持热重载） |
| Claude Desktop | 完全退出并重启 |
| Codex | 重启 Codex（CLI 重开终端；桌面版彻底退出） |
| Gemini CLI / Grok Build | 重启 |
| OpenCode / OpenClaw | 重开终端 |
| Hermes | 点卡片「启用」后生效 |
| Pi / MiniMax Code | 在工具里选模型 |

### 3.4 排序、复制、删除

- 排序：悬停卡片左侧出现 `⋮⋮` 拖拽手柄；顺序同时影响托盘与故障转移队列。
- 复制：卡片 `⋯` →「复制」，生成带 `copy` 后缀的副本。
- 删除：`⋯` →「删除」；**使用中的供应商不能删**，需先切到别家。

### 3.5 其他应用页

其他应用的管理页结构相同，只是当前环境尚未添加供应商，所以显示空状态：

<img src="images/25-codex.png" width="49%"> <img src="images/26-gemini.png" width="49%">
*图 10：Codex（左）与 Gemini CLI（右）的空状态。点「添加供应商」即可开始配置。*

<img src="images/27-grok.png" width="49%"> <img src="images/28-claude-desktop.png" width="49%">
*图 11：Grok Build（左）与 Claude Desktop（右）。Claude Desktop 顶部是「直连 / 路由 / 聚合」，且自带 Claude Desktop Official 官方项。*

<img src="images/29-opencode.png" width="49%"> <img src="images/30-openclaw.png" width="49%">
*图 12：OpenCode（左）与 OpenClaw（右）。OpenClaw 页头下方额外有「供应商 / 工作区 / 配置」三个页签。*

<img src="images/32-hermes.png" width="49%"> <img src="images/33-pi.png" width="49%">
*图 13：Hermes（左）与 Pi（右）。*

<img src="images/34-minimax.png" width="49%"> <img src="images/31-openclaw-workspace.png" width="49%">
*图 14：MiniMax Code（左）与 OpenClaw 工作区（右，详见第 13 节）。*

### 3.6 Claude Desktop 的两种模式

| 模式 | 适用 | 要求 |
|------|------|------|
| 直连 | 原生 Anthropic Messages，且模型名是 `claude-sonnet-*` / `claude-opus-*` / `claude-haiku-*` | 无需保持 CC Switch 运行 |
| 模型映射 | DeepSeek / Kimi / GPT / Gemini 等非 Claude 模型，或需要协议转换 | 必须保持 CC Switch 运行，路由自动启动 |

模型映射示例：

| 模型角色 | 菜单显示名 | 实际请求模型 |
|----------|-----------|--------------|
| Sonnet | DeepSeek V4 Pro | `deepseek-v4-pro` |
| Haiku | DeepSeek Flash | `deepseek-chat` |

### 3.7 共存式应用

OpenCode、OpenClaw、Hermes、Pi、MiniMax Code 可以同时写入多个供应商，在工具里选择使用哪一个。卡片按钮是「添加 / 移除」（Pi 为「启用 / 移除」），没有直连/路由/聚合标签，也不支持托盘切换与故障转移队列。

---

## 4. 本地路由、故障转移与聚合

### 4.1 服务设置

进入「设置 → 本地路由」：

![本地路由设置](/images/CC-Switch-4-x-全功能图解教程/03-settings-routing.png)
*图 15：服务区域。默认监听 `127.0.0.1:15721`；可改端口（1024–65535）、设置连接地址、开关「记录请求用量」。有应用在用路由时「停止」会变灰。*

- 不需要手动启动：应用点「开始路由」时服务自动启动。
- WSL2 里访问 Windows 的 `127.0.0.1` 时：监听地址改 `0.0.0.0`，连接地址填 WSL 能访问的 Windows IP，并放行防火墙。

### 4.2 进入路由后配置变成什么

| 应用 | 配置文件 | 路由后 |
|------|----------|--------|
| Claude Code | `~/.claude/settings.json` | `ANTHROPIC_BASE_URL=http://127.0.0.1:15721`，Key=`PROXY_MANAGED` |
| Codex | `~/.codex/config.toml` | `base_url=http://127.0.0.1:15721/v1` |
| Gemini | `~/.gemini/.env` | `GOOGLE_GEMINI_BASE_URL=http://127.0.0.1:15721` |
| Grok Build | `~/.grok/config.toml` | `http://127.0.0.1:15721/grokbuild/v1` |

格式转换矩阵（Claude 侧）：

| 上游格式 | 行为 |
|----------|------|
| Anthropic Messages | 透传 |
| OpenAI Chat Completions | 请求/响应互转 |
| OpenAI Responses | 请求/响应互转 |
| Gemini Native | 请求/响应互转 |

### 4.3 故障转移

前提：应用在路由模式 + 故障转移开关开启 + 队列有备用。

在「设置 → 本地路由 → 自动故障转移」调参数：

![自动故障转移与整流器](/images/CC-Switch-4-x-全功能图解教程/03b-settings-routing-lower.png)
*图 16：熔断器参数（恢复成功阈值、恢复等待、错误率阈值、最小请求数）以及整流器开关。*

| 参数 | 通用默认 | Claude 默认 | 范围 |
|------|----------|-------------|------|
| 失败阈值 | 4 | 8 | 1–20 |
| 恢复成功阈值 | 2 | 3 | 1–10 |
| 恢复等待（秒） | 60 | 90 | 0–300 |
| 错误率阈值 | 60% | 70% | 0–100% |
| 最小请求数 | 10 | 15 | 5–100 |
| 最大重试 | 3 | 6 | 0–10 |

队列在各应用页的「路由」标签里管理：加入队列、上移/下移、移出；健康状态 🟢 正常 / 🟡 降级 / 🔴 熔断。

### 4.4 聚合模式

- 仅 Claude Code / Codex；不做故障转移。
- 非默认供应商的模型在 `/model` 里带 `ccs-` 前缀；不带前缀走默认。
- Claude Code 改动立即生效；Codex 必须重启（CLI 需「重启 Codex 守护进程」，会中断任务）。
- 官方订阅限制见第 2.3 节。

### 4.5 整流器

自动修复上游不兼容请求：Thinking 签名不兼容时移除相关字段重试、Thinking Budget 修正、不支持图片时降级为 `[Unsupported Image]` 等。开关见图 16。

---

## 5. MCP 服务器

入口：侧栏 **MCP**。

![MCP 列表](/images/CC-Switch-4-x-全功能图解教程/07-mcp.png)
*图 17：矩阵表。每行一个 MCP，每列一个应用，格子开关控制该应用是否启用。*

![添加 MCP](/images/CC-Switch-4-x-全功能图解教程/08-mcp-add.png)
*图 18：添加页。可从模板开始（fetch / time / memory / 思维链 / context7）、粘贴 JSON/TOML，或手填命令与参数；底部「写入到」勾选要同步的应用。*

支持 8 个应用：Claude Code、Codex、Gemini CLI、Grok Build、OpenCode、Hermes、Pi、MiniMax Code（Claude Desktop、OpenClaw 不支持）。

三种传输：`stdio`（本地命令）、`http`、`sse`。

**导入现有配置**：页头「从应用导入」，读取各工具的用户级配置；项目级 MCP 不会导入。

---

## 6. 提示词（Prompts）

入口：侧栏 **提示词**。

![提示词列表](/images/CC-Switch-4-x-全功能图解教程/11-prompts.png)
*图 19：当前应用（Claude Code）的提示词列表。顶部显示目标文件 `~/.claude/CLAUDE.md` 和大小；启用中的条目带「已启用」。*

![添加提示词](/images/CC-Switch-4-x-全功能图解教程/12-prompts-add.png)
*图 20：添加页。名称、说明、Markdown 正文；保存后可在列表里启用。*

规则：

- 同一应用同时只启用一条；启用会覆盖目标文件，停用会清空。
- 目标文件：Claude Code `CLAUDE.md`、Codex `AGENTS.md`、Gemini `GEMINI.md`、Grok `AGENTS.md`、Hermes `SOUL.md`、Pi `AGENTS.md`、MiniMax `AGENTS.md`（≤32KiB）。
- 在外部手动改文件不会丢：下次打开页面会把改动收进启用中的那条。

---

## 7. Skills

入口：侧栏 **Skills**。

![已安装](/images/CC-Switch-4-x-全功能图解教程/09-skills-installed.png)
*图 21：「已安装」视图。当前为 0 个，页面提供「去发现」和「导入本机已有」。*

![发现](/images/CC-Switch-4-x-全功能图解教程/10-skills-discover.png)
*图 22：「发现」视图。可选仓库来源或 skills.sh，先在「安装到」里选应用，再点某一行的「安装」。*

- 更新检测基于 SHA-256；支持单项与全部更新。
- 卸载会备份到 `~/.cc-switch/skill-backups/`，可恢复。
- 「存储与同步」可把主副本放到 `~/.cc-switch/skills/` 或 `~/.agents/skills`，同步方式选自动（软链接优先）/ 仅软链接 / 仅复制。

---

## 8. 会话管理器

入口：侧栏 **会话**。

![会话列表](/images/CC-Switch-4-x-全功能图解教程/13-sessions.png)
*图 23：会话列表（内容已模糊处理）。可按应用、时间/项目分组，搜索标题、目录、首末消息或会话 ID。*

- 点会话可查看分轮对话、执行过程、文件改动，并复制/导出 Markdown。
- 「恢复」会打开终端并续接；macOS 直接拉起偏好终端，其他平台复制命令到剪贴板。
- 删除是永久删除（不进回收站）；支持多选批量删除。
- OpenClaw 会话由网关管理、Hermes 暂不支持命令行恢复。

---

## 9. 授权中心

入口：侧栏 **授权中心**（Beta）。

![授权中心](/images/CC-Switch-4-x-全功能图解教程/14-auth-center.png)
*图 24：集中管理 GitHub Copilot、ChatGPT（Codex OAuth）、xAI（Grok OAuth）账号，支持多账号与默认账号。*

> ⚠️ 这些是逆向接入的 OAuth 流程，可能违反上游服务条款并导致账号受限，使用前自行评估。

---

## 10. 用量与成本

入口：侧栏 **用量统计**。

![用量概览](/images/CC-Switch-4-x-全功能图解教程/15-usage.png)
*图 25：概览。总成本、总请求数、真实消耗 Tokens、缓存命中率；下方是趋势图与请求日志。*

![请求日志](/images/CC-Switch-4-x-全功能图解教程/16-usage-logs.png)
*图 26：请求日志。时间、应用、供应商、模型、新增输入、输出、缓存命中、成本、速度；可按状态码筛选。*

![计费设置](/images/CC-Switch-4-x-全功能图解教程/17-usage-pricing.png)
*图 27：「设置」标签（即定价配置）。可设输入/输出/缓存读取/缓存创建价格，支持从 models.dev 导入。*

要点：

- 不开路由也能统计：默认扫描各工具的本地会话日志（启动一次 + 后台每 10 分钟）。
- 路由请求日志更精确，可看到「请求模型 → 实际模型」和错误详情。
- 金额是估算，token 计数更接近真实；以供应商账单为准。

---

## 11. 应用管理

入口：侧栏底部 **应用**。

![应用管理](/images/CC-Switch-4-x-全功能图解教程/18-apps.png)
*图 28：查看各 CLI 的当前/最新版本，安装或升级；右侧开关决定是否在侧栏显示。*

- 「全部升级」一键升级所有检测到新版本的工具。
- Claude Desktop 是桌面应用，这里只显示是否接入。
- 配置目录指向 WSL 时，会在对应发行版里检测和升级。

---

## 12. 设置六组

快捷键 `Ctrl + ,`。设置左侧是六个分组。

### 12.1 通用

![设置通用](/images/CC-Switch-4-x-全功能图解教程/01-settings-general.png)
*图 29：语言、明暗、侧栏显示、项目切换、新版本检查、开机自启、关闭行为、首选终端。*

### 12.2 应用配置

![设置应用配置](/images/CC-Switch-4-x-全功能图解教程/02-settings-app-config.png)
*图 30：Claude Code 插件同步、跳过初次安装确认；Codex 的官方登录保留、会话历史统一、历史压缩；各应用配置目录。*

### 12.3 本地路由

![设置本地路由](/images/CC-Switch-4-x-全功能图解教程/03-settings-routing.png)
*图 31：服务启停、监听地址与端口、连接地址、记录请求用量；「正在使用路由的应用」列表。*

### 12.4 网络

![设置网络](/images/CC-Switch-4-x-全功能图解教程/04-settings-network.png)
*图 32：全局出站代理。需要通过代理访问外部 API 时填写。*

### 12.5 数据

![设置数据](/images/CC-Switch-4-x-全功能图解教程/05-settings-data.png)
*图 33：存储位置、SQL 导入导出、备份与恢复、云同步。*

![备份与云同步](/images/CC-Switch-4-x-全功能图解教程/05b-settings-data-backup.png)
*图 34：自动备份间隔/保留数量、立即备份与恢复；下方是 WebDAV / S3 云同步。*

### 12.6 关于

![关于](/images/CC-Switch-4-x-全功能图解教程/06-settings-about.png)
*图 35：版本、检查更新、官网/更新日志/近期更新。*

---

## 13. OpenClaw 工作区

入口：侧栏 OpenClaw → 页签「工作区」。

![OpenClaw 工作区](/images/CC-Switch-4-x-全功能图解教程/31-openclaw-workspace.png)
*图 36：管理 `AGENTS.md`、`SOUL.md`、`USER.md`、`IDENTITY.md`、`TOOLS.md`、`MEMORY.md`、`HEARTBEAT.md`、`BOOTSTRAP.md`、`BOOT.md`；右下角进入「每日记忆文件」。*

- 文件存在显示绿勾，不存在则在首次保存时创建。
- 每日记忆存放在 `~/.openclaw/workspace/memory/YYYY-MM-DD.md`，支持搜索、编辑、删除。

---

## 14. 高级功能

### 14.1 深度链接 `ccswitch://`

用于一键导入供应商 / MCP / 提示词 / Skill 仓库，在线生成器：<https://ccswitch.io/deplink.html>

```
ccswitch://v1/import?resource=provider&app=claude&name=My%20Provider&endpoint=https%3A%2F%2Fapi.example.com&apiKey=sk-xxx
```

导入前会显示确认框与风险提示；链接里可能含 Key，不要公开分享。

### 14.2 环境变量冲突

CC Switch 会检测 `ANTHROPIC*`、`OPENAI*`、`GEMINI*`、`XAI_API_KEY` 等环境变量。顶部出现黄色横幅时，点「查看详情」→ 勾选 →「删除选中」；删除前自动备份到 `~/.cc-switch/backups/env-backup-*.json`。

### 14.3 配置目录覆盖

设置 → 应用配置，可把 Claude Code / Codex / Gemini / Grok / OpenCode / OpenClaw / Hermes / Pi 的目录指向别处（例如 WSL 路径）。改完需重启 CC Switch，且 CLI 要使用同一目录。

### 14.4 手动编辑规则

| 位置 | 能否手改 |
|------|----------|
| 工具配置里的全局设置（插件、hooks、MCP…） | ✅ 可以，切换不会动 |
| 工具配置里的关键字段（地址、Key、模型） | ⚠️ 只生效到下次切换 |
| `~/.cc-switch/settings.json` | ✅ |
| `cc-switch.db`、`live-state.json`、登录暂存文件 | ❌ 不建议 |

配置文件语法错误时，CC Switch 会拒绝写入，避免覆盖你的内容；首次改写的原文件备份在 `~/.cc-switch/backups/live-first-write/`。

---

## 15. 故障排查与最佳实践

### 15.1 排查顺序

1. 设置 → 本地路由：服务是否运行、15721 是否被占用；
2. 应用页：当前模式与「使用中 / 路由中」状态；
3. 客户端是否按第 3.3 节重启；
4. 用量统计 → 请求日志里的状态码与错误；
5. `~/.cc-switch/logs/cc-switch.log`。

### 15.2 常见问题

| 现象 | 处理 |
|------|------|
| 切换后不生效 | Claude Code 重开终端；其他 CLI 重启 |
| 路由后全部失败 | 检查服务、端口、是否重开会话 |
| 401/403 | 认证字段用 `ANTHROPIC_AUTH_TOKEN`；核对 Key |
| 404/405 | 上游格式选错、模型名错、路径需开「完整 URL」 |
| 请求超时 | 调路由超时；检查网络与全局代理 |
| `/model` 看不到聚合模型 | Codex 重启守护进程/桌面版；插件重开窗口 |
| 官方供应商在路由页变灰 | 官方订阅不经路由，先回直连 |
| 全部供应商熔断 | 等待恢复，或全部回直连→停服务→重新路由 |
| 额度不显示 | 配置用量查询、切到使用中、重新登录授权 |
| 环境变量冲突提示 | 查看详情并删除，或手动清理 |

### 15.3 最佳实践

1. 大改前先「立即备份」；
2. 路由只监听 `127.0.0.1`；改 `0.0.0.0` 前评估局域网风险；
3. API Key 只放 CC Switch，不要同时放系统环境变量；
4. 模型映射的默认兜底必填；1M 勾选要匹配上游真实窗口；
5. 故障转移队列 P1 放最稳的，参数别调太激进；
6. 用量金额是估算，以账单为准；
7. 不手改 `cc-switch.db` 与 `live-state.json`。

---

## 附录 A：路径速查（Windows）

| 内容 | 路径 |
|------|------|
| CC Switch 数据 | `C:\Users\<用户>\.cc-switch\` |
| 数据库 | `~/.cc-switch/cc-switch.db` |
| 设备设置 | `~/.cc-switch/settings.json` |
| 当前模式 | `~/.cc-switch/live-state.json` |
| 首次改写备份 | `~/.cc-switch/backups/live-first-write/` |
| Claude Code | `~/.claude/settings.json`、`~/.claude.json`（MCP） |
| Codex | `~/.codex/config.toml`、`auth.json` |
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

---

## 附录 C：截图清单

| 文件 | 内容 |
|------|------|
| 01-settings-general.png | 设置 → 通用 |
| 02-settings-app-config.png | 设置 → 应用配置（路径已模糊） |
| 03-settings-routing.png | 设置 → 本地路由服务 |
| 03b-settings-routing-lower.png | 熔断参数与整流器 |
| 04-settings-network.png | 设置 → 网络 |
| 05-settings-data.png | 设置 → 数据（路径已模糊） |
| 05b-settings-data-backup.png | 备份与云同步 |
| 06-settings-about.png | 设置 → 关于 |
| 07-mcp.png / 08-mcp-add.png | MCP 列表 / 添加 |
| 09-skills-installed.png / 10-skills-discover.png | Skills 已安装 / 发现 |
| 11-prompts.png / 12-prompts-add.png | 提示词列表 / 添加 |
| 13-sessions.png | 会话列表（已模糊） |
| 14-auth-center.png | 授权中心 |
| 15/16/17-usage*.png | 用量概览 / 请求日志 / 计费设置 |
| 18-apps.png | 应用管理（路径已模糊） |
| 19-claude-direct.png | Claude Code 直连 |
| 19b-direct-header.png | 直连状态栏局部 |
| 20/20b-claude-routing*.png | 路由视图 / 开始路由确认 |
| 21/21b-claude-aggregation*.png | 聚合视图 / 切换确认 |
| 22/23-add-provider*.png | 添加供应商：预设 / 自定义 |
| 24-edit-provider.png | 编辑供应商 |
| 25-34 | Codex、Gemini、Grok、Claude Desktop、OpenCode、OpenClaw、Hermes、Pi、MiniMax |
| 31-openclaw-workspace.png | OpenClaw 工作区 |

> 所有截图均来自 CC Switch 4.0.18 的实际界面；因版本迭代，按钮文案可能略有差异。
