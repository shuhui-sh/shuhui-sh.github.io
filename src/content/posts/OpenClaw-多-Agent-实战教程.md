---
title: "OpenClaw 多 Agent 实战教程"
date: 2026-04-02
description: "1. 架构概览 2. 多群组 × 独立 Agent 3. 同群组内多 Agent 协同"
tags: ['AI', 'Agent', 'OpenClaw']
draft: true
category: "技术"
---
> Telegram 多群组 × 多 Agent 角色 × 工作流产物共享｜适用于 OpenClaw v2026.x

---

## 目录

1. [架构概览](#第一章架构概览)
2. [多群组 × 独立 Agent](#第二章多群组--独立-agent)
3. [同群组内多 Agent 协同](#第三章同群组内多-agent-协同)
4. [有序工作流 + 产物共享](#第四章有序工作流--产物共享)
5. [完整 Workspace 文件参考](#第五章完整-workspace-文件参考)
6. [常见问题排查](#第六章常见问题排查)
7. [附录：配置速查表](#附录配置速查表)

---

## 第一章：架构概览

本教程覆盖三个核心场景，你可以按需独立使用，也可以组合搭建完整系统：

| # | 场景 | 说明 |
|---|------|------|
| 1 | 多群组 × 独立 Agent | 不同 Telegram 群组绑定不同 Agent，角色完全隔离 |
| 2 | 同群组内多 Agent 协同 | 通过 mentionPatterns 在同一群组召唤不同专家 |
| 3 | 有序工作流 + 产物共享 | 用 Lobster 工作流引擎驱动多 Agent 顺序协作，前一个 Agent 的输出是下一个的输入 |

> 💡 **核心设计原则**：LLM 负责创造性工作（写需求、写代码、写测试），Lobster 负责编排（顺序、条件、循环）。不要用 Prompt 控制流程——LLM 是不可靠的路由器。

---

## 第二章：多群组 × 独立 Agent

最简单的场景：每个 Telegram 群组对应一个专属 Agent，会话历史、Workspace、工具权限完全隔离，互不干扰。

### 2.1 设计思路

OpenClaw 通过 `agents.list` 定义 Agent 实体，通过 `agents.bindings` 将 Agent 绑定到特定群组。每个 Agent 有独立的：

- **Workspace 目录**（SOUL.md 人格、AGENTS.md 行为规范、skills/）
- **工具权限**（编码专家有 `exec`，写作专家没有）
- **模型配置**（可为不同 Agent 选不同的 primary 模型）
- **会话历史**（群组 A 的对话不会污染群组 B）

### 2.2 四个角色配置

**Step 1 — 创建 Workspace 目录**

```bash
mkdir -p ~/.openclaw/workspace-task
mkdir -p ~/.openclaw/workspace-coder
mkdir -p ~/.openclaw/workspace-analyst
mkdir -p ~/.openclaw/workspace-writer
```

**Step 2 — 给每个 Agent 写 SOUL.md**

以编码专家为例（`~/.openclaw/workspace-coder/SOUL.md`）：

```
你是一个资深全栈工程师，擅长代码审查、架构设计和 debug。
回答优先给出可运行的完整代码，附简洁的解释。
若需求不明确，先提问再动手。
输出代码时使用代码块并标注语言。
```

**Step 3 — 获取 Telegram 群组 ID**

在各个群组发一条消息，然后执行：

```bash
openclaw logs --follow
```

在日志里找 `chat.id`，格式为 `-100xxxxxxxxx`，记录每个群组对应的 ID。

**Step 4 — openclaw.json 配置**

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "bailian/qwen3-max-2026-01-23",
        "fallbacks": ["minimax/MiniMax-M2.5", "deepseek/deepseek-reasoner"]
      },
      "maxConcurrent": 4,
      "subagents": { "maxConcurrent": 8 }
    },
    "list": [
      {
        "id": "task-manager",
        "workspace": "~/.openclaw/workspace-task",
        "identity": { "name": "任务助手", "emoji": "📋" },
        "tools": { "allow": ["read", "write", "sessions_send", "message", "cron"] }
      },
      {
        "id": "coder",
        "workspace": "~/.openclaw/workspace-coder",
        "identity": { "name": "编码专家", "emoji": "💻" },
        "tools": { "allow": ["read", "write", "exec", "apply_patch"] }
      },
      {
        "id": "analyst",
        "workspace": "~/.openclaw/workspace-analyst",
        "identity": { "name": "需求分析专家", "emoji": "🔍" },
        "tools": { "allow": ["read", "write", "browser", "web_search"] }
      },
      {
        "id": "writer",
        "workspace": "~/.openclaw/workspace-writer",
        "identity": { "name": "写作专家", "emoji": "✍️" },
        "tools": { "allow": ["read", "write", "browser"] }
      }
    ],
    "bindings": [
      { "agentId": "task-manager", "match": { "channel": "telegram", "peer": { "kind": "group", "id": "-100111111111" } } },
      { "agentId": "coder",        "match": { "channel": "telegram", "peer": { "kind": "group", "id": "-100222222222" } } },
      { "agentId": "analyst",      "match": { "channel": "telegram", "peer": { "kind": "group", "id": "-100333333333" } } },
      { "agentId": "writer",       "match": { "channel": "telegram", "peer": { "kind": "group", "id": "-100444444444" } } }
    ]
  }
}
```

> ⚠️ `-100111111111` 等是占位符，替换为你在 Step 3 中获取的真实群组 ID。

### 2.3 群组级别精细控制

每个群组还可以在 `channels.telegram.groups` 下独立配置：

| 配置项 | 示例值 | 说明 |
|--------|--------|------|
| `groupPolicy` | `open` / `allowlist` | 群组内谁能触发 Agent |
| `requireMention` | `true` / `false` | 是否必须 @ 机器人 |
| `systemPrompt` | 额外提示词 | 叠加到 SOUL.md 之上的上下文 |
| `skills` | `["code-review"]` | 限制该群组只能用哪些 skill |
| `allowFrom` | `[123456789]` | 用户 ID 白名单（数字格式） |
| `enabled` | `false` | 直接禁用某个群组 |

```json
{
  "channels": {
    "telegram": {
      "groups": {
        "-100222222222": {
          "groupPolicy": "open",
          "requireMention": true,
          "systemPrompt": "只回答与编程相关的问题，拒绝其他话题"
        }
      }
    }
  }
}
```

---

## 第三章：同群组内多 Agent 协同

如果你不想建太多群组，也可以在同一个群组里用不同的 `mentionPatterns` 召唤不同的 Agent。

### 3.1 设计思路

通过 `agents.list[].groupChat.mentionPatterns` 为每个 Agent 注册自定义触发词。用户输入 `@code` 就路由到 coder，输入 `@需求` 就路由到 analyst，@ 机器人真实用户名时仍然触发默认 Agent。

### 3.2 配置示例

```json
"list": [
  {
    "id": "coder",
    "groupChat": {
      "mentionPatterns": ["@code", "@coder", "@编码"]
    }
  },
  {
    "id": "analyst",
    "groupChat": {
      "mentionPatterns": ["@analyst", "@需求", "@分析"]
    }
  },
  {
    "id": "writer",
    "groupChat": {
      "mentionPatterns": ["@writer", "@写作", "@文案"]
    }
  }
]
```

### 3.3 使用方式

在任意已授权的群组内发送：

```
@code 帮我写一个 Python 爬虫，抓取豆瓣 Top250
@需求 整理一下用户反馈，提炼出核心功能点
@写作 根据以下要点写一篇产品公告
```

> 💡 **与 bindings 的区别**：`bindings` 是一对一绑定（群组 → Agent），`mentionPatterns` 是一对多路由（同一群组内多个 Agent 共存）。两种方式可以组合使用：用 `bindings` 设置群组的默认 Agent，用 `mentionPatterns` 在群组内召唤其他专家。

---

## 第四章：有序工作流 + 产物共享

当你需要「需求分析 → UI 设计 → 编码实现 → 回归测试」这样有顺序依赖的工作流时，每个阶段的输出是下一个阶段的输入，这就需要用 OpenClaw 内置的 **Lobster 工作流引擎**来编排。

### 4.1 三层架构

```
┌─────────────────────────────────────────────────┐
│  Telegram 群组（人触发 / 接收通知）              │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│  Lobster 工作流引擎（确定性编排）                │
│  dev-pipeline.lobster                            │
│  └── coding-review.lobster（子工作流，可循环）   │
└──────┬──────┬──────┬──────┬───────────────────── ┘
       │      │      │      │
    analyst  ui   coder  tester     ← 独立 Agent
       │      │      │      │
┌──────▼──────▼──────▼──────▼──────────────────────┐
│  ~/projects/<project>/  （共享项目目录）           │
│  ├── requirements.md   ← analyst 输出              │
│  ├── ui-spec.md        ← ui-designer 输出          │
│  ├── src/              ← coder 输出                │
│  └── test-report.md    ← tester 输出               │
└───────────────────────────────────────────────────┘
```

### 4.2 共享项目目录（产物流转核心）

每个 Agent 的 Workspace 是独立的，但它们都可以读写同一个**共享项目目录**，这是产物流转的关键机制。

```bash
# 初始化项目目录结构
mkdir -p ~/projects/my-project/src

# 目录规划
~/projects/my-project/
├── requirements.md    # analyst 写入，ui-designer/coder 读取
├── ui-spec.md         # ui-designer 写入，coder 读取
├── src/               # coder 写入，tester 读取
│   └── *.py / *.ts
└── test-report.md     # tester 写入，任务管理者读取
```

在每个 Agent 的 `AGENTS.md` 中明确约定读写职责（以 analyst 为例）：

```markdown
# AGENTS.md
## 输入
- 来自对话的用户需求描述

## 输出
- 写入：~/projects/<project>/requirements.md

## requirements.md 格式
### 1. 功能需求列表（每项有优先级 P0/P1/P2）
### 2. 非功能需求
### 3. 边界条件和约束
### 4. 验收标准
```

> ✅ **关键约定**：每个 Agent 只写自己职责范围内的文件，只读上游 Agent 的输出。这种约定防止产物污染，也让调试更容易——出问题看哪个文件就知道是哪个 Agent 的责任。

### 4.3 Agent 配置（加入 agentToAgent）

```json
{
  "agents": {
    "defaults": {
      "tools": {
        "agentToAgent": {
          "enabled": true,
          "allow": ["analyst", "ui-designer", "coder", "tester"]
        }
      }
    },
    "list": [
      {
        "id": "analyst",
        "workspace": "~/.openclaw/workspace-analyst",
        "identity": { "name": "需求分析专家", "emoji": "🔍" },
        "model": { "primary": "bailian/qwen3-max-2026-01-23" },
        "tools": { "allow": ["read", "write", "browser", "web_search"] }
      },
      {
        "id": "ui-designer",
        "workspace": "~/.openclaw/workspace-ui",
        "identity": { "name": "UI 设计专家", "emoji": "🎨" },
        "model": { "primary": "bailian/qwen3-max-2026-01-23" },
        "tools": { "allow": ["read", "write"] }
      },
      {
        "id": "coder",
        "workspace": "~/.openclaw/workspace-coder",
        "identity": { "name": "编码专家", "emoji": "💻" },
        "model": { "primary": "bailian/qwen3-max-2026-01-23" },
        "tools": { "allow": ["read", "write", "exec", "apply_patch"] }
      },
      {
        "id": "tester",
        "workspace": "~/.openclaw/workspace-tester",
        "identity": { "name": "测试专家", "emoji": "🧪" },
        "model": { "primary": "deepseek/deepseek-chat" },
        "tools": { "allow": ["read", "exec"] }
      }
    ]
  }
}
```

> 💡 tester 使用 `deepseek-chat` 节省成本；只读文件不写，防止越权修改代码。

### 4.4 Session Key 命名约定

Session Key 是 Agent 间通信的地址，设计好命名是关键：

```bash
# 格式：pipeline:<project>:<role>
pipeline:auth-module:analyst
pipeline:auth-module:ui-designer
pipeline:auth-module:coder
pipeline:auth-module:tester

# 好处：
# 1. project 隔离 —— 多个项目并行时互不干扰
# 2. role 标识 —— 一眼知道是哪个 Agent 在处理
# 3. 可追溯 —— openclaw logs 按 sessionKey 过滤，方便 debug
```

### 4.5 Lobster 工作流文件

#### 主流程：dev-pipeline.lobster

```yaml
name: dev-pipeline
args:
  project: { required: true }
  requirement: { required: true }
  chat_id: { required: true }

steps:
  # ─── Step 1: 需求分析 ───────────────────────────
  - id: analysis
    command: >
      openclaw.invoke --tool agent-send --args-json '{
        "agentId": "analyst",
        "message": "分析以下需求，输出到 ~/projects/${project}/requirements.md：${requirement}",
        "sessionKey": "pipeline:${project}:analyst"
      }'

  # ─── Step 2: UI 设计（依赖 requirements.md）────
  - id: ui-design
    command: >
      openclaw.invoke --tool agent-send --args-json '{
        "agentId": "ui-designer",
        "message": "读取 ~/projects/${project}/requirements.md，输出 UI 规范到 ~/projects/${project}/ui-spec.md",
        "sessionKey": "pipeline:${project}:ui-designer"
      }'
    condition: $analysis.exitCode == 0

  # ─── Step 3: 编码（含循环审查，最多 3 轮）──────
  - id: coding-loop
    lobster: ./coding-review.lobster
    args:
      project: ${project}
    loop:
      maxIterations: 3
      condition: '! echo "$LOBSTER_LOOP_JSON" | jq -e ".approved"'
    condition: $ui-design.exitCode == 0

  # ─── Step 4: 回归测试 ───────────────────────────
  - id: testing
    command: >
      openclaw.invoke --tool agent-send --args-json '{
        "agentId": "tester",
        "message": "对 ~/projects/${project}/src/ 执行回归测试，输出报告到 ~/projects/${project}/test-report.md",
        "sessionKey": "pipeline:${project}:tester"
      }'
    condition: $coding-loop.json.approved == true

  # ─── Step 5: 完成通知 ───────────────────────────
  - id: notify
    command: >
      openclaw.invoke --tool message --action send --args-json '{
        "provider": "telegram",
        "to": "${chat_id}",
        "text": "✅ ${project} 全流程完成！测试报告：~/projects/${project}/test-report.md"
      }'
    condition: $testing.exitCode == 0
