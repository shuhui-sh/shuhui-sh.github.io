---
title: "Android第一代加固技术原理详解（附源码）"
description: "所谓加固，其实就是通过一些手段隐藏业务代码实现的细节，增加反编译工具（如jadx等）对apk进行反编译，静态分析业务代码的难度。 ​"
pubDate: "2025-08-30"
tags: ['Android', '逆向']
heroImage: "/images/Android第一代加固技术原理详解-附源码/01.png"
---
## Android第一代加固技术原理详解（附源码）

### 加固概述

所谓加固，其实就是通过一些手段隐藏业务代码实现的细节，增加反编译工具（如jadx等）对apk进行反编译静态分析代码的难度。

#### **​Android 加固技术代际发展概览​**​

| ​**​代际​**​ | ​**​技术名称​**​ | ​**​核心原理​**​ | ​**​主要优势​**​ | ​**​固有缺陷​**​ |
| --- | --- | --- | --- | --- |
| ​**​第一代​**​ | 动态加载（落地加载） | 将程序切分为加载器（Loader）和加密的关键逻辑（Payload），运行时解密Payload至文件系统后加载 | 实现简单，兼容性好；有效对抗静态分析 | Payload需落地文件系统，易被复制；易被自定义虚拟机拦截关键函数 |
| ​**​第二代​**​ | 不落地加载 | Payload在内存中解密，直接通过虚拟机内部接口加载，避免文件落地 | 避免文件泄露；开发流程零干扰 | 启动时加解密耗时，导致黑屏；内存中DEX连续完整，可被调试工具（如GDB）Dump |
| ​**​第三代​**​ | 指令抽离 | 发布时清除DEX函数体（CodeItem）并单独加密存储；运行时按需恢复至内存 | 函数级保护；内存中无连续DEX，增加Dump难度 | 兼容性差（依赖未公开的虚拟机特性）；与JIT优化冲突；可通过解释器记录函数内容还原DEX |
| ​**​第四代​**​ | 指令转换/VMP加固 | 将Java函数标记为Native（dex2c），转换为自定义指令或动态库，由私有解释器执行；通过JNI与系统交互 | 对抗内存Dump；自定义指令集提高逆向难度 | 兼容性问题（同第三代）；性能损耗大；仅保护Java层，未覆盖Native代码（C/C++） |
| ​**​第五代​**​ | 虚拟机源码保护 | 核心代码编译为中间二进制，在独立虚拟环境中执行；支持多语言（Java、C++、Swift等） | 全代码类型保护；可变指令集抗逆向；内置反调试探针 | 理论仍可破解（需掌握虚拟机指令机制），但难度极高；需平衡性能与安全性 |

---

**不管技术发展到几代，第一代的原理是后续所有代际发展的基础中的基础，所以理解第一代的技术原理是重中之重。下面分享实践中编写的一个示例demo(附带大量实现源码)**

### 项目概述

AppShield是一个完整的Android APK加壳保护系统，采用模块化设计，包含三个核心模块：

- **packer**: 加壳工具模块，负责将源APK和壳APK合并
- **shell-app**: 壳程序模块，负责运行时解密和加载源程序
- **source-app**: 源程序模块，被保护的目标应用

### 模块一：Packer 加壳工具模块

#### 1.1 模块架构

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

```
classDiagram
    class PackerMain {
        +main(String[] args) void
        -createOptions() Options
        -printUsage(Options options) void
    }
    
    class ApkPacker {
        -PathsConfig paths
        -ApkTool apkTool
        -ApkSignAndAlignTool signTool
        +start() void
        -prepareDirectories() void
        -extractApks() void
        -handleManifest() void
        -handleNativeLibraries() void
        -combineApks() void
        -repackApk() void
        -signApk() void
    }
    
    class DexProcessor {
        +combineShellDexAndSrcApk() void
        -fixFileSize(byte[], int) void
        -fixSignature(byte[]) void  
        -fixCheckSum(byte[]) void
        -encrypt(byte[]) byte[]
    }
    
    class ManifestEditor {
        -Document document
        +getApplication() String
        +setApplication(String) void
        +addMetaData(String, String) void
        +getManifestData() String
    }
    
    class ApkSignAndAlignTool {
        +resignAndAlign(String, String) boolean
        -alignApk(String, String) boolean
        -signApk(String, String) boolean
    }
    
    PackerMain --> ApkPacker
    ApkPacker --> DexProcessor
    ApkPacker --> ManifestEditor
    ApkPacker --> ApkSignAndAlignTool
```

#### 1.2 核心功能

##### 1.2.1 主要依赖

- **commons-cli**: 命令行参数解析
- **dom4j**: XML文件处理
- **zip4j**: ZIP文件操作增强
- **apksig**: APK签名工具
- **logback**: 日志框架

##### 1.2.2 加壳流程

```
sequenceDiagram
    participant User as 用户
    participant Main as PackerMain
    participant Packer as ApkPacker
    participant Tool as ApkTool
    participant Dex as DexProcessor
    participant Manifest as ManifestEditor
    participant Sign as ApkSignAndAlignTool
    
    User->>Main: 执行加壳命令
    Main->>Packer: start()
    
    Note over Packer: 第一阶段：解包APK
    Packer->>Tool: extractApk(源APK)
    Tool-->>Packer: 解包完成
    Packer->>Tool: extractApk(壳APK)
    Tool-->>Packer: 解包完成
    
    Note over Packer: 第二阶段：处理Manifest
    Packer->>Manifest: handleManifest()
    Manifest->>Manifest: 替换Application为壳Application
    Manifest->>Manifest: 添加源Application到meta-data
    Manifest-->>Packer: Manifest处理完成
    
    Note over Packer: 第三阶段：DEX合并
    Packer->>Dex: combineShellDexAndSrcApk()
    Dex->>Dex: 读取源APK并加密
    Dex->>Dex: 合并壳DEX和加密源APK
    Dex->>Dex: 修复DEX文件头
    Dex-->>Packer: DEX合并完成
    
    Note over Packer: 第四阶段：重打包签名
    Packer->>Tool: repackApk()
    Tool-->>Packer: 重打包完成
    Packer->>Sign: resignAndAlign()
    Sign-->>Packer: 签名对齐完成
    
    Packer-->>Main: 加壳完成
    Main-->>User: 返回加固APK
```

**PackerMain.java** - 程序入口

```
// 支持的命令行参数
//-src <PATH>     # 源APK文件路径
//-shell <PATH>   # 壳APK文件路径
//-o <PATH>       # 输出APK路径（可选）
//-h              # 帮助信息


package com.csh.packer;

import com.csh.packer.utils.PathsConfig;

import org.apache.commons.cli.*;

import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * 加壳程序主入口
 */
public class PackerMain {

    public static void main(String[] args) {
        Options options = createOptions();
        CommandLineParser parser = new DefaultParser();

        try {
            CommandLine cmd = parser.parse(options, args, true);

            if (cmd.hasOption("help") || !cmd.hasOption("src") || !cmd.hasOption("shell")) {
                printUsage(options);
                return;
            }

            // 获取必需参数
            Path srcApk = Paths.get(cmd.getOptionValue("src"));
            Path shellApk = Paths.get(cmd.getOptionValue("shell"));

            // 获取输出路径，如果没有指定则使用默认值
            Path outputApk;
            if (cmd.hasOption("out")) {
                outputApk = Paths.get(cmd.getOptionValue("out"));
            } else {
                String defaultName = srcApk.getFileName().toString();
                int dotIndex = defaultName.lastIndexOf('.');
                if (dotIndex > 0) {
                    defaultName = defaultName.substring(0, dotIndex) + "_protected.apk";
                } else {
                    defaultName = defaultName + "_protected.apk";
                }
                outputApk = Paths.get("./out").resolve(defaultName);
            }

            // 创建路径配置
            PathsConfig paths = new PathsConfig(srcApk, shellApk, outputApk);

            System.out.println("Source APK: " + paths.getSrcApkPath());
            System.out.println("Shell APK: " + paths.getShellApkPath());
            System.out.println("Output APK: " + paths.getNewApkPath());

            // 执行加壳
            ApkPacker packer = new ApkPacker(paths);
            packer.start();

        } catch (ParseException e) {
            System.err.println("参数解析错误: " + e.getMessage());
            printUsage(options);
        } catch (Exception e) {
            System.err.println("加壳失败: " + e.getMessage());
            e.printStackTrace();
        }
    }

    private static Options createOptions() {
        Options options = new Options();

        options.addOption(Option.builder("src").longOpt("src-apk").hasArg(true).argName("PATH").desc("源APK文件路径").build());

        options.addOption(Option.builder("shell").longOpt("shell-apk").hasArg(true).argName("PATH").desc("壳APK文件路径").build());

        options.addOption(Option.builder("o").longOpt("out").hasArg(true).argName("PATH").desc("输出APK路径 (默认: ./out/<src-apk>_protected.apk)").build());

        options.addOption(Option.builder("h").longOpt("help").desc("显示帮助信息").build());

        return options;
    }

    private static void printUsage(Options options) {
        HelpFormatter formatter = new HelpFormatter();
        formatter.printHelp(74,  // width
                "java -jar apk-packer.jar",  // cmdLineSyntax
                "Android APK Packer - APK加壳工具\n\n",  // header
                options,  // options
                "\n示例:\n" + "java -jar apk-packer.jar -src source.apk -shell shell.apk\n" + "java -jar apk-packer.jar -src source.apk -shell shell.apk -o output.apk\n",  // footer
                true  // autoUsage
        );
    }
}
```

为了方便本地调试，可以在AndroidStudio的工程使用Application的配置来进行本地debug运行，可以实现加壳程序的本地断点，如下图所示

![image.png](/images/Android第一代加固技术原理详解-附源码/01.png)

**ApkPacker.java** - 核心加壳逻辑

