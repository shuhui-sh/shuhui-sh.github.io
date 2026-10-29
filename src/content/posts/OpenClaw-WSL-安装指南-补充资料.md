---
title: "OpenClaw WSL 安装指南 - 补充资料"
date: 2026-04-02
description: "OpenClaw 的 Browser 技能需要 Chrome 或 Brave 浏览器。WSL2 支持 WSLg，可以原生显示 Linux GUI 应用。"
tags: ['OpenClaw']
draft: true
category: "技术"
---
> 本文档是对《OpenClaw-WSL安装指南.md》的补充，涵盖启动命令、浏览器扩展配置等高级内容。

---

## 一、Gateway 启动命令大全

### 1.1 基础命令

| 命令 | 说明 |
|------|------|
| `openclaw gateway status` | 检查 Gateway 状态 |
| `openclaw gateway install` | 安装 Gateway 为系统服务 |
| `openclaw gateway start` | 启动 Gateway 服务 |
| `openclaw gateway stop` | 停止 Gateway 服务 |
| `openclaw gateway restart` | 重启 Gateway 服务 |
| `openclaw gateway uninstall` | 卸载 Gateway 服务 |
| `openclaw logs --follow` | 实时查看日志 |

### 1.2 前台运行模式（调试用）

```bash
# 基础前台运行
openclaw gateway --port 18789

# 详细日志模式
openclaw gateway --port 18789 --verbose

# 强制启动（忽略 TS 编译警告）
openclaw gateway --force

# 允许未配置状态启动
openclaw gateway run --allow-unconfigured
```

### 1.3 状态检查选项

```bash
# 基础状态
openclaw gateway status

# 深度扫描（包括系统服务）
openclaw gateway status --deep

# 跳过 RPC 探测（网络故障时有用）
openclaw gateway status --no-probe

# JSON 输出（适合脚本）
openclaw gateway status --json
```

### 1.4 systemd 服务管理（WSL/Linux）

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

---

## 二、浏览器扩展配置

### 2.1 在 WSL 中安装 Chrome

OpenClaw 的 Browser 技能需要 Chrome 或 Brave 浏览器。WSL2 支持 WSLg，可以原生显示 Linux GUI 应用。

```bash
# 下载并安装 Chrome
cd /tmp
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
sudo apt-get install -f -y

# 验证安装
google-chrome --version
```

### 2.2 浏览器窗口不显示问题

如果 Linux 浏览器窗口没有在 Windows 桌面显示：

```powershell
# 在 PowerShell 中更新 WSL
wsl --update
wsl --shutdown
```

然后重新启动 WSL。

### 2.3 Browser Service 配置

在 `~/.openclaw/openclaw.json` 中配置浏览器服务：

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

### 2.4 Playwright/Puppeteer MCP 配置

如果你使用 Playwright 或 Puppeteer MCP，需要先安装 mcporter：

```bash
sudo npm install -g mcporter
```

然后在配置文件中启用：

```json
{
  "skills": {
    "allowBundled": ["mcporter"]
  }
}
```

重启 Gateway：

```bash
openclaw gateway restart
```

### 2.5 MCP 配置文件共享

WSL 会共享 Windows 用户目录，因此以下文件可能已存在：

- `~/.cursor/mcp.json` - Cursor 的 MCP 配置
- `~/.claude/mcp.json` - Claude Desktop 的 MCP 配置

一旦 mcporter 激活，OpenClaw 可以自动检测并使用这些配置。

---

## 三、Control UI 访问

### 3.1 本地访问

```bash
# 打开 Dashboard
openclaw dashboard

# 或直接访问
# http://127.0.0.1:18789/
```

### 3.2 局域网访问配置

编辑 `~/.openclaw/openclaw.json`：

```json
{
  "gateway": {
    "port": 18789,
    "bind": "lan",
    "auth": {
      "mode": "token",
      "token": "your_secure_token"
    },
    "controlUi": {
      "allowInsecureAuth": true
    }
  }
}
```

