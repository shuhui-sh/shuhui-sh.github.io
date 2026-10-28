---
title: "Android第一代加固技术原理详解（附源码）"
date: 2026-04-02
description: "所谓加固，其实就是通过一些手段隐藏业务代码实现的细节，增加反编译工具（如jadx等）对apk进行反编译、静态分析代码的难度。"
tags: ['Android']
category: "技术"
---
> 作者：见前行
> 发布于：2025-08-30
> 原文链接：https://juejin.cn/post/7543901300719681570

所谓加固，其实就是通过一些手段隐藏业务代码实现的细节，增加反编译工具（如jadx等）对apk进行反编译、静态分析代码的难度。

---

## 加固概述

所谓加固，其实就是通过一些手段隐藏业务代码实现的细节，增加反编译工具（如jadx等）对apk进行反编译静态分析代码的难度。

### Android 加固技术代际发展概览

| **代际** | **技术名称** | **核心原理** | **主要优势** | **固有缺陷** |
| --- | --- | --- | --- | --- |
| **第一代** | 动态加载（落地加载） | 将程序切分为加载器（Loader）和加密的关键逻辑（Payload），运行时解密Payload至文件系统后加载 | 实现简单，兼容性好；有效对抗静态分析 | Payload需落地文件系统，易被复制；易被自定义虚拟机拦截关键函数 |
| **第二代** | 不落地加载 | Payload在内存中解密，直接通过虚拟机内部接口加载，避免文件落地 | 避免文件泄露；开发流程零干扰 | 启动时加解密耗时，导致黑屏；内存中DEX连续完整，可被调试工具（如GDB）Dump |
| **第三代** | 指令抽离 | 发布时清除DEX函数体（CodeItem）并单独加密存储；运行时按需恢复至内存 | 函数级保护；内存中无连续DEX，增加Dump难度 | 兼容性差（依赖未公开的虚拟机特性）；与JIT优化冲突；可通过解释器记录函数内容还原DEX |
| **第四代** | 指令转换/VMP加固 | 将Java函数标记为Native（dex2c），转换为自定义指令或动态库，由私有解释器执行；通过JNI与系统交互 | 对抗内存Dump；自定义指令集提高逆向难度 | 兼容性问题（同第三代）；性能损耗大；仅保护Java层，未覆盖Native代码（C/C++） |
| **第五代** | 虚拟机源码保护 | 核心代码编译为中间二进制，在独立虚拟环境中执行；支持多语言（Java、C++、Swift等） | 全代码类型保护；可变指令集抗逆向；内置反调试探针 | 理论仍可破解（需掌握虚拟机指令机制），但难度极高；需平衡性能与安全性 |

> 不管技术发展到几代，第一代的原理是后续所有代际发展的基础中的基础，所以理解第一代的技术原理是重中之重。

---

## 项目概述

AppShield是一个完整的Android APK加壳保护系统，采用模块化设计，包含三个核心模块：

- **packer**: 加壳工具模块，负责将源APK和壳APK合并
- **shell-app**: 壳程序模块，负责运行时解密和加载源程序
- **source-app**: 源程序模块，被保护的目标应用

---

## 模块一：Packer 加壳工具模块

### 1.1 模块架构

```
packer/
├── build.gradle.kts          # 构建配置，支持fatJar打包
└── src/main/java/com/csh/packer/
    ├── PackerMain.java        # 主入口，命令行参数解析
    ├── ApkPacker.java         # 核心加壳逻辑
    ├── apktool/               # APK解包重打包工具
    │   ├── ApkTool.java
    │   └── ApkToolWrapper.java
    ├── dexUtils/              # DEX文件处理
    │   └── DexProcessor.java
    ├── manifestUtils/         # AndroidManifest.xml处理
    │   └── ManifestEditor.java
    ├── sign/                  # APK签名工具
    │   └── ApkSignAndAlignTool.java
    └── utils/                 # 工具类
        ├── FileUtils.java
        └── PathsConfig.java
```

### 1.2 核心功能

#### 加壳流程

