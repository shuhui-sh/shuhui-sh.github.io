---
title: "云手机定制与风控对抗系列 (一)：CVD 是什么？从零搭建你的第一台虚拟 Android 设备"
date: 2026-05-27
description: "做逆向分析或安全研究时，你一定遇到过这些痛点： CVD (Cuttlefish Virtual Device) 正是解决这些问题的方案。"
tags: ['云游戏', 'Android']
category: "技术"
---
> 系列受众：有一定 Android 逆向基础（会用 JADX/Frida/apktool），但对 AOSP 编译、内核修改、风控对抗链路不熟悉的读者。
> 本系列不涉及任何商业课程付费内容，所有知识来自 Google 官方文档、开源项目和公开技术文章。

---

## 背景：为什么你需要虚拟设备？

做逆向分析或安全研究时，你一定遇到过这些痛点：

- **真机越来越难解锁 Bootloader**：小米、OPPO、vivo 的新机型 BL 解锁门槛逐年提高，部分品牌已彻底关闭解锁通道
- **新系统权限收紧**：Android 12+ 对 ADB、/proc、/sys 的访问被逐步限制
- **物理设备成本高**：多开、群控需要大量真实设备，采购和维护成本可观
- **环境不可控**：真机系统版本固定，无法随意升降级或替换内核

**CVD (Cuttlefish Virtual Device)** 正是解决这些问题的方案。它不是"模拟"Android，而是"编译"出一个完整的 Android 系统。

---

## 1. CVD 到底是什么？

CVD 全称 Cuttlefish Virtual Device，是 Google 官方推出的虚拟 Android 设备方案。它与普通模拟器（如 Android Emulator、Genymotion）有本质区别：

| 特性 | CVD | Android Emulator |
|------|-----|------------------|
| 系统来源 | 直接编译 AOSP 源码 | 使用预编译的系统镜像 |
| 框架保真度 | **完全保真**，行为与真机一致 | 包含大量 App 开发的便利钩子，不完全等同于真机 |
| 内核可定制 | 可替换/修改内核 | 一般不可修改 |
| HAL 层 | AOSP 标准 HAL | 模拟器专用 HAL |
| 云部署 | 原生支持 Google Cloud 等 | 有限支持 |
| 并发多开 | 支持多实例并发 | 有限支持 |

Google 官方原话：

> "Cuttlefish guarantees full fidelity with the Android framework (...) you should expect Cuttlefish to respond to your interactions at the OS level just like a physical phone target."

**通俗理解**：Android Emulator 是给 App 开发者用的，CVD 是给平台/系统开发者用的。做逆向和风控对抗，你需要的是 CVD。

### 技术原理

CVD 依赖 Linux KVM (Kernel-based Virtual Machine) 实现虚拟化：

```
┌──────────────────────────────────────────┐
│              AOSP 系统镜像                  │
│  ┌─────────┐ ┌──────┐ ┌──────────────┐  │
│  │ Framework │ │ Apps │ │ HAL (虚拟)   │  │
│  └─────────┘ └──────┘ └──────────────┘  │
├──────────────────────────────────────────┤
│          Linux Kernel (可替换)            │
├──────────────────────────────────────────┤
│          KVM 虚拟化层 (宿主机)             │
├──────────────────────────────────────────┤
│           宿主机硬件 (x86_64 / ARM64)      │
└──────────────────────────────────────────┘
```

---

## 2. 环境准备

### 2.1 系统要求

- **操作系统**：Linux (推荐 Ubuntu 20.04+) 或 ARM64 Linux 机器
- **虚拟化支持**：CPU 必须支持 KVM
- **磁盘空间**：至少 400GB（主要给 AOSP 源码）
- **内存**：至少 16GB，推荐 32GB+

Windows/macOS 用户可通过 WSL2 或虚拟机运行。

### 2.2 验证 KVM 可用性

```bash
# 检查 KVM 支持
grep -c -w "vmx\|svm" /proc/cpuinfo
# 输出必须 > 0

# 检查 /dev/kvm 设备节点
find /dev -name kvm
# 应输出: /dev/kvm
```

