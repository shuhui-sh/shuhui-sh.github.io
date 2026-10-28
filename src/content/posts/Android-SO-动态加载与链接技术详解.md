---
title: "Android SO 动态加载与链接技术详解"
date: 2026-06-01
description: "Android 系统中，C/C++ 代码编译为 .so（Shared Object）文件，供 Java 层通过 JNI 调用。"
tags: ['Android']
category: "技术"
---
> 从 Java 层 `System.loadLibrary` 到底层 ELF 链接器，系统梳理 Android 原生库（SO）的加载、链接与动态化方案。

---

## 一、概述

Android 系统中，C/C++ 代码编译为 `.so`（Shared Object）文件，供 Java 层通过 JNI 调用。与平台无关的 DEX 字节码不同，SO 文件是**架构相关的 ELF 格式二进制**，其加载过程涉及操作系统动态链接器的完整参与。

动态 SO 加载在以下场景中至关重要：

- **插件化**：插件携带自己的 native 库，需要与宿主 SO 隔离
- **热修复**：线上 native 代码出现 Bug 时，下发 SO 补丁修复
- **按需加载**：大型游戏/应用按需下载特定架构的 native 模块
- **SO 加固/加壳**：逆向保护，运行时解密并加载隐藏的 SO

---

## 二、两种 Java 层 SO 加载入口

### 2.1 `System.loadLibrary(String libName)`

接收**短名称**（如 `"foo"`，系统自动映射为 `libfoo.so`），通过 ClassLoader 在已注册的 native 库搜索路径中查找：

```java
// 仅传库名，由 ClassLoader 负责搜索
System.loadLibrary("foo");
```

### 2.2 `System.load(String path)`

接收**完整文件路径**，直接加载指定位置的 SO 文件，不经过 ClassLoader 搜索：

```java
// 传入完整路径，直接加载
System.load("/data/data/com.example/app_libs/libfoo.so");
```

### 2.3 关键差异

| 特性 | `System.loadLibrary` | `System.load` |
|------|----------------------|---------------|
| 参数格式 | 短名（`foo` → `libfoo.so`） | 完整绝对路径 |
| ClassLoader 关联 | 关联调用者的 ClassLoader | 不关联 |
| Linker Namespace | 使用 classloader-namespace，受隔离保护 | 使用默认 namespace，无隔离 |
| 安全性 | 较高（namespace 约束） | 较低（可绕过隔离） |
| ABI 过滤 | 自动按设备 ABI 选取 | 需手动判断架构 |

---

## 三、正常加载流程：从 Java 到底层 Linker

### 3.1 完整调用链

```
System.loadLibrary("foo")
  │
  └─ Runtime.loadLibrary0("foo", classLoader, callerClass)
       │
       ├─ ClassLoader.findLibrary("foo")         // ← Java 层路径查找
       │    └─ DexPathList.findLibrary("foo")
       │         └─ 遍历 nativeLibraryPathElements[]
       │              └─ 返回 /data/app/.../lib/arm64/libfoo.so
       │
       └─ Runtime.nativeLoad(path, classLoader, callerClass)  // JNI
            │
            └─ Runtime_nativeLoad()              // Runtime.c
                 │
                 └─ JVM_NativeLoad()
                      │
                      └─ art::JavaVMExt::LoadNativeLibrary()
                           │
                           └─ android::OpenNativeLibrary()
                                │
                                ├─ classLoader == NULL?
                                │   ├─ 是 → dlopen(path, RTLD_NOW)   // System.load 路径
                                │   └─ 否 → android_dlopen_ext(...)  // System.loadLibrary 路径
                                │
                                └─ linker 执行实际的 ELF 装载、解析与链接
```

### 3.2 ClassLoader 搜索路径机制

`DexPathList.findLibrary()` 负责在 native 库目录列表中查找 SO 文件：

```java
// BaseDexClassLoader 内部结构
public class BaseDexClassLoader extends ClassLoader {
    private final DexPathList pathList;
}

final class DexPathList {
    private Element[] dexElements;
    // SDK < 23: File[] nativeLibraryDirectories
    // SDK >= 23: Element[] nativeLibraryPathElements
    private Element[] nativeLibraryPathElements;
}
```