```java
/**
 * ApkPacker.java - 核心加壳逻辑
 *
 * 加壳流程：
 * 1. 准备工作目录
 * 2. 使用apktool解包源APK和壳APK
 * 3. 修改壳APK的AndroidManifest.xml（设置application为壳Application）
 * 4. 处理Native库（将源APK的so库复制到壳APK）
 * 5. 合并DEX文件：将加密后的源APK附加到壳DEX末尾
 * 6. 使用apktool重新打包
 * 7. 签名并对齐APK
 */
public class ApkPacker {
    private static final String TAG = "ApkPacker";

    // 合并后的DEX格式：[壳DEX][加密源APK][源APK大小(4字节)]
    public void start() {
        log("=== AppShield 加壳工具启动 ===");

        // 1. 准备工作目录
        prepareDirectories();

        // 2. 解包APK
        extractApks();

        // 3. 处理AndroidManifest.xml
        handleManifest();

        // 4. 处理Native库
        handleNativeLibraries();

        // 5. 合并DEX文件
        combineDexFiles();

        // 6. 重新打包
        repackApk();

        // 7. 签名
        signApk();

        log("=== 加壳完成 ===");
    }
}
```

### 1.3 关键技术点

#### DEX文件合并

```java
/**
 * DexProcessor.java - DEX处理器
 */
public class DexProcessor {

    // DEX文件头偏移量
    private static final int CHECKSUM_OFFSET = 8;    // Adler32校验和偏移
    private static final int SIGNATURE_OFFSET = 12;  // SHA-1签名偏移
    private static final int FILE_SIZE_OFFSET = 32;  // 文件大小偏移

    /**
     * 合并壳DEX与加密后的源APK
     *
     * @param shellDexArray   壳DEX数据
     * @param encryptedSrcApk 加密后的源APK
     * @return 合并后的新DEX数据
     */
    public static byte[] mergeShellDexAndSrcApk(byte[] shellDexArray, byte[] encryptedSrcApk) {
        // 计算新DEX总大小
        int newDexLen = shellDexArray.length + encryptedSrcApk.length + 4;
        byte[] newDexArray = new byte[newDexLen];

        // 1. 拷贝壳DEX
        System.arraycopy(shellDexArray, 0, newDexArray, 0, shellDexArray.length);

        // 2. 追加加密后的源APK
        System.arraycopy(encryptedSrcApk, 0, newDexArray, shellDexArray.length, encryptedSrcApk.length);

        // 3. 写入源APK大小（4字节，小端序）
        int srcApkSize = encryptedSrcApk.length;
        newDexArray[newDexLen - 4] = (byte) (srcApkSize & 0xFF);
        newDexArray[newDexLen - 3] = (byte) ((srcApkSize >> 8) & 0xFF);
        newDexArray[newDexLen - 2] = (byte) ((srcApkSize >> 16) & 0xFF);
        newDexArray[newDexLen - 1] = (byte) ((srcApkSize >> 24) & 0xFF);

        // 4. 修复DEX头部信息
        fixFileSize(newDexArray, newDexLen);  // 修正文件大小
        fixSignature(newDexArray);             // 重新计算SHA-1签名
        fixCheckSum(newDexArray);              // 重新计算Adler32校验和

        return newDexArray;
    }

    /**
     * XOR加密（与解密使用相同算法）
     */
    public static byte[] encrypt(byte[] data) {
        for (int i = 0; i < data.length; i++) {
            data[i] ^= (byte) 0xFF;  // 每字节与0xFF异或
        }
        return data;
    }

    /**
     * 修正DEX文件大小字段
     */
    private static void fixFileSize(byte[] dex, int size) {
        dex[32] = (byte) (size & 0xFF);
        dex[33] = (byte) ((size >> 8) & 0xFF);
        dex[34] = (byte) ((size >> 16) & 0xFF);
        dex[35] = (byte) ((size >> 24) & 0xFF);
    }

    /**
     * 重新计算SHA-1签名
     */
    private static void fixSignature(byte[] dex) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-1");
            md.update(dex, 32, dex.length - 32);
            byte[] signature = md.digest();
            System.arraycopy(signature, 0, dex, 12, 20);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-1 algorithm not found", e);
        }
    }

    /**
     * 重新计算Adler32校验和
     */
    private static void fixCheckSum(byte[] dex) {
        Adler32 adler32 = new Adler32();
        adler32.update(dex, 12, dex.length - 12);
        long checksum = adler32.getValue();
        dex[8] = (byte) (checksum & 0xFF);
        dex[9] = (byte) ((checksum >> 8) & 0xFF);
        dex[10] = (byte) ((checksum >> 16) & 0xFF);
        dex[11] = (byte) ((checksum >> 24) & 0xFF);
    }
}
```

