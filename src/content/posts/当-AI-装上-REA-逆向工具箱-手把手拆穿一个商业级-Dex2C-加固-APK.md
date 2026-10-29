---
title: "当 AI 装上 REA 逆向工具箱：手把手拆穿一个商业级 Dex2C 加固 APK"
date: 2026-10-27
description: "很多做 Android 开发或移动安全的同学，第一次逆向商业 App 时都会经历同一个崩溃瞬间： 你拿到了一个线上发行的 APK，满怀信心地拖进 JADX-GUI。"
tags: ['逆向', 'Android', 'REA', 'AI']
draft: true
category: "技术"
---
> **项目地址**：[https://github.com/morluto/rea](https://github.com/morluto/rea) ｜ MIT 开源
> **官网与文档**：[https://rea.tools](https://rea.tools)
>
> 读完本文你将掌握：把 **REA（Reverse Engineer Anything）** 接入 Claude Code → 理解 REA 基于 `ev_<sha256>` 证据锚定的逆向工作流 → 亲手构建一个包含 Java 校验逻辑与 C++ JNI 算子的 Android 靶场工程，并用企业级 **易盾 Dex2C 加固配置** 对其加壳 → 跟着 AI 用 5 个递进步骤，从"业务类在 DEX 可见类列表中消失"的困境出发，一路完成 **JADX 壳入口拆解、ELF 初始化 Stub 分析、加密代码段静态还原、`RegisterNatives` 9 项混淆映射表还原、OLLVM 控制流平坦化与原子锁 XOR 字符串池解密**，最终揪出整条安全防线的"木桶短板"。
>
> **环境说明**：本文所有逆向数据、地址偏移、SHA-256 摘要与截图均来自配套验证工程 `rea-jiagu-demo/` 的真实构建与逆向产物（REA `@6.4.0` + Headless JADX `0.7.1` + Headless Ghidra `12.1.4` + JDK 21，2026-10 实测），详见文末「附录：验证工程与复现指南」。

---

## 一、问题提出：为什么加固后的 APK，传统逆向工具一上来就"瞎"了？

很多做 Android 开发或移动安全的同学，第一次逆向商业 App 时都会经历同一个崩溃瞬间：

你拿到了一个线上发行的 APK，满怀信心地拖进 JADX-GUI。结果展开左侧包名树一看——**原本熟悉的业务包名（比如 `com.demo.reajiagu`）连影子都找不到**，整个 `classes.dex` 里只剩下一个名叫 `com.netease.dexshell.ProxyApplication` 的壳入口，外加一堆名字长得像乱码的 `I0O0I0OOo0`、`IO00OI0o0` 方法；点进 `onCreate()`，只有孤零零的一行：

```java
@Override // android.app.Application
public native void onCreate();
```

更让人绝望的是，当你顺藤摸瓜解压出 `lib/arm64-v8a/` 下的核心 Native 库（`libnetease_ssl.so` 与 `libandroidmainruns.so`），把它们拖进 IDA 或 Ghidra 想看 `JNI_OnLoad` 时，反编译器直接甩给你一行冰冷的报错：

```c
/* WARNING: Control flow encountered bad instruction data */
void JNI_OnLoad(void) {
    /* WARNING: Bad instruction - Truncating control flow here */
    halt_baddata();
}
```

**Java 业务类从 `classes.dex` 的可见类列表中消失，主要导出函数的 Native 代码入口又因加密而无法直接反汇编。** 这就是本文样本所采用的 **DEX 加密壳 + Dex2C（将部分 Java 方法转换为 C/C++ Native）+ SO 代码段加密** 组合拳的威力。

在传统手工逆向时代，要啃下这块硬骨头，你得在 JADX、010 Editor、Readelf、IDA/Ghidra 和 Frida 之间来回切窗口，手动算 ELF 偏移、写脚本还原 SO 加密区、找 `RegisterNatives` 结构体表、再一行行抠 OLLVM 状态机里的异或字符串。

现在，如果把 **REA（Reverse Engineer Anything）** 装进 Claude Code，让 AI 调动 JADX，并在需要时直接驱动本机 Ghidra 对这个加固包发起全链路剖析，会发生什么？

为了把整个过程讲透，我们不拿黑盒的第三方商业 App 做演示，而是**自己动手写一个五脏俱全的 Android 靶场 Demo，用真实生产线上的加固配置把它加固，再让 AI 带着我们一层一层把它剥开**。

---

## 二、相关知识点与工具链准备

### 2.1 一句话认识 REA：不是"让 AI 猜代码"，而是"让结论可定位、可复核"

**REA（Reverse Engineer Anything）** 是一个基于 MCP（Model Context Protocol）协议的开源逆向工程工具包。它把逆向分析能力直接装进你的 AI 编程助手（Claude Code、Cursor、Codex、Gemini CLI 等）。

和传统的"把反编译代码复制粘贴给大模型看"相比，REA 有两个本质区别：

1. **工具路由自动化**：你只需要用自然语言提问（例如「检查这个加固 APK 的真实 Application 藏在哪，追出它的 DEX 解密和 Native 注册链路」），AI 会按内置的路由规则自动调用 `inspect_artifact`、`inspect_android_package`、`inspect_android_method`、Ghidra Headless 等工具，自己去翻二进制、追交叉引用（Xrefs）。
2. **加密哈希锁定的证据账本（Evidence Ledger）**：大模型搞逆向最怕"幻觉"（看个函数名就开始瞎编逻辑）。REA 的工具调用会生成带 `ev_<sha256>` 唯一标识的 `Evidence` 记录，绑定目标文件的 SHA-256、分析引擎版本、置信度（`observed` / `derived` / `inferred`）以及覆盖局限性（`limitations`）。分析时应让关键结论尽量引用对应的 `evidence_id` 和虚拟地址；但证据 ID 只是定位与复核凭证，并不自动证明结论正确，仍需检查证据覆盖范围和推导过程。

### 2.2 把 REA 接入 Claude Code，并划清本次工具边界

前置条件为 Node.js 与 npm，具体版本要求以所安装 REA 版本的文档为准。本文统一按实测的 `6.4.0` 复现：

```bash
# 一键非交互式接入 Claude Code（若想先预览变更，可加上 --dry-run）
npx -y rea-agents@6.4.0 setup --yes --client claude_code

# 也可以按同一版本全局安装 CLI，使用 rea doctor 自检或 rea update 升级
npm install --global rea-agents@6.4.0
```

执行完成后，REA 会自动完成两件事：
- 在 `~/.claude.json` 中注册名为 `rea` 的 MCP 服务器（启动命令为 `npx -y rea-agents@6.4.0 mcp`）；
- 在 `~/.claude/skills/reverse-engineer-anything/` 下安装完整的逆向路由 Skill。

本文使用的引擎配置如下：

| 能力域 | 环境变量 / 配置项 | 本文实测版本与调用方式 |
|---|---|---|
| **Android DEX / Manifest 分析** | `REA_JADX_MCP_JAR` + `JAVA_HOME` | `jadx-headless-mcp 0.7.1` + `JDK 21`，通过 REA 调用 |
| **Native ELF 反编译** | 本机 Ghidra 安装目录 | `Ghidra 12.1.4 PUBLIC`，由 Claude Code 直接调用 `analyzeHeadless` + 自定义 PostScript |

这里有两个容易误解的边界：

1. **本地分析不等于整个 AI 工作流离线。** REA 在本地分析目标文件，但工具返回的反编译文本和证据会交给 AI Agent；模型服务商的数据策略仍需单独评估，敏感样本不能只看“本地运行”四个字。
2. **本次 Native ELF 分析不是由 REA 的 Windows Ghidra Provider 自动完成。** 该 Provider 在本文 Windows 环境下不接受本次 ARM64 ELF 目标，因此 Step 3～5 改为由 Claude Code 直接运行本机 Ghidra Headless。REA 主要负责 APK/JADX 分析与证据记录，不能据此宣称所有平台和格式都能仅靠一个环境变量自动打通。

### 2.3 本文的加固代际划分与四层制品结构

在之前发布的《Android 第一代加固技术原理详解》和《Android 第二代加固技术原理详解》中，我们梳理过加固技术的演进脉络。本文沿用该系列对“二代 DEX 加密”和“四代 Dex2C”的称呼，**这不是 Android 官方统一的代际标准**；不同资料可能采用不同划分。本次样本可拆成“三层厂商防护 + 一层业务自研边界”，其中第四层是分析对象和潜在短板，不是加固平台提供的主动防线：

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 1: APK 清单与 DEX 壳层 (AndroidManifest.xml + classes.dex)        │
│   • 入口 Application 被替换为 com.netease.dexshell.ProxyApplication      │
│   • 业务类从 classes.dex 消失；后续加载链指向加密资源 assets/a4f47ca30a  │
├─────────────────────────────────────────────────────────────────────────┤
│ Layer 2: 二代壳 Native 加载引擎 (lib/arm64-v8a/libnetease_ssl.so)       │
│   • 主要代码区被加密，初始化 Stub 在加载期执行 ~byte 自解密             │
│   • JNI_OnLoad 通过 RegisterNatives 动态绑定 ProxyApplication 的 9 个方法 │
│   • 负责解密主 DEX、注入 BaseDexClassLoader.pathList、反射移交 Application │
├─────────────────────────────────────────────────────────────────────────┤
│ Layer 3: 四代 Dex2C + OLLVM 转换库 (lib/arm64-v8a/libandroidmainruns.so)│
│   • 主要代码区同样受按位取反加密保护，且 ELF Section 名称被混淆          │
│   • 部分 Java 方法被转换为 C++ JNI，配合原子锁 XOR 字符串池与平坦化      │
├─────────────────────────────────────────────────────────────────────────┤
│ Layer 4: 业务自写 C++ JNI 算子库 (lib/arm64-v8a/libreajiagu.so)         │
│   • NDK/CMake 编译的业务库，是独立分析面，不属于厂商主动防护层           │
└─────────────────────────────────────────────────────────────────────────┘
```

搞清楚这四层制品地图，接下来的实战就不会迷路。

---

## 三、具体实例应用展示：从构建加固靶场到 5 步全链路逆向破局

### Step 0：构建 Android 靶场 Demo，并用 `microgameapp` 加固配置完成加壳

我们先在 `rea-jiagu-demo/` 工程中编写一个标准的业务靶场。它包含 4 个核心类与 1 个 C++ JNI 库：

1. **`DemoApplication.java`**：应用启动时调用 `TokenEngine.generateBootToken()` 生成启动鉴权票据。
2. **`TokenEngine.java`**（Java 层核心业务类）：包含 `generateBootToken()` 与 `verifyVipOrder()` 两个核心算法，内部通过 `XOR 0x5A` 解密前缀 `"CG_AUTH"`，计算 SHA-256 摘要，并调用 JNI 层签名。
3. **`NativeBridge.java` + `native-lib.cpp`**（C++ 层核心算子，编译为 `libreajiagu.so`）：

```java
// ===== Java 层核心算法：TokenEngine.java =====
public final class TokenEngine {
    private static final String APP_CHANNEL = "netease_cloudgame_demo";
    private static final int XOR_MAGIC = 0x5A;

    public static String generateBootToken(String pkgName, long seed) {
        String rawHeader = deobfuscatePrefix() + ":" + pkgName + ":" + APP_CHANNEL + ":" + seed;
        String shaPart = sha256Short(rawHeader);
        String nativePart = NativeBridge.signPayloadNative(rawHeader, seed);
        return " V1_" + shaPart + "_" + nativePart;
    }

    public static int verifyVipOrder(String userId, String licenseCode, int amountCent) {
        if (userId == null || userId.isEmpty() || amountCent <= 0) return -1;
        if (!NativeBridge.verifyLicenseCodeNative(licenseCode)) return 0;
        int score = (userId.hashCode() & 0x7FFF) + (amountCent / 100) * 17;
        return (score % 2 == 0) ? 2 : 1;
    }

    private static String deobfuscatePrefix() {
        // 异或 0x5A 还原 "CG_AUTH"
        byte[] enc = new byte[]{0x19, 0x1D, 0x05, 0x1B, 0x0F, 0x0E, 0x12};
        byte[] out = new byte[enc.length];
        for (int i = 0; i < enc.length; i++) out[i] = (byte) (enc[i] ^ XOR_MAGIC);
        return new String(out, StandardCharsets.UTF_8);
    }
    // ... sha256Short() 略
}
```

```cpp
// ===== C++ JNI 层核心算子：native-lib.cpp (编译为 libreajiagu.so) =====
static const uint8_t kSecretSalt[] = {
    0x52, 0x45, 0x41, 0x5F, 0x4E, 0x41, 0x54, 0x49,
    0x56, 0x45, 0x5F, 0x4B, 0x45, 0x59, 0x5F, 0x39
}; // 16 字节私有盐值："REA_NATIVE_KEY_9"

static uint32_t computeFnv1a32(const char* data, size_t len) {
    uint32_t hash = 0x811c9dc5u;
    for (size_t i = 0; i < len; ++i) {
        uint8_t mixed = static_cast<uint8_t>(data[i]) ^ kSecretSalt[i & 0x0F];
        hash ^= mixed;
        hash *= 0x01000193u;
    }
    return hash;
}

extern "C" JNIEXPORT jboolean JNICALL
Java_com_demo_reajiagu_NativeBridge_verifyLicenseCodeNative(JNIEnv* env, jclass, jstring code_jstr) {
    // ... 读取字符串 input ...
    if (input.size() != 12) return JNI_FALSE;
    return (computeFnv1a32(input.c_str(), input.size()) == computeFnv1a32("REA-2026-PRO", 12))
           ? JNI_TRUE : JNI_FALSE;
}
```

这里的“签名”和“激活码校验”只是**教学用完整性校验算子**：算法是 FNV-1a 风格的逐字节 XOR 盐混合，不是标准密码学 MAC，更不是数字签名。32 位输出存在碰撞，盐又随 SO 分发，因此不能把它直接用于生产授权。

接着，我们复用 `D:\Code\NetEase1\microgameapp` 项目中的 `build_config.sh` 与 `build_testease.sh` 加固流水线配置，调用 `testease/Dex2CUpload.jar`（v2.1.0，开启 `-useVmProtect true`）对编译出的 `app-raw.apk` 进行加固，再用 `testease/apksigner.jar` 和 `micro_app.jks` 重新签名：

```bash
# 1. 编译未加固 Release 基线包
bash build.sh assembleRelease --no-daemon
cp app/build/outputs/apk/release/app-release.apk apks/app-raw.apk

# 2. 使用 microgameapp 的加固凭证与参数调用 Dex2CUpload.jar 加固
#    注：appKey / appSecret / appId 为加固平台按包名下发的私有凭证，需从加固控制台自行申请
java -Dfile.encoding=UTF-8 -jar "D:/Code/NetEase1/microgameapp/testease/Dex2CUpload.jar" \
  -appKey "<YOUR_APP_KEY>" -appSecret "<YOUR_APP_SECRET>" -appId "<YOUR_APP_ID>" \
  -input "apks/app-raw.apk" -output "apks/app-protected-unsigned.apk" -useVmProtect true

# 3. 加固会剥离原包签名，使用 apksigner.jar 与自己的 keystore 重新签名
java -jar "D:/Code/NetEase1/microgameapp/testease/apksigner.jar" sign --verbose \
  --ks "<YOUR_KEYSTORE.jks>" \
  --ks-key-alias "<YOUR_KEY_ALIAS>" --ks-pass pass:<YOUR_KEYSTORE_PASS> --key-pass pass:<YOUR_KEY_PASS> \
  --out "apks/app-protected-signed.apk" "apks/app-protected-unsigned.apk"
```

![编译靶场 Demo 并使用 microgameapp 加固配置执行 Dex2C + VMP 加固实录](/images/当-AI-装上-REA-逆向工具箱-手把手拆穿一个商业级-Dex2C-加固-APK/shot01_jiagu_build_and_protect.png)

加固完成后，APK 体积从 **464 KB（474,946 B）** 暴涨到了 **3.3 MB（3,397,416 B）**。接下来，我们假装自己手里只有这个加固后的 `app-protected-signed.apk`，用 REA 把它彻底拆穿。

---

### Step 1：制品全景取证——用 `inspect_android_package` 与 `inspect_artifact` 揪出壳的伪装

逆向的第一步永远不是盲目翻代码，而是**摸清制品边界与变化增量**。

我们让 Claude Code 调用 REA 的 `inspect_android_package`、`search_android_classes` 和 `inspect_artifact` 工具，分别对加固前后的两个 APK 做静态清点：

![REA MCP — inspect_android_package & inspect_artifact 加固前后全景取证对比](/images/当-AI-装上-REA-逆向工具箱-手把手拆穿一个商业级-Dex2C-加固-APK/shot02_rea_apk_inventory_diff.png)

从 REA 返回的结构化证据（`ev_7250f91f1fd45888...` 与 `ev_48f88e283f646f78...`）中，三个核心事实立刻浮出水面：

**1. `AndroidManifest.xml` 入口被劫持，但真实入口藏在 `meta-data` 里：**

```xml
<!-- REA inspect_android_package 实测提取的加固后 Manifest -->
<application
    android:theme="@android:style/Theme.Material.Light.NoActionBar"
    android:label="@string/app_name"
    android:name="com.netease.dexshell.ProxyApplication"
    android:allowBackup="false"
    android:extractNativeLibs="false">
    <meta-data
        android:name="SHELL_VERSION"
        android:value="2.2.4.1_9b22f84"/>
    <meta-data
        android:name="II0OI00IO"
        android:value="com.demo.reajiagu.DemoApplication"/>
    <meta-data
        android:name="IOO0IIO0"
        android:value="1.0.0_100_91b26472737088f22f9ebc4f4bc3c7ab"/>
```

可以看到，加固器把 `<application android:name>` 替换成了壳入口 `com.netease.dexshell.ProxyApplication`，同时塞进了三条 `meta-data`：
- `SHELL_VERSION`：壳版本号 `2.2.4.1_9b22f84`（该字段前 7 位与构建日志里的 `processVersion` 前缀一致）；
- `II0OI00IO`：原包真实的 `com.demo.reajiagu.DemoApplication`（壳在完成 DEX 解密后，必须靠它反射恢复应用上下文）；
- `IOO0IIO0`：版本标识与校验 MD5（`1.0.0_100_91b26472737088f22f9ebc4f4bc3c7ab`）。

**2. 原包业务类在 `classes.dex` 中全军覆没：**
调用 `search_android_classes`（`ev_9f52200e5f1042e6...`）枚举全部 66 个类，除了 `androidx.annotation.*` 注解接口外，只剩下 4 个壳类：`com.netease.dexshell.ProxyApplication`、`Utils`、`BuildConfig`、`R`。原包的 `DemoApplication`、`MainActivity`、`TokenEngine`、`NativeBridge` 在 `classes.dex` 中全部消失。

**3. 制品图谱（Artifact Graph）锁定新增的加密载荷与 Native 引擎：**
通过 `open_binary` + `inspect_artifact` / `extract_artifact`对比归档节点，加固后的 APK 多出了两组关键文件：
- **`assets/` 下的神秘文件**：`assets/923ed6ec7b`（仅 10 字节）、`assets/a4f47ca30a`（94,404 字节，文件头为 `df de c3 b1`，并非标准 `dex\n035` 魔数，提示其可能被加密或采用自定义封装）、`assets/netease_hook_arm`（158 KB）、`assets/netease_ssl`（485 KB）；
- **`lib/arm64-v8a/` 下新增的 4 个 SO 库**：`libnetease_ssl.so`（449,692 B）、`libandroidmainruns.so`（750,724 B）、以及崩溃捕获库 `libxcrash.so` / `libxcrash_dumper.so`。

**第一阶段结论**：原包的 DEX 极大概率被加密成了 `assets/a4f47ca30a`，而解密并加载它的钥匙，就藏在 `ProxyApplication` 与那两个新增的 Native SO 里。

---

### Step 2：拆解 Java 壳加载器——用 `inspect_android_method` 破译 `XOR 0xBB` 索引表

锁定了 `com.netease.dexshell.ProxyApplication`，我们无需打开 JADX 图形界面，直接调用 REA 的 `inspect_android_class`（`ev_f36ea62c996e59dc...`）查看它的方法清单，再用 `inspect_android_method` 反编译它的核心生命周期方法 `attachBaseContext` 与 `IO00OI0o0`：

![REA MCP — 拆解 ProxyApplication 壳加载器与 XOR 0xBB 配置解密逻辑](/images/当-AI-装上-REA-逆向工具箱-手把手拆穿一个商业级-Dex2C-加固-APK/shot03_proxy_application_decompile.png)

REA 返回的 `attachBaseContext` 源码（`ev_e06b5f58acd38c44...`）把壳的启动三部曲交代得清清楚楚：

```java
// REA inspect_android_method 实测输出 (evidence_id: ev_e06b5f58acd38c44f348ec26c8e0ab64af6a8492e86afceaefb72b10eaf5e745)
@Override
protected void attachBaseContext(Context context) {
    super.attachBaseContext(context);
    proxy = this;
    ApplicationInfo applicationInfo = getPackageManager().getApplicationInfo(getPackageName(), 128);
    II0OO0II0O = applicationInfo.metaData.getString("II0OI00IO"); // "com.demo.reajiagu.DemoApplication"
    I00I067    = applicationInfo.metaData.getString("IOO0IIO0");  // "1.0.0_100_91b26472737088f22f9ebc4f4bc3c7ab"

    // 第一步：根据 CPU ABI 释放 hook so，并加载核心壳引擎 libnetease_ssl.so
    I0O0I0OOo0(Utils.II0OO0I0(context), context);

    // 第二步：创建私有解密目录 /data/user/0/<pkg>/files/net_opt/<I00I067>/enc，提取并注入主 DEX
    String str = String.format(Locale.CHINA, "%s/net_opt/%s/enc", getFilesDir(), I00I067);
    IO00OI0o0(context, str);

    // 第三步：Android 5.0~9.0 下启动后台线程，延迟 50 秒后调用 dex2oat 编译生成 OAT
    I0O00OIIoO(context, str);
}
```

紧接着看第二步调用的 `IO00OI0o0(context, str)`（`ev_74f8ccec5fc5cc76...`），一段极其关键的解密代码跃然纸上：

```java
// REA inspect_android_method 实测输出 (evidence_id: ev_74f8ccec5fc5cc76e030635f9af2347a414649097e91a9b321927067699b88ef)
InputStream inputStreamOpen = context.getAssets().open("923ed6ec7b");
int iAvailable = inputStreamOpen.available();
byte[] bArr = new byte[iAvailable];
inputStreamOpen.read(bArr);
for (int i3 = 0; i3 < iAvailable; i3++) {
    bArr[i3] = (byte) (bArr[i3] ^ 187);   // <-- 核心发现：逐字节异或 187 (0xBB)！
}
inputStreamOpen.close();
strArrSplit = new String(bArr).split(":");
```

原来，`assets/923ed6ec7b` 是一个用 **`XOR 187`（即 `0xBB`）** 加密的 DEX 资源索引表！我们立刻对刚刚 `extract_artifact` 提取出的 10 字节文件 `923ed6ec7b`（十六进制：`da 8f dd 8f 8c d8 da 88 8b da`）执行异或 `0xBB` 验证：

$$\text{0xDA} \oplus \text{0xBB} = \text{'a'}, \quad \text{0x8F} \oplus \text{0xBB} = \text{'4'}, \quad \dots \implies \texttt{"a4f47ca30a"}$$

严丝合缝！解密出来的字符串 `"a4f47ca30a"`，正是 Step 1 在 `assets/` 目录下看到的那个 94,404 字节的加密 DEX 文件！

继续往下读 `IO00OI0o0`：壳把 `assets/a4f47ca30a` 原样拷贝到私有目录的 `enc_opt0.dex` 后，依次调用了 4 个方法：
1. `IO0I0II00O(file2.getAbsolutePath())`：设置文件只读；
2. `objArrIOIOOI0 = IOIOOI0(context, file, file2)`：把加密的 `enc_opt0.dex` 解析为 `DexPathList$Element[]` 数组；
3. `I00OO0OI(context, objArr)`：将 `Element[]` 注入当前 ClassLoader；
4. `IOOO00IIII(context)`：初始化运行时保护服务。

然而，当我们用 `inspect_android_method` 查看 `IOIOOI0`、`I00OO0OI`、`I0II0IIO00` 以及 `onCreate` 时，REA 全部返回：

```text
body_status: "not_available"
text: "// method exists but has no decompiled body (native/abstract)"
```

在 `ProxyApplication` 的 18 个方法里，**凡是涉及核心解密、ClassLoader 注入、AssetManager Hook、以及最终 `Application` 替换的 9 个方法，全部是 `native` 方法**！而 `I0O0I0OOo0` 里写得明明白白：`System.loadLibrary("netease_ssl")`。

这意味着，战场正式从 Java DEX 层转移到了 Native ELF 层——`libnetease_ssl.so`。

---

### Step 3：攻克 SO 加壳——逆向 `_DT_INIT` 破解按位取反（`~byte`）自解密算法

为了分析 `libnetease_ssl.so` 与 `libandroidmainruns.so`，我们调用 Ghidra 12.1.4 Headless 对它们进行反编译。

然而，正如文章开头所展示的，如果直接把未脱壳的 `libnetease_ssl.so`（SHA-256: `c0982e34...`）或 `libandroidmainruns.so`（SHA-256: `39b0ca2f...`）喂给反编译器，所有导出函数（包括 `JNI_OnLoad`、`Java_com_demo_reajiagu_DemoApplication_initNeteaseXcrashMethod00__`）在入口处全部是无法反汇编的脏数据（`halt_baddata()`）。

**为什么静态看主要导出函数是乱码，真机运行却不崩溃？**
Android 动态链接器在调用 `JNI_OnLoad` 前，会执行 ELF 动态段中 `DT_INIT` / `DT_INIT_ARRAY` 等标签指向的初始化代码。`DT_INIT` 是动态标签，不是固定的函数名；本文把 Ghidra 中识别出的初始化 Stub 记作 `_DT_INIT`。**在本文样本里，这个初始化 Stub 未被加密，并包含自解密逻辑**，所以成为静态分析的突破口。其他壳可能使用不同初始化路径或按需解密，不能推广成“所有壳都只有 `_DT_INIT` 可读”。

我们在 Ghidra 中直接定位 `libnetease_ssl.so` 的 `_DT_INIT`（虚拟地址 `0x00159b7c`），果然看到了清晰完整的可执行代码：

![Ghidra 12.1.4 — 分析初始化 Stub 的按位取反自解密逻辑与加密区静态还原](/images/当-AI-装上-REA-逆向工具箱-手把手拆穿一个商业级-Dex2C-加固-APK/shot04_so_unpacking_dt_init.png)

把 Ghidra 反编译出的 `_DT_INIT`（`0x00159b7c`）与它的辅助函数 `FUN_001595c8`、`FUN_001598d0` 连起来读，易盾 SO 加壳的自脱壳算法被完整还原：

```c
// Ghidra 12.1.4 反编译 libnetease_ssl.so :: _DT_INIT @ 0x00159b7c (经符号重命名整理)
void _DT_INIT(void) {
    // 1. 扫描 /proc/self/maps 获取当前 SO 在内存中的加载基址 (即 ELF Header 起始地址)
    void *so_base = find_so_base_from_proc_maps();
    if (so_base != NULL) {
        // 2. 精妙设计：借用 64 位 ELF Header 偏移 +0x18 处的 e_entry 字段存放「加密区字节长度」！
        long enc_len = *(long *)((long)so_base + 0x18);

        // 3. 从 /proc/<pid>/maps 找到当前 SO 在磁盘或 APK 映射中的真实文件路径并打开
        char *so_path = find_so_path_from_proc_maps(getpid(), get_process_name());
        FILE *fp = fopen(so_path, "r");
        if (fp != NULL) {
            // 4. 定位到 SO 文件末尾倒数第 4 个字节，读取 32 位整数作为「加密区起始偏移」！
            int enc_offset = 0;
            fseek(fp, -4, SEEK_END);
            fread(&enc_offset, 4, 1, fp);
            fclose(fp);

            // 5. 修改加密区内存页权限为 RWX (7 = PROT_READ | PROT_WRITE | PROT_EXEC)
            byte *target = (byte *)((long)so_base + (long)enc_offset);
            void *page_start = (void *)((ulong)target & ~0xfffUL);
            mprotect(page_start, (size_t)(target + enc_len - (byte *)page_start), 7);

            // 6. 核心解密循环：逐字节按位取反 (~byte)！
            for (byte *p = target; enc_len != 0; enc_len--) {
                *p = ~(*p);
                p++;
            }

            // 7. 恢复代码段权限为 RX (5 = PROT_READ | PROT_EXEC)
            mprotect(page_start, ..., 5);

            // 8. 反内存 Dump 抹头：将内存中 ELF Header 前 64 (0x40) 字节全部清零！
            mprotect(so_base, 0x1000, 7);
            for (long i = 0; i < 0x40; i++) {
                *((uint8_t *)so_base + i) = 0;
            }
            mprotect(so_base, 0x1000, 5);
        }
    }
}
```

这段代码揭示了三个极具工程价值的攻防细节：
1. **为什么本文样本直接抓取的运行时 SO 镜像可能无法被 IDA 正常加载？** 因为第 8 步在自解密完成后，立刻用 `mprotect` 把内存中 ELF Header 的前 64 字节（包含 `\x7fELF` 魔数、体系结构、`e_phoff`、`e_shoff`）全部抹成了 `0x00`。这是该样本的一项反 Dump 措施，不代表所有 SO 无法加载都由同一原因造成。
2. **如果 APK 设置了 `extractNativeLibs="false"`（SO 不解压直接从 base.apk 内存映射加载），`fopen(so_path)` 打不开独立 SO 文件怎么办？** 我们在反编译中发现，`_DT_INIT` 紧接着写了第二个分支 `FUN_00159d58(so_base, so_base, enc_len)`（位于 `0x00159d58`）：当文件打开失败时，它会直接遍历内存中 ELF 的 `PT_DYNAMIC` 段，根据 `DT_PLTGOT` 与 `DT_JMPREL` 动态计算出 `.text` 段的起始偏移，同样执行 `*p = ~(*p)`！
3. **如何对这段加密区做静态完整还原？** 既然我们已经拿到了它的加密参数公式：
   - **加密区长度 `enc_len`** $=$ ELF Header `+0x18`（`e_entry`）处的 `uint64_t`；
   - **加密区起始偏移 `enc_offset`** $=$ 文件末尾最后 4 字节的 `uint32_t`；
   - **解密运算** $=$ 对 `[enc_offset, enc_offset + enc_len)` 区间内的每个字节执行 `~byte & 0xFF`。

我们只需写一个 10 行的脚本，就能在本地对两个 SO 的这段 `~byte` 加密区完成**静态完整还原**（保留磁盘文件原有的前 64 字节 ELF Header，并恢复该区间内的机器码）。函数数量只是 Ghidra 自动分析结果的变化，不能单独用来证明恢复出了加固前的原始 SO 或全部运行时语义：

| 目标 SO 库 | 文件总大小 | 文件尾 4 字节 (`enc_offset`) | ELF `+0x18` (`enc_len`) | 还原前 Ghidra 识别函数数 | **加密区还原后识别函数数** |
|---|---:|---:|---:|---:|---:|
| `libnetease_ssl.so` | 449,692 B (`0x6dc9c`) | **`0x000076a0`** (30,368) | **`0x00051f28`** (335,656 B) | 348 个（`JNI_OnLoad` 断流） | **940 个** |
| `libandroidmainruns.so` | 750,724 B (`0xb7484`) | **`0x0000c8a0`** (51,360) | **`0x00080850`** (526,416 B) | 392 个（主要导出函数断流） | **622 个** |

---

### Step 4：还原 `libnetease_ssl.so`——揭开 `RegisterNatives` 9 项映射与 Application 移交链

把静态脱壳后的 `libnetease_ssl_unpacked.so` 重新导入 Ghidra，此前报错 `halt_baddata()` 的 `JNI_OnLoad`（`0x0010fd8c`）瞬间露出了真面目：

```c
// Ghidra 反编译 libnetease_ssl_unpacked.so :: JNI_OnLoad @ 0x0010fd8c (size=344)
int JNI_OnLoad(JavaVM *vm) {
    JNIEnv *env = NULL;
    if ((*vm)->GetEnv(vm, (void **)&env, JNI_VERSION_1_4) != JNI_OK) {
        return -1;
    }
    // 1. 读取 Build.VERSION.SDK_INT 存入全局变量 DAT_0017f090（后续根据 API 版本分支加载 DEX）
    jclass verCls = (*env)->FindClass(env, "android/os/Build$VERSION");
    jfieldID sdkField = (*env)->GetStaticFieldID(env, verCls, "SDK_INT", "I");
    DAT_0017f090 = (*env)->GetStaticIntField(env, verCls, sdkField);

    // 2. 找到 ProxyApplication 类；本文 arm64 样本的 JNIEnv 函数表中，RegisterNatives 位于 +0x6b8
    jclass proxyCls = (*env)->FindClass(env, "com/netease/dexshell/ProxyApplication");
    int rc = (*env)->RegisterNatives(env, proxyCls, (const JNINativeMethod *)0x0017d130, 9);
    (*env)->DeleteLocalRef(env, proxyCls);
    return (rc < 0) ? -1 : JNI_VERSION_1_4;
}
```

顺着 `RegisterNatives` 的第三个参数 `0x0017d130`，我们在 Ghidra 中编写脚本读取 `.data` 段 `0x0017d130` 处的 9 个 `JNINativeMethod` 结构体（每个结构体包含 `name`、`signature`、`fnPtr` 三个指针；**本文 arm64 样本每项 24 字节，32 位环境则为 12 字节**），一次性把 Step 2 中那 9 个混淆 Native 方法的底层实现全部对上了号：

![Ghidra 12.1.4 — 还原 libnetease_ssl.so 动态注册表与 Application 控制权移交链](/images/当-AI-装上-REA-逆向工具箱-手把手拆穿一个商业级-Dex2C-加固-APK/shot05_libnetease_ssl_jninativemethods.png)

| 序号 | `ProxyApplication` 方法名 | JNI 签名 | Native 函数地址 | 逆向还原出的真实职责 |
|:---:|---|---|---|---|
| `[0]` | `IIO00IIOO0` | `(Ljava/lang/String;)V` | `0x0010c59c` | 在解密目录写出一个 292 字节（`0x124`）的空壳 `small.dex`（用于 Android 5.x `loadDex` 占位） |
| `[1]` | `IO0I0II00O` | `(Ljava/lang/String;)I` | `0x0010c658` | `setFileReadOnly`：调用 `chmod(path, 0444)` 将释放出的 DEX 设为只读（兼容 Android 14+ 动态代码加载安全要求） |
| `[2]` | `IOIOOI0` | `(Landroid/content/Context;Ljava/io/File;Ljava/io/File;)[Ljava/lang/Object;` | `0x0010d2a4` | `makeDex`：按 `SDK_INT` 分支反射调用 `DexPathList.makeDexElements()`，将 `enc_opt0.dex` 加载为 `Element[]` |
| `[3]` | `I00OO0OI` | `(Landroid/content/Context;[Ljava/lang/Object;)V` | `0x0010c9cc` | 反射获取 `BaseDexClassLoader.pathList.dexElements`，通过 `System.arraycopy` 将解密后的 `Element[]` 拼接注入 |
| `[4]` | `IOOO00IIII` | `(Landroid/content/Context;)V` | `0x0010f2ec` | 启动两个守护线程：`FUN_0010e490`（上报 `.xCrashLog` 崩溃日志）与 `FUN_0010f250`（反调试与环境检测） |
| `[5]` | `IOO0OO0IIo` | `(Landroid/content/Context;Ljava/util/ArrayList;Ljava/lang/String;Ljava/lang/String;)I` | `0x0010f8cc` | `doDexOpt`：拼接 `--dex-file=` 与 `--oat-file=` 参数，调用 `/system/bin/dex2oat` 执行 OAT 预编译 |
| `[6]` | `onCreate` | `()V` | `0x0010f464` | 调用 `FUN_0010cc48` 实例化原包 `DemoApplication`，完成四处系统级引用替换后调用其 `onCreate()` |
| `[7]` | `I0II0IIO00` | `(Landroid/content/res/AssetManager;Landroid/content/Context;)V` | `0x0010fc60` | 检查 `assets/baidu_loge.png`（`XOR 0xDD` 资源加密表），并通过 PLT Hook 拦截 `libandroidfw.so`（`memcpy`）与 `libutils.so`（`mmap64`）实现 DEX/资源流式解密 |
| `[8]` | `createPackageContext` | `(Ljava/lang/String;I)Landroid/content/Context;` | `0x0010f5b4` | 若 `delegate` 尚未绑定则先调用 `FUN_0010cc48` 绑定，防止 ContentProvider 或插件提前调用时拿不到真实 Application |

更精彩的是第 `[6]` 项 `onCreate`（`0x0010f464`）内部调用的 `FUN_0010cc48`（`0x0010cc48`，大小 1,628 字节）。它用纯 JNI 反射完成了教科书级的 **Application 偷梁换柱**：

```c
// Ghidra 反编译 libnetease_ssl_unpacked.so :: FUN_0010cc48 @ 0x0010cc48 (核心逻辑提炼)
void bindRealApplication_0010cc48(JNIEnv *env, jobject proxyApp) {
    // 1. 读取 ProxyApplication.II0OO0II0O 静态字段（即 "com.demo.reajiagu.DemoApplication"）
    jstring realAppName = getStaticObjectField(env, "com/netease/dexshell/ProxyApplication", "II0OO0II0O", "Ljava/lang/String;");
    jobject baseCtx = callObjectMethod(env, proxyApp, "android/app/Application", "getBaseContext", "()Landroid/content/Context;");

    // 2. 通过已注入主 DEX 的 ClassLoader 加载 DemoApplication 并调用 newInstance()
    jclass realAppCls = callStaticObjectMethod(env, "java/lang/Class", "forName", "(Ljava/lang/String;)Ljava/lang/Class;", realAppName);
    jobject delegateApp = callObjectMethod(env, realAppCls, "java/lang/Class", "newInstance", "()Ljava/lang/Object;");

    // 3. 保存到 ProxyApplication.delegate，并反射调用 DemoApplication.attach(baseCtx)
    setStaticObjectField(env, "com/netease/dexshell/ProxyApplication", "delegate", "Landroid/app/Application;", delegateApp);
    callObjectMethod(env, delegateApp, "android/app/Application", "attach", "(Landroid/content/Context;)V", baseCtx);

    // 4. 替换系统四处核心引用，让 Android 框架彻底遗忘 ProxyApplication 的存在：
    //   (a) ContextImpl.mOuterContext = delegateApp
    setObjectField(env, baseCtx, "android/app/ContextImpl", "mOuterContext", "Landroid/content/Context;", delegateApp);
    //   (b) ActivityThread.mInitialApplication = delegateApp
    jobject mainThread = getObjectField(env, baseCtx, "android/app/ContextImpl", "mMainThread", "Landroid/app/ActivityThread;");
    setObjectField(env, mainThread, "android/app/ActivityThread", "mInitialApplication", "Landroid/app/Application;", delegateApp);
    //   (c) ActivityThread.mAllApplications.remove(proxyApp) & add(delegateApp)
    jobject allApps = getObjectField(env, mainThread, "android/app/ActivityThread", "mAllApplications", "Ljava/util/ArrayList;");
    callBooleanMethod(env, allApps, "java/util/ArrayList", "remove", "(Ljava/lang/Object;)Z", proxyApp);
    callBooleanMethod(env, allApps, "java/util/ArrayList", "add", "(Ljava/lang/Object;)Z", delegateApp);
    //   (d) LoadedApk.mApplication = delegateApp & ApplicationInfo.className = realAppName
    jobject loadedApk = getObjectField(env, baseCtx, "android/app/ContextImpl", "mPackageInfo", "Landroid/app/LoadedApk;");
    setObjectField(env, loadedApk, "android/app/LoadedApk", "mApplication", "Landroid/app/Application;", delegateApp);
    jobject appInfo = getObjectField(env, loadedApk, "android/app/LoadedApk", "mApplicationInfo", "Landroid/content/pm/ApplicationInfo;");
    setObjectField(env, appInfo, "android/content/pm/ApplicationInfo", "className", "Ljava/lang/String;", realAppName);
}
```

至此，二代壳 `libnetease_ssl.so` 的核心加载链与 Application 移交链已基本还原。`FUN_0010f464` 在完成上述引用替换后调起 `delegate.onCreate()`（即 `DemoApplication.onCreate()`），执行流随后进入被 **Dex2C** 保护的 `libandroidmainruns.so` 以及业务自写的 `libreajiagu.so`。

---

### Step 5：决战 Dex2C 与业务 Native 库——为什么高强度壳仍挡不住未覆盖的业务短板？

我们把静态脱壳后的 `libandroidmainruns_unpacked.so`（750 KB，622 个函数）与原包自带的 `libreajiagu.so`（288 KB，907 个函数）同时放进 Ghidra 对比分析：

![Ghidra 12.1.4 — libandroidmainruns.so (Dex2C+OLLVM) 与 libreajiagu.so 算法逆向对比](/images/当-AI-装上-REA-逆向工具箱-手把手拆穿一个商业级-Dex2C-加固-APK/shot06_dex2c_and_native_bridge_decomp.png)

这一对比，直接暴露出了真实项目里最震撼的安全反差：

#### 5.1 易盾生成的 `libandroidmainruns.so`：武装到牙齿的四重防护

在 `libandroidmainruns_unpacked.so` 中，哪怕我们已经脱掉了最外层的 `_DT_INIT` 按位取反壳，里面依然躺着四道硬核防线：

1. **ELF Section 名称表混淆**：Ghidra 导入时，所有节区名（`.text`、`.rodata`、`.data`）全部被篡改为高字节乱码，阻止逆向工具按节区名快速定位常量池。
2. **原子自旋锁保护的 64-bit XOR 字符串加密池**：`libandroidmainruns.so` 中，多数 JNI 描述符、反射目标和字符串池内容不以明文出现，但导出符号仍可能泄露业务类名。反编译 `Java_com_demo_reajiagu_DemoApplication_initNeteaseXcrashMethod00__`（`0x0010ca34`）与 `FUN_00134964`（`0x00134964`）可以看到，**多个使用加密字符串的函数会在入口处通过 ARM64 独占访存指令（`ldaxr` / `stlxr`，Ghidra 反编译为 `ExclusiveMonitorPass`）争抢一个状态位（`0 -> 1 -> 2`），首个进入的线程把 `.data` 段密文与 `.rodata` 段的 64-bit 密钥流做异或解密**：
   - `0x001c3040 ^ 0x0018e700` $\implies$ `"java/lang/reflect/Proxy\0"`
   - `0x001c31f0 ^ 0x0018e780` $\implies$ `"java/lang/reflect/Method\0"`
   - `0x001c2140 ^ 0x0018de80` $\implies$ `"(Landroid/content/Context;Ljava/lang/String;Ljava/lang/String;ZZZZLjava/lang/String;Ljava/lang/String;Z)V"`
   - `0x001c21e0 ^ 0x0018def0` $\implies$ `"https://safe-log.166.net/interface/log/uploadFile\0"`
3. **OLLVM 控制流平坦化（Control Flow Flattening）+ 不透明谓词（Opaque Predicates）**：在核心转换函数 `FUN_00150a34`（`0x00150a34`，单函数长达 18,724 字节）中，正常的顺序/分支结构被彻底打碎成一个由 32 位状态变量 `iVar15`（初始种子 `-0x75a26df1`）驱动的巨型 `switch-case` 分发器，且多个控制流分发块之间插入了数论恒真/恒假谓词：
   ```c
   // 典型的 OLLVM 不透明谓词：相邻两个整数的乘积 (y - 1) * y 必定是偶数，因此 & 1 恒等于 0！
   uVar12 = (DAT_001c7ad4 + -1) * DAT_001c7ad4 & 1;
   bVar10 = 9 < DAT_001c7ad0 == uVar12 && (9 < DAT_001c7ad0 | uVar12) == 1;
   ```
   我们通过编写 Ghidra 脚本 `DecryptVMAndRefs.java` 扫描该函数内所有异或指令并自动配对 `.rodata` 密钥，才批量还原出它的 34 个 JNI 调用字符串（`java/util/zip/ZipEntry`、`getInputStream`、`java/io/ByteArrayOutputStream`、`toByteArray`、`assets/`、`classes` 等）。
4. **JNI 反射代理跳板（`FUN_00111c20` / `FUN_00112580` / `FUN_00114178`）**：本文分析的多个转换后函数不直接暴露明文 Java API 调用，而是经过 `FUN_00111c20` 等混淆跳板动态查找 `jclass` 与 `jmethodID`，并在 JNI 调用前后穿插 `FUN_0010ea04` 异常检查与局部引用销毁。

需要特别区分：**Dex2C、OLLVM 与 VMP 不是同一概念。** 上述证据支持“部分 Java 方法被 Native 化，并施加 OLLVM 控制流与字符串混淆”；OLLVM 是编译期混淆，不等于自定义虚拟机保护。虽然构建参数包含 `-useVmProtect true`，本文不据此断言具体函数已经过 VMP；若要下这个结论，还需另行定位 VM 字节码与解释分发语义。

#### 5.2 业务自写的 `libreajiagu.so`：无需额外脱壳的"木桶短板"

然而，当我们把目光转向开发者自己用 NDK 编译的 `libreajiagu.so` 时，画风突变！

虽然构建命令里开启了 `-useSoProtect default -useVmProtect true`，但**本次参数组合与平台版本只对厂商生成的壳 SO（`libnetease_ssl.so`）和 Dex2C 转换库（`libandroidmainruns.so`）施加了相应保护，业务工程自带的 `libreajiagu.so` 则原样保留**。这只能证明本次加固流程未覆盖业务 SO，不能据此推断该平台所有版本或配置都不支持业务 Native 保护。

于是，在 `libreajiagu.so` 中，Ghidra 无需额外脱壳，便可直接定位到导出符号 `Java_com_demo_reajiagu_NativeBridge_signPayloadNative`（`0x0011d770`）和 `verifyLicenseCodeNative`（`0x0011da60`），给出近乎源码级的 C 伪代码。这里强调的是**无需再做加密区还原和字符串解密**，不是整个 APK 的逆向总耗时只有一秒：

```c
// Ghidra 12.1.4 反编译 libreajiagu.so :: Java_com_demo_reajiagu_NativeBridge_signPayloadNative @ 0x0011d770
undefined8 Java_com_demo_reajiagu_NativeBridge_signPayloadNative
          (long *param_1, undefined8 param_2, long param_3, undefined8 param_4) {
    // ... 获取输入字符串并拼接 "|ts=%lld" ...
    FUN_0011d9bc(acStack_88, 0x20, 0x20, "|ts=%lld", param_4);
    std::__ndk1::basic_string::append(&local_e0, acStack_88);

    // 完整暴露 FNV-1a 初始种子 0x811c9dc5、素数乘数 0x1000193 以及 0x00114650 处的 16 字节盐值！
    uVar6 = 0x811c9dc5;
    for (sVar7 = 0; sVar7 != sVar4; sVar7++) {
        uVar6 = (uVar6 ^ ((&DAT_00114650)[sVar7 & 0xf] ^ puVar9[sVar7])) * 0x1000193;
    }
    FUN_0011d9bc(auStack_c8, 0x40, 0x40, "NSIG-%08X-%04X", uVar6, (uint)param_4 & 0xffff ^ 0xa5a5);
    return (**(code **)(*param_1 + 0x538))(param_1, auStack_c8);
}
```

更值得注意的是 `verifyLicenseCodeNative`（`0x0011da60`）：源码中的 `computeFnv1a32("REA-2026-PRO", 12)` 让 Clang `-O2` 能在编译期算出完整目标哈希 **`0xe44c0d32`**，并进一步利用乘法逆元改写最后一轮比较。下面伪代码中的 **`0xd205450d` 是改写后的派生比较常量，不是完整目标哈希**；同时，输入侧的多轮循环被展开成异或乘法嵌套表达式：

```c
// Ghidra 12.1.4 反编译 libreajiagu.so :: Java_com_demo_reajiagu_NativeBridge_verifyLicenseCodeNative @ 0x0011da60
if (sVar4 == 0xc) { // 长度必须为 12
    bVar2 = ((uint)pbVar5[0xb] ^
            ((uint)pbVar5[10] ^
             ((uint)pbVar5[9] ^
              ((uint)pbVar5[8] ^
               ((uint)pbVar5[7] ^
                ((uint)pbVar5[6] ^
                 ((uint)pbVar5[5] ^
                  ((uint)pbVar5[4] ^
                   ((uint)pbVar5[3] ^
                    ((uint)pbVar5[2] ^
                     ((uint)pbVar5[1] ^ (*pbVar5 ^ 0x811c9d97) * 0x1000193 ^ 0x45) * 0x1000193 ^
                    0x41) * 0x1000193 ^ 0x5f) * 0x1000193 ^ 0x4e) * 0x1000193 ^ 0x41) * 0x1000193 ^
                0x54) * 0x1000193 ^ 0x49) * 0x1000193 ^ 0x56) * 0x1000193 ^ 0x45) * 0x1000193 ^ 0x5f
            ) * 0x1000193) == 0xd205450d;
}
```

注意看上面这串展开式里的立即数序列：
- 首字节：`0x811c9d97` $=$ `0x811c9dc5 ^ 0x52`（`0x52` 即 `'R'`）
- 后续异或字节依次为：`0x45` (`'E'`), `0x41` (`'A'`), `0x5f` (`'_'`), `0x4e` (`'N'`), `0x41` (`'A'`), `0x54` (`'T'`), `0x49` (`'I'`), `0x56` (`'V'`), `0x45` (`'E'`), `0x5f` (`'_'`) —— **前 11 个字节连 `.rodata` 都不用查，直接嵌在指令立即数里拼出了 `"REA_NATIVE_"`！**

`0xd205450d` 的来源也能用同一套算法精确复核。FNV-1a 的乘法因子 `0x01000193` 在模 $2^{32}$ 下是奇数，其模逆元为 **`0x359c449b`**；盐数组第 11 项（从 0 开始计数）是 `0x4b`，即 `'K'`：

```text
完整目标哈希 = 0xe44c0d32
(0xe44c0d32 × 0x359c449b mod 2^32) XOR 0x4b = 0xd205450d
```

因此，编译器实际是在比较“输入末字节与前十一步状态的异或结果”和这个派生常量。模逆元可以辅助我们在**已知或枚举候选字节**时逆推中间状态，但不能消除未知输入字节的搜索空间，更不能从单个 32 位值唯一恢复 12 字节激活码。实际绕过此类教学校验仍需离线字典、约束求解或碰撞构造；而且 32 位 FNV 校验允许碰撞，并不等价于验证唯一的激活码明文。

---

## 四、量化对比与总结

### 4.1 加固前后制品指标与四层逆向实测总表

我们将本次实验中获取的全部实测数据汇总如下：

| 维度 / 指标 | 加固前 (`app-raw.apk`) | 加固后 (`app-protected-signed.apk`) | 逆向突破手段与实测耗时 |
|---|---|---|---|
| **APK 文件大小** | 474,946 B（463.81 KiB / 0.475 MB） | **3,397,416 B（3.397 MB / 3.240 MiB，+615%）** | `inspect_artifact` 完成归档节点比对 |
| **Manifest 入口 Application** | `com.demo.reajiagu.DemoApplication` | `com.netease.dexshell.ProxyApplication` | `inspect_android_package` 从 `meta-data[II0OI00IO]` 直接读出真实入口 |
| **`classes.dex` 大小与类数** | 7,428 B / 5 个业务类 | 35,356 B / 66 个壳与注解类（**0 个业务类**） | `inspect_android_method` 反编译 `IO00OI0o0` 破译 `XOR 0xBB` 索引解密 |
| **加密 DEX 载荷** | 无 | `assets/923ed6ec7b` (10 B) $\to$ `assets/a4f47ca30a` (94,404 B) | 异或 `0xBB` 还原文件名；通过 `libnetease_ssl.so` 的 `IOIOOI0` 还原加载链 |
| **二代壳引擎 `libnetease_ssl.so`** | 无 | 449,692 B（`.text` 偏移 `0x76a0` 起 335,656 B 被加密） | 逆向 `_DT_INIT` (`0x00159b7c`) 静态 `~byte` 脱壳，识别函数 **348 $\to$ 940 个** |
| **四代 Dex2C 库 `libandroidmainruns.so`** | 无 | 750,724 B（`.text` 偏移 `0xc8a0` 起 526,416 B 被加密） | 静态 `~byte` 脱壳识别函数 **392 $\to$ 622 个**；写 Ghidra 脚本批量解密 64-bit XOR 字符串池 |
| **业务自写库 `libreajiagu.so`** | 288,776 B (907 个函数) | **288,776 B（SHA-256 `c33c9a15...` 完全未变！）** | 无需额外脱壳，Ghidra 直接反编译 `0x0011d770` 与 `0x0011da60`，还原盐值与校验逻辑 |

![加固前后 APK 制品结构变化、加密区还原效果与四层制品结构短板诊断](/images/当-AI-装上-REA-逆向工具箱-手把手拆穿一个商业级-Dex2C-加固-APK/shot07_architecture_and_metrics.png)

### 4.2 速查表：用 REA 逆向加固 Android 应用的 5 步标准作业法（SOP）

```text
✅ 1. 先跑 inspect_android_package + inspect_artifact 建立全局证据账本
      看 Application 是否被替换为壳入口，查 meta-data 里的隐藏原入口，
      对比 assets/ 与 lib/ 下多出来的加密载荷与加壳 SO。

✅ 2. 用 inspect_android_method 拆解 Java 壳的 attachBaseContext
      常见壳的 Java 层通常负责三件事：读取 meta-data、释放/加载核心壳 SO、准备私有解密目录。
      凡是 body_status = not_available 的 native 方法，记下签名去壳 SO 里找对应实现。

✅ 3. 遇到主要函数反编译断流（halt_baddata），优先检查初始化路径
      查看 DT_INIT / DT_INIT_ARRAY 指向的代码是否包含自解密逻辑。
      本文样本可从初始化 Stub 得到 enc_offset 与 enc_len 公式并静态还原；
      若遇到按需解密或运行时校验，仍需动态分析，不能套用同一个公式。

✅ 4. 加密区还原后，检查 JNI_OnLoad 里的 RegisterNatives
      混淆后的 Java native 方法常通过 JNINativeMethod 数组批量动态注册。
      本文 arm64 样本的函数表偏移为 +0x6b8、每项 24 字节；
      32 位环境对应 +0x35c、每项 12 字节，不能机械照搬地址和结构大小。

✅ 5. 优先排查"未被加壳覆盖的业务自写 SO"，再去啃 Dex2C + OLLVM
      安全防线的强度取决于最短的那块木板。先用 SHA-256 比对业务自研 SO 是否被原样打包；
      必须分析 OLLVM + 字符串加密函数时，让 AI 写 Ghidra PostScript 批量跑 XOR 解密，不要人工手算。
```

### 4.3 方法论升华：从"手工作坊逆向"到"AI 证据驱动逆向"

回顾整场实战，如果我们用传统方式逆向这个加固包，光是在 `libnetease_ssl.so` 的 `halt_baddata()` 和 `libandroidmainruns.so` 的 18,000 字节 OLLVM 状态机里打转，就足以消耗掉一整天的时间。

而当 Claude Code 接上 REA 之后，人机协作的分工发生了质变：
- **AI + REA / 本地引擎负责"体力活与高精度取证"**：秒级清点 APK 归档图谱、反编译 Java 壳与 ELF 初始化 Stub、扫描 `0x0017d130` 的 `JNINativeMethod` 结构体表、编写 Ghidra 脚本批量解密数十处 64-bit XOR 字符串池，并把可复核的结论锚定在 `ev_<sha256>` 证据链上；
- **人类工程师负责"破局方向与架构洞察"**：指出从初始化 Stub 突破 SO 加密区、识别出"Dex2C 与 OLLVM 提高了分析成本，但业务自写 `libreajiagu.so` 未被本次流程覆盖"的木桶短板。

这也给我们自己的应用安全加固提了一个醒：**千万不要以为接入了商业级 Dex2C 加固就万事大吉。** 如果核心加解密、签名算子写在业务自研的 C++ `.so` 里，可以在 CMake 编译期开启 `-fvisibility=hidden`、Strip 符号表、采用 `RegisterNatives` 动态注册；若所用平台和版本支持，还应显式将该 `.so` 纳入 SO 加壳与 VMP 保护范围，否则需要自行补充 Native 保护。这些手段只是提高分析成本，不能替代服务端授权、密码学签名与密钥生命周期设计——否则，Java 层的高强度防护仍可能被未覆盖的 Native 侧翼绕过。

---

## 附录：验证工程与复现指南

**配套工程暂不公开，复现步骤见正文。**

该工程内含靶场全部源码、Ghidra 自动化逆向脚本、逆向结论证据账本与本文 7 张配图。出于合规考虑，其中不包含加固后的 APK 与脱壳后的 SO（它们内含第三方商业加固产品的代码）；这两类产物请按正文 Step 0 与 Step 3 的步骤在本地自行生成，产物的 SHA-256 摘要与函数数量已记录在下表与本工程 `results/FINDINGS.md` 中，可用于逐步自校验。

工程目录结构与各文件作用如下：

| 文件 / 目录 | 作用说明 |
|---|---|
| `app/src/main/java/com/demo/reajiagu/` | 靶场 Java 源码（`DemoApplication`、`MainActivity`、`TokenEngine`、`NativeBridge`） |
| `app/src/main/cpp/native-lib.cpp` | 靶场 C++ JNI 源码（加盐 FNV-1a 签名与激活码校验，编译产出 `libreajiagu.so`） |
| `apks/app-raw.apk` | 加固前 Release 基线包（474,946 B，SHA-256: `f56ad24b5b2f134e...`），仓库内可直接获取 |
| `apks/app-protected-signed.apk` | 使用 `microgameapp` 加固配置产出的易盾 Dex2C + VMP 加固重签包（3,397,416 B）——**本地加固生成** |
| `unpacked_so/libnetease_ssl_unpacked.so` | 按初始化 Stub 公式静态还原加密区后的二代壳 Loader SO（Ghidra 识别 940 个函数）——**本地还原生成** |
| `unpacked_so/libandroidmainruns_unpacked.so` | 按初始化 Stub 公式静态还原加密区后的四代 Dex2C 转换库 SO（Ghidra 识别 622 个函数）——**本地还原生成** |
| `InspectTables.java` / `InspectDeep.java` | Ghidra 自动脚本：解析 `0x0017d130` 处 9 项 `JNINativeMethod` 表并反编译核心函数 |
| `DecryptStrings.java` / `DecryptVMAndRefs.java` | Ghidra 自动脚本：批量解密 `libandroidmainruns.so` 中 64-bit XOR 字符串池与 OLLVM 函数常量 |
| `generate_shots.py` | 一键生成正文全部 7 张终端取证截图与量化对比图（输出至 `../images/`） |
| `results/FINDINGS.md` | 全部制品的 SHA-256、REA `evidence_id` 以及 H1–H5 逆向结论核对表 |
