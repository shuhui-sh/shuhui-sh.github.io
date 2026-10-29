---
title: "深入使用 Claude Code"
date: 2026-04-02
description: "大多数人第一次用 Claude Code，只是在终端里问问题、让它修个 Bug。 这只用到了它的一小部分能力。"
tags: ['Claude Code']
draft: true
category: "技术"
---
### 从 MCP 到多代理协作的完整指南

---

## 引言

大多数人第一次用 Claude Code，只是在终端里问问题、让它修个 Bug。

这只用到了它的一小部分能力。

Claude Code 本质上是一个 **AI 代理编排框架**——可以连接外部工具（数据库、GitHub、浏览器）、把复杂任务分拆给多个专门的 AI 代理并行处理、用可复用的工作流自动化重复操作，并支持团队级的权限管理。

本文介绍六个核心能力：

- **MCP** — 连接外部工具（数据库、GitHub、浏览器……）
- **斜杠命令（Slash Commands）** — 一键触发自定义工作流
- **子代理（Subagents）** — 多个 AI 并行处理任务，防止上下文爆炸
- **Hooks** — 绑定到 Claude Code 生命周期的自动化操作
- **插件（Plugins）** — 把以上所有配置打包成可分发的工具集
- **权限管理** — 控制 Claude 能做什么、不能做什么

---

## 第一章：基础配置

> 如果你还没有安装 Claude Code，请先阅读上一篇文章《Claude Code 入门：从零安装到第一次对话》完成安装和登录，再回来继续。

### 两个核心配置文件

#### CLAUDE.md — 项目记忆文件

在项目根目录创建 `CLAUDE.md`，Claude 每次启动时会自动读取，把内容作为背景知识。

可以通过在项目目录启动claude code后，输入`/init`命令，让agent自动读取项目自动生成项目的`CLAUDE.md`

```markdown
# 我的项目

## 技术栈
- 后端：Node.js + Express
- 数据库：PostgreSQL
- 测试框架：Jest

## 开发规范
- 所有函数必须有 JSDoc 注释
- 提交前必须通过 npm run test
- 不要直接修改 production.config.js
```

`~/.claude/CLAUDE.md` 是全局配置（自己没有配置也是不会自动生成的），对所有项目生效。项目目录里的 `CLAUDE.md` 优先级更高，会覆盖全局配置中的同名项。

#### settings.json — 权限配置文件

控制 Claude Code 能做什么、不能做什么。位置在 `.claude/settings.json`（项目级）或 `~/.claude/settings.json`（全局）。

```json
{
  "permissions": {
    "allow": [
      "Bash(npm run lint)",
      "Bash(npm run test *)"
    ],
    "deny": [
      "Bash(curl *)",
      "Read(./.env)"
    ]
  }
}
```

第三章会详细讲解权限配置。

---

## 第二章：MCP——连接外部工具

### 2.1 MCP 是什么？

MCP（Model Context Protocol，模型上下文协议）是 Anthropic 推出的开放标准，相当于 AI 工具的标准接口协议。

没有 MCP 时，Claude Code 只能读写本地文件、执行终端命令。有了 MCP，Claude Code 可以直接查询数据库、操作 GitHub、控制浏览器、调用各类 API。目前已有超过 300 个 MCP 服务器可用。

### 2.2 三种安装作用域

安装 MCP 时，**必须用 `--scope` 明确指定安装位置**，否则很容易装错。

| 参数                | 存储位置                    | 生效范围          | 适用场景                   |
| ----------------- | ----------------------- | ------------- | ---------------------- |
| `--scope user`    | `~/.claude.json` 全局区块   | 所有项目          | 个人私密工具（私人 Token、私人数据库） |
| `--scope project` | 项目根目录的 `.mcp.json`      | 仅当前项目，可提交 Git | 团队共用工具                 |
| 不加参数（默认）          | `~/.claude.json` 当前项目区块 | 仅当前项目         | 几乎不应该用这个               |

不加 `--scope` 时，无论在哪个目录执行，配置只对当前目录生效，不会全局可用。**想全局，必须显式加 `--scope user`。**

### 2.3 用户级安装

用 `--scope user` 安装，配置写入 `~/.claude.json` 全局区块，所有项目都能用。

**基础语法：**

```bash
claude mcp add <名称> <启动地址或命令> [选项] --scope user
```

