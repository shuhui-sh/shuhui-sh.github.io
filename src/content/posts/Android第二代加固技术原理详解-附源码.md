---
title: "Android第二代加固技术原理详解（附源码）"
date: 2026-01-01
description: "一代加固存在一个致命缺陷：解密后的DEX文件需要落地到文件系统。为了解决这一安全隐患，二代加固应运而生——核心思想是DEX不落地，直接在内存中加载。"
tags: ['Android', '逆向']
category: "技术"
source: "https://juejin.cn/post/7589935326781669410"
---
## Android第二代加固技术原理详解（附源码）

### 前言

在上一篇[Android第一代加固技术原理详解（附源码）](https://juejin.cn/post/7543901300719681570 "https://juejin.cn/post/7543901300719681570")，我们详细介绍了Android第一代加固的实现原理——**落地加载方案**。该方案通过将加密的源APK解密后写入私有目录，再使用`DexClassLoader`加载的方式实现代码保护。

然而，一代加固存在一个致命缺陷：**解密后的DEX文件需要落地到文件系统**。这意味着攻击者可以通过以下方式轻松获取源程序代码：

1. **Root设备直接读取**：访问`/data/user/0/<package_name>/app_tmp_dex/`目录
2. **Hook文件操作**：监控`FileOutputStream.write()`等方法
3. **监控私有目录**：使用`inotify`等机制监听文件创建事件

为了解决这一安全隐患，**二代加固应运而生**——核心思想是**DEX不落地，直接在内存中加载**。（本系列文章承前启后，为更好理解下文内容，建议先理解上一篇[Android第一代加固技术原理详解（附源码）](https://juejin.cn/post/7543901300719681570 "https://juejin.cn/post/7543901300719681570")，再看本文，可有事半功倍之效。）

---

### 一代 vs 二代：核心差异对比

| 特性 | 一代加固 (V1) | 二代加固 (V2) |
| --- | --- | --- |
| **DEX存储** | 解密后写入磁盘`Source.apk` | 仅存在于内存`ByteBuffer` |
| **ClassLoader** | `DexClassLoader` | `InMemoryDexClassLoader` |
| **核心API** | `DexClassLoader(apkPath,...)` | `InMemoryDexClassLoader(ByteBuffer[],...)` |
| **安全级别** | 中等（文件可被dump） | 较高（内存加载不落地） |
| **最低版本** | Android 4.0+ (API 14) | Android 5.0+ (API 21) |
| **Multidex** | 需额外处理 | 原生支持`ByteBuffer[]` |

#### 一代加固的安全缺陷回顾

```
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

#### 二代加固的解决方案

```
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

### 二代加固的技术挑战

虽然`InMemoryDexClassLoader`是Android 8.0 (API 26)才引入的API，但二代加固需要支持Android 5.0+的设备。这带来了以下技术挑战：

#### 1. API版本兼容性问题

| Android版本 | API级别 | InMemoryDexClassLoader支持情况 |
| --- | --- | --- |
| Android 10+ | 29+ | 支持`ByteBuffer[]` + `libraryPath` |
| Android 8.1-9 | 27-28 | 支持`ByteBuffer[]`，不支持`libraryPath` |
| Android 8.0 | 26 | 仅支持单个`ByteBuffer` |
| Android 5.0-7.1 | 21-25 | 不存在此API |

#### 2. Multidex支持

现代Android应用通常包含多个DEX文件，二代加固必须能够处理`classes.dex`、`classes2.dex`等多DEX场景。

#### 3. Native库加载

Android 10以下版本的`InMemoryDexClassLoader`不支持`librarySearchPath`参数，需要手动注入Native库路径。

另外，若源程序设置了`android:extractNativeLibs="false"`，系统安装应用时则不会释放lib文件到文件系统，而是运行时直接映射apk文件的lib数据。当前为了方便理解加固的原理，先简化lib文件的处理流程，加壳时，直接把源程序的lib库拷贝到壳程序的lib库下，并且把清单文件的`android:extractNativeLibs="false"`属性改成`android:extractNativeLibs="true"`, 这样壳程序运行后可以根据运行版本不同手动注入Native库路径。

---

### 二代加固整体架构

#### 与一代的模块对比

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

### 模块一：Packer 加壳工具模块

> **相对一代的改动**：此模块有**重要修改**。主要变化是处理对象从"整个源APK"变为"源DEX集合"，支持Multidex打包格式。

#### 1.1 与一代的核心差异

| 对比项 | 一代加固 (V1) | 二代加固 (V2) |
| --- | --- | --- |
| **处理对象** | 加密后的整个源APK | 加密后的源DEX集合 |
| **尾部格式** | `[壳DEX][加密APK][APK大小4字节]` | `[壳DEX][加密DEXs][DEXs大小4字节]` |
| **Multidex支持** | 不支持 | 原生支持 |
| **数据结构** | 单一APK文件 | DEX集合（带长度前缀） |

#### 1.2 DEX合并数据格式

#### DEX集合的打包格式

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

#### 具体解析示例

假设源APK包含3个DEX文件：

```
classes.dex  - 大小: 1048576 bytes (0x100000)
classes2.dex - 大小: 2097152 bytes (0x200000)
classes3.dex - 大小: 524288 bytes  (0x80000)

打包后的DEX集合数据（加密前）：
┌─────────────┬─────────────┬─────────────┬─────────────┬─────────────┬─────────────┐
│ 0x00100000  │ DEX1 数据   │ 0x00200000  │ DEX2 数据   │ 0x00080000  │ DEX3 数据   │
│ (小端序)    │ (1MB)       │ (小端序)    │ (2MB)       │ (小端序)    │ (512KB)     │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────────┴─────────────┘
     4字节       1048576       4字节        2097152        4字节         524288

总大小 = 4 + 1048576 + 4 + 2097152 + 4 + 524288 = 3670028 bytes
```

#### 核心打包代码

以下是DEX处理器的核心实现，与一代相同但处理对象不同：

```
/**
 * DexProcessor.java - DEX处理器
 * 将壳DEX与加密后的源DEX集合合并
 */
public class DexProcessor {

    // DEX文件头偏移量（与一代相同）
    private static final int CHECKSUM_OFFSET = 8;    // Adler32校验和偏移
    private static final int SIGNATURE_OFFSET = 12;  // SHA-1签名偏移
    private static final int FILE_SIZE_OFFSET = 32;  // 文件大小偏移

    /**
     * 合并壳DEX与加密后的源DEX集合
     * 
     * @param shellDexArray   壳DEX数据
     * @param encryptedDexs   加密后的源DEX集合
     * @return 合并后的新DEX数据
     */
    public static byte[] mergeDexFiles(byte[] shellDexArray, byte[] encryptedDexs) {
        // 计算新DEX总大小
        int newDexLen = shellDexArray.length + encryptedDexs.length + 4;
        byte[] newDexArray = new byte[newDexLen];
        
        // 1. 拷贝壳DEX
        System.arraycopy(shellDexArray, 0, newDexArray, 0, shellDexArray.length);
        
        // 2. 追加加密后的源DEX集合
        System.arraycopy(encryptedDexs, 0, newDexArray, shellDexArray.length, encryptedDexs.length);
        
        // 3. 写入DEX集合大小（4字节，小端序）
        int dexsSize = encryptedDexs.length;
        newDexArray[newDexLen - 4] = (byte) (dexsSize & 0xFF);
        newDexArray[newDexLen - 3] = (byte) ((dexsSize >> 8) & 0xFF);
        newDexArray[newDexLen - 2] = (byte) ((dexsSize >> 16) & 0xFF);
        newDexArray[newDexLen - 1] = (byte) ((dexsSize >> 24) & 0xFF);
        
        // 4. 修复DEX头部信息
        fixFileSize(newDexArray, newDexLen);  // 修正文件大小
        fixSignature(newDexArray);             // 重新计算SHA-1签名
        fixCheckSum(newDexArray);              // 重新计算Adler32校验和
        
        return newDexArray;
    }
    
    /**
     * 将源DEX列表打包为DEX集合格式
     * 
     * @param dexList DEX字节数组列表
     * @return 打包后的DEX集合（[大小1][数据1][大小2][数据2]...）
     */
    public static byte[] packDexList(List<byte[]> dexList) {
        // 计算总大小
        int totalSize = 0;
        for (byte[] dex : dexList) {
            totalSize += 4 + dex.length;  // 4字节大小 + DEX数据
        }
        
        byte[] result = new byte[totalSize];
        int pos = 0;
        
        for (byte[] dex : dexList) {
            // 写入当前DEX大小（小端序）
            int dexSize = dex.length;
            result[pos++] = (byte) (dexSize & 0xFF);
            result[pos++] = (byte) ((dexSize >> 8) & 0xFF);
            result[pos++] = (byte) ((dexSize >> 16) & 0xFF);
            result[pos++] = (byte) ((dexSize >> 24) & 0xFF);
            
            // 写入DEX数据
            System.arraycopy(dex, 0, result, pos, dex.length);
            pos += dex.length;
        }
        
        return result;
    }
}
```

#### DEX头部修复实现

当DEX文件被修改后，必须重新计算头部的三个字段：

```
/**
 * 修正DEX文件大小字段
 * 位置: 偏移量32，长度4字节
 */
private static void fixFileSize(byte[] dex, int size) {
    // DEX文件大小字段位于偏移量32处，4字节，小端序
    dex[32] = (byte) (size & 0xFF);
    dex[33] = (byte) ((size >> 8) & 0xFF);
    dex[34] = (byte) ((size >> 16) & 0xFF);
    dex[35] = (byte) ((size >> 24) & 0xFF);
}

/**
 * 重新计算SHA-1签名
 * 位置: 偏移量12，长度20字节
 * 范围: 对偏移量32到文件末尾的数据计算SHA-1
 */
private static void fixSignature(byte[] dex) {
    try {
        MessageDigest md = MessageDigest.getInstance("SHA-1");
        // 从偏移量32开始计算到文件末尾
        md.update(dex, 32, dex.length - 32);
        byte[] signature = md.digest();
        // 将20字节签名写入偏移量12
        System.arraycopy(signature, 0, dex, 12, 20);
    } catch (NoSuchAlgorithmException e) {
        throw new RuntimeException("SHA-1 algorithm not found", e);
    }
}

/**
 * 重新计算Adler32校验和
 * 位置: 偏移量8，长度4字节
 * 范围: 对偏移量12到文件末尾的数据计算Adler32
 */
private static void fixCheckSum(byte[] dex) {
    Adler32 adler32 = new Adler32();
    // 从偏移量12开始计算到文件末尾
    adler32.update(dex, 12, dex.length - 12);
    long checksum = adler32.getValue();
    // 将4字节校验和写入偏移量8，小端序
    dex[8] = (byte) (checksum & 0xFF);
    dex[9] = (byte) ((checksum >> 8) & 0xFF);
    dex[10] = (byte) ((checksum >> 16) & 0xFF);
    dex[11] = (byte) ((checksum >> 24) & 0xFF);
}
```

---

### 模块二：Shell-App 壳程序模块（业内也叫脱壳流程）

> **相对一代的改动**：此模块是**核心改动模块**。主要变化包括：
>
> 1. **DEX加载方式**：从`DexClassLoader`（文件加载）改为`InMemoryDexClassLoader`（内存加载）
> 2. **数据解析**：从提取完整APK改为解析DEX集合格式并转换为`ByteBuffer[]`
> 3. **版本兼容**：新增`CompatInMemoryDexClassLoader`处理Android 5.0-9的兼容性
> 4. **Native库注入**：新增`RetroLoadLibrary`解决Android 10以下的JNI加载问题

#### 2.1 与一代的核心差异对比

| 对比项 | 一代加固 Shell | 二代加固 Shell |
| --- | --- | --- |
| **ClassLoader类型** | `DexClassLoader` | `InMemoryDexClassLoader` |
| **DEX来源** | 文件系统`Source.apk` | 内存`ByteBuffer[]` |
| **DEX解析** | 提取完整APK | 解析DEX集合格式 |
| **文件落地** | 需要落地到私有目录 | 不落地（纯内存） |
| **Native库加载** | 原生支持 | 需手动注入（Android 10以下） |
| **版本兼容** | 简单 | 需处理多版本API差异 |
| **新增组件** | 无 | `CompatInMemoryDexClassLoader`、`RetroLoadLibrary` |

#### 2.2 二代壳Application整体流程

```
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
            log("成功从源APK中读取classes.dex");
            
            // Step 2: 从中分离出源DEX文件集合（关键步骤！）
            ByteBuffer[] byteBuffers = extractDexFilesFromShellDex(shellDexData);
            log("成功分离出源dex集合");
            
            // Step 3: 替换ClassLoader（使用内存加载，不落地）
            boolean classLoaderSuccess = replaceClassLoader(byteBuffers);
            if (!classLoaderSuccess) {
                log("ClassLoader replacement failed");
                return;
            }
            log("InMemoryDexClassLoader replacement succeeded");
            
            // Step 4: 获取源程序Application类名
            mApplicationName = getSourceApplicationName();
            if (mApplicationName == null) {
                log("No source application found");
                return;
            }
            
            // Step 5: 创建源程序Application实例
            mSourceApplication = makeSourceApplication();
            if (mSourceApplication == null) {
                log("Failed to create source application instance");
                return;
            }
            
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

#### 关键步骤：从壳DEX中提取源DEX集合

这是二代加固与一代加固的**核心区别**：一代提取的是完整APK，二代提取的是DEX集合并转换为`ByteBuffer[]`：

```
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
    log("源DEX集合的大小: " + sourceDexsSizeInt);
    
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
        log("当前singleDex的大小: " + singleDexSizeInt);
        
        // 边界校验：确保数据合法
        if (singleDexSizeInt <= 0 || pos + 4 + singleDexSizeInt > sourceDexsData.length) {
            throw new IOException("Invalid dex size: " + singleDexSizeInt);
        }
        
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
    log("源DEX的数量: " + dexNum);
    
    ByteBuffer[] dexBuffers = new ByteBuffer[dexNum];
    for (int i = 0; i < dexNum; i++) {
        dexBuffers[i] = ByteBuffer.wrap(sourceDexList.get(i));
    }
    
    return dexBuffers;  // 返回ByteBuffer[]供InMemoryDexClassLoader使用
}

/**
 * 简单XOR解密（与加密使用相同算法）
 */
private byte[] decrypt(byte[] data) {
    for (int i = 0; i < data.length; i++) {
        data[i] ^= (byte) 0xFF;  // 每字节与0xFF异或
    }
    return data;
}
```

#### 解析流程图解

```
壳DEX数据 (shellDexData):
┌───────────────────────────────────────────────────────────────────────┐
│     壳代码区域        │       加密DEX集合区域       │  4字节集合大小   │
│  (ProxyApplication)  │                            │   (小端序)       │
└───────────────────────────────────────────────────────────────────────┘
                       ↑                            ↑                  ↑
                       │                            │                  │
              shellDexLength-4-sourceDexsSizeInt    │          shellDexLength-4
                       │                            │
                       │←────── sourceDexsSizeInt ────→│

解密后的DEX集合 (sourceDexsData):
┌─────────┬───────────┬─────────┬───────────┬─────────┬───────────┐
│ DEX1大小│  DEX1数据  │ DEX2大小│  DEX2数据  │ DEX3大小│  DEX3数据  │
│ (4字节) │           │ (4字节) │           │ (4字节) │           │
└─────────┴───────────┴─────────┴───────────┴─────────┴───────────┘
    ↓           ↓           ↓           ↓           ↓           ↓
    └───────────┘           └───────────┘           └───────────┘
         ↓                       ↓                       ↓
   ByteBuffer[0]           ByteBuffer[1]           ByteBuffer[2]
         ↓                       ↓                       ↓
         └───────────────────────┴───────────────────────┘
                                 ↓
                    InMemoryDexClassLoader加载
                         （内存加载，不落地）
```

#### 2.3 ClassLoader替换与版本兼容（与一代核心区别）

> **与一代的区别**：一代使用`DexClassLoader(filePath)`，二代使用`InMemoryDexClassLoader(ByteBuffer[])`，需要处理多版本API差异。

##### ClassLoader替换核心逻辑

与一代加固类似，二代加固也需要替换系统的ClassLoader。但二代加固使用的是`InMemoryDexClassLoader`：

```
/**
 * 替换壳App的ClassLoader为源App的ClassLoader
 * 
 * 核心流程：
 * 1. 获取当前ClassLoader
 * 2. 反射获取ActivityThread和LoadedApk
 * 3. 使用CompatInMemoryDexClassLoader创建新ClassLoader
 * 4. 替换LoadedApk中的mClassLoader字段
 */
private boolean replaceClassLoader(ByteBuffer[] byteBuffers) {
    try {
        // 1. 检查Android版本支持（需要API 21+）
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.LOLLIPOP) {
            log("✗ Android version " + Build.VERSION.SDK_INT + " not supported");
            return false;
        }
        
        // 2. 获取当前ClassLoader
        ClassLoader classLoader = this.getClassLoader();
        log("Current ClassLoader: " + classLoader.toString());
        
        // 3. 反射获取ActivityThread
        Object activityThread = Reflection.getStaticField(
            "android.app.ActivityThread", "sCurrentActivityThread");
        
        // 4. 反射获取LoadedApk
        ArrayMap mPackages = (ArrayMap) Reflection.getField(
            "android.app.ActivityThread", activityThread, "mPackages");
        WeakReference weakReference = (WeakReference) mPackages.get(getPackageName());
        Object loadedApk = weakReference.get();
        
        // 5. 使用工厂方法创建ClassLoader（自动选择最佳实现）
        String libPath = getApplicationInfo().nativeLibraryDir;
        ClassLoader dexClassLoader = CompatInMemoryDexClassLoader.create(
            byteBuffers,      // DEX数据
            this,             // Context
            libPath,          // Native库路径
            classLoader.getParent()  // 父ClassLoader
        );
        
        // 6. 替换LoadedApk中的mClassLoader
        Reflection.setField("android.app.LoadedApk", "mClassLoader", 
                           loadedApk, dexClassLoader);
        
        // 7. Android 10以下需要手动注入Native库路径
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            installNativeLibraryPath(dexClassLoader);
        }
        
        log("Successfully replaced ClassLoader");
        return true;
        
    } catch (Exception e) {
        log("Error: " + Log.getStackTraceString(e));
        return false;
    }
}
```

#### 版本兼容性工厂方法（核心亮点）

`CompatInMemoryDexClassLoader.create()`是二代加固的核心创新，它根据Android版本自动选择最佳加载方案：

```
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

