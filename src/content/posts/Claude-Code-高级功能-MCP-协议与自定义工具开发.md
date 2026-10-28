---
title: "Claude Code 高级功能：MCP 协议与自定义工具开发"
date: 2026-02-11
description: "MCP（Model Context Protocol） 是 Anthropic 设计的开放协议，允许 AI 模型与外部工具和数据源进行标准化交互。 Claude Code 内置了多个 MCP 服务器："
tags: ['Claude Code']
category: "技术"
---
> 深入了解 Claude Code 的 MCP（Model Context Protocol）协议，学习如何开发自定义工具扩展 AI 的能力边界。

## 什么是 MCP？

**MCP（Model Context Protocol）** 是 Anthropic 设计的开放协议，允许 AI 模型与外部工具和数据源进行标准化交互。

```
┌─────────────────┐     MCP 协议      ┌─────────────────┐
│   Claude Code   │ ◄──────────────► │   MCP Server    │
│   (AI Client)   │                  │   (工具提供者)    │
└─────────────────┘                  └─────────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
              ┌─────▼─────┐           ┌───────▼───────┐          ┌─────▼─────┐
              │  数据库    │           │   API 服务    │          │  文件系统  │
              └───────────┘           └───────────────┘          └───────────┘
```

### MCP 的优势

| 特性 | 说明 |
|-----|------|
| **标准化** | 统一的协议规范，一次开发到处使用 |
| **安全性** | 明确的权限模型，可控的工具访问 |
| **可扩展** | 轻松添加新工具，无需修改核心代码 |
| **互操作** | 不同 AI 客户端都可使用相同的 MCP 服务器 |

---

## 快速上手：使用现有 MCP 工具

### 1. 查看可用的 MCP 服务器

Claude Code 内置了多个 MCP 服务器：

```bash
# 在 Claude Code 中
/mcp list
```

常见的内置服务器：
- `filesystem` - 文件系统操作
- `git` - Git 版本控制
- `web` - 网络请求
- `postgres` - PostgreSQL 数据库

### 2. 添加社区 MCP 服务器

```bash
# 安装社区 MCP 服务器
npm install -g @anthropic/mcp-server-github

# 在 Claude Code 配置中添加
```

编辑 `~/.claude/config.json`：

```json
{
  "mcpServers": {
    "github": {
      "command": "mcp-server-github",
      "env": {
        "GITHUB_TOKEN": "your_github_token"
      }
    }
  }
}
```

### 3. 使用 MCP 工具

```
请使用 GitHub MCP 查看我的仓库列表

为 my-repo 仓库创建一个新的 Issue:
标题: 优化登录性能
描述: 当前登录响应时间过长，需要优化
```

---

## 开发自定义 MCP 服务器

### 项目结构

```
my-mcp-server/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts          # 入口文件
│   ├── server.ts         # MCP 服务器实现
│   └── tools/
│       ├── weather.ts    # 天气查询工具
│       └── translate.ts  # 翻译工具
└── README.md
```

### 步骤 1：初始化项目

```bash
mkdir my-mcp-server
cd my-mcp-server
npm init -y
npm install @modelcontextprotocol/sdk typescript
npm install -D @types/node
```

### 步骤 2：创建 MCP 服务器

```typescript
// src/server.ts
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

// 定义工具列表
const TOOLS = [
  {
    name: 'get_weather',
    description: '获取指定城市的天气信息',
    inputSchema: {
      type: 'object',
      properties: {
        city: {
          type: 'string',
          description: '城市名称，如：北京、上海',
        },
      },
      required: ['city'],
    },
  },
  {
    name: 'translate',
    description: '翻译文本',
    inputSchema: {
      type: 'object',
      properties: {
        text: {
          type: 'string',
          description: '要翻译的文本',
        },
        targetLang: {
          type: 'string',
          description: '目标语言：en, zh, ja, ko 等',
        },
      },
      required: ['text', 'targetLang'],
    },
  },
];

// 创建服务器实例
const server = new Server(
  { name: 'my-mcp-server', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

// 处理工具列表请求
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: TOOLS,
}));

// 处理工具调用请求
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case 'get_weather':
      return await handleGetWeather(args.city);
    case 'translate':
      return await handleTranslate(args.text, args.targetLang);
    default:
      throw new Error(`Unknown tool: ${name}`);
  }
});

// 天气查询实现
async function handleGetWeather(city: string) {
  // 这里可以调用真实的天气 API
  const mockWeather = {
    city,
    temperature: 22,
    condition: '晴朗',
    humidity: 45,
  };
  
  return {
    content: [
      {
        type: 'text',
        text: JSON.stringify(mockWeather, null, 2),
      },
    ],
  };
}

// 翻译实现
async function handleTranslate(text: string, targetLang: string) {
  // 这里可以调用翻译 API
  const result = `[${targetLang}] ${text} (translated)`;
  
  return {
    content: [
      {
        type: 'text',
        text: result,
      },
    ],
  };
}

// 启动服务器
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('MCP Server started');
}

main().catch(console.error);
```

### 步骤 3：配置并运行

