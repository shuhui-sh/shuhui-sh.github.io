---
title: "Android第二代加固技术原理详解（附源码）"
date: 2026-04-02
description: "一代加固存在一个致命缺陷：解密后的DEX文件需要落地到文件系统。为了解决这一安全隐患，二代加固应运而生——核心思想是DEX不落地，直接在内存中加载。"
tags: ['Android']
category: "技术"
---
> 作者：见前行
> 发布于：2026-01-01
> 原文链接：https://juejin.cn/post/7589935326781669410

一代加固存在一个致命缺陷：解密后的DEX文件需要落地到文件系统。为了解决这一安全隐患，二代加固应运而生——核心思想是DEX不落地，直接在内存中加载。

---

## 前言

在上一篇[Android第一代加固技术原理详解（附源码）](https://juejin.cn/post/7543901300719681570)，我们详细介绍了Android第一代加固的实现原理——**落地加载方案**。该方案通过将加密的源APK解密后写入私有目录，再使用`DexClassLoader`加载的方式实现代码保护。

然而，一代加固存在一个致命缺陷：**解密后的DEX文件需要落地到文件系统**。这意味着攻击者可以通过以下方式轻松获取源程序代码：

1. **Root设备直接读取**：访问`/data/user/0/<package_name>/app_tmp_dex/`目录
2. **Hook文件操作**：监控`FileOutputStream.write()`等方法
3. **监控私有目录**：使用`inotify`等机制监听文件创建事件

为了解决这一安全隐患，**二代加固应运而生**——核心思想是**DEX不落地，直接在内存中加载**。

---

## 一代 vs 二代：核心差异对比

| 特性 | 一代加固 (V1) | 二代加固 (V2) |
| --- | --- | --- |
| **DEX存储** | 解密后写入磁盘`Source.apk` | 仅存在于内存`ByteBuffer` |
| **ClassLoader** | `DexClassLoader` | `InMemoryDexClassLoader` |
| **核心API** | `DexClassLoader(apkPath,...)` | `InMemoryDexClassLoader(ByteBuffer[],...)` |
| **安全级别** | 中等（文件可被dump） | 较高（内存加载不落地） |
| **最低版本** | Android 4.0+ (API 14) | Android 5.0+ (API 21) |
| **Multidex** | 需额外处理 | 原生支持`ByteBuffer[]` |

### 一代加固的安全缺陷回顾

```java
// 一代加固：解密后的APK必须写入磁盘
File apkFile = new File(apkPath);
FileOutputStream fos = new FileOutputStream(apkFile);
fos.write(decryptedApkData);  // [安全风险] DEX落地到文件系统
fos.close();

// 使用DexClassLoader从文件加载
DexClassLoader dexClassLoader = new DexClassLoader(
        apkPath,   // 源APK文件路径 - 攻击者可直接复制此文件
        dexPath,   // 优化后的DEX路径
        libPath,   // Native库路径
        parent     // 父ClassLoader
);
```

### 二代加固的解决方案

```java
// 二代加固：DEX直接在内存中加载，不写入磁盘
ByteBuffer[] dexBuffers = extractDexFilesFromShellDex(shellDexData);

// 使用InMemoryDexClassLoader从内存加载（Android 8.0+）
InMemoryDexClassLoader dexClassLoader = new InMemoryDexClassLoader(
        dexBuffers,  // DEX字节数据 - 仅存在于内存中
        libraryPath, // Native库路径
        parent       // 父ClassLoader
);
// DEX从未写入文件系统，攻击者无法通过文件监控获取
```

---

## 二代加固的技术挑战

虽然`InMemoryDexClassLoader`是Android 8.0 (API 26)才引入的API，但二代加固需要支持Android 5.0+的设备。这带来了以下技术挑战：

### 1. API版本兼容性问题

| Android版本 | API级别 | InMemoryDexClassLoader支持情况 |
| --- | --- | --- |
| Android 10+ | 29+ | 支持`ByteBuffer[]` + `libraryPath` |
| Android 8.1-9 | 27-28 | 支持`ByteBuffer[]`，不支持`libraryPath` |
| Android 8.0 | 26 | 仅支持单个`ByteBuffer` |
| Android 5.0-7.1 | 21-25 | 不存在此API |

### 2. Multidex支持

现代Android应用通常包含多个DEX文件，二代加固必须能够处理`classes.dex`、`classes2.dex`等多DEX场景。

### 3. Native库加载

Android 10以下版本的`InMemoryDexClassLoader`不支持`librarySearchPath`参数，需要手动注入Native库路径。

---

## 二代加固整体架构

### 与一代的模块对比

```
一代加固流程：
┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐
│  壳DEX      │    │  加密源APK   │    │  合并后的classes.dex    │
│             │ +  │             │ => │  [壳DEX][加密APK][4字节] │
└─────────────┘    └─────────────┘    └─────────────────────────┘
                                                  │
                         运行时解密 → 写入Source.apk到本地文件 → DexClassLoader加载

二代加固流程：
┌─────────────┐    ┌─────────────┐    ┌──────────────────────────┐
│  壳DEX      │    │加密源DEX集合 │    │  合并后的classes.dex     │
│             │ +  │(支持Multidex)│ => │  [壳DEX][加密DEXs][4字节]│
└─────────────┘    └─────────────┘    └──────────────────────────┘
                                                  │
                      运行时解密 → ByteBuffer[] → InMemoryDexClassLoader
                                     ↑
                              DEX不落地，直接内存加载
```

---

## 核心代码实现

### 1. DEX集合的打包格式

为了支持Multidex，二代加固使用特殊的DEX集合格式：

```
加密前的DEX集合格式：
┌──────────────────────────────────────────────────────────────────┐
│  [DEX1大小][DEX1数据][DEX2大小][DEX2数据]...[DEXn大小][DEXn数据]   │
│   4字节                4字节                  4字节               │
└──────────────────────────────────────────────────────────────────┘
                              ↓ XOR加密
                              ↓
最终classes.dex格式：
┌────────────────────────────────────────────────────────────────────┐
│         壳DEX          │      加密DEX集合       │  集合大小(4字节)  │
│  (ShellProxyV2 代码)   │    (XOR加密后的数据)   │   小端序存储      │
└────────────────────────────────────────────────────────────────────┘
```

### 2. 二代壳Application整体流程

```java
/**
 * ShellProxyApplicationV2.java - 二代加固壳Application
 *
 * 核心流程：
 * 1. 从APK读取合并后的classes.dex
 * 2. 从dex尾部解析并解密源DEX集合
 * 3. 将源DEX集合转换为ByteBuffer[]
 * 4. 使用InMemoryDexClassLoader加载（不落地）
 * 5. 替换系统ClassLoader引用
 * 6. 替换Application实例
 */
public class ShellProxyApplicationV2 extends Application {
    private static final String TAG = "shell_v2";

    private String mApplicationName;
    private Application mSourceApplication;

    @Override
    protected void attachBaseContext(Context base) {
        super.attachBaseContext(base);

        try {
            // Step 1: 读取壳DEX文件
            byte[] shellDexData = readDexFromApk();
            if (shellDexData == null) {
                log("Failed to read dex from APK");
                return;
            }

            // Step 2: 从中分离出源DEX文件集合（关键步骤！）
            ByteBuffer[] byteBuffers = extractDexFilesFromShellDex(shellDexData);

            // Step 3: 替换ClassLoader（使用内存加载，不落地）
            boolean classLoaderSuccess = replaceClassLoader(byteBuffers);
            if (!classLoaderSuccess) {
                log("ClassLoader replacement failed");
                return;
            }

            // Step 4: 获取源程序Application类名
            mApplicationName = getSourceApplicationName();

            // Step 5: 创建源程序Application实例
            mSourceApplication = makeSourceApplication();

            // Step 6: 替换系统中的Application引用
            replaceApplicationInSystem(this, mSourceApplication);

            // Step 7: 调用源程序Application的attachBaseContext
            invokeSourceApplicationAttach(mSourceApplication, base);

            log("Application replacement completed successfully");

        } catch (Throwable e) {
            log("Error in attachBaseContext: " + Log.getStackTraceString(e));
        }
    }

    @Override
    public void onCreate() {
        super.onCreate();
        // 调用源Application的onCreate
        if (mSourceApplication != null) {
            mSourceApplication.onCreate();
        }
    }
}
```

### 3. 从壳DEX中提取源DEX集合

这是二代加固与一代加固的**核心区别**：一代提取的是完整APK，二代提取的是DEX集合并转换为`ByteBuffer[]`

```java
/**
 * 从壳DEX文件中提取源DEX集合
 *
 * 数据格式（从尾部开始）：
 * ┌──────────────────────────────────────────────────────────────┐
 * │    壳DEX代码     │      加密的DEX集合      │  集合大小(4字节) │
 * └──────────────────────────────────────────────────────────────┘
 *                                               ← 从这里开始解析
 */
private ByteBuffer[] extractDexFilesFromShellDex(byte[] shellDexData) throws IOException {
    int shellDexLength = shellDexData.length;

    // ==================== 第一步：读取DEX集合的总大小 ====================
    byte[] sourceDexsSizeByte = new byte[4];
    // 从最后4字节读取
    System.arraycopy(shellDexData, shellDexLength - 4, sourceDexsSizeByte, 0, 4);
    // 使用ByteBuffer转换，注意是小端序
    ByteBuffer wrap = ByteBuffer.wrap(sourceDexsSizeByte);
    int sourceDexsSizeInt = wrap.order(ByteOrder.LITTLE_ENDIAN).getInt();

    // ==================== 第二步：读取加密的DEX集合数据 ====================
    byte[] sourceDexsData = new byte[sourceDexsSizeInt];
    // 数据位置 = 总长度 - DEX集合大小 - 4字节（尾部大小字段）
    System.arraycopy(shellDexData, shellDexLength - sourceDexsSizeInt - 4,
                     sourceDexsData, 0, sourceDexsSizeInt);

    // ==================== 第三步：解密DEX集合 ====================
    sourceDexsData = decrypt(sourceDexsData);  // XOR解密

    // ==================== 第四步：从DEX集合中分离各个DEX ====================
    ArrayList<byte[]> sourceDexList = new ArrayList<>();
    int pos = 0;

    while (pos < sourceDexsSizeInt) {
        // 读取当前DEX的大小（4字节，小端序）
        byte[] singleDexSizeByte = new byte[4];
        System.arraycopy(sourceDexsData, pos, singleDexSizeByte, 0, 4);
        ByteBuffer singleDexWrap = ByteBuffer.wrap(singleDexSizeByte);
        int singleDexSizeInt = singleDexWrap.order(ByteOrder.LITTLE_ENDIAN).getInt();

        // 读取DEX数据
        byte[] singleDexData = new byte[singleDexSizeInt];
        System.arraycopy(sourceDexsData, pos + 4, singleDexData, 0, singleDexSizeInt);

        // 加入列表
        sourceDexList.add(singleDexData);

        // 移动位置指针
        pos += 4 + singleDexSizeInt;
    }

    // ==================== 第五步：转换为ByteBuffer数组 ====================
    int dexNum = sourceDexList.size();
    ByteBuffer[] dexBuffers = new ByteBuffer[dexNum];
    for (int i = 0; i < dexNum; i++) {
        dexBuffers[i] = ByteBuffer.wrap(sourceDexList.get(i));
    }

    return dexBuffers;  // 返回ByteBuffer[]供InMemoryDexClassLoader使用
}
```

### 4. 版本兼容性工厂方法

`CompatInMemoryDexClassLoader.create()`是二代加固的核心创新，它根据Android版本自动选择最佳加载方案：

```java
/**
 * CompatInMemoryDexClassLoader.java - 兼容性ClassLoader工厂
 *
 * 支持Android 5.0+ (API 21+)的内存DEX加载
 */
public class CompatInMemoryDexClassLoader extends BaseDexClassLoader {

    /**
     * 静态工厂方法：根据Android版本自动选择最佳实现
     */
    public static ClassLoader create(ByteBuffer[] dexBuffers, Context context,
                                     String libraryPath, ClassLoader parent) {
        Log.d(TAG, "Creating ClassLoader for SDK " + Build.VERSION.SDK_INT);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            // ==================== Android 10+ (API 29+) ====================
            // 完整支持：InMemoryDexClassLoader(ByteBuffer[], libraryPath, parent)
            Log.d(TAG, "Using InMemoryDexClassLoader with libraryPath");
            return new InMemoryDexClassLoader(dexBuffers, libraryPath, parent);

        } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            // ==================== Android 8.1-9 (API 27-28) ====================
            // 部分支持：InMemoryDexClassLoader(ByteBuffer[], parent)
            // 不支持libraryPath，需要后续手动注入
            Log.d(TAG, "Using InMemoryDexClassLoader without libraryPath");
            return new InMemoryDexClassLoader(dexBuffers, parent);

        } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            // ==================== Android 8.0 (API 26) ====================
            // 有限支持：仅支持单个ByteBuffer
            if (dexBuffers.length == 1) {
                Log.d(TAG, "Using single InMemoryDexClassLoader");
                return new InMemoryDexClassLoader(dexBuffers[0], parent);
            } else {
                // 多DEX：使用反射注入方案
                Log.d(TAG, "Using CompatInMemoryDexClassLoader for multi-dex");
                return new CompatInMemoryDexClassLoader(dexBuffers, context, parent);
            }

        } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            // ==================== Android 5.0-7.1 (API 21-25) ====================
            // 无原生支持：使用兼容实现
            Log.d(TAG, "Using CompatInMemoryDexClassLoader (5.0-7.1)");
            return new CompatInMemoryDexClassLoader(dexBuffers, context, parent);

        } else {
            throw new RuntimeException("Android version not supported");
        }
    }
}
```

---

## 总结：一代与二代加固对比

| 特性 | 一代加固 (V1) | 二代加固 (V2) |
| --- | --- | --- |
| **DEX存储位置** | 写入文件系统 | 仅在内存中 |
| **核心ClassLoader** | `DexClassLoader` | `InMemoryDexClassLoader` |
| **安全性** | 中等（可被文件监控） | 较高（需内存dump） |
| **最低版本** | Android 4.0+ | Android 5.0+ |
| **兼容性复杂度** | 低 | 高（需处理多版本差异） |
| **Native库支持** | 原生支持 | 需手动注入（Android 10以下） |
| **Multidex支持** | 需控制单个dex生成 | 可支持多dex |

### 二代加固的优势

1. **更高安全性**：DEX不落地，攻击者无法通过文件监控获取
2. **原生Multidex支持**：`ByteBuffer[]`天然支持多DEX
3. **更快的加载速度**：无需写入磁盘的I/O开销

### 二代加固的挑战

1. **版本兼容性**：需要处理Android 5.0-9的各种API差异
2. **Native库注入**：Android 10以下需要手动处理

### 进一步安全增强

二代加固虽然比一代安全，但仍然可以通过**内存dump**技术获取DEX。为进一步增强安全性，后续的技术路线将沿下面方向发展：

1. **指令抽离**：发布时清除DEX函数体（CodeItem）并单独加密存储；运行时按需恢复至内存
2. **Native化**：将Java代码转换为Native代码
3. **VMP（虚拟机保护）**：将关键代码转换为自定义字节码
