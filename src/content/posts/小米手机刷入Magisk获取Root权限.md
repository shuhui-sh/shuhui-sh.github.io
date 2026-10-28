---
title: "小米手机刷入Magisk获取Root权限"
date: 2026-04-02
description: "作为一个资深的Android开发工程师，如果没有自己的Root手机的话，犹如钦差大臣没有尚方宝剑一样。Android Root手机在逆向安全开发，自动化脚本测试，性能监控等方面有着巨大的作用。"
tags: []
category: "技术"
---
> 作者：见前行
> 发布于：2025-07-17
> 原文链接：https://juejin.cn/post/7527868423193296959

作为一个资深的Android开发工程师，如果没有自己的Root手机的话，犹如钦差大臣没有尚方宝剑一样。Android Root手机在逆向安全开发，自动化脚本测试，性能监控等方面有着巨大的作用。下面以小米手机为例（**小米手机官方支持解锁Bootloader刷入其他系统，比较友好**），详细介绍如何获取Root权限。

---

## 一、解锁手机Bootloader锁

### 步骤

1. 插入手机sim卡，然后关掉wifi，启用数据网络（用sim卡来上网）
2. 在设置里面登录用该手机号申请的小米账号
3. 进入"`设置 -- 开发者选项 -- 设备解锁状态`"中绑定账号和设备。成功后，会提示如下tips：

> **注意**：如果是比较新的系统，比如小米的澎湃系统，可能就需要足够的等级去小米社区的内测中心申请解锁了。下面也是我使用小米13pro测试机去申请解锁，是不能绑定的（同时我先是使用了已经停更小米6的MIUI11.05，直接就能绑定）

4. 接着进入[小米手机解锁官网](https://unlock.miui.com/)，下载解锁工具后解压，运行文件夹里的【miflash_unlock】，登录手机上的小米账号，验证手机是否支持解锁。

5. 手机关机，然后同时长按`开机键`和`音量下键`来启动系统进入`Bootloader` 模式，直到看到如下界面才松手

6. 将处于`FASTBOOT`界面的手机，用USB线连上PC。若显示当前未连接手机，可拔插USB重新连接手机，如果还是有问题可按如下步骤来尝试解决

### 驱动安装步骤

此时，在PC上打开设备管理器，可发现一个黄色叹号的Android设备，说明是处于FASTBOOT状态的手机的驱动没有装好

选中`Android`右键，选择更新驱动，选`浏览我的电脑以查找驱动驱`，

然后把刚才`miflash_unlock`文件夹的路径填入，windows系统会自动搜索并安装上小米的`MiUsbDriver.exe`

安装好驱动后，重新运行miflash_unlock.exe，并登陆小米账号。若显示当前未连接手机，可拔插USB重新连接手机。

7. 点击解锁，解锁手机`Bootloader`锁

---

## 二、获取小米手机对应型号的boot.img文件

### 步骤

1. 到[XiaomiROM](https://xiaomirom.com/)，寻找自己的手机型号，在右边选择版本，国内买的一般选择"国行版"。

2. 点击"Fastboot 线刷包"，找到于自己的手机系统版本号相同的一项，系统版本号可以在【我的设备】里查看，

点击【下载】按钮后再点击【小米官方】进行下载，下载速度要是很慢是因为被限速了(发现一个下载地址很慢，可以选择另外一个小米官方#2等其他链接)

3. 下载完成后进行解压，要解压两次，解压完成后打开文件夹，可以在【images】文件夹里找到`boot.img`，可以直接用数据线复制到手机上，比如`Download`目录，或者用网盘传到手机上，也可以用微信和QQ，但是可能找不到文件在哪里。

---

## 三、手机下载Magisk.apk安装，去修改`Download`目录里的`boot.img`文件

### 步骤

1. 手机下载安装 `Magisk` [Magisk-download](https://github.com/topjohnwu/Magisk/releases)

2. Magisk.apk安装后打开，安装 – 选择 `boot.img`– 开始修补文件 – 修补完成

修补生成的文件 `magisk_patched-xxx.img` 在 `Download` 目录

3. 电脑下载工具 `adb-fastboot`[蓝奏盘](https://www.lanzou.com/b07n8rjeb)（解压出来）

4. 手机插电脑，打开 `传输文件` 模式，打开 `Download` 目录，把 `magisk_patched-xxx.img` 复制到电脑 `adb-fastboot` 目录

5. 手机关机，长按`电源键` + `音量下键`，两个键触发进入 `Bootloader` 模式，

6. `打开CMD命令行.bat` 输入下面的刷入命令

`magisk.img` 每次修补生成的名字都不一样，使用的时候请输入生成的名字

```bash
fastboot flash boot 面具文件名
```

7. 显示 `OKAY` 就是成功刷入了。再使用指令 `fastboot reboot` 重启手机

8. 开机有震动基本没问题了，耐心等开机。（打开`MagiskApp`显示 `Magisk` 的版本，就是刷好了的）

也可以通过点击底部超级用户tab，能切换过去也代表已经能获取Root权限了

---

## 四、使用Root权限

### 步骤

1. cmd输入以下命令，会触发`com.androidian.shell`程序去`Magisk`获取Root权限

```bash
adb shell

su
```

可在`Magisk`的`超级用户`tab里面授予Root权限
