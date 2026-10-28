---
title: "让_AI_当逆向工程师_Claude_Code_自主分析_APK_和_so_文件_解决_Unity_插件化启动崩溃"
date: 2026-04-08
description: "本文记录了一次与 AI 编程助手（Claude Code）协作排查并优化 Android 插件化云游戏项目的完整过程。"
tags: ['插件化', 'Android', '逆向', 'AI']
category: "技术"
---
## 前言

本文记录了一次与 AI 编程助手（Claude Code）协作排查并优化 Android 插件化云游戏项目的完整过程。从最初的 "Not enough storage space" 启动失败，经历 4 轮迭代，最终实现 sourceDir 运行时重定向方案，将 ~179 MB 重复资源从宿主 APK 中彻底移除。

整个过程跨越两个会话（共 117 条交互消息、7 次上下文溢出续传）。在解决问题的过程中，对 Claude Code 这个 AI Agent 的能力有了更深的理解——不仅是它能做什么，更是如何给它配工具、指方向，逐步摸索出一套"发现问题 → 搜索确认方案 → 实施修复 → 自主验证"的半自动化闭环机制。

之所以叫 **L3.5 辅助驾驶**，是因为 AI 在这个过程中已经能自主完成大量操作（搜索、分析、编码、安装、监控），但关键方向决策、错误纠正、环境搭建仍然需要人来把控——就像 L3.5 级别的自动驾驶，大部分时间可以放手，但人不能离开驾驶位。

---

## 一、问题起源

### 1.1 架构背景

这个插件化工程采用"壳程序 + 插件"的 Android 插件化架构：

```
安装到设备的 APK（base.apk / 壳程序）
    ├── classes.dex          ← 壳程序代码
    ├── lib/                 ← Native 库
    └── assets/
        ├── assets_cloud.apk  ← 云游戏插件
        └── assets_game.apk   ← 完整游戏资源（~2GB）
```

当游戏资源就绪后，壳程序通过 ClassLoader 注入加载 `assets_game.apk` 中的游戏 DEX 和资源，运行完整游戏。

### 1.2 问题出现

用该项目制作的免安装包，游戏原包是 Unity 引擎的。先运行云游戏，下载好游戏原包资源后重启运行 Unity 游戏，启动就出现了 "not enough storage to install required resources" 的错误。