```
package com.csh.packer;


import com.csh.packer.apktool.ApkTool;
import com.csh.packer.dexUtils.DexProcessor;
import com.csh.packer.manifestUtils.ManifestEditor;
import com.csh.packer.sign.ApkSignAndAlignTool;
import com.csh.packer.utils.FileUtils;
import com.csh.packer.utils.PathsConfig;

import java.nio.file.Files;
import java.nio.file.Path;

/**
 * APK加壳程序主类
 * 负责将源程序APK和壳程序APK合并成加固后的APK
 */
public class ApkPacker {
    private final PathsConfig paths;

    public ApkPacker(PathsConfig paths) {
        this.paths = paths;
    }

    /**
     * 执行加壳操作
     */
    public void start() throws Exception {
        paths.cleanupTempDirectories();
        ApkTool apkTool = new ApkTool();
        ApkSignAndAlignTool apkSignerTool = new ApkSignAndAlignTool();

        try {
            // 1. 分别解包源文件和壳文件到临时目录
            System.out.println("Extracting source and shell apk...");
            apkTool.extractApk(paths.getSrcApkPath(), paths.getSrcApkTempDir());
            System.out.println("Extract source apk success!");

            System.out.println("Extracting shell apk...");
            apkTool.extractApk(paths.getShellApkPath(), paths.getShellApkTempDir());
            System.out.println("Extract shell apk success!");

            // 2. 复制源apk所有文件到新apk临时目录中
            System.out.println("Copying source apk files to new apk temp dir...");
            FileUtils.copyDirectory(paths.getSrcApkTempDir().toFile(), paths.getNewApkTempDir().toFile());
            System.out.println("Copy source apk files success!");

            // 3. 处理AndroidManifest.xml
            System.out.println("Handling AndroidManifest.xml...");
            handleManifest(paths.getSrcApkTempDir(), paths.getShellApkTempDir(), paths.getNewApkTempDir());
            System.out.println("Handle AndroidManifest.xml success!");

            // 4. 合并壳dex和源apk并导出文件
            System.out.println("Combining shell dex and source apk...");
            DexProcessor.combineShellDexAndSrcApk(paths.getSrcApkPath(), paths.getShellApkTempDir(), paths.getNewApkTempDir());
            System.out.println("Combine shell dex and source apk success!");
//
//            // 5. 确保native libraries正确复制
//            System.out.println("Handling native libraries...");
//            handleNativeLibraries(paths.getSrcApkTempDir(), paths.getNewApkTempDir());
//            System.out.println("Handle native libraries success!");

             //6. 重打包apk
            System.out.println("Repacking apk...");
            apkTool.repackApk(paths.getNewApkTempDir(), paths.getNewApkPath());
            System.out.println("Repack apk success!");

            // 7. 签名apk
            System.out.println("Signing apk...");
            apkSignerTool.setVerbose(true);  // 启用详细日志
            apkSignerTool.resignAndAlign(paths.getNewApkPath().toString(), paths.getNewApkSignPath().toString());
            System.out.println("Resign apk success!");

        } catch (Exception e) {
            System.err.println("加壳失败: " + e.getMessage());
            e.printStackTrace();
            throw e;
        } finally {
            // 8. 删除临时目录
            System.out.println("Deleting temp directories...");
            if (Files.exists(paths.getTmpDir())) {
//                paths.cleanupTempDirectories();
            }
            System.out.println("Delete temp directories success!");
        }
    }

    /**
     * 提取源apk的Manifest文件，修改application为壳application，输出新的Manifest文件
     */
    private void handleManifest(Path srcApkTempDir, Path shellApkTempDir, Path newApkTempDir) throws Exception {

        // 从源apk提取AndroidManifest.xml
        Path srcManifestPath = srcApkTempDir.resolve("AndroidManifest.xml");
        String srcManifestContent = Files.readString(srcManifestPath);
        ManifestEditor srcManifestEditor = new ManifestEditor(srcManifestContent);
        String srcApplication = srcManifestEditor.getApplication();

        // 从壳apk提取AndroidManifest.xml
        Path shellManifestPath = shellApkTempDir.resolve("AndroidManifest.xml");
        String shellManifestContent = Files.readString(shellManifestPath);
        ManifestEditor shellManifestEditor = new ManifestEditor(shellManifestContent);
        String shellApplication = shellManifestEditor.getApplication();
        System.out.println("ShellApplication: " + shellApplication);

        // 修改源AndroidManifest.xml的application为壳的代理application
        srcManifestEditor.setApplication(shellApplication);

        // 写入meta-data标签保存源apk的原始application
        if (srcApplication != null) {
            System.out.println("Source application: " + srcApplication);
            srcManifestEditor.addMetaData("APPLICATION_CLASS_NAME", srcApplication);
        }

        // 输出新的AndroidManifest.xml
        Path newManifestPath = newApkTempDir.resolve("AndroidManifest.xml");
        Files.writeString(newManifestPath, srcManifestEditor.getManifestData());
    }

    /**
     * 处理native libraries，确保它们被正确复制和对齐
     */
    private void handleNativeLibraries(Path srcApkTempDir, Path newApkTempDir) throws Exception {
        Path srcLibDir = srcApkTempDir.resolve("lib");
        Path destLibDir = newApkTempDir.resolve("lib");

        if (!Files.exists(srcLibDir)) {
            System.out.println("No native libraries found in source APK");
            return;
        }

        System.out.println("Processing native libraries...");

        // 确保目标lib目录存在
        Files.createDirectories(destLibDir);

        // 复制所有架构的native libraries
        Files.walk(srcLibDir).forEach(sourcePath -> {
            try {
                Path relativePath = srcLibDir.relativize(sourcePath);
                Path destPath = destLibDir.resolve(relativePath);

                if (Files.isDirectory(sourcePath)) {
                    Files.createDirectories(destPath);
                } else {
                    // 确保父目录存在
                    Files.createDirectories(destPath.getParent());
                    // 复制文件
                    Files.copy(sourcePath, destPath, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
                    System.out.println("Copied native library: " + relativePath);
                }
            } catch (Exception e) {
                System.err.println("Failed to copy native library: " + sourcePath + " - " + e.getMessage());
            }
        });

        System.out.println("Native libraries processing completed");
    }
}
```

##### 1.2.3 APKTool解包核心逻辑

**ApkToolWrapper.java** - APKTool包装器，关键在于保留DEX完整结构，不解析dex为smali代码，因为第一代操作的是dex整体文件，示例demo为了方便展示，限制了源程序仅打包构建出一个Dex文件，然后最后重新回编Apk时是用的源Apk的资源进行回编译。

```
public class ApkToolWrapper {
    private static final String APKTOOL_JAR_PATH = "tools/apktool_2.9.3.jar";

    /**
     * 解包APK的核心方法
     * @param apkPath APK文件路径
     * @param outputDir 输出目录
     * @param decodeClasses 是否解包DEX为smali代码
     */
    public void decodeApkWithCommand(Path apkPath, Path outputDir, boolean decodeClasses) throws Exception {
        // 构建apktool命令
        List<String> command = new ArrayList<>();
        command.add("java");
        command.add("-jar");
        command.add(APKTOOL_JAR_PATH);

        // 关键：根据decodeClasses参数决定是否使用-s选项
        if (!decodeClasses) {
            command.add("-s");  // 精简解包,只解包资源文件，不解包DEX
        }

        command.add("d");  // decode操作
        command.add(apkPath.toString());
        command.add("-o");
        command.add(outputDir.toString());
        command.add("-f");  // 强制覆盖已存在的目录

        // 执行命令
        executeCommand(command, apkPath, outputDir);
    }

    /**
     * 仅解包资源文件，不解包DEX（关键方法）
     * 这样保留了DEX文件的完整二进制结构，避免smali转换
     */
    public void extractApk(Path apkPath, Path outputDir) throws Exception {
        decodeApkWithCommand(apkPath, outputDir, false);  // false = 不解包DEX
    }

    /**
     * 重新打包APK
     */
    public void repackApk(Path inputDir, Path outputApk) throws Exception {
        buildApkWithCommand(inputDir, outputApk, false, false);
    }

    /**
     * 执行apktool命令的核心方法
     */
    private void executeCommand(List<String> command, Path apkPath, Path outputDir) throws Exception {
        ProcessBuilder processBuilder = new ProcessBuilder(command);
        processBuilder.redirectErrorStream(true);
        
        Process process = processBuilder.start();
        
        // 读取输出用于调试
        StringBuilder output = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
            String line;
            while ((line = reader.readLine()) != null) {
                output.append(line).append("\n");
            }
        }
        
        // 等待进程完成（设置60秒超时）
        boolean finished = process.waitFor(60, TimeUnit.SECONDS);
        if (!finished) {
            process.destroyForcibly();
            throw new Exception("apktool命令执行超时（60秒）");
        }
        
        // 检查退出码
        int exitCode = process.exitValue();
        if (exitCode != 0) {
            throw new Exception("apktool执行失败，退出码: " + exitCode + "\n输出: " + output.toString());
        }
    }
}
```

**ApkTool.java** - 高级封装接口

```
public class ApkTool {
    private final ApkToolWrapper wrapper;

    public ApkTool() {
        this.wrapper = new ApkToolWrapper();
    }

    /**
     * 使用apktool解包APK，只解包资源不解包dex
     * 这是加壳工具的关键：保持DEX文件的完整二进制格式
     */
    public void extractApk(Path apkPath, Path outputDir) throws Exception {
        wrapper.extractApk(apkPath, outputDir);
    }

    /**
     * 重新打包APK
     */
    public void repackApk(Path inputDir, Path outApk) throws Exception {
        wrapper.repackApk(inputDir, outApk);
    }
}
```

**解包策略说明：**

1. **使用-s参数**：apktool的-s（skip）参数跳过DEX到smali的转换
2. **保留DEX结构**：DEX文件以原始二进制格式保存在解包目录中
3. **仅解析资源**：AndroidManifest.xml、资源文件等被正常解析为可编辑格式
4. **避免重编译**：由于DEX未被转换，重打包时无需重新编译smali代码

##### 1.2.4 DEX文件处理核心算法

**DexProcessor.java** - DEX合并和加密

```
public class DexProcessor {
    
    /**
     * 合并壳DEX和源APK
     * 核心算法：将加密的源APK附加到壳DEX文件末尾
     */
    public static void combineShellDexAndSrcApk(Path sourceApkPath, Path shellApkTempDir, Path newApkTempDir)
            throws IOException, NoSuchAlgorithmException {

        // 读取源APK文件
        byte[] sourceApkArray = Files.readAllBytes(sourceApkPath);
        
        // 读取壳DEX文件
        Path shellDexPath = shellApkTempDir.resolve("classes.dex");
        byte[] shellDexArray = Files.readAllBytes(shellDexPath);
        
        int sourceApkLen = sourceApkArray.length;
        int shellDexLen = shellDexArray.length;
        
        // 计算新DEX文件长度：壳DEX + 加密源APK + 4字节长度标识
        int newDexLen = shellDexLen + sourceApkLen + 4;
        
        // 加密源APK文件（简单XOR加密）
        byte[] encryptedApkArray = encrypt(sourceApkArray);
        
        // 创建新DEX文件内容
        byte[] newDexArray = new byte[newDexLen];
        
        // 复制壳DEX
        System.arraycopy(shellDexArray, 0, newDexArray, 0, shellDexLen);
        
        // 复制加密的源APK
        System.arraycopy(encryptedApkArray, 0, newDexArray, shellDexLen, sourceApkLen);
        
        // 添加源APK长度标识（小端存储）
        int lengthOffset = shellDexLen + sourceApkLen;
        newDexArray[lengthOffset] = (byte) (sourceApkLen & 0xFF);
        newDexArray[lengthOffset + 1] = (byte) ((sourceApkLen >> 8) & 0xFF);
        newDexArray[lengthOffset + 2] = (byte) ((sourceApkLen >> 16) & 0xFF);
        newDexArray[lengthOffset + 3] = (byte) ((sourceApkLen >> 24) & 0xFF);
        
        // 修复DEX文件头
        fixDexHeader(newDexArray);
        
        // 写入新的DEX文件
        Path newDexPath = newApkTempDir.resolve("classes.dex");
        Files.write(newDexPath, newDexArray);
        
        System.out.println("DEX合并完成: " + newDexPath);
        System.out.println("原始DEX大小: " + shellDexLen + " bytes");
        System.out.println("源APK大小: " + sourceApkLen + " bytes");
        System.out.println("新DEX大小: " + newDexLen + " bytes");
    }
    
    /**
     * 简单XOR加密算法
     */
    private static byte[] encrypt(byte[] data) {
        byte[] encrypted = new byte[data.length];
        byte key = (byte) 0x88; // 简单的XOR密钥
        
        for (int i = 0; i < data.length; i++) {
            encrypted[i] = (byte) (data[i] ^ key);
        }
        
        return encrypted;
    }
    
    /**
     * 修复DEX文件头信息
     * 更新文件大小、校验和等关键字段
     */
    private static void fixDexHeader(byte[] dexArray) throws NoSuchAlgorithmException {
        // 修复文件大小（偏移量4-7，小端存储）
        int fileSize = dexArray.length;
        dexArray[32] = (byte) (fileSize & 0xFF);
        dexArray[33] = (byte) ((fileSize >> 8) & 0xFF);
        dexArray[34] = (byte) ((fileSize >> 16) & 0xFF);
        dexArray[35] = (byte) ((fileSize >> 24) & 0xFF);
        
        // 计算并更新SHA-1签名（偏移量12-31）
        MessageDigest sha1 = MessageDigest.getInstance("SHA-1");
        sha1.update(dexArray, 32, dexArray.length - 32);
        byte[] signature = sha1.digest();
        System.arraycopy(signature, 0, dexArray, 12, 20);
        
        // 计算并更新Adler32校验和（偏移量8-11）
        Adler32 adler32 = new Adler32();
        adler32.update(dexArray, 12, dexArray.length - 12);
        int checksum = (int) adler32.getValue();
        dexArray[8] = (byte) (checksum & 0xFF);
        dexArray[9] = (byte) ((checksum >> 8) & 0xFF);
        dexArray[10] = (byte) ((checksum >> 16) & 0xFF);
        dexArray[11] = (byte) ((checksum >> 24) & 0xFF);
        
        System.out.println("DEX文件头修复完成");
        System.out.println("文件大小: " + fileSize + " bytes");
        System.out.println("校验和: 0x" + Integer.toHexString(checksum));
    }
}
```

##### 1.2.5 AndroidManifest.xml处理

**ManifestEditor.java** - 清单文件编辑器，这是加壳过程中最关键的组件之一，负责实现Application替换的核心逻辑。

**核心功能概述：**

1. **解析AndroidManifest.xml**：使用DOM4J解析XML文件
2. **提取源Application**：获取原始应用的Application类名
3. **替换为壳Application**：将入口Application改为壳程序的代理Application
4. **保存原始信息**：通过meta-data标签保存原始Application类名，供运行时恢复使用

