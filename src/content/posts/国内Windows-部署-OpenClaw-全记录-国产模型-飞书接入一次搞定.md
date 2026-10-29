---
title: "国内Windows 部署 OpenClaw 全记录：国产模型 + 飞书接入一次搞定"
date: 2026-03-05
description: "踩了一个月的坑，换过五个国产模型，才让 OpenClaw 在 Windows 上真正跑起来。从 WSL 环境搭建、国内镜像配置，到模型选型、浏览器控制，每个坑都替你趟过了。"
tags: []
category: "技术"
source: "https://juejin.cn/post/7613330850831777842"
---
## 引言

### 为什么写这篇指南

我折腾 AI 编程助手不少，OpenClaw 是其中让我花时间最多的一个——不是因为它不好，而是从安装到真正跑起来，坑踩得不少。Windows 上没有原生支持，得借助 WSL；国内网络环境又有各种阻碍；加上大模型的选择直接影响体验好坏。折腾完之后觉得值得整理成文章，希望能帮后来人少走弯路。

### 我的踩坑历程

**先说模型选择上的弯路。**

近一个月里，我前后在闲鱼上买过智谱、MiniMax 的共享 API Key，试过智谱 GLM4.7、GLM5.0、Deepseek 3.2、MiniMax2.5，以及阿里 Qwen3-max。这些模型在当时的 OpenClaw 上的体验有一个共同问题：任务跑着跑着就中断，频繁回来询问我的意见，无法持续自主地把任务完成。直到换成 qwen3.5-plus，交代的任务才基本能直接跑完，这可能和它上下文窗口扩展到 1M 有关。

这件事让我意识到：**Agent 的能力和底层大模型的能力强相关**。想要好的体验，就要舍得用当前最强的生产力模型。当然，也可以慢慢等国产模型能力追上来。

下图是2026年1月31号最开始的使用截图：

![2b9b24aa8a78cfe1c3ff38e8763f8627.jpg](/images/国内Windows-部署-OpenClaw-全记录-国产模型-飞书接入一次搞定/01.png)

下面是最近的使用截图：

![2026-03-04-23-12-09-d6a18a20750532c258637461cfe07eae.jpg](/images/国内Windows-部署-OpenClaw-全记录-国产模型-飞书接入一次搞定/02.png)

**再说安装过程里的坑。**

OpenClaw 安装本身不复杂，但在国内环境下有几个地方容易卡住：

- **海外依赖下载慢**：安装过程中会拉取不少海外资源，不配置国内镜像源的话速度极慢甚至超时。APT 源、npm、pip 都需要单独换源。
- **网络环境要和宿主机同步**：WSL 默认的 NAT 网络模式下，网络环境配置和 Windows 主机是隔离的。需要把 WSL 切换成镜像网络模式，才能让 WSL 内部自动复用 Windows 的网络环境设置，省去大量排查网络问题的麻烦。
- **浏览器控制功能需要额外配置**：OpenClaw 支持通过 Chrome 扩展控制浏览器，这是一个很实用的功能，但配置步骤容易被忽略，需要单独安装扩展并配置 Relay 端口。
- **Brave Search 注册会扣 1 美元**：给 OpenClaw 开启网页搜索能力需要注册 Brave Search API，注册时会从海外信用卡扣 1 美元用于账号验证，几天后会退回。没有海外信用卡的话这一步会卡住，要提前做好准备。

### 部署环境选型

在开始之前，有必要先说清楚为什么选择 WSL，而不是其他系统或方案。

OpenClaw 本质上是一个运行在命令行环境下的 AI Agent，对操作系统的依赖主要体现在两点：**命令行能力**和**文件系统的可访问性**。

#### macOS — 最优选择

macOS 基于 Unix，天生具备完整的命令行环境，bash/zsh、curl、git 等工具开箱即用，同时拥有成熟的 GUI 生态（Homebrew、各类原生应用），开发体验和日常使用可以无缝共存。

如果你用 Mac，直接跳过本文，按官方文档安装即可，几乎不会遇到环境问题。

#### Linux — 命令行原生，但桌面生态薄弱

Linux 的命令行能力毋庸置疑，OpenClaw 在 Linux 上运行最为顺畅。但对于大多数普通用户来说，Linux 桌面生态相对薄弱，日常办公软件、国内应用的支持有限，很难作为主力工作系统使用。

#### Windows — 用 WSL 弥补命令行劣势

Windows 是国内用户占比最高的系统，但它对命令行的支持历来是短板。PowerShell 能处理基础任务，但面对 OpenClaw 这类依赖 Unix 工具链的应用时力不从心。

在 Windows 上运行 Linux 环境主要有两条路：

| 方案 | 说明 | 劣势 |
| --- | --- | --- |
| 虚拟机（VMware / VirtualBox） | 运行完整的 Linux 系统 | 资源占用高，文件互通繁琐，体验割裂 |
| WSL（Windows Subsystem for Linux） | 微软官方 Linux 子系统 | 极少数场景下兼容性略有限制 |

**WSL 是更好的选择**，原因在于它打破了 Windows 和 Linux 之间的壁垒：

- **文件系统双向互通**：WSL 可以直接挂载并访问 Windows 的任意目录（路径格式为 `/mnt/c/...`），Windows 也可以直接访问 WSL 的文件系统。无需复制、无需共享文件夹，两侧文件操作无缝衔接。

![2026-03-04-23-13-40-image.png](/images/国内Windows-部署-OpenClaw-全记录-国产模型-飞书接入一次搞定/03.png)

- **网络共享**：配置镜像网络模式后，WSL 与 Windows 共享同一个网络栈，网络端口、局域网访问全部打通，不存在虚拟机的网络隔离问题。
- **性能接近原生**：WSL 2 运行完整的 Linux 内核，性能远优于虚拟机。
- **与 Windows 生态共存**：你可以继续使用熟悉的 Windows 应用、输入法、浏览器，同时在 WSL 里运行 Linux 工具链。

综合来看，**WSL + Windows 的组合体验接近 macOS**：既有完整的 Unix 命令行环境，又保留了 Windows 丰富的桌面生态，两套系统的文件和网络融为一体。这也是本文选择 WSL 方案的核心原因。

> 本文的所有内容均基于 **Windows 11 + WSL 2 + Ubuntu** 环境编写。Windows 10 用户需确保系统版本支持 WSL 2（Build 19041 及以上）。

### 这篇指南能帮你做什么

从零开始，在 Windows 11 的 WSL 环境中完整安装并运行 OpenClaw，并接入国内大模型 API。每个容易踩坑的环节都有详细说明，零基础新手也可以跟着一步步完成。

---

## 目录

