---
title: "云手机定制与风控对抗系列 (二)：Android 系统级定制 —— 让你的设备'更像真机'"
date: 2026-05-27
description: "风控引擎在识别虚拟设备/改机时，最核心的思路是多维度采集 + 交叉验证。它不会只检查某一个字段，而是采集大量设备参数，然后检查它们之间的一致性。"
tags: ['云游戏', 'Android']
category: "技术"
---
> 上一篇我们搭建了 CVD 环境，这一篇深入系统级定制：为什么要改系统属性、怎么改、以及风控系统到底检测什么。

---

## 背景：风控系统如何识别"假设备"？

风控引擎在识别虚拟设备/改机时，最核心的思路是**多维度采集 + 交叉验证**。它不会只检查某一个字段，而是采集大量设备参数，然后检查它们之间的**一致性**。

举例：一个 Galaxy S23 的设备报告了 Mediatek SoC 的 cpuinfo，或者 build.prop 显示 Android 13 但内核版本却是 4.19——这些不一致就是风控的突破口。

因此，系统级定制的核心目标不是"改一个属性"，而是**让所有能被采集到的维度保持逻辑一致性**。

---

## 1. 理解 Android 设备指纹的多维采集面

风控 SDK 一般从以下维度采集设备信息：

```
┌─────────────────────────────────────────────┐
│               设备指纹采集维度                  │
├─────────────┬─────────────┬─────────────────┤
│  系统属性层  │  硬件信息层  │   行为特征层      │
├─────────────┼─────────────┼─────────────────┤
│ build.prop  │ cpuinfo     │ 传感器数据        │
│ default.prop│ /proc/mem   │ 触摸轨迹          │
│ ro.* 属性   │ GPU 信息    │ 电池状态          │
│ 开发者选项  │ 传感器列表  │ 网络特征          │
│ ADB 状态    │ SIM 卡信息  │ 安装 App 列表     │
│ 系统版本    │ DRM ID     │ 系统服务状态       │
└─────────────┴─────────────┴─────────────────┘
```

---

## 2. 修改系统属性 (build.prop & default.prop)

### 2.1 核心属性详解

在 AOSP 中，系统属性定义在多个位置：

| 文件 | 作用 |
|------|------|
| `build/make/tools/buildinfo.sh` | 生成 build.prop 的脚本 |
| `device/generic/goldfish/vendor.mk` | 模拟器/虚拟设备的产品配置 |
| `device/google/cuttlefish/shared/config/cf_common.mk` | CVD 的产品配置 |
| `system/core/init/property_service.cpp` | 属性服务的实现 |

关键的可修改属性：

```
# 设备标识
ro.product.model=SM-S9180           # 型号（如 Galaxy S23）
ro.product.brand=samsung            # 品牌
ro.product.manufacturer=samsung     # 制造商
ro.product.device=dm3q              # 内部代号

# 指纹信息（风控重点检测对象）
ro.build.fingerprint=samsung/...
ro.build.description=...

# 安全属性（影响 SafetyNet/Play Integrity）
ro.debuggable=0                     # 非调试模式
ro.secure=1                         # 安全模式
ro.build.type=user                  # 非 userdebug/eng
ro.build.tags=release-keys          # 非 test-keys

# 版本信息
ro.build.version.sdk=34
ro.build.version.release=14
```

### 2.2 在 AOSP 源码中修改

```bash
# 编辑 CVD 的设备配置
vim device/google/cuttlefish/shared/config/cf_common.mk
```

在 `PRODUCT_PROPERTY_OVERRIDES` 区域添加：

```makefile
PRODUCT_PROPERTY_OVERRIDES += \
    ro.product.model=SM-S9180 \
    ro.product.brand=samsung \
    ro.product.manufacturer=samsung \
    ro.build.fingerprint=samsung/dm3qxxx/dm3q:14/UP1A.231005.007/S9180ZCU2BWK7:user/release-keys \
    ro.debuggable=0 \
    ro.secure=1 \
    ro.build.type=user \
    ro.build.tags=release-keys
```

