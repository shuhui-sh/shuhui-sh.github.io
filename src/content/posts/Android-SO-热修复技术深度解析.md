---
title: "Android SO 热修复技术深度解析"
date: 2026-06-01
description: "SO 热修复与 Java 热修复有一个根本性差异： 结论：dlclose 调用后，SO 的代码段和数据段依然在进程地址空间中，所有已解析的 GOT/PLT 依然指向旧 SO 的地址。"
tags: ['Android']
category: "技术"
---
> 聚焦 DT_NEEDED 依赖链、Linker Namespace 隔离与工程对抗方案。

---

## 一、核心矛盾：SO 的"不可卸载"特性

SO 热修复与 Java 热修复有一个根本性差异：

```
Java 热修复：ClassLoader 可以重新加载一个 Class（新的 dexElement 插入头部即可）
SO 热修复：  dlopen 后的 SO 永远驻留在进程空间，dlclose 只是递减引用计数
```

### 1.1 `dlclose` 的真实行为

```cpp
// bionic/linker/linker.cpp — dlclose 的简化逻辑
int dlclose(void* handle) {
    soinfo* si = reinterpret_cast<soinfo*>(handle);
    
    // 仅递减引用计数
    si->decrement_ref_count();
    
    if (si->get_ref_count() == 0) {
        // 调用 .fini_array 析构函数
        si->call_destructors();
        // 从 soinfo 链表中移除
        si->remove_from_solist();
        // ⚠️ 但 mmap 的内存并未 munmap！
        // soinfo 结构体未被释放！
    }
    return 0;
}
```

**结论**：`dlclose` 调用后，SO 的代码段和数据段依然在进程地址空间中，所有已解析的 GOT/PLT 依然指向旧 SO 的地址。下一次 `dlopen("libfoo.so")` 时，linker 会复用已有的 `soinfo`。

### 1.2 Android 8.0+ 的加重限制

```
"Shared library /data/app/.../lib/arm/libfoo.so already opened by 
 ClassLoader 0x2b7; can't open in ClassLoader 0xff912a74"
```

从 Android 8.0（API 26）开始，linker 记录每个 SO 被哪个 ClassLoader 首次打开。同一个 SO 不能被不同的 ClassLoader 重复加载——这对插件化/热修复场景是雪上加霜。

---

## 二、DT_NEEDED 依赖链：看不见的"锁链"

### 2.1 DT_NEEDED 是什么

每个 SO 的 `.dynamic` 段中包含若干 `DT_NEEDED` 条目，声明该 SO 依赖的其他共享库：

```bash
$ aarch64-linux-android-readelf -d libfoo.so | grep NEEDED
 0x00000001 (NEEDED)   Shared library: [libc++_shared.so]
 0x00000001 (NEEDED)   Shared library: [liblog.so]
 0x00000001 (NEEDED)   Shared library: [libc.so]
 0x00000001 (NEEDED)   Shared library: [libm.so]
 0x00000001 (NEEDED)   Shared library: [libdl.so]
```

### 2.2 Linker 如何解析 DT_NEEDED

Linker 在 `find_libraries()` 中递归展开依赖图（BFS 遍历）：

```cpp
// bionic/linker/linker.cpp — 简化逻辑
bool find_libraries(android_namespace_t* ns, soinfo* start_si,
                    const char* const library_names[],
                    std::vector<soinfo*>* load_tasks) {
    
    // Step 1: 将初始 SO 加入队列
    // Step 2: BFS 遍历 — 对队列中每个 SO：
    for (size_t i = 0; i < load_tasks->size(); ++i) {
        soinfo* si = (*load_tasks)[i];
        
        // 遍历 DT_NEEDED 条目
        for_each_dt_needed(si, [&](const char* needed_name) {
            // 在当前 namespace 中查找依赖 SO
            soinfo* needed_si = find_library_internal(
                ns, needed_name, ...);
            
            if (needed_si == nullptr) {
                // ❌ 依赖 SO 找不到 → dlopen 失败
                return false;
            }
            
            if (!needed_si->is_linked()) {
                // 未链接的依赖加入处理队列
                load_tasks->push_back(needed_si);
            }
        });
    }
    // ...
}
```

**关键行为**：

```
对每个 DT_NEEDED 条目，linker 执行：
1. 检查是否已加载（find_loaded_library_by_soname）
2. 若已加载 → 复用现有 soinfo（无论版本！）
3. 若未加载 → 在 namespace 的 search.paths 中搜索文件 → 加载新 SO
4. 若找不到 → dlopen 失败
```