不同 SDK 版本的查找实现：

- **SDK < 23**：遍历 `nativeLibraryDirectories`（`File[]`），匹配文件名
- **SDK >= 23**：遍历 `nativeLibraryPathElements`（`Element[]`），依次在每个 Element 对应的目录中搜索

---

## 四、Linker 层：ELF 装载与动态链接

当 `dlopen()` / `android_dlopen_ext()` 被调用后，真正的工作由 Bionic Linker（`bionic/linker/linker.cpp`）完成。整个过程分为 **7 个阶段**。

### 4.1 ELF 文件速览

```
ELF 文件结构
├── ELF Header           （文件类型、目标架构、入口地址）
├── Program Header Table （运行时必需：PT_LOAD 段描述、PT_DYNAMIC 位置）
├── .text                （代码段，r-x）
├── .rodata              （只读数据）
├── .data                （可读写数据，rw-）
├── .dynamic             （动态链接元信息，核心段）
│   ├── DT_NEEDED        依赖的 SO 列表
│   ├── DT_SONAME        自身的规范名称
│   ├── DT_SYMTAB       符号表 (.dynsym)
│   ├── DT_STRTAB       字符串表 (.dynstr)
│   ├── DT_HASH / DT_GNU_HASH  符号哈希表
│   ├── DT_JMPREL       PLT 重定位表 (.rel.plt)
│   ├── DT_REL / DT_RELA 普通重定位表 (.rel.dyn)
│   ├── DT_INIT / DT_FINI / DT_INIT_ARRAY / DT_FINI_ARRAY
│   └── DT_NEEDED...
├── .dynsym              （动态符号表）
├── .dynstr              （符号名字符串表）
├── .rel.dyn             （数据重定位表）
├── .rel.plt             （函数重定位表）
├── .plt                 （过程链接表）
├── .got / .got.plt      （全局偏移表）
└── Section Header Table （链接阶段使用，运行时可选）
```

### 4.2 阶段 0—准备：创建加载任务

```cpp
// linker.cpp — find_libraries
// 根据传入的 so 名称数组，初始化 load_tasks 列表
```

### 4.3 阶段 1—扩展：递归加载依赖

```cpp
// 对每个待加载的 SO：
// 1. 在 namespace 中搜索文件路径
// 2. 解析 DT_NEEDED 条目，递归将依赖 SO 加入加载队列
// 3. 去重：已加载的 SO 不重复处理
```

`DT_NEEDED` 的递归解析示例：

```
libfoo.so 依赖:
  ├── DT_NEEDED: libc.so       → 系统库，已加载，跳过
  ├── DT_NEEDED: libbar.so     → 未加载，递归查找并加入队列
  │     └── DT_NEEDED: libbaz.so → 未加载，递归查找
  └── DT_NEEDED: liblog.so     → 系统库，已加载，跳过
```

### 4.4 阶段 2—装载：mmap 映射内存

```cpp
// ElfReader 负责 ELF 文件的读取和映射
ElfReader::Load():
  1. ReadElfHeader()      // 校验魔数、位数、字节序、架构
  2. ReadProgramHeader()  // 解析 Program Header Table
  3. 计算 load_size 和 load_bias
  4. ReserveAligned()     // 预留连续的地址空间
  5. LoadSegments():      // 用 mmap 将各 PT_LOAD 段映射到内存
     ├── .text  → mmap(PROT_READ | PROT_EXEC)  // 代码段：可读可执行
     └── .data  → mmap(PROT_READ | PROT_WRITE) // 数据段：可读可写
```

**关键概念 `load_bias`**：

```
load_bias = 实际映射基地址 - ELF 文件中声明的 p_vaddr

所有对 ELF 内地址的引用都需要加上 load_bias 得到运行时地址：
runtime_addr = elf_vaddr + load_bias
```

### 4.5 阶段 3—预链接：解析 .dynamic 段

