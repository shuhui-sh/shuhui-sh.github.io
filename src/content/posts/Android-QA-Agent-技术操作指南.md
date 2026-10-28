---
title: "Android QA Agent 技术操作指南"
date: 2026-04-08
description: "android-qa-agent 是一个基于 Claude Code + ADB 的 Android UI 自动化测试工具。"
tags: ['AI', 'Agent', 'Android']
category: "技术"
---
## 一、概述

android-qa-agent 是一个基于 Claude Code + ADB 的 Android UI 自动化测试工具。它的核心模式是 **录制-回放-验证（Record-Replay-Verify）**：

1. 用户用自然语言描述测试场景
2. Claude Code 通过 ADB 在真实设备上执行操作，每一步都被透明记录
3. 录制产物可以倍速回放，并由 AI 进行截图对比验证

工具本身只有 4 个 Python 脚本，没有复杂依赖，核心逻辑清晰。

> 项目地址：https://github.com/tobrun/android-qa-agent

---

## 二、环境准备

### 2.1 前置条件

| 依赖 | 要求 |
|------|------|
| Python | 3.8+ |
| ADB | 在 PATH 中，或设置 `ANDROID_HOME` |
| 设备 | Android 模拟器运行中或真机 USB 连接 |
| Claude Code | 已安装并可用 |

### 2.2 安装

```bash
git clone git@github.com:tobrun/android-qa-agent.git
cd android-qa-agent
```

确认设备连接正常：

```bash
adb devices
# 应输出至少一个 device 状态的设备
```

### 2.3 项目结构

```
android-qa-agent/
├── android-qa              # ADB 代理，拦截并记录所有 ADB 命令
├── android-qa-replay       # 回放工具，支持倍速和 AI 验证
├── start-recording         # 开始录制会话
├── stop-recording          # 停止录制并归档
├── CLAUDE.md               # Claude Code 的行为指令
├── .claude/
│   ├── settings.json       # Stop hook，会话中断时自动归档
│   └── skills/             # Claude Code 技能定义
│       ├── start-recording.md
│       └── stop-recording.md
├── recordings/             # 已完成的录制产物（可提交 Git）
├── artifacts/              # 录制过程中的截图和 UI dump（临时文件）
└── .android-qa/
    └── active-session.json # 录制锁文件（仅录制期间存在）
```

---

## 三、核心操作流程

### 3.1 启动 Claude Code

```bash
cd android-qa-agent
claude
```

进入 Claude Code 交互界面后，直接用自然语言描述你的测试场景。

### 3.2 执行一次完整测试

以"添加联系人"为例，输入：

```
打开联系人应用，添加一个新联系人，姓名为 John Doe，电话号码为 +001 1234 5678
```

Claude Code 会自动执行以下步骤：

**Step 1: 会话初始化**

Claude 从你的提示词中提取关键信息：
- 解析出 session 名称：`add-contact-john-doe`
- 搜索目标包名：`adb shell pm list packages | grep contacts`
- 检测连接的设备（单设备自动选择，多设备交互选择）
- 调用 `./start-recording` 开始录制（自动 force-stop 并 clear data）

```bash
./start-recording add-contact-john-doe \
  --prompt "打开联系人应用，添加一个新联系人，姓名为 John Doe..." \
  --device emulator-5554 \
  --package com.google.android.contacts
```

**Step 2: 观察-行动循环**

这是工具最核心的工作模式，每一次交互都严格遵循：

```
截图（看当前画面） → UI dump（获取精确坐标） → 计算坐标 → 执行操作
```

具体地：

1. 截图，了解当前屏幕状态
2. 执行 `uiautomator dump`，获取 XML 格式的 UI 层级结构
3. 解析 XML，找到目标控件的 `bounds="[left,top][right,bottom]"`
4. 计算中心坐标 `x = (left+right)/2, y = (top+bottom)/2`
5. 通过 `./android-qa shell input tap x y` 点击

每个命令都通过 `android-qa` 代理执行，被透明记录到 JSONL 文件中。

**Step 3: 停止录制**

测试完成后 Claude 调用 `./stop-recording`，产物归档到 `recordings/add-contact-john-doe/`：

```
recordings/add-contact-john-doe/
├── recording.json       # 完整命令记录 + 元数据
├── golden.png           # 最后一张截图（向后兼容）
├── golden-001.png       # 第 1 个检查点截图
├── golden-002.png       # 第 2 个检查点截图
└── ...
```

### 3.3 回放与验证

**基本回放**（按原始时间间隔执行）：

```bash
./android-qa-replay add-contact-john-doe
```

**5 倍速回放**：