**常用选项：**

| 选项                | 作用                              |
| ----------------- | ------------------------------- |
| `-t http`         | 协议为 HTTP（适用于 URL 含 `/mcp` 的接口）  |
| `-t sse`          | 协议为 SSE（适用于 URL 含 `/sse` 的流式接口） |
| `-H "Key: Value"` | 添加请求头，常用于传 Authorization Token  |
| `--env KEY=VALUE` | 注入环境变量，适合传数据库密码等敏感信息            |

URL 含 `/sse` 结尾必须用 `-t sse`，用 `-t http` 会连接失败（显示 `✗ Failed to connect`）。

**例子 1：接入 HTTP 类型（URL 含 `/mcp`）**

```bash
claude mcp add WebSearch https://example.com/api/mcps/WebSearch/mcp \
  -t http \
  -H "Authorization: Bearer 你的Token" \
  --scope user
```

**例子 2：接入 SSE 类型（URL 含 `/sse`）**

```bash
claude mcp add WebParser https://example.com/api/mcps/WebParser/sse \
  -t sse \
  -H "Authorization: Bearer 你的Token" \
  --scope user
```

**查看连接状态：**

```bash
claude mcp list
# WebSearch:  https://...  (HTTP) - ✓ Connected
# WebParser:  https://...  (HTTP) - ✗ Failed to connect
```

**删除：**

```bash
claude mcp remove <名称> --scope user
```

### 2.4 项目级安装

项目级 MCP 配置写入 `.mcp.json`，提交 Git 后团队所有人自动获得。

**命令行安装（自动写入 `.mcp.json`）：**

```bash
claude mcp add playwright npx @playwright/mcp@latest --scope project
```

**直接编辑 `.mcp.json`（适合批量配置）：**

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    },
    "postgres": {
      "command": "npx",
      "args": ["@anthropic/postgres-mcp-server"],
      "env": {
        "DATABASE_URL": "${DATABASE_URL}"
      }
    }
  }
}
```

数据库密码用 `${DATABASE_URL}` 引用环境变量，不要写死在文件里。每个开发者在本机设置该环境变量（写入 `~/.zshrc` 或 `.env.local`）。

```bash
git add .mcp.json
git commit -m "chore: add team MCP server configuration"
```

**删除：**

```bash
claude mcp remove <名称> --scope project
```

### 2.5 作用域分配参考

```
团队项目：Node.js Web 应用

✅ 装用户级（--scope user）：
   - WebSearch     个人搜索工具，带自己的 API Key
   - WebParser     带个人 Token 的网页解析工具
   - postgres-prod 只有你有权限的生产数据库账号
   - jira          你个人的 Jira API Token

✅ 装项目级（--scope project）：
   - playwright    每个人都要跑 E2E 测试
   - github        团队共用 GitHub 组织
   - postgres-dev  团队共用测试数据库（密码用环境变量引用）
```

### 2.6 推荐必装清单

#### 实时联网搜索

Claude 的训练数据有截止日期，虽然Claude code有内置自己的WebSearch工具，但是它内置的工具需要经过他们的服务器，这就对设备上的网络有要求。所以这个时候使用一些第三方的搜索MCP或搜索技能进行兜底就很有必要了。Agent没有实时联网搜索的功能，其能力只有50%，所有的知识都依靠它之前的训练学习，然后预测性的输出token，没有办法通过外部搜索验证。这就是为何我要把搜索工具放在第一位这么重要。

**Brave Search**

**获取 API Key：** 注册 https://brave.com/search/api/，免费额度每月 2000 次。因为OpenClaw的爆火，从2月份开始已经没有免费plan了，所以以下只针对之前已注册有Free plan的用户。

**安装（macOS / Linux）：**

```bash
claude mcp add brave-search -s user \
  --env "BRAVE_API_KEY=你的Key" \
  -- npx -y @modelcontextprotocol/server-brave-search