```cpp
// soinfo_link_image() — 遍历 .dynamic 段的所有 DT_* 条目
for (d = si->dynamic; d->d_tag != DT_NULL; ++d) {
    switch (d->d_tag) {
        case DT_SYMTAB:   si->symtab  = base + d->d_un.d_ptr; break;
        case DT_STRTAB:   si->strtab  = base + d->d_un.d_ptr; break;
        case DT_HASH:     解析 ELF hash 表; break;
        case DT_GNU_HASH: 解析 GNU hash 表; break;
        case DT_JMPREL:   si->plt_rel = base + d->d_un.d_ptr; break;
        case DT_PLTRELSZ: si->plt_rel_count = d->d_un.d_val; break;
        case DT_REL:      si->rel = base + d->d_un.d_ptr; break;
        case DT_RELSZ:    si->rel_count = d->d_un.d_val; break;
        case DT_NEEDED:   记录依赖 SO 名称，稍后递归加载; break;
        case DT_SONAME:   记录自身规范名称; break;
        case DT_INIT:     si->init_func = base + d->d_un.d_ptr; break;
        case DT_INIT_ARRAY / DT_FINI_ARRAY: ...; break;
    }
}
```

### 4.6 阶段 4-5：LD_PRELOAD 与依赖分组

- **LD_PRELOAD**：强制设置预加载库的 `DF_1_GLOBAL` 标志，使其符号优先于其他库被找到
- **依赖分组**：按 `DT_NEEDED` 关系构建符号查找的 `local_group`（同一命名空间内可见的 SO 集合）

### 4.7 阶段 6—链接：符号解析与重定位（核心）

这是动态链接最核心的步骤，由 `soinfo_relocate()` 完成。

**两步重定位**：

| 重定位表 | 对应段 | Dynamic Tag | 重定位类型 | 用途 |
|----------|--------|-------------|------------|------|
| PLT 重定位 | `.rel.plt` | `DT_JMPREL` | `R_*_JUMP_SLOT` | 函数调用（跨 SO 跳转） |
| 普通重定位 | `.rel.dyn` | `DT_REL`/`DT_RELA` | `R_*_GLOB_DAT` / `R_*_ABS32` / `R_*_RELATIVE` | 全局变量、内部地址修正 |

**单个重定位项的處理**：

```
对于每个 Elf_Rel 条目:

Step 1 — 解析
  type  = ELF_R_TYPE(rel->r_info)    // 重定位类型（低 8 位）
  sym   = ELF_R_SYM(rel->r_info)     // 符号表索引（高 24 位）
  addr  = si->load_bias + rel->r_offset  // 目标修正地址

Step 2 — 查找符号 (sym != 0 时)
  sym_name = si->strtab + si->symtab[sym].st_name   // 取函数名
  s = soinfo_do_lookup(si, sym_name, &found_in)     // 在依赖中搜索
  sym_addr = s->st_value + found_in->load_bias      // 运行时地址

Step 3 — 按类型修正
  根据 type 的值:
  ├── R_ARM_JUMP_SLOT  / R_AARCH64_JUMP_SLOT:
  │     *addr = sym_addr                             // PLT.GOT 项写入真实地址
  ├── R_ARM_GLOB_DAT   / R_AARCH64_GLOB_DAT:
  │     *addr = sym_addr                             // GOT 项写入真实地址
  ├── R_ARM_ABS32      / R_AARCH64_ABS64:
  │     *addr += sym_addr                            // 绝对地址修正
  ├── R_ARM_RELATIVE   / R_AARCH64_RELATIVE:
  │     *addr += si->base                            // 内部地址基址修正
  └── ...
```

### 4.8 PLT / GOT 工作原理

**重定位前**：

```
代码调用:                    PLT 桩:                     GOT.PLT:
bl printf@plt ──────►  printf@plt:              GOT[printf]:
                       adrp x16, GOT[printf]    ──► 指向 PLT 桩的下一条指令
                       ldr  x17, [x16]              （待链接器修正）
                       br   x17
```

**重定位后**（Android 立即绑定）：

