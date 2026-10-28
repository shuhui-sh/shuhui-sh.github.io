---
title: "OpenClaw 最佳实践：协同与隔离完全指南"
date: 2026-04-02
description: "1. 核心概念与心智模型 2. 四个维度的隔离边界 3. 群组的组织哲学 4. Agent 的角色设计"
tags: ['OpenClaw']
category: "技术"
---
> 如何组织 Telegram 群组、Agent、角色与工作流，发挥 OpenClaw 的最大效用

---

## 目录

1. [核心概念与心智模型](#第一章核心概念与心智模型)
2. [四个维度的隔离边界](#第二章四个维度的隔离边界)
3. [群组的组织哲学](#第三章群组的组织哲学)
4. [Agent 的角色设计](#第四章agent-的角色设计)
5. [协同机制详解](#第五章协同机制详解)
6. [工作流的三种模式](#第六章工作流的三种模式)
7. [完整实战场景：软件研发团队](#第七章完整实战场景软件研发团队)
8. [安全边界与权限设计](#第八章安全边界与权限设计)
9. [运维与可观测性](#第九章运维与可观测性)
10. [附录：配置速查](#附录配置速查)

---

## 第一章：核心概念与心智模型

在开始配置之前，你需要先建立一个清晰的心智模型。OpenClaw 不是一个聊天机器人，它是一个**有状态的、事件驱动的多 Agent 编排系统**，Telegram 群组只是它的"输入界面"之一。

### 1.1 OpenClaw 的五层结构

理解 OpenClaw 最重要的是搞清楚它的五层结构，每一层都有独立的生命周期和职责：

```
┌──────────────────────────────────────────────────────────────┐
│  Layer 5：渠道层（Channel）                                   │
│  Telegram / WhatsApp / Discord / Feishu / Webhook            │
│  ↑ 消息输入                                 消息输出 ↓        │
├──────────────────────────────────────────────────────────────┤
│  Layer 4：路由层（Bindings）                                  │
│  "这条消息应该由哪个 Agent 处理？"                            │
│  channel + accountId + peer.kind + peer.id                   │
├──────────────────────────────────────────────────────────────┤
│  Layer 3：Agent 层（agents.list）                             │
│  每个 Agent 有独立的 identity / workspace / tools / model    │
├──────────────────────────────────────────────────────────────┤
│  Layer 2：Session 层（sessions）                              │
│  每个 Agent × 每个对话上下文 = 独立的 Session                │
│  会话历史 / 记忆 / 上下文窗口都在这里                        │
├──────────────────────────────────────────────────────────────┤
│  Layer 1：Workspace 层（workspace）                           │
│  Agent 的"家"：SOUL.md / AGENTS.md / skills / memory/        │
└──────────────────────────────────────────────────────────────┘
```

**关键洞察**：你在 Telegram 群组里看到的每一次对话，本质上是「渠道层事件 → 路由层匹配 → Agent 处理 → Workspace 读写 → Session 持久化」这整条链路的执行结果。

### 1.2 隔离与协同的本质矛盾

OpenClaw 最核心的设计张力是：

- **隔离**保证了 Agent 的专注性、可预测性和安全性
- **协同**保证了复杂任务的完成能力

这不是非此即彼的选择，而是在不同粒度上的精确控制：

| 维度   | 隔离机制                         | 协同机制                        |
| ---- | ---------------------------- | --------------------------- |
| 文件系统 | 独立 workspace，sandbox 沙箱      | 共享项目目录（绝对路径）                |
| 会话历史 | 每个 Agent × 每个 Session Key 独立 | sessions_send 跨 Agent 传递上下文 |
| 工具权限 | tools.allow / tools.deny 白名单 | agentToAgent 显式开启           |
| 模型选择 | 每个 Agent 独立的 primary model   | fallbacks 共享兜底模型            |
| 渠道接入 | bindings 精确路由                | mentionPatterns 在同群组多路由     |

### 1.3 什么时候需要独立 Agent，什么时候只需要 Prompt 区分

这是最容易走弯路的问题。判断标准：

**需要独立 Agent（agents.list 独立条目）的情况：**

- 工具权限不同（一个能执行代码，一个不行）
- 会话历史需要完全隔离（专业上下文不该互相污染）
- 使用不同模型（省钱 or 能力差异）
- 有独立的记忆文件（各自的 USER.md / MEMORY.md）
- 需要被其他 Agent 精确寻址（pipeline 场景）

**只需要群组级别 systemPrompt 或 skills 区分的情况：**

- 仅仅是"角色扮演"不同，但能力和权限完全一样
- 不需要独立历史，共享上下文反而更好
- 轻量临时场景，不值得为其维护一个完整 workspace

---

## 第二章：四个维度的隔离边界

### 2.1 Workspace 隔离（最强隔离）

每个 Agent 的 Workspace 是其"大脑"，包含：

```
~/.openclaw/workspace-<agentId>/
├── SOUL.md        # 人格、语气、价值观 —— 每次 Session 都加载
├── AGENTS.md      # 操作规程、行为规则 —— 每次 Session 都加载
├── USER.md        # 对话方是谁、如何称呼 —— 每次 Session 都加载
├── IDENTITY.md    # Agent 的名称和 emoji
├── TOOLS.md       # 工具使用约定（不控制权限，只是指导）
├── HEARTBEAT.md   # 心跳任务清单（保持简短）
├── BOOT.md        # 网关重启时的启动清单
├── memory/
│   ├── 2026-02-25.md   # 每日记忆日志
│   └── 2026-02-24.md
├── MEMORY.md      # 长期记忆（仅在私有主会话加载）
└── skills/        # 该 Agent 专属的 skill（覆盖全局同名 skill）
    └── my-skill/
        └── SKILL.md
```

> ⚠️ **重要**：Workspace 是默认工作目录，不是硬沙箱。Agent 通过相对路径访问 Workspace，但绝对路径仍然可以访问宿主机任意位置。如果需要真正的文件系统隔离，需要启用 `agents.defaults.sandbox`。

### 2.2 Session 隔离（中等隔离）

Session Key 决定了哪些消息共享同一个上下文。OpenClaw 的 Session Key 规则：

```
# DM 对话（合并到主会话）
agent:<agentId>:main

# 群组对话（按群组隔离）
agent:<agentId>:telegram:group:-100123456789

# Forum 话题（按话题隔离）
agent:<agentId>:telegram:group:-100123456789:topic:42

# Pipeline 自定义 Session
pipeline:<project>:<role>
```

这意味着：**同一个 Agent，面对不同的群组，天然就有独立的会话历史**。你不需要做任何额外配置，群组 A 的编码讨论不会出现在群组 B 的上下文里。

可以用 `session.reset` 控制重置策略：

```json
{
  "session": {
    "resetByType": {
      "group":  { "mode": "idle", "idleMinutes": 120 },
      "direct": { "mode": "idle", "idleMinutes": 240 },
      "thread": { "mode": "daily", "atHour": 4 }
    }
  }
}
```

### 2.3 工具权限隔离（精细隔离）

工具权限是 Agent 能力边界最直接的表达。OpenClaw 支持白名单（allow）和黑名单（deny）两种方式，deny 优先级高于 allow：

```json
{
  "agents": {
    "list": [
      {
        "id": "coder",
        "tools": {
          "allow": ["read", "write", "exec", "apply_patch", "browser"],
          "deny": ["gateway", "cron"]
        }
      },
      {
        "id": "tester",
        "tools": {
          "allow": ["read", "exec"],
          "deny": ["write", "edit", "apply_patch", "browser", "gateway"]
        }
      }
    ]
  }
}
```

可用的工具分组快捷方式：

| 分组               | 包含工具                           |
| ---------------- | ------------------------------ |
| `group:fs`       | read, write, edit, apply_patch |
| `group:runtime`  | exec, process                  |
| `group:openclaw` | 所有内置工具                         |

### 2.4 Sandbox 沙箱隔离（最强文件系统隔离）

当你需要真正防止 Agent 访问 Workspace 之外的文件时，启用 sandbox：

```json
{
  "agents": {
    "defaults": {
      "sandbox": {
        "mode": "non-main",
        "scope": "agent"
      }
    },
    "list": [
      {
        "id": "main",
        "sandbox": { "mode": "off" }
      },
      {
        "id": "untrusted-agent",
        "sandbox": {
          "mode": "all",
          "scope": "shared",
          "workspaceRoot": "/tmp/sandboxes"
        },
        "tools": {
          "deny": ["exec", "browser", "gateway"]
        }
      }
    ]
  }
}
```

> 💡 `mode: "non-main"` 的含义是：Session Key 不是 `main` 的会话（即所有群组会话和 Pipeline 会话）都自动沙箱化。这是生产环境的推荐设置。

---

## 第三章：群组的组织哲学

### 3.1 群组的三种功能模式

不同的群组应当承担不同的功能角色：

| 模式        | 用途                          | requireMention | groupPolicy       |
| --------- | --------------------------- | -------------- | ----------------- |
| **控制台群组** | 给你自己用的操作面板，触发 pipeline、查看状态 | false          | allowlist（只允许你自己） |
| **协作群组**  | 团队成员共同使用，触发特定 Agent         | true           | open 或 allowlist  |
| **通知群组**  | 只接收 Agent 的输出通知，人不触发        | —              | disabled          |
| **沙箱群组**  | 实验性 Agent，隔离测试              | true           | allowlist         |

### 3.2 群组权限的三层模型

OpenClaw 的群组访问控制是三层叠加的，从最宽到最窄：

```
第一层：channels.telegram.groups（哪些群组被允许接入）
    ├── 未配置 → 所有群组都允许
    └── 配置了 → 只有列出的群组（或 "*" 通配）允许

第二层：channels.telegram.groupPolicy（群组内谁能触发 Agent）
    ├── open    → 所有成员
    ├── allowlist → 白名单用户（groupAllowFrom）
    └── disabled  → 无人

第三层：channels.telegram.groups.<id>.allowFrom（单个群组的用户白名单覆盖）
    └── 覆盖全局 groupAllowFrom
```

实际配置示例：

```json
{
  "channels": {
    "telegram": {
      "groupPolicy": "allowlist",
      "groupAllowFrom": [123456789],
      "groups": {
        "-100111111111": {
          "groupPolicy": "open",
          "requireMention": true,
          "systemPrompt": "这是公开协作群，回答时语气正式"
        },
        "-100222222222": {
          "groupPolicy": "allowlist",
          "allowFrom": [123456789, 987654321],
          "requireMention": false,
          "systemPrompt": "这是私有控制台，可以执行所有操作"
        },
        "-100333333333": {
          "enabled": false
        }
      }
    }
  }
}
```

### 3.3 Forum 超级群组：一个群组承载多个 Agent

如果你使用 Telegram Forum 超级群组，可以在每个话题（Topic）上配置独立的 Agent 行为。这是在不创建多个群组的情况下实现 Agent 分工的最优雅方式：

```json
{
  "channels": {
    "telegram": {
      "groups": {
        "-100999999999": {
          "requireMention": true,
          "topics": {
            "101": {
              "systemPrompt": "这个话题专门讨论需求，你是需求分析专家",
              "skills": ["requirement-analysis"]
            },
            "102": {
              "systemPrompt": "这个话题专门讨论代码，你是编码专家",
              "skills": ["code-review", "debugging"]
            },
            "103": {
              "systemPrompt": "这个话题专门讨论文案，你是写作专家",
              "skills": ["copywriting"]
            }
          }
        }
      }
    }
  }
}
```

话题级别的 Session Key 格式为 `agent:<agentId>:telegram:group:-100999999999:topic:101`，每个话题天然隔离历史。

### 3.4 推荐的群组分工结构

以一个开发团队为例，推荐这样组织：

```
Telegram 群组结构
│
├── 🎛️ 【控制台】私有群组（只有你）
│   └── 触发 pipeline、查状态、发测试消息
│
├── 👥 【团队协作】半公开群组
│   ├── Topic #101: 需求讨论 → analyst agent
│   ├── Topic #102: 技术讨论 → coder agent
│   └── Topic #103: 文档/公告 → writer agent
│
├── 🤖 【自动化通知】只读群组
│   └── pipeline 完成通知、监控告警
│
└── 🧪 【沙箱测试】私有群组
    └── 实验新 skill、测试新 Agent 配置
```

---

## 第四章：Agent 的角色设计

### 4.1 Workspace 文件的编写原则

每个文件有明确的定位，不要把内容放错地方：

**SOUL.md —— 人格层（最稳定，很少改）**

```markdown
# 角色定位
你是一位资深软件架构师，有 15 年 C++ 和分布式系统经验。

# 沟通风格
- 直接、精确，避免废话
- 给结论时先说结论，再说理由
- 遇到不确定的事情明确说"我不确定"，不猜测

# 边界
- 只处理技术问题
- 不发表政治观点
- 不讨论竞争对手产品
```

**AGENTS.md —— 行为规程（按需更新）**

```markdown
# 工具使用约定
- 修改文件前先用 read 确认当前内容
- exec 执行前先说明要执行什么
- 写入输出文件后告知完成路径

# 记忆策略
- 会话开始时读取 memory/今天.md 和 memory/昨天.md
- 会话结束时将重要信息写入今天的记忆文件

# 输出格式
- 代码用代码块包裹并标注语言
- 重要决策用 > ⚠️ 标注
```

**USER.md —— 用户画像（个性化）**

```markdown
# 对话方信息
- 称呼：阿明
- 技术背景：Python 熟练，不熟悉 Rust
- 工作节奏：上午专注，下午会议多，尽量简洁

# 偏好
- 喜欢代码示例多于文字描述
- 遇到问题先给解决方案，不要先问"你确定要这样吗"
```

**IDENTITY.md —— Agent 标识**

```markdown
name: 架构师 Arc
emoji: 🏗️
description: 专注系统设计与代码质量
```

### 4.2 Skills 的分层设计

Skills 是 Agent 处理特定任务的"肌肉记忆"。OpenClaw 支持三个级别的 skill 作用域：

```
优先级从高到低：
1. ~/.openclaw/workspace-<agentId>/skills/  （Agent 专属，仅该 Agent 可用）
2. ~/.openclaw/skills/                       （全局共享，所有 Agent 可用）
3. 内置/安装的 skill                         （通过 openclaw skills install 安装）
```

Skill 的核心是 `SKILL.md` 文件，它会被注入到系统提示词里告诉 Agent 如何使用这个能力：

```markdown
# SKILL: code-review

## 触发条件
当用户要求审查代码时使用本 skill。

## 审查清单
1. 逻辑正确性：是否有 off-by-one 错误、边界条件遗漏
2. 安全问题：SQL 注入、XSS、不安全的反序列化
3. 性能：O(n²) 以上的算法是否有优化空间
4. 可读性：变量命名、函数长度、注释必要性

## 输出格式
### 🔴 严重问题（必须修复）
### 🟡 建议改进（可选）
### ✅ 做得好的地方
```

### 4.3 模型选型策略

不同角色用不同模型，在能力和成本之间取得平衡：

```json
{
  "agents": {
    "list": [
      {
        "id": "architect",
        "model": {
          "primary": "bailian/qwen3-max-2026-01-23",
          "fallbacks": ["minimax/MiniMax-M2.5"]
        }
      },
      {
        "id": "tester",
        "model": {
          "primary": "deepseek/deepseek-chat",
          "fallbacks": ["minimax/MiniMax-M2.1"]
        }
      },
      {
        "id": "summarizer",
        "model": {
          "primary": "deepseek/deepseek-chat"
        }
      }
    ]
  }
}
```

| Agent 类型  | 推荐策略            | 原因           |
| --------- | --------------- | ------------ |
| 需求分析、架构设计 | 最强模型            | 需要深度推理       |
| 编码实现      | 强模型 + reasoning | 代码生成质量优先     |
| 代码审查      | 中等模型            | 检查规则导向，不需要最强 |
| 测试执行      | 便宜模型            | 任务明确，指令跟随即可  |
| 通知/总结     | 最便宜模型           | 简单格式化任务      |

### 4.4 Context Compaction（上下文压缩）策略

随着对话变长，上下文窗口会被撑满。OpenClaw 的 compaction 机制会自动压缩旧对话，但你可以控制触发行为：

```json
{
  "agents": {
    "defaults": {
      "compaction": {
        "mode": "safeguard"
      }
    }
  }
}
```

对于群组 Agent，建议让会话历史自然滚动，并通过 `historyLimit` 控制注入的历史深度：

```json
{
  "channels": {
    "telegram": {
      "historyLimit": 30,
      "groups": {
        "-100111111111": {
          "historyLimit": 50
        }
      }
    }
  }
}
```

---

## 第五章：协同机制详解

### 5.1 三种 Agent 间通信模式

OpenClaw 提供三种不同抽象层次的 Agent 间通信：

#### 模式 A：sessions_send（点对点消息）

直接向另一个 Agent 的 Session 发消息，可以同步（等待回复）或异步（fire-and-forget）：

```
sessions_send(
  sessionKey: "agent:coder:main",
  message: "请审查这段代码：...",
  timeoutSeconds: 60    # 0 = fire-and-forget
)
```

**适用场景**：一个 Agent 完成任务后需要通知或委托另一个 Agent。

**注意事项**：

- `sessions_send` 是 ping-pong 模式，目标 Agent 可以回复，最多 `session.agentToAgent.maxPingPongTurns`（默认 5）次来回
- 之后会有 announce 步骤，目标 Agent 的结果会反馈给发起方
- 回复 `REPLY_SKIP` 停止 ping-pong，回复 `ANNOUNCE_SKIP` 静默 announce

#### 模式 B：sessions_spawn（动态子 Agent）

让当前 Agent 创建一个临时子 Agent 来完成子任务：

```
sessions_spawn(
  task: "分析这份需求文档并提取功能点列表",
  agentId: "analyst",
  runTimeoutSeconds: 300,
  model: "deepseek/deepseek-chat"
)
```

**适用场景**：主 Agent 遇到需要专业能力的子任务，临时委托给专家子 Agent。

**限制**：

- 默认最大嵌套深度为 1（子 Agent 不能再 spawn 子 Agent），最大允许 2
- 全局并发受 `subagents.maxConcurrent` 控制
- 子 Agent 完成后自动归档

#### 模式 C：Lobster 工作流（确定性编排）

当流程需要多步骤、有条件分支、有循环时，用 Lobster 工作流文件来编排，而不是让 LLM 自己决定下一步：

```yaml
steps:
  - id: analyze
    command: openclaw.invoke --tool agent-send ...
  - id: code
    command: openclaw.invoke --tool agent-send ...
    condition: $analyze.exitCode == 0
  - id: test
    command: openclaw.invoke --tool agent-send ...
    condition: $code.exitCode == 0
```

**这是最重要的设计原则**：LLM 擅长创造性工作，不擅长可靠的流程控制。复杂工作流的编排应该交给代码（Lobster），而不是 Prompt。

### 5.2 agentToAgent 的配置与安全边界

Agent 间通信默认关闭，需要显式启用并配置 allowlist：

```json
{
  "agents": {
    "defaults": {
      "tools": {
        "agentToAgent": {
          "enabled": true,
          "allow": ["analyst", "coder", "tester"]
        }
      }
    }
  },
  "session": {
    "agentToAgent": {
      "maxPingPongTurns": 3
    }
  }
}
```

> ⚠️ **安全提示**：`agentToAgent.allow` 是白名单，控制当前 Agent 可以向哪些其他 Agent 发消息。如果某个 Agent 可能处理不可信内容（例如爬取的网页），要严格限制它的 agentToAgent 权限，防止 Prompt Injection 攻击通过 sessions_send 扩散。

### 5.3 共享项目目录（产物传递的物理基础）

多个 Agent 之间传递工作产物最可靠的方式是通过**文件系统上的共享目录**，而不是通过 sessions_send 传递大量文本。

原理：Agent 的 Workspace 是隔离的，但每个 Agent 的 `tools.allow` 包含 `read`/`write` 时，它可以通过**绝对路径**访问宿主机上的任意目录。

```
Agent A（analyst）写入：    ~/projects/auth/requirements.md
Agent B（coder）读取：      ~/projects/auth/requirements.md
Agent C（tester）只读：     ~/projects/auth/src/
```

这种模式的好处是：

- 产物有持久化记录，方便人工审查
- 大文件（代码库、规格文档）不需要通过 sessions_send 传输
- Agent 只读自己"上游"的文件，边界清晰

**项目目录结构规范**：

```
~/projects/<project-name>/
├── .meta/
│   ├── pipeline.json        # 当前 pipeline 状态（由 Lobster 写入）
│   └── log.md               # 各 Agent 操作日志
├── requirements.md          # analyst 写入
├── ui-spec.md               # ui-designer 写入
├── architecture.md          # architect 写入
├── src/                     # coder 写入
│   ├── main.py
│   └── tests/
├── review-notes.md          # reviewer 写入（可能有多轮）
└── test-report.md           # tester 写入
```

---

## 第六章：工作流的三种模式

### 6.1 模式一：即时响应（无工作流）

最简单的场景，用户发消息，Agent 处理，回复。适合：

- 日常 QA 对话
- 即时任务（写一段代码、改一个文档）
- 不需要跨 Agent 协作的单步任务

```
用户 → Telegram 群组 → [routing] → Agent → 直接回复
```

配置要点：bindings 正确，群组权限设置好，无需额外配置。

### 6.2 模式二：Agent 自主委托（半结构化）

Agent 在处理任务过程中，自己判断何时需要调用其他 Agent，通过 `sessions_send` 或 `sessions_spawn` 实现。适合：

- 主 Agent 能力主要，子任务偶发
- 流程本身不固定，需要 Agent 灵活判断
- 任务复杂度中等

```
用户 → 主 Agent
         └── 发现需要代码审查
               └── sessions_spawn(agentId: "reviewer")
                     └── 完成后 announce 给主 Agent
                           └── 主 Agent 综合回复用户
```

配置要点：

```json
{
  "agents": {
    "list": [
      {
        "id": "main",
        "tools": {
          "allow": ["sessions_spawn", "sessions_send", "sessions_list"]
        }
      }
    ],
    "defaults": {
      "subagents": {
        "maxConcurrent": 4,
        "runTimeoutSeconds": 300,
        "archiveAfterMinutes": 60
      }
    }
  }
}
```

### 6.3 模式三：Lobster 确定性工作流（完全结构化）

流程完全由 Lobster YAML 文件定义，LLM 不参与流程决策，只负责每个步骤内的内容生成。适合：

- 有明确阶段和顺序依赖的流程
- 需要循环（审查-修改-再审查）
- 需要条件分支（测试通过才部署）
- 需要并行执行（多个 Agent 同时工作）

```
用户触发 → Lobster 工作流引擎
              ├── Step 1: 调用 analyst    (输出: requirements.md)
              ├── Step 2: 调用 architect  (输出: architecture.md)
              ├── Step 3: Loop(最多3轮)
              │     ├── 调用 coder       (输出: src/)
              │     └── 调用 reviewer    (输出: review-notes.md)
              │           └── 判断: approved? 继续 : 下一轮
              ├── Step 4: 调用 tester    (输出: test-report.md)
              └── Step 5: 发送通知
```

**Lobster 的 condition 系统**（基于 shell 命令的确定性判断）：

```yaml
# 只在上一步成功时继续
condition: $prev-step.exitCode == 0

# 根据 JSON 输出判断
condition: '! echo "$LOBSTER_LOOP_JSON" | jq -e ".approved"'

# 文件存在性检查
condition: 'test -f ~/projects/${project}/requirements.md'
```

---

## 第七章：完整实战场景——软件研发团队

以下是一个完整的、可运行的配置方案，模拟一个由 AI Agent 组成的软件研发团队。

### 7.1 团队结构设计

```
┌──────────────────────────────────────────────────────────────┐
│                      研发团队 Agent 矩阵                      │
├────────────┬───────────────┬──────────────┬──────────────────┤
│  Agent ID  │  职责         │  工具权限     │  绑定群组         │
├────────────┼───────────────┼──────────────┼──────────────────┤
│ orchestr   │ 任务协调/派发  │ sessions 全集 │ 控制台群组        │
│ analyst    │ 需求分析       │ read,write,  │ 协作群组 Topic101 │
│            │               │ browser,     │                  │
│            │               │ web_search   │                  │
│ architect  │ 系统设计       │ read,write,  │ 协作群组 Topic102 │
│            │               │ browser      │                  │
│ coder      │ 编码实现       │ read,write,  │ 协作群组 Topic103 │
│            │               │ exec,patch   │                  │
│ reviewer   │ 代码审查       │ read (只读)  │ 协作群组 Topic104 │
│ tester     │ 测试执行       │ read,exec    │ 协作群组 Topic105 │
│ notifier   │ 通知/报告      │ message      │ 通知群组          │
└────────────┴───────────────┴──────────────┴──────────────────┘
```

### 7.2 Step-by-Step：完整配置

**Step 1：初始化所有 Workspace**

```bash
# 创建各 Agent workspace
for agent in orchestrator analyst architect coder reviewer tester notifier; do
  mkdir -p ~/.openclaw/workspace-$agent/skills
  mkdir -p ~/.openclaw/workspace-$agent/memory
done

# 创建共享项目目录
mkdir -p ~/projects
```

**Step 2：编写 SOUL.md（以 coder 为例）**

```bash
cat > ~/.openclaw/workspace-coder/SOUL.md << 'EOF'
# 你是谁
你是一位资深全栈工程师，专注于编写高质量、可维护的代码。

# 行事风格
- 代码优先于解释：先给代码，再解释
- 明确声明依赖：列出所需的包和版本
- 错误处理是标配：每个可能失败的操作都要有错误处理
- 注释写"为什么"而不是"是什么"

# 你的限制
- 不做架构层面的设计决策（这是 architect 的职责）
- 不运行破坏性命令（DROP TABLE、rm -rf 等）
- 不提交代码（git 操作由 orchestrator 统一管理）
EOF
```

**Step 3：编写 AGENTS.md（以 coder 为例）**

```bash
cat > ~/.openclaw/workspace-coder/AGENTS.md << 'EOF'
# 工作流程

## 接收任务
1. 读取 ~/projects/<project>/architecture.md 了解系统设计
2. 读取 ~/projects/<project>/ui-spec.md 了解接口规范
3. 如果有上一轮 review，读取 ~/projects/<project>/review-notes.md

## 编码输出
- 代码输出到 ~/projects/<project>/src/
- 每个文件顶部写模块说明注释
- 依赖列表写入 ~/projects/<project>/src/requirements.txt 或 package.json

## 完成标志
- 写入完成后，输出最后一行：`DONE: src/ 已更新`

# 记忆约定
- 每次会话结束前，将本次处理的项目名写入 memory/今天.md
EOF
```

**Step 4：完整 openclaw.json 配置**

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "bailian/qwen3-max-2026-01-23",
        "fallbacks": ["minimax/MiniMax-M2.5", "deepseek/deepseek-reasoner"]
      },
      "maxConcurrent": 4,
      "subagents": {
        "maxConcurrent": 8,
        "runTimeoutSeconds": 600,
        "archiveAfterMinutes": 120
      },
      "compaction": { "mode": "safeguard" },
      "tools": {
        "agentToAgent": {
          "enabled": true,
          "allow": ["orchestrator", "analyst", "architect", "coder", "reviewer", "tester", "notifier"]
        }
      }
    },
    "list": [
      {
        "id": "orchestrator",
        "workspace": "~/.openclaw/workspace-orchestrator",
        "identity": { "name": "协调员 Orchy", "emoji": "🎯" },
        "model": { "primary": "bailian/qwen3-max-2026-01-23" },
        "tools": {
          "allow": [
            "read", "write",
            "sessions_send", "sessions_spawn", "sessions_list", "sessions_history",
            "message", "cron", "gateway"
          ]
        }
      },
      {
        "id": "analyst",
        "workspace": "~/.openclaw/workspace-analyst",
        "identity": { "name": "需求专家 Ana", "emoji": "🔍" },
        "model": { "primary": "bailian/qwen3-max-2026-01-23" },
        "tools": {
          "allow": ["read", "write", "browser", "web_search"],
          "deny": ["exec", "gateway", "cron"]
        }
      },
      {
        "id": "architect",
        "workspace": "~/.openclaw/workspace-architect",
        "identity": { "name": "架构师 Arc", "emoji": "🏗️" },
        "model": { "primary": "bailian/qwen3-max-2026-01-23" },
        "tools": {
          "allow": ["read", "write", "browser"],
          "deny": ["exec", "gateway", "cron"]
        }
      },
      {
        "id": "coder",
        "workspace": "~/.openclaw/workspace-coder",
        "identity": { "name": "工程师 Code", "emoji": "💻" },
        "model": { "primary": "bailian/qwen3-max-2026-01-23" },
        "tools": {
          "allow": ["read", "write", "exec", "apply_patch", "process"],
          "deny": ["browser", "gateway", "cron", "sessions_spawn"]
        }
      },
      {
        "id": "reviewer",
        "workspace": "~/.openclaw/workspace-reviewer",
        "identity": { "name": "审查员 Rev", "emoji": "🔬" },
        "model": { "primary": "deepseek/deepseek-reasoner" },
        "tools": {
          "allow": ["read"],
          "deny": ["write", "exec", "edit", "apply_patch", "browser", "gateway"]
        }
      },
      {
        "id": "tester",
        "workspace": "~/.openclaw/workspace-tester",
        "identity": { "name": "测试员 Test", "emoji": "🧪" },
        "model": { "primary": "deepseek/deepseek-chat" },
        "tools": {
          "allow": ["read", "exec", "process"],
          "deny": ["write", "edit", "apply_patch", "browser", "gateway"]
        }
      },
      {
        "id": "notifier",
        "workspace": "~/.openclaw/workspace-notifier",
        "identity": { "name": "通知员 Noti", "emoji": "📢" },
        "model": { "primary": "deepseek/deepseek-chat" },
        "tools": {
          "allow": ["message", "read"],
          "deny": ["write", "exec", "browser", "gateway"]
        }
      }
    ],
    "bindings": [
      {
        "agentId": "orchestrator",
        "match": { "channel": "telegram", "peer": { "kind": "group", "id": "-100100000001" } }
      },
      {
        "agentId": "analyst",
        "match": { "channel": "telegram", "peer": { "kind": "group", "id": "-100100000002" } }
      },
      {
        "agentId": "architect",
        "match": { "channel": "telegram", "peer": { "kind": "group", "id": "-100100000003" } }
      },
      {
        "agentId": "coder",
        "match": { "channel": "telegram", "peer": { "kind": "group", "id": "-100100000004" } }
      },
      {
        "agentId": "reviewer",
        "match": { "channel": "telegram", "peer": { "kind": "group", "id": "-100100000005" } }
      },
      {
        "agentId": "tester",
        "match": { "channel": "telegram", "peer": { "kind": "group", "id": "-100100000006" } }
      }
    ]
  },
  "session": {
    "dmScope": "per-channel-peer",
    "resetByType": {
      "group": { "mode": "idle", "idleMinutes": 120 },
      "direct": { "mode": "idle", "idleMinutes": 480 }
    },
    "agentToAgent": { "maxPingPongTurns": 3 }
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "YOUR_BOT_TOKEN",
      "dmPolicy": "pairing",
      "groupPolicy": "allowlist",
      "groupAllowFrom": [123456789],
      "streaming": "partial",
      "historyLimit": 30,
      "groups": {
        "-100100000001": {
          "groupPolicy": "allowlist",
          "allowFrom": [123456789],
          "requireMention": false,
          "systemPrompt": "这是控制台群组，可以执行所有管理操作"
        },
        "-100100000002": {
          "requireMention": true,
          "systemPrompt": "需求分析群组，专注需求澄清与文档输出"
        },
        "-100100000003": {
          "requireMention": true,
          "systemPrompt": "架构设计群组，专注系统设计与技术选型"
        },
        "-100100000004": {
          "requireMention": true,
          "systemPrompt": "编码实现群组，专注代码编写与调试"
        },
        "-100100000005": {
          "requireMention": true,
          "systemPrompt": "代码审查群组，只读模式，输出审查报告"
        },
        "-100100000006": {
          "requireMention": true,
          "systemPrompt": "测试执行群组，执行测试并输出报告"
        },
        "-100100000099": {
          "enabled": false
        }
      }
    }
  },
  "messages": {
    "ackReactionScope": "group-mentions"
  }
}
```

**Step 5：Lobster 工作流文件**

创建 `~/.openclaw/workflows/dev-pipeline.lobster`：

```yaml
name: dev-pipeline
description: 完整软件研发流水线

args:
  project:     { required: true,  description: "项目名称（用于目录和 sessionKey）" }
  requirement: { required: true,  description: "原始需求描述" }
  chat_id:     { required: true,  description: "通知发送到哪个 Telegram Chat ID" }

steps:
  # ─── 初始化项目目录 ────────────────────────────────
  - id: init
    command: |
      mkdir -p ~/projects/${project}/src
      mkdir -p ~/projects/${project}/.meta
      echo "{ \"startedAt\": \"$(date -Iseconds)\", \"requirement\": \"${requirement}\" }" \
        > ~/projects/${project}/.meta/pipeline.json
      echo "## Pipeline 启动：$(date)" > ~/projects/${project}/.meta/log.md

  # ─── Step 1: 需求分析 ──────────────────────────────
  - id: analysis
    command: >
      openclaw.invoke --tool agent-send --args-json '{
        "agentId": "analyst",
        "message": "项目「${project}」需求分析任务。\n\n原始需求：${requirement}\n\n请分析并输出到 ~/projects/${project}/requirements.md",
        "sessionKey": "pipeline:${project}:analyst"
      }'
    condition: $init.exitCode == 0

  # ─── Step 2: 系统设计 ──────────────────────────────
  - id: architecture
    command: >
      openclaw.invoke --tool agent-send --args-json '{
        "agentId": "architect",
        "message": "项目「${project}」系统设计任务。\n\n请读取 ~/projects/${project}/requirements.md 并输出系统架构设计到 ~/projects/${project}/architecture.md",
        "sessionKey": "pipeline:${project}:architect"
      }'
    condition: $analysis.exitCode == 0

  # ─── Step 3: 编码 + 审查循环（最多 3 轮）──────────
  - id: coding-loop
    lobster: ./coding-review.lobster
    args:
      project: ${project}
    loop:
      maxIterations: 3
      condition: '! echo "$LOBSTER_LOOP_JSON" | jq -e ".approved // false" > /dev/null 2>&1'
    condition: $architecture.exitCode == 0

  # ─── Step 4: 回归测试 ──────────────────────────────
  - id: testing
    command: >
      openclaw.invoke --tool agent-send --args-json '{
        "agentId": "tester",
        "message": "项目「${project}」测试任务。\n\n请对 ~/projects/${project}/src/ 执行回归测试，参照 ~/projects/${project}/requirements.md 验收标准，输出报告到 ~/projects/${project}/test-report.md",
        "sessionKey": "pipeline:${project}:tester"
      }'
    condition: $coding-loop.json.approved == true

  # ─── Step 5: 完成通知 ──────────────────────────────
  - id: notify-success
    command: >
      openclaw.invoke --tool message --action send --args-json '{
        "provider": "telegram",
        "to": "${chat_id}",
        "text": "✅ 项目「${project}」研发流水线完成！\n\n📋 需求文档：~/projects/${project}/requirements.md\n🏗️ 架构文档：~/projects/${project}/architecture.md\n💻 代码目录：~/projects/${project}/src/\n🧪 测试报告：~/projects/${project}/test-report.md"
      }'
    condition: $testing.exitCode == 0

  # ─── 失败通知 ──────────────────────────────────────
  - id: notify-failure
    command: >
      openclaw.invoke --tool message --action send --args-json '{
        "provider": "telegram",
        "to": "${chat_id}",
        "text": "❌ 项目「${project}」流水线失败，请检查日志"
      }'
    condition: $testing.exitCode != 0