```

**安装（Windows PowerShell）：**

```powershell
claude mcp add brave-search -s user --env "BRAVE_API_KEY=你的Key" '--' npx -y @modelcontextprotocol/server-brave-search
```

Windows 上 `--` 必须用单引号包住，否则 PowerShell 报错。

**验证：**

```bash
claude mcp list
# brave-search: npx -y @modelcontextprotocol/server-brave-search - ✓ Connected
```

**Tavily（推荐）**

免费层每月 1000 次查询，专门为 AI agent 设计，有官方 MCP 支持。 [Shipyard](https://shipyard.build/blog/claude-code-cheat-sheet/)安装方式和 Brave Search 几乎一样：

bash

```bash
# macOS / Linux
claude mcp add tavily-search -s user \
  --env "TAVILY_API_KEY=你的Key" \
  -- npx -y tavily-mcp@latest

# Windows PowerShell
claude mcp add tavily-search -s user --env "TAVILY_API_KEY=你的Key" '--' npx -y tavily-mcp@latest
```

Key 在 [https://app.tavily.com](https://app.tavily.com) 注册后直接获得，不需要绑信用卡。

**Serper**

每月 2500 次免费查询 [Medium](https://medium.com/@ooi_yee_fei/how-claude-code-agents-and-mcps-work-better-together-5c8d515fcbbd)，走 Google 索引，结果质量和 Google 一致，适合需要 Google 搜索结果的场景。


这些都是海外厂商的搜索，当然国内厂商也有，如果在上一篇文章有开通阿里云的code plan的话，他们也会有免费的搜索MCP，但是那个搜索引擎都是国产的，搜出来的文章内容几乎都是优先国产文章，质量比较差，所以我试过之后就删了，搜出来的东西对我没什么用。


**网络问题（中国大陆）**

`npx` 启动的 stdio 类型 MCP 走独立子进程，Node.js 原生 `fetch` 不读 `HTTP_PROXY` 环境变量，系统代理对它无效。HTTP/SSE 类型（URL 形式）则由 Claude Code 主进程发请求，系统代理通常有效。

| 子进程语言     | 代理行为                            |
| --------- | ------------------------------- |
| Node.js   | 原生 fetch 不读 `HTTP_PROXY`，系统代理无效 |
| Python    | 读 `HTTP_PROXY`，系统代理通常有效         |
| Go / Rust | 多数读系统代理环境变量                     |

解决方案：开启 Clash 的 TUN 模式，在网络层接管所有进程流量：

- **Clash for Windows**：`General` 标签 → 打开 `TUN Mode`
- **Clash Verge / Clash Verge Rev**：`设置` → 打开 `TUN 模式`

开启后所有 npx 类 MCP 的网络问题同时解决。

#### GitHub MCP——搜索仓库、查看源码、管理 Issue

装上后 Claude 可以直接搜索任意公开仓库源码、查看 PR、管理 Issue，不需要手动复制粘贴。

**获取 Personal Access Token（PAT）：**

1. 打开 https://github.com/settings/tokens
2. 点 `Generate new token (classic)`
3. 勾选：`repo`、`read:org`、`read:user`
4. 生成并复制 Token（`ghp_` 开头）

**安装（macOS / Linux）：**

```bash
claude mcp add github \
  --transport http https://api.githubcopilot.com/mcp \
  -H "Authorization: Bearer 你的PAT" \
  --scope user
```

**安装（Windows PowerShell）：**

```powershell
$pat = "你的PAT"
claude mcp add github --transport http https://api.githubcopilot.com/mcp/ -H "Authorization: Bearer $pat" --scope user
```

GitHub MCP 是 HTTP 类型，不受 Node.js 代理问题影响，系统代理开启即可，不需要 TUN 模式。

**gh CLI vs GitHub MCP：token 消耗对比**

同样是"列出最近 10 个 PR"：

- `gh pr list --limit 10` → 约 200 token（格式化文本）
- GitHub MCP `list_pull_requests` → 约 2000~5000 token（完整 JSON，含大量无用字段）

|                   | gh CLI     | GitHub MCP |
| ----------------- | ---------- | ---------- |
| Token 消耗          | 少          | 多          |
| 管理自己的仓库（PR、Issue） | ✅ 够用       | ✅          |
| 搜索其他公开仓库源码        | ❌ 需先 clone | ✅ 直接查      |

两个都装，按场景分工：管理自己项目用 `gh` CLI，查其他仓库源码用 GitHub MCP。

**安装 gh CLI：**

```bash
# macOS
brew install gh && gh auth login

