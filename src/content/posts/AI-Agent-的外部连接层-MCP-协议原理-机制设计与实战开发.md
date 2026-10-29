---
title: "AI Agent 的外部连接层：MCP 协议原理、机制设计与实战开发"
date: 2026-03-12
description: "本文从为什么需要 MCP 讲起，逐步拆解其三角色架构、三大能力原语、传输方式与连接生命周期，再通过一个 *Python 实战案例带你从零搭建可运行的 MCP Server。"
tags: []
category: "技术"
source: "https://juejin.cn/post/7616025751747182598"
---
> 当我们让 AI 助手"查一下知识库"或"在 Jira 上建个工单"时，背后需要一套标准方式让 AI 与外部工具对话——这就是 **MCP（Model Context Protocol）** 要解决的问题。它的定位类似于 AI 世界的"USB 接口"：工具开发者按协议实现一次 Server，所有支持 MCP 的 AI 应用即可即插即用，告别"每换一个平台就重写集成代码"的困境。
>
> 本文从**为什么需要 MCP** 讲起，逐步拆解其三角色架构、三大能力原语、传输方式与连接生命周期，再通过一个 **Python 实战案例**带你从零搭建可运行的 MCP Server。读完你将理解：AI Agent 是如何通过 MCP 协议"长出手脚"、安全地操作外部世界的。

---

## 目录

