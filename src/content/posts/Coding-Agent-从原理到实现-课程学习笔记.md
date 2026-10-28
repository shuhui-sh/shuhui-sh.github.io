---
title: "Coding Agent：从原理到实现 —— 课程学习笔记"
date: 2026-10-19
description: "课程简介里有一句话，是整门课的题眼： 两节课加一篇论文，构成了一个非常清晰的递进结构： 这个'原型 → 工程 → 架构'的三级跳，是本课程最有价值的地方：它既能让你亲手写出一个能跑的 Agent，又能"
tags: ['AI', 'Agent']
category: "技术"
---
> **课程名称**：Coding Agent：从原理到实现
> **课程来源**：网易易·Learning GO（salon.netease.com，课程 ID 3009288）
> **原始课程**：Stanford CS146S《The Modern Software Developer》Lecture 9/22 与 9/24
> **讲师**：Mihail Eric（Stanford；Monaco AI 负责人；Alexa 早期 LLM 建设者）
> **整理说明**：本文综合了 **两节课的课件（15+17 页，含中文翻译）、两段课程视频的完整转写（44:30 英文原声 + 28:28 中文配音）、第二课官方英文逐字稿、随课代码，以及指定阅读论文全文（53 页）**。文中标注"讲师原话"处均为依据英文原文的**意译**；不确定处标 ⚠；我补充的内容标注"延伸建议，非课程原文"。材料的覆盖范围与局限见 **0.3**，原始材料见文末附录。整理于 2026-10-19。

---

## 目录