```

#### 子流程：coding-review.lobster（支持循环）

```yaml
name: coding-review
args:
  project: { required: true }

steps:
  # ─── 编码 ────────────────────────────────────────
  - id: code
    command: >
      openclaw.invoke --tool agent-send --args-json '{
        "agentId": "coder",
        "message": "读取 ~/projects/${project}/ui-spec.md，实现代码到 ~/projects/${project}/src/，当前第 $LOBSTER_LOOP_ITERATION 轮",
        "sessionKey": "pipeline:${project}:coder"
      }'

  # ─── 结构化审查（llm-task 输出可判断的 JSON）───
  - id: review
    command: >
      openclaw.invoke --tool llm-task --action json --args-json '{
        "prompt": "检查 ~/projects/${project}/src/ 是否完整实现了 ui-spec.md 的要求。返回 approved(bool) 和 feedback(string)。",
        "schema": {
          "type": "object",
          "properties": {
            "approved": { "type": "boolean" },
            "feedback": { "type": "string" }
          },
          "required": ["approved", "feedback"]
        }
      }'
    stdin: $code.stdout
```

> ⚠️ **关于 Lobster loop 支持**：`loop` 功能由社区贡献的 PR #20 引入，请确认你的 OpenClaw 版本已包含此功能（v2026.2.x 之后）。如未包含，可用 Webhook 轮询替代 loop 步骤。

### 4.6 触发工作流

**方式一：Telegram 命令（推荐）**

在任务派发群组里发送：

```
/run-pipeline project=auth-module requirement="实现用户注册登录，支持手机号和邮箱双通道"
```

**方式二：Webhook（外部系统触发）**

```bash
curl -X POST http://127.0.0.1:18789/hooks/agent \
  -H 'Authorization: Bearer YOUR_GATEWAY_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "run dev-pipeline",
    "agentId": "task-manager",
    "sessionKey": "hook:auth-module:orchestrator",
    "deliver": false
  }'