```
package com.csh.packer.manifestUtils;

import org.dom4j.Document;
import org.dom4j.Element;
import org.dom4j.Namespace;
import org.dom4j.QName;
import org.dom4j.io.OutputFormat;
import org.dom4j.io.SAXReader;
import org.dom4j.io.XMLWriter;

import java.io.ByteArrayInputStream;
import java.io.StringWriter;
import java.util.Map;
import java.util.HashMap;

/**
 * AndroidManifest.xml的编辑器，用于获取和修改标签属性，以及添加标签
 * 核心作用：实现Application入口的替换和原始信息的保存
 */
public class ManifestEditor {
    // Android命名空间定义
    private static final String ANDROID_NS_URI = "http://schemas.android.com/apk/res/android";
    private static final Namespace ANDROID_NS = Namespace.get("android", ANDROID_NS_URI);
    
    private final Document document;

    /**
     * 构造函数：解析AndroidManifest.xml内容
     * @param xmlContent XML文件内容（字节数组或字符串）
     */
    public ManifestEditor(byte[] xmlContent) throws Exception {
        SAXReader reader = new SAXReader();
        this.document = reader.read(new ByteArrayInputStream(xmlContent));
    }
    
    public ManifestEditor(String xmlContent) throws Exception {
        this(xmlContent.getBytes("UTF-8"));
    }

    /**
     * 获取指定标签的android属性值
     * @param tagName 标签名称（如"application"、"manifest"）
     * @param attrName 属性名称（如"name"、"package"）
     * @return 属性值，如果不存在返回null
     */
    public String getTagAttribute(String tagName, String attrName) {
        if ("manifest".equals(tagName)) {
            // manifest根标签特殊处理（不在android命名空间下）
            Element rootElement = document.getRootElement();
            return rootElement.attributeValue(attrName);
        } else {
            // 其他标签在android命名空间下
            Element element = (Element) document.selectSingleNode("//" + tagName);
            if (element != null) {
                QName qname = new QName(attrName, ANDROID_NS);
                return element.attributeValue(qname);
            }
        }
        return null;
    }

    /**
     * 设置指定标签的属性值
     * @param tagName 标签名称
     * @param attrName 属性名称
     * @param newValue 新属性值
     * @return 是否设置成功
     */
    public boolean setTagAttribute(String tagName, String attrName, String newValue) {
        if ("manifest".equals(tagName)) {
            Element rootElement = document.getRootElement();
            rootElement.addAttribute(attrName, newValue);
            return true;
        } else {
            Element element = (Element) document.selectSingleNode("//" + tagName);
            if (element != null) {
                QName qname = new QName(attrName, ANDROID_NS);
                element.addAttribute(qname, newValue);
                return true;
            }
        }
        return false;
    }

    /**
     * 添加子标签及其属性
     * @param parentTagName 父标签名称
     * @param childTagName 子标签名称
     * @param attributes 属性映射
     */
    public void addTagWithAttributes(String parentTagName, String childTagName, Map<String, String> attributes) {
        Element parentElement = (Element) document.selectSingleNode("//" + parentTagName);
        if (parentElement != null) {
            Element childElement = parentElement.addElement(childTagName);
            for (Map.Entry<String, String> entry : attributes.entrySet()) {
                QName qname = new QName(entry.getKey(), ANDROID_NS);
                childElement.addAttribute(qname, entry.getValue());
            }
        }
    }

    /**
     * 获取Application类名（核心方法）
     * @return 原始Application类名，如果没有自定义Application返回null
     */
    public String getApplication() {
        return getTagAttribute("application", "name");
    }
    
    /**
     * 设置Application类名（核心方法）
     * 将原始Application替换为壳程序的代理Application
     * @param application 壳Application类名（如".ShellProxyApplicationV1"）
     */
    public void setApplication(String application) {
        setTagAttribute("application", "name", application);
    }

    /**
     * 添加meta-data标签（核心方法）
     * 用于保存原始Application类名，供运行时恢复使用
     * @param name meta-data的name属性
     * @param value meta-data的value属性
     */
    public void addMetaData(String name, String value) {
        Map<String, String> attrs = new HashMap<>();
        attrs.put("name", name);
        attrs.put("value", value);
        addTagWithAttributes("application", "meta-data", attrs);
    }

    /**
     * 获取修改后的manifest数据的XML字符串形式
     * @return 格式化的XML字符串
     */
    public String getManifestData() throws Exception {
        OutputFormat format = OutputFormat.createPrettyPrint();
        format.setEncoding("UTF-8");
        format.setIndent(true);
        format.setIndentSize(2);
        
        StringWriter stringWriter = new StringWriter();
        XMLWriter xmlWriter = new XMLWriter(stringWriter, format);
        xmlWriter.write(document);
        xmlWriter.close();
        
        return stringWriter.toString();
    }
}
```

**AndroidManifest.xml处理流程详解：**

**1. 处理前的文件状态**

```
<!-- 源程序的AndroidManifest.xml -->
<application android:name=".SourceApplication">
    <activity android:name=".MainActivity">
        <!-- 活动配置 -->
    </activity>
</application>

<!-- 壳程序的AndroidManifest.xml -->
<application android:name=".ShellProxyApplicationV1">
    <!-- 壳程序配置 -->
</application>
```

**2. 加壳工具的Application处理逻辑**

```
// ApkPacker.java中的handleManifest方法
private void handleManifest(Path srcApkTempDir, Path shellApkTempDir, Path newApkTempDir) throws Exception {
    // 1. 读取源程序的AndroidManifest.xml
    Path srcManifestPath = srcApkTempDir.resolve("AndroidManifest.xml");
    String srcManifestContent = Files.readString(srcManifestPath);
    ManifestEditor srcManifestEditor = new ManifestEditor(srcManifestContent);
    
    // 2. 提取源程序的Application类名
    String srcApplication = srcManifestEditor.getApplication();
    // 结果：".SourceApplication"
    
    // 3. 读取壳程序的AndroidManifest.xml
    Path shellManifestPath = shellApkTempDir.resolve("AndroidManifest.xml");
    String shellManifestContent = Files.readString(shellManifestPath);
    ManifestEditor shellManifestEditor = new ManifestEditor(shellManifestContent);
    
    // 4. 提取壳程序的Application类名
    String shellApplication = shellManifestEditor.getApplication();
    // 结果：".ShellProxyApplicationV1"
    
    // 5. 关键步骤：替换源程序的Application为壳Application
    srcManifestEditor.setApplication(shellApplication);
    
    // 6. 关键步骤：保存原始Application信息到meta-data
    if (srcApplication != null) {
        srcManifestEditor.addMetaData("APPLICATION_CLASS_NAME", srcApplication);
    }
    
    // 7. 输出修改后的AndroidManifest.xml
    Path newManifestPath = newApkTempDir.resolve("AndroidManifest.xml");
    Files.writeString(newManifestPath, srcManifestEditor.getManifestData());
}
```

**3. 处理后的文件状态**

```
<!-- 加壳后的AndroidManifest.xml -->
<application android:name=".ShellProxyApplicationV1">
    <!-- 保存原始Application信息 -->
    <meta-data 
        android:name="APPLICATION_CLASS_NAME" 
        android:value=".SourceApplication" />
    
    <!-- 保留源程序的所有Activity配置 -->
    <activity android:name=".MainActivity">
        <!-- 活动配置 -->
    </activity>
</application>
```

**4. 运行时恢复机制**

当加壳后的APK运行时，Android系统会：

1. **启动壳Application**：系统读取AndroidManifest.xml，创建ShellProxyApplicationV1实例
2. **壳程序获取原始信息**：通过PackageManager读取meta-data，获取原始Application类名
3. **动态替换**：壳程序解密源APK，替换ClassLoader，创建原始Application实例
4. **透明运行**：用户看到的是原始应用的界面和功能

```
// ShellProxyApplicationV1.java中的恢复逻辑
public boolean replaceApplication() {
    String appClassName = null;
    try {
        // 从meta-data中读取原始Application类名
        ApplicationInfo applicationInfo = getPackageManager()
            .getApplicationInfo(this.getPackageName(), PackageManager.GET_META_DATA);
        Bundle metaData = applicationInfo.metaData;
        
        if (metaData != null && metaData.containsKey("APPLICATION_CLASS_NAME")) {
            appClassName = metaData.getString("APPLICATION_CLASS_NAME");
            // 结果：".SourceApplication"
        }
    } catch (PackageManager.NameNotFoundException e) {
        // 处理异常
    }
    
    // 使用反射创建原始Application实例并替换系统引用
    // ...
}
```

**技术要点总结：**

1. **XML命名空间处理**：正确处理android命名空间，确保属性设置有效
2. **DOM操作**：使用DOM4J进行XML解析和修改，保持文档结构完整
3. **信息传递机制**：通过meta-data标签实现编译时到运行时的信息传递
4. **透明替换**：用户和系统都感知不到Application的替换过程
5. **兼容性保证**：保留原始应用的所有配置信息（Activity、Service、权限等）

##### 1.2.6 APK签名工具

**ApkSignAndAlignTool.java** - APK签名和对齐

```
public class ApkSignAndAlignTool {
    private boolean verbose = false;
    
    public void setVerbose(boolean verbose) {
        this.verbose = verbose;
    }
    
    /**
     * 重新签名并对齐APK
     */
    public void resignAndAlign(String inputApkPath, String outputApkPath) throws Exception {
        // 1. 创建签名配置
        ApkSigner.SignerConfig signerConfig = createSignerConfig();
        
        // 2. 配置APK签名器
        ApkSigner.Builder signerBuilder = new ApkSigner.Builder(Arrays.asList(signerConfig))
                .setInputApk(new File(inputApkPath))
                .setOutputApk(new File(outputApkPath))
                .setOtherSignersSignaturesPreserved(false)
                .setV1SigningEnabled(true)
                .setV2SigningEnabled(true)
                .setV3SigningEnabled(false)
                .setV4SigningEnabled(false)
                .setVerityEnabled(false)
                .setDebuggableApkPermitted(true)
                .setMinSdkVersion(21);
        
        if (verbose) {
            System.out.println("开始签名APK: " + inputApkPath);
        }
        
        // 3. 执行签名
        ApkSigner signer = signerBuilder.build();
        signer.sign();
        
        if (verbose) {
            System.out.println("APK签名完成: " + outputApkPath);
        }
    }
    
    /**
     * 创建默认签名配置（使用内置测试证书）
     */
    private ApkSigner.SignerConfig createSignerConfig() throws Exception {
        // 使用Android SDK默认的debug证书
        PrivateKey privateKey = loadPrivateKey();
        X509Certificate certificate = loadCertificate();
        
        return new ApkSigner.SignerConfig.Builder(
                "CERT", privateKey, Arrays.asList(certificate))
                .build();
    }
    
    private PrivateKey loadPrivateKey() throws Exception {
        // 实现私钥加载逻辑
        // 这里使用内置的测试私钥
        return TestKeyProvider.getPrivateKey();
    }
    
    private X509Certificate loadCertificate() throws Exception {
        // 实现证书加载逻辑
        // 这里使用内置的测试证书
        return TestKeyProvider.getCertificate();
    }
}
```

##### 1.2.7 文件工具类

**FileUtils.java** - 文件操作工具

```
public class FileUtils {
    
    /**
     * 递归复制目录
     */
    public static void copyDirectory(File sourceDir, File destDir) throws IOException {
        if (!destDir.exists()) {
            destDir.mkdirs();
        }
        
        File[] files = sourceDir.listFiles();
        if (files != null) {
            for (File file : files) {
                File destFile = new File(destDir, file.getName());
                
                if (file.isDirectory()) {
                    copyDirectory(file, destFile);
                } else {
                    copyFile(file, destFile);
                }
            }
        }
    }
    
    /**
     * 复制单个文件
     */
    public static void copyFile(File source, File dest) throws IOException {
        try (FileInputStream fis = new FileInputStream(source);
             FileOutputStream fos = new FileOutputStream(dest)) {
            
            byte[] buffer = new byte[8192];
            int bytesRead;
            while ((bytesRead = fis.read(buffer)) != -1) {
                fos.write(buffer, 0, bytesRead);
            }
        }
    }
    
    /**
     * 递归删除目录
     */
    public static void deleteDirectory(File directory) throws IOException {
        if (directory.exists()) {
            File[] files = directory.listFiles();
            if (files != null) {
                for (File file : files) {
                    if (file.isDirectory()) {
                        deleteDirectory(file);
                    } else {
                        file.delete();
                    }
                }
            }
            directory.delete();
        }
    }
}
```