### 2.3 动态修改（通过 Magisk/KSU 模块）

如果不想每次重新编译 AOSP，可以通过 Magisk/KernelSU 模块动态覆盖属性：

```bash
# Magisk 模块结构
/data/adb/modules/custom_props/
├── module.prop
├── system.prop         # 系统属性覆盖
└── post-fs-data.sh     # 启动脚本
```

`system.prop` 示例：
```
ro.product.model=SM-S9180
ro.product.brand=samsung
ro.debuggable=0
ro.secure=1
```

**注意**：`ro.*` 属性是只读的，普通方式无法在运行时修改。Magisk 通过 `resetprop` 工具在内核层面修改：

```bash
# resetprop 使用示例
resetprop ro.debuggable 0
resetprop ro.secure 1

# 持久化：在 service.d 中执行
# /data/adb/service.d/00_custom_props.sh
#!/system/bin/sh
resetprop ro.debuggable 0
resetprop ro.secure 1
```

---

## 3. 调整开发者选项与 ADB 行为

### 3.1 ADB 状态伪装

风控常检查 ADB 是否开启：

```java
// 常见风控检测代码
int adbEnabled = Settings.Global.getInt(
    context.getContentResolver(),
    Settings.Global.ADB_ENABLED, 0
);
// ADB_ENABLED = 1 即触发风控
```

在 AOSP 中，ADB 启用状态由 `Settings.Global.ADB_ENABLED` 和 `Settings.Global.DEVELOPMENT_SETTINGS_ENABLED` 共同控制。

**AOSP 层面隐藏 ADB 的方法**：

修改 `frameworks/base/services/core/java/com/android/server/adb/AdbService.java`：

```java
// 始终返回 ADB 未启用（仅影响 Settings 检查，不影响实际 adbd 运行）
// 风险：会破坏正常连接，仅用于风控分析场景
```

**更安全的做法**——通过 LSPosed/Xposed Hook：

```java
// Hook Settings.Global 的 getInt 方法
XposedHelpers.findAndHookMethod(
    "android.provider.Settings$Global",
    lpparam.classLoader,
    "getInt",
    ContentResolver.class, String.class, int.class,
    new XC_MethodHook() {
        @Override
        protected void beforeHookedMethod(MethodHookParam param) {
            String key = (String) param.args[1];
            if ("adb_enabled".equals(key)) {
                param.setResult(0);
            }
        }
    }
);
```

### 3.2 开发者选项检测的痛点

风控还会检查：

- `ro.debuggable` — 是否为可调试 ROM
- `ro.build.type` — user/userdebug/eng
- `init.svc.adbd` — adbd 服务状态
- `/system/xbin/su` — su 二进制文件存在

---

## 4. 输入设备特征模拟

真机一定有触摸屏、传感器等硬件。CVD 默认的输入设备可通过以下方式定制。

### 4.1 查看当前输入设备

```bash
adb shell getevent -pl
# 查看所有输入设备及其能力

adb shell dumpsys input
# 查看输入设备详细信息
```

### 4.2 在 CVD 中定制输入设备

CVD 使用 `cvd_config.json` 配置虚拟硬件，包括输入设备类型：

```json
{
  "input": {
    "touchscreen": true,
    "multi_touch_points": 10,
    "keyboard": false,
    "hardware_buttons": ["power", "volume_up", "volume_down"]
  }
}
```

通过 REST API 运行时控制：

```bash
# 启动时指定
launch_cvd --config_file=cvd_config.json

# 运行时通过 REST API
curl -X POST https://localhost:8443/input/...
```

---

## 5. SIM 卡信息模拟

许多应用（特别是社交/金融类）会检查是否有 SIM 卡，因为虚拟设备通常没有。

### AOSP 层面模拟 SIM 卡

修改 `device/google/cuttlefish/guest/hals/ril/` 下的 RIL HAL 实现：