```

创建 `~/.openclaw/workflows/coding-review.lobster`：

```yaml
name: coding-review
description: 编码-审查子流程（支持循环）

args:
  project: { required: true }

steps:
  # 编码
  - id: code
    command: >
      openclaw.invoke --tool agent-send --args-json '{
        "agentId": "coder",
        "message": "项目「${project}」编码任务（第 $LOBSTER_LOOP_ITERATION 轮）。\n\n请读取 ~/projects/${project}/architecture.md 和 ~/projects/${project}/ui-spec.md 实现代码，输出到 ~/projects/${project}/src/",
        "sessionKey": "pipeline:${project}:coder"
      }'

  # 代码审查（输出结构化 JSON）
  - id: review
    command: >
      openclaw.invoke --tool llm-task --action json --args-json '{
        "prompt": "作为代码审查专家，检查 ~/projects/${project}/src/ 目录下的代码是否符合 ~/projects/${project}/architecture.md 的设计要求。严格返回 JSON：{\"approved\": bool, \"issues\": [\"问题1\",\"问题2\"], \"feedback\": \"改进建议\"}",
        "schema": {
          "type": "object",
          "properties": {
            "approved":  { "type": "boolean" },
            "issues":    { "type": "array", "items": { "type": "string" } },
            "feedback":  { "type": "string" }
          },
          "required": ["approved", "feedback"]
        }
      }'
    stdin: $code.stdout

  # 将审查结果写入文件（供下一轮 coder 参考）
  - id: save-review
    command: |
      echo "# 第 $LOBSTER_LOOP_ITERATION 轮审查结果" >> ~/projects/${project}/review-notes.md
      echo "$LOBSTER_LOOP_JSON" | jq -r '.feedback' >> ~/projects/${project}/review-notes.md
      echo "" >> ~/projects/${project}/review-notes.md