#### 版本兼容性详解图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      InMemoryDexClassLoader 版本支持                             │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  ✅ Android 10+ (API 29+)                                                       │
│  ───────────────────────────────────────────────────────────────────────────    │
│  构造函数: InMemoryDexClassLoader(ByteBuffer[], libraryPath, parent)            │
│                                                                                 │
│  • 完整支持多DEX                                                                 │
│  • 完整支持Native库路径                                                          │
│  • 纯内存加载，不落地                                                            │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  ⚠️ Android 8.1-9 (API 27-28)                                                   │
│  ───────────────────────────────────────────────────────────────────────────    │
│  构造函数: InMemoryDexClassLoader(ByteBuffer[], parent)                         │
│                                                                                 │
│  • 支持多DEX                                                                     │
│  • 不支持libraryPath参数                                                         │
│  • 需要使用RetroLoadLibrary手动注入Native库路径                                   │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  ⚠️ Android 8.0 (API 26)                                                        │
│  ───────────────────────────────────────────────────────────────────────────    │
│  构造函数: InMemoryDexClassLoader(ByteBuffer, parent)                           │
│                                                                                 │
│  • 仅支持单个ByteBuffer                                                          │
│  • 多DEX需要多次使用InMemoryDexClassLoader加载dexFile后                          │
│    反射注入到 BaseDexClassLoader.pathList.dexElements                           │
│  • 不支持libraryPath                                                            │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  🔨 Android 5.0-7.1 (API 21-25)                                                 │
│  ───────────────────────────────────────────────────────────────────────────    │
│  构造函数: CompatInMemoryDexClassLoader（自定义实现）                             │
│                                                                                 │
│  • InMemoryDexClassLoader 不存在                                                 │
│  • 通过反射将DEX数据注入到BaseDexClassLoader.pathList.dexElements                │
│  • 优先尝试内存加载出dex的方法，失败则回退到临时文件方案                            │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  ❌ Android 4.x (API < 21)                                                      │
│  ───────────────────────────────────────────────────────────────────────────    │
│  示例Demo未做支持二代加固                                                         │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### 2.4 Android 5.0-7.1 兼容实现（CompatInMemoryDexClassLoader）