# Windows
winget install GitHub.cli
gh auth login
```

把 `Bash(gh *)` 加进 `settings.json` 的 allow 列表，调用时不再询问：

```json
"allow": [
  "Bash(gh *)"
]
```

#### Playwright——浏览器自动化

```bash
# macOS / Linux
claude mcp add playwright -s user -- npx -y @playwright/mcp@latest

# Windows PowerShell
claude mcp add playwright -s user '--' npx -y @playwright/mcp@latest
```

#### 文件系统 MCP——跨目录访问

```bash
# macOS / Linux
claude mcp add filesystem -s user -- npx -y @modelcontextprotocol/server-filesystem /Users/你的用户名

# Windows PowerShell
claude mcp add filesystem -s user '--' npx -y @modelcontextprotocol/server-filesystem C:\Users\你的用户名
```

---

## 第三章：减少打扰——让 Claude 自动干活

Claude Code 默认每一步都问你：读这个文件可以吗？执行这条命令可以吗？做一个稍微复杂的任务，要点几十次"允许"。

我们一般要实现目标是：**讨论方案时你来把关，方案确认后全程自动，不再打扰。** 以下有几种方式基本可以达到减少确认，提高自动化程度的做法。

### 3.1 权限模式

用 `Shift + Tab` 在会话中随时切换：

| 模式                  | 行为             | 使用场景              |
| ------------------- | -------------- | ----------------- |
| `plan`              | 只读，不写文件不执行命令   | 讨论方案阶段            |
| `acceptEdits`       | 文件读写自动批准，命令仍询问 | 方案确认后执行           |
| `default`           | 每个工具首次使用时询问    | 默认状态              |
| `bypassPermissions` | 跳过所有检查         | 仅限 CI/Docker 隔离环境 |

**工作流：**

```
① Shift+Tab → 切到 plan 模式
  > 我想加一个用户登录限速功能，你看代码，给我方案

② Claude 分析代码给出方案，不动任何文件
  确认方案后说"开始实现"

③ Shift+Tab → 切到 acceptEdits 模式
  Claude 修改文件，不再询问文件操作

④ Claude 完成后，手动 git push
```

这一层是临时的，关掉会话就重置。

### 3.2 持久化配置

把规则写进 `settings.json`，每次启动都生效。

**配置文件位置：**

| 文件                            | 作用范围      | 提交 Git |
| ----------------------------- | --------- | ------ |
| `~/.claude/settings.json`     | 所有项目      | 否      |
| `.claude/settings.json`       | 当前项目，团队共享 | 是      |
| `.claude/settings.local.json` | 当前项目，仅本机  | 否      |

**个人开发推荐配置（写入 `~/.claude/settings.json`）：**

```json
{
  "defaultPermissionMode": "acceptEdits",
  "permissions": {
    "allow": [
      "Bash(*)",
      "Read(*)",
      "Write(*)",
      "Edit(*)",
      "WebFetch(*)",
      "mcp__*__*"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Bash(git push *)",
      "Bash(sudo *)"
    ]
  }
}
```

- `defaultPermissionMode: acceptEdits` — 启动时默认自动接受模式
- `Bash(*) / Read(*) / Write(*) / Edit(*)` — 放行所有文件操作和命令
- `WebFetch(*)` — 放行所有 URL 抓取
- `mcp__*__*` — 放行所有 MCP 工具调用
- deny 三条是底线：递归删除、推送代码、提权，永远需要手动确认

`deny` 永远优先于 `allow`。即使 `Bash(*)` 放行了所有命令，`Bash(rm -rf *)` 的 deny 仍然生效。

### 3.3 团队配置

写在 `.claude/settings.json` 提交 Git，团队共享。团队配置比个人配置更保守，逐条列出允许的命令：

```json
{
  "permissions": {
    "allow": [
      "Bash(npm run lint)",
      "Bash(npm run test)",
      "Bash(npm run build)",
      "Bash(git status)",
      "Bash(git diff *)",
      "Bash(git add *)",
      "Bash(git commit *)",
      "mcp__*__*"
    ],
    "deny": [
      "Bash(git push *)",
      "Bash(rm -rf *)",
      "Bash(sudo *)",
      "Read(./.env)",
      "Read(./secrets/**)"
    ]
  }
}
```

### 3.4 查看当前生效的配置

```
/status
```

### 3.5 CI/CD 无人值守

启动claude时，使用以下命令，可以跳过所有的确认。

```bash
claude --dangerously-skip-permissions -p "运行所有测试并修复失败的用例"
```

跳过所有权限检查包括 deny 列表，仅在隔离的 Docker 容器或 CI 环境中使用。

---

## 第四章：斜杠命令——一键触发工作流

### 4.1 内置命令

| 命令             | 作用                          |
| -------------- | --------------------------- |
| `/help`        | 显示所有可用命令                    |
| `/status`      | 查看当前配置状态、权限来源               |
| `/model`       | 切换模型（Haiku / Sonnet / Opus） |
| `/compact`     | 压缩对话历史，节省上下文                |
| `/clear`       | 清空当前会话                      |
| `/permissions` | 交互式管理工具权限                   |
| `/init`        | 初始化项目，自动生成 CLAUDE.md        |
| `/cost`        | 查看当前会话的 Token 用量            |

### 4.2 创建自定义命令

在指定目录创建 Markdown 文件：

- `.claude/commands/命令名.md` — 当前项目，可提交 Git 共享
- `~/.claude/commands/命令名.md` — 所有项目可用

示例：`.claude/commands/review.md`

```markdown
# 代码审查

