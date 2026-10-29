---
title: "CLI：AI Agent 真正的'手'——兼谈 CLI-Anything 如何让万物 Agent 化"
date: 2026-04-04
description: "厘清CLI在Agent工具链的定位，解析CLI-Anything自动化流水线，对比Android的ADB方案体系。"
tags: []
category: "技术"
source: "https://juejin.cn/post/7624447286865362984"
---
## 前言

上一篇讲完了 MCP 协议[《AI Agent 的外部连接层：MCP 协议原理、机制设计与实战开发》](https://juejin.cn/post/7616025751747182598 "https://juejin.cn/post/7616025751747182598")——AI Agent 工具调用的标准化层。很多读者留言问：「CLI 直接调用到底算什么，和 MCP 是什么关系？什么时候该用 CLI，什么时候用 MCP？」

这篇来彻底回答这个问题。

本文会厘清 CLI 调用在 Agent 工具链中的本质定位，深度解析最近在 AI 圈爆火的开源项目 **CLI-Anything**——港大数据科学实验室（HKUDS）出品，发布首周即突破万星、截至发稿已超 27K Star，它用一个 7 阶段自动化流水线，把「让任意软件变成 Agent 可调用的 CLI」这件事做成了工业级方案，已覆盖 16+ 个专业软件，通过了 1,800+ 个测试。

**同时**，本文还会专门回答一个 Android 开发者会自然冒出的问题：CLI-Anything 这套方案能用在 Android App 上吗？答案是不能——但 Android 有一套以 ADB 为地基的等价体系，某种程度上比桌面端更成熟，和上一篇文章[《AI 当逆向工程师：Claude Code 自主分析 APK 和 so 文件，解决 Unity 插件化启动崩溃》](https://juejin.cn/post/7622139072376684579 "https://juejin.cn/post/7622139072376684579")里「给 AI 换上 root 手机」的实战场景直接衔接。

---

## 一、先厘清：三者的分工，不是竞争

先把常见的混淆拆开。上篇 MCP 文章里有一张三层对比图，这里再补充一下它们在实际调用链里的位置：

```
用户："帮我用 Blender 渲染这个 3D 场景"
        │
        ▼
[模型层] AI 模型通过 Function Calling 格式表达意图：
        {"tool": "blender_render", "params": {"scene": "room.blend"}}
        │
        ▼
[协议层] Agent 应用通过 MCP 协议，把请求发给 Blender MCP Server
        │
        ▼
[执行层] MCP Server 内部，通过 subprocess 调用 CLI：
        $ cli-anything-blender render --scene room.blend --output out.png
        │
        ▼
[Blender 真实引擎] 渲染，返回结果
```

所以 CLI 调用**不是"第三种替代方案"**，而是执行层的具体实现。同时它也可以绕过 MCP，让 Agent 直接在终端执行命令——这在 Claude Code 这类编程 Agent 里极为常见：Claude Code 每次运行 `bash`、`grep`、`git`、`jq`，走的都是 subprocess 直接调用，和 MCP 毫无关系。

三者的关系是：

```
Function Calling  →  AI 的语言：表达"我想做什么"
MCP 协议          →  工具的标准接口：统一发现和路由  
直接 CLI 调用     →  真正的执行：命令落地的地方
```

---

## 二、GUI 的敌意：为什么图形界面是 AI Agent 的噩梦

要理解 CLI 为什么重要，先理解它在解决什么问题。

现在的软件世界分裂成两个平行宇宙：

**第一个宇宙：API 优先的云服务**
Stripe、Twilio、各种 SaaS——天生有 REST API。AI Agent 直接 HTTP 调用，零障碍。

**第二个宇宙：GUI 优先的桌面软件**
GIMP、Blender、LibreOffice、Audacity、OBS Studio、各种开发工具IDE——这些是专业工作流真正依赖的工具。它们为人类的眼睛和双手设计：浮动面板、工具栏、拖拽操作、右键菜单。

当 AI Agent 试图操控第二类软件时，只有三条路：

| 方案 | 做法 | 核心问题 |
| --- | --- | --- |
| 手写 Wrapper | 逐个研究软件 API，手动封装 | 耗时数周，软件版本一更新就失效 |
| RPA 自动化 | 截图 → 视觉模型识别 → 模拟点击 | 窗口布局、主题、分辨率任意变化就崩 |
| 直接 CLI | 调用软件底层 API，生成结构化命令 | **这才是正确答案** |

RPA 的脆弱性不是工程问题，而是架构问题：它在模仿人类操作，而人类操作本身就不是为机器设计的。一个按钮换了颜色，整套自动化就失效了。

CLI 走的是另一条路：**绕过 GUI，直接调用软件已有的底层 API**。GUI 只是软件给人看的外壳，底层 API 才是软件真正的神经系统。

---

## 三、CLI 的四大天赋：为什么它是 Agent 最顺手的工具

CLI 天然适合 Agent 的工作方式，有四个结构性优势：

### 天赋 1：可组合性（Composability）

命令可以管道链接，一个命令的输出成为下一个命令的输入：

```
# Agent 完成：图片处理 → 压缩 → 上传，三步一气呵成
cli-anything-gimp image resize --input photo.jpg --width 1920 --output resized.png && \
  cli-anything-gimp export --format webp --quality 80 --input resized.png -o final.webp && \
  aws s3 cp final.webp s3://bucket/
```

这种 Unix 链式组合是 GUI 软件根本做不到的。Agent 可以把多个工具串联成自动化流水线，不需要任何中间件。

### 天赋 2：相对于 RPA 的确定性（Determinism）

相同的命令 + 相同的参数，在相同的环境下产生相同的结果。不存在「今天 UI 渲染有点不一样」的情况。

这对 AI Agent 极为关键：Agent 需要能重复执行、能调试、能回溯的操作。RPA 的截图方案天然非确定——光线条件、系统主题、字体渲染都可能影响结果。当然，CLI 也受环境变量和软件版本影响，但这是可控的变量，而不是像 RPA 一样的视觉噪声。

### 天赋 3：自文档化（Self-documentation）

每个 CLI 工具都自带 `--help`：

```
$ cli-anything-gimp --help
Usage: cli-anything-gimp [OPTIONS] COMMAND [ARGS]...

  GIMP CLI - Agent-native interface for GIMP

Commands:
  image      Image manipulation operations
  layer      Layer management
  export     Export to various formats
  ...
```

Agent 不需要提前知道工具的所有功能，它可以动态探索、动态学习。这和 MCP 的 `tools/list` 发现机制完美契合。

### 天赋 4：对 Context Window 极其友好

这一点经常被忽视，但在生产环境中至关重要。

一个有 20 个工具的 MCP Server（比如官方 Stripe MCP），在会话开始时会把**所有工具 schema 全部加载进上下文**——即使本次任务只需要用其中 2 个。行业实测数据显示，每个 MCP 工具的 schema 通常消耗 **550-1,400 tokens**，20 个工具意味着数千甚至上万 tokens 的"入场费"。而一条 CLI skill 描述通常只需几十 tokens——差距可达两个数量级。

在多步调试工作流中，这种差距会被放大：MCP 方案的 schema 开销不断挤压可用上下文，CLI 方案则几乎零开销。实际测试中，工具数量越多、对话轮次越长，CLI 方案的 token 效率优势越明显。

```
MCP 方案：会话开始时加载所有工具 schema → 数千 tokens 的"入场费"
CLI 方案：零 schema 开销，Agent 直接 subprocess 调用 → 几十 tokens 搞定
```

---

## 四、CLI-Anything：把"让软件 Agent 化"变成一条工业流水线

问题来了：给每一个 GUI 软件手写 CLI Wrapper，工程量依然巨大。GIMP 有数百个功能，Blender 更复杂。

港大 HKUDS 实验室的回答是：**不用手写，让 AI 自动生成**。

这就是 CLI-Anything 的核心：把任意软件的源码扔进去，自动产出一套完整的、经过严格测试的、Agent 可用的 CLI。

### 7 阶段自动化流水线

```
Phase 1: Analyze（分析）
    扫描源代码，识别 GUI 事件处理器、API 调用、用户操作
    将"点击按钮"等 GUI 交互映射成可编程的函数接口

Phase 2: Design（设计）
    设计命令组结构（如 image / layer / export）
    构建状态模型（当前项目、选中对象、编辑历史）
    定义标准化输入输出格式和错误处理规范

Phase 3: Implement（实现）
    基于 Python Click 框架生成完整 CLI 代码
    内建 --json 结构化输出、REPL 交互模式、持久化项目状态

Phase 4: Plan Tests（测试规划）
    基于分析结果自动生成 TEST.md，规划覆盖边界条件的测试策略

Phase 5: Write Tests（编写测试）
    实现单元测试 + 端到端测试，覆盖所有命令路径

Phase 6: Document（文档）
    更新 TEST.md，完善命令文档和使用示例

Phase 7: Publish（发布）
    生成 setup.py，pip install -e . 安装到系统 PATH
    Agent 通过 which cli-anything-gimp 即可发现工具
```

整个过程：**一条命令触发，全程自动**。

```
# 以 Claude Code 为例安装插件（也支持 OpenCode、Codex 等平台）
/plugin marketplace add HKUDS/CLI-Anything
/plugin install cli-anything

# 对任意软件生成 CLI（指向源码目录或 GitHub 仓库）
/cli-anything /path/to/gimp/source
```

### 关键设计：调用真实后端，不重新实现功能

这是 CLI-Anything 和各种"轻量 Wrapper"最本质的区别。

生成的 CLI **不是在重新实现软件功能**，而是通过 subprocess 调用软件本身的原生 API、脚本接口或无头模式，驱动真实的软件后端：

- `cli-anything-blender render` → subprocess 调用真正的 Blender 渲染引擎
- `cli-anything-libreoffice writer export --format pdf` → 调用 LibreOffice 自己的 PDF 导出模块
- `cli-anything-gimp image resize` → 调用 GIMP 的原生图像处理 API

结果：生成的 PDF 和你手动用 LibreOffice 导出的**完全一致**——格式、字体、布局不差分毫。这不是近似实现，是真实软件能力的完整透传。

### 测试覆盖：不是 Demo，是工程

截止目前，CLI-Anything 已覆盖 16+ 个专业软件（且仍在持续增加），通过了 **1,800+ 个测试**（含单元测试、端到端测试、Node.js 测试），**通过率 100%**。

这比大多数开发者手写的 Wrapper 更严格。

### CLI-Anything 的局限性

需要正视的边界：

- **需要有源码**：分析阶段依赖扫描源代码，闭源商业软件不适用
- **目前聚焦开源软件**：GIMP、Blender 这类开源专业工具是主战场
- **多平台支持但仍在早期**：目前已适配 Claude Code、OpenCode、Codex、GitHub Copilot CLI 等 6+ 个 Agent 平台，但核心流水线仍在快速迭代中

---

## 五、实战：Agent 通过 CLI-Anything 操控专业软件

### 场景 1：Agent 驱动 LibreOffice 批量生成报告

```
# 创建新文档
cli-anything-libreoffice writer new -o report.json

# 添加结构化内容
cli-anything-libreoffice writer heading --level 1 --text "2026 Q1 销售报告"
cli-anything-libreoffice writer paragraph --text "本季度总营收同比增长 23%..."
cli-anything-libreoffice writer table \
  --data '[["地区","销售额","增长率"],["华东","320万","28%"],["华南","280万","19%"]]'

# 导出真实 PDF
cli-anything-libreoffice writer export --format pdf -o q1_report.pdf
```

Agent 不打开任何界面，不"看"屏幕，输出是 LibreOffice 引擎生成的真实 PDF。

### 场景 2：Agent 驱动 Blender 创建 3D 场景

```
# 新建项目
cli-anything-blender project new --width 1920 --height 1080 -o scene.json

# 添加几何体和材质
cli-anything-blender mesh add --type cube --location "0,0,1"
cli-anything-blender material set --object cube --color "#2563EB" --roughness 0.3

# Cycles 渲染
cli-anything-blender render --engine cycles --samples 128 -o output.png
```

光照、材质、阴影全部由 Blender 真实引擎计算。

### 场景 3：GIMP 批量图像处理

```
# 批量调整尺寸 + 添加水印（每次调用独立处理一张图，通过 --input/--output 串联步骤）
for f in *.jpg; do
  cli-anything-gimp image resize --input "$f" --width 1920 --height 1080 --output "resized_$f"
  cli-anything-gimp layer add --input "resized_$f" --type text --text "© 2026 MyBrand" \
    --position "bottom-right" --opacity 0.7 --output "watermarked_$f"
  cli-anything-gimp export --input "watermarked_$f" --format jpg --quality 90 -o "output_$f"
done
```

100 张图，Agent 自动完成，不需要人工操作 GIMP 一次。

---

## 六、Android 篇：CLI-Anything 到不了的地方，ADB 早就在了

> 这一节专门写给 Android 开发者。如果你读完前面几节，自然会问：CLI-Anything 这套方案能用在 Android App 上吗？

### 为什么 CLI-Anything 不适用于 Android

CLI-Anything 的核心是**扫描桌面软件源码**，从 GUI 事件处理器提取接口，生成可 subprocess 调用的 Python CLI 包。这个链路在 GIMP、Blender 上成立，是因为软件和 Agent 运行在同一台电脑上。

Android App 有三道根本性的墙：

| 障碍 | 说明 |
| --- | --- |
| **沙箱隔离** | App 运行在手机/模拟器的 ART 沙箱里，不是 PC 的本地进程 |
| **源码不可扫描** | 大多数 APK 没有可读源码，打包后是编译过的 DEX 字节码（经过混淆/加固后更难分析） |
| **无本地 CLI 入口** | 没有像 LibreOffice 那样能直接 subprocess 调用的命令行接口 |

所以 CLI-Anything 的 7 步流水线在 Android 这里根本走不通。

### Android 的地基：ADB 就是桌面世界的 CLI

Android 天生有一个对 Agent 极为友好的 CLI——**ADB（Android Debug Bridge）**。作为 Android 开发者，你天天在用它：

```
adb install myapp.apk          # 安装
adb shell am start -n pkg/.Activity   # 启动 Activity
adb shell input tap 540 1200   # 点击坐标
adb logcat -s MyTag            # 抓日志
adb shell screencap /sdcard/screen.png && adb pull /sdcard/screen.png  # 截图
```

ADB 的地位，等同于 CLI-Anything 为桌面软件生成的那套 CLI——都是**绕过 GUI，直接调用底层能力**。区别只是一个在本机 subprocess，一个通过 USB/网络桥接到设备。

但裸用 ADB 有个问题：`adb shell input tap 540 1200` 是坐标硬编码，分辨率一变就失效，和 RPA 的脆弱性如出一辙。Agent 真正需要的是**结构化的 UI 元素引用**，而不是像素坐标。

这就是 Android Agent CLI 生态要解决的问题。

### 三个成熟方案

#### 方案一：agent-android（最轻量，Snapshot + Ref 模式）

> PyPI：`pip install agent-android`（v1.4.0，纯 Python 实现）

```
# 1. 安装（前置条件：ADB 已安装并在 PATH，设备开启 USB 调试）
pip install agent-android
adb devices   # 确认设备已连接

# 2. 连接 + 启动 App
./agent-android connect
./agent-android start_app com.example.myapp

# 3. 获取带 Ref 的可交互 UI 快照（-i 只显示可交互元素）
./agent-android snapshot -i
# 输出（结构化元素列表，不是像素坐标）：
# - TextView "确认支付" [id=com.app:id/confirm] [clickable] [ref=e1]
# - EditText "输入金额" [id=com.app:id/amount]             [ref=e2]
# - Button   "取消"    [id=com.app:id/cancel]  [clickable] [ref=e3]

# 4. 通过 Ref 操控，跟分辨率彻底解耦
./agent-android tap @e1
./agent-android input "99.00"    # 在当前焦点处输入
./agent-android get text @e1     # 读取元素文本

# 5. 其他常用操作
./agent-android screenshot screen.png
./agent-android swipe 100,200 300,400
./agent-android press home
./agent-android stop_app com.example.myapp
./agent-android disconnect
```

**Agent 使用方式**：在 CLAUDE.md 里写「需要操控 Android 设备时，使用 agent-android 工具，先 `snapshot -i` 拿元素列表，再用 `@ref` 操控，不要猜坐标」。Agent 即可自主完成「快照 → 识别 → 操控 → 验证」的闭环。

**核心设计**：把像素坐标转成语义化 `@ref` 引用——和 CLI-Anything 的 `--json` 结构化输出是同一种哲学：让机器只处理机器该处理的格式。

---

#### 方案二：agent-device（跨平台，iOS / Android / macOS / tvOS / AndroidTV 通用）

> GitHub：[callstackincubator/agent-device](https://link.juejin.cn?target=https%3A%2F%2Fgithub.com%2Fcallstackincubator%2Fagent-device "https://github.com/callstackincubator/agent-device")
> 需要 Node 22+，Callstack 团队出品

```
# 1. 安装
npm install -g agent-device
agent-device --version   # 验证

# 2. 【关键步骤】把操作手册作为 Skill 注入 Claude Code
#    装完后 Agent 自动知道完整操作范式，无需每次解释命令
npx skills add https://github.com/callstackincubator/agent-device --skill agent-device
# 也可在 ClawHub 搜索 "agent-device" 安装

# 3. 标准 Agent 操作流程
agent-device open com.example.myapp --platform android  # 建立 session

agent-device snapshot -i          # 拿带 Ref 的可交互元素快照
# 输出：
# @e1 [button]   "登录"
# @e2 [edittext] "用户名"
# @e3 [edittext] "密码"

agent-device press @e2            # 点击（press 是标准命令，click 是别名）
agent-device fill @e2 "test@example.com"   # 先清空再输入
agent-device fill @e3 "mypassword"

agent-device diff snapshot -i     # 操作后对比 UI 变化（低噪声，token 高效）
agent-device screenshot result.png
agent-device logs stream --app com.example.myapp  # 日志流（自动跟随 App 重启后新 PID）

agent-device close                # 释放 session
```

**Skill 的价值**：注入 Skill 后，Claude Code 不只是会执行命令，而是理解完整操作范式——什么时候 snapshot、什么时候 diff、元素消失时怎么重试。无需在每次会话里解释用法。

**`diff snapshot` 是核心亮点**：Agent 操作后精确知道 UI 变了什么，而不是重新截图识别。Token 消耗低，速度更快。

---

#### 方案三：Android-Debug-Bridge-MCP（接入 Claude Code 最快路径）

> npm：`npm install -g android-debug-bridge-mcp`

如果你不想折腾 Python 环境或 Node Skill，这是最省事的接入方式——直接把 ADB 能力作为 MCP Server 挂进 Claude Code，一条命令搞定：

```
# 1. 安装
npm install -g android-debug-bridge-mcp

# 2. 全局接入 Claude Code（所有项目生效）
claude mcp add --scope user android-debug-bridge-mcp -- npx android-debug-bridge-mcp

# 验证已接入
claude mcp list
```

接入后无需任何其他配置，Claude Code 在会话中就能直接调用 ADB 操控手机，不再需要你手动跑命令再把结果粘贴给 AI。

**最有价值的特性是 UI Automator 集成**——返回当前界面的完整 XML 结构，让元素定位精准可靠：

```
<!-- Claude Code 调用 UI Automator 后拿到的结构化界面描述 -->
<hierarchy>
  <node class="android.widget.Button"
        text="确认支付"
        resource-id="com.app:id/confirm"
        clickable="true"
        bounds="[108,1847][972,1953]" />
  <node class="android.widget.EditText"
        text=""
        resource-id="com.app:id/amount"
        bounds="[108,1650][972,1750]" />
</hierarchy>
```

Agent 拿到 XML 后可以按 `resource-id` 或 `text` 定位元素，再通过 ADB 执行操作——比裸猜坐标稳定，也比 UI Automator 测试脚本轻量。

**三个方案对比**：

|  | agent-android | agent-device | ADB MCP |
| --- | --- | --- | --- |
| **安装** | `pip install` | `npm install -g` | `npm install -g` + MCP 接入 |
| **接入 Claude Code** | 写 CLAUDE.md | 装 Skill | MCP 协议，零配置 |
| **元素定位** | `@ref` | `@ref` | XML selector |
| **Diff 感知** | ❌ | ✅ | ❌ |
| **最适合场景** | 轻量探索操控 | 深度 Agent 集成 | 快速接入，无额外依赖 |

### 和上篇「换 root 手机」的衔接

上一篇文章的转折点是：把 adb 切换到 root 设备，AI 从「只能看日志」变成「能直接操作设备」。那次是手动让 Claude Code 调 `adb shell` 命令。

现在有了这套工具链，**升级路径**是：

```
[现状] Claude Code 裸调 adb shell 命令
    → 命令靠 AI 猜，坐标硬编码，截图靠人工粘贴
         │
         ▼
[升级] 接入 Android-Debug-Bridge-MCP + agent-android
    → Agent 拿到结构化 UI 树（@e1 / XML）
    → snapshot diff 感知操作结果
    → 真正实现「安装包 → AI 自动测试验证」的完整自动化闭环
```

这也是 Android 开发者最直接能用上 CLI-Agent 体系的场景：**把 CI/CD 里的回归测试、兼容性验证、截图对比，交给 Agent 跑**——不需要写 Espresso 测试，不需要维护 UI Automator 脚本，Agent 会自己探索界面、自己写验证逻辑。

### 桌面 vs Android：CLI Agent 体系对比

| 维度 | CLI-Anything（桌面） | ADB Agent CLI（Android） |
| --- | --- | --- |
| **信息来源** | 扫描软件源码 | ADB + Accessibility Tree（无障碍树） |
| **元素定位** | 函数参数（`--input file`） | Ref（`@e1`）或 XML selector |
| **操控通道** | 本机 subprocess | ADB 桥接（USB / 网络） |
| **状态感知** | 项目文件（`.json`）持久化 | snapshot + diff |
| **工具生成** | AI 自动从源码生成 | 现成工具，直接安装 |
| **适用对象** | 开源桌面软件 | 任意 Android App（无需源码） |

一个有趣的反差：CLI-Anything 需要源码才能工作，而 ADB 方案**不需要 App 源码**——只要能装到设备上，Agent 就能通过 Accessibility Tree 理解和操控它。**这意味着 Android 开发者甚至可以让 Agent 去操控竞品 App 做功能对比测试。**

---

## 七、什么时候用 CLI，什么时候用 MCP？

两者不是非此即彼，是按场景分工的工具组合。

```
flowchart TD
    A["需要给 AI Agent 接入一个工具"] --> B{"有成熟的 CLI 工具？"}

    B -->|是| C["✅ 直接用 CLI\n零 schema 开销\n可管道组合\nAgent 训练数据熟悉"]

    B -->|否| D{"需要复杂状态管理\nOAuth / 流式响应？"}

    D -->|是| E["✅ 用 MCP\n结构化可发现\n权限管理完善\n跨平台标准协议"]

    D -->|否| F{"能写一个\nCLI Wrapper 吗？"}

    F -->|是| G["✅ 写 CLI Wrapper\n或用 CLI-Anything\n自动生成"]

    F -->|否| E

    style C fill:#d4edda,stroke:#28a745,color:#155724
    style E fill:#cce5ff,stroke:#004085,color:#004085
    style G fill:#d4edda,stroke:#28a745,color:#155724
```

实际上，两者经常**同时存在于同一个 Agent 系统**：

- Claude Code 用 CLI subprocess 执行本地操作（git、bash、编译器）
- 同时连接 MCP Server 访问外部服务（GitHub API、Slack、数据库）
- 两者背后共用同一套 Skills/CLAUDE.md 来引导 Agent 行为

**一个直观的判断标准**：

- 内层循环（本地、高频、低延迟）→ 优先 CLI
- 外层循环（外部服务、OAuth、多租户）→ 优先 MCP

---

## 八、CLI-Anything + MCP：完整的 Agent 工具栈

CLI-Anything 生成的 CLI，可以直接成为 MCP Server 的执行后端：

```
用户："帮我把这批照片处理成产品图"
    │
    ▼
Function Calling：AI 表达意图 → 需要图像处理工具
    │
    ▼
MCP 协议：Agent 把请求路由给 GIMP MCP Server
    │
    ▼
CLI-Anything GIMP：MCP Server 通过 subprocess 调用 cli-anything-gimp
    │
    ▼
真实 GIMP 引擎：处理图像，返回结构化 JSON 结果
```

三层各司其职，最终让 Agent 摸到真实软件的核心能力。

---

## 结语：今天的软件为人类而生，明天的用户是 Agent

CLI-Anything 项目的 slogan 是：

> *"Today's software serves humans. Tomorrow's users will be agents."*

过去 40 年，软件设计的前提是：**人类是操作者**。所以有 GUI，有视觉反馈，有鼠标交互——一切为了降低人类的认知负担。现在这个前提正在改变。在越来越多的场景里，**Agent 才是操作者**——它需要的不是漂亮的 UI，而是结构化的输入输出、可重复的确定性行为、可组合的接口。

CLI-Anything 发布首周即突破万星，因为**它击中了一个正在形成的时代需求**：不是所有软件都会重写成 API-first 的架构，但通过 CLI-Anything，现有桌面软件可以在几分钟内变成 Agent 可以调用的工具。

国内现在很多IM软件，如钉钉，飞书等，都第一时间推出了CLI版本，目的就是为了适配Agent直接调用。

回到最初的问题——CLI 直接调用在三层工具链中是什么位置？

- **Function Calling**：AI 的语言，表达"我想做什么"
- **MCP**：工具的标准接口，统一发现和路由
- **CLI 直接调用**：真正的执行层，Agent 的"手"

三者不是替代关系，而是**从意图到执行的完整链路**。CLI 是 Agent 时代的地基——那些无法通过 HTTP API 触达的专业软件、那些深嵌在桌面工作流中的工具，正在以前所未有的速度向 Agent 开放。

**假设你手边有一个没有 API 的内部工具，你会怎么让 Agent 操控它？** 也许 CLI-Anything 的 7 步流水线就是答案——或者至少是一个足够好的起点。