如果是云端机器（如 GCE），需要[启用嵌套虚拟化](https://cloud.google.com/compute/docs/instances/nested-virtualization/enable)。

---

## 3. 方式一：使用预编译镜像（快速体验）

如果只是想快速体验 CVD，不需要修改源码：

```bash
# 1. 安装依赖和 CVD 宿主工具
sudo apt install -y git devscripts equivs config-package-dev debhelper-compat golang curl
git clone https://github.com/google/android-cuttlefish
cd android-cuttlefish
tools/buildutils/build_packages.sh
sudo dpkg -i ./cuttlefish-base_*_*64.deb || sudo apt-get install -f
sudo dpkg -i ./cuttlefish-user_*_*64.deb || sudo apt-get install -f
sudo usermod -aG kvm,cvdnetwork,render $USER
sudo reboot   # 加载内核模块，应用 udev 规则

# 2. 从 Android CI 下载预编译镜像
# 访问 http://ci.android.com/
# 选择分支: aosp-android-latest-release
# 选择构建目标: aosp_cf_x86_64_only_phone-userdebug
# 下载:
#   - aosp_cf_x86_64_phone-img-xxxxxx.zip  (系统镜像)
#   - cvd-host_package.tar.gz               (宿主工具)

# 3. 解压并启动
mkdir cf && cd cf
tar xvf /path/to/cvd-host_package.tar.gz
unzip /path/to/aosp_cf_x86_64_phone-img-xxxxxx.zip

HOME=$PWD ./bin/launch_cvd --daemon

# 4. 验证
./bin/adb devices
# 浏览器访问 https://localhost:8443 查看虚拟设备画面

# 5. 停止
HOME=$PWD ./bin/stop_cvd
```

---

## 4. 方式二：从 AOSP 源码编译（深入定制的前提）

要进行系统级或内核级定制，必须从源码编译。

### 4.1 搭建编译环境

```bash
# Ubuntu 环境必备工具
sudo apt-get update
sudo apt-get install -y git git-core gnupg flex bison build-essential \
  zip curl zlib1g-dev gcc-multilib g++-multilib libc6-dev-i386 \
  libncurses5 lib32ncurses5-dev x11proto-core-dev libx11-dev \
  lib32z1-dev libgl1-mesa-dev libxml2-utils xsltproc unzip \
  fontconfig python3 python3-pip

# 安装 repo 工具
mkdir -p ~/bin
curl https://storage.googleapis.com/git-repo-downloads/repo > ~/bin/repo
chmod a+x ~/bin/repo
export PATH=~/bin:$PATH
```

### 4.2 下载 AOSP 源码

```bash
# 创建工作目录
mkdir aosp && cd aosp

# 初始化仓库（使用最新稳定分支）
repo init -u https://android.googlesource.com/platform/manifest \
  -b android-latest-release

# 同步源码（非常耗时，取决于网络和机器性能）
repo sync -c -j$(nproc)
```

**注意**：AOSP 源码约 60GB，同步可能需要数小时。

### 4.3 编译 CVD 专用目标

```bash
# 加载编译环境
source build/envsetup.sh

# 选择 CVD 目标
lunch aosp_cf_x86_64_only_phone-userdebug
# 或 ARM64: lunch aosp_cf_arm64_only_phone-userdebug

# 开始编译
m -j$(nproc)

# 编译产物位于 out/target/product/vsoc_x86_64_only_phone/
```

### 4.4 启动自编译的 CVD

```bash
# 加载环境
source build/envsetup.sh
lunch aosp_cf_x86_64_only_phone-userdebug

# 启动 CVD
launch_cvd --daemon

# 查看设备
adb devices
```

---

## 5. CVD 的关键配置参数

`launch_cvd` 支持大量参数用于定制虚拟设备行为：

```bash
launch_cvd \
  --daemon \                    # 后台运行
  --cpus=4 \                    # CPU 核心数
  --memory_mb=4096 \            # 内存大小 (MB)
  --x_res=1080 --y_res=1920 \   # 分辨率
  --dpi=480 \                   # 屏幕 DPI
  --start_webrtc=true \         # 启用 WebRTC 画面流
  --num_instances=3             # 同时启动多个实例（多开）
```

### 多开实例管理

CVD 原生支持多开，每个实例是独立的虚拟设备：

```bash
# 启动 3 个实例
launch_cvd --daemon --num_instances=3

# 每个实例前缀不同
adb devices
# List of devices attached
# 0.0.0.0:6520  device   # 实例 1
# 0.0.0.0:6521  device   # 实例 2
# 0.0.0.0:6522  device   # 实例 3
```

---

## 6. 读者实践建议

| 阶段 | 内容 | 预计时间 |
|------|------|----------|
| 1 | 用预编译镜像快速跑通 CVD | 2 小时 |
| 2 | 下载 AOSP 源码，完整编译一次 | 1 天（含等待时间） |
| 3 | 修改 `build/make/target/product/aosp_x86_64.mk` 中的默认属性，重新编译验证 | 2-3 小时 |
| 4 | 编译自定义内核并替换（下篇详述） | 半天 |

---

## 下一篇预告

下一篇我们将深入 **AOSP 系统级定制**：如何修改 build.prop、定制开发者选项、隐藏 ADB、模拟 SIM 卡信息、集成 GMS、替换 WebView、伪造 GPU 设备信息等。这些是让虚拟设备在风控系统面前"更像真机"的第一步。

---

### 参考资源

- [Cuttlefish 官方文档](https://source.android.com/docs/devices/cuttlefish)
- [CVD Get Started](https://source.android.com/docs/devices/cuttlefish/get-started)
- [CVD Kernel Dev](https://source.android.com/docs/devices/cuttlefish/kernel-dev)
- [CVD Environment Control API](https://source.android.com/docs/devices/cuttlefish/control-environment)
- [Building Custom Android ROM (Android Authority)](https://www.androidauthority.com/build-custom-android-rom-720453/)
- [CVD Launch Automation Guide](https://medium.com/@michaelyukunxi/android-cuttlefish-virtual-device-launch-automation-a-step-by-step-guide-1417360723d6)
- [Building and Using Cuttlefish (Nathan Chancellor)](https://nathanchance.dev/posts/building-using-cuttlefish/)