1. [MCP 是什么，解决了什么问题](#1-mcp-%E6%98%AF%E4%BB%80%E4%B9%88%E8%A7%A3%E5%86%B3%E4%BA%86%E4%BB%80%E4%B9%88%E9%97%AE%E9%A2%98 "#1-mcp-%E6%98%AF%E4%BB%80%E4%B9%88%E8%A7%A3%E5%86%B3%E4%BA%86%E4%BB%80%E4%B9%88%E9%97%AE%E9%A2%98")
2. [MCP 整体架构：三个角色，一套标准](#2-mcp-%E6%95%B4%E4%BD%93%E6%9E%B6%E6%9E%84%E4%B8%89%E4%B8%AA%E8%A7%92%E8%89%B2%E4%B8%80%E5%A5%97%E6%A0%87%E5%87%86 "#2-mcp-%E6%95%B4%E4%BD%93%E6%9E%B6%E6%9E%84%E4%B8%89%E4%B8%AA%E8%A7%92%E8%89%B2%E4%B8%80%E5%A5%97%E6%A0%87%E5%87%86")
3. [协议基石：JSON-RPC 2.0](#3-%E5%8D%8F%E8%AE%AE%E5%9F%BA%E7%9F%B3json-rpc-20 "#3-%E5%8D%8F%E8%AE%AE%E5%9F%BA%E7%9F%B3json-rpc-20")
4. [协议核心：三大能力原语](#4-%E5%8D%8F%E8%AE%AE%E6%A0%B8%E5%BF%83%E4%B8%89%E5%A4%A7%E8%83%BD%E5%8A%9B%E5%8E%9F%E8%AF%AD "#4-%E5%8D%8F%E8%AE%AE%E6%A0%B8%E5%BF%83%E4%B8%89%E5%A4%A7%E8%83%BD%E5%8A%9B%E5%8E%9F%E8%AF%AD")
5. [传输层：消息怎么送达？](#5-%E4%BC%A0%E8%BE%93%E5%B1%82%E6%B6%88%E6%81%AF%E6%80%8E%E4%B9%88%E9%80%81%E8%BE%BE "#5-%E4%BC%A0%E8%BE%93%E5%B1%82%E6%B6%88%E6%81%AF%E6%80%8E%E4%B9%88%E9%80%81%E8%BE%BE")
6. [连接生命周期：从握手到断开](#6-%E8%BF%9E%E6%8E%A5%E7%94%9F%E5%91%BD%E5%91%A8%E6%9C%9F%E4%BB%8E%E6%8F%A1%E6%89%8B%E5%88%B0%E6%96%AD%E5%BC%80 "#6-%E8%BF%9E%E6%8E%A5%E7%94%9F%E5%91%BD%E5%91%A8%E6%9C%9F%E4%BB%8E%E6%8F%A1%E6%89%8B%E5%88%B0%E6%96%AD%E5%BC%80")
7. [实战：用 Python 开发一个 MCP Server](#7-%E5%AE%9E%E6%88%98%E7%94%A8-python-%E5%BC%80%E5%8F%91%E4%B8%80%E4%B8%AA-mcp-server "#7-%E5%AE%9E%E6%88%98%E7%94%A8-python-%E5%BC%80%E5%8F%91%E4%B8%80%E4%B8%AA-mcp-server")
8. [安全最佳实践](#8-%E5%AE%89%E5%85%A8%E6%9C%80%E4%BD%B3%E5%AE%9E%E8%B7%B5 "#8-%E5%AE%89%E5%85%A8%E6%9C%80%E4%BD%B3%E5%AE%9E%E8%B7%B5")
9. [MCP vs Function Calling vs 直接 CLI 调用](#9-mcp-vs-function-calling-vs-%E7%9B%B4%E6%8E%A5-cli-%E8%B0%83%E7%94%A8 "#9-mcp-vs-function-calling-vs-%E7%9B%B4%E6%8E%A5-cli-%E8%B0%83%E7%94%A8")
10. [常见问题 FAQ](#10-%E5%B8%B8%E8%A7%81%E9%97%AE%E9%A2%98-faq "#10-%E5%B8%B8%E8%A7%81%E9%97%AE%E9%A2%98-faq")

---

## 1. MCP 是什么，解决了什么问题

### 1.1 LLM 能做什么，不能做什么

大语言模型（LLM）的本质是一个概率预测器。训练时，它从海量文本中学习语言规律和知识——给定一段输入，预测下一个最合理的 token，不断重复，就生成了连贯的输出。这个过程让它能够理解语义、推理逻辑、写代码、归纳总结，表现出很强的通用能力。

但这套机制也决定了它有几条硬性的边界。

**知识是静态的。** 训练完成之后，模型的参数就固定下来了，它的"知识"是训练截止日期之前的文本快照。它不知道今天的新闻，不了解你公司内部的数据，也不清楚你的代码库里昨天发生了什么。

**没有记忆，没有状态。** 每次对话都是全新开始，上下文只存在于当前的 context window 里，窗口之外的内容它完全不知道。它无法主动"记住"什么，也没有持久化存储。

**只能输出文字，无法执行操作。** LLM 的输出是 token 序列，它能写出"删除这条记录"的 SQL，但无法真正连接数据库执行它；它能给出"发送邮件"的步骤，但没有办法自己点击发送按钮。

这三条限制叠在一起，意味着单独的 LLM 更像一个博学的顾问——能分析、能建议、能解释，但所有的实际动作还是要人来做。

**Agent：让 LLM 从"说"变成"做"**

为了突破这些限制，AI Agent 的概念应运而生。Agent 的核心思路是给 LLM 配上工具：让它不只是输出文字，而是能调用函数、读取数据、执行操作，然后根据结果继续推理，形成一个"感知 → 思考 → 行动"的循环。

```
flowchart TD
    A["用户输入"] --> B["LLM 推理"]
    B -->|"输出结构化指令：'调用 query_db，参数 { sql: SELECT ... }'"| C["Agent（如 Claude Desktop、LangChain、自研框架）"]

    C -->|"解析 LLM 的输出，识别出工具调用意图<br/>代为执行：连接数据库，跑 SQL，拿到结果"| D["执行结果"]

    D -->|"把执行结果以文本形式<br/>重新塞回 LLM 的 context"| E["LLM 读取结果，继续推理"]

    E --> F["输出最终回答"]

    style B fill:#fff3e0
    style C fill:#e8f5e9
```

> ⚠️ **关键理解**：LLM 只是输出了文字，它自己什么都没执行。"调用工具"这个动作，从头到尾都是 Agent 在执行，LLM 只是在用语言表达意图。

LLM 在整个过程中始终只做一件事：根据输入预测输出。"调用工具"这个动作，从头到尾都是 Agent 在执行，LLM 只是在用语言表达意图。这也是为什么工具调用的安全控制要放在 Agent 层而不是模型层——模型管不了，Agent 才能拦截和审计。

但这里又冒出一个新问题：Agent 要调用的工具五花八门——数据库、第三方 API、本地文件系统、内部业务系统——每个工具的接口格式、认证方式、错误处理都不一样。没有统一标准的话，每接一个新工具就要写一套对接代码，换一个 Agent 框架又要重写一遍。这就是 MCP 出现的原因：它定义了 Agent 与外部工具之间通信的统一规范，让工具只需实现一次，任何支持 MCP 的 Agent 都能直接接入。

### 1.2 没有 MCP 之前：M×N 集成地狱

```
graph LR
    subgraph " "
        direction TB
        CP[ChatGPT Plugin] -->|自研集成| N1[Notion]
        CP -->|自研集成| G1[GitHub]
        CP -->|自研集成| J1[Jira]
        CL[Claude] -->|自研集成| N2["Notion ← 重复造轮子"]
        CL -->|自研集成| G2[GitHub]
        CU[Cursor] -->|自研集成| G3["GitHub ← 再造一遍"]
    end

    style CP fill:#ffcdd2
    style CL fill:#c8e6c9
    style CU fill:#bbdefb
```

**M 个 AI 工具 × N 个外部服务 = M×N 套各自为政的集成代码。** 每个 AI 厂商都自己定义调用格式、认证方式、错误处理——生态碎片化严重。

### 1.3 解法：一个标准协议，把 M×N 变成 M+N

**MCP（Model Context Protocol，模型上下文协议）** 就是为了解决这个问题而生的。

它的思路和 **USB** 完全一样——

| 类比 | 没有 USB 的时代 | 有 USB 之后 |
| --- | --- | --- |
| 硬件 | 每个外设一种专用接口（打印口、串口、PS/2……） | 统一 USB 口，即插即用 |
| AI | 每个工具一套专用集成代码 | 统一 MCP 协议，一次适配，处处可用 |

```
有了 MCP 之后：

  Claude  ─┐                ┌──▶ GitHub MCP Server
  ChatGPT ─┤── MCP 协议 ────┤──▶ Jira MCP Server
  Cursor  ─┘                └──▶ 知识库 MCP Server

  3 + 3 = 6 次适配（不再是 9 次）
  每新增一端，只需 +1
```

每个 AI 应用通过 MCP 协议**直接连接**所需的 Server——没有中心化的"总线"或网关，只有一套统一的通信标准。

**3 + 3 = 6 次适配**（不再是 9 次），每新增一端，只需 +1。

有了 MCP：

- **工具开发者**：按 MCP 协议写一个 Server，所有支持 MCP 的 AI 应用都能直接接入。
- **AI 应用开发者**：实现一个 MCP Client，就能接入整个 MCP 生态的所有 Server。

### 1.4 MCP 到底是什么，不是什么

在开始深入之前，先校准一下认知：

| MCP **是** | MCP **不是** |
| --- | --- |
| 一个开放的通信**协议规范**（类似 HTTP、USB） | 一个具体的软件产品或 SDK |
| 基于 JSON-RPC 2.0 的消息格式标准 | 某种编程语言或框架 |
| AI 应用与外部工具之间的"通用翻译层" | AI 模型本身的能力 |
| Anthropic 发起，但完全开源的社区协议 | Anthropic 的私有技术 |

## 2. MCP 整体架构：三个角色，一套标准

理解了"为什么需要 MCP"之后，我们来看它的架构设计。MCP 世界里有三个核心角色：

### 2.1 Host、Client、Server

```
┌─────────────────────────────────────────┐
│              Host（宿主应用）              │
│  例：Claude Desktop / Cursor / 你的应用   │
│                                         │
│  ┌──────────┐  ┌──────────┐             │
│  │ Client A │  │ Client B │  ...        │
│  └────┬─────┘  └────┬─────┘             │
└───────┼──────────────┼──────────────────┘
        │              │
   MCP 协议         MCP 协议
        │              │
   ┌────▼─────┐   ┌────▼─────┐
   │ Server A │   │ Server B │
   │ (GitHub) │   │ (知识库)  │
   └──────────┘   └──────────┘
```

用一个更生活化的类比来理解：

| 角色 | 是什么 | 生活类比 | 典型例子 |
| --- | --- | --- | --- |
| **Host** | 用户直接使用的 AI 应用 | 你的电脑 | Claude Desktop、Cursor、自研 AI 助手 |
| **Client** | Host 内部负责对接协议的模块 | 电脑上的 USB 控制器 | 每个 Client 对应一个 Server 的连接 |
| **Server** | 提供具体工具/数据的服务 | USB 外设（鼠标、U盘） | GitHub Server、数据库 Server |

**几个关键点：**

- 一个 Host 可以包含**多个** Client（就像电脑有多个 USB 口）。
- 每个 Client 与一个 Server 保持 **1:1 连接**。
- Client 和 Server 之间的通信严格遵守 MCP 协议，**双向通信**——不是只有 Client 问、Server 答，Server 也可以主动发消息给 Client。

### 2.2 谁发起连接？

始终是 **Client 主动连接 Server**，不会反过来。这一点和 HTTP 的"客户端发起请求"是一样的。

但连接建立后，**两边都可以主动发消息**。比如：

- Client → Server：调用一个工具
- Server → Client：通知"我的工具列表变了，请重新获取"

### 2.3 为什么要分 Host 和 Client？

你可能会问：Host 和 Client 有什么区别，直接叫一个不行吗？

分开是因为**职责不同**：

- **Host** 负责：用户交互界面、AI 模型调度、安全策略（比如弹窗问用户"是否允许执行这个操作"）。
- **Client** 负责：协议层的脏活——消息序列化、连接管理、能力协商。

这种分离让 Host 开发者可以专注用户体验，不用操心协议细节。

### 2.4 完整调用链：从用户指令到工具执行

现在我们把三个角色串起来，看一个完整的调用过程。这是最容易让人迷惑的地方——MCP Server 到底是被谁调用的？

```
sequenceDiagram
    participant U as 用户
    participant H as Host/Agent
    participant L as LLM
    participant C as MCP Client
    participant S as MCP Server
    participant E as 外部系统

    U->>H: "帮我在 Jira 创建一个 Bug ticket"
    H->>L: 转发用户请求
    Note right of L: 模型决定调用哪个 Tool<br/>生成结构化调用请求
    L-->>H: 需要调用 create_ticket
    H->>C: 转发 Tool 调用
    C->>S: tools/call
    S->>E: 调用 Jira API
    E-->>S: 返回结果
    S-->>C: 返回结果
    C-->>H: 返回结果
    H->>L: 把结果注入 context
    L-->>H: 生成最终回答
    H-->>U: "已成功创建工单 #12345"
```

**关键理解：**

- MCP Server **不是**被用户直接调用的
- MCP Server **也不是**被 LLM 直接调用的
- 真正的调用链是：**LLM 做决策 → Host 转发 → Client 发送 → Server 执行**

LLM 看到的只是 Tool 的 `name`、`description` 和 `inputSchema`，它根据用户意图决定调哪个 Tool、传什么参数。Server 只是执行层，不涉及任何 AI 逻辑。

---

## 3. 协议基石：JSON-RPC 2.0

在讲 MCP 的具体功能之前，必须先理解它的底层消息格式——**JSON-RPC 2.0**。

### 3.1 什么是 JSON-RPC？

JSON-RPC 是一个轻量级的远程过程调用协议。说白了就是：**用 JSON 格式来表达"我要调用什么方法、传什么参数、你给我什么结果"。**

MCP 的所有通信都是 JSON-RPC 2.0 消息。一共只有三种消息类型：

### 3.2 三种消息类型

**① Request（请求）——"我要你做件事，请给我回复"**

```
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search_docs",
    "arguments": { "query": "退款政策" }
  }
}
```

关键字段：

- `id`：唯一标识，用来匹配响应（你问的第几个问题，回答对应第几个）。
- `method`：要调用的方法名。
- `params`：参数。

**② Response（响应）——"这是你要的结果"**

```
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      { "type": "text", "text": "退款政策：30天内可全额退款……" }
    ]
  }
}
```

如果出错了，`result` 换成 `error`：

```
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32602,
    "message": "参数 query 不能为空"
  }
}
```

**③ Notification（通知）——"告诉你一声，不用回复"**

```
{
  "jsonrpc": "2.0",
  "method": "notifications/tools/list_changed"
}
```

注意：通知**没有 `id` 字段**，这就是区分请求和通知的方式。

### 3.3 批量请求（Batching）

MCP 支持将多个请求打包成一个数组一次性发送，减少通信开销：

```
[
  { "jsonrpc": "2.0", "id": 1, "method": "tools/list" },
  { "jsonrpc": "2.0", "id": 2, "method": "resources/list" }
]
```

Server 会返回一个数组，包含每个请求的响应。

> ⚠️ **注意**：协议规定所有实现**必须能接收** batch 消息，但**发送 batch 是可选的**。另外，`initialize` 请求**不得**放在 batch 中发送——因为初始化完成前不能发送其他请求。

### 3.4 为什么选 JSON-RPC 而不是 REST？

| 对比项 | REST API | JSON-RPC 2.0 |
| --- | --- | --- |
| 消息格式 | URL + HTTP 方法 + Body | 统一 JSON 格式 |
| 双向通信 | 天然不支持（Server 无法主动推送） | 天然支持（双方都能发消息） |
| 适合场景 | CRUD 资源操作 | 方法调用、工具执行 |
| 消息匹配 | 靠 HTTP 连接本身 | 靠 `id` 字段精确匹配 |

MCP 需要双向通信（Server 要能主动通知 Client），需要灵活的方法调用（不是简单的增删改查），所以 JSON-RPC 是更合适的选择。

---

## 4. 协议核心：三大能力原语

MCP Server 可以向 Client 暴露三种类型的能力，协议里叫 **Primitives（原语）**：

```
graph LR
    subgraph 原语["MCP Server 能提供什么？"]
        T["Tools<br/>工具"]
        R["Resources<br/>资源"]
        P["Prompts<br/>提示词模板"]
    end

    T -.- T1["AI 调用 → '帮我执行'"]
    R -.- R1["AI 读取 → '帮我看'"]
    P -.- P1["用户选择 → '帮我写'"]

    style T fill:#ffcdd2
    style R fill:#c8e6c9
    style P fill:#bbdefb
```

### 4.1 Tools（工具）—— AI 可以"动手做"的事情

**一句话理解：** Tool 就是 AI 可以调用的函数。

**例子：** 搜索知识库、发送邮件、创建 Jira 工单、执行数据库查询。

**关键特征：**

- 由 **AI 模型主动决定**是否调用（模型判断用户意图后，选择合适的工具）。
- 可以有**副作用**（会改变外部状态，比如发邮件、写数据库）。
- 需要人工确认（Host 应该在执行前弹窗问用户"是否允许"）。

**Tool 的定义长什么样：**

```
{
  "name": "search_docs",
  "description": "搜索内部知识库文档，返回最相关的结果",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": { "type": "string", "description": "搜索关键词" },
      "top_k": { "type": "integer", "description": "返回数量", "default": 5 }
    },
    "required": ["query"]
  },
  "annotations": {
    "title": "知识库搜索",
    "readOnlyHint": true,
    "openWorldHint": false
  }
}
```

这里有两个重要部分：

- **`inputSchema`**：用 JSON Schema 定义参数格式，AI 模型会根据这个生成正确的参数。
- **`annotations`（工具标注）**：这是最新版协议的重要特性，用于告诉 Host 这个工具的"性质"：

| 标注字段 | 含义 | 默认值 | 例子 |
| --- | --- | --- | --- |
| `readOnlyHint` | 是否只读（不会修改外部状态） | `false` | 搜索=true，删除=false |
| `destructiveHint` | 是否有破坏性 | `true` | 删除文件=true |
| `idempotentHint` | 是否幂等（重复调用结果一样） | `false` | 查询=true，发邮件=false |
| `openWorldHint` | 是否会访问外部网络 | `true` | 调用第三方 API=true |

> 💡 这些标注是"提示（hint）"，不是强制约束。Host 可以根据这些标注调整安全策略，比如：`destructiveHint=true` 的工具执行前一定要弹窗确认。
>
> 注意默认值的设计哲学是**安全优先（fail-safe）**：默认认为工具可能修改状态（`readOnlyHint=false`）、有破坏性（`destructiveHint=true`）、不幂等（`idempotentHint=false`）、会访问外网（`openWorldHint=true`）。这样即使开发者忘记设置标注，Host 也会采取最严格的安全策略。

**Tool 还支持结构化输出（Structured Output）：**（⚡ 2025-06-18 版新增）

如果你希望工具返回的不只是文本，还能返回机器可解析的 JSON 数据，可以定义 `outputSchema`：

```
{
  "name": "get_user_info",
  "description": "查询用户信息",
  "inputSchema": { ... },
  "outputSchema": {
    "type": "object",
    "properties": {
      "name": { "type": "string" },
      "email": { "type": "string" },
      "plan": { "type": "string", "enum": ["free", "pro", "enterprise"] }
    }
  }
}
```

定义了 `outputSchema` 后，工具返回的响应中会同时包含 `content`（给 AI 模型看的文本）和 `structuredContent`（结构化 JSON 数据），调用方可以直接用结构化数据做后续处理。

### 4.2 Resources（资源）—— AI 可以"阅读"的数据

**一句话理解：** Resource 就是 AI 可以读取的数据源，类似 REST 里的 GET 接口。

**例子：** 一份文档的内容、一个数据库表的 schema、一张配置文件。

**关键特征：**

- 由**用户或应用**决定是否读取（不是 AI 自己决定的）。
- **只读**，不会产生副作用。
- 通过 URI 标识，比如 `file:///docs/refund-policy.md` 或 `db://users/schema`。

```
{
  "uri": "docs://knowledge-base/refund-policy",
  "name": "退款政策文档",
  "mimeType": "text/markdown",
  "description": "公司退款政策的完整文档"
}
```

**Resource 支持两种发现方式：**

- **直接列表**（`resources/list`）：Server 列出所有可用资源，Client 选择要读取的。
- **模板**（`resources/templates/list`）：Server 提供 URI 模板，Client 动态填参数。比如 `db://tables/{table_name}/schema`，Client 填入具体表名来获取不同资源。

### 4.3 Prompts（提示词模板）—— 预制的交互剧本

**一句话理解：** Prompt 是 Server 预定义好的提示词模板，用户可以选择使用。

**例子：** "帮我做 Code Review"的提示词模板、"帮我写 SQL"的提示词模板。

**关键特征：**

- 由**用户主动选择**触发（比如在聊天框里选一个模板）。
- 可以带参数（模板里的变量由用户填入）。
- 返回的是完整的 `messages` 数组，可以直接塞给 AI 模型。

```
{
  "name": "code_review",
  "description": "对指定代码进行 Code Review",
  "arguments": [
    {
      "name": "code",
      "description": "要 review 的代码",
      "required": true
    },
    {
      "name": "language",
      "description": "编程语言",
      "required": false
    }
  ]
}
```

### 4.4 三种原语对比总结

|  | Tools（工具） | Resources（资源） | Prompts（模板） |
| --- | --- | --- | --- |
| 类比 | 函数/API | 文件/数据 | 预制剧本 |
| 谁决定使用 | AI 模型 | 用户/应用 | 用户 |
| 是否有副作用 | 可能有 | 没有（只读） | 没有 |
| 是否需要确认 | 推荐确认 | 通常不需要 | 不需要 |
| 发现方式 | `tools/list` | `resources/list` | `prompts/list` |
| 调用方式 | `tools/call` | `resources/read` | `prompts/get` |

---

## 5. 传输层：消息怎么送达？

协议定义好了"说什么"，传输层解决的是"怎么送达"。MCP 支持两种传输方式：

### 5.1 stdio（标准输入/输出）

**原理：** Host 直接启动 Server 进程，通过进程的 stdin/stdout 传递 JSON-RPC 消息。

```
graph LR
    H["Host 进程"] -->|"写入 stdin"| S["Server 进程"]
    S -->|"读取 stdout"| H
```

**特点：**

- 最简单，不需要网络配置。
- Server 作为子进程运行，生命周期由 Host 管理。
- **只能本机通信**——Host 和 Server 必须在同一台机器上。

**适合场景：** 本地开发工具（如 Cursor 调用本地的 Git Server）、桌面应用。

### 5.2 Streamable HTTP

**原理：** Server 作为 HTTP 服务运行，Client 通过 HTTP 请求与之通信。Server 可以用 SSE（Server-Sent Events）流式推送响应。

```
graph LR
    C["Client"] -->|"HTTP POST（发送请求）"| S["Server（/mcp 端点）"]
    C -->|"HTTP GET（打开 SSE 流）"| S
    S -.->|"SSE 流（推送通知/响应）"| C
    C -->|"HTTP DELETE（终止会话）"| S
```

**特点：**

- 单一端点：Server 只需暴露一个 HTTP 端点（如 `/mcp`），同时支持 POST、GET、DELETE。
- 支持**远程访问**——Server 可以部署在云端。
- 支持会话管理（通过 `Mcp-Session-Id` 请求头）。
- 支持流式响应（Server 可以边处理边推送结果）。
- Client 可以通过 **GET 请求**打开独立的 SSE 流，接收 Server 主动推送的通知——这是 MCP 双向通信的关键。
- 可以无状态部署，天然支持水平扩展（但协议也允许通过 Session ID 维护有状态会话）。

**适合场景：** 生产环境部署、多用户共享的 Server、需要远程访问的场景。

> ⚠️ 旧版协议（2024-11-05 版）使用的是 HTTP+SSE 双端点方案（`/sse` + `/messages` 两个端点），已在 2025-03-26 版中被 **Streamable HTTP** 单端点方案取代。如果你看到旧教程提到双端点，请忽略。

### 5.3 如何选择？

```
flowchart TD
    Q{"你的 Server 需要远程访问吗？"}
    Q -->|"不需要，只在本机"| A["→ stdio"]
    Q -->|"需要远程 / 多用户"| B["→ Streamable HTTP"]
```

|  | stdio | Streamable HTTP |
| --- | --- | --- |
| 网络要求 | 无（本机进程） | 需要 HTTP 网络 |
| 部署复杂度 | 低 | 中等 |
| 远程访问 | ❌ | ✅ |
| 水平扩展 | ❌ | ✅ |
| 典型用法 | `claude desktop` 本地配置 | 云端 MCP 服务 |

---

## 6. 连接生命周期：从握手到断开

一个 MCP 连接从建立到关闭，经历三个阶段：

```
  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │  Initialize │────▶│  Operation  │────▶│  Shutdown   │
  │  初始化握手  │     │  正常工作    │     │  优雅关闭    │
  └─────────────┘     └─────────────┘     └─────────────┘
```

### 6.1 阶段一：初始化（握手）

Client 和 Server 需要先"自我介绍"，交换各自支持的能力：

```
sequenceDiagram
    participant C as Client
    participant S as Server

    C->>S: initialize 请求（我是谁，我支持什么）
    S-->>C: initialize 响应（我是谁，我支持什么）
    C->>S: initialized 通知（收到，握手完成！）
```

**initialize 请求示例：**

```
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-06-18",
    "capabilities": {
      "roots": { "listChanged": true }
    },
    "clientInfo": {
      "name": "MyAIApp",
      "version": "1.0.0"
    }
  }
}
```

**Server 响应示例：**

```
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-06-18",
    "capabilities": {
      "tools": { "listChanged": true },
      "resources": { "subscribe": true }
    },
    "serverInfo": {
      "name": "knowledge-base-server",
      "version": "2.0.0"
    }
  }
}
```

**重点：能力协商。** 双方通过 `capabilities` 字段告诉对方自己支持什么。比如 Server 说"我支持 tools"，那 Client 后续才能调用 `tools/list` 和 `tools/call`。如果 Server 没声明某个能力，Client 就不该尝试使用它。

### 6.2 阶段二：正常工作

握手完成后，双方就可以自由通信了：

**Client → Server（常见操作）：**

- `tools/list` — 列出所有可用工具
- `tools/call` — 调用某个工具
- `resources/list` — 列出所有资源
- `resources/read` — 读取某个资源
- `prompts/list` — 列出提示词模板
- `prompts/get` — 获取某个模板的内容
- `completion/complete` — 请求自动补全
- `ping` — 心跳检测

**Server → Client（主动通知和请求）：**

- `notifications/tools/list_changed` — 通知工具列表变了
- `notifications/resources/updated` — 通知某个资源更新了
- `elicitation/create` — 主动向用户收集信息（比如弹窗让用户选择一个选项）（⚡ 2025-06-18 版新增）

> 💡 **Elicitation（主动询问）** 是 2025-06-18 版本新增的特性，设计仍在演进中：Server 在处理请求的过程中，可以反过来向用户提问。比如一个部署工具在执行时发现有两个环境可选，它可以通过 Elicitation 让用户选择"部署到 staging 还是 production"。使用时需要 Client 在初始化阶段声明 `elicitation` 能力。

### 6.3 阶段三：优雅关闭

MCP 协议**没有定义**专门的 `close` 或 `shutdown` JSON-RPC 方法——关闭是通过底层传输机制来完成的：

**stdio 模式：**

1. Client 关闭 Server 子进程的 stdin；
2. 等待 Server 自行退出；
3. 如果超时未退出，发送 `SIGTERM`；
4. 仍未退出则发送 `SIGKILL`。

**Streamable HTTP 模式：**

1. Client 向 MCP endpoint 发送 **HTTP DELETE** 请求（携带 `Mcp-Session-Id` 头）；
2. Server 清理会话资源，关闭关联的 SSE 流。

---

## 7. 实战：用 Python 开发一个 MCP Server

### 7.1 需求

我们要做一个**知识库搜索 MCP Server**，提供：

- 一个 Tool：`search_docs` — 搜索知识库
- 一个 Resource：`docs://knowledge-base/summary` — 知识库概要

### 7.2 环境准备

```
# 需要 Python 3.10+
pip install "mcp[cli]" httpx
# [cli] extra 提供 mcp dev / mcp run / mcp install 等 CLI 命令
# 如果不需要 CLI 工具，也可以只装：pip install mcp httpx
```

### 7.3 完整代码

```
"""knowledge_base_server.py - 知识库搜索 MCP Server"""

import os
import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

# ── 初始化 Server ──────────────────────────────
mcp = FastMCP(
    name="knowledge-base-server",
    instructions="内部知识库搜索服务",
)

# ── 配置 ──────────────────────────────────────
KB_API_URL = os.getenv("KB_API_URL", "https://kb.example.com/api")
KB_TOKEN = os.getenv("KB_TOKEN", "")  # 必须从环境变量获取


# ── Tool：搜索知识库 ──────────────────────────
@mcp.tool(
    title="知识库搜索",
    annotations=ToolAnnotations(
        readOnlyHint=True,          # 只读操作，不会修改数据
        destructiveHint=False,
        openWorldHint=True,         # 会访问外部 API
    ),
)
async def search_docs(query: str, top_k: int = 5) -> str:
    """
    搜索内部知识库，返回最相关的文档片段。

    Args:
        query: 搜索关键词
        top_k: 返回结果数量，默认 5
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{KB_API_URL}/search",
                json={"query": query, "top_k": top_k},
                headers={"Authorization": f"Bearer {KB_TOKEN}"},
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
    except httpx.HTTPError as e:
        return f"搜索服务暂时不可用：{e}"

    if not results:
        return "未找到相关文档。"

    # 拼成可读文本返回给 AI
    lines = []
    for i, doc in enumerate(results, 1):
        title = doc.get("title", "无标题")
        snippet = doc.get("snippet", "")
        score = doc.get("score", 0)
        lines.append(f"{i}. **{title}**（相关度 {score:.2f}）\n   {snippet}")

    return "\n\n".join(lines)


# ── Resource：知识库概要 ──────────────────────
@mcp.resource("docs://knowledge-base/summary")
async def kb_summary() -> str:
    """知识库概要信息：文档数量、最后更新时间等"""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{KB_API_URL}/stats",
            headers={"Authorization": f"Bearer {KB_TOKEN}"},
        )
        resp.raise_for_status()
        stats = resp.json()

    return (
        f"知识库概要：\n"
        f"- 文档总数：{stats.get('total_docs', '未知')}\n"
        f"- 最后更新：{stats.get('last_updated', '未知')}\n"
        f"- 覆盖主题：{', '.join(stats.get('topics', []))}"
    )


# ── 启动入口 ──────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="stdio")  # 本地开发用 stdio
```

### 7.4 运行与调试

**方式一：MCP Inspector（推荐调试时使用）**

```
npx @modelcontextprotocol/inspector python knowledge_base_server.py
```

浏览器打开后可以：

- 查看 Server 声明的 Tools / Resources / Prompts
- 手动调用 Tool，查看输入输出
- 检查 JSON-RPC 消息流

**方式二：接入 Claude Desktop**

编辑 Claude Desktop 配置文件：

- macOS：`~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows：`%APPDATA%\Claude\claude_desktop_config.json`

```
{
  "mcpServers": {
    "knowledge-base": {
      "command": "python",
      "args": ["/path/to/knowledge_base_server.py"],
      "env": {
        "KB_API_URL": "https://kb.your-company.com/api",
        "KB_TOKEN": "your-secret-token"
      }
    }
  }
}
```

重启 Claude Desktop，在聊天框中输入"帮我查一下退款政策"，AI 就会自动调用 `search_docs` 工具。

### 7.5 如果需要远程部署（Streamable HTTP）

只需将初始化和启动方式改为：

```
mcp = FastMCP(
    name="knowledge-base-server",
    instructions="内部知识库搜索服务",
    host="0.0.0.0",
    port=8000,
)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

Client 通过 `http://your-server:8000/mcp` 连接即可。

---

## 8. 安全最佳实践

MCP Server 本质上是在给 AI 模型"开权限"，安全至关重要。

### 8.1 核心原则

```
flowchart TD
    A["最小权限原则"]
    A --> B["输入验证"]
    A --> C["人工确认循环"]
    A --> D["密钥安全"]
```

### 8.2 具体措施

| 领域 | 做法 | 原因 |
| --- | --- | --- |
| **输入验证** | 对所有 Tool 参数做严格校验，永远不要把参数直接拼接到 SQL/命令中 | AI 生成的参数可能被 Prompt Injection 操控 |
| **人工确认** | 有副作用的操作（写入、删除、发送），必须让 Host 弹窗确认 | AI 可能误判用户意图 |
| **最小权限** | Server 只请求必要的权限，数据库账号只给只读权限 | 限制爆炸半径 |
| **密钥管理** | Token/密码通过环境变量传入，不硬编码在代码里 | 防止泄露到代码仓库 |
| **Tool Annotations** | 正确设置 `readOnlyHint`、`destructiveHint` 等标注 | 让 Host 能智能决定安全策略 |
| **传输安全** | 远程部署时使用 HTTPS + OAuth 2.1 | 防止中间人攻击和未授权访问 |
| **DNS Rebinding 防护** | Streamable HTTP Server 必须验证 `Origin` 头；本地运行时绑定 `127.0.0.1` 而非 `0.0.0.0` | 防止恶意网页通过 DNS 重绑定攻击本地 Server |
| **日志审计** | 记录所有 Tool 调用的入参和结果 | 事后追溯和异常检测 |

### 8.3 OAuth 2.1 授权

对于远程部署的 Streamable HTTP Server，MCP 协议内建了 OAuth 2.1 授权框架：

1. Client 首次连接时，Server 返回 `401` 并指明授权端点；
2. Client 引导用户完成 OAuth 登录（授权码流程 + **PKCE**，PKCE 是所有客户端的强制要求）；
3. 获取 Access Token 后，后续请求通过 `Authorization: Bearer <token>` 携带；
4. Token 过期后自动刷新。

这意味着你不需要自己实现鉴权中间件——协议已经规定好了标准流程。

---

## 9. MCP vs Function Calling vs 直接 CLI 调用

这三者经常被混淆，我们来梳理本质区别。

### 9.1 三者定位

```
graph TB
    subgraph AI应用["AI 应用"]
        U["用户说：'帮我查一下退款政策'"]
        U --> M["AI 模型推理<br/>'需要搜索知识库'"]
    end

    M --> FC["Function Calling<br/>(模型层接口)"]
    M --> MCP["MCP Tool<br/>(协议层标准)"]
    M --> CLI["CLI 调用<br/>(操作系统层)"]

    FC --> API["模型 API<br/>供应商绑定"]
    MCP --> Server["MCP Server<br/>标准化通信"]
    CLI --> Shell["shell 命令<br/>无标准化"]

    style MCP fill:#c8e6c9
```

### 9.2 核心区别对比

| 对比维度 | Function Calling | MCP | 直接 CLI 调用 |
| --- | --- | --- | --- |
| **是什么** | 模型 API 的参数格式约定 | 独立的通信协议 | 直接执行系统命令 |
| **标准化** | 每家模型供应商各有格式 | 统一开放协议 | 无标准 |
| **谁定义工具** | 开发者在 API 调用时传入 | MCP Server 自行声明，Client 动态发现 | 开发者硬编码 |
| **工具发现** | ❌ 无法动态发现 | ✅ `tools/list` 自动发现 | ❌ 无 |
| **供应商绑定** | 绑定特定模型供应商 | 不绑定任何模型 | 不绑定 |
| **双向通信** | ❌ | ✅ | ❌ |
| **安全机制** | 开发者自行实现 | 协议内建（Annotations、OAuth、确认流程） | 几乎没有 |
| **适合场景** | 快速原型、简单集成 | 标准化生态、多应用共享 | 脚本、自动化 |

### 9.3 它们不是互斥的

一个典型的 AI 应用中，三者经常**协同工作**：

1. 用户说"帮我搜一下退款政策"；
2. AI 模型通过 **Function Calling** 的格式，告诉Agent应用"我想调用 search\_docs"；
3. Agent应用通过 **MCP 协议**，将这个调用转发给知识库 MCP Server；
4. MCP Server 内部可能通过 **CLI 调用** `grep` 或 `curl` 来执行实际操作。

```
flowchart LR
    A["Function Calling<br/>（模型怎么表达意图）"] --> B["MCP 协议<br/>（应用怎么传递请求）"]
    B --> C["CLI 调用<br/>（Server 怎么执行）"]
```

---

## 10. 常见问题 FAQ

### Q1：MCP 只能和 Claude 一起用吗？

**不是。** MCP 是开放协议，任何 AI 应用都可以实现。目前已支持的 Host 包括 Claude Desktop、Cursor、Windsurf、Cline 等，OpenAI 也已宣布支持。

### Q2：MCP Server 必须用 Python 写吗？

**不是。** 协议不限制语言。官方提供了 Python 和 TypeScript 的 SDK，社区还有 Go、Rust、Java、C# 等实现。

### Q3：MCP Server 是有状态的还是无状态的？

**都可以。** 协议通过 `Mcp-Session-Id` 支持有状态会话，但也完全允许无状态设计。对于 Streamable HTTP 模式，推荐无状态设计以便水平扩展；如果确实需要会话状态（比如维护一个数据库连接），可以通过 Session ID 实现。

### Q4：Tool 和 Resource 有什么区别？什么时候用哪个？

| 判断标准 | 用 Tool | 用 Resource |
| --- | --- | --- |
| 谁决定使用？ | AI 模型自主决定 | 用户/应用主动选择 |
| 有没有副作用？ | 可能有 | 没有（只读） |
| 需要传参数吗？ | 通常需要 | 通常不需要（URI 定位） |

经验法则：如果这个操作是"AI 根据对话判断要不要做的"，用 Tool；如果是"提前把某些数据塞给 AI 当背景知识"，用 Resource。

### Q5：怎么调试 MCP Server？

推荐使用 **MCP Inspector**：

```
npx @modelcontextprotocol/inspector python your_server.py
```

它会启动一个网页界面，你可以直观地看到所有工具、资源、模板，手动调用并查看请求/响应。

### Q6：生产环境该怎么部署？

- **小规模/内部使用：** stdio 模式，Server 作为本地进程运行。
- **多用户/远程访问：** Streamable HTTP 模式，部署在云端，配合 OAuth 2.1 鉴权、HTTPS 加密、负载均衡。

### Q7：MCP Server 在哪里运行？是在云端吗？

**看你选择。** stdio 模式下 Server 是 Host 启动的本地子进程，运行在你自己的机器上；Streamable HTTP 模式下可以部署在任何能提供 HTTP 服务的地方——本地、云端、Docker 容器都行。协议不限制部署位置，只规定通信方式。

---

## 系列文章

本文是「Claude Code 实战系列」的一部分，可按顺序阅读：

- [国内安装 Claude Code 并切换使用国内大模型 API：完整指南](https://juejin.cn/post/7611769471619645478 "https://juejin.cn/post/7611769471619645478") — 安装、登录、基本使用
- [AI Agent 的外部连接层：MCP 协议原理、机制设计与实战开发](https://juejin.cn/post/7616025751747182598 "https://juejin.cn/post/7616025751747182598") — MCP 的原理与生态全貌
- [Claude Code 核心配置全解：MCP、子代理、Skills、Hooks、插件](https://juejin.cn/post/7619245854760009743 "https://juejin.cn/post/7619245854760009743") — MCP、子代理、Skills、Hooks、插件

---

最后说一句个人观点：同类的 AI 编程 CLI 工具，学一个就够了。Claude Code、OpenAI Codex CLI、Gemini CLI……原理都差不多，真正的差距在于你对这套工具理解有多深、用得有多顺手，而不是你装了多少个。

人的时间和精力是有限的。挑行业里最领先的那个，把它用到极致，比浅尝十个工具有价值得多。AI 时代反而更需要这种取舍——工具越来越多，专注越来越稀缺。

---

## 附：推荐阅读

- [MCP 官方规范](https://link.juejin.cn?target=https%3A%2F%2Fspec.modelcontextprotocol.io "https://spec.modelcontextprotocol.io")（协议的权威定义）
- [MCP Python SDK](https://link.juejin.cn?target=https%3A%2F%2Fgithub.com%2Fmodelcontextprotocol%2Fpython-sdk "https://github.com/modelcontextprotocol/python-sdk")（Python 开发者首选）
- [MCP TypeScript SDK](https://link.juejin.cn?target=https%3A%2F%2Fgithub.com%2Fmodelcontextprotocol%2Ftypescript-sdk "https://github.com/modelcontextprotocol/typescript-sdk")（Node.js 开发者首选）
- [MCP Servers 仓库](https://link.juejin.cn?target=https%3A%2F%2Fgithub.com%2Fmodelcontextprotocol%2Fservers "https://github.com/modelcontextprotocol/servers")（官方和社区的 Server 集合，拿来即用或参考学习）
