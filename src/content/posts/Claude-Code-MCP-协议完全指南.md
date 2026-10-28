---
title: "Claude Code MCP 协议完全指南"
date: 2026-04-02
description: "1. 什么是 MCP？ 2. MCP 传输类型 3. 安装和配置 MCP 4. 常用 MCP 服务器"
tags: ['Claude Code']
category: "技术"
---
> Model Context Protocol - 让 Claude 连接外部世界

## 目录

1. [什么是 MCP？](#1-什么是-mcp)
2. [MCP 传输类型](#2-mcp-传输类型)
3. [安装和配置 MCP](#3-安装和配置-mcp)
4. [常用 MCP 服务器](#4-常用-mcp-服务器)
5. [创建自定义 MCP](#5-创建自定义-mcp)
6. [最佳实践](#6-最佳实践)

---

## 1. 什么是 MCP？

**MCP (Model Context Protocol)** 是 Anthropic 推出的开放标准，允许 Claude Code 连接到外部工具、数据库和 API，无需自定义集成。

### MCP 的价值

传统方式需要为每个服务编写自定义集成代码。MCP 提供了标准化方式：

```
以前: 需要为 Notion、GitHub、PostgreSQL 分别编写集成
现在: 使用 MCP 服务器，即插即用
```

### MCP vs 传统集成

| 方面 | MCP 集成 | 传统集成 |
|------|----------|----------|
| 开发时间 | 几分钟配置 | 几天/几周开发 |
| 维护成本 | 低（服务器自动更新） | 高（需手动维护） |
| 标准化 | 统一协议 | 各不相同 |
| 安全性 | 标准权限模型 | 各自实现 |

---

## 2. MCP 传输类型

### HTTP 传输（推荐）

适用于远程服务器和云服务：

```
Claude Code ←→ MCP Server (HTTP)
```

**特点**:
- 最稳定的传输方式
- 适合生产环境
- 自动重连
- 支持认证

**示例服务**: Notion, GitHub, Sentry

### Stdio 传输

适用于本地进程：

```
Claude Code ←→ 本地进程 (stdin/stdout)
```

**特点**:
- 适合数据库和本地工具
- 无需网络
- 更快的响应

**示例服务**: PostgreSQL, SQLite, 本地文件工具

### SSE 传输（已弃用）

遗留的 Server-Sent Events 传输，新项目不应使用。

---

## 3. 安装和配置 MCP

### 添加 MCP 服务器

#### HTTP 服务器

```bash
# Notion 集成
claude mcp add --transport http notion https://mcp.notion.com/mcp

# GitHub 集成
claude mcp add --transport http github https://api.githubcopilot.com/mcp/

# Sentry 集成
claude mcp add --transport http sentry https://mcp.sentry.dev/mcp
```

#### Stdio 服务器

```bash
# PostgreSQL 数据库
claude mcp add --transport stdio db -- \
  npx -y @bytebase/dbhub --dsn "postgresql://user:pass@host/db"

# SQLite 数据库
claude mcp add --transport stdio sqlite -- \
  npx -y @modelcontextprotocol/server-sqlite --db-path ./data.db

# Airtable
claude mcp add --transport stdio --env AIRTABLE_API_KEY=YOUR_KEY airtable -- \
  npx -y airtable-mcp-server
```

### 管理 MCP 服务器

```bash
# 列出所有 MCP 服务器
claude mcp list

# 查看特定服务器详情
claude mcp get <name>

# 移除 MCP 服务器
claude mcp remove <name>

# 在 Claude Code 中检查状态
/mcp
```

### 配置文件位置

| 范围 | 存储文件 | 用途 |
|------|----------|------|
| `local` (默认) | `~/.claude.json` | 仅你私有，当前项目 |
| `project` | `.mcp.json` | 与团队通过版本控制共享 |
| `user` | `~/.claude.json` | 在所有项目中可用 |

---

## 4. 常用 MCP 服务器

### GitHub MCP

**功能**: PR 审查、问题管理、代码搜索

```bash
claude mcp add --transport http github https://api.githubcopilot.com/mcp/
```

**使用场景**:
```bash
> 获取最新的 5 个 PR
> 审查 PR #123
> 在仓库中搜索 "auth" 相关代码
```

### Notion MCP

**功能**: 读写页面、搜索数据库

```bash
claude mcp add --transport http notion https://mcp.notion.com/mcp
```

**使用场景**:
```bash
> 在 Notion 中创建新页面 "API 文档"
> 搜索标题包含 "发布计划" 的页面
> 将此代码更新添加到 Product Database
```

### PostgreSQL MCP

**功能**: 查询数据库、架构探索

```bash
claude mcp add --transport stdio db -- \
  npx -y @bytebase/dbhub --dsn "postgresql://user:pass@localhost:5432/mydb"
```

**使用场景**:
```bash
> 显示 users 表结构
> 查找过去 7 天注册的所有用户
> 分析 orders 表中的销售趋势
```

### Sentry MCP

**功能**: 错误追踪、问题分析

```bash
claude mcp add --transport http sentry https://mcp.sentry.dev/mcp
```

**使用场景**:
```bash
> 获取今天最新的 10 个错误
> 分析错误 SENTRY-123 的根本原因
> 查找与特定用户相关的所有问题
```

### Slack MCP（通过 Zapier）

**功能**: 频道访问、消息发送

```bash
# 首先设置 Zapier 连接
claude mcp add --transport http slack https://zapier-mcp-server.com/slack
```

**使用场景**:
```bash
> 在 #announcements 频道发布部署通知
> 获取 #dev 频道的最近消息
```

### Figma MCP

**功能**: 设计系统访问、组件信息

```bash
claude mcp add --transport http figma https://mcp.figma.com/mcp
```

**使用场景**:
```bash
> 获取 Button 组件的设计规范
> 列出 Design System 中的所有颜色变量
> 提取图标的 SVG 代码
```

---

## 5. 创建自定义 MCP

### MCP 服务器结构

```
my-mcp-server/
├── package.json
├── src/
│   └── index.ts
└── tsconfig.json
```

### 基础 HTTP MCP 服务器

```typescript
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

// 创建服务器实例
const server = new Server(
  {
    name: 'my-custom-mcp',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// 注册工具列表
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'get_weather',
        description: '获取指定城市的天气',
        inputSchema: {
          type: 'object',
          properties: {
            city: {
              type: 'string',
              description: '城市名称',
            },
          },
          required: ['city'],
        },
      },
    ],
  };
});

// 处理工具调用
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (name === 'get_weather') {
    // 调用天气 API
    const weather = await getWeatherFromAPI(args.city);
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(weather, null, 2),
        },
      ],
    };
  }

  throw new Error(`未知工具: ${name}`);
});

// 启动服务器
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Custom MCP Server running');
}

main().catch(console.error);
```

### 部署自定义 MCP

```bash
# 本地开发
npm run dev

# 发布到 npm
npm publish

# 使用自定义 MCP
claude mcp add --transport stdio my-tool -- npx -y @username/my-custom-mcp
```

---

## 6. 最佳实践

### 上下文管理

⚠️ **不要启用所有 MCP！**

过多的 MCP 服务器会显著减少上下文窗口：

| MCP 数量 | 工具数量 | 可用上下文 |
|----------|----------|------------|
| 0 | 0 | 200K tokens |
| 5 | 50 | ~150K tokens |
| 10+ | 100+ | ~70K tokens |

**建议**: 保持少于 10 个 MCP，少于 80 个活动工具。

### 安全性

#### 1. 使用环境变量存储密钥

```bash
# 不好的做法
claude mcp add --transport http github https://api.github.com/mcp?token=ghp_xxxx

# 好的做法
export GITHUB_TOKEN=ghp_xxxx
claude mcp add --transport http github https://api.github.com/mcp
```

#### 2. 限制权限

```json
{
  "permissions": {
    "allow": [
      "mcp__github__read",
      "mcp__github__search"
    ],
    "deny": [
      "mcp__github__write",
      "mcp__github__delete"
    ]
  }
}
```

#### 3. 审计 MCP 工具

```bash
# 查看 MCP 提供的所有工具
claude mcp get github

# 测试 MCP 连接
> 测试 GitHub MCP 连接
```

### 性能优化

#### 1. 使用 HTTP 传输进行远程调用

HTTP 比 Stdio 更稳定，适合生产环境。

#### 2. 延迟加载工具

```json
{
  "env": {
    "ENABLE_TOOL_SEARCH": "true"
  }
}
```

#### 3. 监控 MCP 性能

```bash
/cost
```

定期检查 token 使用情况。

### 项目级 MCP 配置

创建 `.mcp.json` 与团队共享：

```json
{
  "mcpServers": {
    "github": {
      "transport": "http",
      "url": "https://api.githubcopilot.com/mcp",
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "postgres": {
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@bytebase/dbhub", "--dsn", "${DATABASE_URL}"]
    }
  }
}
```

### 故障排除

#### MCP 无法连接

```bash
# 检查 MCP 状态
/mcp

# 查看详细日志
claude --log-level debug
```

#### 工具不可用

```bash
# 重新加载 MCP
claude mcp reload <name>

# 检查工具列表
> 列出所有可用的 MCP 工具
```

---

## MCP 资源

- [MCP 官方文档](https://modelcontextprotocol.io/)
- [MCP SDK GitHub](https://github.com/modelcontextprotocol)
- [MCP 服务器列表](https://github.com/modelcontextprotocol/servers)

---

**最后更新**: 2026年2月 | **来源**: 汇总自 Claude Code MCP 官方文档和社区最佳实践