---

## 模块二：Shell-App 壳程序模块（业内也叫脱壳流程）

### 2.1 模块架构

```
shell-app/
├── src/main/java/com/csh/shell/
│   ├── ShellProxyApplication.java      # 主壳Application
│   ├── ReflectionUtils.java             # 反射工具类
│   └── utils/
│       ├── AESDecrypt.java              # AES解密工具
│       └── FileUtils.java               # 文件操作工具
```

### 2.2 运行时流程

```java
/**
 * ShellProxyApplication.java - 壳Application
 *
 * 核心流程：
 * 1. 从APK读取合并后的classes.dex
 * 2. 从dex尾部提取并解密源APK
 * 3. 将源APK写入私有目录
 * 4. 使用DexClassLoader加载源APK
 * 5. 替换系统ClassLoader引用
 * 6. 替换Application实例
 */
public class ShellProxyApplication extends Application {
    private static final String TAG = "ShellProxy";
    private static final String DEX_FILE = "classes.dex";
    private static final String SOURCE_APK_FILE = "source.apk";
    private static final String DEX_OUTPUT_DIR = "dex_output";

    private String mApplicationName;
    private Application mSourceApplication;

    @Override
    protected void attachBaseContext(Context base) {
        super.attachBaseContext(base);

        try {
            // Step 1: 读取壳DEX文件
            byte[] shellDexData = readDexFromApk(base);

            // Step 2: 从中分离出源APK
            byte[] encryptedSrcApk = extractSourceApk(shellDexData);
            byte[] srcApkData = decrypt(encryptedSrcApk);

            // Step 3: 将源APK写入私有目录
            String srcApkPath = writeSourceApk(base, srcApkData);

            // Step 4: 替换ClassLoader
            boolean classLoaderSuccess = replaceClassLoader(base, srcApkPath);
            if (!classLoaderSuccess) {
                Log.e(TAG, "ClassLoader replacement failed");
                return;
            }

            // Step 5: 获取源程序Application类名
            mApplicationName = getSourceApplicationName();

            // Step 6: 创建源程序Application实例
            mSourceApplication = makeSourceApplication();

            // Step 7: 替换系统中的Application引用
            replaceApplicationInSystem(this, mSourceApplication);

            // Step 8: 调用源程序Application的attachBaseContext
            invokeSourceApplicationAttach(mSourceApplication, base);

            Log.d(TAG, "Shell initialization completed successfully");

        } catch (Throwable e) {
            Log.e(TAG, "Error in attachBaseContext: " + Log.getStackTraceString(e));
        }
    }

    @Override
    public void onCreate() {
        super.onCreate();
        if (mSourceApplication != null) {
            mSourceApplication.onCreate();
        }
    }
}
```

### 2.3 关键步骤：从壳DEX中提取源APK

```java
/**
 * 从壳DEX文件中提取源APK
 *
 * 数据格式（从尾部开始）：
 * ┌────────────────────────────────────────────┐
 * │    壳DEX代码     │      加密源APK      │  大小(4字节)  │
 * └────────────────────────────────────────────┘
 *                                    ← 从这里开始解析
 */
private byte[] extractSourceApk(byte[] shellDexData) {
    int shellDexLength = shellDexData.length;

    // 读取源APK大小（最后4字节，小端序）
    byte[] srcApkSizeByte = new byte[4];
    System.arraycopy(shellDexData, shellDexLength - 4, srcApkSizeByte, 0, 4);

    ByteBuffer wrap = ByteBuffer.wrap(srcApkSizeByte);
    int srcApkSizeInt = wrap.order(ByteOrder.LITTLE_ENDIAN).getInt();

    Log.d(TAG, "源APK大小: " + srcApkSizeInt);

    // 读取加密的源APK数据
    byte[] encryptedSrcApk = new byte[srcApkSizeInt];
    int srcApkOffset = shellDexLength - srcApkSizeInt - 4;
    System.arraycopy(shellDexData, srcApkOffset, encryptedSrcApk, 0, srcApkSizeInt);

    return encryptedSrcApk;
}

/**
 * 简单XOR解密（与加密使用相同算法）
 */
private byte[] decrypt(byte[] data) {
    for (int i = 0; i < data.length; i++) {
        data[i] ^= (byte) 0xFF;
    }
    return data;
}
```