- [0. 先看全貌：这门课到底在讲什么](#0-先看全貌这门课到底在讲什么)
  - 0.1 课程背景 · 0.2 平台课程结构 · 0.3 材料覆盖与可信度 · 0.4 阅读路线
- [1. 第一课：200 行代码搭出 Claude Code](#1-第一课200-行代码搭出-claude-code)
  - 1.0 行业判断 · 1.1 心智模型 · 1.2 代码拆解 · 1.3 原型 vs 生产 · 1.4 Takeaway · **1.5 视频实录（44 分钟全程）** · 1.6 视频与代码差异 · 1.7 动手准备
- [2. 第二课：现代 Coding Agent 的解剖](#2-第二课现代-coding-agent-的解剖)
  - 2.0 课前事务与时间线 · 2.1 Harness（基准表与结构图）· 2.2–2.9 八大组件 · 2.10 原则 · 2.11 金句 · **2.12 抓包实录** · 2.13 课堂问答 · 2.14 作业 1 · 2.15 方法小结
- [3. 第三课：Claude Code 的设计空间（论文精读）](#3-第三课claude-code-的设计空间阅读材料)
  - 3.1 五价值观 · 3.2 十三原则 · 3.3 七组件五层 · **3.4 回合执行 · 3.5 权限系统 · 3.6 扩展机制 · 3.7 上下文与记忆 · 3.8 子代理 · 3.9 持久化** · 3.10 横向对比 · 3.11 相关工作 · 3.12 讨论与实证 · 3.13 元问题 · 3.14 开放方向 · 3.15 方法论与源码结构
- [4. 把三份材料串成一个认知模型](#4-把三份材料串成一个认知模型)（含**课程 vs 论文交叉验证**）
- [5. 实践清单：设计自己的 Agent 时该问的问题](#5-实践清单设计自己的-agent-时该问的问题)
- [6. 动手练习](#6-动手练习延伸建议非课程原文)（7 个递进练习）
- [7. 术语表](#7-术语表)
- [8. 自测题](#8-自测题)（22 题）
- [附录：资料索引](#附录资料索引)（归档文件 · 外部链接 · 延伸阅读 · 已知局限）

---

## 0. 先看全貌：这门课到底在讲什么

课程简介里有一句话，是整门课的题眼：

> **Coding Agent 并不是一个单纯"更会写代码"的大模型，而是一套由 LLM、Context、Tools、System Prompt 与 Agent Loop 共同构成的智能执行系统。**

两节课加一篇论文，构成了一个非常清晰的递进结构：

| 层次 | 材料 | 回答的问题 | 抽象级别 |
|------|------|-----------|---------|
| **看得见** | 课程1：200 行代码搭建 Claude Code | Agent 的最小可用形态是什么？ | 原型 / 实现 |
| **看明白** | 课程2：现代 Coding Agent 的解剖 | 生产级 Agent 比原型多了什么？ | Harness / 工程 |
| **看得透** | 阅读材料：《Dive into Claude Code》 | 这些设计取舍背后的理由是什么？ | 架构 / 设计空间 |

这个"原型 → 工程 → 架构"的三级跳，是本课程最有价值的地方：**它既能让你亲手写出一个能跑的 Agent，又能让你理解工业级产品的每一个设计决策从何而来。**

### 0.1 课程背景：这门课是谁在教、怎么教

课程的原始出处是 **Stanford CS146S《The Modern Software Developer》**（2026 年秋季学期）。下面信息来自课程 1 课件第 8–10 页（*Course Logistics*）、课程 2 课件第 2 页和两节课的开场：

| 项目 | 内容 |
|------|------|
| **讲师** | **Mihail Eric**：斯坦福本科/研究生；**Monaco**（旧金山的销售领域初创公司）的 AI 负责人；为数十家公司（从种子期初创到上市企业）担任 AI 顾问；**在 Amazon Alexa 团队构建了最早期的 LLM**；创办并出售过一家机器学习教育初创公司；**创办过一家获 Y Combinator 支持的 AI 编码公司** |
| **助教（CA）** | Isaac Kan、Vijay Daita |
| **上课时间** | 周二 / 周四 17:30–18:20 |
| **课程网站** | https://themodernsoftware.dev（所有课件、作业、阅读材料公开，"**任何人都可以跟着学**"） |
| **交付物** | **6 次作业**（每周 1 次，重点练习课堂内容；仓库 `mihail911/modern-software-dev-assignments`）、**3–4 次对 OSS 仓库的贡献**、**1 个开放式期末项目**（实践课程中的 AI 编码原则） |
| **成绩构成** | **项目 50% / 作业 15% / OSS 30% / 参与度 5%** |
| **OSS 合作伙伴** | **15 个顶级 AI 原生开源项目**：Vercel、Warp、Marimo、Milvus、Pi、CrewAI、Browserbase、HeyGen、CopilotKit、Semgrep、OpenHands、Cmux、Arize、Sloth、Anyscale |
| **嘉宾讲座** | 当今顶尖 AI 开发团队的**创始人与工程高管**（**Claude Code、Devin、Replit、Factory 等产品的创造者**）；"已融资数十亿美元，估值达数百亿美元，**不要错过这些分享**" |
| **课程定位** | **"这门课讲的是原则，不是工具"**；**"用 AI 编码覆盖软件开发生命周期的每个环节"**；讲师称这是**同类课程中的首个** |

> 💡 **一个值得注意的设计**：**30% 的成绩来自开源贡献**，**期末项目允许"1 个人类 + 一群 agent"**——这门课本身就是它所教内容的**实践**：用 agent 做真实的、被外部检验的工程。

### 0.2 在网易 Learning GO 上的课程结构

网易内部学习平台把这门课组织成 **8 个章节**（页面标注"预计学习时长 25min，共 8 章节"，技术-人工智能，公司级，中文，目标人群"技术开发人员"）：

| # | 章节 | 类型 | 建议时长 | 对应的原始材料 |
|---|------|------|---------|---------------|
| 1 | 【课程1】课件：200 行代码搭建 Claude Code | 文档 | 5 min | `Lecture_9_22_26_中英对照_不遮挡版.pdf`（15 页） |
| 2 | 【课程1】相关代码 | 外部资源 | 5 min | Google Drive 文件；另附 `coding_agent_from_scratch.py` |
| 3 | 【视频材料】构建编程智能体 | 视频 | 25 min | `第一课-中英文.mp4`（实际 **44 分 30 秒**，英文原声） |
| 4 | 【课程2】课件：前沿编码智能体的设计方式 | 文档 | 5 min | `Lecture_9_24_26_中英对照_不遮挡版.pdf`（17 页） |
| 5 | 【课程2】视频 | 视频 | 20 min | `CS146S-9月24日-中文视频课程.mp4`（实际 **28 分 28 秒**，**中文配音精编版**） |
| 6 | 【课程2】逐字稿 | 外部资源 | 5 min | themodernsoftware.dev 的英文逐字稿（约 57 分钟课堂全文） |
| 7 | 【课程2】相关 prompt | 外部资源 | 5 min | Google Drive 文件夹 |
| 8 | 【阅读材料】深入探索 Claude Code | 文档 | 5 min | 论文 `2604.14228v2.pdf`（53 页） |

> ⚠ **"建议学习时长"明显偏短**：平台标注总共约 25 分钟，但**仅两段视频就有 73 分钟**，再加上 53 页论文——**认真学完至少需要 4–6 小时**。这也是本文存在的理由之一。

### 0.3 本文的材料覆盖与可信度标注

为避免"听起来很全，其实有缺口"，这里把每份材料**怎么拿到的、读了多少、有什么局限**说清楚：

| 材料 | 获取方式 | 覆盖 | 局限 |
|------|---------|------|------|
| **课程 1 课件**（15 页） | 下载 PDF；**英文取文本层，中文翻译渲染成图片后逐页阅读** | **全部 15 页** | 中文翻译字体缺 CMap，无法直接提取文本，是**看图转录** |
| **课程 1 视频**（44:30） | 抓取视频流 → 抽音轨 → **Whisper large-v3 转写**（1,008 个片段，英文，置信度 0.99） | **全部** | **机器转写**，个别专有名词有误，已按上下文校正 |
| **课程 1 代码**（193 行） | 下载原文件 | **全部** | 与视频现场代码有差异（见 1.6） |
| **课程 2 课件**（17 页） | 同课程 1 | **全部 17 页**（含基准表放大核对） | 同上 |
| **课程 2 视频**（28:28，中文配音） | **Whisper large-v3 中文转写**（700 个片段，中文，置信度 1.00） | **全部** | **机器转写错误较多**（如把 Claude 识为 "Cloud"、harness 识为 "Hornets"、dumb zone 识为 "Demosong"）；**内容与英文逐字稿一致，是其精编版（略去了课堂事务部分）**，故本文以**英文逐字稿**为准 |
| **课程 2 逐字稿**（约 57 分钟） | 官方英文文本 | **全部** | 含若干 `[Unclear passage]`，已在 2.13 标 ⚠ |
| **论文《Dive into Claude Code》**（53 页） | 下载 PDF，pdftotext 提取 | **正文第 1–14 节、全部附录、参考文献均已通读** | 部分图表（Figure 1–9）只能从文字描述和图内文字还原；**参考文献只在正文引用处核对，未逐篇阅读被引文献** |
| **Google Drive 两项** | ✅ **已获取**（经本机代理下载） | **全部**：课程 1 代码与随课文件 **MD5 完全相同**（无额外内容）；课程 2 的 **6 份提示词原文**（系统提示词、工具清单、plan mode、子代理、压缩、CLAUDE.md）已全文阅读 | 无 |

**文中的标记约定**：

- **"（意译）"/ 引用框**：讲师原话为英文，**本文是中文意译**，不是逐字翻译；
- **⚠**：不确定、听不清、或有口径差异的地方；
- **"（延伸建议，非课程原文）"**：这是**我补充的**内容，不是课程或论文里的；
- **（论文 §n）/（§n）**：指向论文章节，便于回查原文；
- **Tier A/B/C**：论文自带的证据等级（见 3.15.1）。

### 0.4 怎么读这篇文章（三条路线）

| 你的时间 | 推荐路线 |
|---------|---------|
| **30 分钟**（只想懂本质） | 0 章 → 1.1、1.3 → 2.1.2 的结构图 → 2.10、2.11 → 4 章三条主线 |
| **半天**（想能动手） | 上面 + 1.2、1.5（视频实录）→ 2.2–2.9 → 6 章动手练习 1–3 → 5 章清单 |
| **1–2 天**（想读透论文） | 全文；重点读 3.4–3.9（回合、权限、扩展、上下文、子代理、持久化）与 3.12（讨论）；配合 6 章练习 4–7 |

---

## 1. 第一课：200 行代码搭出 Claude Code

> 课件标题：《How to Build Claude Code in 200 Lines of Code》
> 配套代码：`coding_agent_from_scratch.py`（实测 193 行）

### 1.0 开场：2026 年的行业判断

在进入技术细节前，课件开篇（*State of the World: 2026* / *What That Means For You*）给出了几个判断：

- 全行业 AI 采用率持续扩大，**成为 "AI-native" 已经是新的目标**；
- **但门槛更高了（the floor is higher）**：开发者从未如此高产，因此**期望值也随之水涨船高**；
- 竞争焦点转向**整体系统级思维、架构与抽象**；
- 当这些能力与 **AI-first 开发实践**结合时，你将变得不可替代。

课件第二页 *State of the World: 2026* 用了**四张新闻截图**来渲染这个背景（课件原图）：

| 截图 | 内容 |
|------|------|
| *AI · Anthropic* | **"Anthropic、OpenAI 的顶尖工程师说：AI 现在写了他们 100% 的代码——对软件开发岗位的未来影响重大"**（2026-01-29 报道） |
| *Business Insider*（独家） | **"Meta 在推动员工使用 AI，这份文档显示了力度有多大"** |
| OpenAI 新闻 | **"OpenAI 与 Hugging Face 合作应对模型评估期间的安全事件"**（更新于 2026-08-26） |
| *Business Insider* 文化版 | 一篇关于 Z 世代迷上 hacky sack 的文章——**与主题无关，推测是讲师的玩笑**（第二课开场他又提到 hacky sack，问“Is that anything?”，笑点没接住） |

> 这几页的作用是**定调**：不是论证"AI 会不会改变开发"，而是默认它**已经发生**，然后问"**那你该怎么办**"——答案就是下面的 *What That Means For You*。

还有一句贯穿整门课的话：

> **This class is about principles, not tools.**（这门课讲的是原则，不是工具。）

这解释了两节课的取材逻辑：不教某个产品的按钮怎么点，而是拆解**所有 Coding Agent 共通的运行机制**。

### 1.1 心智模型：Agent Loop 就是全部

第一课要建立的核心认知只有一个：**所谓 Coding Agent，剥到最里面，就是一个"问模型 → 执行工具 → 把结果喂回模型"的循环。**

课件把整个过程拆成三步（Steps）：

1. **在终端读取输入，并持续追加到对话历史中**
   （Read in terminal and keep appending to conversation）
2. **告诉 LLM 它有哪些工具可用**
   （Tell LLM what tools are available）
   - LLM 会在合适的时机请求使用工具
   - 你在本地（offline）执行工具，并把结果返回给 LLM
3. **工具集**：`read_file`、`list_files`、`edit_file`

注意这三个工具的选取——它们恰好构成了读写文件系统的最小完备集：

- `read_file` —— 看代码
- `list_files` —— 看目录结构
- `edit_file` —— 改代码

> 🖼 **课件示意图 *"It's that simple"***：画面从左到右是**用户（头像）⇄ harness（一个绿框，里面叠着几个 coding agent 产品的图标，看上去是 Claude Code、Cursor、Windsurf 一类）⇄ LLM**；harness 上方还有一个**"工具"（锤子扳手）图标，与 harness 双向相连**。意思很直白：**我们日常用的那些 coding agent 产品，本质上都是"夹在用户和 LLM 之间、同时能调度工具的那一层"**。第二课的 *Recap* 页重画了同一张图，作为深入 harness 之前的回顾。

**没有搜索、没有 shell、没有 git。** 但就是这个三件套，已经足以让模型完成"理解需求 → 查看项目 → 修改代码"的完整闭环。

> 📌 **命名小差异**：课件里写作 `Read_file` / `List_dir` / `Edit_file`，而随课代码实现为 `read_file` / `list_files` / `edit_file`。能力一一对应，文章以代码中的实际命名为准。

### 1.2 代码拆解

#### ① 系统提示词：把工具"说"给模型听

```python
SYSTEM_PROMPT = """
You are a helpful coding assistant whose goal is to help complete coding tasks. 
You have access to a series of tools you can execute. Here are the tools you have access to:

{tool_list_str}

When you want to use a tool reply with exactly one line in the format: 'tool: TOOL_NAME({{JSON_ARGS}})' and nothing else.
Use compact single-line JSON with double quotes. After receiving a tool_result(...) message, continue the task.
If no tool is needed, respond normally.
"""
```

这里有两个关键设计：

1. **工具列表是"填空"进去的**（`{tool_list_str}`）——工具的增删会自动反映到提示词里，不需要手改提示词；
2. **工具调用走的是"文本协议"**，而不是 function calling API——要求模型输出一行严格的 `tool: NAME({JSON})`。

第 2 点非常值得琢磨。为什么不用 OpenAI 原生的 function calling？

- **可移植性**：文本协议不依赖任何厂商的 API 特性，换个模型（甚至换个厂商）照跑不误；
- **可调试性**：模型输出的就是纯文本，你能一眼看出它想干什么，不需要解析复杂的结构化字段；
- **教学价值**：把"工具调用"这个被 API 封装起来的魔法重新拆解成原始形态，你会真正理解它在协议层是怎么回事。

> 这也是为什么很多生产级 Agent（包括 Claude Code 早期版本）都保留了文本协议的痕迹——它简单、透明、易于干预。

#### ② 工具实现：函数 + docstring 即文档

```python
def read_file_tool(filename: str) -> Dict[str, Any]:
    """
    Gets the full content of a file provided by the user.
    :param filename: The name of the file to read.
    :return: The full content of the file.
    """
    full_path = resolve_abs_path(filename)
    with open(str(full_path), "r") as f:
        content = f.read()
    return {"file_path": str(full_path), "content": content}
```

三个工具都是普通 Python 函数，返回可 JSON 序列化的字典。注意 `resolve_abs_path()`——统一处理相对路径和 `~` 展开，这是让模型可以"随便写法"的基础保障。

#### ③ 工具描述：从 docstring 自动生成

这是这份代码里最"聪明"的一处：

```python
def get_tool_str_representation(tool_name: str) -> str:
    tool = TOOL_REGISTRY[tool_name]
    return f"""
    Name: {tool_name}
    Description: {tool.__doc__}
    Signature: {inspect.signature(tool)}
    """

def create_full_system_prompt() -> str:
    tool_str_repr = ""
    for tool_name in TOOL_REGISTRY:
        tool_str_repr += "TOOL\n===" + get_tool_str_representation(tool_name)
        tool_str_repr += f"\n{"="*15}\n"
    return SYSTEM_PROMPT.format(tool_list_str=tool_str_repr)
```

> ⚠️ **运行环境提示**：`f"\n{"="*15}\n"` 这行用了 PEP 701 语法——**Python 3.12+ 才允许 f-string 内部复用同种引号**。在 3.11 及更早版本上会直接报 `SyntaxError`。

用 `inspect.signature()` 抓函数签名、用 `tool.__doc__` 抓文档字符串，自动拼装出工具说明。

**这一点在第二课里被讲师反复强调**，请记住它：

> 当你为一个 Coding Agent 写工具函数时，docstring 的清晰度和参数类型的明确性**极其重要**——因为工具的名字、描述、完整签名**全都会进入模型的上下文**，模型就是靠这些信息来判断"什么时候该用哪个工具"。

换句话说：**写工具文档 = 写提示词。**

#### ④ 工具调用解析：容错的文本解析器

```python
def extract_tool_invocations(text: str) -> List[Tuple[str, Dict[str, Any]]]:
    """Return list of (tool_name, args) requested in 'tool: name({...})' lines."""
    invocations: List[Tuple[str, Dict[str, Any]]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("tool:"):
            continue
        try:
            after = line[len("tool:"):].strip()
            name, rest = after.split("(", 1)
            name = name.strip()
            args, _ = json.JSONDecoder().raw_decode(rest)
            invocations.append((name, args))
        except Exception:
            # Ignore malformed tool requests
            continue
    return invocations
```

两个细节值得注意：

- 用 `json.JSONDecoder().raw_decode()` 而非 `json.loads()`——前者只解析出第一个合法 JSON 对象就返回，**容忍后面跟着的多余文本**；
- 解析失败时**静默跳过**（`except: continue`），而不是崩溃。

这是与"不完美模型"共处的必要姿态：模型不会永远输出完美格式，harness 必须足够健壮。

#### ⑤ 主循环：双层 while 就是 Agent Loop

```python
def run_coding_agent_loop():
    conversation = [{
        "role": "developer",
        "content": create_full_system_prompt()
    }] 
    while True:                                    # 外层：等待用户输入
        try:
            user_msg = input(f"{YOU_COLOR}You{RESET_COLOR}: ")
        except (EOFError, KeyboardInterrupt):
            break
        conversation.append({"role": "user", "content": user_msg.strip()})
        
        while True:                                # 内层：Agent Loop
            assistant_resp = execute_llm_call(conversation)
            tool_invocations = extract_tool_invocations(assistant_resp)
            
            if not tool_invocations:               # 没有工具调用 → 本轮结束
                print(f"{ASSISTANT_COLOR}Assistant{RESET_COLOR}: {assistant_resp}")
                conversation.append({"role": "assistant", "content": assistant_resp})
                break
            
            conversation.append({"role": "assistant", "content": assistant_resp})
            for name, args in tool_invocations:
                tool = TOOL_REGISTRY[name]
                # 分发到具体工具…
                conversation.append({
                    "role": "user",
                    "content": f"tool_result({json.dumps(resp)})"
                })
```

**双层循环的分工：**

- **外层 while**：交互循环，等待用户输入，往对话历史里追加用户消息；
- **内层 while**：**这才是真正的 Agent Loop**——反复调用模型、执行工具、把 `tool_result(...)` 作为一条 user 消息追加回对话，直到模型不再请求工具（只输出文本）为止。

**"终止条件"是这份实现里最优雅的地方**：不需要任何显式的"任务完成"信号，**模型不再请求工具 = 任务结束**。这个"模型输出纯文本即停止"的判据，在论文中被称为**首要停止条件（primary stop condition）**——生产级系统用的也是同一个。

模型调用部分：

```python
def execute_llm_call(conversation: List[Dict[str, str]]) -> str:
    response = openai_client.responses.create(
        model="gpt-5.6-terra",
        input=conversation,
        max_output_tokens=5000,
    )
    return response.output_text
```

**注意这里没有任何"记忆管理""上下文压缩""权限检查"**——`conversation` 列表无脑增长，直到撞上上下文上限。

### 1.3 从这 193 行里能学到什么

把它和真实产品对比，差距一目了然：

| 能力 | 200 行原型 | 生产级 Agent |
|------|-----------|-------------|
| 工具数量 | 3 个 | ~40–54 个 + MCP 扩展 |
| 上下文管理 | 无（无限增长） | 五层压缩管线 |
| 权限/安全 | 无 | 七层防御 |
| 状态持久化 | 无（进程结束即丢失） | append-only JSONL 会话记录 |
| 扩展机制 | 无 | Skills / Hooks / Plugins / MCP |
| 任务委派 | 无 | Subagents |
| 系统提示词 | ~10 行 | ~50–80 行（曾达 200–250 行） |

**核心结论：Agent 的"智能"来自模型，而 Agent 的"可用性"来自 harness。** 200 行能跑通 loop，但要真正用于生产，99% 的工作量在 loop 之外——这正是第二课的主题。

### 1.4 课件收尾：三组核心观点（The Takeaway）

课件在技术内容之外，给出了三组面向开发者个人的判断：

**① Human-agent engineering（人机工程）**

- 聚焦那些**尚未被 AI 系统替代**的技能
- **业务与产品理解**
- 成为**技术架构师**——培养对软件系统的"好品味"（good taste）
- **沟通至关重要**（Communication is crucial）

**② LLMs are only as good as you are（LLM 的上限取决于你）**

- **好的上下文带来好的代码**（Good context leads to good code）
- **如果你自己看不懂代码库，LLM 也看不懂**
- **防止 AI slop**（阻止 AI 生成的低质垃圾代码）

**③ Experiment aggressively（激进地实验）**

> 这一页其实是整门课的价值观底座：**工具会变，原则和判断力不会。**

### 1.5 视频实录：从零手写 Agent 的完整过程（《构建编程智能体》，44 分 30 秒）

> **材料说明**：课程 1 的视频是讲师 Mihail 的**英文原声屏幕录制**（⚠ 视频里讲师口述课程是“周一”，而课件文件名与第二课逐字稿都是周二 9/22——应是口误或课表调整，不影响内容）（平台标注"中英文"，实际语言检测为英语，置信度 0.99）。本节依据我用 Whisper large-v3 对视频音轨做的**完整转写**整理（1,008 个片段，转写稿已归档于 `课程原始资料/`）。引用的时间戳为视频内时间。转写为机器识别，个别专有名词有误（如 *week two*、*Nirvana* 等口语），已按上下文校正。

#### 1.5.1 视频的起点与目标

开场（00:00–01:40）：这是为 CS146S 周一那节课录的**屏幕录制**——"周一整堂课，我们讲了如何用约 200 行代码实现一个先进 coding agent（Claude Code、Cursor、Warp 那样）的**核心**"；目的是"**走一遍同样的练习，证明大约 200 行代码就有了驱动大多数这些编码平台的核心**"。课程资料全部公开在 themodernsoftware.dev，"任何人都可以跟着学"。

**起点是一份约 60–70 行的脚手架**（01:47–03:00），讲师逐项说明里面已有什么：

| 已有部分 | 说明 |
|---------|------|
| **API 客户端** | 初始化到某个底层模型提供商——"可以是 OpenAI、Claude，随便什么，这里用 OpenAI" |
| **系统提示词** | **留空**，稍后填 |
| **ANSI 颜色字符串** | 给终端输出上色，区分用户与助手 |
| **`resolve_abs_path` 小工具** | 文件名 → 绝对路径，"稍后让 agent 打开文件时有用" |
| **工具注册表** `TOOL_REGISTRY` | **工具名 → 实现函数的映射** |
| **两个辅助函数** | `get_tool_str_representation`（拿任一工具的实现，返回字符串化表示，喂给系统提示词）、`extract_tool_invocations`（从 LLM 输出里解析工具调用） |
| **`execute_llm_call` 与 `run_coding_agent_loop`** | 先是桩 |

讲师预告：**到视频结束，我们会实现大约 100–150 行代码**，并强调"核心依赖三个工具：**读文件、列文件、改文件**"。

#### 1.5.2 讲师先画的心智模型（03:02–05:06）

在敲代码前，讲师用一段话讲透了**所有 coding agent 的本质**，值得原样记住（意译）：

> *"任何一个 coding agent，它真正做的事其实很简单：**它是一个聊天**——我和一个 LLM 在互动。我向 LLM 提一个请求，比如让它创建一个新文件，它会返回给我的响应里**可能包含我应该使用或发起的工具列表**。比如我说'给我建个新文件'，LLM 可能发出一个 `edit_file` 工具调用，带上它想编辑什么的参数。**作为工具的接收方，我会收到它**（这里是我们要实现的 JSON，但你想怎么格式化都行）。然后**由我来执行这个工具调用**——我，用户，在执行这个工具调用。或者说，在很多情况下，是 **IDE 或 Claude Code 在执行**。然后我们**把工具调用的结果返回给 LLM**，把它追加到一个**运行中的上下文**里，LLM 拿到后用这个上下文跟进。"*

关键三点：**① LLM 自己不执行工具**——"在本地、offline 执行，**不是由 LLM 执行**"；**② 并非每次对话都涉及工具**——"因为不是每次我们对 LLM 说话，都要和工具交互"，所以要有"**走普通对话**"与"**发起工具调用**"两条分支；③ 循环可以"无限继续"。

#### 1.5.3 实现顺序：先写循环，再填工具（共八个里程碑）

讲师选择了一条**很有教学价值的顺序**——**先写 agent 主循环（工具都是桩），再逐个把工具接进去**，这样每一步都能运行、都能看到变化：

| 里程碑 | 视频时间 | 做了什么 | 为什么这样做 / 讲师的点评 |
|--------|---------|---------|------------------------|
| ① 写主循环骨架 | 06:42–13:49 | 先**打印完整系统提示词**（调试用，"我们会在构建其余组件时迭代地看到这个提示词在变"）；初始化 `conversation`（首条为 system）；外层 `while True` 取用户输入，用 ANSI 转义字符给 `You` 上色，**捕获 `KeyboardInterrupt` 和 `EOFError`**（"这样可以 Ctrl+C / Ctrl+D 跳出"）；内层再套一层 `while True` 做 agent 循环 | "这是标准的消息格式——**这条消息的角色是什么？内容是什么？**"（用过 GPT、Claude、Ollama API 的都熟悉） |
| ② 两种分支 + 工具桩 | 09:42–13:49 | **无工具调用**：打印助手响应、追加进历史、`break` 回到用户输入；**有工具调用**：迭代 `(tool_name, args)` 元组，对 `read_file` / `list_files` / `edit_file` 先**只打印"called"** | "若 LLM 回复且没有工具要调，就**回到循环最顶部**" |
| ③ **工具结果以 `user` 角色回灌** | 13:49–15:00 | 每次工具执行后，把结果以 `tool_result({json})` 的格式、**角色为 user** 追加进对话 | **"这次是因为是我们在发起工具，而不是 LLM"**——对话里谁产生内容，谁就是那个角色 |
| ④ `execute_llm_call` | 15:01–16:20 | 调用 `openai_client.chat.completions.create`，`model="GPT-5"`，`messages=conversation`，`max_completion_tokens=2000`（"为了激进一点，**这大概远超所需**，但求稳"）；返回 `response.choices[0].message.content` | "大部分与 LLM 对话的重活都由 OpenAI 客户端完成" |
| ⑤ **第一次运行：只是聊天机器人** | 16:49–17:13 | 对它说 *Hello there*，它正常回话 | **"没有工具调用的循环，字面上就是一个对话循环……还不是 coding agent，它只是个聊天机器人。"** |
| ⑥ 系统提示词 + 工具表示 | 17:24–23:55 | 填系统提示词（**几句话就够**）：角色（`You are a helpful coding assistant. Its goal is to help complete coding tasks.`）、有工具可用并列出、**严格输出格式**（`tool: TOOL_NAME(JSON_ARGS)` **单行**、紧凑单行 JSON、双引号）、收到 `tool_result` 后继续任务、无需工具则正常回复；再实现 `get_tool_str_representation`（**名字 + docstring 描述 + `inspect.signature` 签名**）和把所有工具拼成一个字符串（`TOOL\n===` … 分隔线） | "**格式是任意的**，但要**足够明确，让 LLM 能解析出一个工具做什么，并与其他工具的语义区分开**" |
| ⑦ 解析工具调用 | 24:00–27:47 | 逐行 `strip()`，不以 `tool:` 开头就 `continue`；去掉 `tool:` 前缀；按 `(` 切出名字和剩余部分；**如果剩余部分不以 `)` 结尾就当作格式错误跳过**；把括号内的内容当 JSON 加载；`try/except` 兜底 | 讲师坦承"**有点脆弱的字符串解析**"，"你当然可以更防御性、更小心"；"**不是最好的写法，但为了教学，我们想看看发生什么**" |
| ⑧ 逐个实现三个工具并接线 | 28:15–41:33 | **`read_file`** → 运行验证 → **`list_files`** → 运行验证 → **`edit_file`**（最复杂）→ 运行验证 | 见 1.5.4 / 1.5.5 |

> 💡 **这个顺序本身就是一条经验**：**先打通"对话 → 解析 → 分发 → 回灌"的全链路，工具只是往里填的插件。** 实际工程里增加第 4 个、第 5 个工具，就是同样的"填空"动作。

#### 1.5.4 讲师在编码中反复强调的六条教学点

1. **docstring 就是给 LLM 的说明书**（28:25–29:15）——全视频最重要的一句话：

   > *"为 LLM 定义工具时，要**明确、要具体**说明它们做什么。**别指望'我定义了函数，LLM 就知道该干什么'。不——它是用 docstring 来推理这个工具在做什么、该不该用它、在什么时点用它。**"*
   
   因此即使是看似极简单的 `read_file`，也要写明：功能（"获取用户提供的文件的完整内容"）、参数（`filename`——要读取的文件名）、返回（"文件的完整内容"）。讲师甚至自嘲"烦人，也许显而易见，但**我们必须明确**"，并指出"**加上这些冒号，对后续解析非常有帮助**"。
2. **类型标注同样重要**（21:45）：*"重要的是，**输入和输出都要有类型定义**"*——因为 `inspect.signature` 会把它们一并交给 LLM；
3. **返回值要写成"能告诉 LLM 发生了什么"的字典**（38:23）：`edit_file` 返回 `{"path": ..., "action": "created_file" / "edited" / "old_str not found"}`——*"这只是为了在响应里明确，**让 LLM 知道发生了什么**。"*；
4. **返回值之所以像 JSON，是因为它们会被加进 LLM 的上下文**（34:49–35:18）：*"因为我们在工具结果里提供的就是这个，**这就是为什么这些写得非常明确，几乎像 JSON 表示**。"*；
5. **`edit_file` 的一个"约定"**（37:25–37:45）：**`old_str` 为空字符串 = 创建/覆盖文件**——"**这只是我们采用的一个约定**"。这个小设计让一个工具同时覆盖了"创建"与"修改"两种操作；
6. **失败路径的取舍**（39:36–40:12）：`old_str` 找不到时（`find` 返回 -1），**只是告诉 LLM `old_str not found`**，不做兜底。讲师点出了工业产品的做法——

   > *"我们本可以做得更复杂：发现 `old_str` 找不到时，**重新提示用户**说明想替换什么，或做某种**隐式假设**。**这正是这些 AI IDE 和 AI 编码平台所做的：依据工具结果，它们会内置自己的兜底行为。**但就我们的目的，保持非常简单。"*

   这句话恰好是**第一课与第二课的衔接点**：第二课讲的"harness"，在很大程度上就是这些**围绕工具结果的兜底与增强行为**。

#### 1.5.5 三次现场演示（逐步验证每个工具）

| 演示 | 用户输入 | 观察到的行为 | 验证点 |
|------|---------|-------------|--------|
| **A. 读文件**（30:56–33:21） | `What's in testfile.py`（该目录下的一个文件） | 先**打印系统提示词**（讲师借机展示：`edit_file`、`list_files` 只有名字和签名，而 **`read_file` 多出一段 description，来自 docstring**——"**这就是让 LLM 能推理、知道何时使用 `read_file` 的原因**"）；助手发出**紧凑单行 JSON** 的 `read_file` 调用 → 解析出文件名 → 解析为绝对路径 → 打印内容 | 内容确为"一个极简单的两行 `main`，打印 *this works*" |
| **B. 列目录**（33:30–36:12） | 问某个周目录里有什么 | 助手发出 `list_files`，返回该目录的文件列表 | 讲师提示"**还可以更进一步：让它用 `read_file` 打开那个文件——那就是与 LLM 的两步交互**" |
| **C. 创建 + 编辑**（41:35–43:15） | ① `make me a new file called hello.py and implement hello world in it`<br>② `Edit hello.py and add a function to it for multiplying two arbitrary numbers` | ① 助手调用 `edit_file`：`path=hello.py`、`old_str=""`、`new_str=print hello world`，"Done"；<br>② 助手**自动先 `read_file` 读出现有内容**，再 `edit_file`：`old_str` 是原来的 `print hello world`，`new_str` 是**带新增乘法函数的版本**，随后汇报"我们刚刚加了一个乘法函数" | **多步自主行为涌现**：用户只说了一句话，agent 自己决定**先读、再改**——这正是 Agent Loop 内层 `while` 的价值 |

> 讲师在 ① 里说了句"**This is not what we would expect.**"（"这不是我们预期的"）——这说明现场第一次创建文件时输出与预期略有出入，随即进入第二个编辑演示；转写稿未显示出错细节，因此本文不做猜测。

#### 1.5.6 视频结尾的金句（43:15–44:30）

> *"**这就是 coding agent 循环的核心。** 到这里，我们可以继续创建新文件、继续编辑现有文件，**仅此而已**。**这就是 Claude Code 在做的事，也是 Cursor 之类在做的事。** 我是说，它们都有复杂度，但**都是'填充物'——都是围绕它的'花里胡哨'**，只是为了让 UI 更流畅而加在上面的。但看看我们刚做的：**这是 207、208 行代码，我们有了一个功能完整的 coding agent，光靠对话就能写代码。绝对疯狂。**"*

这与课件的 *"It's that simple"* 一页（用户 ↔ harness ↔ LLM，harness 再 ↔ 工具）完全呼应。

---

### 1.6 视频现场代码 vs 课程发布的 `coding_agent_from_scratch.py`：差异对照

两份代码**目标一致，但细节不同**——对照读一遍，能看到"教学演示版"与"整理发布版"的区别：

| 项目 | 视频现场 | 课程发布的 `coding_agent_from_scratch.py` |
|------|---------|------------------------------------------|
| 总行数 | **约 207–208 行**（讲师现场口述） | **193 行**（实测） |
| OpenAI 接口 | `client.chat.completions.create(...)` | **`client.responses.create(...)`**（Responses API） |
| 模型名 | `GPT-5` | `gpt-5.6-terra` |
| 输出长度参数 | `max_completion_tokens=2000` | `max_output_tokens=5000` |
| 取返回文本 | `response.choices[0].message.content` | `response.output_text` |
| 系统消息角色 | `system`（讲师说"role is system"） | **`developer`** |
| 助手消息的角色 | 现场口误说过一次"system"，实为 assistant | `assistant` |
| 工具调用解析 | 检查剩余串**以 `)` 结尾**，截取后 `json.loads` | **`json.JSONDecoder().raw_decode(rest)`**——允许括号后还有多余内容，更宽容 |
| 工具分发 | `if name == "read_file": ... elif ...` 逐个写；讲师提到"未知工具可抛错或提示用户重试"，但**现场没写** | 同样的 `if/elif`，但**参数用 `.get(key, 默认值)`** 取，缺参时更稳；**未知工具名会在 `TOOL_REGISTRY[name]` 处直接 `KeyError`**（教学版未做防御） |
| `read_file` 调试输出 | 打印完整路径 | 同样 `print(full_path)` |
| 返回结构 | 每个工具返回字典 | 一致 |

> 💡 **一个有意思的细节**：`raw_decode` 的"宽容解析"是对视频里"有点脆弱的字符串解析"的改进，**这正是教学版 → 发布版的演进轨迹**——先让它跑通，再让它更健壮。

### 1.7 动手前的准备清单（延伸建议，非课程原文）

想复现这份 Agent，需要注意：

1. **Python 版本**：发布代码里 `f"\n{"="*15}\n"` 使用 **PEP 701 语法，需 Python 3.12+**；
2. **依赖**：`pip install openai python-dotenv`；在同目录 `.env` 里放 `OPENAI_API_KEY=...`（代码用 `load_dotenv()` 读取）；
3. **模型名**：`gpt-5.6-terra` 是课程发布时的名字，**请替换成你账号上实际可用的模型**；视频里明确说"**可以是 OpenAI、Claude，随便什么**"，换厂商只需改 `execute_llm_call` 一个函数；
4. **安全提醒**：`edit_file` 的 `old_str=""` 会**直接覆盖文件**，且**没有任何权限检查**——在真实项目目录里试之前，**先建一个临时目录**，这也正是第二课与论文花大篇幅讲"权限系统"的原因。

---

## 2. 第二课：现代 Coding Agent 的解剖

> 课件标题：《The Anatomy of a Modern Coding Agent》
> 讲师原话："周二是个 proof of concept——看看 200 行能做到什么。今天我要把大家带到现代 coding agent 和它的 harness 面前，解剖一个 state-of-the-art coding agent 的内部结构。"

讲师特别说明了一件事：**除了"智能层"（模型本身）看不到，其他所有东西我们都能看到。** 模型是私有的、两万亿参数级别、分布在全球服务器上；但包裹在它外面的 harness，是可以完整观测的。

> 讲师用的是一个**代理工具（proxy）拦截 Claude Code 的请求与响应**，把每次交互导出成 JSON trace 来逐层拆解。他打了个比方：*这就像用 Wireshark 抓网络包，或者浏览器 DevTools 的调试面板。* 顺带回应了一个问题：**这些信息不是靠泄露源码才知道的**——抓包就能看到，而且 Codex 的 harness 本来就开源于 GitHub。

### 2.0 课前事务与背景：从"课程运营"里读到的信息

第二课开场十分钟（逐字稿 00:59–07:58）讲的是课程运营事务，但里面有几条对**理解这门课的语境**很有用：

| 事项 | 内容 |
|------|------|
| **期末项目** | 规格已发布。整个学期**大约四个里程碑**（含一次提案和若干中间节点），目的是**避免最后一周大家集中"疯狂 vibe coding"** |
| **团队规模** | 允许**一名人类搭档 + 任意数量的 coding agent**（讲师原话："a swarm of them, in fact. That's all fair game."）；**也可以一个人做**——"很多人选择如此，我觉得这是可以接受的，甚至在今天可能是合适的，**考虑到 coding agent 有多强大**" |
| **额度（credits）** | 课程拿到了多家 coding agent 厂商的额度：**Claude Code、Factory、xAI、Devin**（Windsurf 与 Devin 同属 Cognition）。讲师说"这样你们在 vibe coding、botmaxing、**token maxing** 时，不用烧自己的信用卡"。下周发放，可能收集邮箱，部分厂商有二维码 |
| **OSS 合作伙伴** | 下周详细说明；部分合作方会**来现场做 5–10 分钟分享**，并可能做线上/线下 office hours |
| **等候名单 / 申请** | 申请门槛"不算特别高，但是成功学完这门课的最低要求"；**申请截止日是 9 月 27 日**（周日）；非斯坦福本科但有同等课程基础的可申请例外 |
| **课件** | 周二的课件已上传课程网站，周四的"会尽量上课前放上去"；已注册学生可通过 Ed 访问 |
| **作业 1** | **当天发布，周日截止**——内容就是"**复现讲师现场演示的抓包拆解**"（见 2.14） |

> 💬 一个小插曲：讲师吐槽现场把两张桌子拼在一起的怪异布置、以及"hacky sack 到底算不算梗"——第一课课件里恰好有一张 *hacky sack* 的新闻截图，推测是同一个梗。这类现场互动在文章其余部分略去。

#### 2.0.1 课堂上提到的"行业演进时间线"（按讲座日 2026-09-24 推算；讲师多为口头的大致说法，**日期是估算**）

讲师在不同位置随口提到了一批**时间点**，把它们排在一起，能看出 harness 这两年的演化方向：

| 时间 | 事件 | 出处 |
|------|------|------|
| **2024 年末** | **MCP 发布**；早期的 MCP 服务器（如 GitHub 的）开箱就有约 **110 个工具** | 2.2 节 |
| **讲座前约 9 个月或更早**（≈ 2025 年底前） | **多数 coding agent harness 引入了 plan mode** | 2.5 节 |
| **2025 年 12 月** | **Claude Code 之所以变得很火，靠的是"极简 harness"**——很长一段时间里工具集克制，却几乎无所不能 | 2.2 节 |
| **讲座前约 6 个月**（≈ 2026 年 3 月前后） | Claude Code 的整套系统**被泄露**；讲师强调他的抓包方法**与泄露无关** | 2.3 节 |
| **讲座前一两个月以前** | Claude Code 的系统提示词还有 **200–250 行** | 2.3 节 |
| **约一个月前** | 系统提示词又**削减了约 8%** | 2.3 节 |
| **几周前** | Anthropic **也开始支持 `AGENTS.md`**（此前只认 `CLAUDE.md`） | 2.4 节 |
| **讲座前约两天**（≈ 2026-09-22） | **Opus 5.5 发布**；**同一天** OpenAI 也发布了新模型——"这就是这两家公司的动态：他们把发布时间卡在同一天" | 2.1 节 |

> 另据论文引用，**Linux Foundation 在 2025 年成立 Agentic AI Foundation（AAIF）**，**MCP、goose 和 `AGENTS.md` 是它最初锚定的项目**——这从侧面印证了讲师说的"大家都收敛到 `AGENTS.md`"。

### 2.1 什么是 Harness

课件给出的定义很直接：

> **Harness design is one of the most important problems in coding agents.**
> （Harness 设计是 Coding Agent 中最重要的问题之一。）

课件列出的一组标准组件：

- **System prompt**（系统提示词）
- **Custom configuration files**（自定义配置文件，如 `AGENTS.md`）
- **Tool list**（工具列表）
- **Plan mode**（计划模式）
- **Subagents**（子代理）
- **Skills**（技能）
- **Hooks**（钩子）
- **Compaction**（上下文压缩）

下面逐个拆解之前，先看课件开头的几页铺垫。

课件的第 4–7 页用三张图完成了"从原型进入现代 harness"的过渡，下面逐一说明。

#### 2.1.1 "进入最先进的编码智能体"：基准表

课件第 5 页（*Enter a state-of-the-art coding agent*）贴了 Anthropic 发布 **Opus 5.5** 时的**基准对比表**（讲师："根据 Anthropic 放出的基准，它是 state of the art"）。我放大逐格核对后的数字如下（**加粗为各行最高**）：

| 类别 / 基准 | **Opus 5.5** | Fable 5.1 | Opus 5 | GPT-6 Astra | GPT-5.6 Sol |
|------------|:-----------:|:---------:|:------:|:-----------:|:-----------:|
| Agentic coding · **Terminal-Bench 4.0** | **66.4%** | 55.8% | 52.3% | 57.9% | 37.3% |
| Agentic coding · **FrontierCode v1.1 (Main)** | **54.4%** | 50.3% | 48.0% | 53.3% | 47.5% |
| Agentic coding · **CursorBench 4.0** | **57.8%** | 51.8% | 46.6% | — | 41.7% |
| Knowledge work · **GDPval-AA v2.1** | **1846** | 1735 | 1708 | 1542 | 1588 |
| Business workflows · **AutomationBench** | 40.0% | 31.4% | 26.9% | **41.4%** | 28.8% |
| Multidisciplinary reasoning · **Humanity's Last Exam**（带工具） | **67.7%** | 65.6% | 63.6% | 57.2% | — |

**怎么读这张表**：① 三个"agentic coding"基准上 Opus 5.5 全面领先，**这也是课程选它的 harness 做解剖对象的原因**；② 唯一没赢的是 **AutomationBench（业务流程）——GPT-6 Astra 的 41.4% 略高于 Opus 5.5 的 40.0%**；③ 表中有两个"—"（缺失），说明这些模型并非每个基准都有数据；④ 这张表**只是引子**——讲师紧接着说的是"**这些数字背后真正重要的是 harness**"。

> ⚠ **别过度解读**：这是**厂商自己发布的基准**，课程把它当作"这就是当下最先进"的背景，**不是课程的论证内容**。

#### 2.1.2 "现代 harness 更复杂"：两张图

**第 6 页**列出前面那八个组件；**第 7 页是一张结构图**，我把它的内容还原如下——这是整门课最值得记住的**一张图**：

```
  ┌─ Context inputs（上下文输入，紫色）──┐        ┌──── Agent loop ────┐        ┌─ Harness mechanisms（harness 机制，绿色）┐
  │ System prompt  身份、规则、环境      │ ─────► │  Context window     │ ◄───── │ Compaction   缩减历史                    │
  │ AGENTS.md      项目记忆文件          │ ─────► │  （所有在场的 token）│        │                                          │
  │ Tool list      Bash、Edit、Grep…     │ ─────► │        │            │        │                                          │
  │ Skills         按需加载              │ ─────► │        ▼            │        │                                          │
  └──────────────────────────────────────┘        │  Model              │ ◄───── │ Plan mode    只读工具                    │
                                                  │  （选择下一个动作） │        │                                          │
                                                  │        │            │        │                                          │
                                                  │        ▼            │        │                                          │
                                                  │  Tool execution     │ ◄────► │ Subagents    隔离的上下文                │
                                                  │  （harness 执行调用）│        │                                          │
                                                  │        │            │        └──────────────────────────────────────────┘
                                                  │        └──回到 Context window
                                                  └─────────────────────┘
```

**这张图把八个组件分成了两类，非常有启发性**：

| 类别 | 成员 | 作用 | 对应课件的话 |
|------|------|------|-------------|
| **上下文输入（Context inputs）** | System prompt、AGENTS.md、Tool list、Skills | **往上下文窗口里"灌"什么** | 决定模型**看到什么** |
| **Harness 机制（Harness mechanisms）** | Compaction、Plan mode、Subagents | **作用在循环上的控制机制**：压缩（缩减窗口）、计划模式（限制模型只用只读工具）、子代理（隔离上下文的旁路执行） | 决定循环**怎么运转** |
| *Hooks* | （图里没画，但在组件列表里） | 在生命周期各点插入代码 | 属于"机制"一类 |

> 这与论文的"**assemble / model / execute 三注入点**"（3.6.1）是**同一个思想的两种画法**：左列对应 `assemble()`（看到什么）和 `model()`（工具表）；右列的机制对应 `execute()` 和上下文管理。

讲师同时强调，**中间的 Agent loop 仍然是第一课那个循环**——"循环还在，但围绕它有一堆花哨的东西，我们称之为 harness"。**核心循环里有三样：上下文窗口（本学期会花很多时间讲）、模型（智能层）、工具执行**。

下面逐个拆解八个组件。

### 2.2 组件一：Tool List（工具列表）

**工具是模型"接触真实世界"的唯一通道**——它的静态权重之外，一切对外部世界的操作都要通过工具。

Claude 内置约 **40 个工具**，覆盖：

- **文件访问**类
- **Bash / Shell 命令**类
- **定时/监控**类（含专门的 cron 工具）
- **Web 搜索**类
- **LSP 搜索**（Language Server Protocol，用于理解当前语言的语义）
- **Agent 专用工具**（如启动子代理）
- **规划与隔离**工具
- **Artifact 创建**、**MCP 资源列举**工具
- **用户交互**工具：提问、推送通知、发送反馈
- **Skill 调用**工具

#### 关键洞察 1：工具定义全量进入上下文

> **一个工具的全部定义——description、注释、名字、完整签名——都会变成 prompt 的一部分，被注入上下文。**

这正是第一课里 `create_full_system_prompt()` 做的事情的工业级版本。所以：

- **写工具的 docstring = 写提示词**，必须清晰、一致；
- **参数类型要明确**，因为这是模型判断"何时用、怎么用"的依据；
- 这对**设计 MCP server 和任何 Agent 工具都成立**。

#### 关键洞察 2：MCP 工具也是全量注入

> **你加载的每一个 MCP server、每一个第三方工具，都会出现在这个 block 里，伴随每一次请求发送出去。**

讲师在这里讲了一段很重要的行业史：

- **MCP 出现得早，Skills 出现得晚。** Skills 引入的动机之一就是**渐进式披露（progressive disclosure）**——先只把一小段元数据放进上下文，等真正相关时再把完整内容拉进来。而 MCP 工具是**全量常驻**的。
- **早期 MCP server 极其臃肿**：GitHub 的 MCP server 开箱就有 **110 个工具**（list issues、create issue、comment…），"有用，但它们吃掉了大量上下文"。
- **Claude Code 的成功很大程度上归功于"极简 harness"**：**用更少、但更强大的工具**。典型代表是 **Bash 和 SQL**——本质上它们各自都是一门完整的语言，一个 Bash 工具能表达的操作用专用工具要几十个。

> **行业趋势是从复杂度走向简化**：从"3–5 个能做很多事的工具"起步，再逐步扩展，而不是一开始就堆砌。

> ⚠️ **上下文膨胀的代价**：引入越多无关内容，Agent 表现越差。已有研究在找"性能开始下降的 token 临界点"——这就是为什么必须警惕 MCP 工具的数量。讲师预告了后续课程要讲的 **"dumb zone"（变笨区）**概念。

#### 顺带一提：一个有意思的问答

有学生问：**为什么 Claude 启动 agent 时用自然语言，而不用向量？**

讲师回答：**训练语料主要是自然语言文本，代码和指令也是以文本片段表示的**——无论是网页语料还是人类标注数据都是如此。而且**人类很难用向量这种非人类可读的格式去沟通和标注**。另外，抓包看到的是**最人类可读的形式**，实际喂给模型前几乎肯定还有一层处理（压缩、裁剪、转换），但那部分属于"秘方"，看不到。

### 2.3 组件二：System Prompt（系统提示词）

**定义**：系统提示词是 LLM 行为的**蓝图（blueprint）**，由 harness 静态设定、自动注入，**用户无法直接控制**，且**每一次请求都会带上**。

它定义了：

- **Harness 的行为**（这是一个什么系统、怎么交互）
- **护栏（Guardrails）**，包括安全相关指令
- **环境信息**（当前是什么系统、在哪、有哪些模型可用）

#### 抓包实测的发现

在 trace 里能看到两个 block：

1. 第一句：`You are Claude Code, Anthropic's official CLI for Claude.` —— harness 用自然语言告诉模型"你是什么"；
2. 第二块是实质指令，即 **Opus 5.5 的系统提示词，约 50–80 行**（讲师原话："about 80 lines—or closer to 50"）。

内容包括：你是帮助用户完成软件工程任务的交互式 agent、安全注意事项、harness 是什么、session 相关信息、环境信息（可用模型）、上下文管理说明……

**其中一个新增的大块是 memory（记忆）**：

- 这是 Anthropic 较新加入的**隐式记忆机制**，从你的使用行为中学习；
- 记忆存储在**项目级路径**下；
- 提示词里详细规定了**写入格式**，以及如何与这些记忆交互。

> 💬 **一个值得记录的问答**：有学生问，记忆检索该用 RAG 还是 GraphRAG？讲师回答：**这些系统增加的复杂度，并不总是比让系统直接解析纯文本（flat text）更有优势**——效果很大程度上取决于任务，不能一概而论。他还补充：自己所在公司（销售领域，非 coding）自建的 harness 和 agent，最终也用了 **flat files** 来做记忆。

#### 关键洞察：系统提示词正在变短

> 直到一两个月前，系统提示词还有 **200–250 行**，而现在是 **约 50 行**。**大约一个月前，他们又削减了约 8%。**

被砍掉的内容包括"如何使用 Git""如何提交任务"这类显式指令。

**讲师给出的解释**：这些知识**很可能已经被训练过程吸收进模型参数**了。这和"减少 MCP 工具"是同一个逻辑——**减少一切不必要的上下文膨胀**。

> 讲师的感叹很真实：*"这些字我一个都没写，但我每发一次请求，它就在我的上下文窗口里。我甚至看不见它，但它就在那。我第一次提问时，可能已经有好几万 token 被不受我控制的材料消耗掉了。然后我还纳闷为什么它表现不如预期——我想他们是想减少这种意外。"*

**注意：系统提示词不是"越长越安全"。** 有人问能不能通过 prompt injection 覆盖系统提示词，讲师的观点是：这是已知问题，Anthropic 有专门团队处理；而且**抓包本来就不难，源码也泄露过**——所以"harness 的可见性"并不是想象中的重大攻击面。

### 2.4 组件三：Agent 配置文件（CLAUDE.md / AGENTS.md）

**定义**：这是**用户可控**的那一半——系统提示词的"用户侧对应物"。系统提示词是静态的、由 harness 设定、后台注入；配置文件同样会被注入，**但由我们掌控**。

- `CLAUDE.md` —— Claude 专属
- `AGENTS.md` —— 更通用的标准

**关于这两者的现状**：本来大家已经统一到 `AGENTS.md`，只有 Anthropic 想搞自己的一套；**但几周前他们也开始加入了**，你甚至可以把 `CLAUDE.md` 软链接（symlink）到 `AGENTS.md`。讲师评价：*"它们功能上完全一样，只是名字不同。在 Codex 和 Anthropic 之间切换时很烦人——一个非常弱的围墙花园。"*

#### 抓包实测：它长什么样

在 trace 里，CLAUDE.md 的内容出现在**第一条用户消息的上方**（技术上也属于这个 user block，但**不是用户手打进去的，是 harness 后台加的**）：

```
These instructions override default behavior and must be followed exactly as written.
```

后面跟着 CLAUDE.md 的路径和完整内容。讲师 demo 的 to-do 应用里，CLAUDE.md 描述的是**项目结构的高层概况**。

> 讲师补充：这份 CLAUDE.md 是他和 Claude **一起写的**（"We collaborated"）。

#### 关键洞察：CLAUDE.md 的"度"

> 共识是：包含一些**运行代码的指令**是好的（比如测试怎么跑、server 怎么启动），**但不要太多**。

**为什么？**

> **如果你放太多内容，就会过度约束系统（overconstrain）**——你以为多给信息是在帮忙，实际上可能把系统**过拟合到你的指令上**（overfitting it to your instructions）。

**实践建议**：

- ✅ 写 1–2 条精确命令：跑单测的确切命令、启动 server 的确切命令
- ❌ 不要塞进大段代码块
- ❌ 不要写成事无巨细的说明书

这与"系统提示词变短"是同一个趋势的两个侧面。

### 2.5 组件四：Plan Mode（计划模式）

**定位**：用于**设计方案、撰写规格说明、处理较难任务**的模式。

**历史**：约 9 个月前，主流 coding agent harness 几乎都引入了 plan mode。

**机制**：

- 它是一个**文本块（prompt block）**，由 harness 在你进入该模式时注入；
- Claude 中有一个工具用于**进入** plan mode，另一个工具用于**退出**；
- 提示词中定义了完整的工作流：

| 阶段 | 内容 |
|------|------|
| **Phase 1 理解需求** | 理解用户需求，其中甚至包括**启动 agent 去探索代码库** |
| **Phase 2 设计** | 设计方案 |
| **Phase 3 评审** | 审查方案 |
| **最终** | 产出最终计划，然后退出 plan mode |

**重要产物：plan 文件**——整个规划过程结束后生成的 artifact。

讲师 demo：他想给 to-do 应用加"定时任务/周期性提醒"（比如"每周给植物浇水"），于是进入 plan mode，来回几轮后生成了计划。

> 讲师强调：**这个思路可以推广到几乎所有现代 coding harness，包括 Codex。**

### 2.6 组件五：Skills（技能）

**定义**：Skill 描述的是**一段书面的操作流程（written procedure）**，可以包含多个工具调用、脚本，以及串联它们的提示词，从而完成更复杂的任务。

**调用方式**：

- **主动触发**：模型根据上下文判断应该用（比如它发现任务完成，主动调用 code review skill）
- **显式调用**：用户直接要求

**结构**：定义一个 `SKILL.md` 文件，描述"要做什么"以及"好的代码质量和差的代码质量分别长什么样"。讲师为这门课写了一个叫 **"check code quality"** 的 skill。

#### 抓包实测的优雅之处

当用户说 "check my code quality. Use the skill."：

1. harness 注入一个 **command message** 文本块，告知模型"该检查代码质量了"；
2. harness 随后**定位 skill 文件并把内容插入上下文**。

**这就是渐进式披露（progressive disclosure）的落地**：平时上下文里只有 skill 的少量元数据，真正需要时才把完整内容拉进来。这正是它与 MCP 工具（全量常驻）的关键区别。

> 讲师预告：后面会有**整整一节课**讲 skill 的最优设计。

### 2.7 组件六：Subagents（子代理）

**机制**：

- 一个**主控/orchestrator agent**（Claude Code 的主控制循环）
- 通过**显式工具调用**启动**自己的、全新上下文窗口**的 worker
- worker 完成后，**结果返回给主 agent**

**核心价值：上下文管理**

> 每个 subagent **以全新的上下文启动**，而不是继承父级的全部上下文。它的探索过程发生在主控制流之外，完成后只把结果带回来。

这也解释了为什么它能并行（**代价是 token 消耗上升**）。

**抓包实测**：trace 里能看到 subagent 的工具调用——"启动了一个 agent，它做完自己的事，返回了结果"。

### 2.8 组件七：Hooks（钩子）

**定义**：在 **harness 生命周期的不同节点**插入的提示词或代码片段。

**典型用途**：需要做**前置/后置处理**（pre/post-processing）的场景。

> 讲师点到为止："最佳实践我们后面再讨论。"

（补充：在阅读材料中，这一机制的规模被量化了——**横跨 27 种事件类型的 hook 管线**，其中 5 种与安全相关，其余 22 种服务于生命周期与编排。）

### 2.9 组件八：Compaction（上下文压缩）

**定义**：当上下文快超出限制时，**生成 agent 运行过程关键点的整合摘要**，然后**用摘要替换已有的历史**。

**触发方式**：

- **自动**：即将超限时（比如接近一百万 token 的窗口上限）
- **手动**：用户主动调用

> **警告：压缩是有损的（lossy）**——所以你可能想自己适配一套策略。讲师预告后续会讲"何时该主动触发压缩"的最佳实践。

（补充：阅读材料显示，实际实现是**五层压缩管线**，远不止"一次摘要替换"。）

### 2.10 有效 Harness 的原则

课件在最后给出了三条原则：

#### 原则一：Simplicity（简单至上）

> **更少、更强大的工具是被偏好的**——`sql`、`bash` 这类"瑞士军刀"式工具优于几十个专用工具。

#### 原则二：Mind the context window（警惕上下文窗口）

> **避开"变笨区"（dumb zone）——小心工具膨胀（tool bloat）。**

讲师在收尾时补充：**这是一个大问题——该投资模型还是投资 harness？** 行业一直在两者之间摇摆：有时说价值和护城河在 harness，有时又指着训练 LLM 砸进去的几十亿美元说钱该投模型。

> **当下的落点**：让 harness **尽可能简单、精炼**，但依然能做出有意思的事——**关键是别把上下文撑爆。**

#### 原则三：Prompt 内容和长度会演进

> **让提示词易于适配（make it easy to adapt them）。**

讲师原话：*"提示词长度时长时短。现在的倾向是更短的提示词，因为我们要避免上下文膨胀、要对上下文窗口保持敏感。而且短提示词也更容易按任务适配。"*

### 2.11 本课金句

> **"Harness design is probably one of the hardest and most important problems in coding agents."**
>
> （Harness 设计，很可能是 Coding Agent——乃至更广泛的 agent——中最难也最重要的问题。）

而且：**这些原则不限于 coding 领域**。销售、法律、客服……很多原理是通用的。讲师特别提到：**即使是非 coding 领域的 agent，现在也越来越多地被设计在 coding 能力之上**。

### 2.12 抓包实录：一次 Claude Code 请求到底长什么样

> 这一节把讲师在 18:33–47:05 的现场演示**按结构重新整理**，因为它是第二课信息量最大的部分，也是**作业 1 的直接预演**。

#### 2.12.1 演示环境

- **抓包工具**：一个**拦截 Claude Code 请求与响应的代理**（课程会给大家用）。讲师的类比：**Wireshark 抓网络包**，或 **Chrome 开发者调试控制台**——都是"在协议层看发生了什么"；"这工具好用在**能把信息展开**"；
- **被测项目**：一个**命令行 to-do 工具**——能加任务、列任务、标完成、加子任务；讲师自己说"**基本上是 vibe coding 出来的，然后我选择继续扩展**"；
- **会话**：凌晨 4 点和 Claude Code 的一次对话，**一堆提示 → 抓下请求 → 记录进文件**。讲师现场分析这些文件。

#### 2.12.2 trace 文件的整体结构

整份 trace 是**一个 JSON 文件**，"结构对我们解析很友好，因为它清楚地区分了正在发生的事"。**一次请求的顶层结构（由上到下）**：

| 区块 | 内容 | 要点 |
|------|------|------|
| **`model`** | 使用的模型名 | 如 Opus 5.5 |
| **`messages`** | **消息列表**——"**就是我们两天前追加的那个对话列表**" | 每条有 **`role`**（user / assistant）和内容 |
| **`system`** | **系统提示词**，分**两个块** | 见 2.3 节 |
| **`tools`** | **工具列表**，每项是一个字典 | 含 `name`、`description`、**输入 schema**（"你可以把它当作这个工具的函数签名"） |

**`messages` 里的三类来源**（22:42 前后）：

1. **`user` 角色**——"通常是我发出的东西，**但也可能包含工具调用的响应**"（呼应第一课：tool_result 以 user 角色回灌）；
2. **harness 在后台注入的"系统级消息"**——"Claude Code 在幕后注入的东西"；
3. **`assistant` 角色**——"Claude 在做的事，比如发出工具调用"。

> **关键观察**：讲师说"**有些消息被丰富了——以帮助 Claude 完成工作，尽管我们通常看不到这些信息。这就是我们拦截这些请求的原因：看看引擎盖下面。**"

**讲师"进入对话"的位置**是第一条用户消息：*"What are the core components of this to-do app?"*（想重新熟悉自己 vibe coding 出来的仓库）。**但这条消息上方还有很多不是他输入的内容**——他没敲过 *system reminder* 或别的那些东西，**是 harness 在后台加的**，其中就包括 **CLAUDE.md 的全文**（见 2.4 节）。

#### 2.12.3 `tools` 区块的细节

- 例如 **`Agent` 工具**：描述是"启动一个新 agent 来处理复杂的多步任务"并解释该 agent 的能力；还有一个 **schema**（可当函数签名），"**当工具被调用时，你会看到为其中某些属性填入的值**"；
- "它相当精细。**重要的是：所有这些都会被注入 LLM 的上下文窗口。**"；
- 还有 **artifact 工具**等；"有些定义相当精细，取决于底层工具的复杂度"；
- 讲师把 tools 区块拆成两组：**原生工具（~40）**与**额外工具（MCP 工具等）**。**原生工具的类别**（课堂口述）：
  - **文件访问**；**通过 Bash 与 shell 交互**；**类似 cron 的监控**；**搜索网页**；**LSP 搜索**（Language Server Protocol，检视所用语言）；
  - **Agent 专用工具**、**规划与隔离**工具、**调度工具（含专门的 cron 工具）**；
  - **创建 artifact**、**列 MCP 资源**（"与 MCP 工具不同"）；
  - **与用户交互**：**调用技能、提问、推送通知、发送反馈**。
- **MCP 工具的识别方式**：名字以 **`mcp__`** 开头（例如 `mcp__claude_ai…` 的 Claude Docs 工具）——"**`mcp__` 前缀告诉你这是外部工具**"。讲师还提到自己装了 Mintlify（文档托管）的 MCP；"你也可以有 Notion、Slack 等的工具，**全都会注入工具列表**"。

#### 2.12.4 "我们看到的，就是送进 LLM 的吗？"

有学生追问：**这是不是实际喂给 LLM 的形式**？讲师的回答很谨慎（28:36–30:00）：

- "这是**原始形式**，但被摄入时**几乎肯定还有某种处理来折叠或压缩它**"；
- "这是我们能解析出来的**最人类可读的形式**，**不一定是喂给 LLM 的形式**"——"**几乎肯定还有别的事在发生，有些内容被剥离或转换**"；
- "要更进一步，你**可能得在 LLM 所在的服务器上**，看它被 token 化输入之前的那一刻——**我不认为我们能看到，有些可能是他们的秘方**。"

**这是一条重要的认识论边界**：**抓包能看到"请求内容"，看不到"模型最终看到的 token"。**与论文 3.15.2 的"逆向工程认识论"互相印证。

#### 2.12.5 讲师抓包时没细讲、但值得记下的几个细节

- **元数据里有校验和、哈希、UID**（30:54）："我不会逐个讲每段元数据……**没有这类东西会造成安全漏洞**。"
- **系统提示词里的记忆块**：路径是**项目级**（路径里能看到代码所在位置）；每当 LLM 判断应写入记忆时，**提示词指定了一种格式**；"如果打开那个位置，会看到 Claude 提取的记忆的**元数据块**"；
- **`system reminder` 等块是 harness 注入的**，用户不可见；
- **plan mode 的提示词、skill 的 command message、subagent 的工具调用**都能在 trace 里找到——讲师选择把后三者**分享 trace 文件**让学生自己看（因为作业 1 会让他们自己抓）。

#### 2.12.6 课程公开的六份真实提示词（Google Drive 原文）

> 平台上的"【课程2】相关 prompt"是一个 Google Drive 文件夹。**我已完整获取**，里面是**六份从现场演示中提取的 prompt / 配置文件原文**，归档于 `课程原始资料/课程2提示词原文/`。
>
> 这是第二课最好的"课后答案"——**课上讲的每个组件，都能在这里看到真身**。

**① `system_prompt.md`（6.3 KB）——真实的系统提示词**

结构逐块如下：

| 块 | 内容要点 |
|----|---------|
| **首句** | `You are an interactive agent that helps users with software engineering tasks.` |
| **安全策略块** | 可协助**授权范围内的**安全测试、防御性安全、CTF、教育场景；**拒绝**破坏性技术、DoS、大规模定向攻击、供应链攻击、恶意目的的规避检测；**双用途安全工具需要明确的授权上下文**（渗透测试、CTF、安全研究、防御用途） |
| **`# Harness`** | 输出以 GitHub 风格 Markdown 在终端渲染；工具在**用户选择的权限模式**下运行，**"被拒绝的调用意味着用户拒绝了它——应调整，而不是原样重试"**；系统可能通过对话中途的系统消息发来更新/提醒/规则修改，**hooks 可能拦截工具调用，hook 的输出应当作用户反馈**；`<pasted_content>` 标签的处理规则；**优先用专用文件/搜索工具而不是 shell**；独立工具调用可并行；引用代码用 `file_path:line_number` |
| **写作风格** | **"写出来的代码要读起来像周围的代码：匹配它的注释密度、命名与惯用法。"** |
| **代词规则** | 未说明时用 **they/them**；"名字不能告诉你一个人的代词" |
| **不可逆 / 对外动作** | **先确认**，除非已获持久授权；**一个上下文里的批准不延伸到下一个**；发送到外部服务即"发布"；**删除/覆盖前先看目标**；**如实报告结果**（测试失败就说失败并给输出；跳过的步骤要说明） |
| **`# Session-specific guidance`** | 需要用户自己执行命令时，建议其用 `! <command>` 前缀；用户输入 `/skill-name` 时通过 Skill 调用，**不要猜技能名** |
| **`# Memory`** | **持久化的文件式记忆**：给出具体路径；每个记忆一个文件，带 frontmatter（`name` / `description` / `metadata.type`）；**四种类型** `user` / `feedback` / `project` / `reference`；用 `[[name]]` 互相链接；写完后在 `MEMORY.md` 加一行指针；**保存前先查重**；**不保存仓库已记录的内容**（代码结构、历史修复、git 历史、CLAUDE.md） |
| **`# Environment`** | 最新模型（**Fable 5.1 / Opus 5.5 / Sonnet 5 / Haiku 4.5**，含 model ID）；Claude Code 的形态（CLI、桌面应用、Web、IDE 扩展）；fast mode 用的是 Opus 且**不会降级到更小的模型** |
| **`# Context management`** | 对话变长时会被摘要，摘要+剩余上下文进入下一个窗口；**"有足够信息就行动。不要重新推导已确立的事实，不要重提用户已做的决定……如果要权衡，给建议，而不是穷举选项。"** |

> 📏 **对照课程**：讲师说系统提示词"约 80 行，或更接近 50 行"——这份文件正好 **55 行**，**结构与课上描述完全吻合**；也印证了"人设 + 安全护栏 + 环境信息 + 记忆 + 上下文管理"这几大块。

**② `tool_list.md`（2.9 KB）——真实工具清单**

按 **10 个类别**列出 **36 个工具**：

| 类别 | 工具 |
|------|------|
| **Files** | Read、Edit、Write、NotebookEdit |
| **Shell** | Bash、Monitor（流式读取长时间运行的后台脚本） |
| **Search & code intelligence** | WebSearch、WebFetch、**LSP**（查询语言服务器的定义、引用、悬停信息、符号） |
| **Agents** | Agent、ListAgents、SendMessage、TaskStop、Workflow |
| **Planning & isolation** | EnterPlanMode、ExitPlanMode、EnterWorktree、ExitWorktree |
| **Scheduling** | CronCreate、CronDelete、CronList、ScheduleWakeup、RemoteTrigger |
| **Artifacts** | Artifact、ArtifactComments、ArtifactData |
| **MCP resources** | ListMcpResourcesTool、ReadMcpResourceTool、ReadMcpResourceDirTool |
| **Interaction** | AskUserQuestion、**Skill**、PushNotification、SendFeedback、EndConversation |
| **Design & review** | DesignSync、ReportFindings |

> 📊 **三方口径对照**：课程口述"约 **40** 个"、论文源码统计"最多 **54** 个"、这份演示配置清单 **36** 个——**三者不矛盾**，恰好证明了论文说的"工具池是**按构建/模式动态装配**的"（`getAllBaseTools()` 19 个无条件 + 35 个条件）。

**③ `plan_mode.md`（5.5 KB）——真实的 Plan Mode 提示词**

开头是**最高优先级的强约束**：

> *"Plan mode is active. The user indicated that they do not want you to execute yet — you **MUST NOT make any edits**（计划文件除外），run any non-readonly tools … **This supercedes any other instructions you have received.**"*

然后是**五阶段工作流**：

| 阶段 | 要求 |
|------|------|
| **Phase 1 初始理解** | **只使用 Explore 子代理**；**最多并行 3 个**，但**用最小必要数量（通常 1 个）**；用于已知文件/小改动时用 1 个，范围不确定或跨多个区域时才用多个 |
| **Phase 2 设计** | 启动 Plan 子代理（**默认至少 1 个**；只有改错别字、单行改动这类琐碎任务才跳过）；最多并行 3 个，用于需要不同视角的复杂任务 |
| **Phase 3 评审** | 读探索中识别的关键文件，确保方案对齐用户原始请求，**用 AskUserQuestion 澄清剩余问题** |
| **Phase 4 最终计划** | 写入**指定的 plan 文件**（**唯一允许编辑的文件**）；必须包含 **Context 段**（为什么做、问题是什么、预期结果）；**只写推荐方案**；简洁到能快速扫读、详细到能执行；命名要改的关键文件；引用可复用的函数与路径；**包含验证段** |
| **Phase 5 提交** | 调用 **ExitPlanMode** 请求批准 |

> ✅ **课上说法逐字得到证实**：讲师说"Phase 1 理解需求、Phase 2 设计、然后审查、最终计划、退出"，并提到"**其中甚至会启动 agent 来探索代码仓库**"——原文正是 *"Launch up to 3 Explore agents IN PARALLEL"*。

**④ `subagent_prompt.md`（3.2 KB）——真实的子代理任务提示**

这是一份发给"性能分析子代理"的**完全自包含**任务书，包含：

- **边界约束**：不要修改仓库任何文件；**不要碰真实的 `~/.todo_tasks.json`**（用临时路径或把 `HOME` 指向临时目录）；把基准脚本/数据放进指定的 **scratchpad 目录**；
- **背景**：完整的 repo 路径与各文件职责（`todo/models.py`、`todo/storage.py`、`todo/cli.py`、`api/main.py`、`web/src/...`），甚至点名了已知问题（**每个操作都全量 load + save、无缓存、无锁、非原子写入、线性扫描**）；
- **要覆盖的五件事**：① 每个操作的算法复杂度（统计每条 CLI 命令/每个 HTTP 请求的读写次数）；② **实证测量**（100 / 1k / 10k / 50k 任务下的 add、get、complete、list、add_subtask，含嵌套子任务；CLI 启动耗时；JSON 文件增长）；③ **并发与正确性**（CLI / FastAPI / Express 并发写同一文件的丢失更新、非原子写入、async handler 中阻塞 I/O）；④ **无界增长**；⑤ **按优先级排序的建议 + 预估影响**；
- **输出格式**：简洁的 Markdown 报告——**汇总表（严重度/领域/发现）→ 实测数据表（注明机器与 Python 版本）→ 带 `file:line` 的详细发现 → 分优先级建议**，并且**"明确区分实测事实与推断"**。

> ✅ 完美印证："**子代理的提示必须自包含**"（默认不继承父级历史）；以及论文说的 **Explore 类子代理的写/编辑工具在 deny 列表里**——这份提示里的"不要修改任何文件"就是同一约束的**提示词层面表达**。

**⑤ `compaction_prompt.md`（6.4 KB）——真实的压缩提示词**

开头同样是强约束：

> *"**CRITICAL: Respond with TEXT ONLY. Do NOT call any tools.** … Tool calls will be REJECTED and will waste your only turn — you will fail the task."*

输出被要求分成两个块：

- **`<analysis>`**：按时间顺序梳理——用户的明确请求与意图、你的方法、关键技术概念、具体文件与代码片段、**遇到的错误与修复**、**用户的反馈（尤其是"让你换个做法"的反馈）**、**安全相关的指令与约束（必须逐字保留）**；
- **`<summary>`**：固定九个栏目——Primary Request、Key Technical Concepts、Files and Code、Errors and fixes、Problem Solving、**All user messages**、Pending Tasks、Current Work、Optional Next Step。

> 🔍 **这解释了论文里的两个判断**：① 压缩**有损且非确定性**（摘要内容由模型判断取舍）；② 摘要是一次**独立的模型调用**，所以是"阻塞式推理停顿"（Cim et al., 2026）。同时注意它**专门要求保留"用户的纠正"与"安全约束"**——这是在对抗"压缩把重要指令压没了"这个失效模式。

**⑥ `config_files.md`（1.6 KB）——真实的 CLAUDE.md**

就是那个 todo 项目的 `CLAUDE.md`：

- **Project Overview**：Python CLI + 两个 Web 前端（FastAPI、TypeScript/Express）+ JSON 文件持久化；
- **Project Structure**：`todo/`（cli/models/storage）、`api/`、`web/`；
- **Running the Application**：**6 条精确命令**（add / list / done / delete / add-subtask / done-subtask，含参数）；
- **Code Style**：类型标注、dataclass、函数职责单一。

> ✅ 正好印证第二课的建议：**"项目结构 + 精确运行命令 + 少量风格约定"，没有大段代码**。而这段内容在 trace 里就是被 harness 以 *"These instructions OVERRIDE any default behavior…"* 注入的那一块。

**这六份材料共同回答了一个问题**："第二课讲的那些组件，真实长什么样？"——它们不是二手转述，而是**现场演示的直接产物**。

### 2.13 课堂问答汇总

第二课有 **11 个问答**，按出现顺序整理如下。**逐字稿里有几处提问录音听不清（标 ⚠），我只能根据讲师的回答反推问题**，请据此谨慎看待：

| # | 问题（大意） | 讲师回答要点 |
|---|-------------|-------------|
| 1 | 课件在网站上吗？ | 周二的在，**周四的会在上课前放上去**；已注册学生可通过 Ed 访问 |
| 2 | **这是不是同一个请求的全部内容？** | **是**。MCP 先出，**Skills 后出，一个原因就是渐进式披露**；工具全量注入，所以**上下文工程**很重要 |
| 3 | **为什么 Claude 启动 agent 时用自然语言，而不用向量？** | 训练数据（网页语料与人工标注数据）主要是**自然语言文本**；"**人类很难用向量或别的非人类可读格式来沟通**" |
| 4 | 这就是实际喂给 LLM 的形式吗？ | 很可能还有折叠/压缩处理；看不到服务器端 token 化前的形式，"**有些可能是他们的秘方**" |
| 5 | 元数据里的校验和 / UID？ | 在元数据某处；"**没有类似的东西会造成安全漏洞**" |
| 6 | ⚠ **MCP 和 Skills 有什么区别？**（提问听不清，据回应推断；讲师说大家在“抢跑问 skills”） | **MCP 是原语**——"几乎就像一次 API 调用：一个输入输出机制"，是与第三方资源交互的**最小原语**；**Skills 把工具、函数、脚本等封装成多步操作**，"有这种粒度是有帮助的" |
| 7 | ⚠ **能否通过 prompt injection 覆盖系统提示词？**（提问听不清，据回答推断） | "**你绝对做不到**……人们试了很久，我想最简单的尝试他们都处理了。这**不是他们的秘方**，他们有整个团队防这种情况。"并指出：① 抓取请求响应**不难**（有开源工具）；② 他们**大约半年前泄露过整个系统**；③ **Codex 的 harness 本来就在 GitHub 上**——"**harness 的可见性不是你想象的那么严重的攻击面**" |
| 8 | **记忆是每次执行本地的吗？** | 从路径看是**项目级**；"追加到系统提示词"说得太重——**把它们看成被拼接进请求的独立块**，是 prompt 的一部分，但与系统提示词是不同对象 |
| 9 | **记忆检索该用 RAG / GraphRAG 吗？** | "这些设计决定是**基准驱动**的……**复杂度不总是比让系统解析平文本更有优势**，取决于任务，不一概而论"；自己公司的**销售类 agent 也用 flat files 做记忆** |
| 10 | ⚠ CLAUDE.md 该写多长？（开头提问听不清，据回答推断） | "包含一些**运行代码的指令**是好的（测试、起服务器），**但不要太多**……放太多会**过度约束**，**几乎过拟合到你的指令**"；通常只放 1–2 条精确命令；"**下面会有整整一课讲怎么定制 agent**" |
| 11 | 这个块为什么是 `.md` 文件？ | "为了从原始文本变得好看一点，我本可以用 `.txt`。**只是为了演示**"；该块在 trace 里**并不是单独的 Markdown 文件**，是他从 JSON 里**摘出来放进一个空文件**的 |

### 2.14 作业 1 与课程节奏

**作业 1（当天发布，周日截止）**——讲师原话："*它让你做一个类似我刚演示的练习：**拿一个 Claude Code 实例，发出调用，拦截请求与响应，拆开它们看底层发生了什么**。*"并且"**我们会拆解每次向 Claude 发出提示时发生的事**"；**代理工具会提供给所有人**。

> **这就是最好的学习方式**：读了 3.4–3.9（论文）和 2.2–2.9（课程）之后，自己抓一次包，对照每个机制在 trace 里的**真身**——**一次实证比十次阅读更能让这些概念扎根**。

#### 2.14.1 延伸：如果你想自己复现抓包（非课程原文，仅供参考）

课程提供的代理工具我们拿不到，但**思路是通用的**：让 Claude Code 把 API 请求发到一个**你控制的本地代理**，由代理记录请求/响应 JSON。常见做法有两类：

1. **改 API 基址**：给 Claude Code 设置 `ANTHROPIC_BASE_URL` 指向本地转发服务，转发时把请求体落盘；
2. **走 HTTPS 代理做中间人抓包**：用 `mitmproxy` 一类工具，设置 `HTTPS_PROXY`，并让 Node 信任代理的 CA（如 `NODE_EXTRA_CA_CERTS`）。

⚠ **注意**：① 抓到的请求里会带你的 **API key / 会话令牌与项目代码**，**不要把 trace 上传或分享**；② 具体变量与证书配置以你所用版本的官方文档为准，本文不作保证；③ 请只对**自己的账号与环境**操作。

### 2.15 第二课的"元信息"小结：这堂课教了什么方法

回头看，第二课除了**知识点**，还示范了一种**研究 agent 的方法**——它可能比任何单个知识点更有用：

1. **用抓包代替猜测**：想知道 harness 在做什么，**看它发出的请求**，而不是读营销文案；
2. **按"谁产生的内容"拆 trace**：区分 **用户输入 / harness 注入 / 模型输出 / 工具结果**四类来源；
3. **把"每次请求都带着的东西"当成成本**：工具列表、系统提示词、CLAUDE.md、记忆——**这些你看不见，却每次都在占用上下文**（讲师："*perhaps tens of thousands of tokens have already been consumed by material outside my control*"）；
4. **对"我看到的"保持认识论的谦逊**：看到的是请求，不是模型最终的输入。

---

## 3. 第三课：Claude Code 的设计空间（阅读材料）

> **论文**：《Dive into Claude Code: The Design Space of Today's and Future AI Agent Systems》
> **作者**：Jiacheng Liu, Xiaohan Zhao, Xinyi Shang, Zhiqiang Shen（VILA Lab, MBZUAI / UCL）
> **arXiv**：2604.14228v2
> **开源**：https://github.com/VILA-Lab/Dive-into-Claude-Code

这篇论文做了一件非常硬核的事：**通过分析公开可得的 TypeScript 源码**（v2.1.88，约 1,884 个文件、51.2 万行），完整描述了 Claude Code 的架构，并与另外两个开源 agent 系统（OpenClaw、Hermes Agent）做横向对比。

#### 论文的核心结论（摘要的七句话）

1. **核心是一个简单的 while 循环**——调用模型、运行工具、重复；**大部分代码在这个循环周围的系统里**；
2. **权限系统**：**7 种模式 + 一个 ML 分类器**；
3. **上下文管理**：**五层压缩管线**；
4. **四种扩展机制**：MCP、插件、技能、钩子；
5. **子代理委派与编排机制**；
6. **面向追加的会话存储**（append-oriented）；
7. 与 OpenClaw、Hermes 对比：**Claude Code 强调逐动作安全，OpenClaw 强调边界级访问控制，Hermes 把逐动作审批渲染到多个界面**；最后给出**六个开放的设计方向**。

> 全文共 **14 节 + 附录**：§1 引言 · §2 价值观与原则 · §3 架构总览 · §4 回合执行 · §5 授权 · §6 扩展 · §7 上下文与记忆 · §8 子代理 · §9 持久化 · §10 对比 · §11 相关工作 · §12 讨论 · §13 未来方向 · §14 结论。下面 3.1–3.15 **基本按此顺序**展开（§1 引言并入本引言，§14 结论并入 3.13）。

### 3.1 五个价值观（Five Values）

论文的核心方法论是：**先找"人的价值诉求"，再追踪到设计原则，最后落到具体实现。**

| 价值观 | 含义 | 典型体现 |
|--------|------|---------|
| **Human Decision Authority**<br>人的决策权 | 人保有最终决策权，且能**知情地**行使：实时观察、批准/拒绝、中断、事后审计 | 主体现层级（Anthropic → 运营方 → 用户） |
| **Safety, Security, and Privacy**<br>安全 | 即使人**疏忽或犯错**，系统也有义务保护代码、数据、基础设施 | 自动模式威胁模型覆盖 4 类风险 |
| **Reliable Execution**<br>可靠执行 | 做对了人真正想做的事，跨上下文边界/会话恢复/多 agent 委派仍保持连贯 | 三阶段循环：收集上下文 → 行动 → **验证结果** |
| **Capability Amplification**<br>能力放大 | 单位投入产出显著提升 | 约 **27%** 的任务是"没有它就不会被尝试的工作" |
| **Contextual Adaptability**<br>上下文适配 | 贴合用户的项目、工具、约定、技能水平，且关系随时间变好 | 自动批准率从 <50 次会话的 ~20% 上升到 750 次会话的 40%+ |

#### 一个反直觉的数据点

> Anthropic 发现用户**批准了 93% 的权限提示**。

**他们的反应不是"加更多警告"，而是重构问题**：划定明确边界（沙箱、自动模式分类器），**让 agent 在边界内自由工作**——而不是让用户做逐动作审批，因为用户一旦形成习惯就不再认真看了。

这个洞察极其重要：**当人被训练成无脑点"同意"时，审批机制就失效了。** 这是所有做权限设计的人应该记住的教训。

#### 关于"能力放大"的一个佐证

论文引用 Anthropic 内部对 132 名工程师和研究员的研究：**约 27% 的 Claude Code 辅助任务是"本来不会被尝试的工作"**——这说明架构带来的是**质变的新工作流**，而不只是加速原有工作。

同时也提到 Claude Code 被其创造者描述为 **"a Unix utility rather than a traditional product"**——由最小的、**"有用、可理解、可扩展"**的积木搭建而成。

> **架构上的选择**：投资于**确定性基础设施**（上下文管理、工具路由、错误恢复），而非**决策脚手架**（显式 planner 或状态图）。前提假设是：**越来越强的模型，从"丰富的操作环境"中获得的收益，大于从"限制其选择的框架"中获得的收益。**

### 3.2 十三条设计原则

论文把这些价值观操作化为 **13 条设计原则**，每条都在回答一个生产级 agent 必须解决的问题：

| 设计原则 | 回答的设计问题 |
|---------|--------------|
| **Deny-first with human escalation**<br>默认拒绝 + 人工升级 | 未被识别的动作应该被允许、阻止，还是升级给人？ |
| **Graduated trust spectrum**<br>渐变式信任谱 | 固定的权限等级，还是用户可以随时间穿越的谱系？ |
| **Defense in depth with layered mechanisms**<br>纵深防御 | 单一安全边界，还是用不同技术的多重重叠边界？ |
| **Externalized programmable policy**<br>外置可编程策略 | 硬编码策略，还是外置配置 + 生命周期钩子？ |
| **Context as scarce resource with progressive management**<br>上下文是稀缺资源 + 渐进式管理 | 什么是真正的约束？单次截断，还是渐进的管线？ |
| **Append-only durable state**<br>只追加的持久状态 | 可变状态、检查点快照，还是只追加日志？ |
| **Minimal scaffolding, maximal operational harness**<br>最小脚手架 + 最大操作 harness | 投资"脚手架侧推理"，还是让模型自由推理的操作基础设施？ |
| **Values over rules**<br>价值观优于规则 | 刚性决策流程，还是确定性护栏支撑下的情境判断？ |
| **Composable multi-mechanism extensibility**<br>可组合的多机制扩展 | 统一的扩展 API，还是不同上下文成本的分层机制？ |
| **Reversibility-weighted risk assessment**<br>按可逆性加权评估风险 | 所有动作同等监管，还是对可逆/只读操作更宽松？ |
| **Transparent file-based configuration and memory**<br>透明基于文件的配置与记忆 | 不透明数据库、向量检索，还是用户可见、可版本控制的文件？ |
| **Isolated subagent boundaries**<br>隔离的子代理边界 | 子代理共享父级上下文和权限，还是隔离运行？ |
| **Graceful recovery and resilience**<br>优雅恢复 | 遇错硬失败，还是静默恢复并把人的注意力留给不可恢复的情况？ |

#### 论文指出的"三种替代设计家族"

Claude Code 的原则集，是相对另外三种路线的选择：

1. **基于规则的编排**（如 LangGraph）——把决策逻辑编码为显式的状态图和带类型边，**选脚手架而非极简 harness**；
2. **容器隔离执行**（如 SWE-Agent、OpenHands）——依赖 Docker 隔离，而非分层策略执行；
3. **版本控制即安全**（如 Aider）——用 Git 回滚作为主要安全机制，而非默认拒绝评估。

> **Claude Code 的独特性在于组合**：最小决策脚手架 + 分层策略执行；基于价值观的判断 + 默认拒绝；渐进式上下文管理 + 可组合扩展。

#### 关于"不做什么"

论文特意指出架构**没有**做的三件事：

- ❌ 不对模型的推加强加**显式规划图**
- ❌ 不提供**单一统一**的扩展机制
- ❌ 会话恢复时**不恢复**所有会话级信任状态

**这些"缺席"与其原则集是一致的**——不是遗漏，是选择。

### 3.3 七组件 → 五层架构

#### 论文的四个设计问题与运行示例（论文 §3.1）

论文把架构读成对**四个反复出现的设计问题**的一组回答，并用**同一个任务**贯穿全文（*"Fix the failing test in auth.test.ts"*，后文 3.4–3.9 沿用）：

| 设计问题 | Claude Code 的回答 | 可选的替代方案 |
|---------|-------------------|---------------|
| **推理放在哪？** | **模型负责推理，harness 负责执行**。模型发出 `tool_use` 块，harness 解析、查权限、分发、收结果；**模型从不直接访问文件系统、跑 shell 或发网络请求**。推理与强制执行走**不同的代码路径**——所以**被攻破或被对抗性操纵的模型也无法越过沙箱、权限检查或 deny-first 规则**。社区估算 **仅约 1.6%** 的代码是 AI 决策逻辑 | **Devin**：显式规划与任务追踪结构；**LangGraph**：开发者定义的状态图路由 |
| **要几个执行引擎？** | **只有一个 `queryLoop()`**，无论用户是在交互终端、无头 CLI、Agent SDK 还是 IDE 里——**只有渲染与交互层不同** | **按模式分设引擎**（如 IDE 集成走和 CLI 不同的代码路径，换来界面专属优化，失去统一性） |
| **默认安全姿态是什么？** | **deny-first + 人工升级**：**deny 覆盖 ask，ask 覆盖 allow**；无法识别的动作升级给用户而不是静默放行；**多个独立安全层并行**（权限规则、PreToolUse 钩子、auto 分类器、可选 shell 沙箱），**任意一层都可阻断** | **SWE-Agent / OpenHands**：靠容器隔离；**Aider**：靠 Git 回滚 |
| **约束性资源是什么？** | **上下文窗口**（老模型 200K，Claude 4.6 系列 1M）。每次调用模型前执行**五种上下文削减策略**，另有惰性加载、延迟 schema、摘要回传 | 把**算力预算**（限制调用次数）或**工作记忆**（显式草稿本）当主要瓶颈 |

**论文 Figure 2：一个回合的运行时流程**（文字还原）：

```
用户提示 → 上下文装配（设置、历史）
   │
   ▼
迭代 1：模型调用 → 工具请求 → 权限闸门 ──Allow──► 执行（同步 / 子代理 / 后台）→ 结果 ─┐
   │                              └──Deny──► Deny Feedback（拒绝反馈回给模型）──────┤
   │              （上下文压力大时：Compact）                                       │
   ▼                                                                               │
迭代 2 … 迭代 N  ◄─────────────────────────── 更多迭代 ◄───────────────────────────┘
   │
   ▼  （某次迭代没有工具请求）
助手响应 → 用户阅读并回复
```

> **注意图里"Deny → Deny Feedback → 回到循环"这条边**——它就是 3.5.4 所说的"**拒绝是路由信号，不是硬停止**"。

#### 七组件高层结构

```
        User ──> Interfaces ──> Agent Loop ──> Tools ──> Execution Environment
                    ↑                │            ↑            (Files/Shell/Web/MCP)
                    │            Permission        │
               Prompt/Progress     System          │
                                    │             │
                                 State & Persistence
```

| # | 组件 | 内容 |
|---|------|------|
| 1 | **User** | 提交提示、批准权限、审查输出 |
| 2 | **Interfaces** | 交互式 CLI、无头 CLI（`claude -p`）、Agent SDK、IDE/桌面/浏览器——**所有入口汇聚到同一个 loop** |
| 3 | **Agent loop** | 模型调用 → 工具分发 → 结果收集的迭代循环，实现为 `queryLoop()` |
| 4 | **Permission system** | 默认拒绝的规则评估 + 自动模式 ML 分类器 + 基于钩子的拦截 |
| 5 | **Tools** | 最多 **54 个内置工具**（19 个无条件、35 个依赖特性开关和用户类型），与 MCP 工具合并 |
| 6 | **State & persistence** | 主要是**只追加的 JSONL** 会话记录、全局提示历史、子代理 sidechain 文件 |
| 7 | **Execution environment** | Shell 执行（可选沙箱）、文件操作、Web 抓取、MCP 连接、远程执行 |

> 💡 **注意工具数量的口径差异**：讲师课上讲的是"**约 40 个**内置工具"，而论文统计源码得到"**最多 54 个**（19 无条件 + 35 条件）"。差异来自统计口径——论文统计的是源码中定义的全部工具（含特性开关控制的），讲师展示的可能是特定配置下实际呈现的。**这本身也说明"工具列表是动态装配的"**。

> 🔒 **一个容易被忽略的安全细节**：程序入口 `main()` 在分发执行模式之前，会先初始化安全设置——其中包括 `NoDefaultCurrentDirectoryInExePath`，**用于防止 Windows 上从当前目录加载同名可执行文件导致的 PATH 劫持**，并注册优雅关闭的信号处理器。

#### 五层子系统分解

| 层 | 职责 | 关键实现 |
|----|------|---------|
| **Surface 层** | 入口与渲染 | 交互式 CLI（实时流式、权限对话框、进度指示）、无头 CLI、Agent SDK（通过 async generator 发出类型化事件） |
| **Core 层** | Agent loop、压缩管线 | `queryLoop()`；每次模型调用前的**五层顺序 shaper**：budget reduction → snip → microcompact → context collapse → auto-compact |
| **Safety/Action 层** | 权限、钩子、扩展、工具、沙箱、子代理 | 权限模式（最多 7 种）+ 自动模式 ML 分类器（两阶段：快速过滤 + 思维链评估）；**27 种事件类型**的 hook 管线；工具池装配 `assembleToolPool()`；shell 沙箱；子代理经 `AgentTool` 复用 `buildTool()` 工厂 |
| **State 层** | 上下文装配、运行时状态、持久化、记忆、sidechain | `getSystemContext()`（git 状态等）、`getUserContext()`（**CLAUDE.md 层级 + 当前日期**）；**四级 CLAUDE.md 指令层级**；sidechain transcript 独立存文件 |
| **Backend 层** | 执行后端、外部资源 | Shell 执行 + 沙箱、远程执行、多传输方式 MCP（stdio/SSE/HTTP/WebSocket/SDK/IDE 适配器）、**42 个工具子目录** |

#### 一个重要的架构澄清

论文专门澄清了 `QueryEngine` 的定位：**它是一个会话包装器（conversation wrapper），不是引擎本身。**

> **真正共享的代码路径是 loop 函数 `query()`，而不是那个 engine 类。** 交互式 CLI 直接调用 `query()`，完全绕过 `QueryEngine`。

**为什么重要**：这印证了"**极简核心**"的设计哲学——所有复杂度都在核心循环的外围，核心本身保持薄。

### 3.4 回合执行：Agentic Query Loop（论文 §4）

论文用一个贯穿全文的**运行示例**来串起所有机制：用户输入 *"Fix the failing test in auth.test.ts"*。这一节追踪这句话进入 `queryLoop()` 之后，一个回合内部到底发生了什么。它同时体现三条设计原则：**最小脚手架 + 最大运行时 harness**、**上下文是稀缺资源**、**优雅恢复**。

#### 3.4.1 一个回合的九个固定步骤

| # | 步骤 | 关键实现 / 细节 |
|---|------|----------------|
| 1 | **设置解析** | `queryLoop()` 解构不可变参数：系统提示词、用户上下文、权限回调、模型配置 |
| 2 | **可变状态初始化** | **只有一个 `State` 对象**，装着消息、工具上下文、压缩跟踪、恢复计数器等所有跨迭代的可变状态。循环里有 **7 个"继续点"（continue sites）**，每个继续点都是**整对象一次性赋值**，而不是逐字段修改——避免状态被改到一半 |
| 3 | **上下文装配** | `getMessagesAfterCompactBoundary()`：从**最近一次压缩边界**往后取消息，保证被压缩的内容以"摘要"而非原文形式出现 |
| 4 | **模型前上下文塑形** | **五个 shaper 顺序执行**（见 3.4.3） |
| 5 | **模型调用** | `for await` 遍历 `deps.callModel()` 的流式响应。传入：前置了用户上下文的消息、完整系统提示词、thinking 配置、可用工具集、abort 信号、当前模型规格，以及 fast-mode、effort 值、fallback 模型等附加选项 |
| 6 | **工具调用分发** | 响应含 `tool_use` 块 → 进入工具编排层 |
| 7 | **权限闸门** | 每个工具请求都要穿过权限系统（见 3.5） |
| 8 | **工具执行与结果收集** | 结果作为 `tool_result` 消息追加回对话，循环继续 |
| 9 | **停止条件** | 响应里**没有 `tool_use` 块（纯文本）→ 本回合结束** |

**为什么 `queryLoop()` 是 AsyncGenerator？** 它逐步 `yield` 出 `StreamEvent`、`RequestStartEvent`、`Message`、`TombstoneMessage`、`ToolUseSummaryMessage` 等事件。这样既能把**流式输出实时推给 UI 层**，又能在循环内部保持**单一的同步控制流**——UI 渲染和控制逻辑被干净地解耦了。

> 对照第一课：第一课的内层 `while True` 就是这个循环的"骨架版"。差别在于生产版多了第 2、3、4、7 步——状态管理、压缩边界、上下文塑形、权限闸门，这些正是"循环之外的 99%"。

#### 3.4.2 为什么选 ReAct 式的反应式循环

Claude Code 的循环遵循 **ReAct 模式**（Yao et al., 2022）：模型生成推理和工具调用 → harness 执行 → 结果喂给下一轮。论文列出了替代方案：

| 替代模式 | 做法 | 代价 |
|---------|------|------|
| **显式图式路由**（LangGraph） | 控制流定义为带类型边的状态机 | 脚手架重，灵活性被编码死 |
| **树搜索**（LATS, Zhou et al., 2023） | 在提交动作前探索多条轨迹 | 成本与延迟高 |
| **反应式循环**（Claude Code） | 每回合只提交**一条**动作序列，不回溯 | **牺牲搜索完备性，换取简单和低延迟** |

Anthropic 自己在《Building Effective Agents》里总结了 **5 种可组合的 workflow 模式**：prompt chaining、routing、parallelization、orchestrator-workers、evaluator-optimizer。Claude Code **核心循环保持反应式**，主要只在**子代理委派**上使用 *orchestrator-workers* 模式。

#### 3.4.3 工具分发与流式执行（§4.2）

模型响应里出现 `tool_use` 块后，系统在两条执行路径里选一条：

- **主路径 `StreamingToolExecutor`**：**模型还在流式输出时就开始执行工具**，降低多工具响应的延迟；
- **回退路径 `runTools()`**（`toolOrchestration.ts`）：遍历 `partitionToolCalls()` 切出来的分区批量执行。

两条路径都把工具分成 **"并发安全"与"独占"** 两类：**只读操作可并行，修改状态的操作（如 shell 命令）串行**——也就是 **"并发读、串行写"**。

`StreamingToolExecutor` 靠两个协调机制管理并发：

1. **兄弟中止控制器（sibling abort controller）**：任何一个 Bash 工具出错，**立刻终止**其他还在飞行中的子进程，而不是让它们跑完；
2. **进度可用信号（progress-available signal）**：新输出就绪时唤醒结果消费者。

**结果按"收到工具请求的顺序"缓冲并输出**，即使工具是并行跑的——因为**模型期望 tool_result 的顺序与自己的 tool_use 请求顺序一致**。论文指出这是介于"完全串行"与"更激进的推测执行"之间的中间立场；后者以 **PASTE**（Sui et al., 2026）为代表——模型还没生成完就**预测并预先执行**后续工具调用，用推测来隐藏工具延迟。

另有细节：若 `PostToolUse` 钩子发出 `hook_stopped_continuation` 附件，会置位 `shouldPreventContinuation`；结果经 `normalizeMessagesForAPI()` 规整，**只保留 user 类型消息**。

#### 3.4.4 五个"模型前上下文塑形器"（§4.3）

**每次调用模型之前**，五个 shaper 在 `query.ts` 里顺序执行，都作用于 `messagesForQuery` 数组。**顺序原则：越轻量的越靠前，越重的越靠后**（论文称之为 *lazy degradation*，懒降级）。

| # | Shaper | 开关 | 做什么 | 关键细节 |
|---|--------|------|--------|---------|
| 1 | **Budget reduction**<br>预算削减 | **始终开启** | `applyToolResultBudget()`：强制单条工具结果的大小上限，把超大输出**替换成内容引用** | `maxResultSizeChars` 非有限的工具豁免；替换记录会持久化以便 resume 重建；**必须在 microcompact 之前跑**——因为 microcompact 只按 `tool_use_id` 操作、从不检视内容，二者能干净组合 |
| 2 | **Snip**<br>裁剪 | `HISTORY_SNIP` | `snipCompactIfNeeded()`：轻量地**砍掉较旧的历史片段**，返回 `{messages, tokensFreed, boundaryMessage}` | 主 token 计数器是从**最近一条 assistant 消息的 usage 字段**推算上下文大小的，而这条消息在 snip 后依然带着 snip 前的 `input_tokens`——所以 snip 省下的量对计数器**不可见**，必须把 `snipTokensFreed` 显式传给 auto-compact |
| 3 | **Microcompact**<br>微压缩 | 时间路径始终跑；缓存感知路径由 `CACHED_MICROCOMPACT` 控制 | 细粒度压缩 | 启用缓存路径时，**边界消息推迟到 API 响应之后**再生成，以便使用真实的 `cache_deleted_input_tokens` 而非估算值 |
| 4 | **Context collapse**<br>上下文折叠 | `CONTEXT_COLLAPSE` | 对对话历史做**读时投影（read-time projection）** | 源码注释原文：*"Nothing is yielded; the collapsed view is a read-time projection over the REPL's full history. Summary messages live in the collapse store, not the REPL array. This is what makes collapses persist across turns."* **不修改**存储的历史，只是用 `applyCollapsesIfNeeded()` 把 `messagesForQuery` 换成投影视图——模型看到折叠版，完整历史仍可用于重建 |
| 5 | **Auto-compact**<br>自动压缩 | 默认开启，可关闭 | 通过 `compactConversation()` 让**模型生成完整摘要** | 先执行 `PreCompact` 钩子，用 `getCompactPrompt()` 构造摘要请求，结果交给 `buildPostCompactMessages()`。**仅当前四个 shaper 跑完后上下文仍超压力阈值时才触发** |

> 论文总结为什么要五层：**"没有任何单一压缩策略能应对所有类型的上下文压力。"** 预算削减对付**单个超大输出**；snip 对付**时间深度**；microcompact 对付**缓存开销**；context collapse 对付**极长历史**；auto-compact 是**最后手段**的语义压缩。这与第二课讲师说的"压缩是有损的"完全呼应——Claude Code 的办法就是**尽量先用无损/低损手段，实在不行才让模型总结**。

#### 3.4.5 五种恢复机制（§4.4）

| 机制 | 触发 | 行为 |
|------|------|------|
| **最大输出 token 升级** | 响应撞上输出 token 上限 | 用更高的上限重试（受 GrowthBook 开关控制，且要求无现有覆盖/环境变量上限），**每回合最多 3 次**（`MAX_OUTPUT_TOKENS_RECOVERY_LIMIT = 3`） |
| **响应式压缩**（`REACTIVE_COMPACT`） | 上下文接近容量 | 只总结"刚好够腾出空间"的量；`hasAttemptedReactiveCompact` 标志保证**每回合最多一次** |
| **prompt_too_long 处理** | API 返回 `prompt_too_long` | **先**尝试 context-collapse 溢出恢复和响应式压缩，**都失败后才**以 `reason: 'prompt_too_long'` 终止 |
| **流式回退** | 流式 API 出问题 | `onStreamingFallback` 回调，允许换策略重试 |
| **回退模型** | 主模型失败 | `fallbackModel` 参数切换到备选模型 |

#### 3.4.6 五个停止条件（§4.5）

1. **无工具调用**：模型只输出文本（**主停止条件**）
2. **达到最大回合数**：可配置的 `maxTurns`
3. **上下文溢出**：API 返回 `prompt_too_long`
4. **钩子干预**：`PostToolUse` 钩子设置 `hook_stopped_continuation`
5. **显式中止**：`abortController` 信号触发

> **横向参照**：论文后面对比的 Hermes Agent 用的是"**迭代次数上限（默认 90）+ 独立迭代预算**"；预算耗尽时**会再发一次"剥离工具"的总结调用**，让 agent 给出收尾消息，而不是在半截思路里被强行终止。这是一种很值得借鉴的"优雅收尾"设计。

---

### 3.5 工具授权与权限系统（论文 §3.5 + §5）

> 论文把这一节作为**最能体现"安全不依赖人类警觉"**的部分。

#### 3.5.1 出发点：人类审批是不可靠的

生产级 coding agent 的安全架构大致有三条路：**分层策略执行**、**OS 级沙箱**、**基于版本控制的回滚**。Claude Code 组合了前两条。

动机来自一个实测数据：Anthropic 对 auto 模式的分析发现，**用户批准了约 93% 的权限提示**——**"审批疲劳"使交互式确认在行为层面不可靠**。结论是：**既然用户习惯性地无脑批准，系统就必须在不依赖人类警觉的前提下独立维持安全。**这直接催生了三个**独立于用户注意力**运作的层：**默认拒绝评估、整体预过滤、沙箱**。

**Auto 模式的威胁模型**明确覆盖四类风险：**过度积极的行为（overeager）、诚实的错误、提示注入、模型失准**。

#### 3.5.2 七种权限模式（§5.1）

| # | 模式 | 含义 | 可见性 |
|---|------|------|--------|
| 1 | `plan` | 模型必须先做计划，**经用户批准后才执行** | 外部 |
| 2 | `default` | 标准交互使用，**大多数操作需要用户批准** | 外部 |
| 3 | `acceptEdits` | **工作目录内的编辑**、以及部分文件系统 shell 命令（`mkdir`、`rmdir`、`touch`、`rm`、`mv`、`cp`、`sed`）**自动批准**；其他 shell 命令仍需批准 | 外部 |
| 4 | `auto` | 对未通过快速路径检查的请求，由 **ML 分类器**评估（受 `TRANSCRIPT_CLASSIFIER` 开关控制） | **条件启用** |
| 5 | `dontAsk` | **抑制提示**——本该弹窗的动作**自动拒绝**；显式 allow/deny 规则仍生效 | 外部 |
| 6 | `bypassPermissions` | 跳过大部分权限提示，但**安全关键检查和"bypass 免疫"规则仍生效** | 外部 |
| 7 | `bubble` | **内部专用**：子代理向父终端升级权限请求 | 仅类型联合中存在 |

"外部可见"的 5 个模式在 `EXTERNAL_PERMISSION_MODES` 数组里定义；`auto` 只在 `TRANSCRIPT_CLASSIFIER` 开启时加入；`bubble` 既不在任何数组里，只用于子代理权限升级。

这七个模式构成一个**渐进的自治谱系**：从 `plan`（用户批准一切计划）经 `default`、`acceptEdits`，到 `bypassPermissions`（几乎不提示）。**自治增加时，系统必须从"交互式审批"转向"自动化安全检查"。**

#### 3.5.3 规则评估：deny 永远赢（§5.1）

规则按 **deny-first** 顺序评估（`permissions.ts`）。`toolMatchesRule()` 先检查 deny 规则：**deny 永远优先于 allow，哪怕 allow 更具体。** 论文的例子：**宽泛的 deny（"禁止所有 shell 命令"）不能被狭窄的 allow（"允许 `npm test`"）覆盖**。规则同时支持：

- **工具级匹配**（按工具名）
- **内容级匹配**（匹配具体输入模式，如 `Bash(prefix:npm)`）

> 论文 §3.1 给出的优先级更完整的说法是：**deny 规则覆盖 ask 规则，ask 规则覆盖 allow 规则；无法识别的动作升级给用户，而不是静默放行。**

#### 3.5.4 授权流水线（§5.2）

一个工具请求要依次经过：

1. **预过滤**：`filterToolsByDenyRules()` 在**工具池装配阶段**就把被整体拒绝的工具从模型视野里**彻底剥掉**。源码文档说明它与运行时权限检查**使用同一个匹配器**，所以像 `mcp__server` 这样的 MCP 服务器前缀规则，会在模型看到之前就**剥离该服务器的全部工具**。效果：**模型根本不会浪费调用去尝试被禁的工具。**
2. **`PreToolUse` 钩子**：已注册的钩子作为权限流水线的一部分触发，可返回 `permissionDecision`（`deny` 或 `ask`）或 `updatedInput`（改写工具输入）。**钩子的 `allow` 不会绕过后续基于规则的拒绝和安全检查。**交互路径中，**用户对话框先排队、钩子异步运行**；而 coordinator 等后台路径则是**先等自动检查完成再弹对话框**。
3. **规则评估**：deny-first 引擎评估。MCP 工具按全限定名 `mcp__server__tool` 匹配，服务器级规则匹配该服务器所有工具。
4. **权限处理器**（`useCanUseTool.tsx`）根据运行时上下文走**四条路径之一**：
   - **Coordinator**：多 agent 协调模式，先尝试自动化解决（分类器、钩子、规则），再退回用户交互；
   - **Swarm worker**：多 agent 蜂群里的 worker，有自己的解决逻辑；
   - **推测性分类器**：`BASH_CLASSIFIER` 开启且工具是 `BashTool` 时，**让预先启动的分类结果与超时赛跑**；分类器高置信度返回则**即时批准、无需用户交互**；
   - **交互式**：兜底路径，通过终端 UI 展示标准审批对话框。

> **一个极其重要的设计观点**：**当分类器或 deny 规则阻止一个动作时，系统把拒绝当作"路由信号"，而不是硬停止**——模型会收到拒绝原因，**修改方案，在下一轮循环尝试更安全的替代方案**。`PermissionDenied` 钩子事件允许外部代码以编程方式观察并响应这些拒绝。论文总结："**权限执行是在塑造 agent 的行为，而不是简单地让它停下来。**"

#### 3.5.5 自动模式分类器与五类权限相关钩子（§5.3）

`yoloClassifier.ts` 中的分类器启用时会加载**三份提示资源**：基础系统提示、外部权限模板，以及（仅 Anthropic 内部用户）单独的内部模板。它拿**待执行的工具调用 + 对话转录 + 权限模板**去评估，输出 **allow / deny / 请求人工批准**。

源码定义的 **27 个钩子事件**里，**5 个直接参与权限流程**，各有经过 Zod 校验的输出 schema：

| 钩子事件 | 能做什么 |
|---------|---------|
| **`PreToolUse`** | 返回 `permissionDecision`（`deny`/`ask`；`allow` **不绕过**后续检查）、`permissionDecisionReason`、`updatedInput`（改写参数） |
| **`PostToolUse`** | 注入 `additionalContext`；对 **MCP 工具**还能返回 `updatedMCPToolOutput` 在结果进入上下文前修改它 |
| **`PostToolUseFailure`** | 注入针对错误的 `additionalContext` 指导 |
| **`PermissionDenied`** | 在 auto 模式拒绝后提供重试指导 |
| **`PermissionRequest`** | 返回 `allow`/`deny`。coordinator 等路径中可**先于**用户对话框解决；标准交互路径中可与对话框**并行**运行 |

**时序细节**：对**非 MCP 工具**，`tool_result` **先于** `PostToolUse` 钩子发出；对 **MCP 工具**，结果**推迟到后置钩子运行之后**才发出——这样 `updatedMCPToolOutput` 才能生效。

#### 3.5.6 Shell 沙箱：授权 ≠ 隔离（§5.4）

`shouldUseSandbox.ts` 的 `shouldUseSandbox()` 检查：是否全局启用沙箱、此次调用是否选择退出、命令是否匹配排除模式。沙箱提供**独立于应用层权限模型的文件系统与网络隔离**。

> **关键洞察**：**"一个命令可以被权限批准但仍被沙箱限制，也可以被权限拒绝而根本到不了沙箱检查。"** 两套系统运行在**不同的轴上：授权 vs 隔离**。

#### 3.5.7 纵深防御的阿喀琉斯之踵：它们并不独立

分层安全依赖一个**独立性假设**：一层失效，别的层能兜住。但论文指出这几层**共享性能约束**。安全研究者（Adversa.ai, 2026）记录到：**子命令超过 50 个的命令会退回到一次通用审批提示，而不再做逐子命令的 deny 规则检查**——原因是逐子命令解析曾导致 UI 卡死。这说明：**当各层共享故障模式时，纵深防御会同时退化。**

另有独立安全研究指出：沙箱的网络限制存在 **"主机白名单用 JavaScript 后缀匹配，而名称解析在内嵌空字节处截断"** 的解析器差异——精心构造的主机名能通过后缀检查却解析到另一个被拦截的主机（受影响版本区间 v2.0.24–v2.1.89，**含论文所分析的 v2.1.88 快照**，未分配 CVE）。

#### 3.5.8 七层防御总表

一个请求必须穿过所有适用的层，**任意一层都可以阻断**它：

| # | 层 | 机制 |
|---|-----|------|
| 1 | **工具预过滤** | 被整体禁用的工具，在任何调用前就**从模型视野中移除** |
| 2 | **默认拒绝的规则评估** | **deny 永远优先于 allow，即使 allow 更具体** |
| 3 | **权限模式约束** | 当前模式决定"没有任何显式规则匹配"时的基线处理 |
| 4 | **自动模式分类器** | ML 分类器**可以拒绝规则系统本会放行的请求** |
| 5 | **Shell 沙箱** | 已批准的命令**仍可能在沙箱内执行** |
| 6 | **恢复时不恢复权限** | **会话级权限在 resume / fork 时不会被恢复** |
| 7 | **基于钩子的拦截** | `PreToolUse` 可修改决策；`PermissionRequest` 可异步并行决策 |

第 6 层看似不起眼，实则精妙：**"上次我点了同意"不应该成为"这次也可以"的理由**——信任不能被静默继承。

---

### 3.6 扩展机制：MCP、Plugins、Skills、Hooks（论文 §6）

#### 3.6.1 三个注入点：assemble / model / execute

论文 Figure 5 把整个 agent loop 抽象成三步，**每种扩展机制只在其中某个点接入**：

```python
# Claude Code 一回合 agent loop 的抽象（论文 Figure 5 的伪代码）
while not stopped:
    # a. assemble：构造模型看到的内容
    context = assemble(
        system_prompt,   # 指令头
        tool_schemas,    # 可调用工具签名
        history,         # 此前回合消息
        hook_additions,  # 由钩子推入
    )
    # b. model：选择下一个动作
    action = model(context, tools)         # 扁平的工具池
    if action.is_text_only():
        stopped = run_stop_hooks(action)   # 可否决
        continue
    # c. execute：授权并执行工具调用
    action, hook_decision = run_pre_tool_hooks(action)
    if not permitted(action, hook_decision):
        continue
    result = execute(action)
    result = run_post_tool_hooks(result)   # 修改/标注
    history.append(action, result)
```

| 注入点 | 控制什么 | 对应元素 |
|-------|---------|---------|
| **`assemble()`** | 模型**看到什么** | CLAUDE.md 文件（启动时加载上层，子目录按需加载）、Skill 描述、MCP 资源与提示、输出风格（替换响应格式化系统块）、`UserPromptSubmit` 钩子（每轮注入上下文或拦截）、`SessionStart` 钩子（会话开始一次性注入） |
| **`model()`** | 模型**能触达什么** | 内置工具（Read/Edit/Bash…）、MCP 工具（同一个扁平池）、`SkillTool`（按名字启动技能的元工具）、`AgentTool`（递归生成子代理的元工具） |
| **`execute()`** | 动作**是否 / 如何执行** | 权限规则（逐调用 allow/deny/ask）、`PreToolUse` 钩子、`PostToolUse` 钩子、`Stop` 钩子（模型停止时强制循环继续）、`SubagentStop` 钩子、`Notification` 钩子 |

> 这个三分法是理解整个扩展体系的钥匙：**扩展 = 改变"看到什么"、"能做什么"或"能不能做"。**

#### 3.6.2 四种机制，逐个看

**MCP 服务器（外部工具集成的主通道）**
- **配置作用域**：项目、用户、本地、企业，另有插件和 claude.ai 服务器在运行时合并（`services/mcp/config.ts`）；
- **传输类型**：stdio、SSE、HTTP、WebSocket、SDK，外加 IDE 专用变体（`sse-ide`、`ws-ide`）和内部的 `claudeai-proxy`；
- 每个连接的服务器贡献若干 `MCPTool` 对象；内置的 `ListMcpResourcesTool` / `ReadMcpResourceTool` 用于访问 MCP **资源**（对应第二课提到的"MCP 资源 ≠ MCP 工具"）。

**Plugins（打包与分发机制）**
- 既是**打包格式**也是**分发机制**；`PluginManifestSchema` 接受**十种组件类型**：commands、agents、skills、hooks、MCP servers、LSP servers、output styles、channels、settings、user configuration；
- 加载器校验 manifest，把各组件路由到各自注册表：commands/skills 经 `SkillTool` 元工具暴露，agents 进入 `AgentTool` 消费的定义，hooks 并入钩子注册表，MCP/LSP 服务器并入标准配置，output styles 修改响应格式；
- **一个插件包可以同时在多种组件类型上扩展 Claude Code**，因此是第三方扩展的主要分发载体。

**Skills（教模型"怎么想"）**
- 每个技能由带 **YAML frontmatter** 的 `SKILL.md` 定义；`parseSkillFrontmatterFields()` 解析 **15+ 个字段**：显示名、描述、**允许的工具**（授予该技能额外工具）、参数提示、模型覆盖、执行上下文（`'fork'` = 隔离执行）、关联 agent 定义、effort 等级、shell 配置等；
- 技能可以**自带钩子**，调用时动态注册；内置技能在启动时在内存中注册；
- 调用时 `SkillTool` 把技能指令注入上下文。

**Hooks（跨切面的生命周期控制）**——**27 个事件**，按类别：

| 类别 | 事件 |
|------|------|
| **工具授权** | `PreToolUse`、`PostToolUse`、`PostToolUseFailure`、`PermissionRequest`、`PermissionDenied` |
| **会话生命周期** | `SessionStart`、`SessionEnd`、`Setup`、`Stop`、`StopFailure` |
| **用户交互** | `UserPromptSubmit`、`Elicitation`、`ElicitationResult` |
| **子代理协调** | `SubagentStart`、`SubagentStop`、`TeammateIdle`、`TaskCreated`、`TaskCompleted` |
| **上下文管理** | `PreCompact`、`PostCompact`、`InstructionsLoaded`、`ConfigChange` |
| **工作区事件** | `CwdChanged`、`FileChanged`、`WorktreeCreate`、`WorktreeRemove` |
| **通知** | `Notification` |

其中 **15 个有事件专属的输出 schema**，支持权限决策、上下文注入、输入修改、MCP 结果转换和重试控制。持久化的钩子命令有**四种类型**：`command`（shell 命令）、`prompt`（LLM 提示钩子）、`http`（HTTP 钩子）、`agent`（**智能体验证器钩子**）；运行时另支持不可持久化的 `callback`（供 SDK 和内部插桩）。钩子来源：`settings.json`、插件、托管策略；技能钩子则在调用时动态注册。

#### 3.6.3 工具池装配：`assembleToolPool()` 的五步（§6.2）

源码注释称之为 *"the single source of truth for combining built-in tools with MCP tools"*：

1. **基础工具枚举**：`getAllBaseTools()` 返回**最多 54 个**——19 个无条件、35 个依赖特性开关/环境变量/用户类型。内部用户有额外工具；worktree 模式启用 `EnterWorktreeTool`/`ExitWorktreeTool`；蜂群启用团队工具；**Bun 二进制内嵌搜索工具可用时，省略独立的 `GlobTool` / `GrepTool`**；
2. **模式过滤**：`getTools()` 做模式特定过滤。**`CLAUDE_CODE_SIMPLE` 模式下只剩 `Bash`、`Read`、`Edit` 三个工具**——与第一课的 3 工具原型异曲同工！每个工具的 `isEnabled()` 做运行时可用性检查；
3. **deny 规则预过滤**：`filterToolsByDenyRules()`；
4. **MCP 工具集成**：`appState.mcp.tools` 经 deny 规则过滤后与内置工具合并；
5. **去重**：按名字去重，**内置工具优先于 MCP 工具**。

`REPL.tsx` 与 `AgentTool.tsx`（构建 worker 工具集时）都调用此函数，确保各条执行路径装配一致。**请求时，被"延迟"的工具可能对模型隐藏，直到通过 ToolSearch 显式查询。**

#### 3.6.4 为什么是四种机制而不是一种？（§6.3）

**答案是上下文成本不同**——单一机制无法覆盖从"零上下文的生命周期钩子"到"重 schema 的工具服务器"的整个范围。论文 Table 2：

| 机制 | 独特能力 | 上下文成本 | 插入点 |
|------|---------|-----------|--------|
| **MCP 服务器** | 外部服务集成（多传输） | **高**（工具 schema） | `model()`：工具池 |
| **Plugins** | 多组件打包 + 分发 | **中**（视内容而定） | 三个注入点都有 |
| **Skills** | 领域指令 + 元工具调用 | **低**（仅描述） | `assemble()`：上下文注入 |
| **Hooks** | 生命周期拦截 + 事件驱动自动化 | **默认为零** | `execute()`：工具前后 |

- **MCP**：给模型新的**可调用工具**，代价是服务器管理开销 + schema 占用上下文预算；
- **Skills**：塑造 agent **怎么想**（而不只是有什么工具），成本极低——**提示词里只保留 frontmatter 描述，不保留全文**；
- **Hooks**：跨切面控制（阻断、改写、标注工具调用），默认**零上下文足迹**（但可选择注入额外上下文）；
- **Plugins**：打包 + 分发层，**不是独立的运行时原语**。

**成本阶梯（零 → 低 → 中 → 高）的意义**：便宜的扩展可以大量铺开而不耗尽上下文，昂贵的留给**真正需要新工具面**的场景。

> 与第二课对读：讲师说"MCP 是原语，Skills 是封装多步流程"。论文进一步量化了它们的**上下文成本差异**——这是 Skills 作为"渐进式披露"产物的**架构层面的证据**。代价是**学习曲线**：开发者需要判断某个集成该用哪种机制。

---

### 3.7 上下文构建与记忆（论文 §7）

#### 3.7.1 上下文窗口由九类来源组装

论文 Figure 6 把上下文窗口画成**六个层次**，按"何时加载"排列：

| 层 | 内容 | 加载时机 |
|----|------|---------|
| **(1) 系统层** | 系统提示词、环境信息、输出风格、Skill 描述、MCP 工具名 | 启动 |
| **(2) 项目配置** | CLAUDE.md 层级、路径作用域规则（`.claude/rules/*`） | 启动 / 惰性 |
| **(3) 记忆** | 自动记忆、压缩摘要（替换长历史） | 启动 |
| **(4) 对话** | 对话历史、子代理摘要 | 逐回合累积 |
| **(5) 运行时** | 读取的文件、命令输出、工具结果 | 执行中追加 |
| **(6) 按需** | 延迟加载的工具定义（完整 schema 仅在需要时加载，经 ToolSearch） | 按需 |

展开成**九类来源**：① 系统提示词（含输出风格修改和 `--append-system-prompt` 内容）；② 环境信息 `getSystemContext()`（git 状态——远程模式或关闭 git 指令时跳过；每会话 memoize 一次）；③ CLAUDE.md 层级 `getUserContext()`（同样 memoize）；④ 路径作用域规则（读到匹配目录才惰性加载）；⑤ 自动记忆（异步预取相关条目）；⑥ 工具元数据；⑦ 对话历史（受压缩约束）；⑧ 工具结果；⑨ 压缩摘要（替换旧历史段）。

**一个耐人寻味的结构细节**：系统提示词由 `asSystemPrompt(appendSystemContext(systemPrompt, systemContext))` 组合；而**用户上下文（CLAUDE.md 和日期）通过 `prependUserContext()` 前置到消息数组里**。论文指出：**"这种分离意味着 CLAUDE.md 内容在 API 请求中占据与系统提示词不同的结构位置，可能影响模型的注意力模式。"**

> 这与第二课抓包实测**完全吻合**：讲师在 trace 里看到 CLAUDE.md 出现在**第一条 user 消息的上方**，并带着 *"These instructions override default behavior and must be followed exactly as written"* 的声明——它是 **user 消息**，不是 system。

**另有若干来源是"晚注入"的**：相关记忆预取、MCP 指令增量（仅新增/变化的服务器指令）、agent 列表增量、后台 agent 任务通知。**所以上下文窗口在装配时并非静态，回合内还会增长。**

#### 3.7.2 CLAUDE.md 层级与自动记忆（§7.2）

**设计原则：存储的上下文应当可被用户检查与编辑。**因此 CLAUDE.md 是纯文本 Markdown，而不是结构化配置或不透明数据库——牺牲表达力换取**可审计性**，项目级记忆还可与代码一起做版本控制。

对比其他记忆架构：
- **检索增强（embedding 检索）**：灵活，但用户**难以看到/编辑**检索系统认为相关的内容；
- **数据库式记忆**：支持结构化查询，但需要额外基础设施，且对版本控制不透明。

**Claude Code 的做法：不使用 embedding 或向量相似度索引做记忆检索**，而是用**基于 LLM 的记忆文件头扫描，按需选出最多 5 个相关文件**，**以文件粒度（而非条目粒度）呈现**。代价是不如 embedding 能选择性地检索单个条目。

> 对读第二课的 Q&A：学生问"是否用 RAG/GraphRAG 做记忆检索"，讲师答"复杂度不一定带来优势，他自己公司也用 flat files"。**论文的源码证据印证了这个说法。**

**CLAUDE.md 的四类记忆（`claudemd.ts` 的头部定义）**：

| # | 类型 | 位置 | 用途 |
|---|------|------|------|
| 1 | **托管记忆** | 如 Linux 的 `/etc/claude-code/CLAUDE.md` | OS 级策略，对所有用户生效 |
| 2 | **用户记忆** | `~/.claude/CLAUDE.md` | 私有的全局指令 |
| 3 | **项目记忆** | 项目根的 `CLAUDE.md`、`.claude/CLAUDE.md`、`.claude/rules/*.md` | 随代码库提交的指令 |
| 4 | **本地记忆** | 项目根的 `CLAUDE.local.md` | **gitignore**，私有的项目特定指令 |

> 📌 论文正文说"四级"，而 Figure 6 画的是 5 层（Managed → OS → Project → `.claude/` → local → 目录特定）。这是论文内部的口径差异，**本文以正文的"四类记忆 + 目录遍历"为准**。

**发现与优先级**：从**当前目录向上遍历到根**，在每个目录检查所有项目与本地记忆文件。**离当前目录越近优先级越高（越晚加载）**。文件按 *"reverse order of priority"* 加载：**越晚加载的获得越多模型注意力**。从根到 CWD 的目录里，无条件规则 `.claude/rules/*.md` **启动时急切加载**；而 **CWD 以下的嵌套目录，即使无条件规则也是在 agent 读到匹配目录里的文件时才惰性加载**——所以**模型的指令集可以在对话中随探索代码库而演化**。

**一个至关重要的结论**：

> **CLAUDE.md 作为 user context（一条 user 消息）而非系统提示词交付，因此模型对这些指令的遵从是"概率性"的，而不是被保证的。** 权限规则以 deny-first 顺序评估，提供**确定性的执行层**。这形成了一个有意的分离：**指导（CLAUDE.md，概率性）vs 强制（权限规则，确定性）。**

这条结论对实践有直接指导意义：**不要把"绝对不能做"的事只写在 CLAUDE.md 里——要写进权限 deny 规则或钩子。**

**`@include` 指令**（`processMemoryFile()`）：支持 `@path`、`@./relative`、`@~/home`、`@/absolute` 四种写法；只在**叶文本节点**生效（不在代码块内）；实现里**包含文件先入栈，被包含文件追加在其后**；通过跟踪已处理路径防止循环引用；不存在的文件**静默忽略**。另外，`setCachedClaudeMdContent()` 把加载的内容缓存给 auto 模式分类器，**以避免 CLAUDE.md 加载器与权限系统之间的 import 循环**。

#### 3.7.3 压缩管线的输出与持久化（§7.3）

五层压缩的设计哲学是**懒降级**：**先用破坏性最小的压缩，只有在便宜策略不够时才升级。**代价是**复杂度**：五个相互作用的压缩层（其中三个由特性开关控制）产生**用户难以完全预测的行为**。可见性也不一致：**auto-compact 在转录里产生可见摘要，microcompact 发出边界标记，而 context collapse 完全没有用户可见输出**。

压缩后的输出结构（`buildPostCompactMessages()`）：

```
[boundaryMarker, ...summaryMessages, ...messagesToKeep, ...attachments, ...hookResults]
```

**边界标记**经 `annotateBoundaryWithPreservedSegment()` 标注，记录 **`headUuid`、`anchorUuid`、`tailUuid`**，用于**读时链修补**。这个"主要追加"的设计意味着：**压缩从不修改或删除之前写入的转录行，只追加新的边界和摘要事件。**

另外几个值得记的细节：
- `PreCompact` 钩子先触发，允许钩子注入自定义指令；
- 一个 GrowthBook 特性开关控制压缩路径是否**复用主对话的 prompt cache**。源码注释记录了 **2026 年 1 月的一次实验**：*"false path is 98% cache miss, costs 0.76% of fleet cache_creation"*；
- 压缩后，**附件构建器会从实时应用状态重新宣告运行时状态**（计划、技能、异步 agent），因为压缩丢弃了先前的附件消息，但没有丢弃底层状态。

**上下文窗口尺寸**：论文指出 **老模型 200K，Claude 4.6 系列 1M**。

### 3.8 子代理委派与编排（论文 §8）

> 运行示例继续：Claude 判断"修复 auth 测试需要先探索认证模块的结构"，于是把这次探索**委派给一个子代理**。

#### 3.8.1 Agent 工具与内置子代理类型

委派机制是 **Agent 工具**（`AgentTool.tsx`，`Task` 作为旧别名保留）。模型调用它时传入结构化输入：委派提示、可选的子代理类型，以及隔离模式、权限覆盖、工作目录等配置。输入 schema 里的若干字段由**特性开关**控制（相关功能关闭时省略）：`isolation` 字段对内部用户是 `['worktree','remote']`、对外部用户是 `['worktree']`（**构建时决定**）；`run_in_background` 在后台任务禁用或启用 fork-subagent 模式时省略。

**最多六种内置子代理类型**（取决于特性开关和入口）：

| 类型 | 定位 |
|------|------|
| **Explore** | 以**读/搜索**为主的调查；**写、编辑类工具在其 deny 列表里** |
| **Plan** | 制定结构化计划；执行走标准权限模型 |
| **General-purpose** | 通用，在显式请求时使用（⚠ 注意：**省略类型时可能路由到 fork-subagent 路径**——那条路径**复用父级对话上下文而非隔离**） |
| **Claude Code Guide** | 上手与文档协助，带自己的 `permissionMode` 覆盖 |
| **Verification** | 运行验证检查（测试套件、lint） |
| **Statusline-setup** | 专用于终端状态栏配置 |

**自定义子代理**：用户通过 `.claude/agents/*.md` 文件定义，插件通过 `loadPluginAgents.ts` 贡献。**Markdown 正文就是该 agent 的系统提示词**，YAML frontmatter 配置字段包括：`description`、`tools`（白名单）、`disallowedTools`、`model`、`effort`、`permissionMode`、`mcpServers`、`hooks`、`maxTurns`、`skills`、memory 作用域、后台标志、隔离模式。JSON 形式的定义支持相同字段外加显式的 `prompt` 字段。

**结论：一个自定义 agent 可以是一个完全配置化的隔离子系统**——有自己的工具、模型、权限、钩子、记忆作用域和隔离模式。

#### 3.8.2 `SkillTool` vs `AgentTool`：容易混淆的两个元工具

| | **SkillTool** | **AgentTool** |
|--|--------------|--------------|
| 默认行为 | **把指令注入当前上下文窗口** | **总是启动一个新的隔离上下文** |
| 隔离 | 可选 `context: fork` 模式，经同一套 `runAgent()` 机制启动隔离子代理 | 始终隔离 |
| 本质 | 教当前 agent **怎么做** | 把活**派出去** |

**权衡**：大多数子代理调用需要**自包含的提示词**——因为默认路径**不继承父级对话历史**（fork-subagent 路径是例外）。共享完整转录历史的"对话式框架"可以避免这个成本，但**随 agent 数量增长有上下文爆炸的风险**。

> 这与第二课讲师的说法一致：*"每个 subagent 以全新的上下文启动……它的探索发生在主控制流之外，完成后只把结果带回来。"*

#### 3.8.3 隔离架构（§8.2）

| 模式 | 做法 | 备注 |
|------|------|------|
| **Worktree** | 创建**临时 git worktree**，子代理拥有仓库的**独立副本**，修改不影响父级工作树 | 利用 Git 自带机制，**无需容器编排** |
| **Remote**（仅内部） | 在远程 Claude Code Remote 环境启动 | **始终后台运行** |
| **进程内（默认）** | **与父级共享文件系统**，但会话上下文隔离 | 最轻量 |

**权限覆盖逻辑**（`runAgent.ts`）：
- 子代理定义了 `permissionMode` 时，覆盖生效——**除非父级已处于 `bypassPermissions`、`acceptEdits` 或 `auto` 模式**，因为这些模式代表用户对"安全/自治"权衡的**显式决定**，**永远优先**；
- 异步 agent 是否避免弹提示，走一个级联：先看显式的 `canShowPermissionPrompts`，其次 `bubble` 模式（总是显示，因为会升级到父终端），最后默认值（同步 agent 显示、异步 agent 不显示）；
- 能弹提示的后台 agent 设置 `awaitAutomatedChecksBeforeDialog: true`，**保证分类器和钩子先解决，再打断用户**；
- 显式传入 `allowedTools` 时是**两级权限作用域**：来自 SDK 的 `--allowedTools` 权限（*"explicit permissions from the SDK consumer that should apply to all agents"*）被保留，但**会话级规则被子代理声明的 `allowedTools` 替换**；未传入时（常见的 AgentTool 路径）则**继承**父级会话规则。

**三种隔离范式的横向比较**：

| 范式 | 代表 | 特点 |
|------|------|------|
| **容器隔离** | SWE-Agent、OpenHands | 资源边界更强，但需要容器基础设施 |
| **仅上下文隔离** | AutoGen 等对话式框架 | 共享文件系统，仅分离对话历史 |
| **Worktree 隔离**（Claude Code） | — | **工作区级文件系统分离**，不引入容器编排 |

#### 3.8.4 Sidechain 转录与代价（§8.3）

- 每个子代理把自己的转录写成**独立的 `.jsonl` + `.meta.json`** 文件（`sessionStorage.ts`）——历史用于**调试和审计**，但**不会撑大父级的会话文件**；
- **只有子代理最后一条响应文本和元数据返回父会话**；完整子代理历史**从不进入父级上下文窗口**；
- **代价依然显著**：Claude Code 的 **agent teams 在 plan 模式下消耗约标准会话的 7 倍 token**（Anthropic, 2025b）——所以"只返回摘要"在子代理处于隔离上下文时更为关键；
- **多实例协调用文件锁而非消息代理**：每个队友有自己的收件箱 JSON 文件（`utils/teammateMailbox.ts`），任务分配等消息在**每个收件箱的锁文件**（`utils/lockfile.ts`）保护下推入，文件位于**可预测的文件系统路径**。**用吞吐量换来两个性质：零依赖部署（不需要任何外部基础设施）和完全可调试（读纯文本 JSON 就能检查任何 agent 的状态）。**

---

### 3.9 会话持久化与恢复（论文 §9）

#### 3.9.1 转录模型

- 会话转录是**主要追加的 JSONL 文件**，位于项目特定路径（"显式清理重写"是例外）。`getTranscriptPath()` 计算为 `join(projectDir, ${getSessionId()}.jsonl)`；
- **三条独立的持久化通道**：

| 通道 | 内容 | 存储 |
|------|------|------|
| **会话转录** | 用户/assistant/附件/系统消息，加压缩及其他元数据事件 | 项目作用域，**每会话一个文件** |
| **全局提示历史** | **仅用户提示**（支持 ↑ 键与 `ctrl+r` 导航） | `history.jsonl`，位于 Claude 配置主目录；`makeHistoryReader()` 用 `readLinesReverse()` **倒序读取** |
| **子代理 sidechain** | 每个子代理独立文件 | `.jsonl` + `.meta.json` |

- 转录除消息外还存**压缩标记、文件历史快照、归因快照、内容替换记录**；
- **追加式 JSONL 是有意选择**：**偏向可审计性和简单性，而非查询能力**——每个被记录的事件都是人类可读、可版本控制、无需专用工具就能检视的。数据库方案能做更丰富的查询，但引入部署依赖并降低透明度；
- 会话身份系统把 `sessionId` 与 `sessionProjectDir` **配对**，在 resume/branch 时**一起设置**——转录路径必须使用**写入消息时的同一个项目目录**。

#### 3.9.2 Resume、Fork 与"不恢复权限"

- `--resume` 通过**回放转录**重建对话；Fork 从现有会话创建新会话（`commands/branch/branch.ts`）；
- **两者都不恢复会话级权限**——用户必须在新会话里重新授予。这是**刻意偏向安全保守的设计**：**会话被视为彼此隔离的信任域**。恢复先前授予的权限虽然方便，却有"把陈旧的信任决定带进已变化的上下文"的风险。架构选择"**重新授予而非隐式持久化**"，**接受用户摩擦作为维持"信任总是在当前会话中建立"这一安全不变量的代价**；
- 具体实现：会话级权限**只存在于内存，不序列化进转录**，resume 时从 CLI 参数和磁盘设置**重建**权限上下文；**重建后的上下文不认识的请求会回落到 deny-first 提示**。

#### 3.9.3 压缩边界与"检查点"

- `compact_boundary` 标记配合持久化设计：`annotateBoundaryWithPreservedSegment()` 在边界事件里记录 `headUuid`、`anchorUuid`、`tailUuid`，**让会话加载器能在读时修补消息链**——被保留的消息在磁盘上保留原来的 `parentUuid`，加载器用边界元数据正确链接它们；
- **"checkpoints"其实是文件历史检查点**：用于 `--rewind-files`，存放在 `~/.claude/file-history/<sessionId>/`，是**文件级快照，用于回退文件系统改动**，**不是通用的检查点存储**。

> 论文提炼的原则：**"对话的寿命超出上下文窗口"**（压缩可以回收实时视图而不结束对话）；**"对话会超出单条线性轨迹"**（追加式转录让用户可以 rewind、resume 或 fork 到新分支而不丢失先前工作）。

---

### 3.10 横向对比：Claude Code vs OpenClaw vs Hermes Agent（论文 §10）

论文拿**两个独立的开源 agent 系统**与 Claude Code 对照，目的不是评优劣，而是证明：**同样的设计问题，在不同部署场景下会得到不同的答案。**

| 系统 | 一句话定位 |
|------|-----------|
| **Claude Code** | **绑定单个代码仓库会话**的 CLI/IDE 编码 harness，进程随会话启停 |
| **OpenClaw** | **本地优先的 WebSocket 网关守护进程**（默认端口 18789，仅回环），把 WhatsApp / Telegram / Slack / Discord / Signal 等消息渠道接到嵌入式 agent 运行时，另有 macOS / iOS / Android 伴侣应用——**多渠道个人助理控制平面** |
| **Hermes Agent**（Nous Research） | **单个长驻 Python 进程**，**角色由入口脚本决定**（`hermes` / `hermes-agent` / `hermes-acp`）；会话与多 agent 看板状态持久化到两个 SQLite 文件（`state.db`、`kanban.db`） |

#### 六个对比维度（论文 Table 3）

| 维度 | Claude Code | OpenClaw | Hermes Agent |
|------|------------|----------|--------------|
| **系统范围** | 临时的每会话 CLI 进程 | 持久 WS 网关守护进程 | 单 Python 进程，角色由入口决定 |
| **信任模型** | **逐动作 deny-first 规则评估** + 钩子 + 可选 ML 分类器；7 种权限模式；渐变信任谱 | **每个网关一个受信运营者**；入站渠道靠 DM 配对码与发送者白名单；**沙箱可选**（Docker / SSH / OpenShell，作用域 per-agent / per-session / shared），**默认不启用**；官方明确声明**"共享网关上的敌对多租户隔离不是受支持的安全边界"** | **逐动作审批集中在一个文件**（`tools/approval.py`）；3 种模式（manual / smart / off）+ **无条件的 `HARDLINE_PATTERNS` 底线**（拦截 `rm -rf /`、`mkfs`、对块设备的原始 `dd`、fork 炸弹、系统关机，**无论哪种模式**）；`smart` 模式用辅助 LLM 评估风险 |
| **Agent 运行时** | `queryLoop()` 异步生成器是**系统中心** | 嵌入的 `pi-coding-agent` 核心，位于网关 dispatch 之内；**每会话队列串行化**（可选全局车道） | `AIAgent.run_conversation` 里的**同步 while 循环**；迭代上限默认 90 + 独立迭代预算；耗尽时发一次剥离工具的总结调用；工具文件通过 `registry.register()` 自注册；单条消息的多个工具调用**并行执行并带串行回退** |
| **扩展架构** | 4 种机制按上下文成本分级：MCP / 插件 / 技能 / 钩子 | **清单优先的插件系统**，12 种能力类型 + 中央注册表；独立的技能层（含公共注册表 ClawHub）；通过内置 `openclaw mcp` 支持 MCP | **5 个扩展面**：3 个与 Claude Code 同级（插件、技能、MCP）+ 2 个"换后端"面（可插拔**记忆提供者**、**模型提供者**）；钩子可以是 Python 回调或外部 shell 命令 |
| **记忆与上下文** | 4 级 CLAUDE.md 层级；5 层压缩管线；LLM 扫描记忆 | 工作区引导文件（`AGENTS.md`、`SOUL.md`、`TOOLS.md`、`IDENTITY.md`、`USER.md`，条件性 `BOOTSTRAP.md`/`HEARTBEAT.md`/`MEMORY.md`）；独立记忆系统（`MEMORY.md` + 每日笔记 + 可选 `DREAMS.md`）；**混合检索（向量+关键词，条件于 embedding 提供者）**；实验性"做梦（dreaming）"做长期记忆晋升；压缩前**自动提醒 agent 存笔记** | **单个辅助 LLM 摘要器**，带 token 预算尾部保护和工具输出裁剪；摘要前缀一段"仅供参考"的长声明；**对 `AGENTS.md`、`.cursorrules`、`SOUL.md` 等做注入模式 + 不可见 Unicode 的预注入扫描**，命中则替换为 `[BLOCKED: ...]` |
| **多 agent 与路由** | **任务委派**：Explore / Plan / general-purpose 子代理，隔离上下文，worktree 隔离，只回摘要 | 两个独立关切：(a) **多 agent 路由**（一个网关承载多个完全隔离的 agent，经确定性绑定规则路由到渠道/发送者）；(b) 子代理委派（最大嵌套 5，默认 1，推荐 2）；项目愿景**明确拒绝把 agent 层级框架作为默认架构** | `delegate_task` 在线程池里启动子 `AIAgent`；默认并发上限 3、深度上限 1（夹在 [1,3]）；叶子子代理默认不能再委派；**子代理始终禁用持久记忆**；另有**基于 SQLite 的 Kanban 工作队列**，多进程 worker 认领任务，支持"陈旧认领回收"，连续两次失败自动阻塞 |

> 💡 **论文脚注里的一个小细节**：Hermes 的文档与实现**存在漂移**——`SECURITY.md` 写审批模式是 `on/auto/off`，而 `tools/approval.py` 实际返回 `manual/smart/off`；两份文档说委派深度默认 2，而 `tools/delegate_tool.py` 设 `MAX_DEPTH = 1`。论文**以源码为准**。这是"读源码而非读文档"的现成例证。

#### 三个观察（§10.3）

1. **问题是稳定的，答案随部署场景变化。** 3.3 节介绍的那四个反复出现的设计问题（推理在哪、安全姿态、上下文管理、扩展结构）**对编码之外同样适用**；
2. **三者押注的方向不同**：Claude Code 押**逐动作的分级安全评估**；OpenClaw 押**边界级的身份与访问控制**；Hermes 居中——**逐动作审批像 Claude Code，但渲染到许多界面像 OpenClaw**。三者的**信任边界位置不同**：Claude Code 在**模型与执行环境之间**，OpenClaw 在**网关边界**，Hermes 介于两者；
3. **三者是可组合的，而非互斥的替代品**：OpenClaw 可通过 **ACP（Agent Client Protocol）** 把 **Claude Code / OpenAI Codex / Gemini CLI** 当作外部编码 harness 托管；Hermes 同时站在 ACP 主机与访客两侧（网关托管平台适配器，`hermes-acp` 让外部 IDE 托管 Hermes）。论文由此认为：**AI agent 的设计空间不是平面的分类，而是分层的**。

**Hermes 的额外能力（§10.2，无法放进六维表）**：WAL 模式 SQLite + 全文检索 + 压缩触发的"父会话链"；网关重启后会话**自动恢复**（以转录时间戳新鲜度为依据，默认一小时窗口）；内置 **cron 调度器与 webhook 订阅**（cron 会话禁用持久记忆，默认 600 秒无活动超时）；后台 **"curator" 循环**审查 agent 自创的技能，归档陈旧的但**从不删除**，且仅针对有 agent 出处的技能。

---

### 3.11 相关工作与行业坐标（论文 §11）

#### 编码工具按自治程度分类（Table 4）

| 类别 | 例子 | 模式 |
|------|------|------|
| **行内补全** | Copilot、Tabnine | 编辑器插件 |
| **聊天集成** | Cursor、Windsurf、Cody | 与 IDE 耦合的产品 |
| **Agentic CLI** | Claude Code、Codex CLI、Aider | 工具使用循环 |
| **完全自主** | Devin、SWE-Agent、OpenHands | 沙箱 + 规划 |

Claude Code 共享更高自治系统的一些特性（auto 模式分类器、后台 agent 执行、远程环境），但**默认保留交互式审批**。

#### 上下文管理的设计空间（Table 5）

| 做法 | 机制 | 粒度 |
|------|------|------|
| 简单截断 | 丢弃最旧消息 | 粗 |
| 滑动窗口 | 固定大小的近期历史 | 中 |
| RAG | 检索相关片段 | 细 |
| 单次摘要 | 一次性压缩 | 粗 |
| **渐进式压缩（Claude Code）** | **多层管线** | **极细** |

#### 论文引用的几个有分量的论点

- **复合错误**（Huyen, 2025）：**每步准确率 95% 时，100 步的任务只有 0.6% 的成功率**——这是"逐步验证"的数学动机；
- **规划工具的真相**（Chase, 2025）：Claude Code 的规划工具"**基本上是个空操作（no-op）**"，价值在于**让 agent 保持在轨道上**，而非执行任何外部计算；
- **信任被忽视**（Wang, 2025）：权威/信任是学术框架最常遗漏的要素，"*the most overlooked element*"；
- **Martin（2026）的七种生产模式**：给 agent **文件系统与 shell 访问**作为通用动作层；**按需发现动作**而非预先加载所有工具 schema；
- **Loop engineering（循环工程）**（Osmani, 2026）：不再每轮提示 agent，而是**搭建一个循环**——找活、分配、检查结果、决定下一步，由技能、MCP、子代理这些本文记录的原语拼成。它让单个开发者能**自主指挥多得多的工作**，Claude Code 团队自己也有兴趣——但**减少人的逐回合参与，也加剧了长期开发者能力的担忧**；
- **OpenAI 的 harness engineering**（2026a）同样把"harness 本身的设计"视为核心工程任务；
- **MCP 供应链风险**（Hou et al., 2025）：梳理了 **26 个主要目录里数千个社区 MCP 服务器**，把 MCP 威胁归纳为**4 类攻击者、16 个场景**，包括**工具投毒（tool poisoning）、rug pull、跨服务器遮蔽（cross-server shadowing）**；美国 NSA 的指导把 MCP 安全视为**覆盖协议设计、运行时调度、外部服务集成、长期监控的生命周期问题**；
- **面向 agent 的工具 API 设计**（Pan, 2026）：agent 用的 API 应该提供 **search、resolve、preview、execute、verify、recover** 六个阶段，而不只是面向人的 CRUD 端点；
- **"工具供应链"视角**：MCP 服务器、插件、技能、SDK、agent 间协议共同构成一条工具供应链——它们扩展 agent 能力，同时需要**身份、白名单、版本、审计日志和撤销**。

---

### 3.12 讨论：设计哲学、价值张力与实证信号（论文 §12）

#### 3.12.1 设计哲学：98.4% 是 harness，只有 1.6% 是"决策逻辑"

> **据社区对提取源码的分析估算，Claude Code 代码库里约 1.6% 是 AI 决策逻辑，其余 98.4% 是运行时基础设施。**

这个比例"并非偶然"：整个架构压倒性地是**确定性基础设施**（权限闸门、工具路由、上下文管理、恢复逻辑），LLM 只是被当作**无状态的补全端点**调用。这与主流 agent 工程模式**背道而驰**——LangGraph 把模型输出路由经显式图节点，Devin 把多步规划器与重运行基础设施配对；而 Claude Code **给模型在丰富 harness 内的最大决策自由度**。论文的原话大意：**"工程复杂度的存在不是为了约束模型的决策，而是为了使能它们。"**

论文进而提出一个值得玩味的类比：agentic 编码工具是否正在**收敛到类操作系统的抽象**——**核心循环是内核，其余一切都是 OS**？

**随着前沿模型在编码任务上的实际能力趋同，周边运行时 harness 的质量成为主要差异化因素。**论文引了两条实证：
- **固定模型、只换 harness**，单个模型在长程任务上的得分最多能变化 **18 分**（WildClawBench，Ding et al., 2026；测试的 harness 含 Claude Code 与 OpenClaw）；
- 即使对最强的模型，**仅换 harness 就能让功能与安全通过率变动 10 个百分点以上**（Compagna, 2026）。

**"模型更强了，还需要 harness 吗？"**——论文给出一个分价值观的回答：

| 价值观 | 受模型能力影响吗？ |
|--------|-------------------|
| **能力放大** | **主要受影响**——但受影响的只是其中的**决策脚手架**（规划与控制逻辑）。模型已强的领域（代码、数学）能自行达成解，约束与引导就不那么必要 |
| **可靠执行** | **部分例外**：更强的模型读需求更准、自我纠错更好；但上下文窗口仍有限、会话仍要恢复、模型仍倾向每次用不同方式重建同一件东西——**上下文管理与恢复仍需要** |
| **安全/安保/隐私** | **完全与能力无关**。deny-first、沙箱、分类器、审计日志一如既往重要，**更强的模型反而风险更高而非更安全** |
| **人的决策权** | 关乎人的**决定权**，不是模型的能力，所以审批、中断、转录保持原有作用 |
| **情境适应性** | 强模型仍是**没见过你代码的通用模型**，CLAUDE.md、技能、MCP 仍用来把它适配到你的项目 |

再加上**token 经济学**（约束全部五个价值观）——"更好的模型并不让 token 免费"。**结论：harness 不会因模型变强而失效，变的只是"模型已经够强的地方"的决策脚手架。**

#### 3.12.2 价值张力（论文 Table 6）

五个价值观之间会彼此拉扯，这不是设计缺陷，而是**同时追求多个价值观的结构性后果**：

| 价值对 | 张力 | 证据 |
|--------|------|------|
| **权威 ↔ 安全** | 审批疲劳 vs 保护 | **93%** 批准率削弱人的警觉（Hughes, 2026）；安全必须靠分类器与沙箱补偿 |
| **安全 ↔ 能力** | 性能 vs 防御深度 | **>50 个子命令回退**跳过逐子命令 deny 检查（Adversa.ai, 2026）；安全层共享性能约束 |
| **适应性 ↔ 安全** | 可扩展性 vs 攻击面 | **多个 CVE 利用钩子与 MCP 服务器的"信任前初始化"**（Donenfeld & Vanunu, 2026） |
| **能力 ↔ 适应性** | 主动性 vs 打扰 | **多完成 12–18% 的任务，但高频率下用户偏好下降**（Chen et al., 2025） |
| **能力 ↔ 可靠性** | 速度 vs 一致性 | 有界上下文阻碍整库感知（§7）；子代理隔离限制跨 agent 一致性（§8）；相邻工具观察到复杂度上升（He et al., 2025） |

#### 3.12.3 关于"开发者长期能力"的实证证据

| 研究 | 规模 | 发现 |
|------|------|------|
| **Becker et al., 2025**（随机对照试验） | **16 名资深开发者、246 个任务** | AI 工具使开发者**慢了 19%**，**却主观感觉快了 20%** |
| **He et al., 2025**（因果分析 Cursor 采用） | **807 个仓库** | 代码复杂度**上升 40.7%**（p < 0.001）；**第 1 个月速度飙升 +281%，第 3 个月回落到基线**；复杂度上升与后续开发速度成比例下降 |
| **Kosmyna et al., 2025**（EEG 研究） | **54 名参与者** | LLM 使用者的**神经连接减弱，且在移除 AI 后仍持续** |
| **Shen & Tamkin, 2026** | — | AI 辅助条件下开发者**理解测试得分低 17%** |
| **Liu et al., 2026**（大规模审计） | **304,000 个 AI 撰写的提交、6,275 个仓库** | 可测量的技术债；约**四分之一**的 AI 引入问题**持续存在到最新版本**，安全类问题的持续率**明显更高** |
| **Rak, 2025**（IEEE Spectrum） | 行业数据 | **2023–2024 年入门级技术岗位招聘下降 25%** |

**需要保持清醒的是**：这些证据**针对相邻系统而非 Claude Code 的架构本身**；它们**最相关的是依赖有界上下文、工具使用循环和局部生成决策的 agent 系统**。

#### 3.12.4 四个具体的架构权衡（§12.3）

**① 安全 vs 自治**
- 权限模式构成**单调递减的安全梯度**（plan → default → acceptEdits → auto → bypassPermissions），自治越高安全越少；
- **梯度是被"习惯化"而非"选择"走完的**：McCain et al., 2026 的纵向数据显示，**自动批准率从 <50 次会话的约 20% 升到 750 次会话的 40%+**，且会话时长明显增加；
- **沙箱把权限提示频率降低了约 84%**（Dworken & Weller-Davies, 2025）——**对"人类审批不可靠"的架构回应是：减少人必须做的决定的数量**；
- **独立性假设会被打破**：auto 分类器是一次独立 LLM 调用（直接 token 成本）；`bashSecurity.ts` 做顺序 AST 检查（解析延迟）；deny-first 规则评估作用于命令结构。**性能压力会让各层同时降级**。论文的评判标准很精彩：**"相关评判标准不是任何单层能否被绕过，而是需要多少个独立的层同时失效，以及它们是否共享故障模式。"**

**② "信任前初始化"窗口**（对抗条件下的权限模型）
- 两个独立验证的漏洞有同一个根因：**项目初始化期间执行的代码（钩子、MCP 服务器连接、设置文件解析）在交互式信任对话框展示之前就运行了**——这个窗口**落在 deny-first 评估流水线之外**，形成一个**结构性特权阶段**；
- 涉及 **CVE-2025-59536（CVSS 8.7）** 与 **CVE-2026-21852（CVSS 5.3）**（Check Point Research 发现）；另有 **CVE-2025-54794、CVE-2025-54795** 利用权限流水线别处的路径校验与命令解析缺陷；**四个都在披露后数周内修复**；
- **洞察**：权限流水线展示的是**空间上的检查顺序**，却没有捕捉**时间维度**——"会话初始化期间各机制**何时**生效"。**"扩展加载 → 信任对话框 → 权限执行"这个顺序，制造了扩展架构先于安全架构运行的窗口。**

**③ 上下文效率 vs 透明度**
- 五层压缩有效，但**压缩对用户大体不可见**：预算削减把长输出换成引用、context collapse 用摘要替换消息、snip 修剪旧历史——**用户没法轻易检查丢了什么**；
- 外部研究补充了源码层看不到的两个代价：**摘要步骤是阻塞式推理停顿**，且**非确定性**——相同输入下保留内容会在多次运行间波动（Cim et al., 2026）。

**④ 简单 vs 可扩展**
- 四种扩展机制带来**组合式交互**：插件贡献改写工具输入的 `PreToolUse` 钩子；auto 分类器读取缓存的 CLAUDE.md；路径作用域规则在读新目录时惰性加载，**可能在对话中途改变分类器行为**；权限处理器的四条分支在多处与钩子流水线交互——**产生难以从任何单一配置文件预测的涌现行为**。

#### 3.12.5 可检验的预测与早期信号（§12.4）

论文从架构属性推出**可检验的预测**：**有界上下文窗口**让 agent 无法同时感知整个代码库，每层压缩都引入有损；因此**架构上可预测——agent 生成的代码会比拥有全库可见性时出现更高比例的"模式重复"和"约定违反"**；**子代理隔离让这一效应叠加**——并行 agent 可能**各自独立重新实现已存在于别处的方案**。**"好的局部决策在模型缺乏全局上下文时会产生糟糕的全局结果。"**

一项在 Claude Code 自身上做的**受控最小对（minimal-pair）研究**（Trivedi & Schmitt, 2026）把效应落到实处：**代码整洁度没有改变任务通过率，但更整洁的输入让 token 用量减少 7–8%、文件重复访问减少 34%**——说明 harness 对上下文的处理**最明显体现在操作足迹（成本与导航）上，而非原始成功率**。

#### 3.12.6 局限与新兴方向（§12.5–12.6）

**局限**：`getSystemContext()` 和 `getUserContext()` 都用 lodash `memoize`，所以 git 状态和 CLAUDE.md 内容是**缓存而非每回合重算**（压缩可清缓存，惰性加载的路径作用域规则提供部分补偿）；**特性开关造成构建级差异**（`TRANSCRIPT_CLASSIFIER` 为 false 的构建里，整个 auto 分类器被剔除；特性开关模块用动态 `require()` 而非静态 import，因为 `feature()` 受 `bun:bundle` tree-shaking 约束只能用在 if/三元条件里）。

**新兴方向**：
- **更长上下文窗口**会降低压缩压力，可能简化渐进管线；**多模态工具**（截图、图表、UI 预览）会扩大工具面并带来新的上下文挑战；**对权限性质的形式化验证**（如证明 deny 永远优先、沙箱命令无法逃逸、恢复的会话无法继承陈旧权限）；
- **架构解耦**：Anthropic 的 **Managed Agents** 把 agent 的组件（session、harness、sandbox）虚拟化，使"每个都成为对其他组件做很少假设的接口，且可独立失效或被替换"，**类比操作系统把硬件虚拟化为进程和文件**；Cursor 把 agent 循环、机器状态、对话状态分离；LangChain 的 Managed Deep Agents 把持久线程、检查点、流式、可观测性、人在回路纳入托管运行时；Google 的 Antigravity 让人通过**计划、截图、录屏等 artifact** 检查 agent 的工作。**论文由此提炼的设计问题是"运行时所有权"：哪一层拥有循环、状态、沙箱、策略和恢复路径？**
- **记忆升格为一等子系统**：Claude Code 目前暴露的是**事实层**（CLAUDE.md、自动记忆）与**工作层**（对话窗口），**"经验层"（从过往会话中积累、自动整理的策略手册）是自然的下一步**；LangSmith Context Hub 把 `AGENTS.md`、技能、策略、示例当作**版本化、可审查的 artifact**——**"上下文需要生命周期，而不只是 token 预算"**；
- **可观测性与静默失败**：Bessemer 2026 报告估计 **"78% 的 AI 故障是不可见的"**；LangChain 对 **1,340 名受访者**的调查把**质量（而非成本）**列为生产使用的首要障碍，并发现**可观测性采用率近 89%，而离线评估只有 52.4%**；OpenAI 的 agent 改进循环让 traces 与反馈变成 evals，再变成给 Codex 的 harness 修改交接；
- **治理**：国际 AI 安全报告警告"**AI agent 因自主行动而风险更高，更难在失败造成伤害前介入**"；MIT AI Agent Index 发现**只有 13.3% 的 agentic 系统发布了 agent 专属安全卡**；EU AI Act 等监管可能对日志、透明度、风险管理和人类监督施加外部约束；
- **主动式架构**：特性开关控制的 **KAIROS** 系统实现持久的后台 agent，带**基于 tick 的心跳**——没有待处理用户消息时，系统注入周期性 `<tick>` 提示，**模型决定行动还是睡眠**。它试图通过**终端焦点感知**（用户离开时最大化自主行动，在场时增加协作）和 **`SleepTool` 的经济节流**（每次唤醒花一次 API 调用，**prompt cache 在 5 分钟无活动后过期，睡眠/唤醒因此是显式的成本优化**）来解决"完成率 +12–18% 但高频率下用户偏好下降"的张力。⚠ 论文强调：**无法确认 KAIROS 在生产构建中是否启用。**

#### 3.12.7 三条贯穿的设计承诺（§12.7）

1. **分层渐进，而非单体机制**：安全（7 层）、上下文（5 层压缩 + 惰性加载 + 延迟 schema + 摘要回传）、扩展（4 种机制）都是**独立机制的渐进栈**——**用简单性与可调试性换取纵深防御**，代价是层间交互可能产生难以预测的涌现行为。与 OpenClaw、Hermes 的对比说明，分层模式反映的是**共享的设计问题**，而非 Claude Code 的特有实现；
2. **只追加、偏向可审计性而非查询能力**：转录是追加式 JSONL + 读时链修补；权限不跨会话恢复；压缩用读时投影而非破坏性编辑。**代价**：更丰富的结构化查询（"给我看所有跨会话修改过文件 X 的工具调用"）需要事后重建而非直接查找；
3. **确定性 harness 里的模型判断**：**工具路由、权限执行、上下文装配、恢复逻辑**为模型创造条件；分层权限在 agent 边界上保持安全不变量，`assembleToolPool()` 把内置与 MCP 工具合成单一接口，而**模型对"调用哪些工具、按什么顺序"保有完全自主权**。

---

### 3.13 论文的元问题：人的能力会不会退化？（论文 §2.4 / §13.6）

论文提出了一个超越"五个价值观"的问题：**这套架构是否帮助开发者保住长期的理解力和能力？**

引用的证据令人警醒（详见 3.12.3 表格）：

- Anthropic 自己对 132 名工程师/研究员的研究记录了 **"监督悖论"（paradox of supervision）**：**过度依赖 AI，会萎缩掉监督 AI 所需要的技能**；
- 独立研究发现，AI 辅助条件下开发者的理解测试得分低 17%。

论文诚实地说明：**这个担忧在架构中并没有成为显著的设计驱动力**，因此把它作为**跨领域的关切**而非并列的第六个价值观来处理。结论部分的判断很直接：

> **"对 agent 构建者而言，最重要的开放问题不是如何加更多自治，而是如何随时间保住人的能力。"**
> **"架构只提供了有限的机制来显式保护长期的人类理解、代码库一致性或开发者成长管道。未来系统可以把这个可持续性缺口视为一等设计问题，而不是下游的评估指标。"**

**§13.6 的更细切分**：这个问题要拆成两个子问题——
1. **度量缺口**：现有证据都在"会话到数月"的尺度上，而 harness **没有暴露任何"每会话的理解度或约定漂移"信号**；Barke et al.（2023）的程序员交互模式、Perry et al.（2023）的 AI 引入安全回退、Aiersilan（2026）的会话级"认知卸载探针"协议，勾勒了会话粒度度量的可能；
2. **设计缺口**：度量出来之后，**架构能否响应**？例如"把 generator-evaluator 分离应用到**人这一环**"、"保护理解力的界面"，或"尚未命名的机制"。论文**不对机制类别表态**，也不确定 harness 是否是行动的正确位置（还是 IDE、组织或人的开发循环）；
3. 另与"**过程监督**"相连：He et al. 的人机协作规划研究指出用户需要**过程级控制**而非仅结果级审查——对 coding agent 的类比是：**"工作还在展开时，用户能检查和修改什么？"**

引文方面，论文借用 Karpathy（2026）反思自己转向 agent 驱动编码时的警告：**"你可以外包你的思考，但不能外包你的理解。"**

> 这值得每个使用者自己去回答。

---

### 3.14 论文指出的六个开放方向（论文 §13）

| # | 开放方向 | 核心问题与论文引用的文献 |
|---|---------|---------------------------|
| 1 | **静默失败与可观测性-评估鸿沟** | Agent 失败时常常**不报错**。论文问：**scaffolding（generator-evaluator 分离、sprint contract、事后检查，建立在 Self-Refine 之上）应该在 harness 内（比如作为 27 个钩子之外的新增钩子事件）还是作为独立评估层？** 现有钩子管线能否在当前的上下文成本包络内承载它？文献：Cemri et al. 梳理的 **14 种失败模式**（系统设计、agent 间失调、任务验证）；Pathak et al. 的**轨迹异常检测基准**；Yao et al. 的 **pass^k**（k 次独立尝试全部成功的概率）暴露一致性缺口；Kapoor et al. 指出当前 agent 基准**缺少 holdout 和成本控制**。结论：**"开放工作落在 harness 层"** |
| 2 | **持久化：记忆与长期同事关系** | 在"静态指令（CLAUDE.md）"与"单会话转录"之间，**缺一层既非静态指令、又非单会话记录的持久状态**。文献：MemGPT（Packer et al., 把 LLM 当作带分页内存的操作系统）、Mem0（生产级记忆）、A-Mem、Agent Workflow Memory、Reflexion、Voyager（技能库积累）；**MemGym** 把问题从"笔记存哪里"变成"**哪些被记住的状态能帮 agent 继续正确工作**"。人的一侧：Dell'Acqua et al. 在 **776 名宝洁专业人员**中的田野实验、Copilot 推广的纵向研究。OpenClaw 的"做梦"记忆与 Hermes 的 SQLite+FTS 是两个具体参照点 |
| 3 | **Harness 边界演化：在哪、何时、做什么、与谁** | **Where**：Managed Agents 把 session/harness/sandbox 虚拟化（延续 MemGPT 的虚拟内存类比；DSPy 把 harness 本身当编译目标）。**When**：KAIROS 式主动性（+12~18% 任务通过，但**高频"持续建议"变体偏好跌到 47%，对比 80–90%**）。**What**：**视觉-语言-动作（VLA）**把 harness 扩到**物理动作**（RT-2、π0、Helix、GR00T），**"按可逆性加权的风险"在物理世界的代价不对称是该原则点名却未量化的**。**With whom**：角色分化的多 agent（MetaGPT、CAMEL、AgentVerse、ChatDev）、多 agent 辩论、图结构工作流（GPTSwarm）。问题：**单一 harness 架构能否覆盖四个维度，还是会碎裂成专用栈？** |
| 4 | **视野扩展：从单会话到科学项目** | 当前主要单位是**回合、会话、子代理**。文献：**AI Scientist**（端到端自主研究管线）及其 SIGIR Forum 独立评估、**Google AI co-scientist**（跨**天**运行的假设生成）、**AlphaEvolve**（人类专家需数周的算法发现）、**METR** 测量"前沿 agent 以固定可靠性完成的任务时长"、**Quantitative Goal Persistence** 基准（agent 局部工具调用都合理，却在验证器确认足够有效工作单元前就停了——**"长程编码 agent 的进展需要外部的'完成'概念，而不只是一句流畅的收尾"**）。⚠ 论文标注的**事后发展（Tier A）**：Claude Code **v2.1.154** 引入**动态工作流（dynamic workflows）**——模型写一段 **JavaScript 编排脚本**，由后台运行时执行，**扇出到多个子代理（每次运行最多一千个）**，中间结果存在**脚本变量里而非模型上下文中**，随 Claude Opus 4.8 发布。这是**超越会话/子代理/记忆的协调原语**——把编排逻辑本身搬出对话。**"编排即代码"会否成为主导的长程原语？它的 token 成本与降低的人类中途监督，如何与可靠性收益权衡？** |
| 5 | **大规模治理与监督** | 文献：**欧盟 GPAI 行为准则**与指南、**MIT AI Agent Index**、**国际 AI 安全报告**、**OECD** 报告、Nannini et al. 的 **"AI agents under EU law"**、**Bartz v. Anthropic** 判决（训练数据来源这一**输入侧**约束，区别于 AI 生成代码的**输出侧**版权问题）。⚠ **Tier A 事件**：2026 年 6 月一项美国出口管制令禁止外国公民使用 Anthropic 的 **Fable 5 和 Mythos 5** 模型，**上线数日内 Anthropic 对全球所有用户停用了这两个模型**——**政府政策可以直接决定一个模型是否保持部署**。另有 **Boiling the Frog** 基准评估多轮工作区编辑在**渐进式攻击**下是否变得不安全——对 coding agent 重要，因为**风险对象可能是被修改的仓库，而非最终回答文本**。两个开放性质：deny-first 评估**对内可通过转录审计，但尚不能像 GPAI 准则设想的那样对外审计**；"价值观优于规则"原则能否容纳合规审查可能需要的**显式规则表述** |
| 6 | **长期开发者能力** | 见 3.13。**"度量缺口 + 设计缺口"**两个子问题 |

> 这六个方向本身就说明了这门课的定位：**它教的不只是"今天怎么用"，而是"明天会往哪走"。**

---

### 3.15 论文方法论、证据等级与源码结构（论文附录）

#### 3.15.1 三级证据体系——读论文时的"可信度刻度"

论文给每个论断标了证据等级（文中以 *Tier A/B/C* 标注）：

| 等级 | 含义 | 可信度 |
|------|------|--------|
| **Tier A**（产品文档） | 来自 Anthropic 官方文档与工程文章 | 确立**产品意图**，但**可能不反映内部实现** |
| **Tier B**（代码验证） | 引用提取出的 TypeScript 代码库中的**具体文件与函数**（v2.1.88，取自公开 npm 包的提取） | **最强证据层** |
| **Tier C**（重构） | 来自社区分析、OpenClaw/Hermes 结构对比、或对代码模式的推断 | 以**模棱两可措辞**表述 |

**语料规模**：约 **1,884 个文件、约 51.2 万行 TypeScript**。OpenClaw 与 Hermes 只作**比较参照点**，不是"真理标准"。

#### 3.15.2 方法论与局限

- **设计问题的识别方式**：逐个子系统检查"其他生产 agent 中存在替代设计的反复选择点"，再把 Claude Code 的答案追到具体源文件和函数（Tier B）；五价值观框架则来自官方文档与创造者陈述（Tier A）；
- **token 经济学**被当作**同时约束全部五个价值观的横切约束**；
- **局限（务必记住）**：
  - **静态快照**：只反映一个版本（v2.1.88），特性开关造成构建级差异；
  - **逆向工程认识论**：源码揭示**实现的结构、控制流、依赖和特性门**，**无法确认设计意图、生产环境启用的开关、运行时普遍性或未发布行为**；
  - **单系统分析**：发现描述的是 Claude Code 的设计空间，**不是所有编码 agent 的设计空间**，泛化有边界；
  - **对比系统快照**：OpenClaw 与 Hermes 的分析各自反映特定开发状态，**可能不代表它们当前的能力**。

#### 3.15.3 关键源文件与职责（论文 Table 7）

| 文件 | 大小 | 职责 |
|------|------|------|
| `main.tsx` | 804KB | 入口、模式分发、初始化 |
| `query.ts` | 68KB | **核心 agent 循环、5 个上下文 shaper** |
| `QueryEngine.ts` | 47KB | SDK/无头会话包装器 |
| `Tool.ts` | 30KB | 工具接口、类型、工具函数 |
| `history.ts` | 14KB | 全局提示历史 |
| `mcp/client.ts` | 大 | MCP 客户端（8+ 种传输变体） |
| `compact.ts` | 大 | 压缩引擎 |
| `AgentTool.tsx` | 大 | Agent 工具、子代理分发 |
| `runAgent.ts` | 大 | Agent 生命周期与协调 |

**目录结构**：`src/tools/` 约 **42 个子目录**（每个含 schema、描述、权限要求、执行逻辑），`src/commands/` 约 **86 个斜杠命令子目录**；关键服务目录：`services/tools/`（`StreamingToolExecutor`、`toolOrchestration`、`toolExecution`）、`services/compact/`（压缩引擎）、`services/mcp/`（MCP 客户端与配置）；权限基础设施跨 `utils/permissions/`（规则评估、分类器）、`hooks/useCanUseTool.tsx`（权限处理器）、`types/permissions.ts`（模式定义）、`types/hooks.ts`（事件 schema）。

**两个有意思的结构细节**：
- **`query.ts`（文件）与 `query/`（目录）并存**：文件含主循环，目录放循环配置与上下文装配的辅助模块；
- **代码显式避免循环 import**：`types/permissions.ts` 就是为了打破 import 环才被抽出的；`context.ts` 里的 `setCachedClaudeMdContent()` 则避免了经由权限/文件系统路径的循环。

#### 3.15.4 条件工具可用性（论文 Table 8）

模型"可能只看到 **3 个工具**（简单模式：Bash、Read、Edit），也可能在启用所有特性的完整内部构建里看到 **54 个**（19 无条件 + 35 条件）"。

| 类别 | 例子 |
|------|------|
| **始终包含** | `AgentTool`、`BashTool`、`FileReadTool`、`FileEditTool`、`FileWriteTool`、`SkillTool`、`WebFetchTool`、`WebSearchTool` |
| **环境相关** | `GlobTool`/`GrepTool`（除非已内嵌）、`ConfigTool`（仅 ant）、`PowerShellTool`（Windows） |
| **特性开关** | `TaskCreate/Get/Update/List`（todoV2）、`EnterWorktreeTool`（worktree）、`TeamTools`（蜂群）、`ToolSearchTool` |
| **空值检查** | `SuggestBackgroundPRTool`、`WebBrowserTool`、`RemoteTriggerTool`、`MonitorTool`、`SleepTool` |

#### 3.15.5 社区重实现（论文 Table 9）

Claude Code 的 TypeScript 源码公开可读后，出现了多个**独立的社区重实现**，每一个都是**可运行的 CLI agent**，而不是被动的源码转储：

| 项目 | 运行时 | 方法 |
|------|--------|------|
| **ClawCodex** | Python | 移植 + 多提供商模型层 |
| **Claw Code** | Rust | 独立 Rust 重写 |
| **claude-code-working** | TypeScript / Bun | 逆向工程、可运行 |
| **Claude Code Source: Buildable Research Fork** | TypeScript | 从快照重建构建系统 |
| **Open Claude Code** | JavaScript / npm | 夜间自动反编译管线 |

覆盖 **4 种运行时**（Python、Rust、TypeScript/Bun、JavaScript/npm）与 **3 种重建方法**（基于观察行为的独立重写、基于 TS 快照重建构建的 fork、自动化反编译管线）。

> 📚 **想进一步深入**：论文配套仓库 https://github.com/VILA-Lab/Dive-into-Claude-Code 维护着随时跟踪新进展的"设计空间伴随笔记"（但不作为 Claude Code 实现的证据）。

---

## 4. 把三份材料串成一个认知模型

三份材料其实在讲同一件事的三个高度。把它们叠起来看：

```
                     ┌─────────────────────────────────────┐
   架构层（论文）      │  价值观 → 设计原则 → 具体实现        │
   「为什么这样设计」   │  5 价值观 · 13 原则 · 7 组件 · 5 层  │
                     └─────────────────────────────────────┘
                                      ▲
                     ┌─────────────────────────────────────┐
   工程层（第二课）      │  Harness 组件逐一拆解 + 抓包实证      │
   「多了什么」        │  Tools/SysPrompt/CLAUDE.md/Plan/     │
                     │  Skills/Subagents/Hooks/Compaction   │
                     └─────────────────────────────────────┘
                                      ▲
                     ┌─────────────────────────────────────┐
   原型层（第一课）      │  Agent Loop + 3 个工具 + 系统提示词    │
   「最小内核」        │  193 行 Python                       │
                     └─────────────────────────────────────┘
```

### 三条贯穿始终的主线

#### 主线一：极简核心，复杂外围

- **第一课**：双层 while 循环 + 3 个工具 = 能跑的 agent
- **第二课**：讲师反复强调"更少但更强大的工具"，Bash/SQL 这类"瑞士军刀"优于几十个专用工具；并从 110 个工具的 GitHub MCP server 讲到 Claude 的极简化
- **论文**：核心是"**一个简单的 while 循环**"；真正的共享代码路径是 loop 函数而非 engine 类；**大部分代码活在循环周围的系统里**

> **一句话**：**核心保持薄，复杂度放在外围的能力上，而不是放在决策脚手架里。**

#### 主线二：上下文是最稀缺的资源

这是三份材料里出现频率最高的主题，也是**最容易被初学者忽视的**：

| 材料 | 相关论述 |
|------|---------|
| 第一课 | `conversation` 列表无限增长，撞到上限就完——**原型的最大缺陷** |
| 第二课 | 工具定义全量注入；MCP 工具全量常驻；"dumb zone"；系统提示词从 250 行砍到 50 行；CLAUDE.md 不要过度约束 |
| 论文 | 五层压缩管线；CLAUDE.md 惰性加载；工具 schema 延迟加载；子代理只回摘要；单工具结果预算上限 |

> **实践结论**：**你往上下文里塞的每一段内容，都在和任务本身争夺模型的注意力。** 精简不是偷懒，是性能优化。

#### 主线三："人的位置"被反复重新定义

- **第一课**：人在循环外——打字、看结果。反馈全靠人肉。
- **第二课**：Plan Mode 让人参与方案设计；Subagents 让人学会"委派"；抓包让人能**看见**看不见的东西。
- **论文**：
  - **Human Decision Authority** 是价值观第一位；
  - 但发现"**93% 都点同意**"后，选择**重构问题**而非加警告——从"逐动作审批"转向"划定边界后的自由"；
  - 信任是**渐变谱系**（20% → 40%+ 的自动批准率增长），而非固定状态；
  - 并留下那个尖锐的元问题：**我们会因为过度依赖而失去监督它的能力吗？**

### 课程说的 vs 论文证的：交叉验证

三份材料来自不同视角（讲师现场抓包 / 论文读源码），**能互相印证的地方最可信，有出入的地方最值得细读**。下表把课程里的主要论断逐条对照论文：

| # | 课程里的说法 | 论文里的证据 | 判断 |
|---|-------------|-------------|------|
| 1 | **工具定义（名字/描述/签名）全量注入上下文**（课程 2） | 论文 §6：`assemble()` 注入 `tool_schemas`；MCP 的上下文成本为**高**；并有 **ToolSearch 延迟加载 schema** 作为缓解 | ✅ 一致；论文补充了"延迟加载"这个**缓解手段**，课程没提 |
| 2 | **内置约 40 个工具** | **最多 54 个**（19 无条件 + 35 条件）；简单模式仅 3 个 | ⚠ **口径差异**：本质是"工具集按构建/模式动态装配"；课程说的是讲师那次抓包的实际数量 |
| 3 | **系统提示词由 harness 设定，"你不控制"** | §7.1：系统提示词**包含输出风格修改和 `--append-system-prompt` 追加内容** | ⚠ **课程说法偏绝对**：用户**并非完全无法影响**系统提示词，只是不能直接编辑那个基础块 |
| 4 | **CLAUDE.md 是用户可控的那一半，"优先于其他命令"**（课件）；trace 里带 *"override default behavior"* 声明 | §7.2：CLAUDE.md 作为 **user 消息**交付，**模型遵从是概率性的而非保证的**；强制要靠权限规则 | ⚠ **重要细节**：课件的"优先"是**文本里的措辞**，不是**机制上的保证**——**"绝对不能做"的事不能只写在 CLAUDE.md** |
| 5 | **CLAUDE.md 在 trace 里出现在第一条 user 消息上方** | §7.1：用户上下文通过 `prependUserContext()` **前置到消息数组**，与系统提示词占据**不同的结构位置** | ✅ **完美吻合**，是课程抓包与论文源码的**直接互证** |
| 6 | **Skills = 渐进式披露**（只放元数据，需要时加载全文） | Table 2：Skills 上下文成本**低**，"提示词里只保留 frontmatter 描述" | ✅ 一致；论文进一步给出了**成本阶梯** |
| 7 | **Subagent：全新上下文、可并行、token 成本上升、结果回传父级** | §8：独立上下文、**sidechain 转录**、**仅返回最终响应文本**；agent teams **约 7× token** | ✅ 一致，论文**量化了代价** |
| 8 | **Compaction：自动/手动触发、有损、用摘要替换历史** | §4.3 / §7.3：**五层管线**，auto-compact 是**最后一层**；**压缩不修改转录，只追加边界事件**；摘要阻塞且**非确定性** | ✅ 一致；⚠ 论文揭示**"压缩"远不止"摘要替换"一种** |
| 9 | **Plan mode = 进入/退出两个工具 + 注入的提示块 + plan 文件**；"制定规格" | §5.1：`plan` 是一种**权限模式**（模型必须先做计划、批准后才执行）；`Plan` 还是一种**内置子代理类型** | ⚠ 综合两份材料，plan **同时出现在三个层面**（工具+提示块 / 权限模式 / 子代理类型），课程只讲了其中的"工具+提示块"侧面 |
| 10 | **Hooks：在生命周期插入提示词或代码；前/后处理**（只点到为止） | §6：**27 个事件**、4 种命令类型、**5 个参与权限流程** | ✅ 一致；论文给出了课程没展开的**完整面貌** |
| 11 | **更少、更强大的工具**；Claude Code 靠"极简 harness"流行 | §12.1：**约 1.6% 是决策逻辑**；简单模式只有 Bash/Read/Edit | ✅ 一致，且有**量化支撑** |
| 12 | **记忆用 flat files，RAG 不一定更好** | §7.2：**不用 embedding**，**LLM 扫描文件头选最多 5 个文件**，文件粒度 | ✅ **源码证据直接支持**讲师的说法 |
| 13 | **harness 的可见性不是很大的攻击面**（针对"能否覆盖系统提示词"的回答） | §12.3：**信任前初始化 CVE**、**>50 子命令回退** | ⚠ **不矛盾但视角不同**：讲师说的是"看到 harness 内部"的风险；论文说的是"**harness 实现本身有漏洞**"——两件事 |
| 14 | **（第一课）无工具调用 = 本轮结束** | §4.5：**主停止条件**，另有 4 个 | ✅ 一致；生产版多了 maxTurns、溢出、钩子、中止 |
| 15 | **（第一课）`tool_result` 以 `user` 角色回灌** | §4.2：`normalizeMessagesForAPI()` **只保留 user 类型消息**；结果按**请求顺序**缓冲 | ✅ 一致 |
| 16 | **dumb zone / 工具膨胀会让 agent 变差** | §3.6：**上下文是瓶颈**；**单个工具结果有预算上限** | ✅ 一致 |

> **版本口径提醒**：论文分析的是 **Claude Code v2.1.88 快照**（取自公开 npm 包提取），而课程抓包用的是**讲座当周的 Claude Code + Opus 5.5**——两者**版本不同**，工具数量、系统提示词长度等具体数字有出入属于正常。论文还提到 v2.1.88 之后的发展（如 v2.1.154 的**动态工作流**），说明**这个系统在快速变化，文中数字都是"快照"**。

---

## 5. 实践清单：设计自己的 Agent 时该问的问题

把课程内容转化为可执行的检查清单：

### 5.1 工具设计

- [ ] 我能不能用**更少**的工具覆盖同样的能力？（考虑 Bash/SQL 式的"通用工具"）
- [ ] 每个工具的 **docstring 和参数类型**够清晰吗？（记住：它们会逐字进入上下文）
- [ ] 工具的输出会不会**过大**？需要截断或摘要吗？
- [ ] 我在引入多少 MCP 工具？**每一个都会常驻上下文**——真的都需要吗？

### 5.2 提示词与配置

- [ ] 系统提示词里有多少是**模型早就知道**的？（想想哪些可以删）
- [ ] 我的 `CLAUDE.md` / `AGENTS.md` 是不是**写太长**了？——给 1–2 条精确命令，而不是一本说明书
- [ ] 我是不是在**过度约束**系统，而不是给它判断空间？

### 5.3 上下文管理

- [ ] 上下文快满时会发生什么？有压缩机制吗？
- [ ] 压缩是**有损**的——什么信息绝对不能丢？
- [ ] 有没有可以做**惰性加载**的东西（配置、工具 schema、文档）？
- [ ] 有没有大任务可以**交给子代理**，只把摘要带回来？

### 5.4 安全与信任

- [ ] 默认是**拒绝**还是允许？拒绝规则是否优先于允许规则？
- [ ] 只读/可逆的操作，是否需要**同等强度**的审批？
- [ ] 我的审批机制会不会**被用户逐渐无视**？（想想那个 93%）
- [ ] 会话恢复时，之前的信任状态该不该继承？（论文的答案：不该）

### 5.5 可观测性

- [ ] 我能**看见**每次请求实际发了什么吗？（想想讲师的抓包代理）
- [ ] 当 agent 表现不如预期时，我有手段定位是**哪一段上下文**导致的吗？

### 5.6 扩展机制设计（来自论文 §6）

- [ ] 我要加的扩展，是在改变模型**"看到什么"（assemble）**、**"能做什么"（model）**，还是**"能不能做"（execute）**？对应的**上下文成本**是多少？
- [ ] 能不能用**零上下文成本**的方式（**钩子**）解决，而不是再加一个常驻的 MCP 工具？
- [ ] 一个领域流程应该做成 **Skill（低成本、教模型怎么想）** 还是 **MCP 工具（高成本、给新能力）**？
- [ ] 如果要分发给别人：我是否需要**插件**这种**打包层**？

### 5.7 权限与安全（来自论文 §3.5 / §5 / §12.3）

- [ ] 我的审批机制是否**依赖用户的警觉**？（93% 的批准率说明它不可靠）
- [ ] **deny 是否永远优先于 allow**？有没有"更具体的 allow 覆盖了宽泛 deny"的漏洞？
- [ ] 被禁用的工具，是**到调用时才拒绝**，还是**一开始就从模型视野里移除**？（后者更好：模型不会浪费调用）
- [ ] **拒绝**是否只是"停止"？还是**把拒绝原因返回给模型，让它换个安全的方案**？
- [ ] 沙箱与权限是否**独立**？（授权 ≠ 隔离）它们**共享什么故障模式**？（想想 50 子命令回退）
- [ ] 项目初始化时执行的代码（钩子、MCP 连接、设置解析）**是否发生在用户确认信任之前**？（论文的 CVE 教训）
- [ ] 会话恢复时，**权限是否被静默继承**？
- [ ] **"绝对不能做"的约束**写在哪？如果只写在 CLAUDE.md/提示词里，**模型遵从是概率性的**

### 5.8 子代理与多 agent（来自论文 §8）

- [ ] 子代理的提示是否**自包含**？（默认**不继承**父级历史）
- [ ] 隔离选哪种：**进程内（轻）/ worktree（文件隔离）/ 容器（强）**？
- [ ] 子代理应该只回**摘要**吗？要不要把完整历史存成 **sidechain 文件**以便审计？
- [ ] 并行 agent 会不会**各自重新实现同一个东西**？（论文预测的"模式重复"风险）
- [ ] token 成本是否可接受？（agent teams 约 **7×**）

### 5.9 持久化与恢复（来自论文 §9）

- [ ] 会话记录是**追加式**吗？能否 **resume / fork / rewind**？
- [ ] 压缩是**修改历史**还是**只追加边界标记**？后者让审计和回放成为可能
- [ ] 哪些信息属于"**文件级检查点**"（可回退文件改动），哪些属于"**会话记录**"？别把它们混为一谈

### 5.10 评估与长期能力（来自论文 §12–13）

- [ ] agent 的失败是**会报错**还是**静默**？我有没有**生成-评估分离**的校验？
- [ ] 我关注的指标是**通过率**，还是也包括**token 用量、文件重复访问、复杂度趋势**？
- [ ] 我有没有机制**防止自己（和团队）的理解力退化**？（"你可以外包你的思考，但不能外包你的理解"）
- [ ] "完成"的判据是**外部验证器**，还是只是模型的一句流畅收尾？

---

## 6. 动手练习（延伸建议，非课程原文）

> 本章是我基于课程与论文设计的**练习路线**，**不是课程官方作业**（官方作业 1 是"抓包拆解"，见 2.14）。每个练习都给出**验收标准**，难度递增。

### 练习 1：跑通 193 行的 Agent（30 分钟）

1. 准备环境：Python **3.12+**、`pip install openai python-dotenv`、`.env` 里写 `OPENAI_API_KEY`；
2. 把 `execute_llm_call` 里的模型名换成你**账号上实际可用的**；
3. 在一个**临时空目录**里运行，复现视频里的三个演示（读文件 / 列目录 / 创建并编辑 `hello.py`）。

**验收**：能让 agent **自主完成"先 `read_file` 再 `edit_file`"的两步链**，并能解释每一步 `conversation` 里多了哪些消息、角色是什么。

### 练习 2：加一个 `run_shell` 工具，并让拒绝可被模型"读到"（1 小时）

```python
import subprocess

DENY = ["rm -rf /", "mkfs", ":(){"]          # 示意：真实系统请用白名单 + 沙箱

def run_shell_tool(command: str) -> Dict[str, Any]:
    """
    Runs a shell command in the current working directory and returns its output.
    :param command: The shell command to run.
    :return: A dict with stdout, stderr (each truncated to the last 4000 chars) and the exit code.
    """
    if any(bad in command for bad in DENY):
        return {"error": "command denied by policy; try a safer alternative"}
    r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
    return {"stdout": r.stdout[-4000:], "stderr": r.stderr[-4000:], "exit_code": r.returncode}

# 1) TOOL_REGISTRY["run_shell"] = run_shell_tool
# 2) 在主循环里加: elif name == "run_shell": resp = tool(args.get("command", ""))
```

这个小练习里**同时包含了论文的三个思想**：**docstring 即提示词**（第一课）、**拒绝以"消息"形式返回，让模型自己换方案**（论文 3.5.4 的"拒绝即路由信号"）、**`[-4000:]` 截断就是"单个工具结果的预算上限"**（论文 3.4.4 的 budget reduction）。

**验收**：让它执行 `ls`（成功）、`rm -rf /`（被拒并看到模型改变做法）、一个输出超长的命令（输出被截断，上下文没被撑爆）。

### 练习 3：实现 deny-first 的规则评估与"三态审批"（1–2 小时）

```python
from fnmatch import fnmatch

RULES = {
    "deny":  ["run_shell:rm *", "edit_file:/etc/*"],
    "ask":   ["run_shell:*", "edit_file:*"],
    "allow": ["read_file:*", "list_files:*"],
}

def decide(tool: str, arg: str) -> str:
    key = f"{tool}:{arg}"
    for verdict in ("deny", "ask", "allow"):   # 顺序即优先级：deny > ask > allow
        if any(fnmatch(key, pat) for pat in RULES[verdict]):
            return verdict
    return "ask"                                # 无法识别 → 升级给人，而不是静默放行
```

把 `decide` 插到"执行工具"之前：`deny` 直接返回拒绝消息；`ask` 调 `input()` 让你确认；`allow` 直接执行。

**验收**：构造一个"**宽泛 deny + 更具体的 allow**"冲突的规则集，证明 deny 仍然赢；再统计你**连续批准多少次后开始不看就按回车**——**亲自体验 93% 的"审批疲劳"**。

### 练习 4：给 agent 加上下文压缩（2 小时）

```python
def maybe_compact(conversation, limit_chars=60000):
    if sum(len(m["content"]) for m in conversation) < limit_chars:
        return conversation
    head, middle, tail = conversation[:1], conversation[1:-6], conversation[-6:]
    ask = ("Summarize the key facts, decisions and file paths from the conversation so far:\n"
           + "\n".join(m["content"] for m in middle))
    summary = execute_llm_call(head + [{"role": "user", "content": ask}])
    return head + [{"role": "user", "content": f"[compacted summary]\n{summary}"}] + tail
```

在每次调用 LLM 之前执行 `conversation = maybe_compact(conversation)`。

> ⚠ 这个原型能工作，是因为第一课的协议里 `tool_result` 只是**普通 user 文本**；**如果你换成厂商的结构化 `tool_use`/`tool_result`，切分历史时必须保证二者成对，不能切开**。

**验收**：①让它读多个大文件把对话撑过阈值，观察压缩是否触发；②压缩后问它"之前读过哪个文件"，检查**哪些信息丢了**；③对照论文，思考**你的单层压缩缺了五层管线里的哪几层**（budget、snip、microcompact、collapse）。

### 练习 5：抓包拆解（官方作业 1 的自测版，2–4 小时）

用 2.14.1 的思路抓一次 Claude Code 请求，然后**填这张表**：

| 请求中的块 | 来源（用户 / harness 注入 / 模型 / 工具结果） | 大约字符数 | 它在起什么作用 |
|-----------|------------------------------------------|-----------|---------------|
| `system` 第 1 块 | | | |
| `system` 第 2 块 | | | |
| `tools` 整体 | | | |
| CLAUDE.md 所在位置 | | | |
| 第一条 user 消息 | | | |
| `system-reminder` 类块 | | | |

**验收**：能回答①"**我没输入的东西占了多大比例**"；②"**如果删掉一个 MCP 服务器，请求体少了多少**"；③ 对照 3.7 的"九类来源"找到你能识别的几类。

### 练习 6：写一个 Skill，并观察"渐进式披露"（2 小时）

写一个最小的 `SKILL.md`（YAML frontmatter 含 `name`、`description`，正文是几步流程）。抓两次包：**未触发**时与**触发后**，比较**请求体大小**与**skill 内容出现的位置**。

**验收**：证明①**未触发时请求里只有描述**；②**触发后全文才进入上下文**；③ 说明为什么 **Skills 的上下文成本是"低"而 MCP 是"高"**。

### 练习 7：带着论文读源码（半天，进阶）

论文开源仓库 `VILA-Lab/Dive-into-Claude-Code` 有**伴随笔记**；社区也有重实现项目（见 3.15.5）。选一个你关心的主题（如**权限**），按论文给的**文件→职责**映射，**从 `permissions.ts` 追到 `useCanUseTool.tsx`**，验证 3.5.3 的"deny 永远赢"。

**验收**：能用自己的话画出**一个工具请求从 `tool_use` 到被执行/拒绝**的完整路径，并指出**哪几层可以阻断它**。

---

## 7. 术语表

| 术语 | 含义 | 本文位置 |
|------|------|---------|
| **Agent Loop** | "调用模型 → 执行工具 → 结果回灌 → 再调用"的循环，直到模型不再请求工具 | 1.1、3.4 |
| **Harness（脚手架/运行外壳）** | 包裹在 LLM 外面的一切：系统提示词、工具、配置文件、模式、子代理、技能、钩子、压缩…… | 2.1 |
| **Context window（上下文窗口）** | 模型一次能看到的全部 token；Claude Code 里老模型 200K、4.6 系列 1M | 3.7 |
| **Tool（工具）** | 模型接触外部世界的唯一通道；定义（名字/描述/签名）**全部进入上下文** | 2.2 |
| **tool_use / tool_result** | 模型发出工具调用 / harness 返回执行结果的消息块 | 3.4 |
| **System prompt（系统提示词）** | harness 静态设定的行为蓝图；每次请求都带 | 2.3 |
| **CLAUDE.md / AGENTS.md** | 用户可控的项目指令文件，**以 user 消息**注入；遵从是概率性的 | 2.4、3.7 |
| **Plan mode（计划模式）** | 先制定计划再执行的模式；既是提示块、也是权限模式、也是子代理类型 | 2.5、3.5 |
| **Skill（技能）** | 带 frontmatter 的 `SKILL.md`，描述一段书面操作流程；**渐进式披露** | 2.6、3.6 |
| **Subagent（子代理）** | 通过显式工具调用启动、拥有**全新上下文**的 worker，只回摘要 | 2.7、3.8 |
| **Hook（钩子）** | 在 harness 生命周期各点插入的代码/提示；27 种事件 | 2.8、3.6 |
| **Compaction（压缩）** | 用摘要替换历史；有损；Claude Code 是**五层管线** | 2.9、3.4 |
| **MCP** | Model Context Protocol，外部工具/资源接入协议；是"最小原语"；上下文成本**高** | 2.2、3.6 |
| **LSP** | Language Server Protocol，语言服务器协议，用于理解代码语义 | 2.12 |
| **ReAct** | 推理-行动循环模式；Claude Code 采用反应式循环 | 3.4 |
| **Progressive disclosure（渐进式披露）** | 先放少量元数据，相关时再加载全文 | 2.2、3.6 |
| **Context engineering（上下文工程）** | 设计"往上下文里放什么、何时放"的学问 | 2.2、4 |
| **Dumb zone（变笨区）** | 上下文过长/过杂导致模型变得不那么有效的区间（非正式说法） | 2.10 |
| **Context bloat / tool bloat** | 上下文 / 工具数量膨胀 | 2.2 |
| **Deny-first（默认拒绝）** | deny 规则永远优先于 allow；无法识别则升级给人 | 3.5 |
| **Permission mode（权限模式）** | plan / default / acceptEdits / auto / dontAsk / bypassPermissions / bubble | 3.5 |
| **Auto mode classifier** | 用 ML 分类器代替人审批的模式 | 3.5 |
| **Approval fatigue（审批疲劳）** | 用户习惯性无脑批准（93%），使交互确认不可靠 | 3.5 |
| **Sandbox（沙箱）** | 独立于权限的文件/网络隔离；**授权 ≠ 隔离** | 3.5 |
| **Pre-trust initialization window** | 信任对话框之前就执行的初始化代码（钩子、MCP、设置解析）造成的漏洞窗口 | 3.12 |
| **Worktree** | git 临时工作树，用于子代理的文件隔离 | 3.8 |
| **Sidechain transcript** | 子代理独立的转录文件，不撑大父会话 | 3.8 |
| **Append-only JSONL** | 只追加的会话日志格式；偏可审计性而非查询能力 | 3.9 |
| **Resume / Fork / Rewind** | 回放转录恢复 / 分叉新会话 / 回退文件改动；**都不恢复会话权限** | 3.9 |
| **Budget reduction / Snip / Microcompact / Context collapse / Auto-compact** | 五个上下文塑形器，由轻到重 | 3.4 |
| **Read-time projection（读时投影）** | context collapse 的做法：不改历史，只改"模型看到的视图" | 3.4 |
| **ACP（Agent Client Protocol）** | 让外部 IDE/系统托管 agent 的协议 | 3.10 |
| **KAIROS** | 论文提到的特性开关控制的**主动式后台 agent**（tick 心跳），是否在生产启用**未确认** | 3.12 |
| **Orchestration-as-code（编排即代码）** | 模型写脚本编排大量子代理，中间结果不进上下文（动态工作流） | 3.14 |
| **AI slop** | AI 生成的低质量垃圾代码 | 1.4 |
| **Vibe coding** | 凭感觉让 AI 写、不细看的编码方式 | 2.0 |
| **Flat files memory** | 用纯文本文件做记忆，而非向量库/图 | 2.13、3.7 |
| **PEP 701** | Python 3.12 允许 f-string 内复用同种引号 | 1.2 |
| **Evidence tiers A/B/C** | 论文的证据等级：产品文档 / 代码验证 / 重构推断 | 3.15 |
| **1.6% / 98.4%** | 社区估算：决策逻辑占 1.6%，运行时基础设施占 98.4% | 3.12 |

---

## 8. 自测题

> 点击展开答案。先自己想，再看。

**Q1. 为什么说"没有工具调用的循环只是聊天机器人"？Agent 与聊天机器人的本质差别在哪？**
<details><summary>答案</summary>差别在于**把模型输出解析成动作并执行、再把结果回灌**。没有"解析 → 分发 → 回灌"，循环就只是"用户一句、模型一句"。视频 16:49–17:13 讲师演示了这一点。</details>

**Q2. 第一课的 `tool_result` 为什么用 `user` 角色？**
<details><summary>答案</summary>因为**工具是 harness 执行的、不是 LLM 执行的**——对话里"谁产生这条内容"谁就是那个角色；harness 在代表"外部世界"向模型发话，协议上归为 user。论文 §4.2 也说 `normalizeMessagesForAPI()` 只保留 user 类型消息。</details>

**Q3. `edit_file` 里 `old_str == ""` 表示什么？这个设计有什么好处与风险？**
<details><summary>答案</summary>表示**创建/覆盖文件**（讲师说"只是一个约定"）。好处：一个工具覆盖创建与修改；风险：**直接覆盖且无权限检查**，这就是后面需要权限系统的原因。</details>

**Q4. 为什么工具的 docstring 要写得非常明确？**
<details><summary>答案</summary>因为 `inspect.signature` 和 `__doc__` 会**逐字进入系统提示词**，模型"用 docstring 推理这个工具做什么、该不该用、什么时候用"。写 docstring = 写提示词。类型标注同理。</details>

**Q5. 画出 harness 的两类要素。**
<details><summary>答案</summary>**上下文输入**：System prompt、AGENTS.md、Tool list、Skills（往窗口里灌什么）；**harness 机制**：Compaction、Plan mode、Subagents（作用在循环上的控制）。中间是 Agent loop：Context window → Model → Tool execution。</details>

**Q6. MCP 与 Skills 的区别？各自的上下文成本？**
<details><summary>答案</summary>MCP 是**最小原语**（类似 API 调用），给模型新工具，**全量常驻**，成本**高**；Skills 把多步流程（提示+工具+脚本）封装起来，**只放 frontmatter 描述，触发时才加载全文**，成本**低**。</details>

**Q7. 系统提示词为什么从 200–250 行缩到 ~50 行？**
<details><summary>答案</summary>讲师推测**训练已把很多知识（如怎么用 Git）吸收进模型参数**；同时要**减少用户看不见却每次占用上下文的内容**，与减少 MCP 工具同理。</details>

**Q8. CLAUDE.md 该写什么、不该写什么？为什么？**
<details><summary>答案</summary>写 1–2 条**运行测试/启动服务器的精确命令**与项目结构概览；别写大段代码或事无巨细的说明——**过度约束会让系统"过拟合到你的指令"**。另外因为它是 user 消息，遵从是**概率性**的，硬约束要用权限规则。</details>

**Q9. subagent 为什么有用？代价是什么？**
<details><summary>答案</summary>**全新上下文**，探索发生在主流程之外，**只回摘要**，能并行；代价是 **token 成本上升**（论文：agent teams 约 7×）、提示词必须**自包含**、并行 agent 可能**重复实现**。</details>

**Q10. 压缩为什么要做成五层而不是一次摘要？**
<details><summary>答案</summary>**没有单一策略能应对所有上下文压力**：budget reduction 治单个超大输出；snip 治时间深度；microcompact 治缓存开销；context collapse 治极长历史；auto-compact 是最后手段的语义压缩。**由轻到重（懒降级）**，且 context collapse 用读时投影不改历史。</details>

**Q11. 为什么说"deny 永远赢"？举个例子。**
<details><summary>答案</summary>`deny` 规则先评估，**即使 allow 更具体也不能覆盖**：宽泛的 deny"禁所有 shell"不能被窄的 allow"允许 `npm test`"覆盖。完整顺序是 **deny > ask > allow**，无法识别的升级给用户。</details>

**Q12. 为什么 Anthropic 没有"加更多警告"来应对 93% 的批准率？**
<details><summary>答案</summary>因为**审批疲劳**使交互确认行为上不可靠。他们**重构问题**：划定边界（**沙箱、auto 分类器**）让 agent 在边界内自由工作，**把人必须做的决定减少约 84%**。</details>

**Q13. "权限被拒"在 Claude Code 里意味着什么？**
<details><summary>答案</summary>不是硬停止，而是**路由信号**：模型收到拒绝原因，**换一个更安全的方案**下一轮再试；`PermissionDenied` 钩子可观察。</details>

**Q14. 授权与隔离有什么区别？**
<details><summary>答案</summary>**授权**（权限系统）决定"该不该执行"；**隔离**（沙箱）决定"执行时能碰什么"。**命令可被批准但仍被沙箱限制，也可被拒绝而根本到不了沙箱**。二者在不同轴上，但可能**共享性能约束**（如 >50 子命令回退）。</details>

**Q15. 什么是"信任前初始化"漏洞？**
<details><summary>答案</summary>项目初始化时执行的代码（**钩子、MCP 连接、设置解析**）**先于交互式信任对话框运行**，落在 deny-first 评估之外，形成**结构性特权窗口**（CVE-2025-59536 等）。教训：**扩展加载 → 信任对话框 → 权限执行**的顺序制造了漏洞窗口。</details>

**Q16. 为什么 resume/fork 不恢复权限？**
<details><summary>答案</summary>会话是**隔离的信任域**；恢复旧授权会把**陈旧的信任决定带进已变化的上下文**。选择"重新授予"，接受用户摩擦以维持"**信任总是在当前会话中建立**"。</details>

**Q17. Skills、Hooks、MCP、Plugins 的上下文成本阶梯？**
<details><summary>答案</summary>**Hooks 零（默认）→ Skills 低（仅描述）→ Plugins 中（视内容）→ MCP 高（工具 schema）**。便宜的可大量铺开，贵的留给真需要新工具面的场景。</details>

**Q18. 论文说 Claude Code 只有约 1.6% 是决策逻辑，这说明了什么？**
<details><summary>答案</summary>**复杂度在 harness（98.4%），不在"决策脚手架"**：模型被当作无状态补全端点，**harness 为模型的判断创造条件而非约束它**。与课程"极简核心 + 复杂外围"呼应。</details>

**Q19. 模型越强，harness 越没用吗？**
<details><summary>答案</summary>不。变的只是**决策脚手架**（规划/控制逻辑）；**可靠执行（上下文/恢复）、安全、人的决策权、情境适应、token 经济学**都不随模型变强而消失，**安全甚至更重要**。实证：仅换 harness 就能让同一模型得分变动最多 18 分。</details>

**Q20. 论文认为最重要的开放问题是什么？**
<details><summary>答案</summary>**不是如何加更多自治，而是如何随时间保住人的能力**。现有架构只有有限机制保护长期理解力、代码库一致性与开发者成长管道，**应把"可持续性缺口"视为一等设计问题**。</details>

**Q21. 为什么抓包看到的内容不等于模型最终看到的？**
<details><summary>答案</summary>请求体是"**原始形式**"，**服务器端 token 化之前几乎肯定还有折叠/压缩/转换**；要看到那一步需要在模型服务器上，而那可能是"他们的秘方"。</details>

**Q22. 课程 1 的视频代码与发布代码有哪些差异？**
<details><summary>答案</summary>`chat.completions` vs `responses`；`GPT-5` vs `gpt-5.6-terra`；`max_completion_tokens=2000` vs `max_output_tokens=5000`；`system` vs `developer`；解析用 `json.loads` vs `raw_decode`；视频约 207–208 行 vs 发布 193 行。见 1.6。</details>

---

## 附录：资料索引

> **取材边界与覆盖情况**见 **0.3**。本附录列出归档文件、外部链接和论文引用的延伸阅读。

### A. 课程配套资料（已随本文归档于 `课程原始资料/`）

| 文件 | 说明 |
|------|------|
| `课程1课件_200行代码搭建Claude Code.pdf` | Lecture 9/22 课件，15 页（中英对照） |
| `课程2课件_现代Coding Agent的解剖.pdf` | Lecture 9/24 课件，17 页（中英对照） |
| `coding_agent_from_scratch.py` | 课程 1 随课代码（193 行） |
| `课程1视频转写_英文原声_Whisper-large-v3.txt` | **课程 1 视频（44:30）完整转写**，带时间戳，机器转写 |
| `课程2视频转写_中文配音_Whisper-large-v3.txt` | **课程 2 视频（28:28，中文配音精编版）完整转写**，机器转写，错字较多 |
| `课程2逐字稿_英文原稿.txt` | 课程 2 官方英文逐字稿（约 57 分钟课堂） |
| `阅读材料_Dive into Claude Code(arXiv 2604.14228).pdf` | 指定阅读论文，53 页 |
| `课程1相关代码_GoogleDrive.py` | 课程 1 的 Google Drive 代码，**与 `coding_agent_from_scratch.py` 的 MD5 完全相同** |
| `课程2提示词原文/system_prompt.md` | 真实的系统提示词（55 行） |
| `课程2提示词原文/tool_list.md` | 真实工具清单（10 类 36 个） |
| `课程2提示词原文/plan_mode.md` | Plan Mode 提示词（五阶段工作流） |
| `课程2提示词原文/subagent_prompt.md` | 真实子代理任务提示（性能分析） |
| `课程2提示词原文/compaction_prompt.md` | 压缩提示词（analysis + summary 两段式） |
| `课程2提示词原文/config_files.md` | 真实的 `CLAUDE.md`（todo 项目） |

> 视频本体（两个 MP4）**没有**随附，只保留转写稿；如需视频，请到平台观看。

### B. 外部链接（课程页面提供）

| 资源 | 链接 |
|------|------|
| 课程网站 | https://themodernsoftware.dev |
| 课程 2 英文逐字稿 | https://themodernsoftware.dev/materials/9-24-26-transcript.txt |
| 作业仓库 | https://github.com/mihail911/modern-software-dev-assignments |
| 课程 1 相关代码（**已获取**，与随课代码相同） | https://drive.google.com/file/d/1DxKa_autBOu9s8DvItodgUAwH_pBg7aR/view?usp=drive_link |
| 课程 2 相关 prompt（**已获取**，6 份原文） | https://drive.google.com/drive/folders/1c6_atVW0RrqEBWsNIscG2KNwCiuPxWQG |
| 论文开源仓库（含设计空间伴随笔记） | https://github.com/VILA-Lab/Dive-into-Claude-Code |
| 课程管理员 | 王盈（wangying@corp.netease.com） |

### C. 论文对比与重实现的开源项目

| 项目 | 链接 |
|------|------|
| OpenClaw（多渠道个人助理网关） | https://github.com/openclaw/openclaw |
| Hermes Agent（Nous Research） | https://github.com/NousResearch/hermes-agent |
| ClawCodex（Python 移植） | https://github.com/agentforce314/clawcodex |
| Claw Code（Rust 重写） | https://github.com/ultraworkers/claw-code |
| claude-code-working（TS/Bun） | https://github.com/777genius/claude-code-working |
| Claude Code Source: Buildable Research Fork | https://github.com/T-Lab-CUHKSZ/claude-code |
| Open Claude Code（JS/npm） | https://github.com/ruvnet/open-claude-code |

### D. 论文第 11–13 节引用的部分延伸阅读

> 以下条目与链接**取自论文参考文献表**，**我没有逐一访问核验**；arXiv 编号请以原文为准。

**Anthropic / OpenAI 的工程文章**

| 主题 | 链接 |
|------|------|
| Building Effective Agents（5 种 workflow 模式） | https://www.anthropic.com/research/building-effective-agents |
| Claude Code 沙箱：Beyond permission prompts（**减少约 84% 的提示**） | https://www.anthropic.com/engineering/claude-code-sandboxing |
| Claude Code auto mode（**93% 批准率**的出处） | https://www.anthropic.com/engineering/claude-code-auto-mode |
| Measuring AI agent autonomy in practice（**20%→40%+ 自动批准率**） | https://anthropic.com/research/measuring-agent-autonomy |
| How AI is transforming work at Anthropic（132 名工程师调研） | https://anthropic.com/research/how-ai-is-transforming-work-at-anthropic |
| Harness design for long-running application development | https://anthropic.com/engineering/harness-design-long-running-apps |
| Scaling managed agents: Decoupling the brain from the hands | https://www.anthropic.com/engineering/managed-agents |
| How Claude Code works（官方文档） | https://code.claude.com/docs/en/how-claude-code-works |
| How Claude remembers your project（记忆文档） | https://code.claude.com/docs/en/memory |
| OpenAI：Harness engineering | https://openai.com/index/harness-engineering/ |
| Osmani：Loop engineering | https://addyosmani.com/blog/loop-engineering/ |
| Huyen：Agents（复合错误 95%^100≈0.6%） | https://huyenchip.com/2025/01/07/agents.html |
| Weng：LLM-powered autonomous agents | https://lilianweng.github.io/posts/2023-06-23-agent/ |

**实证研究（开发者能力与代码质量）**

| 研究 | arXiv |
|------|-------|
| Becker et al.：16 位资深开发者 RCT，**慢 19% 却感觉快 20%** | 2507.09089 |
| He et al.：Cursor 采用对 807 个仓库复杂度的影响（**+40.7%**） | 2511.04427 |
| Kosmyna et al.：*Your brain on ChatGPT*（EEG） | 2506.08872 |
| Shen & Tamkin：*How AI impacts skill formation*（**理解测试低 17%**） | 2601.20245 |
| Liu et al.：304,000 个 AI 提交的审计 | 2603.28592 |
| Trivedi & Schmitt：代码整洁度对 coding agent 的影响（最小对研究） | 2605.20049 |
| Aiersilan：*The vibe-check protocol*（认知卸载度量） | 2601.02410 |

**架构、上下文、记忆、评估**

| 研究 | arXiv |
|------|-------|
| Hu et al.：*Memory in the age of AI agents* | 2512.13564 |
| Zhang et al.：*Agentic context engineering* | 2510.04618 |
| Cim et al.：并行上下文压缩（摘要的阻塞与非确定性） | 2605.23296 |
| Ding et al.：*WildClawBench*（**换 harness 最多差 18 分**） | 2605.10912 |
| Sui et al.：**PASTE**（推测式工具执行） | 2603.18897 |
| Cai et al.：*Push your agent*（长程目标持久性） | 2605.23574 |
| Ning et al.：*Code as agent harness* | 2605.18747 |
| Pan：*Agent-first tool API* | 2605.10555 |
| Xu：*AI agent systems: architectures, applications, and evaluation* | 2601.01743 |
| Xu et al.：*MemGym* | 2605.20833 |
| Hu et al.：*Automated design of agentic systems* | 2408.08435 |

**安全与治理**

| 研究 | arXiv / 链接 |
|------|-------------|
| International AI Safety Report 2026 | 2602.21012 |
| The 2025 AI Agent Index（**仅 13.3% 发布 agent 安全卡**） | 2602.17753 |
| Boiling the Frog：多轮 agentic 安全基准 | 2605.22643 |
| Nannini et al.：*AI agents under EU law* | 2604.04604 |
| Check Point：*Caught in the hook*（CVE-2025-59536 / CVE-2026-21852） | https://research.checkpoint.com/2026/rce-and-api-token-exfiltration-through-claude-code-project-files-cve-2025-59536/ |
| Adversa.ai：deny 规则因成本过高被静默绕过（>50 子命令） | https://adversa.ai/blog/claude-code-security-bypass-deny-rules-disabled/ |
| NSA：MCP 安全设计考量 | https://www.nsa.gov/Portals/75/documents/Cybersecurity/CSI_MCP_SECURITY.pdf |

### E. 课程提到的其他资源

- **MCP（Model Context Protocol）**——外部工具/资源集成协议；**2025 年捐赠给 Linux Foundation 新成立的 Agentic AI Foundation（AAIF）**，与 goose、`AGENTS.md` 一同作为初始锚定项目；
- **对比系统**：OpenClaw、Hermes Agent；
- **替代设计家族**：LangGraph（规则编排）、SWE-Agent / OpenHands（容器隔离）、Aider（版本控制即安全）；
- **课程 OSS 合作伙伴**：见 0.1。

### F. 本文的已知局限（诚实清单）

1. ~~缺两份补充材料~~ → **已补齐**：课程 1 的 Google Drive 代码经 MD5 校验**与随课代码完全相同**；课程 2 的 6 份提示词原文**已全文读入**并写入 2.12.6；
2. **两段视频是机器转写**：英文版质量好，中文配音版错字多，**已以英文逐字稿为准**；视频里的**画面**（讲师的 IDE、抓包界面）**没有逐帧分析**，只依据语音与转写；
3. **课件中文翻译是看图转录**，可能有细微出入；
4. **论文的图（Figure 1–9）**只能依据图内文字与正文描述还原，**没有逐像素阅读**；
5. **论文引用的外部文献未逐篇核验**；
6. **文中所有"意译"的讲师原话**不是逐字翻译；
7. **时间线中的日期是估算**（讲师多为口头说"几周前/大约一个月前"）；
8. **没有运行课程代码**——1.7 与 6 章中的代码是**示意与建议**，请在**隔离环境**中验证后再使用；
9. **论文分析的是 v2.1.88 快照**，Claude Code 变化很快，**具体数字会过时**。

---

## 附：课程原始简介

> 本课程从"Coding Agent 到底是怎么工作的"出发，带你从一个最小可运行的 Agent，一路看到生产级 AI Coding 工具背后的设计逻辑。
>
> 课程首先通过搭建一个简化版 Coding Agent，拆解 AI Agent 最核心的运行机制：大语言模型如何通过 Agent Loop 持续理解任务、调用工具并根据执行结果进行下一步判断，以及 read、write、edit、shell 等基础工具如何让模型真正具备读取代码、修改文件和执行命令的能力。
>
> 在此基础上，课程进一步进入生产级 Coding Agent 的设计，重点理解 system prompt 与工具定义如何影响 Agent 的行为，包括角色与任务边界、工具使用规则、环境信息、项目上下文以及长任务中的行为约束。课程也会讨论成熟 Coding Agent 如何通过持续补充上下文和系统提醒，降低长流程执行中的偏移问题。
>
> 通过本课程，你将建立对 Coding Agent 的完整基础认知：**它并不是一个单纯"更会写代码"的大模型，而是一套由 LLM、Context、Tools、System Prompt 与 Agent Loop 共同构成的智能执行系统。**
>
> 学完这一课，你不仅能理解 Claude Code 等 AI Coding 工具为什么能够连续完成开发任务，也能为后续学习 Context Engineering、MCP、Agent Skills 和更复杂的 AI 原生开发工作流打下基础。

---

*本文由两节课的课件（15+17 页）、两段视频的完整转写（44:30 + 28:28）、官方逐字稿、随课代码，以及指定阅读论文（53 页）综合整理。代码片段引自课程随课源码 `coding_agent_from_scratch.py`，第 6 章的代码为延伸示例。*