```cpp
// 在 RIL 响应中注入伪造的 ICCID/IMSI 信息
// 位置: device/google/cuttlefish/guest/hals/ril/reference_ril.cpp
```

或者通过 `cvd_config.json` 在 CVD 启动时注入 SIM 信息：

```json
{
  "sim": {
    "iccid": "89860000000000000000",
    "imsi": "460000000000001",
    "mcc": "460",
    "mnc": "00",
    "operator": "中国移动",
    "phone_number": "13800000000"
  }
}
```

---

## 6. GMS (Google Mobile Services) 集成

GMS 集成是让虚拟环境"更像真机"的关键步骤，因为绝大多数真机都自带 GMS。

```bash
# 方式一：编译时集成
# 将 GMS 包放到 vendor/google/gms/ 下

# 方式二：通过 OpenGApps 刷入
# 下载对应的 OpenGApps 包
# 通过 adb 推送并安装
adb root
adb remount
adb shell mkdir -p /system/priv-app/GoogleServicesFramework
# ... 依次安装核心 GMS 组件
```

关键组件：
- `GoogleServicesFramework.apk` — 核心框架
- `GooglePlayServices.apk` — Play 服务
- `Phonesky.apk` — Google Play 商店

---

## 7. WebView 替换

风控有时会检测 WebView 实现是否为 Google 原版。CVD 默认使用的是 AOSP WebView（Chromium 基础），可以通过替换 APK 来伪装：

```bash
# 替换为特定版本的 WebView
adb root
adb remount
adb push webview.apk /system/app/webview/webview.apk
adb reboot
```

---

## 8. GPU 信息定制

GPU 信息是风控的重点检测维度。真机和虚拟机的 GPU 驱动完全不同。

在 AOSP 层面修改：

```bash
# 修改 EGL/GLES 驱动返回的 GPU 信息
# 源码位置: frameworks/native/opengl/libs/EGL/
# 可伪造 GL_RENDERER, GL_VENDOR 等字段
```

更简单的做法——通过 Magisk 模块修改 `/system/lib64/libEGL.so`：

```bash
# 替换 EGL 字符串
# 将 "Cuttlefish GPU" 替换为 "Adreno (TM) 740"
```

---

## 总结：系统级定制的层次选择

| 定制方式 | 深度 | 隐蔽性 | 灵活性 | 适合场景 |
|----------|------|--------|--------|----------|
| 修改 AOSP 源码重编译 | 最深 | 最高 | 中 | 大规模部署 |
| Magisk/KSU 模块 | 中 | 中 | 高 | 快速迭代测试 |
| Xposed/LSPosed Hook | 浅 | 低 | 最高 | 快速验证 |
| Frida 动态注入 | 浅 | 低 | 最高 | 逆向分析/调试 |

**最佳实践**：先在 Frida/LSPosed 层面快速验证哪些属性被检测，确认后下沉到 Magisk 模块或 AOSP 源码修改。

---

## 下一篇预告

下一篇我们将深入**内核级定制**——KernelSU GKI/LKM 集成、SuSFS 文件隐藏、APatch 内核补丁、cpuinfo 定制、SoC 簇调度策略。这是拉开高手差距的地方。

---

### 参考资源

- [MagiskHidePropsConf 模块](https://github.com/Magisk-Modules-Repo/MagiskHidePropsConf)
- [Magisk Hide 深入配置指南](https://www.didgeridoohan.com/magisk/MagiskHideMore)
- [Adding Custom System Service in AOSP](https://medium.com/@samirdubey/mastering-system-services-a-comprehensive-guide-for-android-aosp-developers-458cf35fbe73)
- [device-spoofing LSPosed 模块](https://github.com/topics/fingerprint-spoofing)
- [CVD Environment Control API](https://source.android.com/docs/devices/cuttlefish/control-environment)
- [AOSP GMS Integration Guide](https://source.android.com/docs/core/gms)