##### 1.2.8 路径配置管理

**PathsConfig.java** - 路径配置类

```
public class PathsConfig {
    private final Path srcApkPath;
    private final Path shellApkPath;
    private final Path newApkPath;
    private final Path newApkSignPath;
    private final Path tmpDir;
    private final Path srcApkTempDir;
    private final Path shellApkTempDir;
    private final Path newApkTempDir;
    
    public PathsConfig(Path srcApkPath, Path shellApkPath, Path outputApkPath) {
        this.srcApkPath = srcApkPath;
        this.shellApkPath = shellApkPath;
        this.newApkPath = outputApkPath;
        this.newApkSignPath = Paths.get(outputApkPath.toString().replace(".apk", "_signed.apk"));
        
        // 创建临时目录结构
        this.tmpDir = Paths.get("tmp");
        this.srcApkTempDir = tmpDir.resolve("src_apk");
        this.shellApkTempDir = tmpDir.resolve("shell_apk");
        this.newApkTempDir = tmpDir.resolve("new_apk");
    }
    
    /**
     * 清理临时目录
     */
    public void cleanupTempDirectories() throws IOException {
        if (Files.exists(tmpDir)) {
            FileUtils.deleteDirectory(tmpDir.toFile());
        }
        
        // 重新创建临时目录
        Files.createDirectories(srcApkTempDir);
        Files.createDirectories(shellApkTempDir);
        Files.createDirectories(newApkTempDir);
    }
    
    // Getter方法
    public Path getSrcApkPath() { return srcApkPath; }
    public Path getShellApkPath() { return shellApkPath; }
    public Path getNewApkPath() { return newApkPath; }
    public Path getNewApkSignPath() { return newApkSignPath; }
    public Path getTmpDir() { return tmpDir; }
    public Path getSrcApkTempDir() { return srcApkTempDir; }
    public Path getShellApkTempDir() { return shellApkTempDir; }
    public Path getNewApkTempDir() { return newApkTempDir; }
}
```

#### 1.3 关键技术点

1. **DEX文件格式**: 深入理解DEX文件结构，正确处理文件头、校验和
2. **APK结构**: 熟悉APK文件组成，正确处理资源、清单文件、签名
3. **加密算法**: 实现源APK的加密保护，防止静态分析
4. **文件操作**: 高效的文件读写、复制、删除操作
5. **XML处理**: 使用DOM4J处理AndroidManifest.xml文件
6. **APK签名**: 使用apksig库进行APK的重新签名和对齐
7. **APK解包**:仅解包资源，不解包dex, 这个至关重要

---

### 模块二：Shell-App 壳程序模块（业内也叫脱壳流程）

#### 2.1 模块架构

```
shell-app/
├── build.gradle.kts              # Android应用构建配置
├── src/main/
│   ├── AndroidManifest.xml        # 壳程序清单文件
│   └── java/com/csh/shell/
│       ├── ShellProxyApplicationV1.java  # 壳代理Application（传统版本）
│       ├── ShellProxyApplicationV2.java  # 壳代理Application（兼容版本）
│       ├── LoadedApkReflectionHelper.java # LoadedApk反射辅助类
│       └── Reflection.java               # 反射工具类
└── release/
    └── shell-app-release.apk      # 编译后的壳APK
```

```
classDiagram
    class ShellProxyApplicationV1 {
        -String apkPath
        -String dexPath  
        -String libPath
        +attachBaseContext() void
        +onCreate() void
        -readDexFromApk() byte[]
        -extractSrcApkFromShellDex() void
        -replaceClassLoader() void
        -replaceApplication() boolean
    }
    
    class ShellProxyApplicationV2 {
        -String mApplicationName
        -Application mSourceApplication
        +attachBaseContext() void
        +onCreate() void
        -extractSourceApk() boolean
        -replaceClassLoader() boolean
        -replaceApplicationInSystem() void
    }
    
    class Reflection {
        +getStaticField() Object
        +setField() void
        +invokeMethod() Object
    }
    
    ShellProxyApplicationV1 --> Reflection
    ShellProxyApplicationV2 --> Reflection
```

#### 2.2 运行时流程

```
sequenceDiagram
    participant System as Android系统
    participant Shell as 壳程序
    participant Reflect as 反射工具
    participant Source as 源程序
    participant ActivityThread as ActivityThread
    participant LoadedApk as LoadedApk
    
    System->>Shell: 启动加固APK
    Shell->>Shell: attachBaseContext()
    
    Note over Shell: 第一阶段：解密源程序
    Shell->>Shell: getDir("tmp_dex", MODE_PRIVATE)
    Shell->>Shell: 创建私有目录 /data/data/pkg/app_tmp_dex
    Shell->>Shell: readDexFromApk()
    Shell->>Shell: 从APK中读取classes.dex
    Shell->>Shell: extractSrcApkFromShellDex()
    Shell->>Shell: 解析DEX文件结构
    Shell->>Shell: 读取末尾4字节获取源APK大小
    Shell->>Shell: 提取加密的源APK数据
    Shell->>Shell: decrypt() - XOR 0xFF解密
    Shell->>Shell: 写入Source.apk文件
    Shell->>Shell: 提取native库文件到lib目录
    
    Note over Shell: 第二阶段：ClassLoader替换
    Shell->>Shell: replaceClassLoader()
    Shell->>Reflect: getStaticField("android.app.ActivityThread", "sCurrentActivityThread")
    Reflect-->>Shell: ActivityThread实例
    Shell->>Reflect: getField("android.app.ActivityThread", activityThread, "mPackages")
    Reflect-->>Shell: ArrayMap<String, WeakReference<LoadedApk>>
    Shell->>Shell: 通过包名获取LoadedApk的WeakReference
    Shell->>Shell: 从WeakReference获取LoadedApk实例
    Shell->>Shell: new DexClassLoader(apkPath, dexPath, libPath, parent)
    Shell->>Reflect: setField("android.app.LoadedApk", "mClassLoader", loadedApk, dexClassLoader)
    Reflect-->>Shell: ClassLoader替换完成
    
    System->>Shell: onCreate()
    
    Note over Shell: 第三阶段：Application替换
    Shell->>Shell: replaceApplication()
    Shell->>Shell: 从meta-data获取源Application类名
    Shell->>Shell: 通过新ClassLoader加载源Application类
    Shell->>Source: 创建源Application实例
    
    Shell->>Reflect: 获取ActivityThread.mBoundApplication
    Shell->>Reflect: 获取LoadedApk实例
    Shell->>Reflect: setField("android.app.LoadedApk", "mApplication", loadedApk, null)
    
    Shell->>Reflect: getField("android.app.ActivityThread", activityThread, "mInitialApplication")
    Shell->>Reflect: getField("android.app.ActivityThread", activityThread, "mAllApplications")
    Shell->>Shell: 从mAllApplications中移除旧Application
    
    Shell->>Shell: 更新ApplicationInfo.className为源Application类名
    Shell->>Reflect: invokeMethod("android.app.LoadedApk", "makeApplication", loadedApk, ...)
    Reflect->>Source: 创建源Application实例
    Source-->>Reflect: 新Application实例
    Reflect-->>Shell: 源Application创建完成
    
    Shell->>Reflect: setField("android.app.ActivityThread", "mInitialApplication", activityThread, sourceApp)
    Shell->>Shell: 处理ContentProvider引用
    Shell->>Source: sourceApplication.onCreate()
    Source->>Source: 执行源程序初始化逻辑
    Source-->>Shell: 源程序启动完成
    
    Shell-->>System: 加固程序运行成功
```

#### 2.3 版本对比分析

##### 2.3.1 V1与V2版本概述

**ShellProxyApplicationV1** - 传统实现方案

- 适用于Android 5.0 - Android 12
- 使用`LoadedApk.makeApplication()`创建源Application
- 依赖反射调用系统内部方法
- 实现相对简单，但在高版本Android中受限

**ShellProxyApplicationV2** - 兼容性增强方案

- 适用于Android 5.0+，特别优化Android 13+
- 使用直接实例化方式创建源Application
- 更完善的系统引用替换机制
- 增强的错误处理和兼容性检查
- **当前推荐使用的版本**

##### 2.3.2 构建配置特点（两版本共同）

```
android {
    defaultConfig {
        multiDexEnabled = false  // 强制单DEX，确保只生成一个classes.dex
    }
    
    signingConfigs {
        create("release") {
            // 使用项目统一的签名配置
            storeFile = file("${project.rootDir}/JKS/AppShield")
        }
    }
}
```

#### 2.4 共同实现流程

##### 2.4.1 阶段1: attachBaseContext() - 环境准备（两版本相同）

```
@Override
protected void attachBaseContext(Context base) {
    super.attachBaseContext(base);
    
    // 1. 创建私有目录保存解密文件
    File dex = getDir("tmp_dex", MODE_PRIVATE);
    File lib = getDir("tmp_lib", MODE_PRIVATE);
    dexPath = dex.getAbsolutePath();
    libPath = lib.getAbsolutePath();
    apkPath = dex.getAbsolutePath() + File.separator + "Source.apk";
    
    // 2. 首次运行时解密源APK
    File apkFile = new File(apkPath);
    if (!apkFile.exists()) {
        byte[] shellDexData = readDexFromApk();  // 读取当前APK的classes.dex
        extractSrcApkFromShellDex(shellDexData); // 从DEX末尾提取加密的源APK
    }
    
    // 3. 替换ClassLoader
    replaceClassLoader();
}
```

##### 2.4.2 阶段2: 源APK解密和提取（两版本相同）

```
private void extractSrcApkFromShellDex(byte[] shellDexData) throws IOException {
    int shellDexLen = shellDexData.length;
    
    // 1. 读取源APK大小（DEX末尾4字节，小端存储）
    byte[] srcApkSizeBytes = new byte[4];
    System.arraycopy(shellDexData, shellDexLen - 4, srcApkSizeBytes, 0, 4);
    int srcApkSize = ByteBuffer.wrap(srcApkSizeBytes).order(ByteOrder.LITTLE_ENDIAN).getInt();
    
    // 2. 提取加密的源APK数据
    byte[] sourceApkData = new byte[srcApkSize];
    System.arraycopy(shellDexData, shellDexLen - srcApkSize - 4, sourceApkData, 0, srcApkSize);
    
    // 3. 解密源APK（异或0xFF）
    sourceApkData = decrypt(sourceApkData);
    
    // 4. 保存解密后的源APK到私有目录
    File apkfile = new File(apkPath);
    FileOutputStream apkfileOutputStream = new FileOutputStream(apkfile);
    apkfileOutputStream.write(sourceApkData);
    apkfileOutputStream.close();
    
    // 5. 提取源APK中的SO库文件到libPath目录
    extractNativeLibraries(apkfile);
}

/**
 * 简单的异或解密
 */
private byte[] decrypt(byte[] data) {
    for (int i = 0; i < data.length; i++) {
        data[i] = (byte) (data[i] ^ 0xFF);
    }
    return data;
}
```

##### 2.4.3 阶段3: ClassLoader替换（两版本相同）

```
private void replaceClassLoader() {
    // 1. 获取当前的ClassLoader
    ClassLoader classLoader = this.getClassLoader();
    
    // 2. 获取当前ActivityThread实例
    Object sCurrentActivityThreadObj = Reflection.getStaticField("android.app.ActivityThread", "sCurrentActivityThread");
    
    // 3. 获取当前应用的LoadedApk对象
    ArrayMap mPackagesObj = (ArrayMap) Reflection.getField("android.app.ActivityThread", sCurrentActivityThreadObj, "mPackages");
    String currentPackageName = this.getPackageName();
    WeakReference weakReference = (WeakReference) mPackagesObj.get(currentPackageName);
    Object loadedApkObj = weakReference.get();
    
    // 4. 创建新的DexClassLoader加载源APK
    DexClassLoader dexClassLoader = new DexClassLoader(apkPath, dexPath, libPath, classLoader.getParent());
    
    // 5. 替换LoadedApk的mClassLoader
    Reflection.setField("android.app.LoadedApk", "mClassLoader", loadedApkObj, dexClassLoader);
}
```