请对 $ARGUMENTS 进行代码审查，重点检查：

1. **代码逻辑**：潜在的 Bug 或边界情况
2. **代码风格**：是否符合项目规范（参考 CLAUDE.md）
3. **安全隐患**：SQL 注入、XSS、敏感信息暴露等
4. **性能问题**：N+1 查询、不必要的循环等

给出 1-10 的综合评分并列出最重要的三条改进建议。
```

使用：

```bash
/review src/auth/login.js

# 不进入交互模式直接运行
claude -p "/review src/auth/login.js"
```

`$ARGUMENTS` 会被替换为命令后面输入的内容。

### 4.3 在命令中编排子代理

斜杠命令可以描述多步骤工作流，让 Claude 自动调用子代理分步完成：

```markdown
# .claude/commands/feature.md

针对需求：$ARGUMENTS

1. 使用 Explore 子代理扫描相关代码，理解现有架构
2. 列出实现方案和需要修改的文件
3. 等待确认方案后再开始实现
4. 实现完成后运行 npm run test 验证
5. 生成 commit message
```

---

## 第五章：子代理（Subagents）

### 5.1 为什么需要子代理？

对话上下文越长，Token 成本越高，回复质量也会下降。子代理解决这个问题：每个子代理是独立的 Claude 实例，有自己的上下文窗口，完成任务后只把结果摘要返回主会话，不污染主对话。

### 5.2 内置子代理

- **Explore** — 只读代码库探索，进入 Plan 模式时自动启动
- **general-purpose** — 通用代理，需要完整工具访问权限时使用

### 5.3 创建自定义子代理

存放位置：

- `.claude/agents/` — 项目级，可提交 Git
- `~/.claude/agents/` — 个人全局

示例：`.claude/agents/code-reviewer.md`

```markdown
---
name: code-reviewer
description: 代码质量审查专家。当用户要求审查代码、检查潜在问题或评估代码质量时自动调用。
tools: Read, Grep, Glob, Bash
model: inherit
---

你是一位经验丰富的高级工程师，专注于代码质量审查。

收到审查请求时：
1. 运行 git diff 查看最新修改
2. 检查代码逻辑、安全漏洞、性能问题
3. 验证是否符合项目编码规范（参考 CLAUDE.md）
4. 给出结构化的审查报告