```
代码调用:                    PLT 桩:                     GOT.PLT:
bl printf@plt ──────►  printf@plt:              GOT[printf]:
                       adrp x16, GOT[printf]    ══► &printf (真实地址)
                       ldr  x17, [x16]
                       br   x17 ───────────────► libc.so 中的 printf()
```

### 4.9 Android 不支持真正的 Lazy Binding

Android Bionic 明确注释：

```c
#define RTLD_LAZY  0x00001   // Not supported on Android.
                              // Android always uses RTLD_NOW for security.
```

**原因**：重定位后立即通过 `mprotect()` 将 GOT/PLT 所在的 `PT_GNU_RELRO` 段设为只读，防止 GOT 覆盖劫持。若允许延迟绑定，GOT 需保持可写，无法应用 RELRO 保护。

### 4.10 阶段 7—收尾与构造函数

```cpp
// 1. 标记所有任务为已链接
// 2. 保护 RELRO 区域：mprotect(PT_GNU_RELRO, PROT_READ)
// 3. 执行构造函数：
//    a. 递归执行所有依赖 SO 的构造函数
//    b. 执行 DT_INIT 指定的函数
//    c. 执行 DT_INIT_ARRAY[] 数组中的所有函数
// 4. 返回 soinfo 句柄
```

### 4.11 `android_dlopen_ext` — Android 扩展加载接口

Android 在 `<android/dlext.h>` 中提供了 `dlopen` 的增强版本，支持命名空间、文件描述符加载等高级特性：

```c
void* android_dlopen_ext(const char* filename, int flags,
                         const android_dlextinfo* extinfo);
```

`android_dlextinfo` 结构体的关键标志位：

| 标志 | 值 | 用途 |
|------|-----|------|
| `ANDROID_DLEXT_USE_NAMESPACE` | `0x200` | 在指定命名空间中加载（`library_namespace` 字段） |
| `ANDROID_DLEXT_USE_LIBRARY_FD` | `0x10` | 通过文件描述符加载，而非文件名 |
| `ANDROID_DLEXT_USE_LIBRARY_FD_OFFSET` | `0x20` | 从 fd 的指定偏移开始读取（从 ZIP 等归档内加载） |
| `ANDROID_DLEXT_FORCE_LOAD` | `0x40` | 跳过 `stat` 检查，强制加载（即使 soinfo 存在） |
| `ANDROID_DLEXT_WRITE_RELRO` / `ANDROID_DLEXT_USE_RELRO` | `0x4` / `0x8` | RELRO 段共享复用（主要用于 Chromium WebView） |

**`System.loadLibrary` 内部用的正是 `android_dlopen_ext`**：

```cpp
// OpenNativeLibrary 中的分支
if (class_loader != nullptr) {
    // System.loadLibrary 路径：通过 namespace 加载
    NativeLoaderNamespace* ns = FindNamespaceByClassLoader(env, class_loader);
    android_dlextinfo extinfo;
    extinfo.flags = ANDROID_DLEXT_USE_NAMESPACE;
    extinfo.library_namespace = ns;
    return android_dlopen_ext(path, RTLD_NOW, &extinfo);
} else {
    // System.load 路径：直接 dlopen，无 namespace 隔离
    return dlopen(path, RTLD_NOW);
}
```

### 4.12 `linkerconfig` 与 `ld.config.txt` — 命名空间配置生成

Android 10+ 通过 `linkerconfig` 程序在每次启动时动态生成 linker 命名空间配置文件。其输入来源包括：

- `/system/etc/public.libraries.txt` — 系统公开库列表
- APEX 模块的 `linker.config.json` — APEX 模块声明的依赖
- VNDK 版本信息（`ro.vndk.version`）

生成的 `ld.config.txt` 格式示例：

```ini
[system]
additional.namespaces = sphal,vndk

namespace.default.isolated = true
namespace.default.search.paths = /system/${LIB}:/system/${LIB}/hw
namespace.default.permitted.paths = /system/${LIB}:/system/${LIB}/hw

namespace.sphal.isolated = true
namespace.sphal.search.paths = /odm/${LIB}:/vendor/${LIB}
namespace.sphal.links = default,vndk
namespace.sphal.link.default.shared_libs = libc.so:libm.so:libdl.so
```

