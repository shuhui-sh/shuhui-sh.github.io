---
title: "Claude Code 高级技巧：32 个提升效率的技巧"
date: 2026-04-02
description: "1. 基础技巧 2. 工作流优化 3. 高级配置 4. 极客技巧 自定义 Claude Code 底部状态栏，显示有用信息："
tags: ['Claude Code']
draft: true
category: "技术"
---
> 汇编自海外资深用户的实战经验

## 目录

1. [基础技巧](#基础技巧-1-8)
2. [工作流优化](#工作流优化-9-16)
3. [高级配置](#高级配置-17-24)
4. [极客技巧](#极客技巧-25-32)

---

## 基础技巧 (1-8)

### 1. 自定义状态栏

自定义 Claude Code 底部状态栏，显示有用信息：

```bash
Opus 4.5 | 📁Daft | 🔀fix/bug (0 files uncommitted, synced) | █░░░░░░░░░ 12% of 200k tokens used
💬 上次消息内容预览...
```

### 2. 使用语音输入

语音输入比打字更快。尝试本地语音转文字工具：
- **Mac**: superwhisper, MacWhisper
- **优点**: 即使转录有错误，Claude 也能理解

### 3. 问题分解原则

当 Claude 无法一次性解决复杂问题时，将其分解为更小的子问题：

```
A → B (困难)
vs
A → A1 → A2 → A3 → B (更易实现)
```

### 4. 让 Claude 处理 Git

```bash
> 提交这些更改并创建 PR
> 创建分支 feature/new-auth
> 拉取最新更改
```

### 5. 新任务新会话

每个新主题开始新对话，保持最佳性能。长对话会降低性能。

### 6. 轻松复制输出

```bash
# 使用 /copy 命令
/copy

# 让 Claude 使用 pbcopy (Mac)
> 将输出复制到剪贴板

# 写入文件后用编辑器打开
> 将结果写入 output.md 并在 VS Code 中打开
```

### 7. 设置终端别名

```bash
# 添加到 ~/.zshrc 或 ~/.bashrc
alias c='claude'
alias ch='claude --chrome'
alias gb='github'
alias co='code'
alias q='cd ~/Desktop/projects'
```

### 8. 理解上下文压缩

- Opus 4.5 总上下文: 200K tokens
- 约 45K 预留给自动压缩
- 约 10% 被系统提示占用
- 主动使用 `/compact` 获得更多控制

---

## 工作流优化 (9-16)

### 9. Cmd+A / Ctrl+A 是朋友

当 Claude 无法直接访问某个页面时：
1. 全选内容 (Cmd+A/Ctrl+A)
2. 复制粘贴到 Claude
3. 适用于任何 AI，不仅是 Claude Code

### 10. 完成写-测试循环

让 Claude Code 运行 `git bisect` 等自动化任务，关键是提供验证方法：

```bash
# 使用 tmux 进行交互式终端测试
tmux kill-session -t test-session 2>/dev/null
tmux new-session -d -s test-session
tmux send-keys -t test-session 'claude' Enter
sleep 2
tmux send-keys -t test-session '/context' Enter
sleep 1
tmux capture-pane -t test-session -p
```

### 11. 使用 Git Worktree

在多个分支上并行工作：

```bash
> 创建 git worktree 用于分支 feature/A
> 创建 git worktree 用于分支 feature/B
```

### 12. 手动指数退避

等待长时间运行的任务时：

```bash
# 使用指数增长的间隔检查状态
# 1 分钟 → 2 分钟 → 4 分钟 → 8 分钟
> 每隔指数增长的间隔检查 Docker 构建状态
```

### 13. 搜索历史对话

历史存储在 `~/.claude/projects/`：

```bash
# 查找包含 "reddit" 的对话
grep -l -i "reddit" ~/.claude/projects/*/*.jsonl

# 查找今天的对话
find ~/.claude/projects/*/*.jsonl -mtime 0 -exec grep -l "keyword" {} \;
```

### 14. 多任务管理 - 级联法

最多同时处理 3-4 个任务：

```
[最旧] ← [较旧] ← [旧] ← [当前]
  Tab1    Tab2    Tab3    Tab4
```

### 15. 技能 vs 斜杠命令 vs CLAUDE.md

| 功能 | 主要设计给 | 加载时机 |
|------|-----------|---------|
| CLAUDE.md | 项目上下文 | 每次会话 |
| Skills | Claude 自动调用 | 按需 |
| Slash Commands | 用户手动调用 | 按需 |

### 16. 保持 CLAUDE.md 简洁

从没有 CLAUDE.md 开始，只有重复说明同一件事时才添加。

---

## 高级配置 (17-24)

### 17. 减少 System Prompt

Claude Code 的系统提示占用约 18K tokens (~9%)。通过补丁可减少到 10K：

**优化前**: ~18K tokens (9%)
**优化后**: ~10K tokens (5%)

### 18. MCP 延迟加载

启用工具搜索，MCP 工具仅在需要时加载：

```json
{
  "env": {
    "ENABLE_TOOL_SEARCH": "true"
  }
}
```

### 19. 禁用自动更新

当使用自定义系统提示时：

```json
{
  "env": {
    "DISABLE_AUTOUPDATER": "1"
  }
}
```

### 20. 理解 MCP 传输类型

| 传输 | 用例 | 示例 |
|------|------|------|
| HTTP | 远程服务器 | Notion, GitHub, Sentry |
| Stdio | 本地进程 | PostgreSQL, Airtable |
| SSE | 遗留 (已弃用) | 旧集成 |

### 21. 添加 MCP 服务器

```bash
# HTTP 服务器 (推荐)
claude mcp add --transport http notion https://mcp.notion.com/mcp

# 本地 Stdio 服务器
claude mcp add --transport stdio db -- npx -y @bytebase/dbhub --dsn "postgresql://user:pass@host/db"
```

### 22. 配置权限模式

```json
{
  "permissions": {
    "allow": [
      "Bash(git *)",
      "Bash(npm run *)",
      "Read",
      "Write",
      "Edit"
    ],
    "deny": [
      "Bash(rm -rf /*)",
      "Bash(sudo *)"
    ]
  }
}
```

### 23. 危险模式 (高级用户)

```bash
# 跳过所有权限确认
claude --dangerously-skip-permissions
# 或
claude -y
```

⚠️ 仅在可信环境中使用！

### 24. 创建自定义 Hook

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "prettier --write \"$CLAUDE_FILE_PATHS\""
      }]
    }]
  }
}
```

---

## 极客技巧 (25-32)

### 25. 使用 Docker 容器运行 Claude Code

在隔离环境中运行实验性任务：

```dockerfile
FROM ubuntu:22.04
RUN apt update && apt install -y curl nodejs npm
RUN curl -fsSL https://claude.ai/install.sh | bash
# 添加你的自定义配置
CMD ["claude", "--dangerously-skip-permissions"]
```

### 26. 本地 Claude 控制容器中的 Claude

使用 tmux 作为控制层：

1. 本地 Claude 启动 tmux 会话
2. 在 tmux 中运行容器
3. 容器内运行 `--dangerously-skip-permissions`
4. 本地 Claude 使用 `tmux send-keys` 发送命令

### 27. 使用 Gemini CLI 作为辅助

创建技能让 Claude 使用 Gemini 访问它无法直接访问的网站（如 Reddit）：

```
# ~/.claude/skills/reddit-fetch/SKILL.md
当需要访问 Reddit 时，使用 Gemini CLI 通过 tmux 获取内容。
```

### 28. 会话克隆/分叉

```bash
# 分支当前会话
/fork