### 2.3 热修复场景中的 DT_NEEDED 死锁

假设补丁 SO `libfoo_patch.so` 的依赖关系如下：

```
libfoo_patch.so
  ├── DT_NEEDED: libbar_v2.so     ← 新版本，只在补丁目录中存在
  └── DT_NEEDED: libc++_shared.so ← 系统已有旧版本加载
```

**热修复加载时的实际行为**：

```
System.load("/patch/libfoo_patch.so")
  │
  └─ dlopen()
       ├─ find_libraries():
       │   ├─ 加载 libfoo_patch.so                   ✅ 成功（指定了全路径）
       │   ├─ 解析 DT_NEEDED: libbar_v2.so
       │   │   └─ 在 namespace.search.paths 中搜索
       │   │       └─ /data/app/.../lib/arm64/       ← 只有旧版 libbar.so 或无此文件
       │   │       └─ /system/lib64/                 ← 没有
       │   │       └─ ❌ 找不到 → dlopen 失败！
       │   └─ 解析 DT_NEEDED: libc++_shared.so
       │       └─ find_loaded_library_by_soname()
       │           └─ 找到已加载的旧版 libc++_shared.so
       │           └─ 复用旧 soinfo ✅（但可能符号不匹配！）
       └─ 结果：要么加载失败，要么链接到错误的依赖版本
```

这就是 **"补丁 SO 自己加载成功，但依赖链断裂"** 的经典故障。

---

## 三、Linker Namespace：看不见的"墙"

### 3.1 为什么需要 Namespace

Android 7.0（Treble 架构）引入 Linker Namespace，核心目的：

| 问题 | 示例 |
|------|------|
| **符号冲突** | `libcutils.so` 同时存在于 `/system/lib` 和 `/vendor/lib`，符号不同 |
| **依赖可见性** | SP-HAL 不应访问 Framework 私有符号（如 `libgui.so` 内部接口） |
| **安全隔离** | 防止应用 `dlopen` 系统私有库 |

### 3.2 Namespace 的配置结构

每个进程在启动时由 `linkerconfig` 动态生成 `/linkerconfig/ld.config.txt`：

```ini
# /linkerconfig/ld.config.txt
[system]
additional.namespaces = sphal,vndk

# --- default namespace（应用 ClassLoader 所在空间）---
namespace.default.isolated = true
namespace.default.search.paths  = /data/app/${org}${app}/lib/arm64
namespace.default.permitted.paths = /data/app/${org}${app}/lib/arm64

# 允许链接到 system namespace（访问系统公共库）
namespace.default.links = system
namespace.default.link.system.shared_libs = libc.so:libm.so:libdl.so:liblog.so:...

# --- system namespace（系统框架所在空间）---
namespace.system.isolated = true
namespace.system.search.paths  = /system/${LIB}:/system/${LIB}/hw
namespace.system.permitted.paths = /system/${LIB}:/system/${LIB}/hw
```

**关键概念**：

| 属性 | 含义 |
|------|------|
| `isolated = true` | 只允许加载 `search.paths` / `permitted.paths` 中的 SO |
| `search.paths` | `dlopen` 时搜索文件的路径（从前到后） |
| `permitted.paths` | 允许加载的路径范围（含子目录） |
| `links` | 可回退（fallback）查找的关联 namespace |
| `link.X.shared_libs` | 允许从 namespace X 导入的具体 SO 白名单 |

### 3.3 Namespace 对热修复的三重打击

**打击一：路径绑定在 ClassLoader 创建时固化**

```
应用启动
  └─ Application 创建
      └─ PathClassLoader 构造
          └─ Linker 创建 classloader-namespace (clns-1)
              └─ search.paths = ["/data/app/pkg/lib/arm64"]
              └─ 此路径集合不可逆改！
```

当你通过反射注入补丁路径后：

```java
// 反射注入成功
nativeLibraryPathElements[0] = patchElement;  // 补丁路径在数组最前面
// 但 clns-1 的 search.paths 仍然只有 "/data/app/pkg/lib/arm64"！
```

**结果**：`System.loadLibrary("foo")` 在 Java 层找到了补丁目录中的 `libfoo.so`，但此 SO 的 `DT_NEEDED` 依赖在 Linker 层解析时，使用的仍是绑定时的 `search.paths`，补丁目录不在其中。

**打击二：已加载 SO 符号优先**