#### 2.5 核心差异对比：Application创建与替换

##### 2.5.1 V1版本：反射调用系统的makeApplication()方法

**V1版本的核心特点：依赖系统makeApplication()方法**

```
public boolean replaceApplication() {
    // 1. 获取源程序的Application类名
    String appClassName = getSourceApplicationName();
    if (appClassName == null) {
        log("源程序中没有自定义Application");
        return false;
    }
    
    // 2. 获取ActivityThread和LoadedApk实例
    Object sCurrentActivityThreadObj = Reflection.getStaticField(
        "android.app.ActivityThread", "sCurrentActivityThread");
    Object infoObj = getLoadedApk(sCurrentActivityThreadObj);
    
    // 3. 重置LoadedApk的mApplication为null（关键步骤）
    Reflection.setField("android.app.LoadedApk", "mApplication", infoObj, null);
    
    // 4. 从ActivityThread移除旧的Application
    Object mInitialApplicationObj = Reflection.getField(
        "android.app.ActivityThread", sCurrentActivityThreadObj, "mInitialApplication");
    ArrayList<Application> mAllApplicationsObj = (ArrayList<Application>) 
        Reflection.getField("android.app.ActivityThread", sCurrentActivityThreadObj, "mAllApplications");
    mAllApplicationsObj.remove(mInitialApplicationObj);
    
    // 5. 设置新的Application类名到ApplicationInfo
    ApplicationInfo applicationInfo = (ApplicationInfo) Reflection.getField(
        "android.app.LoadedApk", infoObj, "mApplicationInfo");
    ApplicationInfo appinfoInAppBindData = (ApplicationInfo) Reflection.getField(
        "android.app.ActivityThread$AppBindData", mBoundApplicationObj, "appInfo");
    applicationInfo.className = appClassName;
    appinfoInAppBindData.className = appClassName;
    
    // 6. 【关键差异】调用系统的makeApplication方法创建Application
    Application application = (Application) Reflection.invokeMethod(
        "android.app.LoadedApk", "makeApplication", infoObj, 
        new Class[]{boolean.class, Instrumentation.class}, 
        new Object[]{false, null});
    
    // 7. 重置ActivityThread的mInitialApplication
    Reflection.setField("android.app.ActivityThread", "mInitialApplication", 
        sCurrentActivityThreadObj, application);
    
    // 8. 处理ContentProvider的Application引用
    updateContentProviderReferences(sCurrentActivityThreadObj, application);
    
    // 9. 调用源程序Application的onCreate
    application.onCreate();
    
    return true;
}
```

**V1版本优势：**

- 使用系统标准的Application创建流程
- 自动处理Application的生命周期
- 代码相对简洁

**V1版本劣势：**

- Android 13+增加了makeApplication创建Application的校验，sApplications存储者一个包名对应初始化过的Application，而这个sApplications常识过反射获取不到，修改不了

![image.png](/images/Android第一代加固技术原理详解-附源码/02.png)

- 依赖系统内部实现，兼容性风险较高
- 错误处理相对简单

##### 2.5.2 V2版本：直接使用反射实例化Application方式

**V2版本的核心特点：绕过makeApplication限制**

```
@Override
protected void attachBaseContext(Context base) {
    super.attachBaseContext(base);
    
    try {
        // 1-3. 前三个阶段与V1相同
        extractSrcApkFromShellDex();
        replaceClassLoader();
        mApplicationName = getSourceApplicationName();
        
        // 4. 【关键差异】直接创建源Application实例
        mSourceApplication = makeSourceApplication();
        if (mSourceApplication == null) {
            log("Failed to create source application instance");
            return;
        }
        
        // 5. 【关键差异】手动替换系统中的Application引用
        replaceApplicationInSystem(this, mSourceApplication);
        
        // 6. 【关键差异】手动调用源Application的attachBaseContext
        invokeSourceApplicationAttach(mSourceApplication, base);
        
    } catch (Throwable e) {
        log("Error in attachBaseContext: " + Log.getStackTraceString(e));
    }
}

/**
 * 【关键差异】直接实例化源Application，不依赖系统makeApplication
 */
private Application makeSourceApplication() {
    try {
        ClassLoader classLoader = getClassLoader();
        Class<?> sourceAppClass = classLoader.loadClass(mApplicationName);
        Application application = (Application) sourceAppClass.newInstance();
        log("Successfully created source application: " + application.getClass().getName());
        return application;
    } catch (Throwable e) {
        log("Error creating source application: " + Log.getStackTraceString(e));
        return null;
    }
}

/**
 * 【关键差异】手动替换系统中的所有Application引用
 */
private void replaceApplicationInSystem(Application shellApp, Application sourceApp) throws Exception {
    // 1. 替换ContextImpl中LoadedApk的mApplication
    Context contextImpl = getApplicationContext();
    if (contextImpl != null) {
        Class<?> contextImplClass = Class.forName("android.app.ContextImpl");
        Field mPackageInfoField = findField(contextImplClass, "mPackageInfo");
        if (mPackageInfoField != null) {
            Object loadedApk = mPackageInfoField.get(contextImpl);
            if (loadedApk != null) {
                Field mApplicationField = findField(loadedApk.getClass(), "mApplication");
                if (mApplicationField != null) {
                    mApplicationField.set(loadedApk, sourceApp);
                    log("✓ Replaced LoadedApk.mApplication");
                }
            }
        }
    }
    
    // 2. 替换ActivityThread中的Application引用
    Object activityThread = getActivityThread();
    if (activityThread != null) {
        // 替换mInitialApplication
        Field mInitialApplicationField = findField(activityThread.getClass(), "mInitialApplication");
        if (mInitialApplicationField != null) {
            mInitialApplicationField.set(activityThread, sourceApp);
            log("✓ Replaced ActivityThread.mInitialApplication");
        }
        
        // 替换mAllApplications列表
        Field mAllApplicationsField = findField(activityThread.getClass(), "mAllApplications");
        if (mAllApplicationsField != null) {
            @SuppressWarnings("unchecked") 
            ArrayList<Application> mAllApplications = (ArrayList<Application>) mAllApplicationsField.get(activityThread);
            if (mAllApplications != null) {
                mAllApplications.remove(shellApp);
                mAllApplications.add(sourceApp);
                log("✓ Updated ActivityThread.mAllApplications");
            }
        }
        
        // 更新mBoundApplication的信息
        updateBoundApplicationInfo(activityThread, mApplicationName);
    }
}

/**
 * 【关键差异】手动调用源Application的attachBaseContext
 */
private void invokeSourceApplicationAttach(Application application, Context baseContext) throws Exception {
    try {
        Method attachMethod = findMethod(Application.class, "attachBaseContext");
        if (attachMethod != null) {
            attachMethod.invoke(application, baseContext);
            log("✓ Successfully called attachBaseContext on source application");
        }
    } catch (Exception e) {
        log("⚠ Failed to call attachBaseContext, trying manual context attachment");
        manuallyAttachContext(application, baseContext);
    }
}

@Override
public void onCreate() {
    super.onCreate();
    
    // 【关键差异】在onCreate中调用源Application的onCreate
    if (mSourceApplication != null) {
        try {
            mSourceApplication.onCreate();
            log("✓ Successfully called onCreate on source application");
        } catch (Exception e) {
            log("✗ Error calling onCreate on source application: " + Log.getStackTraceString(e));
        }
    }
}
```

**V2版本优势：**

- 不依赖系统makeApplication方法，兼容Android 13+

**V2版本劣势：**

- 需手动在壳的Application生命周期调用源程序对应的生命周期方法
- 需要更多的兼容性测试

#### 2.6 版本选择指南

| 特性 | V1版本 | V2版本 |
| --- | --- | --- |
| **兼容性** | Android 5.0-12 | Android 5.0+ (包括13+) |
| **实现方式** | 系统makeApplication | 直接实例化 |
| **代码复杂度** | 简单 | 复杂 |
| **错误处理** | 基础 | 完善 |
| **推荐使用** | 旧版本兼容 | **生产环境推荐** |

**技术总结：**

- V1版本是以前流行的公开通用版本
- V2版本是目前生产环境的最佳选择，能够应对最新的Android版本限制
- 两个版本在前三个阶段（源APK提取、解密、ClassLoader替换）完全相同
- 核心差异在于Application的创建和系统引用替换方式

##### 2.7 反射辅助工具 (LoadedApkReflectionHelper.java)

```
public class LoadedApkReflectionHelper {
    private static final String TAG = "LoadedApkHelper";
    
    public static Object getCurrentActivityThread() throws Exception {
        Class<?> activityThreadClass = Class.forName("android.app.ActivityThread");
        Field sCurrentActivityThreadField = activityThreadClass.getDeclaredField("sCurrentActivityThread");
        sCurrentActivityThreadField.setAccessible(true);
        return sCurrentActivityThreadField.get(null);
    }
    
    public static Object getLoadedApk(Object activityThread, String packageName) throws Exception {
        Field mPackagesField = activityThread.getClass().getDeclaredField("mPackages");
        mPackagesField.setAccessible(true);
        ArrayMap<String, WeakReference<?>> packages = 
            (ArrayMap<String, WeakReference<?>>) mPackagesField.get(activityThread);
        
        WeakReference<?> loadedApkRef = packages.get(packageName);
        if (loadedApkRef == null) {
            throw new RuntimeException("LoadedApk not found for package: " + packageName);
        }
        
        Object loadedApk = loadedApkRef.get();
        if (loadedApk == null) {
            throw new RuntimeException("LoadedApk has been garbage collected");
        }
        
        return loadedApk;
    }
    
    public static ArrayMap<String, WeakReference<?>> getApplications(Object activityThread) throws Exception {
        Field sApplicationsField = Class.forName("android.app.LoadedApk").getDeclaredField("sApplications");
        sApplicationsField.setAccessible(true);
        return (ArrayMap<String, WeakReference<?>>) sApplicationsField.get(null);
    }
    
    public static Set<String> getAllPackageNames(Object activityThread) throws Exception {
        ArrayMap<String, WeakReference<?>> applications = getApplications(activityThread);
        return new HashSet<>(applications.keySet());
    }
}
```

#### 2.8 总结关键技术点

1. **DEX文件结构理解**: 准确解析DEX文件格式，提取嵌入的源APK
2. **Android类加载机制**: 深入理解ClassLoader层次结构和加载流程
3. **Application生命周期**: 正确处理Application的创建和初始化时序
4. **反射技术**: 大量使用反射访问和修改系统私有字段和方法
5. **高版本兼容性处理**: V2版本通过直接实例化Application绕过Android 13+的对LoadedApk.makeApplication()限制
6. **了解应用安装后源apk文件存在的目录**：然后从可以从这里加载源apk,读取加密后的源dex文件

---

### 模块三：Source-App 源程序模块

#### 3.1 模块概述

Source-App模块是AppShield项目中的**被保护程序**，它是一个功能完整的Android应用程序，专门设计用于演示加壳保护技术。该模块展示了现代Android开发的最佳实践，同时针对加壳需求进行了特殊优化。

##### 3.1.1 设计目标

- **单DEX约束**: 确保应用编译为单个DEX文件，满足加壳工具的处理要求，学习阶段，demo实现单dex加固会简单很多。
- **功能完整性**: 提供完整的Android应用功能，包括UI、业务逻辑、数据存储等
- **技术展示**: 集成多种Android技术栈，展示加壳保护的适用性
- **易于测试**: 提供直观的界面和功能，便于验证加壳效果

#### 3.2 模块架构

```
source-app/
├── build.gradle.kts              # 源程序构建配置
├── src/main/
│   ├── AndroidManifest.xml        # 源程序清单文件
│   ├── cpp/                       # NDK原生代码
│   │   ├── CMakeLists.txt
│   │   ├── native-lib.cpp         # 静态注册JNI方法
│   │   └── dynamic-registration.cpp # 动态注册JNI方法
│   ├── java/com/csh/source/
│   │   ├── SourceApplication.kt    # 自定义Application
│   │   ├── MainActivity.kt         # 主Activity
│   │   ├── NativeLibrary.kt        # JNI接口定义
│   │   ├── config/
│   │   │   └── AppConfig.kt        # 应用配置
│   │   ├── ui/theme/               # UI主题
│   │   └── utils/
│   │       └── AppUtils.kt         # 工具类
│   └── res/                        # 资源文件
└── proguard-rules.pro             # 混淆规则
```