> **与一代的区别**：一代无需此兼容逻辑。二代由于使用内存加载，必须在无`InMemoryDexClassLoader`的旧版本上手动实现DEX到`dexElements`的注入。

##### 核心挑战

Android 5.0-7.1没有`InMemoryDexClassLoader`，必须通过反射实现内存加载：

```
/**
 * CompatInMemoryDexClassLoader - 兼容Android 5.0-7.1的内存DEX加载器
 *
 * 核心原理：
 * 1. 创建空的BaseDexClassLoader
 * 2. 通过反射获取其内部的DexPathList.dexElements数组
 * 3. 将内存中的DEX数据转换为DexElement对象
 * 4. 将新的DexElement注入到dexElements数组中
 */
public class CompatInMemoryDexClassLoader extends BaseDexClassLoader {

    private final Context mContext;
    private final List<File> mTempFiles = new ArrayList<>();

    public CompatInMemoryDexClassLoader(ByteBuffer[] dexBuffers,
                                        Context context,
                                        ClassLoader parent) {
        super("", null, null, parent);  // 空路径初始化
        this.mContext = context;
        loadDexBuffers(dexBuffers);     // 手动加载DEX
    }

    /**
     * 加载多个DEX字节数据
     *
     * 关键步骤：
     * 1. 反射获取pathList字段
     * 2. 反射获取dexElements数组
     * 3. 为每个DEX创建Element对象
     * 4. 合并新旧Element并设置回去
     */
    private void loadDexBuffers(ByteBuffer[] dexBuffers) {
        try {
            // 1. 获取pathList字段
            Field pathListField = BaseDexClassLoader.class
                    .getDeclaredField("pathList");
            pathListField.setAccessible(true);
            Object pathList = pathListField.get(this);

            // 2. 获取dexElements数组
            Field dexElementsField = pathList.getClass()
                    .getDeclaredField("dexElements");
            dexElementsField.setAccessible(true);
            Object[] existingElements = (Object[]) dexElementsField.get(pathList);

            // 3. 为每个DEX创建Element
            List<Object> newElementsList = new ArrayList<>();
            for (int i = 0; i < dexBuffers.length; i++) {
                byte[] dexBytes = bufferToBytes(dexBuffers[i]);

                // 验证DEX魔数
                if (!validateDex(dexBytes)) {
                    log("Invalid dex at index " + i);
                    continue;
                }

                Object element = createDexElement(dexBytes, i);
                if (element != null) {
                    newElementsList.add(element);
                }
            }

            // 4. 合并Elements（新的放前面，优先级更高）
            Object[] newElements = mergeElements(existingElements,
                    newElementsList.toArray());

            // 5. 设置回pathList
            dexElementsField.set(pathList, newElements);

            log("Successfully loaded " + newElementsList.size() + " dex files");

        } catch (Exception e) {
            throw new RuntimeException("Failed to load dex from memory", e);
        }
    }
}
```