```json
// package.json
{
  "name": "my-mcp-server",
  "version": "1.0.0",
  "type": "module",
  "bin": {
    "my-mcp-server": "./dist/index.js"
  },
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js"
  }
}
```

```bash
npm run build
npm link  # 全局安装
```

### 步骤 4：在 Claude Code 中注册

```json
// ~/.claude/config.json
{
  "mcpServers": {
    "my-tools": {
      "command": "my-mcp-server"
    }
  }
}
```

### 步骤 5：使用自定义工具

```
查询北京今天的天气

把 "Hello World" 翻译成日语
```

---

## 高级功能：资源（Resources）

除了工具，MCP 还支持"资源"概念，用于提供数据访问：

```typescript
import { ListResourcesRequestSchema, ReadResourceRequestSchema } from '@modelcontextprotocol/sdk/types.js';

// 定义资源
const RESOURCES = [
  {
    uri: 'config://app-settings',
    name: '应用配置',
    description: '当前应用的配置信息',
    mimeType: 'application/json',
  },
];

// 处理资源列表
server.setRequestHandler(ListResourcesRequestSchema, async () => ({
  resources: RESOURCES,
}));

// 处理资源读取
server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  const { uri } = request.params;
  
  if (uri === 'config://app-settings') {
    return {
      contents: [
        {
          uri,
          mimeType: 'application/json',
          text: JSON.stringify({
            theme: 'dark',
            language: 'zh-CN',
            features: ['auth', 'analytics'],
          }),
        },
      ],
    };
  }
  
  throw new Error(`Resource not found: ${uri}`);
});
```

---

## 实战案例：数据库查询 MCP

创建一个可以查询 PostgreSQL 的 MCP 服务器：

```typescript
import { Pool } from 'pg';

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

const TOOLS = [
  {
    name: 'query_database',
    description: '执行 SQL 查询（只读）',
    inputSchema: {
      type: 'object',
      properties: {
        sql: {
          type: 'string',
          description: 'SELECT 查询语句',
        },
      },
      required: ['sql'],
    },
  },
  {
    name: 'list_tables',
    description: '列出所有数据表',
    inputSchema: { type: 'object', properties: {} },
  },
];

async function handleQueryDatabase(sql: string) {
  // 安全检查：只允许 SELECT
  if (!sql.trim().toLowerCase().startsWith('select')) {
    throw new Error('只允许 SELECT 查询');
  }
  
  const result = await pool.query(sql);
  return {
    content: [
      {
        type: 'text',
        text: JSON.stringify(result.rows, null, 2),
      },
    ],
  };
}
```

在 Claude Code 中使用：

```
查询用户表中最近注册的10个用户

统计每个月的订单数量
```

---

## 安全最佳实践

### 1. 输入验证

```typescript
function validateInput(input: unknown, schema: object): boolean {
  // 使用 Zod 或 Joi 进行严格验证
  return true;
}
```

### 2. 权限控制

```typescript
const ALLOWED_OPERATIONS = ['read', 'list'];

function checkPermission(operation: string): void {
  if (!ALLOWED_OPERATIONS.includes(operation)) {
    throw new Error('Permission denied');
  }
}
```

### 3. 速率限制

```typescript
import { RateLimiter } from 'limiter';

const limiter = new RateLimiter({
  tokensPerInterval: 100,
  interval: 'minute',
});

async function handleRequest(request: Request) {
  if (!await limiter.tryRemoveTokens(1)) {
    throw new Error('Rate limit exceeded');
  }
  // 处理请求...
}
```

### 4. 日志记录

```typescript
function logToolCall(toolName: string, args: object, result: object) {
  console.error(JSON.stringify({
    timestamp: new Date().toISOString(),
    tool: toolName,
    args,
    success: true,
  }));
}
```

---

## 常用 MCP 服务器推荐

| 服务器 | 功能 | 安装命令 |
|-------|------|---------|
| `mcp-server-github` | GitHub 操作 | `npm i -g @anthropic/mcp-server-github` |
| `mcp-server-slack` | Slack 消息 | `npm i -g @anthropic/mcp-server-slack` |
| `mcp-server-postgres` | PostgreSQL | `npm i -g @anthropic/mcp-server-postgres` |
| `mcp-server-sqlite` | SQLite | `npm i -g @anthropic/mcp-server-sqlite` |
| `mcp-server-puppeteer` | 浏览器自动化 | `npm i -g @anthropic/mcp-server-puppeteer` |

---

## 总结

MCP 协议为 Claude Code 提供了强大的扩展能力：

1. **标准化接口**：统一的工具调用规范
2. **安全可控**：明确的权限和验证机制
3. **易于开发**：TypeScript SDK 简化开发
4. **生态丰富**：社区提供大量现成工具

通过 MCP，你可以让 Claude Code 访问任何数据源、调用任何 API，真正实现 AI 与现实世界的无缝连接。

---

## 延伸阅读

- [MCP 官方规范](https://modelcontextprotocol.io)
- [MCP SDK 文档](https://github.com/anthropics/mcp)
- [社区 MCP 服务器合集](https://github.com/anthropics/mcp-servers)

---

*本文基于 MCP 协议 v1.0 编写，如有更新请以官方文档为准。*