```bash
./android-qa-replay add-contact-john-doe --speed 5
```

**回放 + AI 视觉验证**：

```bash
./android-qa-replay add-contact-john-doe --speed 5 --verify
```

验证过程：
1. 回放时自动跳过截图/UI dump 等"观察类"命令，只重放交互命令
2. 在每个检查点暂停，截取当前屏幕
3. 调用 `claude -p`（headless 模式）对比 golden 截图和 actual 截图
4. 生成 `verify.json` 报告

验证报告示例：

```json
{
  "pass": true,
  "summary": "3/3 步骤通过",
  "steps": [
    {
      "step": 1,
      "pass": true,
      "reasoning": "两张截图都显示联系人应用的新建联系人表单已打开",
      "golden_screenshot": "golden-001.png",
      "actual_screenshot": "actual-001.png"
    }
  ]
}
```

AI 会自动忽略状态栏时间、电量等无关差异。

**指定设备回放**：

```bash
./android-qa-replay add-contact-john-doe --device emulator-5556
```

---

## 四、测试不同 App 的组织方法

### 4.1 命名规范

每次测试的 session name 是录制产物的目录名，建议采用 `<app>-<功能>` 的命名格式：

| App | 测试场景 | Session 名称 |
|-----|---------|-------------|
| 联系人 | 添加联系人 | `contacts-add-john-doe` |
| 时钟 | 设置闹钟 | `clock-set-alarm-7am` |
| 设置 | 切换暗色模式 | `settings-toggle-dark-mode` |
| 地图 | 搜索地点 | `maps-search-location` |
| 相机 | 拍照 | `camera-take-photo` |

最终目录结构：

```
recordings/
├── contacts-add-john-doe/
│   ├── recording.json
│   ├── golden.png
│   └── golden-001.png
├── clock-set-alarm-7am/
│   ├── recording.json
│   ├── golden.png
│   └── golden-001.png
├── settings-toggle-dark-mode/
│   ├── recording.json
│   └── golden.png
└── maps-search-location/
    ├── recording.json
    └── golden.png
```

### 4.2 逐个 App 录制

每个测试场景是一次独立的 Claude Code 对话。不需要手动调用脚本，只需在 Claude Code 中输入提示词：

**测试联系人应用：**

```
打开联系人应用，添加一个新联系人，姓名为 Jane Smith，电话号码为 +86 13800138000
```

**测试时钟应用：**

```
打开时钟应用，设置一个新闹钟，时间为早上 7:00，重复周一到周五
```

**测试设置应用：**

```
打开设置应用，切换暗色模式
```

**测试相机应用：**

```
打开相机应用，切换到视频模式，录制 3 秒钟，然后停止
```

每次 Claude Code 都会：
1. 自动查找对应的包名
2. 自动 force-stop + clear data（保证干净状态）
3. 执行操作并录制
4. 停止录制并归档

### 4.3 批量回放验证

录制完成后，可以写一个简单的 shell 脚本批量验证所有录制：

```bash
#!/bin/bash
# run-all-tests.sh
SESSIONS=(
  "contacts-add-john-doe"
  "clock-set-alarm-7am"
  "settings-toggle-dark-mode"
  "maps-search-location"
)

FAILED=0
for session in "${SESSIONS[@]}"; do
  echo "=== 回放测试: $session ==="
  ./android-qa-replay "$session" --speed 5 --verify
  if [ $? -ne 0 ]; then
    echo "失败: $session"
    FAILED=$((FAILED + 1))
  fi
  echo ""
done

echo "=== 结果: $((${#SESSIONS[@]} - FAILED))/${#SESSIONS[@]} 通过 ==="
exit $FAILED
```

---

## 五、测试同一 App 的不同功能模块

### 5.1 组织策略

对于同一个 App 的不同功能模块，建议用 `<app>-<module>-<action>` 的三段式命名：

以联系人应用为例：

```
recordings/
├── contacts-add-basic/          # 添加基本联系人
├── contacts-add-with-email/     # 添加带邮箱的联系人
├── contacts-edit-phone/         # 编辑联系人电话
├── contacts-delete/             # 删除联系人
├── contacts-search/             # 搜索联系人
├── contacts-favorites-add/      # 添加到收藏
└── contacts-share-contact/      # 分享联系人
```

### 5.2 功能覆盖矩阵

以设置应用为一个完整示例，规划测试矩阵：