获取局域网 IP：

```bash
ip addr show | grep -E "inet " | awk '{print $2}' | cut -d'/' -f1 | grep -v "^127"
```

访问地址：`http://<局域网IP>:18789/`

---

## 四、Onboarding 向导

### 4.1 首次配置

```bash
# 带守护进程安装的完整向导
openclaw onboard --install-daemon
```

向导会引导你完成：
1. 选择 AI 提供商
2. OAuth 认证
3. 安装 Gateway 服务
4. 创建你的 Agent（"孵化"）

### 4.2 交互式配置

```bash
# 配置特定部分
openclaw configure --section web    # 配置网页搜索
openclaw configure --section model  # 配置模型
```

### 4.3 TUI 终端界面

```bash
# 启动终端用户界面
openclaw tui

# 退出 TUI
/exit
```

---

## 五、常用技能（Skills）配置

### 5.1 启用内置技能

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

### 5.2 Brave Search 配置

```bash
openclaw configure --section web
```

或手动编辑配置：

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

---

## 六、环境变量

| 变量 | 说明 |
|------|------|
| `OPENCLAW_HOME` | 设置 Home 目录 |
| `OPENCLAW_STATE_DIR` | 覆盖状态目录 |
| `OPENCLAW_CONFIG_PATH` | 覆盖配置文件路径 |
| `OPENCLAW_GATEWAY_TOKEN` | Gateway 认证 Token |

---

## 七、故障排除

### 7.1 Browser control service timed out

如果遇到浏览器控制超时：

```bash
# 检查浏览器进程
ps aux | grep chrome

# 重启 Gateway
openclaw gateway restart

# 检查 CDP 端口
netstat -tlnp | grep 9222
```

### 7.2 systemd 服务无法启动

```bash
# 检查 lingering 状态
ls /var/lib/systemd/linger/

# 启用 lingering
sudo loginctl enable-linger $USER

# 重新加载 systemd
systemctl --user daemon-reload
```

### 7.3 Gateway 端口被占用

```bash
# 查找占用端口的进程
lsof -i :18789

# 杀死进程
kill -9 <PID>
```

---

## 八、国内镜像源配置（加速下载）

在国内使用 WSL 安装 OpenClaw 及相关依赖时，即使配置了代理，某些资源下载仍然很慢。配置国内镜像源可以显著加速。

### 8.1 Ubuntu APT 源（清华源）

**备份原配置：**

```bash
sudo cp /etc/apt/sources.list /etc/apt/sources.list.bak
```

**Ubuntu 24.04 (Noble) 配置：**

```bash
sudo tee /etc/apt/sources.list << 'EOF'
# 清华大学镜像源 - Ubuntu 24.04 (noble)
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ noble main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ noble-updates main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ noble-backports main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ noble-security main restricted universe multiverse
EOF
```

**Ubuntu 22.04 (Jammy) 配置：**

```bash
sudo tee /etc/apt/sources.list << 'EOF'
# 清华大学镜像源 - Ubuntu 22.04 (jammy)
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-updates main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-backports main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-security main restricted universe multiverse
EOF
```

**更新软件包索引：**

```bash
sudo apt update && sudo apt upgrade -y
```

**其他可选镜像源：**

| 镜像源 | 地址 |
|--------|------|
| 清华大学 | `https://mirrors.tuna.tsinghua.edu.cn/ubuntu/` |
| 阿里云 | `https://mirrors.aliyun.com/ubuntu/` |
| 中科大 | `https://mirrors.ustc.edu.cn/ubuntu/` |
| 华为云 | `https://repo.huaweicloud.com/ubuntu/` |
| 腾讯云 | `https://mirrors.cloud.tencent.com/ubuntu/` |

---

### 8.2 Node.js 安装（使用国内源）

**方法一：使用 NodeSource 官方脚本 + 代理**

```bash
# 安装 Node.js 22.x（推荐）
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs
```

**方法二：使用 nvm + 国内镜像**