### 2.4 ClassLoader替换

```java
/**
 * 替换壳App的ClassLoader为源App的ClassLoader
 */
private boolean replaceClassLoader(Context context, String srcApkPath) {
    try {
        // 1. 获取当前ClassLoader
        ClassLoader classLoader = context.getClassLoader();

        // 2. 反射获取ActivityThread
        Object activityThread = ReflectionUtils.getStaticField(
            "android.app.ActivityThread", "sCurrentActivityThread");

        // 3. 反射获取LoadedApk
        ArrayMap mPackages = (ArrayMap) ReflectionUtils.getField(
            "android.app.ActivityThread", activityThread, "mPackages");
        WeakReference weakReference = (WeakReference) mPackages.get(context.getPackageName());
        Object loadedApk = weakReference.get();

        // 4. 创建DexClassLoader加载源APK
        String dexOutputDir = context.getDir(DEX_OUTPUT_DIR, Context.MODE_PRIVATE).getAbsolutePath();
        String libPath = context.getApplicationInfo().nativeLibraryDir;

        DexClassLoader dexClassLoader = new DexClassLoader(
            srcApkPath,    // 源APK路径
            dexOutputDir,  // DEX输出目录
            libPath,       // Native库路径
            classLoader.getParent()
        );

        // 5. 替换LoadedApk中的mClassLoader
        ReflectionUtils.setField("android.app.LoadedApk", "mClassLoader",
                                loadedApk, dexClassLoader);

        Log.d(TAG, "Successfully replaced ClassLoader");
        return true;

    } catch (Exception e) {
        Log.e(TAG, "Error: " + Log.getStackTraceString(e));
        return false;
    }
}
```

### 2.5 Application替换

```java
/**
 * 替换系统中的Application引用
 *
 * 需要替换的位置：
 * 1. LoadedApk.mApplication
 * 2. ActivityThread.mInitialApplication
 * 3. ActivityThread.mAllApplications列表
 * 4. ActivityThread.mBoundApplication.appInfo.className
 */
private void replaceApplicationInSystem(Application shellApp, Application sourceApp) throws Exception {
    // ==================== 替换1: LoadedApk.mApplication ====================
    Context contextImpl = getApplicationContext();
    Class<?> contextImplClass = Class.forName("android.app.ContextImpl");

    Field mPackageInfoField = findField(contextImplClass, "mPackageInfo");
    Object loadedApk = mPackageInfoField.get(contextImpl);

    Field mApplicationField = findField(loadedApk.getClass(), "mApplication");
    mApplicationField.set(loadedApk, sourceApp);

    // ==================== 替换2&3: ActivityThread ====================
    Object activityThread = getActivityThread();

    Field mInitialAppField = findField(activityThread.getClass(), "mInitialApplication");
    mInitialAppField.set(activityThread, sourceApp);

    Field mAllAppsField = findField(activityThread.getClass(), "mAllApplications");
    ArrayList<Application> mAllApplications =
            (ArrayList<Application>) mAllAppsField.get(activityThread);
    mAllApplications.remove(shellApp);
    mAllApplications.add(sourceApp);

    // ==================== 替换4: BoundApplication.appInfo ====================
    updateBoundApplicationInfo(activityThread, mApplicationName);
}
```

---

## 模块三：Source-App 源程序模块

### 3.1 模块概述

源程序模块是被保护的目标应用，无需任何特殊处理即可被加壳保护。

### 3.2 对源程序的要求

1. **代码改动**：无需修改源程序代码
2. **Manifest配置**：无需修改AndroidManifest.xml
3. **Native库**：自动处理
4. **Multidex限制**：第一代加固需要控制源程序只生成单个DEX

### 3.3 单DEX优化策略

为确保源程序只生成单个DEX，需要在build.gradle中配置：