| 模块 | 测试场景 | 提示词 | Session 名称 |
|------|---------|--------|-------------|
| 显示 | 切换暗色模式 | `打开设置，切换暗色模式` | `settings-display-dark-mode` |
| 显示 | 调整亮度 | `打开设置，将亮度调到最大` | `settings-display-brightness` |
| 显示 | 调整字体大小 | `打开设置，将字体大小改为大号` | `settings-display-font-size` |
| WiFi | 连接网络 | `打开设置，连接名为 "TestNet" 的 WiFi 网络` | `settings-wifi-connect` |
| WiFi | 断开网络 | `打开设置，断开当前 WiFi 连接` | `settings-wifi-disconnect` |
| 声音 | 调整音量 | `打开设置，将媒体音量调到 50%` | `settings-sound-volume` |
| 声音 | 设置铃声 | `打开设置，更换来电铃声` | `settings-sound-ringtone` |
| 存储 | 查看存储 | `打开设置，查看存储使用情况` | `settings-storage-check` |

### 5.3 有依赖关系的测试

某些测试有前后依赖（先创建、后编辑、再删除）。两种处理方式：

**方式 A：每次独立测试，使用 `--no-clear` 保留状态**

```
# 第 1 步：创建联系人
打开联系人应用，添加一个新联系人，姓名为测试用户，电话为 12345

# 第 2 步：编辑联系人（保留上一步数据）
打开联系人应用，不要清除数据，找到测试用户并将电话号码改为 67890

# 第 3 步：删除联系人（保留上一步数据）
打开联系人应用，不要清除数据，找到测试用户并删除该联系人
```

提示词中包含"不要清除"等关键词，`start-recording` 会自动添加 `--no-clear` 参数，跳过 clear data。

自动检测的 no-clear 关键词列表：
- `don't clear`
- `no clear`
- `preserve state`
- `keep data`
- `warm start`
- `without clearing`

**方式 B：在单次会话中完成完整流程**

```
打开联系人应用，按以下步骤执行：
1. 添加一个新联系人，姓名为测试用户，电话为 12345
2. 返回联系人列表
3. 打开测试用户，将电话号码修改为 67890
4. 返回并验证修改是否生效
5. 删除联系人测试用户
```

这种方式生成一个完整的录制文件，覆盖 CRUD 全流程。

### 5.4 带性能追踪的功能测试

在提示词中加入性能关键词即可自动启用，无需任何额外配置：

```
打开联系人应用，追踪性能，同时滚动浏览联系人列表
```

自动触发的关键词列表：

**性能采集关键词：**
- `track performance`（追踪性能）
- `capture metrics`（采集指标）
- `measure performance`（测量性能）
- `frame rate`（帧率）
- `jank`（卡顿）
- `memory usage`（内存使用）
- `performance metrics`（性能指标）
- `fps`（帧率）
- `frame drops`（掉帧）
- `rendering`（渲染）

**Perfetto trace 关键词：**
- `enable tracing`（启用追踪）
- `systrace`（系统追踪）
- `perfetto`
- `system trace`（系统追踪）
- `capture trace`（捕获追踪）
- `trace the app`（追踪应用）
- `tracing`（追踪）

可以组合使用：

```
追踪性能并启用 perfetto 追踪，同时滚动浏览相册
```

会话停止时自动采集：
- `dumpsys gfxinfo`：帧率数据（总帧数、jank 帧数、百分位帧时间）
- `dumpsys meminfo`：内存数据（Total PSS、Native Heap、Dalvik Heap）
- `dumpsys cpuinfo`：CPU 数据（总 CPU 占比、user/kernel 占比）

性能数据保存为 `performance.json`，Perfetto trace 保存为 `trace.perfetto-trace`，可在 https://ui.perfetto.dev 中查看。

---

## 六、录制产物详解

### 6.1 recording.json 结构

```json
{
  "metadata": {
    "name": "add-contact-john-doe",
    "started_at": "2026-02-08T18:41:57.166Z",
    "completed_at": "2026-02-08T18:44:57.537Z",
    "command_count": 32,
    "prompt": "打开联系人应用，添加一个新联系人...",
    "device_serial": "emulator-5554",
    "package": "com.google.android.contacts",
    "golden_screenshot": "golden.png",
    "golden_screenshots": [
      {"file": "golden-001.png", "after_interaction": 3},
      {"file": "golden-002.png", "after_interaction": 8}
    ],
    "performance": { "..." : "..." },
    "perfetto": { "..." : "..." }
  },
  "commands": [
    {
      "issued_at": "2026-02-08T18:41:57.166Z",
      "args": ["shell", "am", "start", "-n", "com.google.android.contacts/..."],
      "exit_code": 0,
      "duration_ms": 44
    }
  ]
}
```

每条命令记录 4 个字段：