```

**Step 6：触发工作流**

```bash
# 在控制台群组里发送（orchestrator agent 接收）
/run-pipeline project=user-auth requirement="实现用户注册、登录、找回密码功能，支持手机号和邮箱两种方式"

# 或者直接通过 CLI 触发
curl -X POST http://127.0.0.1:18789/hooks/agent \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "启动流水线 project=user-auth requirement=实现用户认证系统",
    "agentId": "orchestrator",
    "sessionKey": "pipeline:user-auth:orchestrator",
    "deliver": false
  }'
```

---

## 第八章：安全边界与权限设计

### 8.1 工具权限最小化原则

每个 Agent 只应获得完成其职责所需的最小工具集：

```
orchestrator: sessions_send + sessions_spawn + message + cron  (编排，不执行)
analyst:      read + write + browser + web_search              (查资料，写文档)
architect:    read + write + browser                            (设计，不执行代码)
coder:        read + write + exec + apply_patch                (执行，不管理 gateway)
reviewer:     read only                                         (只读，绝不修改)
tester:       read + exec                                       (运行测试，不修改源码)
notifier:     message only                                      (只发消息)
```

### 8.2 防止 Prompt Injection 扩散

当 Agent 会处理外部内容（网页、用户上传的文件）时，要严格限制其 agentToAgent 权限：

```json
{
  "agents": {
    "list": [
      {
        "id": "web-researcher",
        "tools": {
          "allow": ["browser", "web_search", "read", "write"],
          "deny": ["sessions_send", "sessions_spawn", "exec", "gateway"]
        }
      }
    ]
  }
}
```

> ⚠️ 如果 web-researcher 可以使用 sessions_send，一个恶意网页可以通过 Prompt Injection 让它向其他 Agent 发送攻击指令。

### 8.3 沙箱化群组会话

对于所有群组（非主会话），建议开启沙箱模式：

```json
{
  "agents": {
    "defaults": {
      "sandbox": {
        "mode": "non-main",
        "scope": "agent"
      }
    },
    "list": [
      {
        "id": "main",
        "sandbox": { "mode": "off" }
      }
    ]
  }
}
```

这样主会话（你的私人 DM）保持完全权限，而所有群组会话都在沙箱内运行。

### 8.4 Workspace Git 备份（防止记忆丢失）

```bash
# 为每个 Agent workspace 建立私有 git 仓库
for agent in orchestrator analyst architect coder reviewer tester; do
  cd ~/.openclaw/workspace-$agent
  git init
  git add AGENTS.md SOUL.md IDENTITY.md USER.md TOOLS.md memory/ skills/
  git commit -m "Initial workspace for $agent"

  # 推送到私有仓库（替换为你的仓库地址）
  git remote add origin git@github.com:yourname/openclaw-workspace-$agent.git
  git push -u origin main