严格保持只读——不要修改任何文件。
```

YAML 字段说明：

| 字段                | 说明                                                |
| ----------------- | ------------------------------------------------- |
| `name`            | 标识名，用于手动调用                                        |
| `description`     | 触发时机描述，越清晰自动委托越准确                                 |
| `tools`           | `Read/Grep/Glob` 只读，`Bash` 执行命令，`Write/Edit` 修改文件 |
| `model`           | `inherit`（继承主会话）、`haiku`、`sonnet`、`opus`          |
| `disallowedTools` | 明确禁止的工具                                           |
| `maxTurns`        | 最多对话轮数，防止无限循环                                     |

### 5.4 触发方式

**自动委托** — 请求匹配 description 时自动调用：

```
> 帮我看一下 src/auth/ 下面的代码有没有安全问题
```

**手动指定：**

```
> 用 code-reviewer 子代理审查一下 src/payment.js
```

**后台异步：** `Ctrl + B`（Mac：`Cmd + B`），子代理在后台运行，完成后通知你。

### 5.5 实战：三阶段开发流水线

三个子代理：

```markdown
# .claude/agents/pm-analyst.md
---
name: pm-analyst
description: 分析需求并生成技术规格文档
tools: Read, Grep
model: sonnet
---
把用户需求转化为技术规格。
输出：需求摘要 / 验收标准 / 涉及文件列表
```

```markdown
# .claude/agents/architect.md
---
name: architect
description: 基于规格文档设计技术方案
tools: Read, Glob, Grep
model: opus
---
设计最优技术实现方案。
输出：方案说明 / 修改文件清单 / 潜在风险
```

```markdown
# .claude/agents/implementer.md
---
name: implementer
description: 按照架构方案实现代码并运行测试
tools: Read, Write, Edit, Bash
model: sonnet
---
按方案实现功能，完成后必须运行 npm run test 并确保全部通过。
```

入口命令 `.claude/commands/build-feature.md`：

```markdown
需求：$ARGUMENTS

1. 调用 pm-analyst 分析需求，输出规格文档
2. 确认规格后，调用 architect 设计方案
3. 确认方案后，调用 implementer 实现代码
4. 完成后给出变更总结
```

```
/build-feature 用户注册时发送欢迎邮件
```

---

## 第六章：Hooks——生命周期自动化

### 6.1 Hooks 是什么？

Hooks 是绑定到 Claude Code 操作事件的 Shell 命令，事件触发时自动执行。类似 Git Hooks，触发点是 Claude Code 的操作事件而不是 git 命令。

### 6.2 事件类型

| 事件             | 触发时机          |
| -------------- | ------------- |
| `PreToolUse`   | Claude 调用工具之前 |
| `PostToolUse`  | Claude 调用工具之后 |
| `Stop`         | Claude 完成任务时  |
| `SubagentStop` | 子代理完成任务时      |
| `Notification` | Claude 发出通知时  |

### 6.3 配置

Hooks 写在 `settings.json` 的 `hooks` 字段里，路径和第三章的权限配置相同：

- `~/.claude/settings.json` — 全局生效，所有项目都有这些 Hook
- `.claude/settings.json` — 只对当前项目生效，可提交 Git 与团队共享

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "notify-send 'Claude Code' '任务完成'"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "cd $CLAUDE_PROJECT_DIR && npm run lint --silent 2>&1 | head -20"
          }
        ]
      }
    ]
  }
}
```

`matcher` 是正则表达式，匹配工具名称，空字符串表示匹配所有。

### 6.4 常用示例

**任务完成后桌面通知（macOS）：**

```json
"Stop": [
  {
    "matcher": "",
    "hooks": [{ "type": "command", "command": "osascript -e 'display notification \"任务完成\" with title \"Claude Code\"'" }]
  }
]
```

**写文件后自动 lint：**

```json
"PostToolUse": [
  {
    "matcher": "Write|Edit",
    "hooks": [{ "type": "command", "command": "npm run lint --silent" }]
  }
]
```

**子代理完成后提示下一步：**

```json
"SubagentStop": [
  {
    "matcher": "",
    "hooks": [{ "type": "command", "command": "echo '下一步建议运行：npm run test'" }]
  }
]
```

Hook 命令以 Claude Code 的权限运行，不要在 Hook 里执行破坏性操作。

---

## 第七章：插件（Plugins）——打包可复用的工作流

### 7.1 插件是什么？

插件把 **MCP 服务器 + 斜杠命令 + 子代理 + Hooks** 打包成可分发单元。别人配置好的工作流，一条命令安装后立刻可用。

适用场景：

- 在不同机器和项目之间同步全套配置
- 新人加入后运行一条命令获得和团队一致的开发环境
- 把自己项目的配套工具发布给用户