| 字段 | 说明 |
|------|------|
| `issued_at` | 发起时间（UTC ISO 8601） |
| `args` | ADB 参数列表 |
| `exit_code` | 退出码 |
| `duration_ms` | 执行耗时（毫秒） |

### 6.2 命令分类

回放时工具会自动区分两类命令：

| 类型 | 命令前缀 | 回放行为 |
|------|---------|---------|
| 观察命令 | `shell screencap`, `shell uiautomator dump`, `pull` | 跳过不执行 |
| 交互命令 | `shell am start`, `shell input tap/text/swipe/keyevent` 等 | 按时间间隔重放 |

回放时，连续两个 input 命令之间的最小间隔强制为 1 秒，防止高倍速下丢字符或漏点击。

### 6.3 完整产物目录

启用全部功能后，一个会话的完整产物如下：

```
recordings/<session-name>/
├── recording.json              # 完整命令记录 + 元数据
├── golden.png                  # 最后一张截图（向后兼容）
├── golden-001.png              # 检查点截图 1
├── golden-002.png              # 检查点截图 2
├── golden-NNN.png              # 检查点截图 N
├── performance.json            # 性能指标（启用 --perf 时）
├── trace.perfetto-trace        # 系统级 trace（启用 --trace 时）
├── verify.json                 # 验证报告（回放 --verify 后生成）
├── actual-001.png              # 回放时的实际截图（验证时生成）
└── actual-002.png
```

---

## 七、CI/CD 集成

### 7.1 集成到 CI Pipeline

录制产物是纯文本 + 图片，适合提交到 Git。典型 CI 流程：

```yaml
# .github/workflows/qa-replay.yml
name: QA 回放测试
on:
  push:
    branches: [main]

jobs:
  qa-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: 启动模拟器
        uses: reactivecircus/android-emulator-runner@v2
        with:
          api-level: 34
          script: |
            # 回放所有录制的测试
            for dir in recordings/*/; do
              session=$(basename "$dir")
              echo "测试: $session"
              ./android-qa-replay "$session" --speed 10 --verify
            done
```

### 7.2 退出码约定

| 退出码 | 含义 |
|--------|------|
| 0 | 回放成功 / 验证通过 |
| 非 0 | 回放失败（某条 ADB 命令执行失败）或验证未通过 |

---

## 八、注意事项与局限

### 8.1 关键规则

1. **绝对不要仅凭截图点击** -- 截图只用于理解上下文，精确坐标必须来自 UI dump
2. **优先用 `am start` 启动应用** -- 不要点击桌面图标（坐标不可靠）
3. **交互后等待 1 秒再做 UI dump** -- 否则可能拿到过渡动画中的旧数据
4. **Stop hook 自动兜底** -- 会话中断时 `.claude/settings.json` 中的 Stop hook 会自动归档，但最好显式调用 `./stop-recording`

### 8.2 已知局限

| 局限 | 影响 |
|------|------|
| 不支持流式 ADB 命令 | `logcat`、`shell top` 等无法录制 |
| 单线程串行 | 同一时间只能运行一个 `android-qa` 调用 |
| 不捕获 stdout/stderr | 只记录命令和元数据，不记录命令输出 |
| 3D 内容识别有限 | GLSurfaceView/TextureView 内容不在 UI dump 中，游戏场景受限 |
| 坐标依赖分辨率 | 在不同分辨率设备上回放时，点击坐标可能偏移 |

### 8.3 提示词编写技巧

提示词越详细，Claude 的执行越准确：

```
# 差的提示词
测试联系人应用

# 好的提示词
打开联系人应用，添加一个新联系人，名为 "John"，姓为 "Doe"，
电话号码为 "+001 1234 5678"，邮箱为 "john@example.com"。
保存后，验证该联系人是否出现在联系人列表中。
```

关键原则：
- 明确指定要操作的 App 名称
- 详细描述每一步要做什么
- 提供具体的测试数据（姓名、号码、文本等）
- 说明预期结果（如"验证该联系人是否出现在列表中"）

---

## 九、总结

android-qa-agent 的设计思路是将 AI 的理解能力与 ADB 的设备控制能力结合，用自然语言替代测试脚本。整个工具链的关键路径：

```
自然语言提示词
    → Claude Code 解析意图
    → 截图 + UI dump 观察
    → 计算坐标 + 执行操作（透明录制）
    → 归档 recording.json + golden screenshots
    → 倍速回放 + AI 视觉验证
    → verify.json 报告
```

适合用于 UI 自动化测试门槛高、测试场景变化频繁、需要快速验证但不想维护大量测试代码的团队。