```cpp
// soinfo_do_lookup 的查找顺序
// 先查 global_group（DF_1_GLOBAL 标记的所有 SO）
// 再查 local_group（本 namespace 内已链接的 SO）
// 如果旧 SO 在 global_group 中，旧符号会先被匹配到
```

补丁 SO 引用的新符号，很可能被已加载的旧 SO 的同名符号"插值"（symbol interposition）——即使旧符号的函数签名和语义已经不同，linker 也不会报错，直接错误链接。

**打击三：跨 namespace 符号隔离**

```
clns-1 (宿主 ClassLoader)        clns-2 (插件 ClassLoader)
  ├── libfoo.so (v1)               ├── libbar.so
  └── libc++_shared.so (旧版)      └── DT_NEEDED: libc++_shared.so
                                    │
                                    └─ 在 clns-2 的 search.paths 中寻找
                                    └─ 找到了补丁版 libc++_shared.so
                                    └─ ❌ 若补丁版不在 permitted.paths 中 → 拒绝加载
                                    └─ ❌ 如果在 Android 8.0+ 上且旧版已被 clns-1 打开
                                           → "already opened by ClassLoader" → 崩溃
```

---

## 四、`find_containing_library` 与 Namespace 归属判定

### 4.1 关键机制

Linker 通过**调用者的代码地址**反查归属的 SO：

```cpp
// bionic/linker/linker.cpp
static soinfo* find_containing_library(const void* p) {
    ElfW(Addr) address = reinterpret_cast<ElfW(Addr)>(p);
    
    // 遍历全体 soinfo 链表
    for (soinfo* si = solist_get_head(); si != nullptr; si = si->next) {
        // 检查 address 是否落在 si 的地址空间内
        if (address < si->base || address - si->base >= si->size) continue;
        
        // 进一步检查地址是否落在某个 PT_LOAD 段
        for (size_t i = 0; i < si->phnum; ++i) {
            const ElfW(Phdr)* phdr = &si->phdr[i];
            if (phdr->p_type != PT_LOAD) continue;
            if (address - si->load_bias >= phdr->p_vaddr &&
                address - si->load_bias <  phdr->p_vaddr + phdr->p_memsz) {
                return si;  // ✅ 找到了
            }
        }
    }
    return nullptr;  // ❌ 匹配不到任何 SO
}

// 调用者 namespace 的确定
static android_namespace_t* get_caller_namespace(soinfo* caller) {
    return caller != nullptr 
        ? caller->get_primary_namespace()   // 调用者 SO 所在的 namespace
        : g_anonymous_namespace;            // 匹配不到 → anonymous namespace
}
```

### 4.2 热修复/加固场景中的致命故障

当 SO 加壳或热修复方案修改了 `soinfo` 结构（例如将壳 SO 的 soinfo 替换为被保护 SO 的信息）：

```
壳 SO 代码执行 dlopen("protected.so")
  │
  └─ find_containing_library(return_address_of_caller)
      │
      ├─ 壳 SO 的代码地址 = 0x7a12340000
      ├─ 遍历 soinfo 链表匹配地址空间
      │   ├─ soinfo[0] = framework.so   → 0x7a12340000 不在此范围
      │   ├──soinfo[1] = 壳 SO           → 但壳 SO 的 soinfo 已被篡改为 protected.so 的地址空间！
      │   │   protected.base = 0x7b00000000, 壳代码地址 0x7a12340000 不匹配
      │   └─ ... 遍历完毕
      └─ return nullptr → caller_namespace = anonymous
          
anonymous namespace 中找不到 protected.so 及其依赖 → dlopen 失败
```

**根因**：`soinfo` 修复只改了符号表/重定位信息，却没有维护地址空间范围的正确性，导致 `find_containing_library` 匹配失败。

---

## 五、实战：SO 热修复的三种可靠方案

### 方案一：冷重启 + 抢先加载（最成熟）

这是 Tinker、Sophix 等主流框架的共同选择。

```
┌─────────────────────────────────────────────────┐
│  ① 下发补丁（BSdiff 差量或完整 SO）             │
│  ② 本地合成完整补丁 SO                          │
│  ③ 写入应用私有目录                              │
│     /data/data/<pkg>/patch_libs/<abi>/libfoo.so │
│  ④ 引导用户重启或下次冷启动                      │
│  ⑤ Application.attachBaseContext 中：           │
│     反射注入 nativeLibraryPathElements 头部      │
│     或使用 System.load(补丁绝对路径)            │
│  ⑥ 后续所有 System.loadLibrary 优先从补丁目录加载│
└─────────────────────────────────────────────────┘
```

**核心代码**：