#### ClassLoader内部结构

要理解为什么需要反射注入，必须了解`BaseDexClassLoader`的内部结构：

```
classDiagram
    direction TB
    
    class ClassLoader {
        <<abstract>>
        #ClassLoader parent
        +loadClass(String name) Class~?~
        +findClass(String name) Class~?~
        #findLoadedClass(String name) Class~?~
    }
    
    class BaseDexClassLoader {
        -DexPathList pathList
        +BaseDexClassLoader(String dexPath, File optimizedDir, String libraryPath, ClassLoader parent)
        +findClass(String name) Class~?~
        +findLibrary(String name) String
        #findResource(String name) URL
    }
    
    class DexPathList {
        -Element[] dexElements ⚡注入目标
        -List~File~ nativeLibraryDirectories
        -List~File~ systemNativeLibraryDirectories
        -NativeLibraryElement[] nativeLibraryPathElements
        +findClass(String name, List~Throwable~ suppressed) Class~?~
        +findLibrary(String libraryName) String
        -makePathElements(List~File~ files) Element[]
    }
    
    class Element {
        <<DexPathList.Element>>
        -DexFile dexFile 📦DEX字节码
        -File path 📂文件路径(可为null)
        +findClass(String name, ClassLoader definingContext, List~Throwable~ suppressed) Class~?~
    }
    
    class DexFile {
        <<dalvik.system>>
        -long mCookie
        -String mFileName
        +loadClass(String name, ClassLoader loader) Class~?~
        +entries() Enumeration~String~
        +close() void
    }
    
    class NativeLibraryElement {
        <<DexPathList.NativeLibraryElement>>
        -File path
        +findNativeLibrary(String name) String
    }

    ClassLoader <|-- BaseDexClassLoader : extends
    BaseDexClassLoader *-- DexPathList : contains
    DexPathList *-- "1..*" Element : dexElements
    DexPathList *-- "0..*" NativeLibraryElement : nativeLibraryPathElements
    Element *-- DexFile : contains
    
    note for DexPathList "🎯 反射注入的核心目标\n通过修改dexElements数组\n实现内存DEX加载"
    note for Element "💡 每个Element对应一个DEX\n内存加载时path可为null"
```