#### 3.2 核心功能

##### 3.2.1 单DEX文件保证机制

**关键配置策略**

```
android {
    defaultConfig {
        multiDexEnabled = false  // 强制单DEX
        ndk {
            abiFilters.addAll(arrayOf("arm64-v8a"))  // 限制ABI减少方法数
        }
    }
    
    buildTypes {
        release {
            isMinifyEnabled = true      // 启用混淆压缩方法数
            isShrinkResources = true    // 启用资源压缩
        }
    }
}
```

**依赖优化策略**

- 使用`implementation`而不是`api`减少传递依赖
- 移除不必要的自动初始化器
- 限制第三方库的使用
- 通过ProGuard/R8进行代码压缩

**单DEX保证的技术要点**：

1. **方法数限制**: Android DEX文件最多支持65536个方法引用
2. **依赖管理**: 精简依赖，避免大型第三方库
3. **代码混淆**: 通过R8/ProGuard移除未使用代码
4. **资源优化**: 压缩资源文件，移除未使用资源
5. **ABI限制**: 只支持主流架构，减少native库体积

##### 3.2.2 应用架构设计

**SourceApplication** - 自定义Application类

- 应用生命周期管理
- 组件初始化协调
- Native库加载
- 配置管理集成

**MainActivity** - Compose UI主界面

- 现代化UI设计（Material Design 3）
- NDK功能测试界面
- 应用信息展示
- 配置管理界面

**NDK集成** - JNI接口设计

- 静态注册JNI方法
- 动态注册JNI方法
- C++实现核心算法
- CMake构建配置

#### 3.3 详细实现

##### 3.3.1 自定义Application (SourceApplication.kt)

```
class SourceApplication : Application() {
    private val tag = "SourceApplication"
    
    override fun onCreate() {
        super.onCreate()
        Log.i(tag, "SourceApplication 启动")
        
        // 初始化配置管理
        AppConfig.init(this)
        
        // 记录启动信息
        logAppInfo()
    }
    
    private fun logAppInfo() {
        Log.i(tag, "应用信息: ${AppUtils.getAppName()}")
        Log.i(tag, "版本信息: ${AppUtils.getVersionName()} (${AppUtils.getVersionCode()})")
        Log.i(tag, "包名: ${AppUtils.getPackageName()}")
    }
    
    fun getAppInfo(): String {
        return buildString {
            appendLine("=== SourceApplication 信息 ===")
            appendLine("应用名: ${AppUtils.getAppName()}")
            appendLine("包名: ${AppUtils.getPackageName()}")
            appendLine("版本: ${AppUtils.getVersionName()} (${AppUtils.getVersionCode()})")
            appendLine("首次启动: ${AppConfig.isFirstLaunch()}")
            appendLine("调试模式: ${AppConfig.isDebugMode()}")
            appendLine("启动次数: ${AppConfig.getLaunchCount()}")
        }
    }
    
    companion object {
        @Volatile
        private var INSTANCE: SourceApplication? = null
        
        fun getInstance(): SourceApplication {
            return INSTANCE ?: throw IllegalStateException("Application not initialized")
        }
        
        internal fun setInstance(app: SourceApplication) {
            INSTANCE = app
        }
    }
    
    override fun attachBaseContext(base: Context?) {
        super.attachBaseContext(base)
        setInstance(this)
    }
}
```

##### 3.3.2 应用工具类 (AppUtils.kt)

```
object AppUtils {
    private const val TAG = "AppUtils"
    private lateinit var context: Context
    
    fun init(context: Context) {
        this.context = context.applicationContext
    }
    
    fun getVersionName(): String {
        return try {
            val packageInfo = context.packageManager.getPackageInfo(context.packageName, 0)
            packageInfo.versionName ?: "Unknown"
        } catch (e: Exception) {
            Log.e(TAG, "获取版本名失败", e)
            "Unknown"
        }
    }
    
    fun getVersionCode(): Long {
        return try {
            val packageInfo = context.packageManager.getPackageInfo(context.packageName, 0)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                packageInfo.longVersionCode
            } else {
                @Suppress("DEPRECATION")
                packageInfo.versionCode.toLong()
            }
        } catch (e: Exception) {
            Log.e(TAG, "获取版本号失败", e)
            -1L
        }
    }
    
    fun getPackageName(): String = context.packageName
    
    fun getAppName(): String {
        return try {
            val applicationInfo = context.applicationInfo
            val packageManager = context.packageManager
            packageManager.getApplicationLabel(applicationInfo).toString()
        } catch (e: Exception) {
            Log.e(TAG, "获取应用名失败", e)
            "Unknown App"
        }
    }
    
    fun getFullAppInfo(): String {
        return buildString {
            appendLine("=== 应用详细信息 ===")
            appendLine("应用名: ${getAppName()}")
            appendLine("包名: ${getPackageName()}")
            appendLine("版本名: ${getVersionName()}")
            appendLine("版本号: ${getVersionCode()}")
            appendLine("目标SDK: ${context.applicationInfo.targetSdkVersion}")
            appendLine("最小SDK: ${getMinSdkVersion()}")
            appendLine("")
            appendLine("=== 设备信息 ===")
            appendLine("设备型号: ${Build.MODEL}")
            appendLine("设备厂商: ${Build.MANUFACTURER}")
            appendLine("Android版本: ${Build.VERSION.RELEASE}")
            appendLine("API级别: ${Build.VERSION.SDK_INT}")
            appendLine("CPU架构: ${Build.SUPPORTED_ABIS.joinToString(", ")}")
            appendLine("")
            appendLine("=== 运行时信息 ===")
            appendLine("可用内存: ${getAvailableMemory()}MB")
            appendLine("总内存: ${getTotalMemory()}MB")
            appendLine("存储空间: ${getAvailableStorage()}MB")
        }
    }
    
    private fun getMinSdkVersion(): Int {
        return try {
            val packageInfo = context.packageManager.getPackageInfo(context.packageName, 0)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                packageInfo.applicationInfo.minSdkVersion
            } else {
                -1
            }
        } catch (e: Exception) {
            -1
        }
    }
    
    private fun getAvailableMemory(): Long {
        val activityManager = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val memoryInfo = ActivityManager.MemoryInfo()
        activityManager.getMemoryInfo(memoryInfo)
        return memoryInfo.availMem / (1024 * 1024)
    }
    
    private fun getTotalMemory(): Long {
        val activityManager = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val memoryInfo = ActivityManager.MemoryInfo()
        activityManager.getMemoryInfo(memoryInfo)
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.JELLY_BEAN) {
            memoryInfo.totalMem / (1024 * 1024)
        } else {
            -1L
        }
    }
    
    private fun getAvailableStorage(): Long {
        return try {
            val stat = StatFs(context.filesDir.path)
            val availableBytes = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.JELLY_BEAN_MR2) {
                stat.availableBytes
            } else {
                @Suppress("DEPRECATION")
                stat.availableBlocks.toLong() * stat.blockSize
            }
            availableBytes / (1024 * 1024)
        } catch (e: Exception) {
            -1L
        }
    }
}
```

##### 3.3.3 配置管理 (AppConfig.kt)

```
object AppConfig {
    private lateinit var context: Context
    private lateinit var sharedPreferences: SharedPreferences
    private const val TAG = "AppConfig"
    private const val PREFS_NAME = "app_config"
    
    // 配置键
    private const val KEY_FIRST_LAUNCH = "first_launch"
    private const val KEY_DEBUG_MODE = "debug_mode"
    private const val KEY_LAST_VERSION = "last_version"
    private const val KEY_LAUNCH_COUNT = "launch_count"
    
    fun init(context: Context) {
        this.context = context.applicationContext
        this.sharedPreferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        
        // 更新启动计数
        updateLaunchInfo()
        
        Log.d(TAG, "AppConfig 初始化完成")
    }
    
    private fun updateLaunchInfo() {
        val currentVersion = AppUtils.getVersionCode()
        val lastVersion = getLong(KEY_LAST_VERSION, -1)
        val launchCount = getInt(KEY_LAUNCH_COUNT, 0)
        
        // 更新版本信息
        if (lastVersion != currentVersion) {
            putLong(KEY_LAST_VERSION, currentVersion)
            Log.i(TAG, "版本更新: $lastVersion -> $currentVersion")
        }
        
        // 更新启动计数
        putInt(KEY_LAUNCH_COUNT, launchCount + 1)
        Log.d(TAG, "应用启动次数: ${launchCount + 1}")
    }
    
    // 基础存储方法
    fun putString(key: String, value: String) {
        sharedPreferences.edit().putString(key, value).apply()
    }
    
    fun getString(key: String, defaultValue: String = ""): String {
        return sharedPreferences.getString(key, defaultValue) ?: defaultValue
    }
    
    fun putInt(key: String, value: Int) {
        sharedPreferences.edit().putInt(key, value).apply()
    }
    
    fun getInt(key: String, defaultValue: Int = 0): Int {
        return sharedPreferences.getInt(key, defaultValue)
    }
    
    fun putLong(key: String, value: Long) {
        sharedPreferences.edit().putLong(key, value).apply()
    }
    
    fun getLong(key: String, defaultValue: Long = 0L): Long {
        return sharedPreferences.getLong(key, defaultValue)
    }
    
    fun putBoolean(key: String, value: Boolean) {
        sharedPreferences.edit().putBoolean(key, value).apply()
    }
    
    fun getBoolean(key: String, defaultValue: Boolean = false): Boolean {
        return sharedPreferences.getBoolean(key, defaultValue)
    }
    
    // 业务配置方法
    fun isFirstLaunch(): Boolean {
        val isFirst = getBoolean(KEY_FIRST_LAUNCH, true)
        if (isFirst) {
            putBoolean(KEY_FIRST_LAUNCH, false)
        }
        return isFirst
    }
    
    fun isDebugMode(): Boolean {
        return getBoolean(KEY_DEBUG_MODE, BuildConfig.DEBUG)
    }
    
    fun setDebugMode(enabled: Boolean) {
        putBoolean(KEY_DEBUG_MODE, enabled)
    }
    
    fun getLaunchCount(): Int {
        return getInt(KEY_LAUNCH_COUNT, 0)
    }
    
    fun getLastVersion(): Long {
        return getLong(KEY_LAST_VERSION, -1)
    }
    
    // 清除所有配置
    fun clearAll() {
        sharedPreferences.edit().clear().apply()
        Log.i(TAG, "所有配置已清除")
    }
    
    // 获取配置摘要
    fun getConfigSummary(): String {
        return buildString {
            appendLine("=== 应用配置 ===")
            appendLine("首次启动: ${isFirstLaunch()}")
            appendLine("调试模式: ${isDebugMode()}")
            appendLine("启动次数: ${getLaunchCount()}")
            appendLine("上次版本: ${getLastVersion()}")
            appendLine("当前版本: ${AppUtils.getVersionCode()}")
        }
    }
}
```

##### 3.3.4 主界面Activity (MainActivity.kt)