```

---

## 第五章：完整 Workspace 文件参考

### 5.1 需求分析专家（analyst）

**目录结构**

```
~/.openclaw/workspace-analyst/
├── SOUL.md
├── AGENTS.md
└── skills/
    └── requirement-template/
        └── SKILL.md
```

**SOUL.md**

```
你是一位经验丰富的产品需求分析师，擅长从模糊描述中提炼清晰的功能需求。
你善于发现边界条件、潜在冲突和未明确的假设。
输出时结构清晰，优先级明确，验收标准可量化。
```

**AGENTS.md**

```markdown
## 输入
- 来自对话的用户需求描述

## 输出
- 写入：~/projects/<project>/requirements.md

## requirements.md 格式
### 1. 功能需求
| 功能 | 优先级 | 验收标准 |
|------|--------|---------|

### 2. 非功能需求
### 3. 边界条件
### 4. 开放问题（需进一步确认）
```

### 5.2 UI 设计专家（ui-designer）

**AGENTS.md**

```markdown
## 输入
- 读取：~/projects/<project>/requirements.md

## 输出
- 写入：~/projects/<project>/ui-spec.md

## ui-spec.md 格式
### 1. 页面/组件清单
### 2. 每个页面的元素和交互
### 3. 数据流说明（输入 → 处理 → 输出）
### 4. API 接口约定（RESTful 风格）
### 5. 错误处理规范
```

### 5.3 编码专家（coder）

**AGENTS.md**

```markdown
## 输入
- 读取：~/projects/<project>/ui-spec.md
- 如有循环反馈，读取：上轮代码审查意见（来自对话上下文）