#### DexElement创建策略

创建`DexPathList.Element`对象是最复杂的部分，因为不同Android版本的构造函数参数不同：

```
/**
 * 创建DexElement对象
 *
 * 策略：
 * 1. Android 8.0+：从InMemoryDexClassLoader提取
 * 2. Android 5.0-7.1：优先内存方法，失败则临时文件
 */
private Object createDexElement(byte[] dexBytes, int index) throws Exception {

    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
        // ==================== Android 8.0+ ====================
        // 借用InMemoryDexClassLoader来创建DexElement
        return createDexElementForAndroid8(dexBytes, index);

    } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
        // ==================== Android 5.0-7.1 ====================
        try {
            // 优先尝试内存加载方案
            return createDexElementInMemory(dexBytes, index);
        } catch (Exception e) {
            // 回退到临时文件方案
            return createDexElementViaFile(dexBytes, index);
        }
    }

    throw new RuntimeException("Unsupported Android version");
}

/**
 * Android 8.0+ 方案：从InMemoryDexClassLoader提取Element
 */
private Object createDexElementForAndroid8(byte[] dexBytes, int index)
        throws Exception {
    // 1. 创建临时InMemoryDexClassLoader
    ByteBuffer buffer = ByteBuffer.wrap(dexBytes);
    InMemoryDexClassLoader tempLoader =
            new InMemoryDexClassLoader(buffer, getClass().getClassLoader());

    // 2. 反射获取其pathList
    Field pathListField = BaseDexClassLoader.class.getDeclaredField("pathList");
    pathListField.setAccessible(true);
    Object tempPathList = pathListField.get(tempLoader);

    // 3. 反射获取dexElements
    Field dexElementsField = tempPathList.getClass().getDeclaredField("dexElements");
    dexElementsField.setAccessible(true);
    Object[] tempElements = (Object[]) dexElementsField.get(tempPathList);

    // 4. 返回提取的Element
    return tempElements[0];
}

/**
 * Android 5.0-7.1 内存加载方案（多种尝试）
 */
private Object createDexElementInMemory(byte[] dexBytes, int index)
        throws Exception {

    Class<?> dexFileClass = Class.forName("dalvik.system.DexFile");
    File optimizedDir = getOptimizedDexDir();
    String optimizedPath = optimizedDir + "/memory_dex_" + index + ".odex";

    // ========== 方法1: loadDex(byte[], String, int) ==========
    // 部分定制ROM支持此方法
    try {
        Method loadDexMethod = dexFileClass.getDeclaredMethod(
                "loadDex", byte[].class, String.class, int.class);
        loadDexMethod.setAccessible(true);

        DexFile dexFile = (DexFile) loadDexMethod.invoke(
                null, dexBytes, optimizedPath, 0);
        if (dexFile != null) {
            log("loadDex(byte[]) succeeded");
            return createElementObject(dexFile, null);
        }
    } catch (NoSuchMethodException e) {
        // 方法不存在，尝试下一个
    }

    // ========== 方法2: openInMemoryDexFile ==========
    try {
        Method openMethod = dexFileClass.getDeclaredMethod(
                "openInMemoryDexFile", byte[].class, int.class, int.class);
        openMethod.setAccessible(true);

        DexFile dexFile = (DexFile) openMethod.invoke(
                null, dexBytes, 0, dexBytes.length);
        if (dexFile != null) {
            log("openInMemoryDexFile succeeded");
            return createElementObject(dexFile, null);
        }
    } catch (NoSuchMethodException e) {
        // 方法不存在，尝试下一个
    }

    // ========== 方法3: DexFile(byte[]) 构造函数 ==========
    try {
        Constructor<?> constructor = dexFileClass.getDeclaredConstructor(byte[].class);
        constructor.setAccessible(true);

        DexFile dexFile = (DexFile) constructor.newInstance((Object) dexBytes);
        log("DexFile(byte[]) succeeded");
        return createElementObject(dexFile, null);
    } catch (NoSuchMethodException e) {
        // 构造函数不存在
    }

    // 所有内存方法都失败
    throw new RuntimeException("No in-memory loading method available");
}
```

#### Element构造函数版本差异

不同Android版本的`DexPathList.Element`构造函数参数完全不同：

```
/**
 * 创建DexPathList.Element对象
 *
 * 不同版本构造函数差异：
 * - Android 8.0+ (API 26+): Element(DexFile)
 * - Android 7.0-7.1 (API 24-25): Element(File, boolean, File, DexFile)
 * - Android 6.0 (API 23): Element(File, boolean, File, DexFile)
 * - Android 5.0-5.1 (API 21-22): Element(File, boolean, File, DexFile)
 */
private Object createElementObject(DexFile dexFile, File dexPath) throws Exception {
    Class<?> elementClass = Class.forName("dalvik.system.DexPathList$Element");

    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
        // ==================== Android 8.0+ ====================
        // 构造函数：Element(DexFile dexFile)
        Constructor<?> constructor = elementClass.getDeclaredConstructor(DexFile.class);
        constructor.setAccessible(true);
        return constructor.newInstance(dexFile);

    } else {
        // ==================== Android 5.0-7.1 ====================
        // 构造函数：Element(File path, boolean isDirectory, File zip, DexFile dexFile)
        try {
            Constructor<?> constructor = elementClass.getDeclaredConstructor(
                    File.class, boolean.class, File.class, DexFile.class);
            constructor.setAccessible(true);
            return constructor.newInstance(dexPath, false, dexPath, dexFile);
        } catch (NoSuchMethodException e) {
            // 回退：遍历所有构造函数尝试匹配
            return createElementFallback(elementClass, dexFile, dexPath);
        }
    }
}

/**
 * 备用方案：遍历所有构造函数尝试匹配
 */
private Object createElementFallback(Class<?> elementClass,
                                     DexFile dexFile, File dexPath) throws Exception {
    Constructor<?>[] constructors = elementClass.getDeclaredConstructors();

    for (Constructor<?> constructor : constructors) {
        Class<?>[] paramTypes = constructor.getParameterTypes();
        constructor.setAccessible(true);

        try {
            if (paramTypes.length == 1 && paramTypes[0] == DexFile.class) {
                // Element(DexFile)
                return constructor.newInstance(dexFile);

            } else if (paramTypes.length == 4) {
                // Element(File, boolean, File, DexFile)
                return constructor.newInstance(dexPath, false, dexPath, dexFile);
            }
        } catch (Exception e) {
            continue;
        }
    }

    throw new RuntimeException("No suitable Element constructor found");
}
```