done
```

`.gitignore` 建议：

```
.DS_Store
.env
**/*.key
**/*.pem
**/secrets*
BOOTSTRAP.md
```

---

## 第九章：运维与可观测性

### 9.1 Session Key 作为调试坐标

Session Key 是 OpenClaw 最重要的调试工具。所有日志、历史查询都以它为索引：

```bash
# 实时追踪特定 pipeline 的执行
openclaw logs --follow | grep "pipeline:user-auth"

# 查看特定 Agent 在某个 project 的完整历史
openclaw sessions history pipeline:user-auth:coder --limit 50

# 查看所有活跃 session
openclaw sessions list --activeMinutes 60
```

### 9.2 会话维护策略

避免 sessions.json 无限增长：

```json
{
  "session": {
    "maintenance": {
      "mode": "enforce",
      "pruneAfter": "30d",
      "maxEntries": 500,
      "rotateBytes": "10mb",
      "maxDiskBytes": "500mb"
    }
  }
}
```

### 9.3 Heartbeat：Agent 主动健康检查

给关键 Agent 配置 Heartbeat，让它定期主动汇报状态：

```json
{
  "agents": {
    "defaults": {
      "heartbeat": {
        "every": "4h",
        "sessionKey": "heartbeat"
      }
    }
  }
}
```

在 Workspace 的 `HEARTBEAT.md` 里定义检查内容：

```markdown
# Heartbeat 任务
1. 检查 ~/projects/ 目录下有无未完成的 pipeline（.meta/pipeline.json status != "done"）
2. 如有未完成的，发送 message 通知 Telegram chat_id=-100100000099
3. 将检查结果写入 memory/今天.md
```

### 9.4 Cron：定时自动化任务

```json
{
  "cron": {
    "enabled": true,
    "maxConcurrentRuns": 2,
    "sessionRetention": "24h"
  }
}
```

在控制台群组发送：

```
/cron add "0 9 * * MON" "project=weekly-report: 生成上周研发进度报告"
```

---

## 附录：配置速查

### Agent 角色与工具权限参考

| 角色               | allow                                                                    | deny                                             |
| ---------------- | ------------------------------------------------------------------------ | ------------------------------------------------ |
| 协调者/Orchestrator | sessions_send, sessions_spawn, sessions_list, message, cron, read, write | exec, browser, gateway（视需要开放）                    |
| 研究者/Analyst      | read, write, browser, web_search                                         | exec, gateway, sessions_spawn                    |
| 设计者/Architect    | read, write, browser                                                     | exec, gateway                                    |
| 编码者/Coder        | read, write, exec, apply_patch, process                                  | browser, gateway, cron                           |
| 审查者/Reviewer     | read                                                                     | write, exec, edit, apply_patch, browser, gateway |
| 测试者/Tester       | read, exec                                                               | write, edit, apply_patch, browser, gateway       |
| 通知者/Notifier     | message, read                                                            | write, exec, browser, gateway                    |

### Session Key 命名约定

| 场景             | 格式                          | 示例                              |
| -------------- | --------------------------- | ------------------------------- |
| Pipeline Agent | `pipeline:<project>:<role>` | `pipeline:auth-module:coder`    |
| Webhook 触发     | `hook:<project>:<role>`     | `hook:auth-module:orchestrator` |
| 定时任务           | `cron:<job-name>`           | `cron:weekly-report`            |
| 私有测试           | `test:<name>`               | `test:new-skill`                |

### 群组模式速查

| 群组模式 | groupPolicy | requireMention | 用途          |
| ---- | ----------- | -------------- | ----------- |
| 控制台  | allowlist   | false          | 你自己操作       |
| 团队协作 | open        | true           | 多人 @ 触发     |
| 专家频道 | allowlist   | true           | 特定人员调用专家    |
| 通知频道 | disabled    | —              | 只收 Agent 推送 |
| 沙箱测试 | allowlist   | true           | 测试新配置       |

### 常用 CLI 命令

```bash
openclaw gateway                                   # 启动网关
openclaw logs --follow                             # 实时日志
openclaw logs --follow | grep "sessionKey"         # 过滤特定 session
openclaw sessions list --activeMinutes 30          # 查看活跃 session
openclaw sessions history <sessionKey> --limit 20  # 查看会话历史
openclaw sessions clear <sessionKey>               # 清除 session
openclaw pairing list telegram                     # 查看配对列表
openclaw channels status                           # 渠道状态检查
openclaw channels status --probe                   # 深度检查（含群组探测）
openclaw doctor                                    # 配置诊断
openclaw doctor --fix                              # 自动修复（如 @username 转 ID）
openclaw skills list                               # 列出已安装 skill
openclaw skills install @openclaw/<skill-name>     # 安装 skill
```

---

> 📌 **版本说明**：本文档基于 OpenClaw v2026.2.x 编写。Lobster loop 功能（`loop.maxIterations`）需要 PR #20 合并后的版本。如有变化，以官方文档 [docs.openclaw.ai](https://docs.openclaw.ai) 为准。
> 
> 💾 **Workspace 备份提醒**：Agent 的记忆和人格定义都在 Workspace 里，记得定期 `git push`。