## 输出
- 写入：~/projects/<project>/src/

## 编码规范
- 每个文件头部有注释说明用途
- 有意义的函数名和变量名，不要单字母
- 边界条件有错误处理
- 代码可直接运行（包含依赖安装说明）
```

### 5.4 测试专家（tester）

**AGENTS.md**

```markdown
## 输入
- 读取：~/projects/<project>/src/（只读，不得修改代码）
- 读取：~/projects/<project>/requirements.md（验收标准参考）

## 输出
- 写入：~/projects/<project>/test-report.md

## test-report.md 格式
### 测试结论：PASS / FAIL
### 测试覆盖率
### 通过用例列表
### 失败用例列表（含复现步骤）
### 改进建议
```

---

## 第六章：常见问题排查

### 6.1 机器人在群组不回复

| 症状 / 原因 | 解决方案 |
|-------------|---------|
| Privacy Mode 开启 | BotFather → `/setprivacy` → Disable，然后重新加入群组 |
| `groups` 白名单未配置 | 在 `channels.telegram.groups` 添加群组 ID 或用 `"*"` 通配 |
| `groupPolicy` 是 `allowlist` 但未配置 `groupAllowFrom` | 添加你的数字 Telegram ID 到 `groupAllowFrom` |
| `bindings` 的群组 ID 有误 | 用 `openclaw logs --follow` 确认真实 `chat.id` |

### 6.2 Agent 间产物没有传递

- 确认共享目录绝对路径正确（用 `~/projects/` 或写完整路径）
- 确认上游 Agent 已完成写入（检查文件是否存在）
- 用 `openclaw logs --follow` 追踪 sessionKey，确认 `agent-send` 有被触发
- Lobster 的 `condition` 检查 `exitCode`，而不是内容是否正确——先让流程跑通再调内容

### 6.3 Lobster loop 不生效

- 确认 OpenClaw 版本包含 loop 支持（v2026.2.x+）
- `loop.condition` 是 shell 命令，exit 0 = 继续，非零 = 停止
- 用 `echo $LOBSTER_LOOP_ITERATION` 在 condition 命令里验证环境变量是否正确注入

### 6.4 多项目并行时会话混乱

- sessionKey 必须包含 project 名称，如 `pipeline:auth-module:coder`
- 不同项目永远不要共用同一个 sessionKey
- 每次启动新项目的工作流前，可选择清理旧会话：`openclaw sessions clear pipeline:old-project:*`

---

## 附录：配置速查表

### 关键配置项一览

| 配置路径 | 类型 | 说明 |
|----------|------|------|
| `agents.list[].id` | string | Agent 唯一标识 |
| `agents.list[].workspace` | path | Workspace 目录 |
| `agents.list[].tools.allow` | string[] | 允许的工具列表 |
| `agents.bindings[].agentId` | string | 绑定哪个 Agent |
| `agents.bindings[].match.peer.id` | string | 群组 ID（-100xxx） |
| `agents.defaults.tools.agentToAgent` | object | 开启 Agent 间直连通信 |
| `channels.telegram.groups.<id>.requireMention` | bool | 是否需要 @ 机器人 |
| `channels.telegram.groups.<id>.groupPolicy` | enum | open / allowlist / disabled |
| `channels.telegram.groupAllowFrom` | number[] | 群组发言用户白名单 |

### 常用 CLI 命令

```bash
# 启动网关
openclaw gateway

# 查看实时日志（获取 chat.id / sessionKey）
openclaw logs --follow

# 查看配对列表
openclaw pairing list telegram

# 批准配对
openclaw pairing approve telegram <CODE>

# 向特定目标发消息
openclaw message send --channel telegram --target @username --message "test"

# 检查 Telegram 连接状态
openclaw channels status

# 自动修复配置中的遗留 @username
openclaw doctor --fix

# 清理指定前缀的旧会话
openclaw sessions clear pipeline:old-project:*
```

---

> 📌 本文档基于 OpenClaw v2026.2.x 编写，Lobster loop 功能需 v2026.2.x 之后版本。如有变化请以官方文档 [docs.openclaw.ai](https://docs.openclaw.ai) 为准。
