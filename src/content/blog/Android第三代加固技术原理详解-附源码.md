---
title: "Android第三代加固技术原理详解（附源码）"
description: "Android三代加固通过代码抽取+运行时指令回填实现保护，使用ByteHook禁用dex2oat，Dobby Hook LoadMethod按需恢复指令，支持Android 7-15。"
pubDate: "2026-04-19"
tags: ['Android', '逆向']
---
## 前言

在上一篇[Android第二代加固技术原理详解（附源码）](https://juejin.cn/post/7589935326781669410 "https://juejin.cn/post/7589935326781669410")，我们详细介绍了二代加固的实现原理——**DEX不落地内存加载方案**。该方案通过`InMemoryDexClassLoader`直接在内存中加载DEX，避免了文件落地带来的安全风险。

然而，二代加固仍然存在一个关键缺陷：**内存中的DEX是完整的**。攻击者可以通过以下方式获取源程序代码：

1. **内存Dump**：使用GDB、Frida等工具在运行时Dump内存中的DEX
2. **Dump ClassLoader**：从`DexPathList.dexElements`中提取DEX数据
3. **Hook关键函数**：拦截`DexFile`相关函数获取DEX字节码

为了解决这一安全隐患，**三代加固应运而生**——核心思想是**代码抽取 + 运行时指令回填**。（本系列文章承前启后，为更好理解下文内容，建议先理解上一篇[Android第二代加固技术原理详解（附源码）](https://juejin.cn/post/7589935326781669410 "https://juejin.cn/post/7589935326781669410")，再看本文，可有事半功倍之效。）

---

## 二代 vs 三代：核心差异对比

| 特性 | 二代加固 (V2) | 三代加固 (V3) |
| --- | --- | --- |
| **DEX完整性** | 内存中DEX完整 | 内存中DEX方法体为空 |
| **安全性** | 较高（需内存dump） | 很高（dump得到空方法） |
| **核心机制** | `InMemoryDexClassLoader` | Native Hook + 指令回填 |
| **Hook框架** | 无 | ByteHook + Dobby |
| **最低版本** | Android 5.0+ (API 21) | Android 7.0+ (API 24) |
| **兼容性复杂度** | 高 | 极高（依赖ART内部结构） |

### 二代加固的安全缺陷回顾

```
// 二代加固：内存中DEX是完整的，可被Dump
ByteBuffer[] dexBuffers = extractDexFilesFromShellDex(shellDexData);

// 攻击者可以通过以下方式获取完整DEX：
// 1. Hook DexFile构造函数，拦截dexBuffers
// 2. 从ClassLoader的pathList.dexElements中提取
// 3. 使用Frida脚本在运行时Dump内存

// DEX数据完整存在于内存中，随时可能被窃取
```

### 三代加固的解决方案

```
// 三代加固：发布时抽取方法指令，运行时按需回填

// 发布阶段：
// 1. 解析DEX文件，抽取每个方法的insns（指令）
// 2. 将insns替换为return-void等空指令
// 3. 生成.codes文件保存抽取的指令

// 运行阶段：
// 1. ART加载DEX（此时方法体为空）
// 2. Hook LoadMethod，在方法加载前回填指令
// 3. ART解析得到完整的方法代码

// 攻击者Dump得到的DEX：方法体为空，无实际代码
```

---

## 三代加固的技术挑战

三代加固的核心是**指令抽取与运行时回填**，这带来了以下技术挑战：

### 1. DEX文件结构理解

必须深入理解DEX文件格式，准确定位方法的指令位置：

```
DEX文件结构：
┌─────────────────────────────────────────┐
│              Header (0x70)               │
├─────────────────────────────────────────┤
│              string_ids                  │
├─────────────────────────────────────────┤
│              type_ids                    │
├─────────────────────────────────────────┤
│              proto_ids                   │
├─────────────────────────────────────────┤
│              field_ids                   │
├─────────────────────────────────────────┤
│              method_ids                  │
├─────────────────────────────────────────┤
│              class_defs                  │
├─────────────────────────────────────────┤
│              data (包含CodeItem)         │
└─────────────────────────────────────────┘

CodeItem结构（方法的字节码）：
┌─────────────────────────────────────────┐
│ registers_size    │ 2 bytes             │
│ ins_size          │ 2 bytes             │
│ outs_size         │ 2 bytes             │
│ tries_size        │ 2 bytes             │
│ debug_info_off    │ 4 bytes             │
│ insns_size        │ 4 bytes             │
├─────────────────────────────────────────┤
│ insns[]           │ N * 2 bytes  ★指令★ │
└─────────────────────────────────────────┘
```

### 2. ART内部函数Hook

需要Hook ART的内部函数`ClassLinker::LoadMethod`，这涉及：

- C++符号名解析（名称修饰/Name Mangling）
- 不同Android版本的函数签名差异
- 结构体内存布局的版本适配

### 3. Android版本兼容性（7-16）

不同Android版本的ART实现差异巨大，本项目已实现 **Android 7 到 Android 15** 全版本覆盖：

| Android版本 | API Level | LoadMethod签名 | 结构体类型 |
| --- | --- | --- | --- |
| 7.0 - 7.1 | 24 - 25 | `(Thread, DexFile, ClassDataItemIterator, Handle, ArtMethod)` | ClassDataItemIterator |
| 8.0 - 8.1 | 26 - 27 | `(DexFile, ClassDataItemIterator, Handle, ArtMethod)` | ClassDataItemIterator |
| 9 | 28 | `(DexFile, ClassDataItemIterator, Handle, ArtMethod)` | ClassDataItemIterator |
| 10 | 29 | `(DexFile, ClassAccessor::Method, Handle, ArtMethod)` | ClassAccessor::Method |
| 11 - 14 | 30 - 34 | `(DexFile, ClassAccessor::Method, ObjPtr, ArtMethod)` | ClassAccessor::Method |
| 15 | 35 | `(DexFile, ClassAccessor::Method, ObjPtr, MethodAnnotationsIterator*, ArtMethod)` | ClassAccessor::Method |
| 16+ | 36+ | LoadMethod 被重构为内部类 `LoadClassHelper::LoadMethod`，符号被隐藏 | 不可行 |

### 4. dex2oat禁用

如果DEX被dex2oat编译为OAT，空方法体会被固化，运行时回填就无效了。必须禁用dex2oat，强制使用解释模式。

### 5. Android 14+ 安全限制

Android 14 引入了 **"禁止加载可写 DEX 文件"** 策略，需要在磁盘上设置只读、在内存中通过 mmap Hook 保持可写。

---

## 三代加固整体架构

### 与二代的模块对比

```
二代加固流程：
┌─────────────┐    ┌─────────────┐    ┌──────────────────────────┐
│  壳DEX      │    │加密源DEX集合 │    │  合并后的classes.dex     │
│             │ +  │(支持Multidex)│ => │  [壳DEX][加密DEXs][4字节]│
└─────────────┘    └─────────────┘    └──────────────────────────┘
                                                  │
                      运行时解密 → ByteBuffer[] → InMemoryDexClassLoader
                                     ↑
                              DEX不落地，内存加载

三代加固流程：
┌─────────────┐    ┌─────────────┐    ┌──────────────────────────┐
│  壳DEX      │    │加密源DEX集合 │    │  合并后的classes.dex     │
│             │ +  │(指令已抽取)  │ => │  [壳DEX][加密DEXs][4字节]│
└─────────────┘    └─────────────┘    └──────────────────────────┘
                                                  │
                            运行时解密 → 写入私有目录
                                     ↓
                    System.loadLibrary → Native Hook
                                     ↓
                    Hook LoadMethod → 指令回填 → DexClassLoader
                                     ↑
                            .codes文件保存抽取的指令
```

### 文件结构对比

```
二代加固产物：
├── classes.dex        # [壳代码][加密的完整DEX集合][大小]
└── lib/
    └── libxxx.so      # 原始Native库

三代加固产物：
├── classes.dex        # [壳代码][加密的抽取后DEX集合][大小]
├── assets/
│   ├── classes.dex.codes    # 第一个DEX的抽取指令
│   ├── classes2.dex.codes   # 第二个DEX的抽取指令
│   └── ...
└── lib/
    ├── libandroidshell.so   # 壳Native库（包含Hook逻辑）
    ├── libbytehook.so       # ByteHook PLT Hook框架
    └── libc++_shared.so     # C++标准库
```

---

## 模块一：Packer 加壳工具模块

> **相对二代的改动**：此模块有**核心新增**。主要变化是新增代码抽取功能，将方法的指令抽取出来生成`.codes`文件。

### 1.1 与二代的核心差异

| 对比项 | 二代加固 (V2) | 三代加固 (V3) |
| --- | --- | --- |
| **DEX处理** | 加密完整的DEX | 抽取指令后再加密 |
| **额外文件** | 无 | `.codes`文件 |
| **核心新增类** | 无 | `DexCodeExtractor` |
| **Manifest** | 指向 `ShellProxyApplicationV2` | 指向 `ShellProxyApplicationV3` |
| **lib 目录** | 不复制 | 复制壳APK的lib目录（含Hook SO） |

### 1.2 V3 加壳主流程

`ApkPacker.startV3Protection()` 方法执行以下步骤：

```
private void startV3Protection() throws Exception {
    // 1. 复制源APK所有文件（排除Manifest和DEX文件）
    FileUtils.copyDirectoryExclude(srcApkTempDir, newApkTempDir,
            "AndroidManifest.xml", "classes*.dex");

    // 2. 抽取源DEX文件的代码 → 生成 .codes 文件到 assets/
    Path assetsDir = newApkTempDir.resolve("assets");
    DexCodeExtractor.extractAllDexFiles(srcApkTempDir, assetsDir);

    // 3. 复制壳APK的lib库文件（包含ByteHook + Dobby的Hook SO）
    Path shellLibDir = shellApkTempDir.resolve("lib");
    Path newLibDir = newApkTempDir.resolve("lib");
    FileUtils.copyDirectory(shellLibDir.toFile(), newLibDir.toFile());

    // 4. 修改AndroidManifest.xml
    //    - 将Application替换为 com.csh.shell.ShellProxyApplicationV3
    //    - 将原Application类名保存到 APPLICATION_CLASS_NAME meta-data
    //    - 确保 extractNativeLibs=true（需要释放SO文件）
    handleManifestV3(srcApkTempDir, shellApkTempDir, newApkTempDir);

    // 5. 合并壳DEX和源DEX（源DEX已被抽取代码，然后XOR 0xFF加密）
    DexProcessor.combineShellAndSourceDexs(shellApkTempDir, srcApkTempDir, newApkTempDir);
}
```

### 1.3 代码抽取核心原理

`DexCodeExtractor` 是三代加固的核心类，负责解析DEX文件并抽取方法指令。

#### DEX头部偏移常量

```
public class DexCodeExtractor {
    private static final byte[] DEX_MAGIC = {0x64, 0x65, 0x78, 0x0a}; // "dex\n"
    private static final int HEADER_SIZE = 0x70;

    // DEX头部各区域的偏移量
    private static final int STRING_IDS_SIZE_OFF = 0x38;
    private static final int STRING_IDS_OFF = 0x3C;
    private static final int TYPE_IDS_SIZE_OFF = 0x40;
    private static final int TYPE_IDS_OFF = 0x44;
    private static final int PROTO_IDS_OFF = 0x4C;
    private static final int METHOD_IDS_OFF = 0x5C;
    private static final int CLASS_DEFS_SIZE_OFF = 0x60;
    private static final int CLASS_DEFS_OFF = 0x64;

    // CodeItem 结构偏移
    private static final int CODE_ITEM_INSNS_SIZE_OFF = 12; // insns_size 距离 CodeItem 头部偏移
    private static final int CODE_ITEM_INSNS_OFF = 16;      // insns[] 距离 CodeItem 头部偏移
```

#### 系统类过滤

抽取时会跳过所有系统库的类，只抽取应用自身代码：

```
private static final String[] SYSTEM_CLASS_PREFIXES = {
    "Ljava/",              // Java标准库
    "Ljavax/",             // Java扩展库
    "Landroid/",           // Android SDK
    "Landroidx/",          // AndroidX库
    "Ldalvik/",            // Dalvik
    "Lkotlin/",            // Kotlin标准库
    "Lkotlinx/",           // Kotlin扩展库
    "Lcom/google/android/", // Google Android库
    "Lorg/apache/",        // Apache库
    "Lorg/json/",          // JSON库
    "Lorg/xml/",           // XML库
    "Lorg/w3c/",           // W3C库
    "Lsun/",               // Sun库
    "Llibcore/",           // Android libcore
};
```

#### 数据结构

```
// 抽取结果
public static class ExtractionResult {
    public byte[] patchedDex;    // 抽取后的DEX（方法体已替换为空指令）
    public byte[] codesData;     // .codes文件的二进制数据
    public int extractedCount;   // 抽取的方法数量
    public int skippedClasses;   // 跳过的系统类数量
}

// 单个方法的抽取信息
private static class ExtractedCode {
    int codeOff;      // CodeItem在DEX文件中的偏移
    int insnsSize;    // 指令数量（以2字节为单位）
    byte[] insns;     // 原始指令字节码
}

// DEX解析上下文
private static class DexContext {
    byte[] dexData;          // 原始DEX数据
    byte[] patchedDex;       // 修改后的DEX（深拷贝）
    ByteBuffer buffer;       // 便于小端序读取
    String[] stringTable;    // 字符串表
    int[] typeIds;           // 类型ID表
    int protoIdsOff;         // proto_ids起始偏移
    int methodIdsOff;        // method_ids起始偏移
}
```

#### 核心抽取算法

完整的抽取流程分为5个步骤：

```
public static ExtractionResult extractCodes(byte[] dexData, String dexFileName) {
    // 1. 验证DEX魔数
    if (!verifyDexMagic(dexData)) throw new IllegalArgumentException("无效的DEX文件");

    DexContext ctx = new DexContext(dexData);

    // 2. 解析字符串表和类型表
    parseStringTable(ctx);   // string_ids → MUTF-8 字符串
    parseTypeIds(ctx);       // type_ids → 类型描述符索引
    ctx.protoIdsOff = ctx.buffer.getInt(PROTO_IDS_OFF);
    ctx.methodIdsOff = ctx.buffer.getInt(METHOD_IDS_OFF);

    // 3. 遍历所有类定义（每个ClassDef 32字节）
    int classDefsSize = ctx.buffer.getInt(CLASS_DEFS_SIZE_OFF);
    int classDefsOff = ctx.buffer.getInt(CLASS_DEFS_OFF);

    for (int i = 0; i < classDefsSize; i++) {
        int classDefOff = classDefsOff + (i * 32);
        int classIdx = ctx.buffer.getInt(classDefOff);
        String className = getClassName(ctx, classIdx);

        if (isSystemClass(className)) continue;  // 跳过系统类

        int classDataOff = ctx.buffer.getInt(classDefOff + 24);
        if (classDataOff == 0) continue;

        // 4. 解析ClassData，抽取每个方法的指令
        extractMethodsFromClassData(ctx, classDataOff, extractedCodes);
    }

    // 5. 生成.codes文件数据
    byte[] codesData = generateCodesDataLegacy(extractedCodes);
    return new ExtractionResult(ctx.patchedDex, codesData, extractedCodes.size(), skippedClasses);
}
```

#### ClassData 解析与方法遍历

ClassData 使用 ULEB128 变长编码，方法索引使用差值编码：

```
private static void extractMethodsFromClassData(DexContext ctx,
        int classDataOff, List<ExtractedCode> extractedCodes) {

    int offset = classDataOff;

    // 读取4个ULEB128编码的头部字段
    int staticFieldsSize = readULEB128(ctx.dexData, offset);
    int instanceFieldsSize = readULEB128(ctx.dexData, offset);
    int directMethodsSize = readULEB128(ctx.dexData, offset);
    int virtualMethodsSize = readULEB128(ctx.dexData, offset);

    // 跳过字段定义（每个字段有 field_idx_diff + access_flags 两个ULEB128）
    // ...

    // 处理direct methods和virtual methods
    offset = extractMethodCodes(ctx, offset, directMethodsSize, extractedCodes);
    extractMethodCodes(ctx, offset, virtualMethodsSize, extractedCodes);
}

private static int extractMethodCodes(DexContext ctx,
        int offset, int methodsSize, List<ExtractedCode> extractedCodes) {

    int methodIdx = 0;  // 方法索引使用差值编码

    for (int i = 0; i < methodsSize; i++) {
        int methodIdxDiff = readULEB128(ctx.dexData, offset);
        methodIdx += methodIdxDiff;  // 累加差值得到真实索引
        int accessFlags = readULEB128(ctx.dexData, offset);
        int codeOff = readULEB128(ctx.dexData, offset);

        if (codeOff != 0 && !isNativeOrAbstract(accessFlags)) {
            String methodName = getMethodName(ctx, methodIdx);
            String returnType = getMethodReturnType(ctx, methodIdx);

            // ★ 关键：跳过 <init> 和 <clinit>
            // <init> 必须调用父类构造函数，不能简单替换
            // <clinit> 可能初始化静态字段，替换后类无法正常使用
            if ("<init>".equals(methodName) || "<clinit>".equals(methodName)) {
                continue;
            }

            extractSingleMethod(ctx, codeOff, extractedCodes, returnType);
        }
    }
    return offset;
}
```

#### 获取方法返回类型

为了生成正确的空方法体，需要查找方法的返回类型。查找链路：`method_ids` → `proto_ids` → `type_ids` → `string_ids`：

```
private static String getMethodReturnType(DexContext ctx, int methodIdx) {
    // method_id_item (8字节): [class_idx(2B)][proto_idx(2B)][name_idx(4B)]
    int methodIdOff = ctx.methodIdsOff + (methodIdx * 8);
    int protoIdx = ctx.buffer.getShort(methodIdOff + 2) & 0xFFFF;

    // proto_id_item (12字节): [shorty_idx(4B)][return_type_idx(4B)][parameters_off(4B)]
    int protoIdOff = ctx.protoIdsOff + (protoIdx * 12);
    int returnTypeIdx = ctx.buffer.getInt(protoIdOff + 4);

    return getClassName(ctx, returnTypeIdx);  // 如 "V", "I", "Ljava/lang/String;"
}
```

### 1.4 方法指令抽取与空方法体填充

抽取单个方法的指令后，需要根据返回类型填充正确的 Dalvik 返回指令，否则 ART 验证器会报 `VerifyError`：

```
private static void extractSingleMethod(DexContext ctx,
        int codeOff, List<ExtractedCode> extractedCodes, String returnType) {

    int insnsSize = ctx.buffer.getInt(codeOff + CODE_ITEM_INSNS_SIZE_OFF);
    if (insnsSize <= 0) return;

    int insnsBytes = insnsSize * 2;           // insnsSize 以2字节为单位
    int insnsOff = codeOff + CODE_ITEM_INSNS_OFF;  // +16 到达 insns[]

    // 保存原始指令
    byte[] insns = new byte[insnsBytes];
    System.arraycopy(ctx.dexData, insnsOff, insns, 0, insnsBytes);
    extractedCodes.add(new ExtractedCode(codeOff, insnsSize, insns));

    // 用nop填充整个指令区域，再根据返回类型填充返回指令
    Arrays.fill(ctx.patchedDex, insnsOff, insnsOff + insnsBytes, (byte) 0x00);
    fillReturnInstruction(ctx.patchedDex, insnsOff, insnsBytes, returnType);
}
```

**返回类型与指令映射表**：

| 返回类型 | 描述符 | 填充的指令 | 字节 |
| --- | --- | --- | --- |
| void | `V` | `return-void` | `0x0e 0x00` (2B) |
| boolean/byte/char/short/int/float | `Z/B/C/S/I/F` | `const/4 v0, 0` + `return v0` | `0x12 0x00 0x0f 0x00` (4B) |
| long/double | `J/D` | `const-wide/16 v0, 0` + `return-wide v0` | `0x16 0x00 0x00 0x00 0x10 0x00` (6B) |
| object/array | `L.../[...` | `const/4 v0, 0` + `return-object v0` | `0x12 0x00 0x11 0x00` (4B) |

### 1.5 .codes文件格式

`.codes`文件使用紧凑的二进制格式，没有文件头，直接由多条记录连续排列：

```
.codes文件格式（Legacy格式，无文件头）：
┌────────────────────────────────────────────────────────────────┐
│ [codeOff(4B LE)][insnsSize(4B LE)][insns(insnsSize*2 B)]      │
│ [codeOff(4B LE)][insnsSize(4B LE)][insns(insnsSize*2 B)]      │
│ ... 重复 ...                                                   │
└────────────────────────────────────────────────────────────────┘

字段说明：
- codeOff:   方法的CodeItem在DEX文件中的偏移（小端序）
- insnsSize: 指令数量（单位：2字节，小端序）
- insns:     原始的Dalvik指令字节码

示例（一个方法）：
┌────────────┬────────────┬──────────────────────────┐
│ B4 4D 00 00│ 10 00 00 00│ 1A 08 00 94 05 0E 00 ... │
│ codeOff    │ insnsSize  │ insns (16个指令单元=32B)  │
│ = 0x4DB4   │ = 0x10     │                           │
└────────────┴────────────┴──────────────────────────┘
```

### 1.6 DEX文件修复

抽取指令后修改了DEX内容，必须修复三个头部字段：

```
private static void fixDexFile(byte[] dexData) throws NoSuchAlgorithmException {
    // 1. 修复 file_size（偏移32处，4字节）
    byte[] fileSizeBytes = intToLittleEndian(dexData.length);
    System.arraycopy(fileSizeBytes, 0, dexData, 32, 4);

    // 2. 修复 signature（SHA-1，偏移12处，20字节）
    // 对偏移32到文件末尾的数据计算SHA-1
    MessageDigest sha1 = MessageDigest.getInstance("SHA-1");
    sha1.update(dexData, 32, dexData.length - 32);
    byte[] signature = sha1.digest();
    System.arraycopy(signature, 0, dexData, 12, 20);

    // 3. 修复 checksum（Adler32，偏移8处，4字节）
    // 对偏移12到文件末尾的数据计算Adler32
    Adler32 adler32 = new Adler32();
    adler32.update(dexData, 12, dexData.length - 12);
    int checksum = (int) adler32.getValue();
    System.arraycopy(intToLittleEndian(checksum), 0, dexData, 8, 4);
}
```

---

## 模块二：Shell-App 壳程序模块（Native层）

> **相对二代的改动**：此模块是**核心改动模块**。三代加固的主要工作在Native层完成，包括：
>
> 1. **Hook execve**：禁用dex2oat编译
> 2. **Hook mmap**：使DEX文件内存可写
> 3. **Hook LoadMethod**：核心指令回填逻辑

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Shell Native Layer                           │
├─────────────────────────────────────────────────────────────────────┤
│  Java层: ShellProxyApplicationV3                                   │
│    ├── loadShellNativeLibrary()    加载SO，触发Hook                │
│    ├── initEnvironments()          释放DEX和.codes文件             │
│    ├── initNativeAndLoadCodes()    JNI加载.codes到codeMapList      │
│    └── replaceClassLoader()        替换ClassLoader                 │
├─────────────────────────────────────────────────────────────────────┤
│  Native层: shell.cpp (2087行)                                      │
│    ├── _init()              SO构造函数，比JNI_OnLoad更早执行       │
│    ├── hookExecve()         (ByteHook PLT Hook) 禁用dex2oat       │
│    ├── hookMmap()           (ByteHook PLT Hook) 使DEX可写         │
│    ├── hookLoadMethod()     (Dobby Inline Hook) 6版本分发 ★核心★  │
│    ├── refillInstructions() 指令回填（路径匹配+memcpy）           │
│    └── JNI接口: init/loadCodesFile/getLoadedCodesCount/...        │
├─────────────────────────────────────────────────────────────────────┤
│  头文件:                                                           │
│    ├── dex/DexFile.h        DexFile结构偏移（5个版本命名空间）     │
│    ├── dex/class_accessor.h ClassAccessor::Method偏移             │
│    └── dex/CodeItem.h       抽取代码项（完整的Rule of Five实现）   │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Hook框架

三代加固使用两个Hook框架：

| Hook框架 | 类型 | 用途 | 原理 | 集成方式 |
| --- | --- | --- | --- | --- |
| **ByteHook** | PLT Hook | Hook libc函数 (execve, mmap) | 修改GOT/PLT表 | Gradle依赖 + Prefab |
| **Dobby** | Inline Hook | Hook ART内部函数 (LoadMethod) | 修改函数入口指令 | 预编译静态库 (libdobby.a) |

```
// shell.cpp 条件编译
#ifdef USE_BYTEHOOK
#include <bytehook.h>  // 字节跳动 PLT Hook
#endif

#ifdef USE_DOBBY
#include "dobby/dobby.h"  // 腾讯 Inline Hook
#else
// Dobby不可用时提供空实现
inline int DobbyHook(void*, void*, void**) { return -1; }
inline void* DobbySymbolResolver(const char*, const char*) { return nullptr; }
#endif
```

**CMakeLists.txt 中的集成方式**：

- Dobby: 预编译静态库 `shell-app/libs/${ABI}/libdobby.a`，作为 `STATIC IMPORTED` 目标
- ByteHook: 优先尝试静态库，回退到 Prefab（`find_package(bytehook CONFIG)`）

### 2.3 全局变量

```
static bool g_initialized = false;  // 防重入标志
static int APILevel = 0;             // 运行时获取的API Level
static const std::string codeFilePostfix = ".codes";

// 二级映射表: DEX路径 → (codeOff → CodeItem)
static std::map<std::string, std::map<uint32_t, CodeItem>> codeMapList;

// 6个版本的原始LoadMethod函数指针
static void (*g_originLoadMethodV24)(...) = nullptr;  // Android 7.0-7.1
static void (*g_originLoadMethodV26)(...) = nullptr;  // Android 8.0-8.1
static void (*g_originLoadMethodV28)(...) = nullptr;  // Android 9
static void (*g_originLoadMethodV29)(...) = nullptr;  // Android 10
static void (*g_originLoadMethodV30)(...) = nullptr;  // Android 11-14
static void (*g_originLoadMethodV35)(...) = nullptr;  // Android 15
```

### 2.4 SO初始化入口

`_init()` 使用 `__attribute__((constructor))` 属性，在 SO 被 `System.loadLibrary` 加载时自动执行，**比 JNI\_OnLoad 更早**：

```
extern "C" __attribute__((constructor))
void _init() {
    if (g_initialized) return;  // 防重入
    g_initialized = true;

    APILevel = android_get_device_api_level();
    LOGI("Android API Level: %d", APILevel);

    doHook();  // 执行所有Hook
}

static void doHook() {
#ifdef USE_BYTEHOOK
    bytehook_init(BYTEHOOK_MODE_AUTOMATIC, false);
#endif
    hookExecve();     // 1. 禁用dex2oat
    hookMmap();       // 2. 使DEX内存可写
    hookLoadMethod(); // 3. 核心指令回填
}
```

### 2.5 Hook execve - 禁用dex2oat

```
static int fakeExecve(const char *pathname, char *const argv[], char *const envp[]) {
    BYTEHOOK_STACK_SCOPE();  // ByteHook栈管理（防递归）

    // 检测是否是dex2oat进程
    if (pathname != nullptr && strstr(pathname, "dex2oat") != nullptr) {
        LOGI("Blocked dex2oat execution: %s", pathname);
        errno = EACCES;  // Permission denied
        return -1;        // 返回错误
    }

    return BYTEHOOK_CALL_PREV(fakeExecve, pathname, argv, envp);
}

static void hookExecve() {
    bytehook_hook_single(
        getArtLibName(),     // 调用者: "libart.so"(API<29) 或 "libartbase.so"(API>=29)
        "libc.so",           // 被调用者
        "execve",            // 函数名
        (void *)fakeExecve,  // 替换函数
        nullptr, nullptr);
}
```

### 2.6 Hook mmap - 使DEX内存可写

```
static void* fakeMmap(void *addr, size_t size, int prot, int flags, int fd, off_t offset) {
    BYTEHOOK_STACK_SCOPE();

    int newProt = prot;
    bool hasRead = (prot & PROT_READ) == PROT_READ;
    bool hasWrite = (prot & PROT_WRITE) == PROT_WRITE;

    // 对所有只读映射添加写权限
    // 这确保DEX文件映射后内存可写，允许指令回填
    if (hasRead && !hasWrite) {
        newProt |= PROT_WRITE;
    }

    return BYTEHOOK_CALL_PREV(fakeMmap, addr, size, newProt, flags, fd, offset);
}
```

### 2.7 libart.so 路径适配

不同Android版本的libart.so路径不同：

```
static const char* getArtLibPath() {
    if (APILevel < 29) {
        // Android 9及以下: /system/lib[64]/libart.so
#if defined(__LP64__)
        return "/system/lib64/libart.so";
#else
        return "/system/lib/libart.so";
#endif
    } else if (APILevel == 29) {
        // Android 10: /apex/com.android.runtime/lib[64]/libart.so
        return "/apex/com.android.runtime/lib64/libart.so";  // 64位示例
    } else {
        // Android 11+: /apex/com.android.art/lib[64]/libart.so
        return "/apex/com.android.art/lib64/libart.so";      // 64位示例
    }
}
```

### 2.8 LoadMethod 符号查找（三级策略）

LoadMethod 是 C++ 函数，经过名称修饰（Name Mangling），不同版本的符号名不同。使用三级策略查找：

```
// 已知符号列表
static const char* KNOWN_LOAD_METHOD_SYMBOLS[] = {
    // Android 11-14 (API 30-34) - ObjPtr<mirror::Class>
    "_ZN3art11ClassLinker10LoadMethodERKNS_7DexFileERKNS_13ClassAccessor6MethodENS_6ObjPtrINS_6mirror5ClassEEEPNS_9ArtMethodE",
    // Android 10 (API 29) - Handle<mirror::Class>
    "_ZN3art11ClassLinker10LoadMethodERKNS_7DexFileERKNS_13ClassAccessor6MethodENS_6HandleINS_6mirror5ClassEEEPNS_9ArtMethodE",
    // Android 9 (API 28) - ClassDataItemIterator
    "_ZN3art11ClassLinker10LoadMethodERKNS_7DexFileERKNS_21ClassDataItemIteratorENS_6HandleINS_6ObjPtrINS_6mirror5ClassEEEEEPNS_9ArtMethodE",
    // Android 7-8 (API 24-27) - 有 Thread* 参数
    "_ZN3art11ClassLinker10LoadMethodEPNS_6ThreadERKNS_7DexFileERKNS_21ClassDataItemIteratorENS_6HandleINS_6mirror5ClassEEEPNS_9ArtMethodE",
    // Android 15+ 可能的符号
    "_ZN3art11ClassLinker10LoadMethodERKNS_7DexFileERKNS_13ClassAccessor6MethodEPNS_9ArtMethodE",
    nullptr
};

static const char* getClassLinkerLoadMethodSymbol() {
    const char* artPath = getArtLibPath();

    // 策略1: 从ELF文件的SHT_STRTAB节中搜索同时包含"ClassLinker"和"LoadMethod"的字符串
    const char* sym = find_symbol_in_elf_file(artPath, 2, "ClassLinker", "LoadMethod");
    if (sym != nullptr) return sym;

    // 策略2: dlopen libart.so + dlsym 尝试已知符号列表
    void* artHandle = dlopen(artPath, RTLD_NOW);
    for (int i = 0; KNOWN_LOAD_METHOD_SYMBOLS[i] != nullptr; i++) {
        void* addr = dlsym(artHandle, KNOWN_LOAD_METHOD_SYMBOLS[i]);
        if (addr != nullptr) { dlclose(artHandle); return KNOWN_LOAD_METHOD_SYMBOLS[i]; }
    }
    dlclose(artHandle);

    // 策略3: Dobby 符号解析器（可能绕过某些dlsym限制）
    for (int i = 0; KNOWN_LOAD_METHOD_SYMBOLS[i] != nullptr; i++) {
        void* addr = DobbySymbolResolver(artPath, KNOWN_LOAD_METHOD_SYMBOLS[i]);
        if (addr != nullptr) return KNOWN_LOAD_METHOD_SYMBOLS[i];
    }

    return nullptr;
}
```

**ELF符号搜索的实现原理**：解析 libart.so 的 ELF 文件结构，遍历所有 `SHT_STRTAB` 类型的节（Section），在字符串表中查找同时包含所有关键字的符号名。这是最灵活的策略，能找到编译时未预见的符号变体。

### 2.9 结构体偏移适配

不同版本使用不同的结构体获取 `code_off`：

```
// dex/class_accessor.h

// ClassAccessor::Method (Android 10+, 64-bit) - 已通过运行时dump验证
namespace ClassAccessorMethodOffsets {
    constexpr size_t DEX_FILE = 0;           // +0x00: DexFile& (8B)
    constexpr size_t PTR_POS = 8;            // +0x08: uint8_t* (8B)
    constexpr size_t INDEX = 0x18;           // +0x18: uint32_t method_idx
    constexpr size_t ACCESS_FLAGS = 0x1c;    // +0x1c: uint32_t
    constexpr size_t HIDDENAPI_FLAGS = 0x20; // +0x20: uint32_t
    constexpr size_t IS_STATIC_OR_DIRECT = 0x24; // +0x24: bool + padding
    constexpr size_t CODE_OFF = 0x28;        // +0x28: uint32_t ★ 已验证 ★
}

// ClassDataItemIterator (Android 7-9, 64-bit) - 已通过运行时dump验证
namespace ClassDataItemIteratorOffsets {
    constexpr size_t METHOD_IDX = 0x14;
    constexpr size_t ACCESS_FLAGS = 0x18;
    constexpr size_t CODE_OFF = 0x20;        // ★ 已验证 ★
}

// DexFile 偏移 - begin_ 所有版本一致，location_ 需要区分
// Android 7-8:  location_ 在 +0x18 (24)，没有 data_begin_/data_size_
// Android 9+:   location_ 在 +0x28 (40)，有 data_begin_(+0x18) 和 data_size_(+0x20)
```

辅助函数提供安全的字段访问：

```
inline uint32_t getMethodCodeOff(const void* method) {
    return *(uint32_t*)((uint8_t*)method + 0x28);
}

inline uint32_t getClassDataCodeOff(const void* it) {
    return *(uint32_t*)((uint8_t*)it + 0x20);
}

inline const uint8_t* getDexFileBegin(const void* dexFile, int apiLevel) {
    return *(const uint8_t**)((uint8_t*)dexFile + 8);  // 所有版本一致
}

inline const std::string& getDexFileLocation(const void* dexFile, int apiLevel) {
    size_t offset = (apiLevel >= 28) ? 40 : 24;  // Android 9+ vs 7-8
    return *(const std::string*)((uint8_t*)dexFile + offset);
}
```

### 2.10 Hook LoadMethod - 核心指令回填

#### 6个版本的Hook函数

```
// Android 7.0-7.1 (API 24-25) - 有额外的 Thread* self 参数
static void newLoadMethodV24(void* thiz, void* self, const DexFile* dex_file,
                              const ClassDataItemIterator* it, void* klass, void* dest) {
    if (g_originLoadMethodV24 != nullptr) {
        refillInstructions(dex_file, getClassDataCodeOff(it));
        g_originLoadMethodV24(thiz, self, dex_file, it, klass, dest);  // 注意 self 参数
    }
}

// Android 8.0-8.1 (API 26-27) - 移除 Thread* 参数
static void newLoadMethodV26(void* thiz, const DexFile* dex_file,
                              const ClassDataItemIterator* it, void* klass, void* dest) {
    if (g_originLoadMethodV26 != nullptr) {
        refillInstructions(dex_file, getClassDataCodeOff(it));
        g_originLoadMethodV26(thiz, dex_file, it, klass, dest);
    }
}

// Android 9 (API 28) - 仍使用 ClassDataItemIterator
static void newLoadMethodV28(void* thiz, const DexFile* dex_file,
                              const ClassDataItemIterator* it, void* klass, void* dest) {
    if (g_originLoadMethodV28 != nullptr) {
        refillInstructions(dex_file, getClassDataCodeOff(it));
        g_originLoadMethodV28(thiz, dex_file, it, klass, dest);
    }
}

// Android 10 (API 29) - 切换为 ClassAccessor::Method
static void newLoadMethodV29(void* thiz, const DexFile* dex_file,
                              ClassAccessor::Method* method, void* klass, void* dest) {
    if (g_originLoadMethodV29 != nullptr) {
        refillInstructions(dex_file, getMethodCodeOff(method));
        g_originLoadMethodV29(thiz, dex_file, method, klass, dest);
    }
}

// Android 11-14 (API 30-34) - klass 变为 ObjPtr
static void newLoadMethodV30(void* thiz, const DexFile* dex_file,
                              ClassAccessor::Method* method, void* klass, void* dest) {
    if (g_originLoadMethodV30 != nullptr) {
        refillInstructions(dex_file, getMethodCodeOff(method));
        g_originLoadMethodV30(thiz, dex_file, method, klass, dest);
    }
}

// Android 15 (API 35) - 新增 MethodAnnotationsIterator* 参数
static void newLoadMethodV35(void* thiz, const DexFile* dex_file,
                              ClassAccessor::Method* method, void* klass, void* mai, void* dest) {
    if (g_originLoadMethodV35 != nullptr) {
        refillInstructions(dex_file, getMethodCodeOff(method));
        g_originLoadMethodV35(thiz, dex_file, method, klass, mai, dest);  // 注意 mai 参数
    }
}
```

#### Hook安装（版本分发）

```
static void hookLoadMethod() {
    const char* symbol = getClassLinkerLoadMethodSymbol();
    void* loadMethodAddress = DobbySymbolResolver(getArtLibPath(), symbol);

    // 通过符号名特征检测版本
    bool isAndroid15 = (strstr(symbol, "MethodAnnotationsIterator") != nullptr);
    bool isAndroid7 = (strstr(symbol, "PNS_6ThreadE") != nullptr);

    int result;
    if (isAndroid15) {
        result = DobbyHook(loadMethodAddress, (void*)newLoadMethodV35, (void**)&g_originLoadMethodV35);
    } else if (isAndroid7) {
        result = DobbyHook(loadMethodAddress, (void*)newLoadMethodV24, (void**)&g_originLoadMethodV24);
    } else if (APILevel >= 30) {
        result = DobbyHook(loadMethodAddress, (void*)newLoadMethodV30, (void**)&g_originLoadMethodV30);
    } else if (APILevel >= 29) {
        result = DobbyHook(loadMethodAddress, (void*)newLoadMethodV29, (void**)&g_originLoadMethodV29);
    } else if (APILevel >= 28) {
        result = DobbyHook(loadMethodAddress, (void*)newLoadMethodV28, (void**)&g_originLoadMethodV28);
    } else {
        result = DobbyHook(loadMethodAddress, (void*)newLoadMethodV26, (void**)&g_originLoadMethodV26);
    }
}
```

#### 指令回填核心逻辑

`refillInstructions` 是最关键的函数，处理 DEX 路径匹配和指令写回：

```
static void refillInstructions(const DexFile* dexFile, uint32_t code_off) {
    // 1. 获取DEX文件路径和内存基址
    const std::string& location = getDexFileLocation(dexFile, APILevel);
    const uint8_t* dexBegin = getDexFileBegin(dexFile, APILevel);

    // 2. 路径匹配 - 判断是否是我们的DEX文件
    // 支持多种路径模式：
    //   - "tmp_dex"       → DexClassLoader加载的文件
    //   - "memory_dex"    → CompatInMemoryDexClassLoader的临时文件（Android 7）
    //   - "dex_temp/dex_opt" → 内存加载的临时路径
    //   - "Anonymous-DexFile/InMemoryDex" → 纯内存加载
    //   - "classes*.dex"  → 通用匹配
    bool isOurDex = false;
    std::string matchedPath = location;

    if (location.find("memory_dex") != std::string::npos) {
        isOurDex = true;
        // 从文件名中提取序号 memory_dex_xxx_N.dex → classesN+1.dex
        // 在codeMapList中查找对应的codes条目
    } else if (location.find("tmp_dex") != std::string::npos) {
        isOurDex = true;
    } else if (location.find("Anonymous-DexFile") != std::string::npos) {
        isOurDex = true;
        matchedPath = codeMapList.begin()->first;  // 使用预加载的codes
    }
    // ... 更多匹配规则

    if (!isOurDex) return;

    // 3. 懒加载.codes文件
    if (codeMapList.find(matchedPath) == codeMapList.end()) {
        codeMapList[matchedPath] = std::map<uint32_t, CodeItem>();
        parseExtractedCodeFiles(matchedPath);
    }

    if (code_off == 0) return;  // 抽象/native方法

    // 4. 计算指令地址并回填
    // code_off 指向 CodeItem 头部
    // +16 跳过: registers_size(2) + ins_size(2) + outs_size(2) + tries_size(2)
    //          + debug_info_off(4) + insns_size(4) = 16字节
    uint8_t* codeAddr = (uint8_t*)(dexBegin + code_off + 16);

    auto it = codeMapList[matchedPath].find(code_off);
    if (it != codeMapList[matchedPath].end()) {
        const CodeItem& codeItem = it->second;
        // ★ 关键操作：将原始指令复制回DEX内存 ★
        memcpy(codeAddr, codeItem.getInsns(), codeItem.getInsnsSize() * 2);
    }
}
```

### 2.11 JNI接口

Native层通过JNI接口供Java层调用：

```
// ShellNative.init(String codesDir) - 接收codes目录路径
JNIEXPORT jboolean JNICALL
Java_com_csh_shell_ShellNative_init(JNIEnv *env, jclass clazz, jstring codes_dir);

// ShellNative.loadCodesFile(String path) - 解析单个.codes文件到codeMapList
// 同时创建路径别名（处理 /data/user/0 vs /data/data 差异）
JNIEXPORT jboolean JNICALL
Java_com_csh_shell_ShellNative_loadCodesFile(JNIEnv *env, jclass clazz, jstring codes_file_path);

// ShellNative.getLoadedCodesCount() - 返回已加载的代码项总数
// ShellNative.isHookInitialized() - 检查LoadMethod Hook是否成功
// ShellNative.getApiLevel() - 返回API Level
// ShellNative.clearCodes() - 清空所有已加载的代码项
```

**路径规范化处理**：Android 上 `/data/user/0/pkg` 和 `/data/data/pkg` 是同一目录的不同路径，ART 内部使用的路径可能与 Java 层保存的不一致，因此 `loadCodesFile` 会同时在两种路径下注册 codeMap。

---

## 模块三：Shell-App 壳程序模块（Java层）

> **相对二代的改动**：核心是新增了 Native 库加载、`.codes` 文件处理和 Android 7 特殊适配。

### 3.1 启动流程

`ShellProxyApplicationV3.attachBaseContext()` 的完整执行流程：

```
@Override
protected void attachBaseContext(Context base) {
    super.attachBaseContext(base);

    // 1. 加载壳SO文件 → 触发_init()构造函数 → 安装3个Hook
    //    ★ 必须在加载DEX之前完成，否则Hook无法拦截类加载 ★
    loadShellNativeLibrary();  // System.loadLibrary("androidshell")

    // 2. 初始化环境（解密DEX、释放.codes文件）
    initEnvironments();

    // 3. 替换ClassLoader（根据版本选择DexClassLoader或InMemoryDexClassLoader）
    replaceClassLoader();

    // 4. 获取源Application类名（从META-DATA读取）
    mApplicationName = getSourceApplicationName();

    // 5. 通过替换后的ClassLoader加载源Application类并实例化
    mSourceApplication = makeSourceApplication();

    // 6. 替换系统中的Application引用
    replaceApplicationInSystem(this, mSourceApplication);

    // 7. 调用源Application的attach方法
    invokeSourceApplicationAttach(mSourceApplication, base);
}
```

### 3.2 环境初始化详解

```
private void initEnvironments() throws IOException {
    // 1. 创建私有目录 /data/user/0/<pkg>/app_tmp_dex/
    File dexDir = getDir("tmp_dex", MODE_PRIVATE);

    // 2. 从APK的classes.dex中读取壳DEX数据
    byte[] shellDexData = readDexFromApk();

    // 3. 解析复合DEX格式并分离源DEX
    //    格式: [壳DEX][加密源DEX集合][源DEX集合大小(4B)]
    ByteBuffer[] byteBuffers = extractDexFilesFromShellDex(shellDexData);

    // 4. 将DEX写入私有目录
    //    Android 10+: 写入后调用 file.setReadOnly()
    //    绕过 "Writable dex file is not allowed" 安全限制
    writeByteBuffersToDirectory(byteBuffers, odexPath);

    // 5. 复制.codes文件：从assets复制到私有目录
    copyClassesCodesFiles(this, odexPath);

    // 6. 初始化Native层并加载codes文件
    //    ShellNative.init(dexDir) → 设置Native层codes目录
    //    ShellNative.loadCodesFile(path) → 为每个.codes文件解析到codeMapList
    initNativeAndLoadCodes(dexDir);

    // 7. 拼接DEX文件路径（供DexClassLoader使用）
    // 跳过.codes文件，拼接为 "path1:path2:path3" 格式
    dexPath = buildDexPathString(dexDir);
}
```

### 3.3 DEX解密过程

```
private ByteBuffer[] extractDexFilesFromShellDex(byte[] shellDexData) throws IOException {
    // 1. 读取源DEX集合大小（最后4字节，小端序）
    int totalSize = ByteBuffer.wrap(shellDexData, shellDexData.length - 4, 4)
                              .order(ByteOrder.LITTLE_ENDIAN).getInt();

    // 2. 读取加密的源DEX数据
    byte[] encrypted = new byte[totalSize];
    System.arraycopy(shellDexData, shellDexData.length - totalSize - 4, encrypted, 0, totalSize);

    // 3. XOR 0xFF 解密
    for (int i = 0; i < encrypted.length; i++) {
        encrypted[i] ^= (byte) 0xFF;
    }

    // 4. 分离各个DEX: [dex1_size(4B)][dex1_data][dex2_size(4B)][dex2_data]...
    ArrayList<byte[]> dexList = new ArrayList<>();
    int pos = 0;
    while (pos < totalSize) {
        int dexSize = ByteBuffer.wrap(encrypted, pos, 4)
                                .order(ByteOrder.LITTLE_ENDIAN).getInt();
        byte[] dexData = new byte[dexSize];
        System.arraycopy(encrypted, pos + 4, dexData, 0, dexSize);
        dexList.add(dexData);
        pos += 4 + dexSize;
    }

    // 5. 转换为ByteBuffer数组
    ByteBuffer[] buffers = new ByteBuffer[dexList.size()];
    for (int i = 0; i < dexList.size(); i++) {
        buffers[i] = ByteBuffer.wrap(dexList.get(i));
    }
    return buffers;
}
```

### 3.4 Android 14+ 安全限制处理

```
private void writeByteBuffersToDirectory(ByteBuffer[] byteBuffers, String dir) throws IOException {
    for (int i = 0; i < byteBuffers.length; i++) {
        String fileName = (i == 0) ? "classes.dex" : "classes" + (i + 1) + ".dex";
        File file = new File(dir, fileName);

        // 删除旧文件（上次运行时可能被setReadOnly了）
        if (file.exists()) file.delete();

        // 写入DEX
        try (FileOutputStream fos = new FileOutputStream(file)) {
            byte[] bytes = new byte[byteBuffers[i].remaining()];
            byteBuffers[i].get(bytes);
            fos.write(bytes);
        }

        // ★ Android 10+ 安全策略：DEX文件必须只读
        // 磁盘上只读 → 绕过Android检查
        // 内存中可写 → 通过mmap Hook添加PROT_WRITE
        if (android.os.Build.VERSION.SDK_INT >= 29) {
            file.setReadOnly();
        }
    }
}
```

### 3.5 ClassLoader替换（版本分支）

```
private void replaceClassLoader() {
    ClassLoader classLoader = this.getClassLoader();
    ClassLoader dexClassLoader;

    if (android.os.Build.VERSION.SDK_INT <= 25) {
        // ★ Android 7 特殊处理 ★
        // DexClassLoader依赖dex2oat编译，但V3的execve Hook阻止了dex2oat
        // Android 7没有JIT解释模式回退，DexClassLoader会直接失败
        // 解决方案：使用InMemoryDexClassLoader，绕过dex2oat
        dexClassLoader = createInMemoryClassLoader(classLoader);
    } else {
        // Android 8+: DexClassLoader + JIT回退到解释模式
        dexClassLoader = new DexClassLoader(dexPath, odexPath, libPath, classLoader.getParent());
    }

    // 替换3个位置的ClassLoader
    replaceClassLoaderInPackages(activityThread, "mPackages", packageName, dexClassLoader);
    replaceClassLoaderInPackages(activityThread, "mResourcePackages", packageName, dexClassLoader);
    replaceClassLoaderInBoundApplication(activityThread, dexClassLoader);
}
```

### 3.6 CompatInMemoryDexClassLoader

Android 7 使用 `CompatInMemoryDexClassLoader` 加载内存中的 DEX：

```
// 根据API Level选择不同的创建策略
public static ClassLoader create(ByteBuffer[] dexBuffers, Context context,
                                  String libraryPath, ClassLoader parent) {
    if (Build.VERSION.SDK_INT >= 29) {
        // Android 10+: InMemoryDexClassLoader(buffers, libraryPath, parent)
        return new InMemoryDexClassLoader(dexBuffers, libraryPath, parent);
    } else if (Build.VERSION.SDK_INT >= 27) {
        // Android 8.1-9: InMemoryDexClassLoader(buffers, parent)
        return new InMemoryDexClassLoader(dexBuffers, parent);
    } else {
        // Android 5.0-8.0: 通过反射注入DexPathList.dexElements
        return new CompatInMemoryDexClassLoader(dexBuffers, context, libraryPath, parent);
    }
}
```

---

## 版本兼容性详解

### 已验证的Android版本支持矩阵

| Android版本 | API Level | LoadMethod签名变化 | ClassLoader方式 | 特殊处理 | 测试状态 |
| --- | --- | --- | --- | --- | --- |
| 7.0-7.1 | 24-25 | 有 `Thread* self` 参数 | InMemoryDexClassLoader | dex2oat无JIT回退 | ✅ 已验证 |
| 8.0-8.1 | 26-27 | 移除 `Thread*` | DexClassLoader |  | ✅ 已验证 |
| 9 | 28 | ClassDataItemIterator | DexClassLoader |  | ✅ 已验证 |
| 10 | 29 | 切换为 ClassAccessor::Method | DexClassLoader | DEX需setReadOnly | ✅ 已验证 |
| 11-13 | 30-33 | ObjPtr[mirror::Class](https://link.juejin.cn?target=) | DexClassLoader |  | ✅ 已验证 |
| 14 | 34 | 同上 | DexClassLoader | **"Writable dex"安全限制** | ✅ 已验证 |
| 15 | 35 | **新增 MethodAnnotationsIterator** | DexClassLoader | 符号名变化 | ✅ 已验证 |
| 16+ | 36+ | **LoadMethod被重构为内部类** | - | **不可行** | ❌ 方案不可行 |

### 结构体偏移验证表（64位）

| Android版本 | API | 结构体 | code\_off偏移 | DexFile.location\_偏移 | 验证方式 |
| --- | --- | --- | --- | --- | --- |
| 7.0-7.1 | 24-25 | ClassDataItemIterator | 0x20 | 0x18 (24) | 运行时dump |
| 8.0-8.1 | 26-27 | ClassDataItemIterator | 0x20 | 0x18 (24) | 运行时dump |
| 9 | 28 | ClassDataItemIterator | 0x20 | 0x28 (40) | 运行时dump |
| 10 | 29 | ClassAccessor::Method | 0x28 | 0x28 (40) | 运行时dump |
| 11-14 | 30-34 | ClassAccessor::Method | 0x28 | 0x28 (40) | 运行时dump |
| 15 | 35 | ClassAccessor::Method | 0x28 | 0x28 (40) | 运行时dump |

### Android 16 不可行性分析

Android 16 对 ART 进行了架构重构，`ClassLinker::LoadMethod` 被移除：

| 对比项 | Android ≤ 15 | Android 16+ |
| --- | --- | --- |
| 函数位置 | `ClassLinker::LoadMethod` | `LoadClassHelper::LoadMethod`（内部类私有方法） |
| 符号可见性 | GLOBAL DEFAULT（导出） | LOCAL HIDDEN（隐藏）或无符号 |
| dlsym/Dobby可用 | ✅ | ❌ |
| 输出类型 | `ArtMethod*` | `ArtMethodData*`（临时结构） |
| Hook可行性 | ✅ | ❌ |

**替代方案**（Android 16+）：

1. **JVMTI ClassFileLoadHook**（推荐，但需要 debuggable 或 kArtTiVersion）
2. **mmap Hook 批量回填**（简单可靠，但失去按需保护）

---

## 完整数据流图

```
                            ════ 编译时（Packer） ════

Source APK
    │
    ├─ [apktool decode] → srcApkTemp/classes*.dex
    │
    ├─ [DexCodeExtractor.extractAllDexFiles]
    │     ├─ 解析DEX: Header → string_ids → type_ids → proto_ids → method_ids → class_defs
    │     ├─ 遍历ClassDefs: 跳过14种系统类前缀
    │     ├─ 遍历methods: 跳过 <init>/<clinit>/native/abstract
    │     ├─ 对每个方法:
    │     │     ├─ 保存 {codeOff, insnsSize, insns} 到 ExtractedCode
    │     │     └─ 替换insns为返回类型匹配的空指令
    │     ├─ fixDexFile: file_size → SHA-1 → Adler32
    │     └─ 输出: 修改后的DEX + .codes文件
    │
    ├─ [DexProcessor.combineShellAndSourceDexs]
    │     ├─ 序列化源DEXs: [size(4B)][data]...
    │     ├─ XOR 0xFF 加密
    │     └─ 合并: [壳DEX][加密blob][blob大小(4B)] → classes.dex
    │
    ├─ [ManifestEditor] → Application改为ShellProxyApplicationV3
    ├─ 复制壳APK的lib/ (libandroidshell.so + libbytehook.so)
    └─ [apktool build] → [zipalign] → [apksigner] → 加固APK


                            ════ 运行时（Shell） ════

App启动 → ShellProxyApplicationV3.attachBaseContext()
    │
    ├─ System.loadLibrary("androidshell")
    │     └─ _init() [constructor]
    │           ├─ APILevel = android_get_device_api_level()
    │           └─ doHook():
    │                 ├─ bytehook_init()
    │                 ├─ hookExecve() → 拦截dex2oat
    │                 ├─ hookMmap()   → 添加PROT_WRITE
    │                 └─ hookLoadMethod() → 6版本Dobby Hook
    │
    ├─ initEnvironments()
    │     ├─ readDexFromApk() → ZipInputStream读取classes.dex
    │     ├─ extractDexFilesFromShellDex() → XOR 0xFF解密 → 分离DEX
    │     ├─ writeByteBuffersToDirectory() → 写入 + setReadOnly(API≥29)
    │     ├─ copyClassesCodesFiles() → assets/*.codes → 私有目录
    │     └─ initNativeAndLoadCodes() → JNI: init() + loadCodesFile()
    │           └─ Native: parseExtractedCodeFiles() → codeMapList填充
    │
    ├─ replaceClassLoader()
    │     ├─ API≤25: CompatInMemoryDexClassLoader（内存加载）
    │     └─ API≥26: DexClassLoader（文件加载）
    │
    ├─ makeSourceApplication() → ClassLoader.loadClass() + newInstance()
    └─ replaceApplicationInSystem() → 替换ActivityThread中的引用

═══════════════════════════════════════════════════════════════════
当ART加载任意源DEX中的类/方法时:

ART: ClassLinker::LoadMethod(dex_file, method/it, klass, dst)
    │
    └─ Dobby Hook 拦截 → newLoadMethodV30() (或对应版本)
          │
          ├─ refillInstructions(dex_file, code_off)
          │     ├─ 获取DEX路径: getDexFileLocation(dexFile, APILevel)
          │     ├─ 路径匹配: tmp_dex / memory_dex / Anonymous-DexFile / ...
          │     ├─ 懒加载.codes: parseExtractedCodeFiles()
          │     └─ ★ memcpy(dexBegin + code_off + 16, insns, size) ★
          │
          └─ 调用原始LoadMethod → ART看到完整方法体 → 正常执行
```

---

## 总结：三代加固方案全面对比

| 特性 | 一代加固 (V1) | 二代加固 (V2) | 三代加固 (V3) |
| --- | --- | --- | --- |
| **DEX存储** | 文件落地 | 内存中完整 | 内存中方法体为空 |
| **ClassLoader** | `DexClassLoader` | `InMemoryDexClassLoader` | `DexClassLoader` + Hook |
| **Native层** | 无 | 无 | ByteHook + Dobby |
| **安全性** | 低（可直接提取） | 较高（需内存dump） | 很高（dump得到空方法） |
| **最低版本** | Android 5.0+ | Android 5.0+ | Android 7.0+ |
| **最高版本** | Android 14 | 无限制 | Android 15（16+不可行） |
| **兼容性复杂度** | 中 | 高 | 极高 |
| **性能影响** | 低 | 低 | 中等（Hook开销） |

### 三代加固的优势

1. **更高安全性**：内存中DEX方法体为空，dump无效
2. **函数级保护**：每个方法单独抽取，粒度细
3. **抗静态分析**：反编译工具看到的是空方法
4. **按需回填**：方法加载时才恢复指令，缩短暴露窗口

### 三代加固的挑战

1. **兼容性问题**：依赖未公开的ART内部结构，需要为每个Android版本做偏移适配
2. **版本适配工作量大**：6个不同版本的Hook函数，3种符号查找策略
3. **Android 16+不可行**：LoadMethod被重构为内部类，符号被隐藏
4. **Hook开销**：每次方法加载都有Hook调用
5. **与AOT冲突**：必须禁用dex2oat，强制使用解释模式

### 进一步安全增强

三代加固仍然可以通过以下方式破解：

1. **解释器Hook**：在ART解释器中记录每次执行的指令
2. **ArtMethod Dump**：在方法执行后dump ArtMethod的CodeItem
3. **主动调用**：触发所有方法加载，回填完成后再dump

为解决这些问题，后续发展出了：

1. **四代加固（dex2c/VMP）**：将Java代码转为Native代码
2. **五代加固（虚拟机保护）**：自定义指令集，完全脱离Dalvik

这将是本系列后续文章的演进思路。