#### 临时文件回退方案

当内存加载失败时，回退到临时文件方案（仍比一代安全，因为用后即删）：

```
/**
 * 临时文件方案（Android 5.0-7.1回退使用）
 *
 * 流程：
 * 1. 将DEX写入临时文件
 * 2. 使用DexFile.loadDex加载
 * 3. 创建Element对象
 * 4. 运行后安全删除临时文件
 */
@SuppressWarnings("deprecation")
private Object createDexElementViaFile(byte[] dexBytes, int index) throws Exception {
    // 1. 创建临时文件
    File tempDir = getTempDexDir();
    String tempFileName = "memory_dex_" + System.currentTimeMillis() + "_" + index + ".dex";
    File tempFile = new File(tempDir, tempFileName);

    try {
        // 2. 写入DEX数据
        FileOutputStream fos = new FileOutputStream(tempFile);
        fos.write(dexBytes);
        fos.flush();
        fos.close();

        // 记录临时文件，后续清理
        mTempFiles.add(tempFile);

        // 3. 使用DexFile.loadDex加载（API 26已废弃，但5.0-7.1有效）
        File optimizedDir = getOptimizedDexDir();
        DexFile dexFile = DexFile.loadDex(
                tempFile.getAbsolutePath(),
                optimizedDir.getAbsolutePath() + "/" + tempFileName + ".odex",
                0
        );

        // 4. 创建Element对象
        return createElementObject(dexFile, tempFile);

    } catch (Exception e) {
        // 失败时清理临时文件
        secureDelete(tempFile);
        throw e;
    }
}

/**
 * 安全删除文件（先清空内容再删除）
 */
private void secureDelete(File file) {
    if (file != null && file.exists()) {
        try {
            // 先清空文件内容
            RandomAccessFile raf = new RandomAccessFile(file, "rws");
            raf.setLength(0);
            raf.close();
        } catch (IOException ignored) {}
        file.delete();
    }
}

/**
 * 清理所有临时文件（应用退出时调用）
 */
public void cleanup() {
    synchronized (mTempFiles) {
        for (File file : mTempFiles) {
            secureDelete(file);
        }
        mTempFiles.clear();
    }
}
```

#### 2.5 Native库路径注入（RetroLoadLibrary）

> **与一代的区别**：这是二代加固**新增的组件**。一代使用`DexClassLoader`原生支持`librarySearchPath`参数，而二代的`InMemoryDexClassLoader`在Android 10以下不支持该参数，因此需要手动注入。

##### 问题背景

Android 10以下版本的`InMemoryDexClassLoader`不支持`librarySearchPath`参数：

| Android版本 | 构造函数 | Native库支持 |
| --- | --- | --- |
| Android 10+ | `InMemoryDexClassLoader(ByteBuffer[], libraryPath, parent)` | 原生支持 |
| Android 8.0-9 | `InMemoryDexClassLoader(ByteBuffer[], parent)` | 不支持 |
| Android 5.0-7.1 | 无此API | 不支持 |

这意味着如果源应用包含Native库（JNI），在Android 10以下版本会出现`UnsatisfiedLinkError`。

#### 解决方案

使用从**Tinker热修复框架**移植的`RetroLoadLibrary`工具类，通过反射将Native库路径注入到`DexPathList`中：

```
/**
 * RetroLoadLibrary.java - Native库路径注入工具
 *
 * 来源：Tinker热修复框架
 * 功能：将Native库路径注入到ClassLoader中，解决JNI加载问题
 */
public class RetroLoadLibrary {

    /**
     * 安装Native库路径
     * 根据Android版本选择不同的注入方案
     */
    public static synchronized void installNativeLibraryPath(
            ClassLoader classLoader, File folder) throws Throwable {

        if (folder == null || !folder.exists()) {
            Log.i(TAG, "folder is illegal: " + folder);
            return;
        }

        // 根据Android版本选择注入方案
        if (Build.VERSION.SDK_INT >= 25) {
            // Android 7.1+ (API 25+)
            try {
                V25.install(classLoader, folder);
                return;
            } catch (Throwable e) {
                // 回退到V23方案
                V23.install(classLoader, folder);
            }
        } else if (Build.VERSION.SDK_INT >= 23) {
            // Android 6.0-7.0 (API 23-24)
            try {
                V23.install(classLoader, folder);
            } catch (Throwable e) {
                // 回退到V14方案
                V14.install(classLoader, folder);
            }
        } else if (Build.VERSION.SDK_INT >= 14) {
            // Android 4.0-5.1 (API 14-22)
            V14.install(classLoader, folder);
        }
    }
}
```

#### DexPathList结构（Native库相关）

```
DexPathList
│
├── dexElements: Element[]                          ← DEX加载元素
│
├── nativeLibraryDirectories: List<File>            ← 用户Native库目录
│   └── [/data/app/<package>/lib/arm64, ...]
│
├── systemNativeLibraryDirectories: List<File>      ← 系统Native库目录
│   └── [/system/lib64, /vendor/lib64, ...]
│
└── nativeLibraryPathElements: NativeLibraryElement[]  ← 合并后的搜索路径
    └── 用于findLibrary()查找.so文件
```

#### Android 4.0-5.1 注入方案（V14）

最简单的版本，直接扩展`nativeLibraryDirectories`数组：

```
/**
 * V14方案（Android 4.0-5.1）
 *
 * DexPathList内部结构：
 * - nativeLibraryDirectories: File[]  ← 直接是数组
 */
private static final class V14 {
    private static void install(ClassLoader classLoader, File folder) throws Throwable {
        // 1. 获取pathList
        Field pathListField = ReflectUtil.findField(classLoader, "pathList");
        Object dexPathList = pathListField.get(classLoader);

        // 2. 扩展nativeLibraryDirectories数组
        // 原始数组：[/system/lib]
        // 扩展后：  [/data/.../lib, /system/lib]
        ReflectUtil.expandFieldArray(
                dexPathList,
                "nativeLibraryDirectories",
                new File[]{folder}
        );
    }
}
```

#### Android 6.0-7.0 注入方案（V23）

从Android 6.0开始，`nativeLibraryDirectories`变成`List<File>`，且需要重建`nativeLibraryPathElements`：