```bash
# 安装 nvm（从 Gitee 镜像）
git clone https://gitee.com/mirrors/nvm.git ~/.nvm
echo 'export NVM_DIR="$HOME/.nvm"' >> ~/.bashrc
echo '[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"' >> ~/.bashrc
source ~/.bashrc

# 配置 nvm 使用国内镜像
export NVM_NODEJS_ORG_MIRROR=https://npmmirror.com/mirrors/node

# 安装 Node.js
nvm install --lts
nvm use --lts
```

---

### 8.3 npm 国内镜像配置

**永久配置（推荐）：**

```bash
# 设置淘宝镜像（npmmirror.com）
npm config set registry https://registry.npmmirror.com

# 验证配置
npm config get registry
```

**临时使用：**

```bash
npm install <package> --registry=https://registry.npmmirror.com
```

**常用 npm 镜像源：**

| 镜像源 | 地址 |
|--------|------|
| 淘宝（npmmirror） | `https://registry.npmmirror.com` |
| 腾讯云 | `https://mirrors.cloud.tencent.com/npm/` |
| 华为云 | `https://repo.huaweicloud.com/repository/npm/` |
| cnpm | `https://r.cnpmjs.org/` |

**使用 nrm 管理镜像源（可选）：**

```bash
# 安装 nrm
npm install -g nrm

# 查看可用源
nrm ls

# 切换到淘宝源
nrm use taobao

# 测试速度
nrm test
```

---

### 8.4 pip/Python 国内镜像配置

**临时使用：**

```bash
pip install <package> -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**永久配置：**

```bash
# 创建配置目录
mkdir -p ~/.pip

# 写入配置文件
cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn

[install]
trusted-host = pypi.tuna.tsinghua.edu.cn
EOF
```

**常用 pip 镜像源：**

| 镜像源 | 地址 |
|--------|------|
| 清华大学 | `https://pypi.tuna.tsinghua.edu.cn/simple` |
| 阿里云 | `https://mirrors.aliyun.com/pypi/simple/` |
| 腾讯云 | `https://mirrors.cloud.tencent.com/pypi/simple` |
| 华为云 | `https://repo.huaweicloud.com/repository/pypi/simple` |
| 中科大 | `https://pypi.mirrors.ustc.edu.cn/simple/` |

---

### 8.5 Git 加速配置

**GitHub 加速（使用镜像）：**

```bash
# 使用 ghproxy 加速 clone
git clone https://ghproxy.com/https://github.com/user/repo.git

# 或配置全局代理（如果有代理）
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890
```

**Git 大文件下载加速：**

```bash
# 浅克隆（只获取最新版本）
git clone --depth 1 https://github.com/user/repo.git

# 禁用 SSL 验证（某些镜像需要）
git config --global http.sslVerify false
```

---

### 8.6 Docker 镜像加速（可选）

如果你在 WSL 中使用 Docker：

```bash
# 创建配置目录
sudo mkdir -p /etc/docker

# 配置镜像加速
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
EOF

# 重启 Docker
sudo systemctl restart docker
```

---

### 8.7 一键配置脚本

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
echo "APT: 清华大学镜像"
echo "npm: 淘宝镜像 (npmmirror.com)"
echo "pip: 清华大学镜像"
```

**运行脚本：**

```bash
chmod +x setup-mirrors.sh
./setup-mirrors.sh
```

---

## 九、相关资源

- [OpenClaw 官方文档](https://docs.openclaw.ai)
- [OpenClaw GitHub](https://github.com/openclaw/openclaw)
- [Shambix WSL 安装教程](https://www.shambix.com/how-to-install-openclaw-on-windows-11-with-wsl/)
- [OpenClaw FAQ](https://openclaws.io/faq)

---

**注意**：
- 使用商业 LLM 时，请注意数据隐私，不要发送敏感信息
- 建议配合本地模型（如 Ollama、LM Studio）使用，确保数据安全
- 妥善保管 API Key 和 Token