```java
public class SoPatchInstaller {
    
    public static void install(Application app) {
        File patchDir = new File(app.getFilesDir(), "patch_libs");
        
        // 确保依赖 SO 在目标 SO 之前加载
        // 用 readelf -d 分析依赖顺序，按拓扑排序依次加载
        String[] loadOrder = getDependencyOrder(patchDir);
        for (String lib : loadOrder) {
            File libFile = new File(patchDir, lib);
            if (libFile.exists()) {
                System.load(libFile.getAbsolutePath());
            }
        }
    }
    
    /**
     * 用 ProcessBuilder 调用 readelf 获取 DT_NEEDED 依赖顺序
     * 也可以嵌入预编译的依赖关系表
     */
    private static String[] getDependencyOrder(File patchDir) {
        // 实际项目中通常预先分析好依赖关系
        // 例如：libc++_shared.so → libssl.so → libcrypto.so → libfoo.so
        return new String[] {
            "libc++_shared.so",
            "libssl.so", 
            "libcrypto.so",
            "libfoo.so"       // 目标 SO 最后加载
        };
    }
}
```

### 方案二：SONAME 重命名隔离（强隔离）

当热修复涉及不兼容的依赖升级时，将补丁 SO 以不同的 SONAME 构建：

```cmake
# CMakeLists.txt — 将补丁 SO 编译为不同 SONAME
add_library(foo_v2 SHARED src/foo.cpp)
set_target_properties(foo_v2 PROPERTIES
    OUTPUT_NAME "foo_v2"
    LINK_FLAGS "-Wl,-soname,libfoo_v2.so"
)
```

```java
// Java 层按版本加载
if (BuildConfig.VERSION_CODE >= patchVersion) {
    System.loadLibrary("foo_v2");   // 新版本
} else {
    System.loadLibrary("foo");      // 旧版本
}
```

**优点**：完全避免新旧版本冲突，两个 SO 在 linker 看来是完全不同的库。
**代价**：需要修改 JNI 函数注册（`JNI_OnLoad` 或 `RegisterNatives`），`System.loadLibrary("foo_v2")` 会查找 `libfoo_v2.so`。

### 方案三：静态链接不稳定依赖

将热修复中可能变化的依赖库**静态链接**进补丁 SO：

```cmake
# 将容易冲突的依赖静态链接
add_library(foo_selfcontained SHARED src/foo.cpp)
target_link_libraries(foo_selfcontained
    # 这些库静态链接，消除运行时 DT_NEEDED 冲突
    ${STATIC_OPENSSL}
    ${STATIC_LIBCPP}
    # 系统库保持动态链接（因为它们不会变）
    log dl c m
)
```

**适用场景**：补丁 SO 依赖了特定版本的 OpenSSL、protobuf 等，而宿主已加载了不同版本。

---

## 六、SO 依赖的拓扑排序与手动加载

### 6.1 分析依赖图

```bash
# 分析每个 SO 的 DT_NEEDED
$ readelf -d libfoo.so | grep NEEDED
 0x00000001 (NEEDED)  Shared library: [libssl.so]
 0x00000001 (NEEDED)  Shared library: [libcrypto.so]
 0x00000001 (NEEDED)  Shared library: [libc++_shared.so]

$ readelf -d libssl.so | grep NEEDED
 0x00000001 (NEEDED)  Shared library: [libcrypto.so]
 0x00000001 (NEEDED)  Shared library: [libc++_shared.so]

$ readelf -d libcrypto.so | grep NEEDED
 0x00000001 (NEEDED)  Shared library: [libc++_shared.so]
```

依赖图：

```
libfoo.so ──► libssl.so ──► libcrypto.so ──► libc++_shared.so
   │              │                │
   └──────────────┴────────────────┘
```

### 6.2 拓扑排序后加载

```java
// 拓扑排序结果（叶子节点优先）
// libc++_shared.so → libcrypto.so → libssl.so → libfoo.so

String[] loadOrder = {
    "libc++_shared.so",  // 无依赖 → 先加载
    "libcrypto.so",      // 仅依赖 libc++_shared → 已加载
    "libssl.so",         // 依赖 libcrypto → 已加载
    "libfoo.so"          // 依赖全部已加载
};

for (String lib : loadOrder) {
    File soFile = new File(patchDir, lib);
    if (soFile.exists()) {
        System.load(soFile.getAbsolutePath());
    } else {
        // 系统已有 → 无需补丁版本
        System.loadLibrary(lib.replace("lib", "").replace(".so", ""));
    }
}
```