三种命名空间隔离模式（由 `BOARD_VNDK_VERSION` 决定）：

| 模式 | 说明 |
|------|------|
| VNDK（完全隔离） | system 和 vendor 命名空间完全隔离，仅通过 links 暴露白名单库 |
| VNDK Lite | 轻量级，允许 vendor 直接访问 system 空间（适用于低内存设备） |
| Legacy | 无隔离，兼容旧设备 |

---

## 五、Linker Namespace 隔离机制

### 5.1 设计目标

Android 7.0+ 引入 Linker Namespace，核心解决两个问题：

- **符号隔离**：不同来源的 SO（如 `system` 和 `vendor`）即使同名，也能被加载到不同 namespace 中互不干扰
- **运行时依赖可见性控制**：一个 namespace 内的 SO 无法随意链接另一个 namespace 内的符号

### 5.2 与 ClassLoader 的绑定关系

```
每个 ClassLoader 实例
  └── 对应一个 Linker Namespace（classloader-namespace）
        ├── 搜索路径：/data/app/<pkg>/lib/arm64
        ├── 允许链接的系统库：/system/etc/public.libraries.txt 中列出的
        └── 不允许链接：framework 私有库（如 libart.so、libgui.so）
```

**命名约定**：classloader-namespace 的格式为 `clns-<数字>`。

### 5.3 不同 APK 类型的访问权限

| APK 类型 | 可访问的系统库范围 |
|----------|-------------------|
| 非捆绑式（下载/更新 APK） | 仅 `/system/etc/public.libraries.txt` 中列出的公共库 |
| 捆绑式（系统预置 APK） | `/system/lib` 下所有库 |
| vendor/product 分区的非捆绑式应用 | 额外可访问 VNDK-SP 库 |

### 5.4 对动态加载的影响

- **正向**：为每个插件创建独立 ClassLoader 时，系统自动分配独立 Namespace，天然 SO 隔离
- **负面**：仅反射注入路径而不创建新 ClassLoader 时，Linker 的 Namespace 不会感知新增路径，导致"当前 SO 能找到，但依赖的 SO 找不到"

---

## 六、SO 动态加载的工程方案

### 6.1 插件化：SO 库隔离

插件化框架需要让多个插件的 native 库共存。三种主流隔离方案：

#### 方案 A：独立 ClassLoader（推荐 — Shadow 方案）

为每个插件创建独立的 `PluginClassLoader`（继承 `BaseDexClassLoader`），传入插件专属 SO 目录作为 `librarySearchPath`：

```java
// Shadow 的实现方式
PluginClassLoader(
    dexPath,        // 插件 APK 路径
    odexDir,        // dex 优化输出目录
    libDir,         // 插件专属 SO 目录 ← 关键
    parent          // 父 ClassLoader，用于访问宿主类
);

// SO 目录结构
// /data/user/0/<host>/files/ShadowPluginManager/
//   UnpackedPlugin/
//     plugin_a/lib/arm64/libnative_a.so
//     plugin_b/lib/arm64/libnative_b.so
```

优势：系统 Linker Namespace 机制自动隔离；不同插件的同名 SO 互不干扰。

#### 方案 B：反射注入 nativeLibraryPathElements

通过反射将插件 SO 路径插入 ClassLoader 的 SO 搜索路径数组头部：

```java
// SDK >= 23
Field pathListField = BaseDexClassLoader.class.getDeclaredField("pathList");
pathListField.setAccessible(true);
Object pathList = pathListField.get(classLoader);

Field elementsField = pathList.getClass().getDeclaredField("nativeLibraryPathElements");
elementsField.setAccessible(true);
Object[] elements = (Object[]) elementsField.get(pathList);

// 构造补丁 Element 并插入最前面
Constructor<?> ctor = Element.class.getDeclaredConstructor(
    File.class, boolean.class, File.class, DexFile.class);
ctor.setAccessible(true);
Object patchElement = ctor.newInstance(new File(patchSoDir), true, null, null);

Object[] newElements = new Object[elements.length + 1];
newElements[0] = patchElement;
System.arraycopy(elements, 0, newElements, 1, elements.length);
elementsField.set(pathList, newElements);
```