```
/**
 * V23方案（Android 6.0-7.0）
 *
 * DexPathList内部结构：
 * - nativeLibraryDirectories: List<File>       ← 变成List
 * - systemNativeLibraryDirectories: List<File> ← 新增系统目录
 * - nativeLibraryPathElements: Element[]       ← 需要重建
 */
private static final class V23 {
    private static void install(ClassLoader classLoader, File folder) throws Throwable {
        // 1. 获取pathList
        Field pathListField = ReflectUtil.findField(classLoader, "pathList");
        Object dexPathList = pathListField.get(classLoader);

        // 2. 获取并修改nativeLibraryDirectories
        Field nativeLibDirsField = ReflectUtil.findField(
                dexPathList, "nativeLibraryDirectories");
        List<File> origLibDirs = (List<File>) nativeLibDirsField.get(dexPathList);

        // 创建新列表（原列表可能是不可修改的）
        ArrayList<File> libDirs = new ArrayList<>(origLibDirs);
        libDirs.add(0, folder);  // 新路径放在最前面，优先搜索
        nativeLibDirsField.set(dexPathList, libDirs);

        // 3. 获取systemNativeLibraryDirectories
        Field sysLibDirsField = ReflectUtil.findField(
                dexPathList, "systemNativeLibraryDirectories");
        List<File> systemLibDirs = (List<File>) sysLibDirsField.get(dexPathList);

        // 4. 合并所有目录
        ArrayList<File> allLibDirs = new ArrayList<>(libDirs);
        allLibDirs.addAll(systemLibDirs);

        // 5. 调用makePathElements重建nativeLibraryPathElements
        // 签名：static Element[] makePathElements(List<File>, File, List<IOException>)
        Method makePathElements = ReflectUtil.findMethod(
                dexPathList, "makePathElements",
                List.class, File.class, List.class);

        ArrayList<IOException> suppressedExceptions = new ArrayList<>();
        Object[] elements = (Object[]) makePathElements.invoke(
                dexPathList, allLibDirs, null, suppressedExceptions);

        // 6. 设置新的nativeLibraryPathElements
        Field elementsField = ReflectUtil.findField(
                dexPathList, "nativeLibraryPathElements");
        elementsField.set(dexPathList, elements);
    }
}
```

#### Android 7.1+ 注入方案（V25）

与V23类似，但`makePathElements`方法签名不同：

```
/**
 * V25方案（Android 7.1+）
 *
 * 与V23的区别：
 * makePathElements方法签名变化：
 * - V23: makePathElements(List<File>, File, List<IOException>)
 * - V25: makePathElements(List<File>)  ← 参数简化
 */
private static final class V25 {
    private static void install(ClassLoader classLoader, File folder) throws Throwable {
        // 步骤1-4与V23相同...

        // 5. 调用makePathElements（参数更简单）
        // 签名：static NativeLibraryElement[] makePathElements(List<File>)
        Method makePathElements = ReflectUtil.findMethod(
                dexPathList, "makePathElements", List.class);

        Object[] elements = (Object[]) makePathElements.invoke(
                dexPathList, allLibDirs);

        // 6. 设置新的nativeLibraryPathElements
        Field elementsField = ReflectUtil.findField(
                dexPathList, "nativeLibraryPathElements");
        elementsField.set(dexPathList, elements);
    }
}
```

#### Native库注入流程图

```
调用 System.loadLibrary("native-lib")
                    │
                    ↓
ClassLoader.findLibrary("native-lib")
                    │
                    ↓
DexPathList.findLibrary("native-lib")
                    │
                    ↓
遍历 nativeLibraryPathElements
                    │
    ┌───────────────┼───────────────┐
    ↓               ↓               ↓
Element[0]      Element[1]      Element[2]
/data/.../lib   /system/lib64   /vendor/lib64
    │
    ↓
检查 /data/.../lib/libnative-lib.so 是否存在
    │
    ├── 存在 → 返回完整路径
    └── 不存在 → 继续下一个Element

注入前：[/system/lib64, /vendor/lib64]
注入后：[/data/.../lib, /system/lib64, /vendor/lib64]
        ↑
        新增的路径，优先搜索
```

#### 2.6 Application替换

> **与一代的区别**：此部分逻辑与一代加固**完全相同**，无需修改。Application替换是Android系统级别的操作，与DEX加载方式无关。

##### 与一代加固的对比

Application替换逻辑与一代加固**完全相同**，因为这是Android系统级别的操作，与DEX加载方式无关：

```
/**
 * 替换系统中的Application引用
 *
 * 需要替换的位置：
 * 1. LoadedApk.mApplication
 * 2. ActivityThread.mInitialApplication
 * 3. ActivityThread.mAllApplications列表
 * 4. ActivityThread.mBoundApplication.appInfo.className
 */
private void replaceApplicationInSystem(Application shellApp,
                                        Application sourceApp) throws Exception {
    // ==================== 替换1: LoadedApk.mApplication ====================
    Context contextImpl = getApplicationContext();
    Class<?> contextImplClass = Class.forName("android.app.ContextImpl");

    // 获取ContextImpl.mPackageInfo (即LoadedApk)
    Field mPackageInfoField = findField(contextImplClass, "mPackageInfo");
    Object loadedApk = mPackageInfoField.get(contextImpl);

    // 替换LoadedApk.mApplication
    Field mApplicationField = findField(loadedApk.getClass(), "mApplication");
    mApplicationField.set(loadedApk, sourceApp);
    log("Replaced LoadedApk.mApplication");

    // ==================== 替换2&3: ActivityThread ====================
    Object activityThread = getActivityThread();

    // 替换mInitialApplication
    Field mInitialAppField = findField(activityThread.getClass(), "mInitialApplication");
    mInitialAppField.set(activityThread, sourceApp);
    log("Replaced ActivityThread.mInitialApplication");

    // 更新mAllApplications列表
    Field mAllAppsField = findField(activityThread.getClass(), "mAllApplications");
    ArrayList<Application> mAllApplications =
            (ArrayList<Application>) mAllAppsField.get(activityThread);
    mAllApplications.remove(shellApp);   // 移除壳Application
    mAllApplications.add(sourceApp);     // 添加源Application
    log("Updated ActivityThread.mAllApplications");

    // ==================== 替换4: BoundApplication.appInfo ====================
    updateBoundApplicationInfo(activityThread, mApplicationName);
}
```

#### Application替换后的系统状态