![79f7fed3a1a7abcff84c5f8ff5fb00e552b0524d.jpeg](https://p0-xtjj-private.juejin.cn/tos-cn-i-73owjymdk6/94f84ed5c80a42878acca23fced1da6d~tplv-73owjymdk6-jj-mark-v1:0:0:0:0:5o6Y6YeR5oqA5pyv56S-5Yy6IEAg5bel56iL5biITGlmZQ==:q75.awebp?policy=eyJ2bSI6MywidWlkIjoiMjM2NTgwNDc1NjA3NjU0MSJ9&rk3s=f64ab15b&x-orig-authkey=f32326d3454f2ac7e96d3d06cdbb035152127018&x-orig-expires=1775365848&x-orig-sign=ZrJiI3WJU1Po%2FMXWIBaQc1nKASY%3D)

向 Claude Code 描述问题时，想着 AI 能直接从网页搜索可能类似的报错，就直接让它去查：

> **我**："用该项目制作的免安装包，游戏原包是 Unity 引擎的，然后先运行云游戏后，下载好游戏原包资源后，重启是运行 Unity 原游戏包，启动就出现了 'not enough storage to install required resources' 的 error 提示，请你搜索网络相关资料，分析出现该问题的原因，看看有什么解决方案，先讨论总结。"

### 1.3 AI 的第一步：网络搜索

AI 使用 **WebSearch** 工具搜索：

```
工具: WebSearch
查询: "Unity il2cpp not enough storage space to install required resources Android"
```

搜索结果指向 Unity il2cpp 资源提取失败，常见于 OBB 缺失或存储空间不足。但 AI 立即意识到：在插件化环境下，这更可能是资源路径问题，而非真正的存储不足。

---

## 二、诊断与根因定位

### 2.1 排除存储空间问题

AI 要求检查设备状态。我在设备上执行命令后提供了结果：

```bash
$ df -h /data
Filesystem      Size  Used Avail Use% Mounted on
/dev/block/...  118G   18G  100G  15% /data

$ ls /data/data/com.example.game/files/il2cpp/
ls: No such file or directory  # 不存在
```

**AI 的推理**：100GB 可用空间，不是真正的存储不足。il2cpp 目录不存在说明提取过程根本没开始——Unity 找不到源文件来提取。

### 2.2 提供目录让 AI 验证

既然 AI 能操作文件系统，那我想不如就直接给它游戏原包路径让它自己验证看看：

> **我**："J:\云游戏\一次包\GameProject\game.nosign 这个目录是游戏原包的解压目录，你可以**搜索定位字符串或验证你的猜想**"

AI 使用 **Bash** 工具在 `libunity.so` 中搜索错误字符串（这是它自主地逆向so文件，ai分析so文件就像人类分析普通txt文件一样简单）：

```bash
$ strings lib/arm64-v8a/libunity.so | grep -B5 -A5 "storage"

输出:
assets/bin/
Failed to load Il2CPP.
il2cpp failed to extract resources (%s => %s)
Not enough storage space to install required resources.
```

**关键发现**：错误字符串紧邻 `assets/bin/` 路径。Unity 需要从 APK 的 `assets/bin/Data/` 读取 `global-metadata.dat` 等 il2cpp 核心资源。

### 2.3 对比分析确认根因

我又提供了构建后的一次包路径：

> **我**："J:\云游戏\一次包\GameProject\cloud_game_0.1.0_103313_... 这个目录是构建好的一次包，你可以再**分析验证下你的猜想**，好像是真的没有 assets/bin/Data/"

Agent自动完成了apk的解压，并对比了两个包的目录结构：

| 位置                       | `assets/bin/Data/` 存在？ |
| ------------------------ | ---------------------- |
| 原游戏 APK（game.nosign.apk） | ✅ 存在，~41 MB            |
| 构建后 base.apk（壳程序）        | ❌ 不存在                  |
| assets_game.apk（游戏插件）    | ✅ 存在                   |

**根因确认**：构建工具将 `assets/bin/` 放入了 `assets_game.apk`，但 Unity 从 `ApplicationInfo.sourceDir`（指向 base.apk）读取，找不到资源 → 误报存储不足。

---

## 三、方案 A：构建时复制资源到宿主（第一轮实现）

### 3.1 AI 提出三个方案

| 方案  | 思路                                 | 优点   | 缺点    |
| --- | ---------------------------------- | ---- | ----- |
| A   | 构建时将 `assets/bin/` 复制到 base.apk    | 简单直接 | 增加包体积 |
| B   | 运行时修改 sourceDir 指向 assets_game.apk | 不增体积 | 反射风险  |
| C   | 运行时预提取资源到 il2cpp 目录                | 灵活   | 复杂度高  |

### 3.2 选择先验证最快的方案

> **我**："先按方案 A 帮我修改，方案 C 应该记着，留着到云游戏工程里面去修改"

AI 修改了 `ApkManager.java` 的 `extraGameAssets()` 方法，将 `assets/bin/` 同时复制到壳程序 assets 目录。

**结果**：✅ Unity 启动成功，il2cpp 资源正常提取。但 base.apk 增加了 ~40 MB。

---

## 四、发现 syncload 问题——排除法定位需要的资源

### 4.1 排除法定位

方案 A 解决了 `assets/bin/` 后，启动后发现还有新的问题，数据包损坏，按照以往的适配经验和前面刚解决的启动报错问题，判断肯定是还有哪些资源也需要放在宿主壳中被加载，于是手动把所有游戏 assets资源都放到宿主壳中，经过验证，猜想确实可行。于是引导ai开始排除法定位具体需要的资源。

告诉 AI 这个好消息，引导它做排除法：

> **我**："告诉你一个好消息，当全部游戏的 assets 资源都复制到宿主的 assets 的时候，下载好其他资源后启动游戏，是能正常运行的。你麻烦基于当前的反馈，看看能不能判断出其真正需要的资源是哪些？...你可以**运用网络搜索等各种工具**"

> **我**："assets/bin/Data/ ~40 MB 和 assets/assets/res/syncload/ 这 2 个比较大的资源...了解一下他们是在何时被加载的，有没有中间路径...先验证研究，不改代码"

验证确认了 syncload（~133 MB）和字体（~6 MB）也被 Unity 通过 `WWW:jar:file://{sourceDir}!/assets/...` 方式加载。总计 **~179 MB 被重复存储** 在宿主 APK 中。（这个定位最小需要的资源的过程，使用的是GLM5.0的模型，并没有使用Opus 4.6，其他的过程均使用Opus 4.6）

### 4.2 引导 AI 搜索 Unity 加载机制

> **我**："方案 B 需要你再仔细研究一下，可以查看当前源码，也需要**搜索网络上关于 Unity 的资源加载机制**等等，Unity 哪些资源必须要在壳宿主里面等"

> **我**："需要你再分析下 Unity 游戏需要保证哪些资源必须在 assets 下的，你可以**搜索网络资料或其他源码**"

> **我**："游戏的 AssetBundle 加载机制是通过 WWW:jar:file:///...base.apk!/... 路径，直接从 APK 内部读取资源。**搜索一下网络资料**，看看有没有什么方案可以从插件里面加载"

### 4.3 预填充方案验证（均失败）

AI 尝试了两种绕过方案：预填充 patch 目录和 GameData/SyncLoad 目录。

**结果**：❌ 都失败了。syncLoadResource **只认 sourceDir**（即 base.apk 路径），无论预填充到哪个目录都无法绕过。唯一的办法是修改 sourceDir 本身。

---

## 五、方案 B-1：sourceDir 运行时重定向（核心突破）

### 5.1 切换 root 设备——一个关键转折

到这里，之前的操作模式一直是：我在设备上跑命令 → 把结果粘贴给 AI。这个过程很低效。于是我做了一个尝试——把 adb 连接切换到一台 root 过的小米 6，看看 AI 能不能直接操作设备：

> **我**："我当前 adb 连接的设备换成了**具有 root 权限的**，你看看还有什么方向不？"

效果出乎意料。从这一刻起，AI 可以直接在设备上安装、启动、读文件、抓日志、截图——不再需要我当"中间人"。这也是我第一次真正意识到：**给 AI 接上"手和眼"，效率会有质的飞跃**。

### 5.2 要求用源码和搜索验证

> **我**："Unity 很可能通过此路径构造 WWW:jar:file:// URL，你可以通过其他方式，如**阅读源码，或者网络搜索**来验证一下吗？"

> **我**："你要理解，我们的目标是要缩小宿主中的大小。然后你可以**运用逆向的知识**再去分析一下，是否还有其他的方案"

过程中 AI 的内置 WebSearch 报错了。我之前给 Claude Code 装过 Brave Search 技能，这时候派上了用场：

> **我**："**你应该直接使用搜索技能**，系统内置的网络访问有问题"

这件事进一步验证了，Claude code的一些内置工具的确是会走他们的服务器，而我们的网络的确是会被限制，所以事先就做好工具的平替非常有必要。如何在国内安装 Claude Code、配置好搜索 MCP 等工具，可以参考 [《国内安装 Claude Code 并切换使用国内大模型 API：完整指南》](https://juejin.cn/spost/7611769471619645478)。

### 5.3 AI 的技术调研过程

#### 步骤 1：搜索 AOSP 源码

AI 使用 Brave Search 和 WebFetch 查阅 Android 源码，发现 `sourceDir` 和 `mAppDir` 是**两个独立副本**：

```
ApplicationInfo.sourceDir       ← PackageManager 提供
LoadedApk.mAppDir               ← 构造时从 sourceDir 初始化，之后独立
Context.getPackageCodePath()    ← 返回 LoadedApk.mAppDir（不是 sourceDir！）
```

#### 步骤 2：分析 libunity.so

AI 使用 **Bash** 工具搜索 Unity native 层的 API 调用：

```bash
$ strings lib/arm64-v8a/libunity.so | grep -E "sourceDir|getPackageCodePath|getApplicationInfo"
```

**发现**：Unity 同时使用 `getApplicationInfo().sourceDir` 和 `getPackageCodePath()`（返回 `mAppDir`）。两个都要改。

#### 步骤 3：查找项目先例

AI 在项目中搜索找到 `TinkerResourcePatcher.java:308`，项目已有反射修改 `publicSourceDir` 的先例，验证了方案可行性。

### 5.4 实现 patchSourceDirForUnity()

AI 在 `AssetsHelper.java` 中实现核心方法，通过反射修改 **4 个对象共 6 个字段**，在 `ProxyApplication.attachBaseContext()` 中调用，时序上远早于 Unity 读取。

---

## 六、四轮测试迭代

### 6.1 第一轮（v1）：仅改 sourceDir → 失败

我安装好新包后引导 AI 自主验证：

> **我**："我在当前设备上已经安装了新的包了，**你可以监控测试验证了**"

AI 通过 logcat 发现字体 URL 仍指向 base.apk——这证实了 `sourceDir` 和 `mAppDir` 的独立性。改一个不够。

### 6.2 第二轮（v2）：增加 mAppDir → 部分成功

AI 增加了 `mAppDir` 和 `mResDir` 的修改。我安装新包后通知：

> **我**："新包已经构建完成了，并在设备上安装了，**你可以监控并测试验证了**"

这次 11/13 个 syncload 文件成功，但 2 个 `.so` 文件缺失。AI 用 Python zipfile 检查 `assets_game.apk`，发现 `libxyvodsdk0.so` 不在其中。

### 6.3 .so 过滤 Bug 的发现

AI 检查一次包工程的构建代码 `ApkManager.java:1132`：

```java
// BUG：过滤条件过于宽泛
if ((entryName.endsWith(".so") && entryName.contains("lib"))) {
    outputPath = gameResDir + File.separator + entryName;  // → 宿主 lib 目录
}
```

`entryName.contains("lib")` 匹配了文件名中的 "lib" 前缀（`libxyvodsdk0.so`），导致 `assets/` 下的游戏资源 .so 被错误路由。

**修复**：`contains("lib")` → `startsWith("lib/")`

### 6.4 第三轮（v3）：.so Bug 修复 → 完全成功

> **我**："现在设备上已经安装好重新构建的了，我看了下好像是正常启动并触发下载资源流程了，**你可以监控验证一下方案的实现**。如果确认没有问题了，那就把 assets/bin 目录也优化一下，不要放在宿主的 assets 下，以达到缩小包体的目的。"

**AI 犯了个错——用了错误的启动命令。** 我纠正：

> **我**："**不，你启动应用的命令不对，应用没有被启动起来**"

AI 通过 `dumpsys package` 找到正确的 LAUNCHER Activity 是 `SelectActivity`，改用 `monkey` 命令。修正后日志显示全部 13 个 syncload 文件加载成功，游戏正常启动。

### 6.5 第四轮（v4）：移除 assets/bin 和 font → 彻底优化

AI 删除了 `copyUnityEssentialResources()` 方法和 `assets/bin/` 复制逻辑。我安装新包后通知：

> **我**："设备上已经安装好新构建的包了，**你可以继续测试验证**"

> **AI 验证时的一个坑**：安装 v4 包后直接启动，发现进程号（PID 9902）与 v3 相同——旧进程未退出，`attachBaseContext()` 没有重新执行。AI 意识到需要先 `force-stop` 杀掉旧进程再启动。

最终日志确认：

- `global-metadata.dat` 从 `assets_game.apk` 加载成功 ✅
- 字体从 `assets_game.apk` 加载成功 ✅
- syncload 全部成功 ✅
- Unity il2cpp 正常启动 ✅

---

## 七、最终优化效果

| 资源                            | 大小          | base.apk 中 | 状态                     |
| ----------------------------- | ----------- | ---------- | ---------------------- |
| `assets/bin/Data/`            | ~40 MB      | ❌ 已移除      | ✅ 从 assets_game.apk 加载 |
| `assets/assets/res/syncload/` | ~133 MB     | ❌ 已移除      | ✅ 从 assets_game.apk 加载 |
| `assets/assets/res/ui/font/`  | ~6 MB       | ❌ 已移除      | ✅ 从 assets_game.apk 加载 |
| **合计**                        | **~179 MB** |            | **宿主包体减少 179 MB**      |

---

## 八、迭代过程图

```
报告 "not enough storage"
    │
    ▼
[第一阶段] 诊断与根因定位
    │  "搜索网络相关资料"→ AI WebSearch
    │  提供原包/一次包路径 → AI 对比目录结构
    │  "验证你的猜想"→ AI strings libunity.so
    │
    ▼
根因：assets/bin/ 不在 base.apk 中
    │
    ├──→ "先按方案 A 修改"──→ ✅ 修复成功（+40MB）
    │
    ▼
发现 syncload 也需要（+133MB）→ 总计 179MB 浪费
    │  "搜索 Unity 资源加载机制"
    │  "运用逆向知识分析"
    │  切换 root 设备 → "你可以直接操作验证"
    │
    ├──→ 预填充 patch 目录 ──→ ❌ 失败
    ├──→ 预填充 GameData/SyncLoad ──→ ❌ 失败
    │
    ▼
结论：唯一出路是修改 sourceDir
    │
    ├──→ v1（仅改 sourceDir）──→ ❌ Unity 用 getPackageCodePath()
    │     "你可以监控测试验证了"
    │     [关键发现] sourceDir ≠ mAppDir
    │
    ├──→ v2（增加 mAppDir）──→ ⚠️ 部分成功（2 个 .so 缺失）
    │     [发现 Bug] .so 过滤条件 contains("lib") 误匹配
    │
    ├──→ v3（修复 .so 过滤）──→ ✅ 完全成功！
    │     "启动命令不对"→ 纠正后成功
    │
    └──→ v4（彻底优化）──→ ✅ 减少 179 MB！
```

---

## 九、事先认知与过程中的能力发现

这次协作的起点并不是"零认知"。在开始之前，对 Claude Code 已经有一些基本了解，但很多能力是在解决问题的过程中才真正体会到的。

### 9.1 事先就知道的

开始这次排查前，对 AI Agent 已有两个基本认知：

**AI 大概率具备逆向分析的知识储备。** Claude Code 背后的大模型训练数据包含大量技术文档和源码，Android 框架、Unity 引擎这些领域的知识应该具备。所以从一开始就敢让它去搜索 Unity 的 il2cpp 机制、分析 AOSP 源码——不是"发现"它会，而是预判它应该会。

**AI 靠预测 token 生成内容，存在幻觉。** 所以不能让它猜，必须让它搜索网络资料、阅读源码来验证推断。这也是为什么整个过程中反复说"搜索网络资料"、"阅读源码验证"——不是不信任 AI 的分析能力，而是要用实证来兜底它可能的幻觉。

### 9.2 过程中灵机一动：给 AI 换上 root 手机

真正让效率产生质变的，是中途的一个意外发现。

AI 在分析问题时，试图通过 adb 查看设备上已安装 APK 的私有目录（`/data/data/`），但普通手机没有权限。我当时手边刚好有一台 root 过的小米 6，于是换上试试：

> **我**："我当前 adb 连接的设备换成了**具有 root 权限的**，你看看还有什么方向不？"

这一换不得了。AI 瞬间从"只能看日志"变成了"能看文件、能推送资源、能自己安装验证"。之前是我跑命令、复制输出、粘贴给 AI 的低效模式，现在变成了 AI 自主操作的高效模式。

**这个转折让我意识到：AI Agent 的能力不只取决于模型本身，更取决于你给它接上了什么工具。** root 设备就像给 AI 装上了"手"，从此它能自己动手验证，而不是只能动嘴分析。

### 9.3 引导研究方向

在整个过程中，我持续在做的一件事是引导 AI 的研究方向，而不是坐等结果：

| 引导输入                        | 目的                    |
| --------------------------- | --------------------- |
| "**搜索网络相关资料**"              | 让 AI 先了解 Unity 错误背景   |
| "**搜索网络上关于 Unity 的资源加载机制**" | 深入理解 AssetBundle 加载路径 |
| "你可以**运用逆向的知识**再去分析"        | 激活 AI 的逆向分析能力         |
| "你可以**搜索定位字符串或验证你的猜想**"     | 引导 AI 用 strings 分析二进制 |
| "你可以通过**阅读源码，或者网络搜索**来验证"   | 要求实证而非猜测              |
| "先验证研究，不改代码"                | 控制节奏，避免盲目修改           |

这些引导的根据，一半来自事先对 AI 能力的了解（知道它能搜索、能读源码），一半来自过程中的经验积累（发现它真的能做到，就越来越大胆地提要求）。

### 9.4 从问题解决中摸索出的闭环机制

这次最大的收获，是在 v1-v4 四轮迭代中自然形成了一套半自动化闭环：

```
人的操作：安装新包 → "你可以监控验证一下"

AI 自主执行：
  1. adb shell am force-stop（杀旧进程）
  2. adb shell monkey（启动应用）
  3. adb logcat 抓日志分析
  4. adb shell screencap 截图验证
  5. 综合判断：成功/失败 + 下一步建议

人只做 1 步，AI 自主做 5 步。
```

这个闭环在四轮迭代中反复运转，每一轮都更流畅：

| 轮次  | 人的输入             | AI 自主完成                       | 结果          |
| --- | ---------------- | ----------------------------- | ----------- |
| v1  | "你可以监控测试验证了"     | logcat 分析 → 发现 mAppDir 问题     | ❌ 发现新问题     |
| v2  | "你可以监控并测试验证了"    | logcat + ZIP 分析 → 发现 .so Bug  | ⚠️ 发现构建 Bug |
| v3  | "你可以监控验证一下方案的实现" | monkey + logcat + 截图 → 全部通过   | ✅ 完全成功      |
| v4  | "你可以继续测试验证"      | force-stop + 启动 + logcat → 确认 | ✅ 179MB 优化  |

这套机制不是事先设计好的，而是在解决问题的过程中自然形成的。但它是可复用的——后来我把它固化成了项目的 `/local-debug` 技能，新的调试任务可以直接走这个闭环。经过这次探索出来的流程总结，当前已经初步可以跑出从用户描述问题开始的：Agent研究——Agent开发——Agent验证——Agent再研究调整——Agent修改开发——Agent再自主验证的循环闭环解法。

![4d74ddb764f3992e941d90850f7e304e.jpg](https://p0-xtjj-private.juejin.cn/tos-cn-i-73owjymdk6/f3063dee6d6442b5ac174895ba495296~tplv-73owjymdk6-jj-mark-v1:0:0:0:0:5o6Y6YeR5oqA5pyv56S-5Yy6IEAg5bel56iL5biITGlmZQ==:q75.awebp?policy=eyJ2bSI6MywidWlkIjoiMjM2NTgwNDc1NjA3NjU0MSJ9&rk3s=e9ecf3d6&x-orig-authkey=f32326d3454f2ac7e96d3d06cdbb035152127018&x-orig-expires=1774847791&x-orig-sign=am1aUdX%2Fn%2FPgSJL6xogjaHSVta4%3D)

### 9.5 纠正 AI 的错误

AI 不是完美的。整个过程中至少纠正了 6 次错误：

| 纠正输入                         | AI 的错误                       |
| ---------------------------- | ---------------------------- |
| "你启动应用的命令不对，应用没有被启动起来"       | 用 `am start` 指定了错误的 Activity |
| "你检测结果不对，我看到的截图和实际效果是不行的"    | 认为验证通过，实际仍弹错误                |
| "你看的是一次包中云游戏部分的，你要看的是看游戏的逻辑" | 分析了错误的目标                     |
| "你应该直接使用搜索技能"                | 用了报错的内置 WebSearch            |
| "你都没正确触发游戏启动"                | 启动验证流程有误                     |
| "安装包数据损坏...说明现在的资源方案不对吧"     | 误判方案已生效                      |

这也是为什么叫 L3.5 而不是 L4——AI 能自主做很多事，但仍然需要人在关键节点把关纠偏。

---

## 十、能力组合的乘数效应

单个能力的价值有限，但**组合使用**产生了乘数效应：

| 我提供的             | AI 获得的能力              | 在本案例中的作用          |
| ---------------- | --------------------- | ----------------- |
| root 设备 + adb 连接 | 设备操作：安装、启动、监控         | 4 轮迭代的自主验证        |
| Brave Search 技能  | 网络搜索：Unity 机制、AOSP 源码 | sourceDir 方案的技术调研 |
| 原包/一次包路径         | 文件分析：对比目录、检查 ZIP      | 根因定位 + .so Bug 发现 |
| "你可以监控验证"        | 自主闭环：logcat + 截图 + 判断 | 每轮迭代的结果验证         |

**对比：不了解 AI 能力的协作方式**：

```
❌ 不知道 AI 能用 adb → 自己手动跑 logcat → 手动复制日志给 AI → 等 AI 分析
❌ 不知道 AI 懂逆向 → 自己查 AOSP 源码 → 告诉 AI 需要改哪些字段
❌ 不知道 AI 能截图 → 自己看屏幕 → 口头描述给 AI

每一步都变成"人类操作 + 文字传递"，效率降低 5-10 倍。
```

---

## 结语

这次从 "Not enough storage" 到 179 MB 包体优化的过程，经历了 4 轮迭代、多次失败、多次方向修正。它不是一个线性的"发现问题 → 解决问题"过程，而是一个充满探索和回溯的螺旋上升过程。

回顾整个过程，技术方案本身固然重要，但更有价值的是在解决问题过程中对 AI Agent 能力认知的加深，以及摸索出的这套半自动化闭环机制：

**1. 事先了解 Agent 的能力范围** → 知道 AI 具备逆向分析知识、知道它靠 token 预测会产生幻觉，所以一开始就让它搜索验证而非空猜。写在CLAUDE.MD的规则， AI不一定每次都会执行的，所以可增加Hook钩子来提醒它执行。这些都是需要事先了解这些Agent的功能边界。关于 Claude Code 的 MCP、子代理、Hooks、Skills 等核心能力，可以系统了解一下 [《Claude Code 只会问问题？解锁 7 个隐藏能力，效率翻倍》](https://juejin.cn/post/7619245854760009743)，配好这些工具之后，才能跑出本文这样的自动化闭环。

**2. 在过程中发现新的可能性** → 给 AI 换上 root 手机是灵机一动，但效果立竿见影——Agent 的能力边界不只取决于模型，更取决于你给它接上了什么工具。**假设你在同样的环境里面装上frida等逆向工具，它的自动化逆向能力会不会更强？**

**3. 引导方向 + 控制节奏** → "搜索 Unity 加载机制"、"读源码验证"、"先验证研究，不改代码"

**4. 形成可复用的闭环** → 发现问题 → 搜索确认方案 → 实施修复 → 自主安装验证。这套闭环后来被固化成项目的 `/local-debug` 技能

**5.对问题可自动验证须有预判**→AI目前对UI相关细节无法完整详细识别完成自动化闭环，但是它对逻辑，对截图的文字识别具有很强分辨能力，所以本次例子中仅是逻辑和截图中简单文案的判断可以完成自动验证的闭环。

**6. 保持人在回路** → AI 会犯错（6 次纠正），关键决策不能放手——所以是 L3.5，不是 L4

这次经历的启示：**用好 AI Agent，既需要事先了解它的能力边界，更需要在实践中不断加深理解、给它配工具、指方向、建闭环。** 这不是一次性的认知，而是一个持续进化的过程。

---

## 系列文章

本文是「Claude Code 实战系列」的一部分：

- [国内安装 Claude Code 并切换使用国内大模型 API：完整指南](https://juejin.cn/spost/7611769471619645478) — 安装、登录、配置国内模型
- [Claude Code 只会问问题？解锁 7 个隐藏能力，效率翻倍](https://juejin.cn/post/7619245854760009743) — MCP、子代理、Hooks、Skills 核心配置
- **让 AI 当逆向工程师（本篇）** — Claude Code 自主分析 APK 和 so 文件的完整实战