```
class MainActivity : ComponentActivity() {
    private val tag = "MainActivity"
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        Log.i(tag, "MainActivity 启动")
        
        setContent {
            AppShieldTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    MainScreen()
                }
            }
        }
    }
}

@Composable
fun MainScreen() {
    var selectedTab by remember { mutableIntStateOf(0) }
    val tabs = listOf("应用信息", "NDK测试", "配置管理")
    
    Column {
        // 顶部标题栏
        TopAppBar(
            title = { Text("AppShield Source App") },
            colors = TopAppBarDefaults.topAppBarColors(
                containerColor = MaterialTheme.colorScheme.primaryContainer
            )
        )
        
        // Tab选项卡
        TabRow(selectedTabIndex = selectedTab) {
            tabs.forEachIndexed { index, title ->
                Tab(
                    selected = selectedTab == index,
                    onClick = { selectedTab = index },
                    text = { Text(title) }
                )
            }
        }
        
        // 内容区域
        when (selectedTab) {
            0 -> AppInfoScreen()
            1 -> NdkTestScreen()
            2 -> ConfigScreen()
        }
    }
}

@Composable
fun AppInfoScreen() {
    val context = LocalContext.current
    val sourceApp = SourceApplication.getInstance()
    
    var appInfo by remember { mutableStateOf("") }
    var deviceInfo by remember { mutableStateOf("") }
    
    LaunchedEffect(Unit) {
        appInfo = sourceApp.getAppInfo()
        deviceInfo = AppUtils.getFullAppInfo()
    }
    
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            InfoCard(
                title = "自定义Application信息",
                content = appInfo
            )
        }
        
        item {
            InfoCard(
                title = "设备详细信息",
                content = deviceInfo
            )
        }
        
        item {
            InfoCard(
                title = "配置信息",
                content = AppConfig.getConfigSummary()
            )
        }
    }
}

@Composable
fun NdkTestScreen() {
    var staticResult by remember { mutableStateOf("") }
    var dynamicResult by remember { mutableStateOf("") }
    var testResults by remember { mutableStateOf("") }
    
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Text(
                text = "NDK功能测试",
                style = MaterialTheme.typography.headlineMedium,
                modifier = Modifier.padding(bottom = 8.dp)
            )
        }
        
        // 静态注册测试
        item {
            Card {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        text = "静态注册方法测试",
                        style = MaterialTheme.typography.titleMedium
                    )
                    
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Button(
                            onClick = {
                                staticResult = try {
                                    "字符串: ${NativeLibrary.staticStringFromJNI()}\n" +
                                    "加法: ${NativeLibrary.staticAddNumbers(10, 20)}\n" +
                                    "数组求和: ${NativeLibrary.staticSumArray(intArrayOf(1, 2, 3, 4, 5))}"
                                } catch (e: Exception) {
                                    "错误: ${e.message}"
                                }
                            }
                        ) {
                            Text("测试静态方法")
                        }
                    }
                    
                    if (staticResult.isNotEmpty()) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = staticResult,
                            style = MaterialTheme.typography.bodyMedium,
                            modifier = Modifier
                                .background(
                                    MaterialTheme.colorScheme.surfaceVariant,
                                    RoundedCornerShape(4.dp)
                                )
                                .padding(8.dp)
                                .fillMaxWidth()
                        )
                    }
                }
            }
        }
        
        // 动态注册测试
        item {
            Card {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        text = "动态注册方法测试",
                        style = MaterialTheme.typography.titleMedium
                    )
                    
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Button(
                            onClick = {
                                dynamicResult = try {
                                    "设备信息: ${NativeLibrary.dynamicGetDeviceInfo()}\n" +
                                    "字符串反转: ${NativeLibrary.dynamicReverseString("Hello World")}\n" +
                                    "斐波那契(10): ${NativeLibrary.dynamicFibonacci(10)}"
                                } catch (e: Exception) {
                                    "错误: ${e.message}"
                                }
                            }
                        ) {
                            Text("测试动态方法")
                        }
                    }
                    
                    if (dynamicResult.isNotEmpty()) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = dynamicResult,
                            style = MaterialTheme.typography.bodyMedium,
                            modifier = Modifier
                                .background(
                                    MaterialTheme.colorScheme.surfaceVariant,
                                    RoundedCornerShape(4.dp)
                                )
                                .padding(8.dp)
                                .fillMaxWidth()
                        )
                    }
                }
            }
        }
        
        // 综合测试
        item {
            Card {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        text = "综合性能测试",
                        style = MaterialTheme.typography.titleMedium
                    )
                    
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    Button(
                        onClick = {
                            testResults = performComprehensiveTest()
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("运行综合测试")
                    }
                    
                    if (testResults.isNotEmpty()) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = testResults,
                            style = MaterialTheme.typography.bodyMedium,
                            modifier = Modifier
                                .background(
                                    MaterialTheme.colorScheme.surfaceVariant,
                                    RoundedCornerShape(4.dp)
                                )
                                .padding(8.dp)
                                .fillMaxWidth()
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun ConfigScreen() {
    var debugMode by remember { mutableStateOf(AppConfig.isDebugMode()) }
    
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Text(
                text = "应用配置",
                style = MaterialTheme.typography.headlineMedium
            )
        }
        
        item {
            Card {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("调试模式")
                        Switch(
                            checked = debugMode,
                            onCheckedChange = { 
                                debugMode = it
                                AppConfig.setDebugMode(it)
                            }
                        )
                    }
                }
            }
        }
        
        item {
            InfoCard(
                title = "配置详情",
                content = AppConfig.getConfigSummary()
            )
        }
        
        item {
            Button(
                onClick = {
                    AppConfig.clearAll()
                },
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.error
                ),
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("清除所有配置")
            }
        }
    }
}

@Composable
fun InfoCard(
    title: String,
    content: String
) {
    Card {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.padding(bottom = 8.dp)
            )
            
            Text(
                text = content,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier
                    .background(
                        MaterialTheme.colorScheme.surfaceVariant,
                        RoundedCornerShape(4.dp)
                    )
                    .padding(8.dp)
                    .fillMaxWidth()
            )
        }
    }
}

private fun performComprehensiveTest(): String {
    return try {
        val startTime = System.currentTimeMillis()
        
        // 测试静态方法
        val staticTests = buildString {
            appendLine("=== 静态注册测试 ===")
            appendLine("字符串: ${NativeLibrary.staticStringFromJNI()}")
            appendLine("加法 (100+200): ${NativeLibrary.staticAddNumbers(100, 200)}")
            
            val largeArray = IntArray(1000) { it + 1 }
            val sum = NativeLibrary.staticSumArray(largeArray)
            appendLine("大数组求和 (1-1000): $sum")
        }
        
        // 测试动态方法
        val dynamicTests = buildString {
            appendLine("\n=== 动态注册测试 ===")
            appendLine("设备信息: ${NativeLibrary.dynamicGetDeviceInfo()}")
            appendLine("字符串反转: ${NativeLibrary.dynamicReverseString("AppShield Test")}")
            appendLine("斐波那契(20): ${NativeLibrary.dynamicFibonacci(20)}")
        }
        
        val endTime = System.currentTimeMillis()
        val duration = endTime - startTime
        
        staticTests + dynamicTests + "\n=== 性能统计 ===\n测试耗时: ${duration}ms"
        
    } catch (e: Exception) {
        "测试失败: ${e.message}"
    }
}
```

#### 3.4 NDK集成

##### 3.4.1 JNI接口定义 (NativeLibrary.kt)

```
object NativeLibrary {
    private const val TAG = "NativeLibrary"
    
    init {
        try {
            System.loadLibrary("native-lib")
            Log.i(TAG, "Native库加载成功")
        } catch (e: UnsatisfiedLinkError) {
            Log.e(TAG, "Native库加载失败", e)
            throw e
        }
    }
    
    // ========== 静态注册方法 ==========
    
    /**
     * 获取来自C++的字符串
     */
    external fun staticStringFromJNI(): String
    
    /**
     * 两个整数相加
     */
    external fun staticAddNumbers(a: Int, b: Int): Int
    
    /**
     * 计算整数数组的和
     */
    external fun staticSumArray(array: IntArray): Long
    
    // ========== 动态注册方法 ==========
    
    /**
     * 获取设备信息
     */
    external fun dynamicGetDeviceInfo(): String
    
    /**
     * 反转字符串
     */
    external fun dynamicReverseString(input: String): String
    
    /**
     * 计算斐波那契数列
     */
    external fun dynamicFibonacci(n: Int): Long
}
```

##### 3.4.2 C++实现 (native-lib.cpp)

```
#include <jni.h>
#include <string>
#include <android/log.h>
#include <vector>
#include <sys/system_properties.h>

#define LOG_TAG "NativeLib"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

// 声明动态注册函数
extern "C" int registerDynamicMethods(JNIEnv *env);

// ========== 静态注册方法实现 ==========

extern "C" JNIEXPORT jstring JNICALL
Java_com_csh_source_NativeLibrary_staticStringFromJNI(JNIEnv *env, jclass clazz) {
    std::string hello = "Hello from C++ (Static Registration) - AppShield";
    LOGI("staticStringFromJNI called");
    return env->NewStringUTF(hello.c_str());
}

extern "C" JNIEXPORT jint JNICALL
Java_com_csh_source_NativeLibrary_staticAddNumbers(JNIEnv *env, jclass clazz, jint a, jint b) {
    jint result = a + b;
    LOGI("staticAddNumbers: %d + %d = %d", a, b, result);
    return result;
}

extern "C" JNIEXPORT jlong JNICALL
Java_com_csh_source_NativeLibrary_staticSumArray(JNIEnv *env, jclass clazz, jintArray array) {
    if (array == nullptr) {
        LOGE("Array is null");
        return 0;
    }
    
    jsize length = env->GetArrayLength(array);
    jint *elements = env->GetIntArrayElements(array, nullptr);
    
    if (elements == nullptr) {
        LOGE("Failed to get array elements");
        return 0;
    }
    
    jlong sum = 0;
    for (jsize i = 0; i < length; i++) {
        sum += elements[i];
    }
    
    env->ReleaseIntArrayElements(array, elements, JNI_ABORT);
    
    LOGI("staticSumArray: length=%d, sum=%lld", length, sum);
    return sum;
}

// ========== JNI_OnLoad ==========

extern "C" JNIEXPORT jint JNICALL
JNI_OnLoad(JavaVM *vm, void *reserved) {
    LOGI("JNI_OnLoad called");
    
    JNIEnv *env;
    if (vm->GetEnv(reinterpret_cast<void **>(&env), JNI_VERSION_1_6) != JNI_OK) {
        LOGE("Failed to get JNI environment");
        return JNI_ERR;
    }
    
    // 注册动态方法
    if (registerDynamicMethods(env) != JNI_OK) {
        LOGE("Failed to register dynamic methods");
        return JNI_ERR;
    }
    
    LOGI("JNI_OnLoad completed successfully");
    return JNI_VERSION_1_6;
}
```

##### 3.4.3 动态注册实现 (dynamic-registration.cpp)

```
#include <jni.h>
#include <string>
#include <android/log.h>
#include <algorithm>
#include <sys/system_properties.h>
#include <unistd.h>
#include <sys/utsname.h>

#define LOG_TAG "DynamicReg"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

// ========== 动态注册方法实现 ==========

jstring dynamicGetDeviceInfo(JNIEnv *env, jobject thiz) {
    LOGI("dynamicGetDeviceInfo called");
    
    char manufacturer[PROP_VALUE_MAX];
    char model[PROP_VALUE_MAX];
    char version[PROP_VALUE_MAX];
    char sdk[PROP_VALUE_MAX];
    
    __system_property_get("ro.product.manufacturer", manufacturer);
    __system_property_get("ro.product.model", model);
    __system_property_get("ro.build.version.release", version);
    __system_property_get("ro.build.version.sdk", sdk);
    
    struct utsname unameData;
    uname(&unameData);
    
    std::string deviceInfo = "设备信息:\n";
    deviceInfo += "厂商: " + std::string(manufacturer) + "\n";
    deviceInfo += "型号: " + std::string(model) + "\n";
    deviceInfo += "Android版本: " + std::string(version) + "\n";
    deviceInfo += "SDK版本: " + std::string(sdk) + "\n";
    deviceInfo += "内核版本: " + std::string(unameData.release) + "\n";
    deviceInfo += "架构: " + std::string(unameData.machine) + "\n";
    deviceInfo += "进程ID: " + std::to_string(getpid());
    
    return env->NewStringUTF(deviceInfo.c_str());
}

jstring dynamicReverseString(JNIEnv *env, jobject thiz, jstring input) {
    if (input == nullptr) {
        LOGE("Input string is null");
        return env->NewStringUTF("");
    }
    
    const char *inputStr = env->GetStringUTFChars(input, nullptr);
    if (inputStr == nullptr) {
        LOGE("Failed to get input string");
        return env->NewStringUTF("");
    }
    
    std::string str(inputStr);
    std::reverse(str.begin(), str.end());
    
    env->ReleaseStringUTFChars(input, inputStr);
    
    LOGI("dynamicReverseString: reversed string length=%zu", str.length());
    return env->NewStringUTF(str.c_str());
}

jlong dynamicFibonacci(JNIEnv *env, jobject thiz, jint n) {
    LOGI("dynamicFibonacci called with n=%d", n);
    
    if (n <= 0) return 0;
    if (n == 1) return 1;
    
    // 使用迭代方式计算，避免递归栈溢出
    jlong prev = 0, curr = 1;
    for (jint i = 2; i <= n; i++) {
        jlong next = prev + curr;
        prev = curr;
        curr = next;
    }
    
    LOGI("dynamicFibonacci: fib(%d) = %lld", n, curr);
    return curr;
}

// ========== 方法注册表 ==========

static JNINativeMethod gMethods[] = {
    {
        "dynamicGetDeviceInfo",
        "()Ljava/lang/String;",
        (void*)dynamicGetDeviceInfo
    },
    {
        "dynamicReverseString",
        "(Ljava/lang/String;)Ljava/lang/String;",
        (void*)dynamicReverseString
    },
    {
        "dynamicFibonacci",
        "(I)J",
        (void*)dynamicFibonacci
    }
};

// ========== 注册函数 ==========

extern "C" int registerDynamicMethods(JNIEnv *env) {
    LOGI("Registering dynamic methods...");
    
    const char *className = "com/csh/source/NativeLibrary";
    jclass clazz = env->FindClass(className);
    
    if (clazz == nullptr) {
        LOGE("Failed to find class %s", className);
        return JNI_ERR;
    }
    
    int methodCount = sizeof(gMethods) / sizeof(gMethods[0]);
    if (env->RegisterNatives(clazz, gMethods, methodCount) < 0) {
        LOGE("Failed to register native methods");
        env->DeleteLocalRef(clazz);
        return JNI_ERR;
    }
    
    env->DeleteLocalRef(clazz);
    LOGI("Successfully registered %d dynamic methods", methodCount);
    return JNI_OK;
}
```