```
替换前：
┌──────────────────────────────────────────────────────────────┐
│ ActivityThread                                               │
│   ├── mInitialApplication ──→ ShellProxyApplicationV2       │
│   ├── mAllApplications: [ShellProxyApplicationV2]           │
│   └── mBoundApplication                                      │
│         └── appInfo.className = "...ShellProxyApplicationV2"│
├──────────────────────────────────────────────────────────────┤
│ LoadedApk                                                    │
│   └── mApplication ──→ ShellProxyApplicationV2              │
└──────────────────────────────────────────────────────────────┘

替换后：
┌──────────────────────────────────────────────────────────────┐
│ ActivityThread                                               │
│   ├── mInitialApplication ──→ SourceApplication [OK]        │
│   ├── mAllApplications: [SourceApplication] [OK]            │
│   └── mBoundApplication                                      │
│         └── appInfo.className = "...SourceApplication" [OK] │
├──────────────────────────────────────────────────────────────┤
│ LoadedApk                                                    │
│   └── mApplication ──→ SourceApplication [OK]               │
└──────────────────────────────────────────────────────────────┘
```

#### 调用源Application的生命周期

```
/**
 * 调用源Application的attachBaseContext
 *
 * 关键：必须正确初始化Context，否则会导致NPE
 */
private void invokeSourceApplicationAttach(Application application,
                                           Context baseContext) throws Exception {
    // 方法1：调用attach方法（首选）
    try {
        Method attachMethod = findMethod(Application.class, "attach");
        if (attachMethod != null) {
            attachMethod.setAccessible(true);
            attachMethod.invoke(application, baseContext);
            log("Called attach method");
            return;
        }
    } catch (Exception e) {
        log("attach method failed: " + e.getMessage());
    }

    // 方法2：调用attachBaseContext方法
    try {
        Method attachBaseContextMethod = findMethod(Application.class, "attachBaseContext");
        if (attachBaseContextMethod != null) {
            attachBaseContextMethod.setAccessible(true);
            attachBaseContextMethod.invoke(application, baseContext);
            log("Called attachBaseContext method");
            return;
        }
    } catch (Exception e) {
        log("attachBaseContext failed: " + e.getMessage());
    }

    // 方法3：手动设置Context字段
    manuallyAttachContext(application, baseContext);
}

/**
 * 手动设置Application的Context字段
 */
private void manuallyAttachContext(Application application,
                                   Context baseContext) throws Exception {
    // ContextWrapper.mBase字段存储实际的Context实现
    Field mBaseField = findField(ContextWrapper.class, "mBase");
    mBaseField.set(application, baseContext);
    log("Set ContextWrapper.mBase field");
}
```

#### onCreate调用

```
@Override
public void onCreate() {
    super.onCreate();
    log("ShellProxyApplicationV2.onCreate() running!");

    if (mSourceApplication != null) {
        try {
            // 验证Context状态
            Context sourceContext = mSourceApplication.getApplicationContext();
            if (sourceContext == null) {
                log("Source application context is null, trying to fix...");
                manuallyAttachContext(mSourceApplication, getApplicationContext());
            }

            // 调用源程序的onCreate
            mSourceApplication.onCreate();
            log("Successfully called onCreate on source application");

        } catch (Exception e) {
            log("Error calling onCreate: " + Log.getStackTraceString(e));
        }
    }
}
```

### 模块三：Source-App 源程序模块

> **相对一代的改动**：此模块与一代加固**基本相同**，无需特殊改动。源应用的代码结构、AndroidManifest配置等保持一致，仅需修改配置文件使得源程序能生成多个dex文件。

#### 3.1 与一代的对比

| 对比项 | 一代加固 Source-App | 二代加固 Source-App |
| --- | --- | --- |
| **代码改动** | 无需修改 | 无需修改 |
| **Manifest配置** | 无需修改 | 无需修改 |
| **Multidex兼容** | 限制只能生成1个dex | `gradle配置支持多dex` |
| **Native库** | 原生支持 | 原生支持 |
| **最低SDK** | API 14+ | API 21+ |

#### 3.2 源程序要求

##### 对源程序的要求

二代加固对源程序的要求与一代完全一致，仅有一点改动：

1. **Multidex支持**
   - 二代加固支持Multidex生成多dex，源程序无需做任何改动
   - build.gradle.kts配置文件删除混淆使得方法数增加，开启支持MultiDex以支持生成多个dex

#### 3.3 加固后的APK结构

```
加固后的APK结构：
├── AndroidManifest.xml    ← 修改：application指向壳Application
├── classes.dex            ← 核心：[壳DEX][加密DEX集合][大小]
├── lib/                   ← 保持：原Native库
│   ├── armeabi-v7a/
│   ├── arm64-v8a/
│   └── ...
├── res/                   ← 保持：原资源文件
├── assets/                ← 保持：原资产文件
└── META-INF/              ← 重新签名
```

---

### 总结：一代与二代加固对比

| 特性 | 一代加固 (V1) | 二代加固 (V2) |
| --- | --- | --- |
| **DEX存储位置** | 写入文件系统 | 仅在内存中 |
| **核心ClassLoader** | `DexClassLoader` | `InMemoryDexClassLoader` |
| **安全性** | 中等（可被文件监控） | 较高（需内存dump） |
| **最低版本** | Android 4.0+ | Android 5.0+ |
| **兼容性复杂度** | 低 | 高（需处理多版本差异） |
| **Native库支持** | 原生支持 | 需手动注入（Android 10以下） |
| **Multidex支持** | 需控制单个dex生成 | 可支持多dex |

#### 二代加固的优势

1. **更高安全性**：DEX不落地，攻击者无法通过文件监控获取
2. **原生Multidex支持**：`ByteBuffer[]`天然支持多DEX
3. **更快的加载速度**：无需写入磁盘的I/O开销

#### 二代加固的挑战

1. **版本兼容性**：需要处理Android 5.0-9的各种API差异
2. **Native库注入**：Android 10以下需要手动处理

#### 进一步安全增强

二代加固虽然比一代安全，但仍然可以通过**内存dump**技术获取DEX。为进一步增强安全性，后续的技术路线将沿下面方向发展：

1. **指令抽离**：发布时清除DEX函数体（CodeItem）并单独加密存储；运行时按需恢复至内存
2. **Native化**：将Java代码转换为Native代码
3. **VMP（虚拟机保护）**：将关键代码转换为自定义字节码

这将是本系列后续文章的演进思路。

下一篇指令抽离思想的第三代加固[《Android第三代加固技术原理详解（附源码）》](https://juejin.cn/post/7629931535735406633 "https://juejin.cn/post/7629931535735406633")