- [引言](#%E5%BC%95%E8%A8%80 "#%E5%BC%95%E8%A8%80")
- [一、快速开始](#%E4%B8%80%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B "#%E4%B8%80%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B")
- [二、前置知识](#%E4%BA%8C%E5%89%8D%E7%BD%AE%E7%9F%A5%E8%AF%86 "#%E4%BA%8C%E5%89%8D%E7%BD%AE%E7%9F%A5%E8%AF%86")
- [三、WSL 安装与网络配置](#%E4%B8%89wsl-%E5%AE%89%E8%A3%85%E4%B8%8E%E7%BD%91%E7%BB%9C%E9%85%8D%E7%BD%AE "#%E4%B8%89wsl-%E5%AE%89%E8%A3%85%E4%B8%8E%E7%BD%91%E7%BB%9C%E9%85%8D%E7%BD%AE")

  - [3.0 启用 WSL 功能（前置步骤）](#30-%E5%90%AF%E7%94%A8-wsl-%E5%8A%9F%E8%83%BD%E5%89%8D%E7%BD%AE%E6%AD%A5%E9%AA%A4 "#30-%E5%90%AF%E7%94%A8-wsl-%E5%8A%9F%E8%83%BD%E5%89%8D%E7%BD%AE%E6%AD%A5%E9%AA%A4")
  - [3.1 安装 Ubuntu 到指定目录（可选）](#31-%E5%AE%89%E8%A3%85-ubuntu-%E5%88%B0%E6%8C%87%E5%AE%9A%E7%9B%AE%E5%BD%95%E5%8F%AF%E9%80%89 "#31-%E5%AE%89%E8%A3%85-ubuntu-%E5%88%B0%E6%8C%87%E5%AE%9A%E7%9B%AE%E5%BD%95%E5%8F%AF%E9%80%89")
  - [3.2 安装 WSL](#32-%E5%AE%89%E8%A3%85-wsl "#32-%E5%AE%89%E8%A3%85-wsl")
  - [3.3 Ubuntu 初始化](#33-ubuntu-%E5%88%9D%E5%A7%8B%E5%8C%96 "#33-ubuntu-%E5%88%9D%E5%A7%8B%E5%8C%96")
  - [3.4 WSL 与 Windows 文件互访](#34-wsl-%E4%B8%8E-windows-%E6%96%87%E4%BB%B6%E4%BA%92%E8%AE%BF "#34-wsl-%E4%B8%8E-windows-%E6%96%87%E4%BB%B6%E4%BA%92%E8%AE%BF")
  - [3.5 WSL 网络模式配置](#35-wsl-%E7%BD%91%E7%BB%9C%E6%A8%A1%E5%BC%8F%E9%85%8D%E7%BD%AE "#35-wsl-%E7%BD%91%E7%BB%9C%E6%A8%A1%E5%BC%8F%E9%85%8D%E7%BD%AE")
  - [3.6 防火墙配置](#36-%E9%98%B2%E7%81%AB%E5%A2%99%E9%85%8D%E7%BD%AE "#36-%E9%98%B2%E7%81%AB%E5%A2%99%E9%85%8D%E7%BD%AE")
- [四、国内镜像源配置](#%E5%9B%9B%E5%9B%BD%E5%86%85%E9%95%9C%E5%83%8F%E6%BA%90%E9%85%8D%E7%BD%AE "#%E5%9B%9B%E5%9B%BD%E5%86%85%E9%95%9C%E5%83%8F%E6%BA%90%E9%85%8D%E7%BD%AE")
- [五、OpenClaw 安装](#%E4%BA%94openclaw-%E5%AE%89%E8%A3%85 "#%E4%BA%94openclaw-%E5%AE%89%E8%A3%85")
- [六、配置国内大模型 API](#%E5%85%AD%E9%85%8D%E7%BD%AE%E5%9B%BD%E5%86%85%E5%A4%A7%E6%A8%A1%E5%9E%8B-api "#%E5%85%AD%E9%85%8D%E7%BD%AE%E5%9B%BD%E5%86%85%E5%A4%A7%E6%A8%A1%E5%9E%8B-api")
- [七、服务管理与访问](#%E4%B8%83%E6%9C%8D%E5%8A%A1%E7%AE%A1%E7%90%86%E4%B8%8E%E8%AE%BF%E9%97%AE "#%E4%B8%83%E6%9C%8D%E5%8A%A1%E7%AE%A1%E7%90%86%E4%B8%8E%E8%AE%BF%E9%97%AE")
- [八、高级配置](#%E5%85%AB%E9%AB%98%E7%BA%A7%E9%85%8D%E7%BD%AE "#%E5%85%AB%E9%AB%98%E7%BA%A7%E9%85%8D%E7%BD%AE")
- [九、使用踩坑技巧](#%E4%B9%9D%E4%BD%BF%E7%94%A8%E8%B8%A9%E5%9D%91%E6%8A%80%E5%B7%A7 "#%E4%B9%9D%E4%BD%BF%E7%94%A8%E8%B8%A9%E5%9D%91%E6%8A%80%E5%B7%A7")
- [十、常见问题 FAQ](#%E5%8D%81%E5%B8%B8%E8%A7%81%E9%97%AE%E9%A2%98-faq "#%E5%8D%81%E5%B8%B8%E8%A7%81%E9%97%AE%E9%A2%98-faq")
- [十一、相关资源](#%E5%8D%81%E4%B8%80%E7%9B%B8%E5%85%B3%E8%B5%84%E6%BA%90 "#%E5%8D%81%E4%B8%80%E7%9B%B8%E5%85%B3%E8%B5%84%E6%BA%90")

---

## 一、快速开始

> 本章节面向有经验的用户，Windows 系统中已有 WSL 环境的，提供快速安装指引。零基础新手请跳转到[第二章](#%E4%BA%8C%E5%89%8D%E7%BD%AE%E7%9F%A5%E8%AF%86 "#%E4%BA%8C%E5%89%8D%E7%BD%AE%E7%9F%A5%E8%AF%86")。

**1. 安装 WSL（PowerShell 管理员）**

```
wsl --install
```

**2. 重启后，创建配置文件 `C:\Users<用户名>.wslconfig`**

```
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

```
wsl --shutdown
```

**4. 进入 WSL，配置国内镜像源后安装 OpenClaw**（镜像源配置参考[第四章](#%E5%9B%9B%E5%9B%BD%E5%86%85%E9%95%9C%E5%83%8F%E6%BA%90%E9%85%8D%E7%BD%AE "#%E5%9B%9B%E5%9B%BD%E5%86%85%E9%95%9C%E5%83%8F%E6%BA%90%E9%85%8D%E7%BD%AE")）

```
curl -fsSL https://molt.bot/install.sh | bash
```

**5. 运行初始化向导**

```
openclaw onboard --install-daemon
```

**6. 配置国内 API**

安装完 OpenClaw 后，推荐使用 Claude Code 自动完成 API Key 写入，参考[第六章](#%E5%85%AD%E9%85%8D%E7%BD%AE%E5%9B%BD%E5%86%85%E5%A4%A7%E6%A8%A1%E5%9E%8B-api "#%E5%85%AD%E9%85%8D%E7%BD%AE%E5%9B%BD%E5%86%85%E5%A4%A7%E6%A8%A1%E5%9E%8B-api")。

**7. 重启服务**

```
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
- 支持国内 API（MiniMax、智谱 GLM 等）

**MCP（Model Context Protocol）**

- AI 插件协议，允许 LLM 调用外部工具和服务
- 社区有丰富的 MCP 服务器（浏览器、数据库、文件系统等）

### 2.2 系统要求

| 要求项 | 最低配置 | 推荐配置 |
| --- | --- | --- |
| 操作系统 | Windows 10 21H2+ | Windows 11 最新版 |
| 内存 | 8GB RAM | 16GB+ RAM |
| 存储 | 10GB 可用空间 | 30GB+ SSD |
| 网络 | 稳定网络连接 | 网络环境稳定更佳 |

---

## 三、WSL 安装与网络配置

### 3.0 启用 WSL 功能（前置步骤）

在安装 WSL 之前，需要先确保 Windows 已启用两个底层功能组件：**适用于 Linux 的 Windows 子系统** 和 **虚拟机平台**。

> 💡 如果你直接执行 `wsl --install` 就能成功安装，说明系统已经自动启用了这些功能，可以跳过本节。但如果 `wsl --install` 报错或提示功能未启用，就需要手动开启。

#### 方式一：GUI 方式（控制面板）

1. 按 `Win + S` 搜索 **"启用或关闭 Windows 功能"** ，点击打开
2. 在弹出的窗口中，找到并勾选以下两项：

   - ✅ **适用于 Linux 的 Windows 子系统**（Windows Subsystem for Linux）
   - ✅ **虚拟机平台**（Virtual Machine Platform）
3. 点击 **"确定"** ，等待系统安装完成
4. **重启计算机**

#### 方式二：命令行方式（dism.exe）

以**管理员身份**打开 PowerShell，依次执行以下命令：

```
# 启用「适用于 Linux 的 Windows 子系统」
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# 启用「虚拟机平台」
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

两条命令执行完毕后，**必须重启计算机**。

重启后，建议将 WSL 默认版本设置为 2：

```
wsl --set-default-version 2
```

#### 验证功能是否已启用

重启后，在 PowerShell 中执行：

```
dism.exe /online /get-featureinfo /featurename:Microsoft-Windows-Subsystem-Linux
dism.exe /online /get-featureinfo /featurename:VirtualMachinePlatform
```

两个功能的状态都应显示为 **"已启用"（Enabled）** 。

### 3.1 安装 Ubuntu 到指定目录（可选）

默认情况下，`wsl --install` 会将 Ubuntu 安装到系统盘（C 盘），随着使用时间增长，WSL 的虚拟磁盘文件（`.vhdx`）会越来越大。如果你的 C 盘空间有限，建议将 Ubuntu 安装到其他磁盘。

> 💡 如果你不在意安装位置，可以直接跳到 [3.2 安装 WSL](#32-%E5%AE%89%E8%A3%85-wsl "#32-%E5%AE%89%E8%A3%85-wsl")，使用默认的一键安装方式。

#### 方式一：使用 --location 参数直接安装到指定目录（推荐）

WSL 较新版本（2.0+）支持 `--location` 参数，可以在安装时直接指定存储位置。

**步骤 1**：先确保 WSL 已更新到最新版本：

```
wsl --update
```

**步骤 2**：使用 `--location` 参数安装 Ubuntu 到指定目录：

```
# 示例：安装到 D 盘的 WSL\Ubuntu 目录
wsl --install -d Ubuntu --location D:\WSL\Ubuntu
```

安装完成后，Ubuntu 的虚拟磁盘文件将存储在 `D:\WSL\Ubuntu` 目录下，而非默认的 C 盘。

**验证安装位置**：

```
# 查看所有已安装的发行版及其详细信息
wsl --list --verbose
```

> ⚠️ 如果你的 WSL 版本较旧，`--location` 参数可能不被支持，会提示"无法识别的参数"。此时请使用方式二。

#### 方式二：手动下载离线包安装到指定目录

这种方式兼容性最好，适用于所有 WSL 版本，原理是手动下载 Ubuntu 发行版包，解压到目标目录后注册。

**步骤 1**：下载 Ubuntu 离线安装包

在 PowerShell 中执行（以 Ubuntu 24.04 为例）：

```
# 创建目标目录
mkdir D:\WSL\Ubuntu

# 下载 Ubuntu 24.04 离线包
Invoke-WebRequest -Uri https://aka.ms/wslubuntu2404 -OutFile D:\WSL\Ubuntu\Ubuntu2404.appx -UseBasicParsing
```

> 💡 常用下载地址：
>
> - Ubuntu 24.04：`https://aka.ms/wslubuntu2404`
> - Ubuntu 22.04：`https://aka.ms/wslubuntu2204`
> - 更多发行版：[微软官方 WSL 手动安装页面](https://link.juejin.cn?target=https%3A%2F%2Flearn.microsoft.com%2Fzh-cn%2Fwindows%2Fwsl%2Finstall-manual%23downloading-distributions "https://learn.microsoft.com/zh-cn/windows/wsl/install-manual#downloading-distributions")

**步骤 2**：解压安装包

```
# 将 .appx 重命名为 .zip 并解压
Rename-Item D:\WSL\Ubuntu\Ubuntu2404.appx D:\WSL\Ubuntu\Ubuntu2404.zip
Expand-Archive D:\WSL\Ubuntu\Ubuntu2404.zip -DestinationPath D:\WSL\Ubuntu
```

解压后，目录下会出现一个类似 `Ubuntu_2404.x.x.x_x64.appx` 的子包文件，继续解压它：

```
# 找到子包并解压（文件名可能略有不同，请根据实际情况调整）
Get-ChildItem D:\WSL\Ubuntu*x64.appx | ForEach-Object {
    Rename-Item $_.FullName ($_.FullName -replace '.appx$', '.zip')
}
Get-ChildItem D:\WSL\Ubuntu*x64.zip | ForEach-Object {
    Expand-Archive $_.FullName -DestinationPath D:\WSL\Ubuntu
}
```

**步骤 3**：运行安装程序

```
# 进入解压目录，运行 ubuntu.exe 完成注册
cd D:\WSL\Ubuntu
.\ubuntu.exe
```

首次运行会提示创建用户名和密码（与默认安装流程相同）。

**步骤 4**：清理安装包（可选）

```
# 删除下载的压缩包，只保留运行时文件
Remove-Item D:\WSL\Ubuntu*.zip -Force
Remove-Item D:\WSL\Ubuntu*.appx -Force 2>$null
```

#### 方式三：先默认安装，再迁移到指定目录

如果你已经用 `wsl --install` 完成了默认安装（在 C 盘），也可以事后迁移到其他磁盘。

**步骤 1**：导出当前 Ubuntu 为备份文件

```
# 导出为 tar 文件（可能需要几分钟，取决于当前系统大小）
wsl --export Ubuntu D:\WSL\Ubuntu-backup.tar
```

**步骤 2**：注销 C 盘上的旧实例

```
# 注意：这会删除 C 盘上的 Ubuntu，请确保已成功导出
wsl --unregister Ubuntu
```

**步骤 3**：导入到新目录

```
# 在 D 盘创建目标目录并导入
mkdir D:\WSL\Ubuntu
wsl --import Ubuntu D:\WSL\Ubuntu D:\WSL\Ubuntu-backup.tar
```

**步骤 4**：设置默认登录用户

迁移后 WSL 默认会以 root 身份登录，需要恢复为之前创建的普通用户：

```
# 将 yourname 替换为你之前创建的用户名
ubuntu config --default-user yourname
```

如果 `ubuntu` 命令不可用，可以在 `/etc/wsl.conf` 中配置：

```
wsl -d Ubuntu -u root
```

在 WSL 中编辑配置文件：

```
cat >> /etc/wsl.conf << 'EOF'
[user]
default=yourname
EOF
```

然后重启 WSL：

```
wsl --shutdown
```

**步骤 5**：验证并清理

```
# 验证迁移结果
wsl --list --verbose

# 确认无误后删除备份文件
Remove-Item D:\WSL\Ubuntu-backup.tar
```

### 3.2 安装 WSL

WSL（适用于 Linux 的 Windows 子系统）目前有两个主要版本：

| 版本 | 说明 | 推荐度 |
| --- | --- | --- |
| WSL 1 | 早期版本，采用系统调用转换层 | ⭐⭐ |
| WSL 2 | 运行完整的 Linux 内核，性能更佳 | ⭐⭐⭐⭐⭐ |

**强烈建议使用 WSL 2**。

#### 一键安装 WSL

在具有管理员权限的 PowerShell 或 Windows 终端中，执行以下命令：

```
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

```
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

```
wsl --update
```

### 3.3 Ubuntu 初始化

首次启动 Ubuntu 时，系统会提示创建 UNIX 用户名和密码：

```
Installing, this may take a few minutes...
Please create a default UNIX user account. The username and password must not match your Windows username.
New UNIX username: yourname
New password:
Retype new password:
```

此账户拥有 `sudo` 权限，是后续执行安装操作的核心身份。

### 3.4 WSL 与 Windows 文件互访

WSL 和 Windows 的文件系统是双向互通的，这是 WSL 相比传统虚拟机最大的优势之一。以下是常用路径的对照表：

#### WSL 中访问 Windows 文件

在 WSL 终端中，Windows 的各个磁盘自动挂载在 `/mnt/` 目录下：

| Windows 路径 | WSL 中的访问路径 | 说明 |
| --- | --- | --- |
| `C:` | `/mnt/c/` | C 盘根目录 |
| `D:` | `/mnt/d/` | D 盘根目录 |
| `C:\Users<用户名>\Desktop` | `/mnt/c/Users/<用户名>/Desktop` | Windows 桌面 |
| `C:\Users<用户名>\Documents` | `/mnt/c/Users/<用户名>/Documents` | Windows 文档 |
| `D:\Projects` | `/mnt/d/Projects` | D 盘项目目录（示例） |

使用示例：

```
# 在 WSL 中直接查看 Windows 桌面文件
ls /mnt/c/Users/yourname/Desktop

# 在 WSL 中编辑 Windows 上的文件
nano /mnt/d/Projects/readme.md

# 在 WSL 中复制 Windows 文件到 WSL 主目录
cp /mnt/c/Users/yourname/Documents/config.json ~/
```

#### Windows 中访问 WSL 文件

Windows 可以通过网络路径 `\wsl$` 或 `\wsl.localhost` 访问 WSL 的文件系统：

| WSL 路径 | Windows 中的访问路径 | 说明 |
| --- | --- | --- |
| `/` | `\wsl$\Ubuntu` | WSL 根目录 |
| `/home/<用户名>/` | `\wsl$\Ubuntu\home<用户名>` | WSL 用户主目录 |
| `~/.openclaw/` | `\wsl$\Ubuntu\home<用户名>.openclaw` | OpenClaw 配置目录 |
| `/etc/` | `\wsl$\Ubuntu\etc` | 系统配置目录 |

使用方式：

1. **文件资源管理器地址栏**：直接输入 `\wsl$\Ubuntu\home<用户名>` 即可浏览 WSL 文件
2. **左侧导航栏**：文件资源管理器左侧通常会显示 **"Linux"** 图标，点击可展开所有已安装的发行版
3. **映射网络驱动器**：右键 `\wsl$\Ubuntu` → 映射网络驱动器，即可为 WSL 分配盘符（如 `Z:`），方便日常访问

> 💡 **性能提示**：WSL 内的程序访问 `/mnt/c/` 下的 Windows 文件时，I/O 性能会显著低于访问 WSL 原生文件系统（`/home/` 下）。因此，建议将需要频繁读写的项目文件放在 WSL 文件系统内，而非 Windows 磁盘上。

#### 快速路径对照速查表

| 场景 | 从哪里访问 | 访问路径 |
| --- | --- | --- |
| WSL 中打开 Windows C 盘 | WSL 终端 | `/mnt/c/` |
| WSL 中打开 Windows D 盘 | WSL 终端 | `/mnt/d/` |
| Windows 中打开 WSL 主目录 | 文件资源管理器 | `\wsl$\Ubuntu\home<用户名>` |
| Windows 中打开 WSL 根目录 | 文件资源管理器 | `\wsl$\Ubuntu` |
| WSL 中用 Windows 程序打开文件 | WSL 终端 | `explorer.exe .`（在当前目录打开资源管理器） |
| Windows 中进入 WSL 终端 | PowerShell / 终端 | `wsl` 或 `wsl -d Ubuntu` |

### 3.5 WSL 网络模式配置

WSL 2 有两种网络模式，选择正确的模式对后续使用至关重要。

#### NAT 模式 vs 镜像模式

| 维度 | NAT 模式 (默认) | 镜像模式 (推荐) |
| --- | --- | --- |
| IP 地址 | 独立虚拟 IP (172.x.x.x) | 与宿主机共享相同局域网 IP |
| IPv6 支持 | 极其有限 | 全面原生支持 |
| 网络环境兼容性 | 经常导致 DNS 丢包 | 显著提升兼容性 |
| 局域网可见性 | 需要手动端口转发 | 局域网内其他设备可直接发现 |
| 防火墙控制 | 独立规则 | 直接使用 Windows 防火墙 |

**推荐使用镜像模式**。

> 💡 **WSL 1 用户注意**：镜像网络模式是 WSL 2 专属功能，`.wslconfig` 中的 `[wsl2]` 配置段对 WSL 1 不生效。不过 WSL 1 也不需要这个配置——WSL 1 没有虚拟机层，网络栈直接与 Windows 共享，天然不存在 NAT 隔离问题。这也是本文推荐 WSL 2 的原因之一：虽然需要额外配置镜像模式，但 WSL 2 运行完整的 Linux 内核，性能和兼容性远优于 WSL 1，配好镜像模式后网络体验与 WSL 1 同样透明。

#### 配置镜像网络模式

**步骤 1**：打开文件资源管理器，导航到以下路径：

```
C:\Users<您的用户名>\
```

**步骤 2**：创建或修改名为 `.wslconfig` 的文件（注意前面的点号）

**步骤 3**：使用记事本打开文件，添加以下配置：

```
[wsl2]
# 启用镜像网络模式 - 这是最重要的配置
networkingMode=mirrored
# 启用 DNS 隧道，防止网络环境下域名解析失效
dnsTunneling=true
# 强制 WSL 使用 Windows 的网络环境设置
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

```
wsl --shutdown
```

**步骤 6**：等待约 8 秒钟以确保虚拟机彻底关闭，然后重新启动 Ubuntu

#### 验证网络模式

进入 WSL 后，执行以下命令验证：

```
# 查看网络接口
ip addr show

# 查看路由表
ip route show

# 测试与局域网的连通性
ping 192.168.1.1
```

如果配置成功，WSL 将使用与 Windows 相同的局域网 IP 地址段。

### 3.6 防火墙配置

在镜像模式下，WSL2 应用将直接暴露在 Windows 防火墙规则中。

#### 创建防火墙规则

以管理员身份打开 PowerShell，执行以下命令：

```
# 创建入站防火墙规则，允许 OpenClaw 服务端口
New-NetFirewallRule -DisplayName "OpenClaw-Service" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 18789

# 验证规则是否创建成功
Get-NetFirewallRule -DisplayName "OpenClaw-Service" | Format-Table
```

#### 测试端口连通性

```
# 测试本地端口
Test-NetConnection -ComputerName localhost -Port 18789
```

---

## 四、国内镜像源配置

在国内使用 WSL 安装 OpenClaw 及相关依赖时，配置国内镜像源可以显著加速下载。

### 4.1 Ubuntu APT 源

#### 备份原配置

```
sudo cp /etc/apt/sources.list /etc/apt/sources.list.bak
```

#### 配置清华镜像源

**Ubuntu 24.04 (Noble)** ：

```
sudo tee /etc/apt/sources.list << 'EOF'
# 清华大学镜像源 - Ubuntu 24.04 (noble)
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ noble main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ noble-updates main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ noble-backports main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ noble-security main restricted universe multiverse
EOF
```

**Ubuntu 22.04 (Jammy)** ：

```
sudo tee /etc/apt/sources.list << 'EOF'
# 清华大学镜像源 - Ubuntu 22.04 (jammy)
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-updates main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-backports main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-security main restricted universe multiverse
EOF
```

#### 更新软件包索引

```
sudo apt update && sudo apt upgrade -y
```

#### 其他可选镜像源

| 镜像源 | 地址 |
| --- | --- |
| 清华大学 | `https://mirrors.tuna.tsinghua.edu.cn/ubuntu/` |
| 阿里云 | `https://mirrors.aliyun.com/ubuntu/` |
| 中科大 | `https://mirrors.ustc.edu.cn/ubuntu/` |
| 华为云 | `https://repo.huaweicloud.com/ubuntu/` |

### 4.2 npm 镜像源

```
# 设置淘宝镜像（npmmirror.com）
npm config set registry https://registry.npmmirror.com

# 验证配置
npm config get registry
```

### 4.3 pip 镜像源

```
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

```
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

```
chmod +x setup-mirrors.sh
./setup-mirrors.sh
```

---

## 五、OpenClaw 安装

### 5.1 基础环境配置

#### 安装基础工具

```
sudo apt install -y curl wget git
```

#### 配置 sudo 免密（可选）

为了避免在后续安装脚本运行中频繁输入密码，可以为当前用户开启 `sudo` 免密权限：

```
sudo visudo
```

在文件末尾添加以下内容（将 `your_username` 替换为你的实际用户名）：

```
your_username ALL=(ALL) NOPASSWD: ALL
```

保存并退出（Ctrl+O → Enter → Ctrl+X）。

### 5.2 安装 OpenClaw

使用官方提供的一键安装脚本进行部署：

```
curl -fsSL https://molt.bot/install.sh | bash
```

### 5.3 运行初始化向导

安装完成后，运行初始化向导完成基本配置：

```
openclaw onboard --install-daemon
```

安装结束后会自动出现提示信息，请根据提示信息完成 OpenClaw 配置，参考配置如下：

| 配置项 | 配置内容 |
| --- | --- |
| I understand this is powerful and inherently risky. Continue? | 选择 **"Yes"** |
| Onboarding mode | 选择 **"QuickStart"** |
| Model/auth provider | 选择 **"Skip for now"** ，后续可以配置 |
| Filter models by provider | 选择 **"All providers"** |
| Default model | 使用默认配置 |
| Select channel (QuickStart) | 选择 **"Skip for now"** ，后续可以配置 |
| Configure skills now? (recommended) | 选择 **"No"** ，后续可以配置 |
| Enable hooks? | 按空格键选中选项，按回车键进入下一步 |
| How do you want to hatch your bot? | 选择 **"Hatch in TUI"** |

### 5.4 验证安装

```
# 检查 OpenClaw 版本
openclaw --version

# 检查 Gateway 状态
openclaw gateway status
```

---

## 六、配置国内大模型 API

完成 OpenClaw 安装后，需要将 `~/.openclaw/openclaw.json` 中的 LLM 配置设置为国内大模型 API。以下提供3种方式供选择。

### 6.1 阿里百炼 Code Plan

国内用户在选择大模型服务商时，可以试试 **阿里百炼 Code Plan**（Lite 版）。理由如下：

- **价格低廉**：首个月仅需 7.5 元，第二个月也只要 20 元（原价 40 元），适合个人开发者低成本上手。
- **一站式多模型访问**：订阅后不仅能使用阿里自家模型，还能直接调用阿里平台部署的**智谱**、**MiniMax** 等最新公开模型，无需逐一前往各厂商官网注册和订阅，节省时间和管理成本。

> 🔗 **[订阅 Code Plan](https://link.juejin.cn?target=https%3A%2F%2Fwww.aliyun.com%2Fbenefit%2Fai%2Faistar%3FuserCode%3D4kjozvjm%26clubBiz%3DsubTask..12417291..10263 "https://www.aliyun.com/benefit/ai/aistar?userCode=4kjozvjm&clubBiz=subTask..12417291..10263")**
>
> 📖 **[阿里百炼 Code Plan 配置 OpenClaw 官方文档](https://link.juejin.cn?target=https%3A%2F%2Fhelp.aliyun.com%2Fzh%2Fmodel-studio%2Fopenclaw-coding-plan "https://help.aliyun.com/zh/model-studio/openclaw-coding-plan")**

完成订阅后，可参考上方官方文档获取 API Key 并完成 OpenClaw 对接（阿里网站页面较复杂，API Key 的位置可参考上篇文章[《国内安装 Claude Code 并切换使用国内大模型 API：完整指南》](https://juejin.cn/post/7611769471619645478 "https://juejin.cn/post/7611769471619645478")），也可继续按照 6.3 节使用 Claude Code 自动完成配置。

### 6.2 字节跳动的方舟 Coding Plan

国内用户在选择大模型服务商时，也可以试试字节跳动的 **方舟 Coding Plan**（Lite 版）。理由如下：

- **价格低廉**：首个月仅需 9.9 元，也适合个人开发者低成本上手。
- **一站式多模型访问**：订阅后不仅能使用字节自家豆包模型，还能直接调用火山引擎部署的**智谱**、**MiniMax**、 **Kimi**等最新公开模型，无需逐一前往各厂商官网注册和订阅，节省时间和管理成本。
- **多模态支持更多**：字节的豆包模型，目前都有的模型都支持文本、图片的输入，连code模型都支持，这个是其他国产厂商模型还不完善。

> 🔗 **[订阅 Code Plan](https://link.juejin.cn?target=https%3A%2F%2Fvolcengine.com%2FL%2FGLulZzeJDMc%2F "https://volcengine.com/L/GLulZzeJDMc/")**
>
> 📖 **[字节火山引擎配置 OpenClaw 官方文档](https://link.juejin.cn?target=https%3A%2F%2Fwww.volcengine.com%2Fdocs%2F82379%2F2183190%3Flang%3Dzh "https://www.volcengine.com/docs/82379/2183190?lang=zh")**

完成订阅后，可参考上方官方文档获取 API Key 并完成 OpenClaw 对接（字节的页面相对阿里的简洁很多，并且文档指引飞书接入也很完善），也可继续按照 6.3 节使用 Claude Code 自动完成配置。

**建议优先选用支持多模态的模型，如：qwen3.5-plus 、kimi-k2.5、doubao-seed-2.0-pro、doubao-seed-2.0-code、doubao-seed-2.0-lite**

![be237521831549f65fa31a399f3b18a3.jpg](/images/国内Windows-部署-OpenClaw-全记录-国产模型-飞书接入一次搞定/04.png)

### 6.3 使用 Claude Code 配置国内 API

手动编辑 JSON 配置文件容易出错，**可以使用 Claude Code 来完成这一步**——它能自动定位配置文件、写入正确的字段格式，并运行测试请求验证配置是否生效。

#### 6.3.1 前置：安装并配置 Claude Code

如果你还没有安装 Claude Code，请参考配套文章：

**[《国内安装 Claude Code 并切换使用国内大模型 API：完整指南》](https://juejin.cn/post/7611769471619645478 "https://juejin.cn/post/7611769471619645478")**

该文章涵盖：

- Claude Code 的安装方式（原生客户端，无需 Node.js）
- 如何获取 DeepSeek、阿里百炼、智谱 GLM 等国内 API Key
- 如何配置 `~/.claude/settings.json` 让 Claude Code 使用国内 API

> 💡 Claude Code 本身也需要一个大模型 API 才能运行，同样可以使用国产大模型 API，上篇文章有详细介绍，这里不赘述。

#### 6.3.2 用 Claude Code 配置 OpenClaw API

Claude Code 安装并连接好国内 API 之后，进入你的工作目录，启动 Claude Code：

```
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

#### 6.3.3 配置文件参考格式

如果你需要了解配置文件的字段结构，以下是两个服务商的参考格式，**不需要手动复制粘贴**，让 Claude Code 来写即可：

**MiniMax 参考：**

```
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

```
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

#### 6.3.4 手动备份配置

无论是否使用 Claude Code，修改配置前请先手动备份：

```
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.backup
```

配置出错时可通过以下命令恢复：

```
cp ~/.openclaw/openclaw.json.backup ~/.openclaw/openclaw.json
openclaw gateway restart
```

---

## 七、服务管理与访问

### 7.1 Gateway 命令大全

| 命令 | 说明 |
| --- | --- |
| `openclaw gateway status` | 检查 Gateway 状态 |
| `openclaw gateway install` | 安装 Gateway 为系统服务 |
| `openclaw gateway start` | 启动 Gateway 服务 |
| `openclaw gateway stop` | 停止 Gateway 服务 |
| `openclaw gateway restart` | 重启 Gateway 服务 |
| `openclaw gateway uninstall` | 卸载 Gateway 服务 |
| `openclaw logs --follow` | 实时查看日志 |

#### 前台运行模式（调试用）

```
# 基础前台运行
openclaw gateway --port 18789

# 详细日志模式
openclaw gateway --port 18789 --verbose

# 强制启动（忽略 TS 编译警告）
openclaw gateway --force
```

#### 状态检查选项

```
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

```
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

```
sudo nano /etc/wsl.conf
```

添加或确认以下内容：

```
[boot]
systemd=true
```

重启 WSL：

```
wsl --shutdown
```

### 7.3 Control UI 访问

#### 本地访问

```
# 打开 Dashboard
openclaw dashboard

# 或直接访问
# http://127.0.0.1:18789/
```

#### 局域网访问配置

编辑 `~/.openclaw/openclaw.json`：

```
nano ~/.openclaw/openclaw.json
```

修改 Gateway 配置：

```
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

```
ip addr show | grep -E "inet " | awk '{print $2}' | cut -d'/' -f1 | grep -v "^127"
```

访问地址：`http://<局域网IP>:18789/`

---

## 八、高级配置

### 8.1 浏览器控制配置

OpenClaw 的 Browser 技能让 AI 可以直接操控浏览器——打开网页、点击元素、填写表单、读取内容。在 WSL 环境下有多种实现方式，先看整体对比再选择适合自己的方案。

#### 五种方式对比

| 方法 | 登录持久 | JS 渲染 | 推荐度 | 适用场景 |
| --- | --- | --- | --- | --- |
| Windows Chrome + CDP | ✅ 复用现有会话 | ✅ | ⭐⭐⭐⭐⭐ | 日常使用首选 |
| WSL Chrome + WSLg | ✅ 独立持久 | ✅ | ⭐⭐⭐⭐ | 纯 WSL 工作流 |
| Playwright 独立浏览器 | ⚠️ 每次新会话 | ✅ | ⭐⭐⭐ | 自动化爬虫 |
| OpenClaw Browser 工具 | ⚠️ 临时 | ✅ | ⭐⭐⭐ | 简单任务 |
| curl / HTTP 请求 | ⚠️ 手动 | ❌ | ⭐⭐ | 纯接口调用 |

**对于大多数用户，方案一（Windows Chrome + CDP）是最佳选择**，可以直接复用已登录的 Chrome 会话，不需要重新登录各网站。有纯 WSL 工作流需求的用户可以选择方案二。

#### 方案一：Windows Chrome + CDP（推荐）

**思路：** 不在 WSL 里跑浏览器，而是让 Windows 侧的 Chrome 开放调试端口，WSL 里的 OpenClaw 通过 Chrome DevTools Protocol（CDP）远程连接控制。

**架构：**

```
┌─────────────────────────────────────────┐
│  Windows                                │
│  ┌──────────────────────────────────┐   │
│  │  Chrome (--remote-debugging-port) │   │
│  │  监听 127.0.0.1:9222             │   │
│  └──────────┬───────────────────────┘   │
│             │ CDP (WebSocket)            │
│  ┌──────────▼───────────────────────┐   │
│  │  WSL (Ubuntu)                    │   │
│  │  OpenClaw Gateway                │   │
│  │  → cdpUrl: http://127.0.0.1:9222 │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

**启动方式：**

在 Windows 终端（非 WSL）中执行：

```
# 方式一：PowerShell 直接启动
Start-Process "chrome.exe" "--remote-debugging-port=9222 --user-data-dir=C:\chrome-openclaw"

# 方式二：通过 WSL 调用 Windows Chrome
/mnt/c/Windows/System32/cmd.exe /c "start chrome.exe --remote-debugging-port=9222 --user-data-dir=C:\chrome-openclaw"
```

**⚠️ 关键踩坑：Chrome 调试端口不生效**

Chrome 有一个隐蔽的行为：**如果系统中已有 Chrome 进程在运行，新启动的 Chrome 窗口会加入已有进程，`--remote-debugging-port` 参数被静默忽略**，调试端口根本不会开放。

很多人会反复尝试命令、检查端口，却始终连不上，原因就在这里。

**解决方法：**

```
# 步骤 1：先彻底关闭所有 Chrome 进程（包括后台）
taskkill /F /IM chrome.exe

# 步骤 2：等待 2 秒确认进程退出
Start-Sleep -Seconds 2

# 步骤 3：再带参数启动，用独立 user-data-dir 隔离配置
Start-Process "chrome.exe" "--remote-debugging-port=9222 --user-data-dir=C:\chrome-openclaw"
```

> 💡 使用独立的 `--user-data-dir` 有两个好处：一是彻底避免与现有 Chrome 进程合并；二是给 OpenClaw 维护一个独立的登录会话，不影响日常使用的 Chrome。

**验证端口是否开放：**

```
# 在 Windows PowerShell 中检查
Test-NetConnection -ComputerName localhost -Port 9222
```

或在 WSL 中：

```
curl http://127.0.0.1:9222/json/version
```

返回 JSON 内容说明连接成功。

**配置 OpenClaw 连接：**

编辑 `~/.openclaw/openclaw.json`：

```
{
  "tools": {
    "browser": {
      "enabled": true,
      "attachOnly": true,
      "cdpUrl": "http://127.0.0.1:9222"
    }
  }
}
```

#### 方案二：WSL Chrome + WSLg

**思路：** 在 WSL 内安装 Linux 版 Chrome，借助 WSLg 将窗口显示在 Windows 桌面上。适合不想依赖 Windows Chrome、需要纯 WSL 工作流的用户。

| 优点 | 缺点 |
| --- | --- |
| ✅ 原生 Linux 应用，与 WSL 完全集成 | ⚠️ 需要 WSLg 支持（Windows 11 或 Win10 最新版） |
| ✅ 无需跨系统互操作 | ⚠️ 中文输入法可能有问题 |
| ✅ 支持 CDP 远程调试 | ⚠️ 登录会话与 Windows Chrome 独立，需重新登录 |

**安装 Chrome：**

```
cd /tmp
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
sudo apt-get install -f -y

# 验证
google-chrome --version
```

**启动（附带网络工具和调试端口）：**

```
google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=~/.chrome-wsl \
  --proxy-server="http://127.0.0.1:7890" &
```

**浏览器窗口不显示的解决方法：**

```
# 在 Windows PowerShell 中更新 WSL
wsl --update
wsl --shutdown
```

重启 WSL 后再尝试。

**配置浏览器网络环境（永久生效，推荐）：**

创建 wrapper 脚本，省去每次手动加参数：

```
mkdir -p ~/bin
cat > ~/bin/google-chrome << 'EOF'
#!/bin/bash
/usr/bin/google-chrome \
  --proxy-server="http://127.0.0.1:7890" \
  --remote-debugging-port=9222 \
  --user-data-dir=~/.chrome-wsl \
  "$@"
EOF
chmod +x ~/bin/google-chrome

# 确保 ~/bin 优先于系统路径
grep -q 'export PATH="$HOME/bin:$PATH"' ~/.bashrc \
  || echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### 方案三：Playwright 独立浏览器

OpenClaw 通过 Playwright 启动一个独立的 Chromium 实例，每次任务结束后会话即销毁。适合不需要登录状态的自动化爬虫场景，不适合需要持久登录的日常任务。

#### 方案四：OpenClaw Browser 工具（内置）

OpenClaw 自带的浏览器控制工具，无需额外配置。功能相对基础，适合简单的网页读取任务。开启方式见 8.2 节 Skills 配置。

#### 方案五：curl / HTTP 请求

直接发送 HTTP 请求，轻量快速，但无法执行 JavaScript，仅适合纯接口调用或静态页面抓取。

#### OpenClaw Chrome 扩展安装（方案一 / 二通用）

OpenClaw 提供了 Chrome 浏览器扩展（Browser Relay），用于将 OpenClaw 连接到现有的 Chrome 标签页，实现浏览器自动化控制。

**步骤 1：安装扩展文件**

```
# 安装扩展到本地目录
openclaw browser extension install

# 查看扩展安装路径
openclaw browser extension path
```

扩展默认安装在：`~/.openclaw/browser/chrome-extension`

**步骤 2：在 Chrome 中加载扩展**

1. 打开 Chrome 浏览器，访问 `chrome://extensions/`
2. 开启右上角的\*\*"开发者模式"\*\*
3. 点击\*\*"加载已解压的扩展程序"\*\*
4. 导航到扩展目录并选择

**⚠️ 常见问题：找不到 `.openclaw` 目录**

在 WSL 中运行的 Chrome 文件选择器默认不显示隐藏目录（以 `.` 开头的目录）。

**解决方案**：

- **方法 1（推荐）** ：在文件选择器对话框中按 **Ctrl + H** 切换显示隐藏文件，然后导航到 `/home/<用户名>/.openclaw/browser/chrome-extension`
- **方法 2**：创建软链接到非隐藏目录

  ```
  ln -s ~/.openclaw/browser/chrome-extension ~/openclaw-chrome-extension
  ```

  然后在文件选择器中选择 `/home/<用户名>/openclaw-chrome-extension`

也可以直接在 Windows 文件浏览器地址栏输入 `\wsl$\Ubuntu\home<用户名>` 来访问 WSL 文件系统，直接定位到扩展目录。

**步骤 3：配置扩展**

扩展加载成功后，需要配置 Gateway Token：

1. 右键点击扩展图标 → 选择\*\*"选项"\*\*
2. 填入以下配置：

   - **Port**：`18792`（默认值）
   - **Gateway token**：你的 Gateway 认证 Token

获取 Gateway Token：

```
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

1. 将扩展固定到 Chrome 工具栏（点击拼图图标 → 点击 OpenClaw 旁边的 📌）
2. 打开要控制的网页
3. 点击工具栏上的 OpenClaw 扩展图标进行 attach/detach

#### Browser Service 配置

编辑 `~/.openclaw/openclaw.json`：

```
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

### 8.2 Skills 启用

**Skills** - OpenClaw 的扩展功能模块。

编辑 `~/.openclaw/openclaw.json`：

```
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

```
sudo npm install -g mcporter
```

启用后，OpenClaw 可以自动检测并使用以下配置文件：

- `~/.cursor/mcp.json` - Cursor 的 MCP 配置
- `~/.claude/mcp.json` - Claude Desktop 的 MCP 配置

### 8.3 即时通讯渠道配置（飞书）

通过飞书机器人与 OpenClaw 进行对话，支持私聊和群聊，
国内网络环境下可直接使用。

> 💡 OpenClaw 通过 WebSocket 长连接接入飞书，不需要公网 URL，
> 也不需要配置回调地址，对 WSL 本地部署非常友好。

整体流程分为四步：**安装飞书插件 → 创建飞书应用 →
配置 OpenClaw 飞书参数 → 配置飞书机器人权限**，
最后完成配对授权即可开始对话。

**前置准备**

飞书开放平台入口：[open.feishu.cn/app](https://link.juejin.cn?target=https%3A%2F%2Fopen.feishu.cn%2Fapp "https://open.feishu.cn/app")

---

#### 第一步：安装 OpenClaw 飞书插件

提供四种安装方式，按顺序尝试，方式一失败则依次尝试后续方式。

**方式一：官方命令安装（推荐）**

```
openclaw plugins install @m1heng-clawd/feishu
```

**方式二：手动下载安装**

```
# 下载插件包到当前目录
curl -O https://registry.npmjs.org/@m1heng-clawd/feishu/-/feishu-0.1.3.tgz

# 从本地安装插件
openclaw plugins install ./feishu-0.1.3.tgz
```

**方式三：让 OpenClaw 自动安装**

在 TUI 或 Web UI 的 Chat 界面发送以下内容
（将 `<App ID>` 和 `<App Secret>` 替换为下一步创建飞书应用后获取的信息）：

```
帮我安装飞书插件：https://github.com/AlexAnys/openclaw-feishu
我的飞书应用配置信息如下：
App ID: <App ID>
App Secret: <App Secret>
```

OpenClaw 会自动完成安装、配置、重启，无需手动执行后续配置命令。

**方式四：通过 openclaw config 界面选择安装（新版支持，最便捷）**

```
openclaw configure
```

进入配置界面后选择飞书插件进行安装。

---

#### 第二步：在飞书开放平台创建企业自建应用

1. 登录飞书开放平台后，点击右上角\*\*「开发者后台」\*\*
2. 点击\*\*「创建企业自建应用」\*\*，填写应用名称（如"OpenClaw 机器人"）和描述，点击创建

![image.png](/images/国内Windows-部署-OpenClaw-全记录-国产模型-飞书接入一次搞定/05.png)

![image.png](/images/国内Windows-部署-OpenClaw-全记录-国产模型-飞书接入一次搞定/06.png)
4. 进入\*\*「基础信息」→「凭证与基础信息」\*\*，记录 **App ID** 和 **App Secret**，后续配置需用

![image.png](/images/国内Windows-部署-OpenClaw-全记录-国产模型-飞书接入一次搞定/07.png)

---

#### 第三步：在 OpenClaw 中配置飞书参数

> 如果你使用了上方**方式三或方式四**完成安装，跳过此步骤。

将 `<App ID>` 和 `<App Secret>` 替换为实际信息，逐行执行：

```
# 配置飞书 App ID
openclaw config set channels.feishu.appId "<App ID>"

# 配置飞书 App Secret
openclaw config set channels.feishu.appSecret "<App Secret>"

# 启用飞书渠道
openclaw config set channels.feishu.enabled true

# 配置长连接模式
openclaw config set channels.feishu.connectionMode websocket

# 单聊策略：配对授权
openclaw config set channels.feishu.dmPolicy pairing

# 群聊策略：白名单
openclaw config set channels.feishu.groupPolicy allowlist

# 群聊需 @机器人 才响应
openclaw config set channels.feishu.requireMention true
```

配置完成后重启 Gateway：

```
openclaw gateway restart
```

也可直接编辑配置文件 `~/.openclaw/openclaw.json`：

```
{
  "channels": {
    "feishu": {
      "enabled": true,
      "connectionMode": "websocket",
      "dmPolicy": "pairing",
      "groupPolicy": "allowlist",
      "requireMention": true,
      "accounts": {
        "main": {
          "appId": "cli_xxxxxxxxxxxxxxxx",
          "appSecret": "YOUR_APP_SECRET",
          "botName": "OpenClaw 机器人",
          "domain": "feishu"
        }
      }
    }
  }
}
```

验证飞书渠道状态：

```
openclaw status
```

成功后应显示：

```
│ Feishu │ ON │ OK │ configured │
```

---

#### 第四步：配置飞书机器人权限与事件订阅

回到飞书开发者后台，按以下步骤配置，**每步配置后记得保存**：

**1. 添加机器人能力**

左侧菜单 → **「应用能力」** → 「添加应用能力」，点击\*\*「机器人」\*\*卡片添加。

![image.png](/images/国内Windows-部署-OpenClaw-全记录-国产模型-飞书接入一次搞定/08.png)

**2. 完善机器人说明**

在机器人配置区域，点击「如何开始使用」旁的编辑按钮，添加简单说明
（如"OpenClaw AI 机器人，输入问题即可解答"）。

![image.png](/images/国内Windows-部署-OpenClaw-全记录-国产模型-飞书接入一次搞定/09.png)

**3. 配置事件订阅**

左侧菜单 → **「开发配置」** → 「事件与回调」，
订阅方式选择\*\*「使用长连接接收事件」\*\*并保存。

![image.png](/images/国内Windows-部署-OpenClaw-全记录-国产模型-飞书接入一次搞定/10.png)

> ⚠️ **最容易遗漏的配置**：如果机器人能发消息但收不到消息，
> 99% 是因为没有选择「使用长连接接收事件」，默认是 Webhook 模式。

**4. 添加接收消息事件**

点击「添加事件」，搜索 `im.message.receive_v1`，添加并确认开通对应权限。

**5. 开通核心权限**

左侧菜单 → **「开发配置」** → 「权限管理」：

![image.png](/images/国内Windows-部署-OpenClaw-全记录-国产模型-飞书接入一次搞定/11.png)

- **应用身份权限**：搜索 `im:message`，全部选中并开通
- **用户身份权限**：搜索 `contact:user.base:readonly`，选中并开通

**6. 创建版本并发布**

点击页面顶部\*\*「应用发布」\*\* → 「版本管理与发布」，
创建新版本并填写更新说明后申请发布。

![image.png](/images/国内Windows-部署-OpenClaw-全记录-国产模型-飞书接入一次搞定/12.png)

> 💡 企业自建应用发布后无需平台审核，直接生效。

---

#### 第五步：配对授权（最后一步）

飞书机器人配置完成后，需完成配对授权才能正常响应消息，
未授权时发送消息会提示权限错误。

**获取配对码**

在飞书中向配置的机器人发送任意消息（如"测试"），
机器人会回复包含配对码的提示：

```
OpenClaw: access not configured. Your Feishu user id: ou_fxxxxxx
Pairing code: xxxx
Ask the bot owner to approve with: openclaw pairing approve feishu xxxx
```

**执行配对命令**

复制回复中的配对命令，将 `xxxx` 替换为实际配对码，在 WSL 终端执行：

```
openclaw pairing approve feishu xxxx
```

终端输出 `Pairing approved successfully` 表示配对成功。

**重启 Gateway 使授权生效**

```
openclaw gateway restart
```

**验证是否成功**

再次在飞书向机器人发送消息（如"你好"），机器人能正常响应即授权成功。

> 若仍提示权限问题，等待 2-3 分钟再试，飞书权限同步存在一定延迟。
> 群聊中需 **@机器人** 才能响应，单聊可直接发送消息。

---

#### ⚠️ 常见问题

**机器人能发消息但收不到消息**

回到飞书开放平台 → 事件与回调，确认已选择「使用长连接接收事件」，
而不是默认的 Webhook 模式。

**插件加载报错 `Cannot find module 'zod'`**

```
openclaw plugins install @m1heng-clawd/feishu
openclaw gateway restart
```

**应用发布后机器人仍无法使用**

确认已开通 `im:message` 权限，权限变更后需重新发布应用版本才能生效。

### 8.4 Brave Search 配置

**Brave Search** - 网页搜索技能，让 OpenClaw 具备搜索能力和读取网页内容的能力。

获取 API Key：[brave.com/search/api/](https://link.juejin.cn?target=https%3A%2F%2Fbrave.com%2Fsearch%2Fapi%2F "https://brave.com/search/api/")

免费计划每个用户每月有 2000 次免费搜索，前提是要绑定海外信用卡，注册时会扣费 1 美元用于验证，几天后会自动退回。

#### 方法一：使用配置命令

```
openclaw configure --section web
```

#### 方法二：手动编辑配置

编辑 `~/.openclaw/openclaw.json`：

```
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

| 变量 | 说明 |
| --- | --- |
| `OPENCLAW_HOME` | 设置 Home 目录 |
| `OPENCLAW_STATE_DIR` | 覆盖状态目录 |
| `OPENCLAW_CONFIG_PATH` | 覆盖配置文件路径 |
| `OPENCLAW_GATEWAY_TOKEN` | Gateway 认证 Token |

### 8.6 TUI 终端界面

```
# 启动终端用户界面
openclaw tui

# 退出 TUI
/exit
```

---

## 九、使用踩坑技巧

### ⚠️ 重要：AI 修改配置文件前先备份

**问题描述：**

让 OpenClaw 的 AI 助手修改 `openclaw.json` 配置文件时，可能会因为配置错误导致 OpenClaw 无法启动。

**最佳实践：**

在 `AGENTS.md` 或 `SOUL.md` 中添加以下规则，让 AI 每次修改配置文件前自动备份：

```
## 📁 文件修改规则

修改 ~/.openclaw/openclaw.json 或其他关键配置文件前：

1. 必须先备份当前配置
   cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.backup_$(date +%Y%m%d_%H%M%S)

2. 修改后验证配置
   openclaw status

3. 如果改挂了，快速恢复
   openclaw gateway stop
   cp ~/.openclaw/openclaw.json.backup_* ~/.openclaw/openclaw.json
   openclaw gateway start
```

**备用方式：通过 Windows 文件浏览器直接操作**

如果命令行恢复不方便，也可以直接在 Windows 文件浏览器地址栏输入以下路径，找到对应文件手动改名恢复：

```
\\wsl$\Ubuntu\home\<用户名>\.openclaw\
```

![2026-03-04-23-28-17-image.png](/images/国内Windows-部署-OpenClaw-全记录-国产模型-飞书接入一次搞定/13.png)

这是 WSL 文件系统双向互通的优势之一，GUI 操作比命令行更直观。

---

## 十、常见问题 FAQ

### Q1: Gateway 启动失败

**解决方案**：

```
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

```
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
2. 检查 `.wslconfig` 文件路径是否正确（`C:\Users<用户名>.wslconfig`）
3. 确认 WSL 版本为 2.0 以上
4. 更新 WSL 内核：`wsl --update`

### Q5: .bashrc 语法错误导致 Shell 无法启动

**问题表现**：

```
-bash: /home/user/.bashrc: line 163: syntax error near unexpected token `('
```

**原因分析**：

- Windows 的 `PATH` 环境变量会被 WSL 继承
- Windows PATH 中包含带括号的路径，如 `C:\Program Files (x86)...`
- 如果 `.bashrc` 中的 `export PATH=...` 语句没有使用双引号，bash 会将括号解释为子 shell 语法

**解决方案**：

**步骤 1**：使用 `--norc` 参数启动 bash（绕过 `.bashrc`）：

```
wsl -d Ubuntu -u your_username -e bash --norc
```

**步骤 2**：修复 `.bashrc` 文件：

```
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

```
source ~/.bashrc
echo $PATH
```

### Q6: OpenClaw 网络环境配置

**问题表现**：OpenClaw 的 `web_search` 工具无法访问外部网络，报错 `fetch failed`。

**原因分析**：

1. OpenClaw Gateway 作为 systemd 用户服务运行时，不会自动继承 `.bashrc` 中的环境变量
2. Node.js 的原生 `fetch()` 不会自动读取系统网络环境变量

**解决方案**：

**方法 1：配置 systemd 服务环境变量（推荐）**

编辑 OpenClaw Gateway 服务文件：

```
nano ~/.config/systemd/user/openclaw-gateway.service
```

在 `[Service]` 部分添加网络环境变量：

```
[Service]
Environment="HTTP_PROXY=http://127.0.0.1:7890"
Environment="HTTPS_PROXY=http://127.0.0.1:7890"
Environment="http_proxy=http://127.0.0.1:7890"
Environment="https_proxy=http://127.0.0.1:7890"
Environment="NO_PROXY=localhost,127.0.0.1,::1"
```

重载并重启服务：

```
systemctl --user daemon-reload
systemctl --user restart openclaw-gateway
```

**方法 2：使用网络工具 TUN 模式（最简单）**

如果你使用 Clash 等网络工具，可以启用 TUN 模式，让所有网络流量自动走指定通道，无需逐个配置。

### Q7: systemd 用户服务不自动启动

**问题表现**：每次启动 WSL 后，OpenClaw Gateway 服务没有自动运行。

**解决方案**：

```
# 步骤 1：确认 WSL 已启用 systemd
sudo nano /etc/wsl.conf
```

添加或确认以下内容：

```
[boot]
systemd=true
```

```
# 步骤 2：重启 WSL
wsl --shutdown

# 步骤 3：启用服务自启动
systemctl --user enable openclaw-gateway

# 步骤 4：启用用户服务的持久化
sudo loginctl enable-linger $USER
```

### Q8: Browser control service timed out

**解决方案**：

```
# 检查浏览器进程
ps aux | grep chrome

# 重启 Gateway
openclaw gateway restart

# 检查 CDP 端口
netstat -tlnp | grep 9222
```

### Q9: Gateway 端口被占用

**解决方案**：

```
# 查找占用端口的进程
lsof -i :18789

# 杀死进程
kill -9 <PID>
```

---

## 十一、相关资源

### 配套文章

- [国内安装 Claude Code 并切换使用国内大模型 API：完整指南](https://juejin.cn/post/7611769471619645478 "https://juejin.cn/post/7611769471619645478")（本系列上篇，包含 API Key 获取、Claude Code 配置方法）

### 官方资源

- [OpenClaw 官方文档](https://link.juejin.cn?target=https%3A%2F%2Fdocs.openclaw.ai "https://docs.openclaw.ai")
- [OpenClaw GitHub](https://link.juejin.cn?target=https%3A%2F%2Fgithub.com%2Fopenclaw%2Fopenclaw "https://github.com/openclaw/openclaw")

### 国内 API 服务商

- [MiniMax 官网](https://link.juejin.cn?target=https%3A%2F%2Fwww.minimaxi.com "https://www.minimaxi.com")
- [智谱 AI 官网](https://link.juejin.cn?target=https%3A%2F%2Fbigmodel.cn "https://bigmodel.cn")
- [阿里百炼](https://link.juejin.cn?target=https%3A%2F%2Fbailian.console.aliyun.com "https://bailian.console.aliyun.com")

### 参考教程

- [Shambix WSL 安装教程](https://link.juejin.cn?target=https%3A%2F%2Fwww.shambix.com%2Fhow-to-install-openclaw-on-windows-11-with-wsl%2F "https://www.shambix.com/how-to-install-openclaw-on-windows-11-with-wsl/")
- [OpenClaw FAQ](https://link.juejin.cn?target=https%3A%2F%2Fopenclaws.io%2Ffaq "https://openclaws.io/faq")
- [飞书开放平台文档](https://link.juejin.cn?target=https%3A%2F%2Fopen.feishu.cn%2Fdocument%2Fhome%2Findex "https://open.feishu.cn/document/home/index")

---

## 附录

### A. 常用镜像源速查表

| 类型 | 推荐镜像 | 地址 |
| --- | --- | --- |
| APT | 清华大学 | `https://mirrors.tuna.tsinghua.edu.cn/ubuntu/` |
| npm | 淘宝 npmmirror | `https://registry.npmmirror.com` |
| pip | 清华大学 | `https://pypi.tuna.tsinghua.edu.cn/simple` |
| Docker | 中科大 | `https://docker.mirrors.ustc.edu.cn` |

### B. OpenClaw 配置文件路径

| 文件 | 路径 |
| --- | --- |
| 主配置 | `~/.openclaw/openclaw.json` |
| 配置备份 | `~/.openclaw/openclaw.json.backup` |
| Gateway 日志 | `~/.openclaw/logs/gateway.log` |
| systemd 服务 | `~/.config/systemd/user/openclaw-gateway.service` |
| WSL 配置 | `/etc/wsl.conf` |
| Windows WSL 配置 | `C:\Users<用户名>.wslconfig` |

### C. OpenClaw 端口速查表

| 端口 | 服务 | 说明 |
| --- | --- | --- |
| `18789` | Gateway 主服务 | OpenClaw 核心 API 和 Control UI 访问端口 |
| `18792` | Browser Relay | Chrome 扩展与 Gateway 通信的 WebSocket 端口 |
| `9222` | Chrome CDP | Chrome DevTools Protocol 调试端口（浏览器自动化） |

> **注意**：配置 Chrome 扩展时填写的是 Browser Relay 端口 `18792`，而不是 Gateway 主端口 `18789`。两者用途不同，请勿混淆。

---

**注意**：请妥善保管您的 API Key 和 Token，定期检查系统安全。使用商业 LLM 时，请注意数据隐私，不要发送敏感信息。