代价：Linker Namespace 不会感知新增路径；多线程加载时存在并发风险。

#### 方案 C：System.load 全路径加载

```java
// 1. 从 APK 中提取 SO 到私有目录
File targetSo = new File(context.getFilesDir(), "plugin_libs/libfoo.so");
// 将 APK 内的 lib/arm64-v8a/libfoo.so 拷贝至 targetSo

// 2. 使用全路径加载
System.load(targetSo.getAbsolutePath());
```

适合依赖链简单的轻量场景。对于依赖链复杂的 SO，可借助 Facebook 的 SoLoader 或 Relinker 解析 ELF 的 `DT_NEEDED` 并递归加载。

### 6.2 热修复：SO 补丁替换

SO 热修复的核心是**让 `System.loadLibrary` 优先找到补丁 SO**。业界有两种主流实现路径。

#### 路径一：反射注入搜索路径（Sophix 风格，推荐）

直接通过反射修改 ClassLoader 内部的 SO 搜索路径数组，对上层调用完全透明，第三方 SO 也能被修复。

**SDK < 23 — 注入 `nativeLibraryDirectories`（`File[]`）**：

```java
public static void injectSoPathBelow23(ClassLoader classLoader, File patchSoDir) 
        throws Exception {
    // 1. 获取 BaseDexClassLoader 的 pathList
    Field pathListField = findField(classLoader, "pathList");
    Object pathList = pathListField.get(classLoader);

    // 2. 获取 DexPathList.nativeLibraryDirectories (File[])
    Field nativeLibDirField = findField(pathList, "nativeLibraryDirectories");
    File[] origDirs = (File[]) nativeLibDirField.get(pathList);

    // 3. 构建新数组：补丁路径插入最前面
    List<File> newDirList = new ArrayList<>(Arrays.asList(origDirs));
    newDirList.add(0, patchSoDir);

    // 4. 反射写回
    nativeLibDirField.set(pathList, newDirList.toArray(new File[0]));
}
```

**SDK >= 23 — 注入 `nativeLibraryPathElements`（`Element[]`）**：

```java
public static void injectSoPathAbove23(ClassLoader classLoader, File patchSoDir) 
        throws Exception {
    Field pathListField = findField(classLoader, "pathList");
    Object pathList = pathListField.get(classLoader);

    // 获取 nativeLibraryPathElements (DexPathList.Element[])
    Field elementsField = findField(pathList, "nativeLibraryPathElements");
    Object[] origElements = (Object[]) elementsField.get(pathList);

    // 获取 DexPathList$Element 类
    Class<?> elementClass = Class.forName("dalvik.system.DexPathList$Element");

    // 构造补丁 Element（适配不同 API Level 的构造函数差异）
    Constructor<?> ctor = elementClass.getDeclaredConstructor(
        File.class, boolean.class, File.class, DexFile.class);
    ctor.setAccessible(true);
    Object patchElement = ctor.newInstance(patchSoDir, true, null, null);

    // 插入最前面
    Object[] newElements = (Object[]) Array.newInstance(
        elementClass, origElements.length + 1);
    newElements[0] = patchElement;
    System.arraycopy(origElements, 0, newElements, 1, origElements.length);

    elementsField.set(pathList, newElements);
}

// 递归查找字段（含父类链）
private static Field findField(Object obj, String fieldName) 
        throws NoSuchFieldException {
    for (Class<?> clazz = obj.getClass(); clazz != null; clazz = clazz.getSuperclass()) {
        try {
            Field f = clazz.getDeclaredField(fieldName);
            f.setAccessible(true);
            return f;
        } catch (NoSuchFieldException ignored) {}
    }
    throw new NoSuchFieldException(fieldName);
}
```

#### 路径二：接口调用替换（Tinker 风格）

用自定义方法包裹 `System.loadLibrary`，从补丁目录加载：

