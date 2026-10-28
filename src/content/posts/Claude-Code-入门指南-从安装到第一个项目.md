---
title: "Claude Code 入门指南：从安装到第一个项目"
date: 2026-02-11
description: "Claude Code 是 Anthropic 推出的 AI 编程助手，它可以： 与传统的代码补全工具不同，Claude Code 是一个真正的 AI 结对编程伙伴，能够理解上下文、进行多步推理，并主"
tags: ['Claude Code']
category: "技术"
---
> 本文将带你从零开始使用 Claude Code，完成安装配置并创建你的第一个 AI 辅助编程项目。

## 什么是 Claude Code？

Claude Code 是 Anthropic 推出的 AI 编程助手，它可以：

- 🔍 理解你的整个代码库
- ✏️ 自动编写和修改代码
- 🐛 智能调试和修复问题
- 📝 生成文档和测试
- 🚀 执行终端命令

与传统的代码补全工具不同，Claude Code 是一个**真正的 AI 结对编程伙伴**，能够理解上下文、进行多步推理，并主动提出优化建议。

## 系统要求

在开始之前，请确保你的系统满足以下要求：

| 要求 | 说明 |
|-----|------|
| 操作系统 | macOS 10.15+, Windows 10+, Linux (Ubuntu 18.04+) |
| Node.js | v18.0.0 或更高版本 |
| 内存 | 建议 8GB 以上 |
| 网络 | 需要访问 Anthropic API |

## 安装步骤

### 1. 安装 Node.js

如果尚未安装 Node.js，请先安装：

```bash
# macOS (使用 Homebrew)
brew install node

# Windows (使用 Chocolatey)
choco install nodejs

# 或者从官网下载: https://nodejs.org/
```

验证安装：

```bash
node --version  # 应显示 v18.x.x 或更高
npm --version
```

### 2. 安装 Claude Code

使用 npm 全局安装：

```bash
npm install -g @anthropic-ai/claude-code
```

或使用 Homebrew（macOS）：

```bash
brew install claude-code
```

### 3. 配置 API 密钥

首次运行时，Claude Code 会引导你完成认证：

```bash
claude
```

按照提示登录你的 Anthropic 账户，或输入 API 密钥。

> 💡 **提示**：你也可以通过环境变量配置：
> ```bash
> export ANTHROPIC_API_KEY=your_api_key_here
> ```

## 第一个项目：创建 Todo 应用

让我们用 Claude Code 创建一个简单的 Todo 应用，体验 AI 编程的魅力。

### 步骤 1：创建项目目录

```bash
mkdir my-todo-app
cd my-todo-app
claude
```

### 步骤 2：描述你的需求

在 Claude Code 中输入：

```
创建一个简单的 React Todo 应用，包含以下功能：
1. 添加待办事项
2. 标记完成/未完成
3. 删除待办事项
4. 本地存储持久化
请使用 TypeScript 和 Tailwind CSS
```

### 步骤 3：观察 Claude Code 工作

Claude Code 会：

1. 📦 初始化项目结构（`package.json`, `tsconfig.json`）
2. 🎨 配置 Tailwind CSS
3. 📝 创建组件文件
4. 🔧 编写完整的功能代码
5. ✅ 运行检查确保无错误

### 步骤 4：运行项目

```bash
npm install
npm run dev
```

打开浏览器访问 `http://localhost:5173`，你的 Todo 应用就完成了！

## 基本使用技巧

### 常用命令

| 命令 | 说明 |
|-----|------|
| `/help` | 显示帮助信息 |
| `/clear` | 清除对话历史 |
| `/compact` | 压缩上下文 |
| `/cost` | 显示使用成本 |
| `Ctrl+C` | 取消当前操作 |
| `Escape` (双击) | 退出 Claude Code |

### 最佳实践

1. **清晰描述需求**：像和同事沟通一样，说明你想要什么
2. **提供上下文**：告诉 Claude Code 相关的文件或约束
3. **逐步迭代**：大任务拆解成小步骤
4. **代码审查**：始终检查 AI 生成的代码

## 常见问题

### Q: 为什么 Claude Code 看不到我的文件？

确保在项目根目录启动 Claude Code，它会自动扫描并索引代码库。

### Q: 如何处理大型项目？

Claude Code 支持智能上下文管理，只加载相关文件。你也可以使用 `.claudeignore` 排除不需要的目录。

### Q: 会产生多少费用？

Claude Code 使用 Anthropic API，费用基于 token 使用量。可使用 `/cost` 命令查看当前会话成本。

## 下一步

- 📖 阅读 [Claude Code 最佳实践](/articles/claude-code-best-practices)
- 🔧 探索 [高级功能与工作流](/articles/claude-code-advanced)
- 🎯 查看 [实战案例](/articles/claude-code-case-studies)

---

*本文基于 Claude Code 官方文档和社区最佳实践整理，如有更新请以官方为准。*