##### 3.4.4 CMake构建配置 (CMakeLists.txt)

```
cmake_minimum_required(VERSION 3.22.1)

# 设置项目名称
project("native-lib")

# 设置C++标准
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 添加编译选项
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -O2")

# 创建共享库
add_library(
    native-lib
    SHARED
    native-lib.cpp
    dynamic-registration.cpp
)

# 查找并链接所需的库
find_library(
    log-lib
    log
)

# 链接库
target_link_libraries(
    native-lib
    ${log-lib}
)

# 设置包含目录
target_include_directories(
    native-lib
    PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
)

# 添加预处理器定义
target_compile_definitions(
    native-lib
    PRIVATE
    ANDROID_NDK
)
```

##### 3.4.5 UI主题配置 (AppShieldTheme.kt)

```
@Composable
fun AppShieldTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = true,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }
    
    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}

private val DarkColorScheme = darkColorScheme(
    primary = Purple80,
    secondary = PurpleGrey80,
    tertiary = Pink80
)

private val LightColorScheme = lightColorScheme(
    primary = Purple40,
    secondary = PurpleGrey40,
    tertiary = Pink40
)

// 颜色定义
val Purple80 = Color(0xFFD0BCFF)
val PurpleGrey80 = Color(0xFFCCC2DC)
val Pink80 = Color(0xFFEFB8C8)

val Purple40 = Color(0xFF6650a4)
val PurpleGrey40 = Color(0xFF625b71)
val Pink40 = Color(0xFF7D5260)

// 字体样式定义
val Typography = Typography(
    bodyLarge = TextStyle(
        fontFamily = FontFamily.Default,
        fontWeight = FontWeight.Normal,
        fontSize = 16.sp,
        lineHeight = 24.sp,
        letterSpacing = 0.5.sp
    )
)
```

#### 3.5 技术要点

1. **现代Android开发**: 既可以使用Kotlin + Compose构建现代化UI，也可以用旧Ui框架
2. **NDK集成**: 同时支持静态和动态JNI方法注册
3. **单DEX优化**: 通过多种手段确保生成单个DEX文件，这是这个原理学习版本最重要的。

#### 3.6 单DEX优化策略

1. **构建配置优化**:

   - 强制禁用MultiDex
   - 限制ABI支持
   - 启用代码混淆和资源压缩
2. **依赖管理优化**:

   - 使用implementation而非api
   - 移除不必要的依赖
   - 禁用自动初始化器
3. **资源优化**:

   - 排除不必要的META-INF文件
   - 使用资源压缩

---

### 整体架构和工作流程

#### 4.1 三模块协作关系

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Source-App    │    │   Shell-App     │    │     Packer      │
│   (被保护程序)   │    │   (壳程序)      │    │   (加壳工具)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  source.apk     │    │  shell.apk      │    │  packer.jar     │
│  (源APK文件)     │    │  (壳APK文件)     │    │  (命令行工具)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │    protected.apk        │
                    │    (加壳后的APK)        │
                    └─────────────────────────┘
```

#### 4.2 完整工作流程

##### 4.2.1 开发阶段

1. **开发源程序** (source-app)

   - 实现业务逻辑
   - 配置单DEX构建
   - 编译生成source.apk
2. **开发壳程序** (shell-app)

   - 实现解密和加载逻辑
   - 配置单DEX构建
   - 编译生成shell.apk
3. **开发加壳工具** (packer)

   - 实现APK合并逻辑
   - 编译生成packer.jar

##### 4.2.2 加壳阶段

```
# 使用packer工具进行加壳
java -jar packer.jar -src source.apk -shell shell.apk -o protected.apk
```

**加壳过程详细步骤**:

1. 解包source.apk和shell.apk
2. 读取shell.apk的classes.dex
3. 加密source.apk内容（异或0xFF）
4. 将加密的source.apk追加到shell的classes.dex末尾
5. 添加source.apk大小标识（4字节）
6. 修复DEX文件头（大小、校验和、签名）
7. 修改AndroidManifest.xml，设置壳Application
8. 重新打包并签名

##### 4.2.3 运行阶段

**用户安装并启动protected.apk时**:

1. **系统启动壳Application** (ShellProxyApplicationV1)
   attachBaseContext() → onCreate()
2. **壳程序解密源程序**
   读取classes.dex → 提取加密的source.apk → 解密 → 保存到私有目录
3. **替换运行环境**
   创建DexClassLoader → 替换LoadedApk.mClassLoader → 替换Application
4. **启动源程序**
   调用源程序Application.onCreate() → 正常运行源程序逻辑

##### 4.2.4 应用启动流程对比

**V1 版本流程**

```
sequenceDiagram
    participant System as Android系统
    participant V1 as ShellProxyApplicationV1
    participant Reflection as 反射工具
    participant Source as 源Application
    
    System->>V1: attachBaseContext()
    V1->>V1: 解密APK
    V1->>V1: 替换ClassLoader
    System->>V1: onCreate()
    V1->>Reflection: 反射调用系统makeApplication，创建源Application
    Reflection->>Source: 创建实例
    V1->>Source: onCreate()
```

**V2 版本流程**

```
sequenceDiagram
    participant System as Android系统
    participant V2 as ShellProxyApplicationV2
    participant Source as 源Application
    
    System->>V2: attachBaseContext()
    V2->>V2: 解密APK
    V2->>V2: 替换ClassLoader
    V2->>Source: 反射直接创建实例
    V2->>System: 替换系统引用
    V2->>Source: attachBaseContext()
    System->>V2: onCreate()
    V2->>Source: onCreate()
```

#### 4.3 安全性分析

##### 4.3.1 保护机制

1. **代码隐藏**: 源程序代码被加密隐藏在DEX文件中

![image.png](/images/Android第一代加固技术原理详解-附源码/03.png)
源程序反编译

![image.png](/images/Android第一代加固技术原理详解-附源码/04.png)
加固后只能看到壳shell的代码，看不到源程序的代码，但是源程序的dex代码又的确在apk中，在这加固后的apk里面的唯一一个dex的尾部，这部分不会被反编译软件静态给反编译出来。

2. **动态解密**: 运行时才解密，增加静态分析难度

![image.png](/images/Android第一代加固技术原理详解-附源码/05.png)
每个应用程序被安装到系统后，都会在内部存储中保留自己的apk文件（root手机可以直接看到），而我们运行时的时候直接从apk里面读取壳和源程序组成的dex

```
/**
 * 从壳APK中解密并提取源APK文件
 */
private boolean extractSourceApk() {
    try {
        // 1. 创建私有目录,保存dex,lib和源apk， 具体路径为data/user/0/<package_name>/app_tmp_dex（root机可看）
        File dex = getDir("tmp_dex", MODE_PRIVATE);
        File lib = getDir("tmp_lib", MODE_PRIVATE);
        oDexPath = dex.getAbsolutePath();
        libPath = lib.getAbsolutePath();
        sourceDexPath = dex.getAbsolutePath() + File.separator + "Source.apk";

        log("oDexPath: " + oDexPath);
        log("libPath: " + libPath);
        log("sourceDexPath: " + sourceDexPath);

        // 2. 根据文件路径创建File对象
        File apkFile = new File(sourceDexPath);
        // 只有首次运行时需要创建相关文件
        if (!apkFile.exists()) {
            // 根据路径创建文件
            apkFile.createNewFile();

            // 3. 读取Classes.dex文件
            byte[] shellDexData = readDexFromApk();
            if (shellDexData == null) {
                log("Failed to read dex from APK");
                return false;
            }

            // 4. 从中分离出源apk文件
            if (!extractSrcApkFromShellDex(shellDexData)) {
                log("Failed to extract source APK from shell dex");
                return false;
            }
        }

        return true;

    } catch (Exception e) {
        log("Error in extractSourceApk: " + Log.getStackTraceString(e));
        return false;
    }
}
```

然后分离他们出来放到对应目录，最后通过构建他们的dexclassLoader来加载真正的源程序代码，最后替换当前应用的classLoader为我们新创建的用来加载源程序dex的。

```
/**
 * 替换壳App的ClassLoader为源App的ClassLoader
 */
private boolean replaceClassLoader() {
    try {
        // 1. 获取当前的classloader
        ClassLoader classLoader = this.getClassLoader();
        log("Current ClassLoader: " + classLoader.toString());

        // 2. 反射获取ActivityThread
        Object sCurrentActivityThreadObj = Reflection.getStaticField("android.app.ActivityThread", "sCurrentActivityThread");
        if (sCurrentActivityThreadObj == null) {
            log("Failed to get ActivityThread");
            return false;
        }

        // 3. 反射获取LoadedApk
        ArrayMap mPackagesObj = (ArrayMap) Reflection.getField("android.app.ActivityThread", sCurrentActivityThreadObj, "mPackages");
        if (mPackagesObj == null) {
            log("Failed to get mPackages");
            return false;
        }

        String currentPackageName = this.getPackageName();
        WeakReference weakReference = (WeakReference) mPackagesObj.get(currentPackageName);
        if (weakReference == null) {
            log("Failed to get WeakReference for package: " + currentPackageName);
            return false;
        }

        Object loadedApkObj = weakReference.get();
        if (loadedApkObj == null) {
            log("Failed to get LoadedApk from WeakReference");
            return false;
        }

        // 4. 替换ClassLoader
        DexClassLoader dexClassLoader = new DexClassLoader(sourceDexPath, oDexPath, libPath, classLoader.getParent());
        Reflection.setField("android.app.LoadedApk", "mClassLoader", loadedApkObj, dexClassLoader);
        
        log("Successfully replaced ClassLoader with: " + dexClassLoader);
        return true;

    } catch (Exception e) {
        log("Error replacing ClassLoader: " + Log.getStackTraceString(e));
        return false;
    }
}
```

```
 DexClassLoader dexClassLoader = new DexClassLoader(sourceDexPath, oDexPath, libPath, classLoader.getParent());
```

这个就是前面文章重点介绍的
 [Android ClassLoader 重点解析](https://juejin.cn/post/7523509642178347018 "https://juejin.cn/post/7523509642178347018")

##### 4.3.2 落地加载的安全性缺失

1、源程序的dex被加密放在壳的dex后面，通过root机就能直接拿到喊加密后的源apk

2、运行时解密出来了源程序的dex，放在了本地路径

```
data/user/0/<package_name>/app_tmp_dex
```

使用这个路径去构建加载源程序dex的classLoader

#### 5 不落地加载方案

**由于第一代落地加载方案的弊端，由此引发了不落地加载的方案，这将在下一篇[Android第二代加固技术原理详解（附源码）](https://juejin.cn/post/7589935326781669410 "https://juejin.cn/post/7589935326781669410")讲解，如感兴趣，建议关注收藏。**

**InMemoryDexClassLoader将是下篇文章的重点，建议重点回看 [Android ClassLoader 重点解析](https://juejin.cn/post/7523509642178347018 "https://juejin.cn/post/7523509642178347018")**