```groovy
android {
    // 禁用分包
    dexOptions {
        preDexLibraries = false
    }

    defaultConfig {
        // 设置方法数上限（避免自动分包）
        multiDexEnabled false
    }

    afterEvaluate {
        tasks.matching { it.name.startsWith('dex') }.each { dx ->
            def listFile = project.dir("build").file("maindexlist.txt")
            if (listFile.exists()) {
                dx.additionalParameters = ['--multi-dex', '--main-dex-list=' + listFile, '--minimal-main-dex']
            } else {
                dx.additionalParameters = ['--set-max-idx-number=50000']  // 限制方法数
            }
        }
    }
}
```

---

## 整体架构和工作流程

### 4.1 三模块协作关系

```
┌─────────────────────────────────────────────────────────────┐
│                        加壳流程                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Source-App (源APK)                                        │
│        │                                                    │
│        ├── [apktool解包]                                     │
│        ↓                                                    │
│   Packer (加壳工具)                                         │
│        │                                                    │
│        ├── 修改AndroidManifest.xml                           │
│        ├── 合并DEX文件                                       │
│        ├── 处理Native库                                      │
│        └── 重新打包签名                                      │
│        │                                                    │
│        ↓                                                    │
│   Shell-App (壳APK) ← 输出                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                       运行时流程                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   用户启动加固后的APK                                        │
│        │                                                    │
│        ↓                                                    │
│   ShellProxyApplication.attachBaseContext()                  │
│        │                                                    │
│        ├── 读取合并后的classes.dex                           │
│        ├── 提取并解密源APK                                   │
│        ├── 写入私有目录                                      │
│        ├── 使用DexClassLoader加载                            │
│        ├── 替换ClassLoader                                   │
│        ├── 创建源Application实例                              │
│        └── 替换Application引用                                │
│        │                                                    │
│        ↓                                                    │
│   源程序正常运行                                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 完整工作流程

#### 加壳阶段

1. **准备阶段**：准备好源APK和壳APK
2. **解包阶段**：使用apktool解包两个APK
3. **修改阶段**：修改壳APK的AndroidManifest.xml，将application指向壳Application
4. **合并阶段**：将加密后的源APK附加到壳DEX末尾
5. **打包阶段**：使用apktool重新打包
6. **签名阶段**：使用apksigner对APK进行签名和对齐

#### 运行时阶段

1. **加载阶段**：系统加载壳Application
2. **解密阶段**：从DEX尾部提取并解密源APK
3. **落地阶段**：将解密后的源APK写入私有目录
4. **加载阶段**：使用DexClassLoader加载源APK
5. **替换阶段**：替换系统的ClassLoader和Application引用
6. **运行阶段**：源程序正常运行

---

## 安全性分析

### 第一代加固的优缺点

#### 优点

1. **实现简单**：技术门槛低，容易理解和实现
2. **兼容性好**：支持Android 4.0+所有版本
3. **对抗静态分析**：有效增加反编译难度
4. **开发零干扰**：源程序无需修改

#### 缺点

1. **文件落地**：解密后的APK需要写入文件系统，易被复制
2. **内存完整**：DEX在内存中是完整的，可被调试工具Dump
3. **可被拦截**：自定义虚拟机可以拦截关键函数
4. **单DEX限制**：源程序只能生成单个DEX文件

### 改进方向

1. **不落地加载**：使用InMemoryDexClassLoader（第二代）
2. **指令抽离**：函数体单独加密存储（第三代）
3. **指令转换**：将Java代码转换为自定义指令（第四代）

---

## 总结

第一代加固技术是Android加固技术的基础，虽然存在安全性问题，但其核心原理为后续所有代际的发展奠定了基础。理解第一代加固的工作原理对于掌握更高级的加固技术至关重要。

**核心要点回顾：**

1. **DEX合并技术**：将加密后的源APK附加到壳DEX末尾
2. **DEX头部修复**：修正文件大小、SHA-1签名、Adler32校验和
3. **ClassLoader替换**：通过反射替换系统的ClassLoader
4. **Application替换**：替换系统中所有对Application的引用
5. **生命周期管理**：正确调用源Application的attachBaseContext和onCreate

掌握这些知识点后，就可以深入理解第二代、第三代等更高级的加固技术了。