### 6.3 Facebook SoLoader 的核心思路

```
SoLoader 做了三件事：
1. 解析 ELF 的 DT_NEEDED → 构建依赖图 → 拓扑排序
2. 按顺序从多个来源（APK lib、data 目录、系统路径）依次查找每个依赖 SO
3. 递归 System.load 保证依赖在先
```

**关键**：SoLoader 完全**不使用** `System.loadLibrary`（避免 ClassLoader 的 namespace 限制），而是使用 `System.load` + 全路径。依赖分析在**构建时**完成，运行时仅执行拓扑序加载。

---

## 七、排障与调试

### 7.1 启用 Linker 完整日志

```bash
# 设置 linker 调试属性（需要 root 或 debug 版本）
adb shell setprop debug.ld.all dlerror,dlopen,dlsym,reloc
# 查看日志
adb logcat -s linker:V
```

典型输出解读：

```
linker: dlopen(name="/data/app/pkg/patch_libs/libfoo.so", flags=0x2, extinfo=...)
linker: find_libraries(ns=clns-1): task=libfoo.so, is_dt_needed=0
linker: find_libraries(ns=clns-1): task=libssl.so, is_dt_needed=1  ← 补丁 SO 的依赖
linker: find_library_internal(ns=clns-1, name=libssl.so):
        search paths = [/data/app/pkg/lib/arm64]  ← 补丁目录不在此列表！
linker: library "libssl.so" not found
linker: failed to load libfoo.so: library "libssl.so" not found
```

### 7.2 检查 Namespace 配置

```bash
# 查看设备实际生效的 namespace 配置
adb shell cat /linkerconfig/ld.config.txt

# 查看进程的 namespace 映射
adb shell cat /proc/<pid>/maps | grep -E "\.so$"
```

### 7.3 检查 soinfo 状态

```bash
# 查看进程中已加载的所有 SO
adb shell cat /proc/<pid>/maps | grep -E "\.so$" | awk '{print $NF}' | sort -u

# 验证补丁 SO 是否在预期地址空间
adb shell cat /proc/<pid>/maps | grep libfoo
```

### 7.4 检查 SO 的符号冲突

```bash
# 导出 SO 中定义的所有符号
readelf -sW libfoo.so | grep -E "FUNC|OBJECT" | grep GLOBAL

# 导出 SO 中从外部引用的符号（UND = undefined）
readelf -sW libfoo.so | grep UND | awk '{print $NF}' | sort
```

---

## 八、方案决策矩阵

```
SO 热修复会遇到以下哪种约束？

├── 仅自有代码使用 SO，可控制所有 loadLibrary 调用点
│   └── 方案一（冷重启 + 抢先加载）+ 接口替换风格
│
├── 第三方 SDK 也在加载 SO，无法控制调用点
│   └── 方案一（冷重启）+ 反射注入 nativeLibraryPathElements 头部
│
├── 补丁涉及不兼容的 SO 依赖升级（如 libssl 大版本升级）
│   ├── 方案二（SONAME 重命名）—— 最可靠
│   └── 方案三（静态链接）—— 体积换稳定性
│
├── 需要 Google Play 合规 + Android 14+ 兼容
│   └── 优先考虑 Play Feature Delivery（官方方案）
│
└── 不能接受冷重启，必须实时生效
    └── ❌ SO 层面无法实现，只能退而求其次：
        ├── Java 层用 AndFix/Sophix 的 ArtMethod 替换（函数级）
        └── 或在 native 层做 PLT Hook 拦截特定函数调用
```

---

## 九、总结

SO 热修复技术三角：

```
               DT_NEEDED 依赖链
              /                \
             /                  \
  冷重启 + 抢先加载 ←────────  Linker Namespace 隔离
             \                  /
              \                /
            静态链接 / SONAME 重命名
```

三者相互制衡：

- **DT_NEEDED** 决定了"谁必须比谁先加载"
- **Linker Namespace** 决定了"在哪个空间里搜索谁"
- **冷重启** 是突破"SO 不可卸载"的根本前提

业界经过近十年的探索，共识已经收敛：**SO 热修复的可靠方案 = 冷重启 + 依赖拓扑排序 + 抢先加载（反射注入或 System.load 全路径）**。实时生效的 SO 热替换在 Android 的安全模型下不存在合法、稳定、通用的实现路径。

---

*参考来源：AOSP bionic/linker 源码、腾讯 Tinker 文档、阿里 Sophix 技术文档、Facebook SoLoader、Android Developers 官方文档（Linker Namespace）。*
