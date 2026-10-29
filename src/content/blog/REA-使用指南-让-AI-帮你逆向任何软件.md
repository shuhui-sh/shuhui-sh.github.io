---
title: "REA 使用指南：让 AI 帮你逆向任何软件"
description: "REA是13万star的MCP逆向工具包，让AI助手具备逆向分析能力，用自然语言问出任意软件的实现原理。本文详解接入配置、Ubuntu实测全流程，并深挖Notion剪贴板桥官方案例。"
pubDate: "2026-10-13"
tags: ['人工智能', '逆向', 'REA', 'AI']
heroImage: "/images/REA-使用指南-让-AI-帮你逆向任何软件/01.png"
---
> 项目地址：[github.com/morluto/rea](https://link.juejin.cn?target=https%3A%2F%2Fgithub.com%2Fmorluto%2Frea "https://github.com/morluto/rea") ｜ MIT 开源 ｜ 13 万+ star
> 官网：[rea.tools](https://link.juejin.cn?target=https%3A%2F%2Frea.tools "https://rea.tools")

## 一句话认识 REA

REA（Reverse Engineer Anything）是一个 MCP 逆向工具包。它把逆向分析能力装进你的 AI 编程助手（Claude Code、Cursor、Codex 等），让你用**自然语言**问出"这个 App 的某个功能是怎么实现的"，AI 会去查二进制、追调用链，然后把证据和结论一起交给你。

传统逆向：你手啃汇编 → 跟调用 → 还原逻辑。
用 REA：你提问题 → AI 去啃 → 你看结论和证据。

## 适合谁

- 想复刻某个 App 功能的产品/独立开发者："Notion 的剪贴板同步是怎么做的？"
- 想理解闭源软件行为的安全研究者、CTF 玩家
- 好奇"为什么计算器上 200+10% 等于 220" 的技术爱好者

不适合：完全没接触过编程概念的纯小白（至少要能看懂 AI 给你的解释）。

## 准备工作

只需要 Node.js：**22.x（≥22.19）、24.x（≥24.11）或 26+**，外加 npm。

```
node -v   # 确认版本符合要求
```

## 第一步：把 REA 接入你的 AI 助手（2 分钟）

终端里运行一条命令：

```
npx rea-agents setup
```

它会让你选择要接入的助手（支持 Claude Code、Codex、Cursor、Gemini CLI、Grok Build 等），展示配置变更方案让你确认，装好后**重启你的 AI 助手**即可。

不想交互式确认，一条命令直接配好（以 Claude Code 为例）：

```
npx -y rea-agents setup --yes --client claude_code
```

`--yes` 跳过确认，`--client` 指定助手；想先看它打算改什么不真正执行，加 `--dry-run`。原生分析想顺手装 Hopper 再加 `--install-hopper`。

想长期用，可以全局安装：

```
npm install --global rea-agents
rea --help    # 查看所有命令
rea update    # 保持更新（REA 迭代很快）
```

## 实测：在 Ubuntu 24.04 上从零跑通（2026-10-12）

以下每一步都是在这台 Linux 云主机（Ubuntu 24.04.5 LTS，x86\_64，Node v24.20.0）上真实跑过的：

**1. 装 Claude Code**——发现它已经全局预装了（`claude --version` → 2.1.296），`npm install -g @anthropic-ai/claude-code` 再跑一遍也无妨。

![环境检查](/images/REA-使用指南-让-AI-帮你逆向任何软件/01.png)

**2. 装 REA**：`npm install -g rea-agents`，装上的是 rea@6.4.0。

![安装 REA](/images/REA-使用指南-让-AI-帮你逆向任何软件/02.png)

**3. 接入**：

```
npx -y rea-agents setup --yes --client claude_code
```

执行后检查到两个落点：

- `~/.claude.json` 里注册了 MCP 服务器 `rea`（启动命令 `npx -y rea-agents@6.4.0 mcp`）；
- skill 装到了 `~/.claude/skills/reverse-engineer-anything/`（含 SKILL.md 和 references 参考文档）。

重启 Claude Code 后，170 个 REA 工具即可被助手调用。下面是 `setup --dry-run` 的真实输出（本机已配好，plannedActions 为空，幂等不重复写配置）：

![setup dry-run](/images/REA-使用指南-让-AI-帮你逆向任何软件/03.png)

![claude.json 内容](/images/REA-使用指南-让-AI-帮你逆向任何软件/04.png)

**4. 自检**：`rea doctor`。实测输出：`healthy: false`，`environment_healthy: false`——node（24.20.0）和 host（ubuntu 24.04）都是 ✓，但 Hopper、Ghidra、IDA 三个原生分析引擎都没装。结论：**JS / Electron / 网站 / APK 等静态分析照常可用；原生二进制的深度反编译需要你自备一个引擎**（Ghidra 需设 `GHIDRA_INSTALL_DIR` 指向 12.1.x 解压目录）。

![rea doctor](/images/REA-使用指南-让-AI-帮你逆向任何软件/05.png)

**5. 真实演示**：建一个只有 3 个文件的 demo 应用（package.json + index.js + lib.js），跑：

```
rea analyze-javascript-application ./app
```

![分析演示](/images/REA-使用指南-让-AI-帮你逆向任何软件/06.png)

约 4 秒完成。输出里有 `evidence_id`（ev\_ 开头）、`root_artifact_sha256`，以及一张 9 个节点的 `JavaScriptApplicationGraph` 应用图谱——每个观测都带 evidence，标注 `authority: artifact-bytes`、`confidence: exact`。也就是说它不是"猜"的，是逐字节哈希锁定的证据链。

**6. 在 Claude Code 里用**：接入后直接中文问就行，例如"这个目录是个什么应用？入口文件和模块调用关系是怎样的？"——助手会按 skill 里的路由规则自动调用 REA 的 MCP 工具，你只管看结论和证据。

## 第二步：用自然语言提问

接入后不需要学任何新语法，直接问。官方给的示例：

> Understand how search works in the Notes app, show me the evidence, and build a similar feature for my project.

翻译成你的场景，比如：

- "用 REA 检查微信读书的划线同步功能，它的数据存在哪，同步逻辑是什么？"
- "分析这个 Electron 应用的自动更新机制，把证据列出来"
- "看看计算器 App 里 % 按钮在 + 和 × 后面的计算规则有什么不同"

AI 会调用 REA 的工具去实际检查目标，返回的结论**附带证据和局限性说明**——它会告诉你哪些是确认的、哪些是不确定的，这点很关键。

官网的经典演示：问"为什么计算器上 200+10% 等于 220"，REA 直接读出安装版计算器 DLL 里 % 处理函数的分支逻辑——加号后面是"取第一个数的百分比"，乘号后面是"除以 100"，AI 拿着反汇编证据给你讲明白。

## 第三步：命令行直接分析（不用 AI 也行）

同一套能力也可以在终端里直接用。比如分析一个解包后的 Electron 应用目录：

```
npx -y rea-agents@latest analyze-javascript-application /path/to/app --json
```

返回模块结构、import 关系、Electron 主进程/渲染进程边界、IPC 调用等，JSON 格式方便写脚本处理。

## 它能分析什么

| 目标 | 能拿到什么 |
| --- | --- |
| 原生二进制（exe/dll/so/Mach-O） | 伪代码、汇编、字符串、符号、调用关系 |
| JavaScript / Electron 应用 | 模块、路由、IPC、原生依赖关系 |
| 网站 | 页面结构、脚本、网络请求、截图 |
| Android APK | Manifest、类、反编译方法 |
| .NET 程序集 | 元数据、CIL 指令 |
| Go 二进制 / WASM / EVM 字节码 | 各自对应的结构化信息 |
| 进程行为 / 网络抓包（HAR） | 运行时的输出、文件操作、请求明细 |
| 固件 | 分区、解包结果 |

**原生二进制深度分析**需要配一个反编译引擎：Hopper、Ghidra 或 IDA 三选一（setup 时可按提示安装 Hopper）；纯 JS 和 .NET 的静态分析不需要引擎，开箱即用。

分析全程在**本地**运行，不上传你的目标文件。

## 三个实战案例（官方 showcase）

1. **DX-Ball 音效还原**：从一个老游戏的二进制里跟出"声音左右声道计算"函数，还原成 C 语言，通过了 3205 个原始测试用例。
2. **Notion 剪贴板追踪**：从渲染进程的剪贴板 API 出发，穿过 preload 和 IPC，一直跟到主进程，还原富文本剪贴板的完整链路（下面有完整深挖）。
3. **TH04 弹幕还原**：分析 16 位 DOS 游戏的汇编，还原出弹幕圆环的角度计算公式。

官网还有个互动例子：分析 Chrome 小恐龙游戏，找出"速度从 6 开始、每次加速 0.001、上限 13"的规则，然后让你拖滑块自己改速度玩。

## 实战深挖：Notion 的剪贴板桥（官方 showcase 详解）

> 本节改写自 REA 官方 case study（对象：Notion Desktop 7.6.1；记录时用 REA 4.1.0），原文：[rea.tools/showcase/no…](https://link.juejin.cn?target=https%3A%2F%2Frea.tools%2Fshowcase%2Fnotion%2F "https://rea.tools/showcase/notion/")

**要回答的问题**：在 Notion 里选中一块内容按 Ctrl+C，文本和 HTML 是怎么穿过 Electron 的进程边界、写进系统剪贴板的？这是每个想复刻"富文本复制"功能的开发者都会问的问题——也是本文开头"适合谁"里提到的典型场景。

**给 AI 的提问**（按官方示例改写）：

```
用 REA 追踪 Notion 是怎么把文本和 HTML 复制到系统剪贴板的，
把每一步的代码摆出来，并给出证据。
```

### 第一步：REA 直接告诉你从哪开始读

Notion 桌面版是个 Electron 应用，核心逻辑打在 `app.asar` 包里。对它的 tab preload 跑 `analyze_javascript_application`，REA 直接给出两个精确位置：

- 页面能看到的 API：`__electronApi`，位于 `preload.js` 第 1 行第 22764–22828 列
- 发起 IPC 请求的调用：`invoke` 操作，channel 表达式在 `preload.js:1:6486–6522`

混淆后的 bundle 动辄几十万列，人工翻等于大海捞针——REA 把"去哪看"精确到了列。AI 打开这两个位置，在拼装好的 API 里找到 clipboard 成员，顺着它的 `invokerInMain` 调用拿到通道名 `notion:clipboard:write`，再去主进程 bundle 里搜这个名字。四段代码，链路就通了。

### 第二步：四段代码，一条完整链路

**① 页面暴露的 API**——渲染进程里能摸到的就是它：

```
const clipboardApi = {
  write: invokerInMain("notion:clipboard:write")
};
// 经 contextBridge 暴露为 window.__electronApi.clipboard
```

**② preload 的包装器**——请求怎么离开渲染进程：

```
function invokerInMain(channel) {
  return (...args) => invokeInMainAndReturnResult(channel, ...args);
}
function invokeInMainAndReturnResult(channel, ...args) {
  return ipcRenderer.invoke(channel, ...args);
}
```

这里用的是 Electron 的请求—响应式 IPC（`ipcRenderer.invoke`），不是 fire-and-forget 的 send。

**③ 主进程的注册**——另一头也有包装器：

```
const handleRequestFromRenderer = {
  addListener(channel, handler) {
    ipcMain.handle(channel, handler);
  }
};
```

**④ 终点：写剪贴板前的发送者检查**：

```
handleRequestFromRenderer.addListener(
  "notion:clipboard:write",
  (event, data) =>
    isNotionWebContents(event.sender)
      ? clipboard.write(data)
      : undefined
);
```

注意这个细节：不是谁发请求都处理——先验 `event.sender` 是不是 Notion 自己的 webContents，通过才调 Electron 的 `clipboard.write(data)`。安全边界就藏在这一行三元表达式里。

![Notion 剪贴板桥链路图](/images/REA-使用指南-让-AI-帮你逆向任何软件/07.png)

### 第三步：为什么粘贴后格式不丢？——富剪贴板格式

光把文本写进剪贴板，块结构就丢了。Notion 的做法是**三样东西一起写**：

1. 纯文本 `text`
2. HTML，里面埋一条注释：`<!-- notionvc: <copy-id> -->`
3. 自定义 MIME 类型 `text/_notion-blocks-v3-production`，携带结构化块数据

粘贴时的还原逻辑：读 HTML 里的 ID → 拿它去本地保存的副本里找相同 ID → 对上了就恢复完整块数据；对不上（比如从别处复制来的）就只剩纯文本和 HTML。

这就是"富文本复制"保真度的全部秘密：**自定义 MIME 类型 + HTML 内嵌 ID**，想复刻照抄这套就行。

### 证据与局限（官方口径）

- 剪贴板桥来自 Notion Desktop 7.6.1 的 `app.asar`（tab preload + `main/index.js`）；文中代码是把混淆变量名展开、删掉无关成员后的简化版
- 富格式与 Markdown 解析的例子来自 2026-07-13 缓存的网页资源；测试是"执行抽取出的模块和小 harness"，不是录制的真实桌面操作——官方把证据边界标得很清楚，这点值得学

### 官方还顺手记录的两条旁支

- **Markdown 表格解析**：表格经解析器变成表头行 + 数据行（table → table\_row → cells）
- **离线 SQLite 路径**：渲染进程经 IPC 请求 `getSqliteMeta`，主进程建消息通道，一头给渲染进程、一头给 SQLite 工具进程——只跟最初的 IPC 请求会漏掉后面的"悄悄话"

## 日常维护

```
rea update                          # 更新 CLI
npx rea-agents@latest setup         # 刷新助手端的注册配置
```

更新后重启 AI 助手。

## 注意事项

1. **只分析你有权利分析的软件**：自己的 App、开源软件、明确允许的测试目标。仓库自带 DISCLAIMER，请遵守当地法律。
2. **结论要看证据**：REA 返回的每条结论都带证据和局限，让 AI 把不确定的地方标出来，别直接当真理。
3. **大二进制文件**分析较慢是正常的；Ghidra/Hopper 首次启动需要一点时间。
4. 遇到问题先去看官网 Guides（[rea.tools），按目标类型有分步指南；Discord](https://link.juejin.cn?target=https%3A%2F%2Frea.tools%25EF%25BC%2589%25EF%25BC%258C%25E6%258C%2589%25E7%259B%25AE%25E6%25A0%2587%25E7%25B1%25BB%25E5%259E%258B%25E6%259C%2589%25E5%2588%2586%25E6%25AD%25A5%25E6%258C%2587%25E5%258D%2597%25EF%25BC%259BDiscord "https://rea.tools%EF%BC%89%EF%BC%8C%E6%8C%89%E7%9B%AE%E6%A0%87%E7%B1%BB%E5%9E%8B%E6%9C%89%E5%88%86%E6%AD%A5%E6%8C%87%E5%8D%97%EF%BC%9BDiscord") 社区很活跃。

## 相关链接

- 仓库：[github.com/morluto/rea](https://link.juejin.cn?target=https%3A%2F%2Fgithub.com%2Fmorluto%2Frea "https://github.com/morluto/rea")
- 官网与教程：[rea.tools](https://link.juejin.cn?target=https%3A%2F%2Frea.tools "https://rea.tools")
- 一键接入：`npx rea-agents setup`