# 或使用别名
claude -c --fs
```

### 29. 半克隆会话

只保留后半部分对话，减少 token 使用：

```bash
/half-clone
```

### 30. 使用 realpath 获取绝对路径

```bash
realpath some/relative/path
```

### 31. Markdown 写作工作流

1. 用语音给 Claude 上下文
2. 获得初稿
3. 逐行审阅和修改
4. 终端左侧，编辑器右侧

### 32. 十亿 Token 规则

想真正精通 AI 和 Claude Code？消耗大量 token：

- 使用多个并行会话
- 不必担心 token 使用（尤其 Opus 4.5）
- 实践是最好的学习方式

---

## 补充：终端 UI 技巧

### 终端操作

- **Shift+Enter**: 默认不支持换行，先用 `/terminal-setup`
- **拖拽文件**: 默认在新标签打开，按 Shift 拖拽可正确引用
- **粘贴图片**: Windows/Linux 用 Ctrl+V（不是 Cmd+V）
- **停止 Claude**: 用 Escape（不是 Ctrl+C）
- **跳转消息**: ESC+ESC 显示所有历史消息列表

### VS Code 扩展技巧

- **内联差异**: 在侧边栏实时查看更改
- **自动接受模式**: 无需确认即可编辑
- **行范围引用**: @file.ts:42-58
- **多个对话**: 在标签页中打开多个对话

---

**最后更新**: 2026年2月 | **来源**: 汇总自海外 Claude Code 高级用户分享
