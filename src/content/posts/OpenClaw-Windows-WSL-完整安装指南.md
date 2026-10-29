---
title: "OpenClaw Windows(WSL) 完整安装指南"
date: 2026-04-02
description: "本教程提供在 Windows 11 WSL 环境下安装和配置 OpenClaw 的完整流程，涵盖从环境初始化到国内 API 配置的全部步骤，适合零基础新手用户。 1."
tags: ['OpenClaw']
draft: true
category: "技术"
---
本教程提供在 Windows 11 WSL 环境下安装和配置 OpenClaw 的完整流程，涵盖从环境初始化到国内 API 配置的全部步骤，适合零基础新手用户。

## 目录

- [一、快速开始](#一快速开始)
- [二、前置知识](#二前置知识)
- [三、WSL 安装与网络配置](#三wsl-安装与网络配置)
- [四、国内镜像源配置](#四国内镜像源配置)
- [五、OpenClaw 安装](#五openclaw-安装)
- [六、使用 Claude Code 配置国内 API](#六使用-claude-code-配置国内-api)
- [七、服务管理与访问](#七服务管理与访问)
- [八、高级配置](#八高级配置)
- [九、常见问题 FAQ](#九常见问题-faq)
- [十、相关资源](#十相关资源)

---

## 一、快速开始

> 本章节面向有经验的用户，Windows系统中已有WSL环境的，提供快速安装指引。零基础新手请跳转到[第二章](#二前置知识)。

**1. 安装 WSL（PowerShell 管理员）**

```powershell
wsl --install
```

**2. 重启后，创建配置文件 `C:\Users\<用户名>\.wslconfig`**

```ini
[wsl2]
networkingMode=mirrored
dnsTunneling=true
autoProxy=true
firewall=true

[experimental]
autoMemoryReclaim=gradual
hostAddressLoopback=true
```

**3. 应用配置**

```powershell
wsl --shutdown
```

**4. 进入 WSL，配置国内镜像源后安装 OpenClaw**

```bash
curl -fsSL https://molt.bot/install.sh | bash
```

**5. 运行初始化向导**

```bash
openclaw onboard --install-daemon
```

**6. 使用 Claude Code 配置国内 API**

安装完 OpenClaw 后，推荐使用 Claude Code 自动完成 API Key 写入，参考[第六章](#六使用-claude-code-配置国内-api)。

**7. 重启服务**

```bash
openclaw gateway restart
```

---

## 二、前置知识

### 2.1 核心概念简介

**WSL（Windows Subsystem for Linux）**

- 微软官方提供的 Windows 子系统，可在 Windows 上原生运行 Linux 环境
- 无需虚拟机，性能优异，与 Windows 文件系统无缝集成

**OpenClaw**

- 本地 AI 编程助手，支持多种大语言模型（LLM）
- 提供 MCP（Model Context Protocol）插件协议，可扩展各种功能
- 支持国内 API（MiniMax、智谱 GLM）

**MCP（Model Context Protocol）**

- AI 插件协议，允许 LLM 调用外部工具和服务
- 社区有丰富的 MCP 服务器（浏览器、数据库、文件系统等）

### 2.2 系统要求

| 要求项  | 最低配置             | 推荐配置           |
| ---- | ---------------- | -------------- |
| 操作系统 | Windows 11 22H2+ | Windows 11 最新版 |
| 内存   | 8GB RAM          | 16GB+ RAM      |
| 存储   | 10GB 可用空间        | 30GB+ SSD      |
| 网络   | 稳定网络连接           | 配置代理更佳         |

---

## 三、WSL 安装与网络配置

### 3.1 安装 WSL

WSL（适用于 Linux 的 Windows 子系统）目前有两个主要版本：

| 版本    | 说明                  | 推荐度   |
| ----- | ------------------- | ----- |
| WSL 1 | 早期版本，采用系统调用转换层      | ⭐⭐    |
| WSL 2 | 运行完整的 Linux 内核，性能更佳 | ⭐⭐⭐⭐⭐ |

**强烈建议使用 WSL 2**。

#### 一键安装 WSL

在具有管理员权限的 PowerShell 或 Windows 终端中，执行以下命令：

```powershell
wsl --install
```

此命令将自动执行：

1. 启用虚拟机平台（Virtual Machine Platform）
2. 启用适用于 Linux 的 Windows 子系统
3. 下载并安装最新的 Linux 内核
4. 默认下载并安装 Ubuntu 发行版

安装完成后，**必须重启计算机**以使 Hyper-V 管理程序生效。

#### 验证安装状态

重启后，通过以下命令验证：

```powershell
wsl --status
wsl --version
```

**预期输出示例**：

```
WSL 版本: 2.0.xxxx.0
内核版本: 5.15.xxxx
Windows 版本: 10.0.22631.xxxx
```

#### 现有 WSL 用户更新

如果系统中已存在旧版 WSL，建议运行以下命令更新：

```powershell
wsl --update
```

### 3.2 Ubuntu 初始化

首次启动 Ubuntu 时，系统会提示创建 UNIX 用户名和密码：

```
Installing, this may take a few minutes...
Please create a default UNIX user account. The username and password must not match your Windows username.
New UNIX username: spoto
New password:
Retype new password:
```

此账户拥有 `sudo` 权限，是后续执行安装操作的核心身份。

### 3.3 WSL 网络模式配置

WSL 2 有两种网络模式，选择正确的模式对后续使用至关重要。

#### NAT 模式 vs 镜像模式

| 维度      | NAT 模式 (默认)         | 镜像模式 (推荐)        |
| ------- | ------------------- | ---------------- |
| IP 地址   | 独立虚拟 IP (172.x.x.x) | 与宿主机共享相同局域网 IP   |
| IPv6 支持 | 极其有限                | 全面原生支持           |
| VPN 兼容性 | 经常导致 DNS 丢包         | 显著提升兼容性          |
| 局域网可见性  | 需要手动端口转发            | 局域网内其他设备可直接发现    |
| 防火墙控制   | 独立规则                | 直接使用 Windows 防火墙 |

**推荐使用镜像模式**。

#### 配置镜像网络模式

**步骤 1**：打开文件资源管理器，导航到以下路径：

```
C:\Users\<您的用户名>\
```

**步骤 2**：创建或修改名为 `.wslconfig` 的文件（注意前面的点号）

**步骤 3**：使用记事本打开文件，添加以下配置：

```ini
[wsl2]
# 启用镜像网络模式 - 这是最重要的配置
networkingMode=mirrored
# 启用 DNS 隧道，防止 VPN 环境下域名解析失效
dnsTunneling=true
# 强制 WSL 使用 Windows 的 HTTP 代理设置
autoProxy=true
# 启用集成防火墙支持
firewall=true

[experimental]
# 自动回收闲置内存，优化性能
autoMemoryReclaim=gradual
# 支持主机回环地址访问
hostAddressLoopback=true
```

**步骤 4**：保存文件

**步骤 5**：在 Windows 终端中执行以下命令以应用配置：

```powershell
wsl --shutdown
```

**步骤 6**：等待约 8 秒钟以确保虚拟机彻底关闭，然后重新启动 Ubuntu

#### 验证网络模式

进入 WSL 后，执行以下命令验证：

```bash
# 查看网络接口
ip addr show

# 查看路由表
ip route show

# 测试与局域网的连通性
ping 192.168.1.1
```

如果配置成功，WSL 将使用与 Windows 相同的局域网 IP 地址段。

### 3.4 防火墙配置

在镜像模式下，WSL2 应用将直接暴露在 Windows 防火墙规则中。

#### 创建防火墙规则

以管理员身份打开 PowerShell，执行以下命令：

```powershell
# 创建入站防火墙规则，允许 OpenClaw 服务端口
New-NetFirewallRule -DisplayName "OpenClaw-Service" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 18789

# 验证规则是否创建成功
Get-NetFirewallRule -DisplayName "OpenClaw-Service" | Format-Table
```

#### 测试端口连通性

```powershell
# 测试本地端口
Test-NetConnection -ComputerName localhost -Port 18789
```

---

## 四、国内镜像源配置

在国内使用 WSL 安装 OpenClaw 及相关依赖时，配置国内镜像源可以显著加速下载。

### 4.1 Ubuntu APT 源

#### 备份原配置

```bash
sudo cp /etc/apt/sources.list /etc/apt/sources.list.bak
```

#### 配置清华镜像源

**Ubuntu 24.04 (Noble)**：

```bash
sudo tee /etc/apt/sources.list << 'EOF'
# 清华大学镜像源 - Ubuntu 24.04 (noble)
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ noble main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ noble-updates main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ noble-backports main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ noble-security main restricted universe multiverse
EOF
```

**Ubuntu 22.04 (Jammy)**：

```bash
sudo tee /etc/apt/sources.list << 'EOF'
# 清华大学镜像源 - Ubuntu 22.04 (jammy)
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-updates main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-backports main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-security main restricted universe multiverse
EOF
```

#### 更新软件包索引

```bash
sudo apt update && sudo apt upgrade -y
```

#### 其他可选镜像源

| 镜像源  | 地址                                             |
| ---- | ---------------------------------------------- |
| 清华大学 | `https://mirrors.tuna.tsinghua.edu.cn/ubuntu/` |
| 阿里云  | `https://mirrors.aliyun.com/ubuntu/`           |
| 中科大  | `https://mirrors.ustc.edu.cn/ubuntu/`          |
| 华为云  | `https://repo.huaweicloud.com/ubuntu/`         |

### 4.2 npm 镜像源

```bash
# 设置淘宝镜像（npmmirror.com）
npm config set registry https://registry.npmmirror.com

# 验证配置
npm config get registry
```

### 4.3 pip 镜像源

```bash
# 创建配置目录
mkdir -p ~/.pip

# 写入配置文件
cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
EOF
```

### 4.4 一键配置脚本

将以下脚本保存为 `setup-mirrors.sh`，一键配置所有常用镜像：

```bash
#!/bin/bash
# WSL 国内镜像源一键配置脚本

echo "=== 配置 APT 源（清华镜像）==="
sudo cp /etc/apt/sources.list /etc/apt/sources.list.bak 2>/dev/null
CODENAME=$(lsb_release -cs)
sudo tee /etc/apt/sources.list << EOF
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ $CODENAME main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ $CODENAME-updates main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ $CODENAME-backports main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ $CODENAME-security main restricted universe multiverse
EOF
sudo apt update

echo "=== 配置 npm 源（淘宝镜像）==="
npm config set registry https://registry.npmmirror.com

echo "=== 配置 pip 源（清华镜像）==="
mkdir -p ~/.pip
cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
EOF

echo "=== 配置完成！==="
```

运行脚本：

```bash
chmod +x setup-mirrors.sh
./setup-mirrors.sh
```

---

## 五、OpenClaw 安装

### 5.1 基础环境配置

#### 安装基础工具

```bash
sudo apt install -y curl wget git
```

#### 配置 sudo 免密（可选）

为了避免在后续安装脚本运行中频繁输入密码，可以为当前用户开启 `sudo` 免密权限：

```bash
sudo visudo
```

在文件末尾添加以下内容（将 `your_username` 替换为你的实际用户名）：

```
your_username ALL=(ALL) NOPASSWD: ALL
```

保存并退出（Ctrl+O → Enter → Ctrl+X）。

### 5.2 安装 OpenClaw

使用官方提供的一键安装脚本进行部署：

```bash
curl -fsSL https://molt.bot/install.sh | bash
```

### 5.3 运行初始化向导

安装完成后，运行初始化向导完成基本配置：

```bash
openclaw onboard --install-daemon
```

安装结束后会自动出现提示信息，请根据提示信息完成 OpenClaw 配置，参考配置如下：

| 配置项                                                           | 配置内容                         |
| ------------------------------------------------------------- | ---------------------------- |
| I understand this is powerful and inherently risky. Continue? | 选择 **"Yes"**                 |
| Onboarding mode                                               | 选择 **"QuickStart"**          |
| Model/auth provider                                           | 选择 **"Skip for now"**，后续可以配置 |
| Filter models by provider                                     | 选择 **"All providers"**       |
| Default model                                                 | 使用默认配置                       |
| Select channel (QuickStart)                                   | 选择 **"Skip for now"**，后续可以配置 |
| Configure skills now? (recommended)                           | 选择 **"No"**，后续可以配置           |
| Enable hooks?                                                 | 按空格键选中选项，按回车键进入下一步           |
| How do you want to hatch your bot?                            | 选择 **"Hatch in TUI"**        |

### 5.4 验证安装

```bash
# 检查 OpenClaw 版本
openclaw --version

# 检查 Gateway 状态
openclaw gateway status
```

---

## 六、配置国内大模型 API

完成 OpenClaw 安装后，需要将 `~/.openclaw/openclaw.json` 中的 LLM 配置设置为国内 大模型API。以下提供两种方式供选择。

### 6.1 推荐：阿里百炼 Code Plan

国内用户在选择大模型服务商时，推荐优先试试 **阿里百炼 Code Plan**（Lite 版）。理由如下：

- **价格低廉**：首个月仅需 7.5 元，第二个月也只要 20 元（原价 40 元），适合个人开发者低成本上手。
- **一站式多模型访问**：订阅后不仅能使用阿里自家模型，还能直接调用阿里平台部署的 **智谱**、**MiniMax** 等最新公开模型，无需逐一前往各厂商官网注册和订阅，节省时间和管理成本。
- **开箱即用**：API 格式兼容主流标准，接入 OpenClaw 配置简单。

> 🔗 **订阅 Code Plan**：https://www.aliyun.com/benefit/ai/aistar?userCode=4kjozvjm&clubBiz=subTask..12417291..10263..
> 
> 📖 **阿里百炼 Code Plan 配置 OpenClaw 官方文档**：https://help.aliyun.com/zh/model-studio/openclaw-coding-plan

完成订阅后，可参考上方官方文档获取 API Key 并完成 OpenClaw 对接，也可继续按照 6.2 节使用 Claude Code 自动完成配置。

<!-- 原图缺失: C:\Users\Administrator\AppData\Roaming\marktext\images\2026-03-01-19-49-39-bef3e3a6581340746631103e787d5409.jpg -->

> 💡 截止目前，近一个月，我前前后后使用过智谱GLM4.7，GLM5.0, Deepseek 3.2，MiniMax2.5，以及阿里Qwen3-max，这些模型在openclaw上都不能持续自主地运行任务，总是中断，来询问我的意见，直到前2天切换成qwen3.5-plus, 这个时候才体验到海外那些人使用claude 4.5 等先进模型的那种类似体验。Agent的能力和大模型能力强相关，虽然现在国内模型能力比海外领先模型还有差距，但是以我们在一线的使用体验来看，这个差距不是很大，大概就是半年，所以说现在去了解这些Agent的应用恰当其时，半年后等国产模型能力上来后会迎来一个质的体验飞跃。

### 6.2 使用 Claude Code 配置国内 API

手动编辑 JSON 配置文件容易出错，**推荐使用 Claude Code 来完成这一步**——它能自动定位配置文件、写入正确的字段格式，并运行测试请求验证配置是否生效。

#### 6.2.1 前置：安装并配置 Claude Code

如果你还没有安装 Claude Code，请参考配套文章：

**《国内安装 Claude Code 并切换使用国内大模型 API：完整指南》**

该文章涵盖：

- Claude Code 的安装方式（原生客户端，无需 Node.js）
- 如何获取 DeepSeek、阿里百炼、智谱 GLM 等国内 API Key
- 如何配置 `~/.claude/settings.json` 让 Claude Code 使用国内 API

> 💡 Claude Code 本身也需要一个大模型 API 才能运行。建议先用 DeepSeek 作为 Claude Code 的底层模型（成本最低），再用 Claude Code 来帮你配置 OpenClaw 的 API。

#### 6.2.2 用 Claude Code 配置 OpenClaw API

Claude Code 安装并连接好国内 API 之后，进入你的工作目录，启动 Claude Code：

```bash
cd ~
claude
```

然后直接用自然语言描述你想要的配置，例如：

**配置 MiniMax：**

```
帮我配置 OpenClaw 使用 MiniMax 国内 API。
配置文件在 ~/.openclaw/openclaw.json，
我的 API Key 是 <你的 MiniMax API Key>。
配置好之后重启 Gateway 并验证模型列表是否正常。
```

**配置智谱 GLM：**

```
帮我配置 OpenClaw 使用智谱 GLM API。
配置文件在 ~/.openclaw/openclaw.json，
我的 API Key 是 <你的智谱 API Key>。
配置好之后重启 Gateway 并验证模型列表是否正常。
```

Claude Code 会自动完成以下步骤：

1. 读取 `~/.openclaw/openclaw.json` 当前内容
2. 备份配置文件（生成 `.backup`）
3. 写入正确的 provider 配置块（baseUrl、apiKey、model 列表等）
4. 执行 `openclaw gateway restart`
5. 执行 `openclaw models list` 验证模型是否出现

#### 6.2.3 配置文件参考格式

如果你需要了解配置文件的字段结构，以下是两个服务商的参考格式，**不需要手动复制粘贴**，让 Claude Code 来写即可：

**MiniMax 参考：**

```json
{
  "models": {
    "mode": "merge",
    "providers": {
      "minimax-cn": {
        "baseUrl": "https://api.minimaxi.com/anthropic",
        "apiKey": "YOUR_MINIMAX_API_KEY_HERE",
        "api": "anthropic-messages",
        "models": [
          {
            "id": "MiniMax-M2.5",
            "name": "MiniMax M2.5 (China)",
            "reasoning": true,
            "input": ["text"],
            "contextWindow": 204800,
            "maxTokens": 131072
          }
        ]
      }
    }
  }
}
```

**智谱 GLM 参考：**

```json
{
  "models": {
    "mode": "merge",
    "providers": {
      "zhipu-cn": {
        "baseUrl": "https://open.bigmodel.cn/api/anthropic",
        "apiKey": "YOUR_ZHIPU_API_KEY_HERE",
        "api": "anthropic-messages",
        "models": [
          {
            "id": "glm-4",
            "name": "GLM-4 (China)",
            "reasoning": true,
            "input": ["text"],
            "contextWindow": 200000,
            "maxTokens": 8192
          }
        ]
      }
    }
  }
}
```

#### 6.2.4 手动备份配置

无论是否使用 Claude Code，修改配置前请先手动备份：

```bash
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.backup
```

配置出错时可通过以下命令恢复：

```bash
cp ~/.openclaw/openclaw.json.backup ~/.openclaw/openclaw.json
openclaw gateway restart
```

---

## 七、服务管理与访问

### 7.1 Gateway 命令大全

| 命令                           | 说明               |
| ---------------------------- | ---------------- |
| `openclaw gateway status`    | 检查 Gateway 状态    |
| `openclaw gateway install`   | 安装 Gateway 为系统服务 |
| `openclaw gateway start`     | 启动 Gateway 服务    |
| `openclaw gateway stop`      | 停止 Gateway 服务    |
| `openclaw gateway restart`   | 重启 Gateway 服务    |
| `openclaw gateway uninstall` | 卸载 Gateway 服务    |
| `openclaw logs --follow`     | 实时查看日志           |

#### 前台运行模式（调试用）

```bash
# 基础前台运行
openclaw gateway --port 18789

# 详细日志模式
openclaw gateway --port 18789 --verbose

# 强制启动（忽略 TS 编译警告）
openclaw gateway --force
```

#### 状态检查选项

```bash
# 深度扫描（包括系统服务）
openclaw gateway status --deep

# 跳过 RPC 探测（网络故障时有用）
openclaw gateway status --no-probe

# JSON 输出（适合脚本）
openclaw gateway status --json
```

### 7.2 systemd 服务配置

WSL 环境下，OpenClaw Gateway 作为 systemd 用户服务运行。

#### 启用服务自启动

```bash
# 启用 lingering（必须，使服务在登出后继续运行）
sudo loginctl enable-linger $USER

# 启用并启动服务
systemctl --user enable --now openclaw-gateway.service

# 查看服务状态
systemctl --user status openclaw-gateway

# 查看服务日志
journalctl --user -u openclaw-gateway -f
```

#### 启用 WSL systemd

编辑 `/etc/wsl.conf`：

```bash
sudo nano /etc/wsl.conf
```

添加或确认以下内容：

```ini
[boot]
systemd=true
```

重启 WSL：

```powershell
wsl --shutdown
```

### 7.3 Control UI 访问

#### 本地访问

```bash
# 打开 Dashboard
openclaw dashboard

# 或直接访问
# http://127.0.0.1:18789/
```

#### 局域网访问配置

编辑 `~/.openclaw/openclaw.json`：

```bash
nano ~/.openclaw/openclaw.json
```

修改 Gateway 配置：

```json
{
  "gateway": {
    "port": 18789,
    "mode": "local",
    "bind": "lan",
    "auth": {
      "mode": "token",
      "token": "your_token_here"
    },
    "controlUi": {
      "allowInsecureAuth": true
    }
  }
}
```

获取本机局域网 IP：

```bash
ip addr show | grep -E "inet " | awk '{print $2}' | cut -d'/' -f1 | grep -v "^127"
```

访问地址：`http://<局域网IP>:18789/`

---

## 八、高级配置

### 8.1 浏览器技能配置

OpenClaw 的 Browser 技能需要 Chrome 或 Brave 浏览器。WSL2 支持 WSLg，可以原生显示 Linux GUI 应用。

#### 安装 Chrome

```bash
# 下载并安装 Chrome
cd /tmp
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
sudo apt-get install -f -y

# 验证安装
google-chrome --version
```

#### 浏览器窗口不显示问题

如果 Linux 浏览器窗口没有在 Windows 桌面显示：

```powershell
# 在 PowerShell 中更新 WSL
wsl --update
wsl --shutdown
```

然后重新启动 WSL。

#### 浏览器代理配置

WSL 中的 Linux Chrome 不会自动使用 Windows 上配置的代理（如 Clash），需要单独配置才能访问 Google 等海外网站。

**方法 1：命令行参数启动（临时）**

在终端中使用代理参数启动 Chrome：

```bash
google-chrome --proxy-server="http://127.0.0.1:7890"
```

**方法 2：创建 wrapper 脚本（永久生效，推荐）**

让每次启动 Chrome 都自动使用代理：

```bash
# 创建本地 bin 目录
mkdir -p ~/bin

# 创建代理包装脚本（同时启用代理和远程调试端口）
cat > ~/bin/google-chrome << 'EOF'
#!/bin/bash
# Chrome 代理包装脚本 - 自动添加代理和 CDP 远程调试端口
/usr/bin/google-chrome --proxy-server="http://127.0.0.1:7890" --remote-debugging-port=9222 "$@"
EOF

# 添加执行权限
chmod +x ~/bin/google-chrome

# 确保 ~/bin 在 PATH 最前面
grep -q 'export PATH="$HOME/bin:$PATH"' ~/.bashrc || echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

配置完成后，每次输入 `google-chrome` 都会自动使用代理。

**验证代理是否生效**：

```bash
# 启动 Chrome 并访问 IP 检测网站
google-chrome https://ip.sb
```

如果显示的是代理服务器所在地区的 IP，说明代理已生效。

#### Browser Service 配置

编辑 `~/.openclaw/openclaw.json`：

```json
{
  "tools": {
    "browser": {
      "enabled": true,
      "headless": false,
      "profiles": 2
    }
  }
}
```

#### 安装 Chrome 浏览器扩展

OpenClaw 提供了 Chrome 浏览器扩展（Browser Relay），用于将 OpenClaw 连接到现有的 Chrome 标签页，实现浏览器自动化控制。

**步骤 1：安装扩展文件**

```bash
# 安装扩展到本地目录
openclaw browser extension install

# 查看扩展安装路径
openclaw browser extension path
```

扩展默认安装在：`~/.openclaw/browser/chrome-extension`

**步骤 2：在 Chrome 中加载扩展**

1. 打开 Chrome 浏览器，访问 `chrome://extensions/`
2. 开启右上角的**"开发者模式"**
3. 点击**"加载已解压的扩展程序"**
4. 导航到扩展目录并选择

**⚠️ 常见问题：找不到 `.openclaw` 目录**

在 WSL 中运行的 Chrome 文件选择器默认不显示隐藏目录（以 `.` 开头的目录）。

**解决方案**：

- **方法 1（推荐）**：在文件选择器对话框中按 **Ctrl + H** 切换显示隐藏文件，然后导航到 `/home/<用户名>/.openclaw/browser/chrome-extension`

- **方法 2**：创建软链接到非隐藏目录
  
  ```bash
  ln -s ~/.openclaw/browser/chrome-extension ~/openclaw-chrome-extension
  ```
  
  然后在文件选择器中选择 `/home/<用户名>/openclaw-chrome-extension`

**步骤 3：配置扩展**

扩展加载成功后，需要配置 Gateway Token：

1. 右键点击扩展图标 → 选择**"选项"**
2. 填入以下配置：
   - **Port**：`18792`（默认值）
   - **Gateway token**：你的 Gateway 认证 Token

获取 Gateway Token：

```bash
# 方法 1：通过命令获取（会显示为 REDACTED）
openclaw config get gateway.auth.token

# 方法 2：直接从配置文件读取
grep -A2 '"auth"' ~/.openclaw/openclaw.json | grep token
```

配置成功后，扩展选项页面会显示：

```
Relay reachable and authenticated at http://127.0.0.1:18792/
```

**步骤 4：使用扩展**

1. 将扩展固定到 Chrome 工具栏（点击拼图图标 → 点击 OpenClaw 旁边的📌）
2. 打开要控制的网页
3. 点击工具栏上的 OpenClaw 扩展图标进行 attach/detach

### 8.2 Skills 启用

**Skills** - OpenClaw 的扩展功能模块。

编辑 `~/.openclaw/openclaw.json`：

```json
{
  "skills": {
    "allowBundled": [
      "mcporter",
      "browser",
      "web-search"
    ]
  }
}
```

#### mcporter 配置

**mcporter** - MCP 配置共享工具，可复用 Cursor/Claude Desktop 的 MCP 配置。

安装 mcporter：

```bash
sudo npm install -g mcporter
```

启用后，OpenClaw 可以自动检测并使用以下配置文件：

- `~/.cursor/mcp.json` - Cursor 的 MCP 配置
- `~/.claude/mcp.json` - Claude Desktop 的 MCP 配置

### 8.3 Telegram 渠道配置

**Telegram** - 通过 Telegram Bot 与 OpenClaw 进行对话的渠道。

#### 创建 Telegram Bot

1. 在 Telegram 中搜索 `@BotFather` 并发送 `/newbot`
2. 按提示设置 Bot 名称和用户名
3. 保存返回的 **Bot Token**（格式如：`123456789:ABCdefGHIjklMNOpqrsTUVwxyz`）

#### 配置 Telegram 渠道

编辑 `~/.openclaw/openclaw.json`：

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "YOUR_TELEGRAM_BOT_TOKEN"
    }
  }
}
```

#### ⚠️ 常见问题：Telegram API 连接失败

**问题表现**：`openclaw status --deep` 显示 Telegram 状态异常，或 Bot 无法收发消息。

**原因分析**：

- Telegram API (`api.telegram.org`) 在国内无法直接访问
- Node.js 的 `fetch()` 不会自动使用系统代理环境变量

**解决方案**：在 Telegram 配置中显式指定代理：

```bash
# 使用命令行配置代理
openclaw config set channels.telegram.proxy "http://127.0.0.1:7890"
```

或手动编辑配置文件：

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "YOUR_TELEGRAM_BOT_TOKEN",
      "proxy": "http://127.0.0.1:7890"
    }
  }
}
```

配置完成后重启 Gateway：

```bash
openclaw gateway restart

# 验证 Telegram 连接状态
openclaw status --deep
```

成功后应显示：

```
Telegram: OK
```

### 8.4 Brave Search 配置

**Brave Search** - 网页搜索技能。

获取 API Key：https://brave.com/search/api/

#### 方法一：使用配置命令

```bash
openclaw configure --section web
```

#### 方法二：手动编辑配置

编辑 `~/.openclaw/openclaw.json`：

```json
{
  "tools": {
    "web": {
      "search": {
        "apiKey": "your_brave_api_key"
      }
    }
  }
}
```

### 8.5 环境变量

| 变量                       | 说明               |
| ------------------------ | ---------------- |
| `OPENCLAW_HOME`          | 设置 Home 目录       |
| `OPENCLAW_STATE_DIR`     | 覆盖状态目录           |
| `OPENCLAW_CONFIG_PATH`   | 覆盖配置文件路径         |
| `OPENCLAW_GATEWAY_TOKEN` | Gateway 认证 Token |

### 8.6 TUI 终端界面

```bash
# 启动终端用户界面
openclaw tui

# 退出 TUI
/exit
```

---

## 九、常见问题 FAQ

### Q1: Gateway 启动失败

**解决方案**：

```bash
# 检查配置文件语法
cat ~/.openclaw/openclaw.json | jq

# 查看日志
tail -f ~/.openclaw/logs/gateway.log

# 恢复备份配置
cp ~/.openclaw/openclaw.json.backup ~/.openclaw/openclaw.json

# 重启服务
openclaw gateway restart
```

### Q2: 局域网无法访问

**解决方案**：

```bash
# 检查防火墙状态
sudo ufw status
sudo ufw allow 18789/tcp

# 检查 Gateway 状态
openclaw gateway status

# 检查 bind 配置
grep '"bind"' ~/.openclaw/openclaw.json
```

### Q3: 模型未显示在列表中

**解决方案**：

1. 检查 JSON 语法是否正确
2. 确认 provider 名称与模型引用一致
3. 确认 API key 有效且有访问权限
4. 重启 Gateway：`openclaw gateway restart`

### Q4: 镜像模式不生效

**解决方案**：

1. 确认已执行 `wsl --shutdown` 并等待 8 秒后重新启动
2. 检查 `.wslconfig` 文件路径是否正确（`C:\Users\<用户名>\.wslconfig`）
3. 确认 WSL 版本为 2.0 以上
4. 更新 WSL 内核：`wsl --update`

### Q5: .bashrc 语法错误导致 Shell 无法启动

**问题表现**：

```
-bash: /home/user/.bashrc: line 163: syntax error near unexpected token `('
```

**原因分析**：

- Windows 的 `PATH` 环境变量会被 WSL 继承
- Windows PATH 中包含带括号的路径，如 `C:\Program Files (x86)\...`
- 如果 `.bashrc` 中的 `export PATH=...` 语句没有使用双引号，bash 会将括号解释为子 shell 语法

**解决方案**：

**步骤 1**：使用 `--norc` 参数启动 bash（绕过 `.bashrc`）：

```bash
wsl -d Ubuntu -u your_username -e bash --norc
```

**步骤 2**：修复 `.bashrc` 文件：

```bash
# 查看问题行
sed -n '160,170p' ~/.bashrc

# 备份原文件
cp ~/.bashrc ~/.bashrc.backup

# 删除损坏的 PATH 行（根据实际行号调整）
sed -i '163d' ~/.bashrc

# 添加正确格式的 PATH（注意使用双引号）
echo 'export PATH="/home/your_username/.openclaw/venv/bin:$PATH"' >> ~/.bashrc
```

**步骤 3**：验证修复：

```bash
source ~/.bashrc
echo $PATH
```

### Q6: OpenClaw 网络代理配置

**问题表现**：OpenClaw 的 `web_search` 工具无法访问外部网络，报错 `fetch failed`。

**原因分析**：

1. OpenClaw Gateway 作为 systemd 用户服务运行时，不会自动继承 `.bashrc` 中的环境变量
2. Node.js 的原生 `fetch()` 不会自动使用 `HTTP_PROXY` 环境变量

**解决方案**：

**方法 1：配置 systemd 服务环境变量（推荐）**

编辑 OpenClaw Gateway 服务文件：

```bash
nano ~/.config/systemd/user/openclaw-gateway.service
```

在 `[Service]` 部分添加代理环境变量：

```ini
[Service]
Environment="HTTP_PROXY=http://127.0.0.1:7890"
Environment="HTTPS_PROXY=http://127.0.0.1:7890"
Environment="http_proxy=http://127.0.0.1:7890"
Environment="https_proxy=http://127.0.0.1:7890"
Environment="NO_PROXY=localhost,127.0.0.1,::1"
```

重载并重启服务：

```bash
systemctl --user daemon-reload
systemctl --user restart openclaw-gateway
```

**方法 2：使用 Clash TUN 模式（最简单）**

如果你使用 Clash 作为代理软件，可以启用 TUN 模式，让所有网络流量自动通过代理。

### Q7: systemd 用户服务不自动启动

**问题表现**：每次启动 WSL 后，OpenClaw Gateway 服务没有自动运行。

**解决方案**：

```bash
# 步骤 1：确认 WSL 已启用 systemd
sudo nano /etc/wsl.conf
```

添加或确认以下内容：

```ini
[boot]
systemd=true
```

```bash
# 步骤 2：重启 WSL
wsl --shutdown

# 步骤 3：启用服务自启动
systemctl --user enable openclaw-gateway

# 步骤 4：启用用户服务的持久化
sudo loginctl enable-linger $USER
```

### Q8: Browser control service timed out

**解决方案**：

```bash
# 检查浏览器进程
ps aux | grep chrome

# 重启 Gateway
openclaw gateway restart

# 检查 CDP 端口
netstat -tlnp | grep 9222
```

### Q9: Gateway 端口被占用

**解决方案**：

```bash
# 查找占用端口的进程
lsof -i :18789

# 杀死进程
kill -9 <PID>
```

---

## 十、相关资源

### 配套文章

- [国内安装 Claude Code 并切换使用国内大模型 API：完整指南](#)（本系列上篇，包含 API Key 获取、Claude Code 配置方法）

### 官方资源

- [OpenClaw 官方文档](https://docs.openclaw.ai)
- [OpenClaw GitHub](https://github.com/openclaw/openclaw)

### 国内 API 服务商

- [MiniMax 官网](https://www.minimaxi.com)
- [智谱 AI 官网](https://bigmodel.cn)

### 参考教程

- [Shambix WSL 安装教程](https://www.shambix.com/how-to-install-openclaw-on-windows-11-with-wsl/)
- [OpenClaw FAQ](https://openclaws.io/faq)

---

## 附录

### A. 常用镜像源速查表

| 类型     | 推荐镜像         | 地址                                             |
| ------ | ------------ | ---------------------------------------------- |
| APT    | 清华大学         | `https://mirrors.tuna.tsinghua.edu.cn/ubuntu/` |
| npm    | 淘宝 npmmirror | `https://registry.npmmirror.com`               |
| pip    | 清华大学         | `https://pypi.tuna.tsinghua.edu.cn/simple`     |
| Docker | 中科大          | `https://docker.mirrors.ustc.edu.cn`           |

### B. OpenClaw 配置文件路径

| 文件             | 路径                                                |
| -------------- | ------------------------------------------------- |
| 主配置            | `~/.openclaw/openclaw.json`                       |
| 配置备份           | `~/.openclaw/openclaw.json.backup`                |
| Gateway 日志     | `~/.openclaw/logs/gateway.log`                    |
| systemd 服务     | `~/.config/systemd/user/openclaw-gateway.service` |
| WSL 配置         | `/etc/wsl.conf`                                   |
| Windows WSL 配置 | `C:\Users\<用户名>\.wslconfig`                       |

### C. OpenClaw 端口速查表

| 端口      | 服务            | 说明                                    |
| ------- | ------------- | ------------------------------------- |
| `18789` | Gateway 主服务   | OpenClaw 核心 API 和 Control UI 访问端口     |
| `18792` | Browser Relay | Chrome 扩展与 Gateway 通信的 WebSocket 端口   |
| `9222`  | Chrome CDP    | Chrome DevTools Protocol 调试端口（浏览器自动化） |

> **注意**：配置 Chrome 扩展时填写的是 Browser Relay 端口 `18792`，而不是 Gateway 主端口 `18789`。两者用途不同，请勿混淆。

---

**注意**：请妥善保管您的 API Key 和 Token，定期检查系统安全。使用商业 LLM 时，请注意数据隐私，不要发送敏感信息。