```java
public class TinkerLoadLibrary {
    public static void loadLibrary(String libName) {
        // 1. 优先从补丁包加载
        File patchSo = new File(getPatchSoDir(), System.mapLibraryName(libName));
        if (patchSo.exists()) {
            System.load(patchSo.getAbsolutePath());
            return;
        }
        // 2. 回退到系统加载
        System.loadLibrary(libName);
    }
}
```

#### 两种路径对比

| 维度 | 反射注入（Sophix） | 接口替换（Tinker） |
|------|-------------------|-------------------|
| 业务代码侵入 | 无侵入，上层透明 | 需替换所有 `System.loadLibrary` 调用 |
| 第三方 SO 修复 | 支持（修改了系统搜索路径） | 不支持（第三方内部调用无法拦截） |
| 版本兼容 | 需持续适配 SDK 变化 | 相对稳定 |
| 适用场景 | 通用热修复平台 | 自有代码的 native 库修复 |

**通用限制**：两种路径都必须**冷启动生效**。因为 SO 一旦加载就驻留在进程地址空间，`dlclose()` 并未真正卸载（Android 不支持安全运行时 SO 卸载）。

### 6.3 加固/加壳：SO 隐藏与运行时解密

保护 SO 不被静态分析的技术路线：

```
编译阶段:
  libfoo.so ──加密──► libfoo_encrypted.so ──替换──► APK 内

运行阶段:
  System.loadLibrary("foo") 
    └─ JNI_OnLoad() 
         └─ 解密 → /data/data/<pkg>/app_libs/libfoo_real.so
              └─ System.load("/data/data/<pkg>/app_libs/libfoo_real.so")
```

借助 Linker 的 `soinfo_do_lookup` 和 PLT 重定位机制，解壳后的 SO 可以透明地被其他模块调用。

### 6.4 Play Feature Delivery — 官方按需分发

Google 通过 App Bundle 提供的官方方案：

```java
// 按需下载 Feature Module（包含 native 库）
SplitInstallManager manager = SplitInstallManagerFactory.create(context);
SplitInstallRequest request = new SplitInstallRequest.Builder()
    .addModule("feature_native")
    .build();

manager.startInstall(request)
    .addOnSuccessListener(sessionId -> {
        // 模块下载完成，System.loadLibrary() 即可正常加载模块中的 SO
    });
```

**局限**：必须通过 Google Play 分发，国内环境不可用。

---

## 七、SO 加载相关的重要系统属性

### 7.1 `android:extractNativeLibs`

| 设置 | 行为 | 存储影响 | 加载性能 |
|------|------|----------|----------|
| `true`（默认） | 安装时将 SO 从 APK 解压到 `/data/app/` | 双份存储（APK 内 + 解压后） | 正常 |
| `false` | 直接从 APK（ZIP）内 mmap 加载 | 仅 APK 一份 | 需满足页对齐要求 |

```xml
<application android:extractNativeLibs="false" ...>
```

`extractNativeLibs="false"` 的技术前提：
- SO 文件必须以**未压缩（Store）**方式存储在 APK 中
- SO 文件必须经过 **`zipalign -p 4`** 进行 4096 字节页对齐
- Android 6.0+ 支持直接从 APK 加载

### 7.2 ABI 选择机制

系统根据 `Build.SUPPORTED_ABIS`（优先级排序的架构列表）自动选取最佳 SO 变体：

```java
// 典型的 SUPPORTED_ABIS
// arm64-v8a 设备:    ["arm64-v8a", "armeabi-v7a", "armeabi"]
// x86_64 设备:       ["x86_64", "x86"]
// 64 位优先，其次回退到 32 位
```

**关键约束**：SoLoader/Relinker 等第三方方案同样依赖此机制；可借助 `readelf -A` 检测 SO 的 Arm 特性（如 MTE、BTI）在运行时是否被内核支持。

---

## 八、常见问题与排障指南

