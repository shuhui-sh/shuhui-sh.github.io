---
title: "Claude Code 完整教程：从零基础到高级用户"
date: 2026-04-02
description: "1. 什么是 Claude Code？ 2. 安装与设置 3. 核心功能与命令 4. CLAUDE.md 项目记忆系统"
tags: ['Claude Code']
category: "技术"
---
> 汇总自海外 2026 年最新 Claude Code 教程资源

## 目录

1. [什么是 Claude Code？](#1-什么是-claude-code)
2. [安装与设置](#2-安装与设置)
3. [核心功能与命令](#3-核心功能与命令)
4. [CLAUDE.md 项目记忆系统](#4-claudemd-项目记忆系统)
5. [Plan Mode 计划模式](#5-plan-mode-计划模式)
6. [高级配置与自定义](#6-高级配置与自定义)
7. [最佳实践与技巧](#7-最佳实践与技巧)
8. [常见问题解答](#8-常见问题解答)

---

## 1. 什么是 Claude Code？

**Claude Code** 是 Anthropic 官方推出的 AI 编程助手，直接在终端中运行。它不是简单的代码补全工具，而是一个完整的**智能代理系统**，能够：

- 理解整个代码库（200,000 token 上下文窗口）
- 读取、搜索和分析项目文件
- 执行多文件修改
- 运行命令、测试和构建脚本
- 管理 Git 操作（提交、分支、PR）
- 通过 MCP 连接外部服务

### 与其他 AI 工具的对比

| 功能 | Claude Code | Cursor | GitHub Copilot | ChatGPT |
|------|-------------|--------|----------------|---------|
| **环境** | 终端 CLI + IDE | VS Code 分支 | IDE 插件 | 浏览器 |
| **文件访问** | 完整读写 | 完整读写 | 只读 | 无 |
| **上下文** | 200K tokens | 变化 | 有限 | 变化 |
| **Git 操作** | 完整支持 | 基础支持 | 无 | 无 |
| **子代理** | 7 个并行 | 单个 | 无 | 无 |
| **价格** | $20-200/月 | $20-40/月 | $10-19/月 | $20/月 |

---

## 2. 安装与设置

### 系统要求

- **操作系统**: macOS 13.0+, Ubuntu 20.04+, Windows 10+ (WSL)
- **内存**: 4GB 最低（推荐 8GB+）
- **网络**: 稳定的互联网连接

### 安装方法

#### macOS / Linux（推荐）

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

#### Windows PowerShell

```powershell
irm https://claude.ai/install.ps1 | iex
```

#### 使用 Homebrew（macOS）

```bash
brew install --cask claude-code
```

### 验证安装

```bash
# 检查版本
claude --version

# 运行诊断
claude doctor

# 启动 Claude Code
claude
```

### 认证方式

1. **Claude Pro/Max 订阅**（推荐）- $20-200/月
2. **API 即用即付** - 通过 Claude Console
3. **Teams/Enterprise** - 团队集中管理
4. **云服务商** - Amazon Bedrock, Google Vertex AI

---

## 3. 核心功能与命令

### 必知斜杠命令

| 命令 | 功能 | 使用场景 |
|------|------|----------|
| `/help` | 显示所有可用命令 | 发现功能 |
| `/init` | 扫描项目并创建 CLAUDE.md | 初始化新项目 |
| `/clear` | 清除对话历史 | 切换任务时重置 |
| `/compact` | 压缩对话以节省上下文 | 长会话 |
| `/memory` | 编辑 CLAUDE.md 记忆 | 配置项目上下文 |
| `/config` | 打开配置界面 | 更改设置 |
| `/model` | 切换 AI 模型 | Opus/Sonnet 选择 |
| `/cost` | 查看当前 token 使用 | 监控费用 |
| `/mcp` | 管理 MCP 服务器 | 外部集成 |
| `/context` | 查看当前上下文状态 | 了解 token 使用 |

### 键盘快捷键

| 快捷键 | 功能 |
|--------|------|
| `Escape` | 停止 Claude 的响应 |
| `Escape + Escape` | 打开回退菜单/导航历史消息 |
| `↑` (上箭头) | 浏览过去的对话 |
| `Ctrl + V` (macOS) | 粘贴图片 |
| `Tab` | 自动补全文件路径和命令 |

### 文件引用使用 @

```bash
# 引用特定文件
> 分析 @src/auth.ts 并提出改进建议

# 比较多个文件
> 比较 @package.json 和 @package-lock.json

# 引用目录
> 解释 @src/components/ 的架构

# 引用行范围 (VS Code)
> 修复 @src/utils.ts:42-58 中的 bug
```

---

## 4. CLAUDE.md 项目记忆系统

**CLAUDE.md** 是项目的"大脑"——每个会话开始时自动加载，让 Claude 理解你的项目。

### CLAUDE.md 结构示例

```markdown
# CLAUDE.md - MyApp API

## 技术栈
- .NET 9, ASP.NET Core Minimal APIs
- Entity Framework Core with PostgreSQL
- MediatR for CQRS
- FluentValidation for request validation

## 项目结构
- `src/MyApp.Api/` — 入口点、端点、中间件
- `src/MyApp.Application/` — 用例、处理器、DTO
- `src/MyApp.Domain/` — 实体、值对象、领域事件
- `src/MyApp.Infrastructure/` — EF Core、外部服务

## 命令
- 构建: `dotnet build`
- 测试: `dotnet test`
- 运行: `dotnet run --project src/MyApp.Api`

## 编码规范
- 使用主构造函数进行依赖注入
- 始终将 CancellationToken 传递给异步方法
- 验证放在 FluentValidation 验证器中，不在处理器中
- 永远不要硬编码连接字符串或密钥

## 工作流规则
- 在进行更改之前总是创建 git 分支
- 每次实现后运行 `dotnet test`
- 保持提交原子化和专注
```

### CLAUDE.md 文件层次

| 位置 | 范围 | 用途 |
|------|------|------|
| `~/.claude/CLAUDE.md` | 全局 | 个人偏好，所有项目 |
| `/project/CLAUDE.md` | 项目 | 项目规范，与团队共享 |
| `/project/src/CLAUDE.md` | 目录 | 目录特定上下文 |
| `/project/CLAUDE.local.md` | 个人 | 机器特定，git 忽略 |

---

## 5. Plan Mode 计划模式

Plan Mode 强制 Claude 在编写代码之前**先思考**——就像与高级工程师结对编程。

### 进入 Plan Mode

- 按 `Shift + Tab` 两次循环到 Plan Mode
- Windows 用户：尝试 `Alt + M`

### Plan Mode 的能力限制

在 Plan Mode 中，Claude **只能**：
- 读取文件
- 搜索和 grep 代码
- 浏览文档
- 询问澄清问题

它**不能**：写入、修改或执行任何内容

### 何时使用 Plan Mode

- 开始一个多组件的新功能
- 进行架构更改
- 对方法不确定时
- 在不熟悉的代码库上工作

### 示例对话

```
我: 构建一个家务管理应用，要求：
- 类似 Outlook 的日历视图
- 添加/删除家务
- 循环计划
- 分配家务给团队成员
- 管理团队成员

Claude (Plan Mode):
让我先了解一些细节：
- 应该使用 React、Vue 还是其他框架？
- 本地存储还是后端数据库？
- 需要身份验证吗？
- 有什么特定的 UI 库偏好吗？
```

---

## 6. 高级配置与自定义

### 设置文件层次（优先级从高到低）

1. **托管设置** - 组织策略
2. **项目共享设置** - `.claude/settings.json`
3. **项目本地设置** - `.claude/settings.local.json`
4. **用户设置** - `~/.claude/settings.json`

### 示例：白名单 MCP 和 Git

```json
{
  "permissions": {
    "allow": [
      "Bash(git status)",
      "Bash(git add *)",
      "Bash(git commit *)",
      "Bash(git push *)",
      "Bash(git pull *)",
      "Bash(git checkout *)",
      "Bash(git branch *)",
      "Bash(gh pr *)",
      "Bash(npm *)",
      "Bash(npx *)",
      "mcp__notion__*",
      "mcp__github__*",
      "mcp__postgres__*"
    ],
    "deny": [
      "Bash(rm -rf /)",
      "Bash(sudo *)",
      "Bash(chmod 777 *)"
    ]
  },
  "enableAllProjectMcpServers": true
}
```

### Hooks（钩子）

| 事件 | 描述 | 用例 |
|------|------|------|
| `PreToolUse` | 工具执行前 | 验证、日志 |
| `PostToolUse` | 工具完成后 | 格式化、清理 |
| `SessionStart` | 会话启动时 | 环境设置 |
| `Stop` | Claude 完成响应时 | 后处理 |

#### 示例 Hook 配置

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "prettier --write \"$CLAUDE_FILE_PATH\""
      }]
    }]
  }
}
```

### 自定义斜杠命令

在 `.claude/commands/` 目录中创建 markdown 文件：

```bash
# 创建命令目录
mkdir -p .claude/commands

# 创建测试命令
echo "为 $ARGUMENTS 创建全面的测试：
- 使用 Jest 和 React Testing Library
- 测试主要功能
- 包含边界情况
" > .claude/commands/test.md

# 现在可以在 Claude Code 中使用 /test
```

---

## 7. 最佳实践与技巧

### 性能优化

1. **频繁使用 /clear** - 切换任务时保持性能
2. **使用 /compact** - 压缩长对话
3. **委托给子代理** - 使用 Task 工具处理繁杂操作
4. **具体明确** - 避免模糊请求

### 成本管理

| 策略 | 实现 | 影响 |
|------|------|------|
| 监控使用 | `/cost` 命令 | 实时追踪费用 |
| 使用 Sonnet | `/model sonnet` | 比 Opus 便宜 40% |
| Opus 用于复杂工作 | 仅架构决策 | 优化成本/质量平衡 |

### 提示技巧

- 使用文件引用 (`@file.ts`) 而非粘贴代码
- 明确表达你想要什么
- 提供上下文
- 将复杂任务分解为小步骤
- 使用 `/init` 引导项目上下文

### Git 工作流最佳实践

```bash
# 创建并切换到新分支
> 创建分支 feature/rate-limiting 并切换

# 实现功能
> 实现认证端点的速率限制

# 运行测试
> 运行测试

# 提交更改
> 提交这些更改

# 推送并创建 PR
> 推送并创建 PR 到 main，包含更改摘要
```

---

## 8. 常见问题解答

### Q: 如何修复 npm 安装权限错误？

不要使用 `sudo npm install -g`。改为修复 npm 权限：

```bash
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
export PATH=~/.npm-global/bin:$PATH
```

### Q: 为什么 Claude Code 不理解我的项目结构？

通常意味着 Claude 没有读取足够的上下文。尝试：

1. 创建 `CLAUDE.md` 文件
2. 明确告诉 Claude 探索项目
3. 指向关键文件

### Q: 如何防止 Claude Code 进行不必要的更改？

- 明确指定范围
- 在 `CLAUDE.md` 中添加规则
- 使用 Plan Mode 审查计划

### Q: 当达到速率限制时会发生什么？

1. 收到警告通知
2. 请求减慢或暂停
3. 5 小时窗口后重置

### Q: 我的代码会被发送到 Anthropic 的服务器吗？

是的，Claude Code 将代码发送到 Anthropic 的 API 进行处理。但 Anthropic 声明来自 Pro/Max 订阅的数据**不用于训练模型**。

---

## 参考资源

- [Claude Code 官方文档](https://code.claude.com/docs/en/overview)
- [Claude Code 最佳实践](https://code.claude.com/docs/en/best-practices)
- [Claude Code GitHub](https://github.com/anthropics/claude-code)

---

**最后更新**: 2026年2月 | **来源**: 汇总自多个海外 Claude Code 教程