### 7.2 插件结构

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json
├── .mcp.json
├── commands/
│   └── review.md
├── agents/
│   └── code-reviewer.md
├── hooks/
└── README.md
```

`plugin.json`：

```json
{
  "name": "my-review-toolkit",
  "version": "1.0.0",
  "description": "代码审查工具：/review 命令 + code-reviewer 子代理",
  "author": "yourname",
  "claude_code_min_version": "1.0.0"
}
```

### 7.3 安装插件

打开管理界面：

```bash
/plugin
```

四个标签：**Discover**（发现）、**Installed**（已安装）、**Marketplaces**（市场）、**Errors**（错误）

添加第三方市场：

```bash
/plugin marketplace add <github用户名>/<仓库名>
```

安装范围：

- `--scope user` — 个人全局
- `--scope project` — 写入 `.claude/`，提交 Git 团队共享
- `--scope local` — 仅本地，不提交 Git

```bash
/plugin install <插件名> --scope user
```

### 7.4 官方插件清单

**第一梯队（优先安装）：**

`commit-commands` — 自动生成符合 Conventional Commits 规范的提交信息

```bash
/plugin install commit-commands --scope user
```

```
/commit
# 分析 git diff 后生成：feat(auth): add rate limiting
```

`pr-review-toolkit` — 六个维度的 PR 审查，每个维度由独立子代理负责

```bash
/plugin install pr-review-toolkit --scope user
/pr-review-toolkit:review-pr --aspects comments,tests,errors
```

`frontend-design` — 前端 UI 生成，内置设计规范，避免风格单一

```bash
/plugin install frontend-design --scope user
```

**第二梯队（按语言安装）：**

```bash
/plugin install typescript-lsp --scope project   # JS/TS
/plugin install python-lsp --scope project       # Python
/plugin install rust-lsp --scope project         # Rust
/plugin install go-lsp --scope project           # Go
/plugin install security-guidance --scope project
/plugin install feature-dev --scope user
```

**推荐安装顺序：**

```bash
/plugin install commit-commands --scope user
/plugin install pr-review-toolkit --scope user
/plugin install frontend-design --scope user
/plugin install typescript-lsp --scope project
/plugin install security-guidance --scope project
```

### 7.5 自动更新

官方市场插件默认自动更新，启动时检查。第三方市场需在 `/plugin → Marketplaces` 手动开启。

```
/reload-plugins
```

### 7.6 插件 vs 手动配置

| 场景           | 做法         |
| ------------ | ---------- |
| 自己专用、经常调整    | 手动创建       |
| 团队统一配置、需版本控制 | 打包插件提交 Git |
| 使用社区成熟工具     | 从市场安装      |

---

## 第八章：综合实战

### 8.1 项目目录结构

```
my-project/
├── CLAUDE.md
├── .mcp.json
├── .claude/
│   ├── settings.json
│   ├── settings.local.json
│   ├── commands/
│   │   ├── review.md
│   │   ├── deploy.md
│   │   └── build-feature.md
│   ├── agents/
│   │   ├── code-reviewer.md
│   │   ├── architect.md
│   │   └── implementer.md
│   └── plugins/
│       └── pr-review-toolkit/
```

### 8.2 日常工作流示例

```bash
cd my-project && claude

# 查看今天的任务
> 看一下今天有哪些 P0 级别的 Issue 需要处理

# 开发新功能
/build-feature 修复用户头像上传失败的 Bug（Issue #234）

# 审查代码
/review src/upload/

# 提交
/commit

# 创建 PR
> 基于当前分支创建一个 PR，描述这次修复的内容
```

### 8.3 最佳实践

- CLAUDE.md 写清楚技术栈、编码规范、项目约定
- 每个子代理只做一件事，职责越单一越好
- description 写成动作指令，"当用户需要审查代码时"，而不是"代码审查工具"
- 只读子代理只给 `Read/Grep/Glob`，写代码的才给 `Write/Edit/Bash`
- Hook 只做无副作用的操作（lint、通知、日志），不要改文件
- 团队配置提交 Git，个人偏好用 `settings.local.json`

---

## 结语

六个功能的选择思路：

- 需要连接外部系统 → **MCP**
- 有重复的工作流 → **斜杠命令**
- 任务复杂、担心上下文过长 → **子代理**
- 需要自动化守卫（lint、通知） → **Hooks**
- 共享配置给团队或使用社区工具 → **插件**
- 控制 Claude 的操作权限 → **settings.json**

---

## 参考资料

- Claude Code 官方文档：https://docs.claude.com/en/docs/claude-code/overview
- Claude Code 设置文档：https://docs.claude.com/en/docs/claude-code/settings
- Awesome Claude Code 社区资源：https://github.com/hesreallyhim/awesome-claude-code