| 问题 | 原因 | 解决 |
|------|------|------|
| `UnsatisfiedLinkError: dlopen failed: library "xxx" not found` | SO 不在搜索路径中；依赖的 SO 缺失或位于不可见的 namespace | 检查 `nativeLibraryDirectories`；用 `readelf -d lib.so \| grep NEEDED` 检查依赖 |
| `dlopen failed: cannot locate symbol "xxx"` | 符号在依赖链中找不到；Android 版本不兼容（如 `android_set_abort_message` 从 API 21 推迟至 API 30） | 用 `readelf -s lib.so` 检查缺失符号；查阅 NDK API Level 引入记录 |
| `UnsatisfiedLinkError: dlopen failed: library "libc++_shared.so" not found` | 未包含 C++ STL 共享库 | 添加 `-DANDROID_STL=c++_shared`；或用静态链接 `c++_static` |
| 加固/混淆后 SO 无法加载 | ELF 头或 Program Header 被损坏 | 确保混淆工具跳过 SO 文件，或使用 `extractNativeLibs=false` |
| `UnsatisfiedLinkError: Bad JNI version` 或 `No JNI_OnLoad found` | 加载了不包含 JNI 符号的普通库；或 JNI 函数签名不匹配 | 确认 SO 导出了 `JNI_OnLoad`；用 `readelf -sW lib.so \| grep JNI` 检查 |
| 32 位和 64 位 SO 混用 | 32 位进程不能加载 64 位 SO，反之亦然 | 确保 `libs/` 目录包含与目标 ABI 一致的 SO |
| 不同模块引入同名 SO 版本冲突 | Gradle 打包进了多个同名 SO | 使用 `pickFirst` 或在模块级别 `exclude` |
| `NS linker` 相关错误 | Android 7.0+ 的 namespace 隔离拦截了跨 namespace 符号解析 | 检查是否使用了错误的 ClassLoader；在 Android 11+ 改用 `ResourcesLoader` API |

---

## 九、技术选型建议

```
需要 SO 隔离？
├── 是
│   ├── 插件化（多个插件，需各自独立命名空间）
│   │   └── Shadow 独立 ClassLoader 方案（推荐）
│   ├── 热修复（单个补丁，覆盖原 SO）
│   │   └── 反射注入 nativeLibraryPathElements + 冷启
│   └── 轻量场景（少量 SO，依赖简单）
│       └── System.load 全路径 + SoLoader 递归依赖
└── 否（宿主自身 SO，按需分发）
    ├── 通过 Google Play 分发
    │   └── App Bundle + Play Feature Delivery
    └── 自有渠道
        └── 私有目录提取后 System.load
```

---

## 十、最佳实践清单

1. **首选 System.loadLibrary**：利用 Linker Namespace 隔离，安全性更高
2. **每个插件独立 ClassLoader**：利用系统 Namespace 机制实现 SO 天然隔离
3. **考虑 `extractNativeLibs=false`**：Android 6.0+ 可直接从 APK 加载，节省磁盘空间
4. **处理 SO 依赖链**：用 `readelf -d` 分析 DT_NEEDED，用 SoLoader 递归加载
5. **C++ STL 静态链接**：避免 `libc++_shared.so` 版本冲突
6. **签名校验**：动态下发的 SO 包必须做完整性校验，防止篡改
7. **架构匹配**：确保下发的 SO 与目标设备 ABI 一致
8. **冷启动生效**：热修复场景中，SO 已由旧代码加载则无法实时替换，需引导用户重启
9. **ABI 降级方案**：对不支持新硬件特性的旧设备提供无 MTE/BTI 的备选 SO

---

## 十一、技术演进总结

```
2014 之前             2014 - 2017            2017 - 2021              2021 - 至今
基础 JNI             热修复/插件化爆发       系统安全强化               平台原生化
────────────────────────────────────────────────────────────────────────────────
                     反射篡改                 Linker Namespace          ResourcesLoader
System.loadLibrary   nativeLibraryDir        android_dlopen_ext        extractNativeLibs
System.load          路径注入                 非 SDK 接口限制            =false
                     插件 ClassLoader         签名校验增强               Play Feature
                     隔离雏形                 VNDK 隔离                 Delivery
```

---

*参考来源：Android Developers 官方文档、AOSP（android.googlesource.com）— bionic/linker、libnativeloader、腾讯 Shadow 开源项目、阿里 Sophix 技术文档、Facebook SoLoader。*
