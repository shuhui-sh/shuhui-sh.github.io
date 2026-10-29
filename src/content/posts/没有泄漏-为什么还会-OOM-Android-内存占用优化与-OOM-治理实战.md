---
title: "没有泄漏，为什么还会 OOM？Android 内存占用优化与 OOM 治理实战"
date: 2026-10-28
description: "第四篇里，我们通过引用链找到了那些本来应该消失、却被长寿命对象拽住的页面。 但修完泄漏，不意味着内存工作结束了。一张全尺寸照片、一个不断积累的缓存、一段高频创建临时数组的循环，都可能没有泄漏报告。"
tags: ['性能优化', 'Android']
draft: true
category: "技术"
---
> 本文是「Android 应用性能优化」系列第五篇，与第四篇《内存泄漏治理》互为姊妹篇。第四篇关注“对象生命周期结束后为什么仍被引用”，这一篇关注另一面：**即使引用关系没有明显错误，图片太大、分配太勤、缓存没有预算，也会让应用承受不必要的内存压力。**
>
> 阅读路线：分清内存指标 → 按目标尺寸解码图片 → 测量分配与 GC → 给缓存加预算 → 区分 Java OOM、native 分配失败与系统杀进程。
>
> **实验说明**：配套工程为 `MemoryDemo`，设备为小米 13 Pro（Android 16 / API 36）。本文区分原始演示记录与审核后补测，不把单次结果写成性能保证，也不把不同指标拼成“优化前后”。构建和原始证据索引见文末。

---

## 一、问题提出：LeakCanary 没报警，内存为什么还在涨？

第四篇里，我们通过引用链找到了那些本来应该消失、却被长寿命对象拽住的页面。

但修完泄漏，不意味着内存工作结束了。一张全尺寸照片、一个不断积累的缓存、一段高频创建临时数组的循环，都可能没有泄漏报告。问题不一定是“引用错了”，也可能是**分辨率、容量和分配频率没有预算**。

因此，LeakCanary 没有报告，只能说明当前观察和检测范围内没发现相应生命周期泄漏，不能证明内存占用合理。接下来需要回答三个不同的问题：

1. **对象分配了多少？** 用于理解 Java 堆使用和分配频率。
2. **进程占了多少物理内存？** 用于理解系统压力和进程成本。
3. **业务真正需要保留多少？** 用于决定图片尺寸和缓存预算。

先看旧版演示中的一次真实 Java OOM。全局缓存连续持有 `ByteArray(1_000_000)`，最终成功保留 264 个块；**随后再申请下一块时失败**：

```text
Failed to allocate a 1000016 byte allocation
with 661744 free bytes and 646KB until OOM,
target footprint 268435456, growth limit 268435456
```

这里的 `growth limit 268435456` 是这次进程报告的堆增长上限，即 **256 MiB**，不是所有 Android 设备和应用的固定上限。每块 payload 是十进制 1 MB，264 块共 264,000,000 B，约 **251.77 MiB**；对象头、集合及应用其他对象还要另外计费。

这个反例说明：**没有页面泄漏，也能因为无限保留业务数据而耗尽 Java 堆。** 但“全局缓存主动持有，所以一定不是泄漏”同样不严谨——若这些数据早已不再需要，仍然属于逻辑上的无效保留。本文把它当作缺乏预算的反例，而不是给它的生命周期设计背书。

![历史演示：成功保留264个块后，后续分配触发Java OOM；界面旧单位标记为MB](/images/没有泄漏-为什么还会-OOM-Android-内存占用优化与-OOM-治理实战/shot03_oom.png)

> 这张截图是旧实验记录，不是新版工程的默认操作。为了避免把教学实验变成设备压力测试，审核后版本改用有限工作量的无界/有界缓存对照，不再提供主线程无限分配循环。捕获 OOM 后继续更新 UI 也不是生产恢复方案：此时构造日志、字符串或界面都可能再次分配失败。

---

## 二、相关知识点讲解

### 2.1 同样叫 Java Heap，数值为什么差这么多？

先执行：

```bash
adb shell dumpsys meminfo com.example.memorydemo
```

以下节选来自原始归档 `meminfo_full.txt`，单位为工具输出的 KB：

```text
                   Pss  Private  Private  SwapPss      Rss     Heap     Heap     Heap
                 Total    Dirty    Clean    Dirty    Total     Size    Alloc     Free
  Native Heap     5090     3916     1148     5784     6036    31332    23283     4132
  Dalvik Heap     7217     1780     5304       14     8884    11297     2824     8473

 App Summary
                       Pss(KB)                        Rss(KB)
           Java Heap:    10716                          28548
         Native Heap:     3916                           6036
                Code:    15656                         126328
            Graphics:    45080                          45084
           TOTAL PSS:   110715            TOTAL RSS:   214536
```

最容易踩的坑是：把 Summary 的 `Java Heap: 10716` 当成 Java 对象已用堆。**同一份输出里，Dalvik Heap 的 `Heap Alloc` 是 2824 KB，并不是10716 KB。**

这些数字不是相互矛盾，而是回答的问题不同：

| 指标 | 回答什么 | 不应该用来做什么 |
|------|----------|----------------|
| `Runtime.totalMemory() - freeMemory()` | 当前进程 Java 堆已用量的近似快照，包含尚未回收的垃圾等 | 不是精确活对象大小，也不是进程物理内存 |
| `Runtime.maxMemory()` | 当前运行时允许的 Java 堆上限 | 不是应用可用的全部系统内存，也不是 PSS 上限 |
| meminfo 明细的 `Heap Size / Alloc / Free` | 分配器/运行时报告的堆容量、分配与空闲情况 | 不等于相应内存页全部驻留在物理内存中 |
| App Summary 的 `Java Heap / Native Heap` | 按 Android 规则归并的私有内存归因 | 不能替代 Runtime used 或 Heap Alloc，不能直接除以 maxMemory 算堆使用率 |
| `TOTAL PSS` | 进程内存成本统计：共享驻留页按比例分摊；本文核查的AOSP总计还计入SwapPss，不能一概当作纯驻留物理内存 | 不是 Java 堆上限，也不保证等同 LMK 的判定阈值 |
| `TOTAL RSS` | 当前驻留物理页，包含共享部分的整份统计 | 多进程 RSS 直接相加会重复计算共享页 |

在本次核查的 AOSP 实现中，`Debug.MemoryInfo.getSummaryJavaHeap()` 的计算包括 `dalvikPrivateDirty` 和 ART 相关私有页；`getSummaryNativeHeap()` 使用 `nativePrivateDirty`。因此，**Summary 中的标签不能机械理解成该类对象的已分配字节数**。具体归并规则和厂商图形统计还可能随系统实现变化。

实际排查可以分两步：

- **先看进程成本**：Summary 哪项高？Java、Native、Graphics、Code，还是多个一起涨？
- **再查对应资源**：Java 查分配和堆对象；Native 查 Bitmap、native allocation、JNI 库；Graphics 查纹理、Surface 和图形缓冲；Code 查映射、实际触达页面等。

例如这份输出中 Graphics 约44 MiB。它提示要关注图形资源，但不能仅凭这个值就断言“图片泄漏”。同样，`.dex/.so` 的映射也不代表整个文件已经全部驻留；**文件大小、虚拟映射大小和驻留内存要分开看**。

> 本文计算容量统一用 **B、MB（10⁶ B）、MiB（2²⁰ B）**。系统日志和原始截图保留其原样，解释时再明确单位。

### 2.2 Bitmap：压缩文件小，不等于解码后省内存

磁盘上的 JPEG 文件可能很小，解码后的像素容量仍然很大。对普通软件 Bitmap，可用下面的式子理解主要量级：

```text
像素容量约等于 rowBytes × height
紧密排列时可近似为 width × height × 每像素字节数
ARGB_8888：4 B / pixel
RGB_565：2 B / pixel
```

`byteCount`、`allocationByteCount`、解码临时缓冲和 GPU 上传后的占用并非总相等。涉及 `inBitmap` 复用时，allocation 还可能大于当前图像逻辑容量；遇到行对齐、其他 Config 或 hardware bitmap，也不能只套一个宽高乘法。

Bitmap 像素存储的位置经历过变化：

- **Android 2.3.3 / API 10 及以前**：像素数据在 native memory，Bitmap 对象在 Dalvik heap。
- **Android 3.0 / API 11 至 Android 7.1 / API 25**：像素数据在 Dalvik/Java heap。
- **Android 8.0 / API 26 起**：像素数据回到 native heap。

这不意味着 Android 8+ 的 Bitmap“绕开了所有 Java OOM 风险”。Java 包装对象、native 分配登记与 GC 协调、解码失败处理都仍然存在。**native 分配失败也可能以 Java 异常形式暴露**，不能仅凭有没有 Java 堆栈判断分配发生在哪。

真正实用的优化顺序是：

1. **先缩小不必要的尺寸**：列表缩略图不解码成完整原图。
2. **再考虑格式和质量**：RGB_565 适合部分不需要 alpha、可接受低色彩精度的软件图像；渐变、暗部、肤色和品牌色需要实际验图，不能笼统说“照片几乎无感”。
3. **最后讨论复用**：让图片库管理合适的 Bitmap 池，减少重复解码分配。复用缓冲不是减少当前图像必须占用的像素容量，也不能无限扩大池。

常规列表应把目标尺寸交给 Glide/Coil 等图片库；自行解码时使用 bounds 预读、合适的 `inSampleSize`，必要时再缩放到最终尺寸。`inPreferredConfig` 是偏好而非保证，必须记录解码器实际返回的 `config`。

### 2.3 内存抖动：要测分配，不能只数代码里的 new

下面两条路径计算相同的校验和，但源代码层面的分配方式不同：

```kotlin
// 路径A：每次创建数组。
for (i in 0 until count) {
    val buffer = ByteArray(64)
    buffer[0] = i.toByte()
    checksum += buffer[0]
}

// 路径B：本轮循环复用一个数组。
val buffer = ByteArray(64)
for (i in 0 until count) {
    buffer[0] = i.toByte()
    checksum += buffer[0]
}
```

大量短命分配可能增加分配器工作、GC 频率和内存带宽压力；若发生在热路径上，也可能影响帧时间。但不能把“GC次数增加”简单等同于“每次都停顿一整帧”：ART 包含并发回收阶段，也存在暂停、调度竞争和其他成本，真正掉帧需要 trace/帧指标联合确认。

还有三条实验规则：

- **没有发生 GC，不等于没有发生分配。** 也可能是尚未达到触发条件、运行模式不同或计数时间窗口没覆盖异步回收。
- **数组不是禁止优化的屏障。** 不逃逸的数组和普通对象都不能仅靠源码保证最终机器执行了多少分配。
- **耗时差不是纯 GC 时间。** 它可能同时包含分配、清零、解释/JIT、循环优化、调度等差异。

因此，复用是一个待测的优化候选，而不是把每个对象都塞进池的理由。对象池还会引入同步、重置状态、容量和长期保留成本；应优先处理频率高、分配量大、已定位的路径。

### 2.4 缓存先有预算，生命周期清理再兜底

`onTrimMemory` 不应被理解为“OOM 之前一定会收到的预警”。尤其在新系统上，不可照搬完整的历史分级表：

| 级别 | 版本与含义 | 本文策略 |
|------|------------|---------|
| `TRIM_MEMORY_UI_HIDDEN` | UI不再可见；不是低内存的证明 | 释放可重建的UI相关缓存 |
| `TRIM_MEMORY_BACKGROUND` | 后台进程状态通知，具体投递受系统实现与状态影响 | 释放可快速重建的数据，不依赖必达 |
| `RUNNING_MODERATE/LOW/CRITICAL`、`MODERATE`、`COMPLETE` | 官方文档说明API34起不再通知这些等级，API35弃用 | 仅作旧系统背景，不作为Android16上的渐进压力策略 |

示意写法：

```kotlin
override fun onTrimMemory(level: Int) {
    super.onTrimMemory(level)
    when (level) {
        ComponentCallbacks2.TRIM_MEMORY_UI_HIDDEN,
        ComponentCallbacks2.TRIM_MEMORY_BACKGROUND -> releaseRebuildableCache()
    }
}
```

这段代码处理的是**收到通知后的行为**，不是对系统投递时机的承诺。应用也可以结合明确的页面/业务生命周期主动清理，但别在每次暂停时无差别清掉所有缓存，造成前后台切换反复重新加载。

真正能主动约束占用的是**缓存容量上限**。例如16 MiB的payload预算，新增数据超出预算时淘汰最旧条目，而不是等到堆用尽才清理。注意：payload预算只约束条目内容，不包含对象头、集合、在途请求和其他进程资源，不能宣传为“整个应用最多用16 MiB”。

### 2.5 都是“内存相关退出”，也要分清故障类型

| 现象 | 能说明什么 | 下一步 |
|------|------------|--------|
| `OutOfMemoryError` 含 `Failed to allocate ... growth limit ...` | ART报告该次分配无法满足，常见于Java堆压力 | 查申请大小、used/max、存活对象、垃圾与分配峰值 |
| Bitmap/JNI分配失败，或native allocator错误 | 可能是native资源/地址空间/映射问题，也可能转成Java异常 | 联合native allocation、tombstone和相关资源统计 |
| 进程被LMK杀死，没有应用异常栈 | 系统回收进程，不是应用抛出Java OOM | 查退出原因、进程重要性、系统压力与历史占用 |
| `Too many open files` | 文件描述符耗尽，通常是EMFILE等错误 | 查FD数量、打开来源及关闭路径；不是一概属于Java OOM |
| 无法创建新线程 | 可能涉及线程数、栈内存、地址空间或进程/系统限制 | 联合线程数、错误文本与系统限制排查 |

native崩溃也可能是越界、UAF等，与内存不足无关。**错误文本是线索，不是凭外观一键定因。**

---

## 三、具体实例应用展示

配套 `MemoryDemo` 保留三个入口：图片解码、分配复用、有界缓存。审核后实验把“创建像素缓冲”和“解码图片”分开，把单次演示和可重复观测分开。以下章节随本轮补测记录给出证据边界。

### Step 0：先给旧实验的数据定名

原稿曾把 Runtime used 的约255 MiB，与 `meminfo` Summary Java Heap 的10708 KB拼成“释放后下降”。这不是同一口径，**不能算一组前后优化数据**。

旧记录能保留的事实是：一次受控应用内反例触发了Java分配失败，截图和错误文本存在；退后台时曾记录到UI_HIDDEN，缓存引用被清空。它不证明系统低内存压力触发了回调，也不证明清空后255 MiB立刻变成10.5 MiB活对象。

本文新版缓存实验会把Runtime used、缓存payload字节数和PSS分别记录，避免重犯这个错误。

### Step 1：同一张图片，真实解码到需要的尺寸

原始版本用 `createBitmap` 创建4000×3000或1000×750缓冲，再画渐变。48,000,000 / 24,000,000 / 3,000,000 B的容量关系成立，但那不是 `inSampleSize` 解码实验。

审核后改为同一张不透明本地JPEG：先读bounds，再按请求的采样率和配置实际解码，关闭资源密度缩放，记录返回尺寸、实际config及allocationByteCount。三个场景独立启动，避免连续点击时旧图、渲染线程和分配器缓存影响解释。核心代码节选：

```kotlin
val bounds = BitmapFactory.Options().apply {
    inJustDecodeBounds = true
    inScaled = false
}
assets.open("opaque_4000x3000.jpg").use {
    BitmapFactory.decodeStream(it, null, bounds)
}
val options = BitmapFactory.Options().apply {
    inScaled = false
    inSampleSize = 4 // 本实验：4000×3000解码到1000×750。
    inPreferredConfig = Bitmap.Config.ARGB_8888
}
val bitmap = assets.open("opaque_4000x3000.jpg").use {
    checkNotNull(BitmapFactory.decodeStream(it, null, options))
}
// 检查实际bitmap.width/height/config与allocationByteCount。
```

生产代码应由目标尺寸计算采样率，并处理解码失败、取消和资源所有权；这里的4是本实验条件，不是适用于所有图片的固定值。

本次使用非 debuggable、未开启 R8 的 release-like 构建，每种场景独立启动3次，实际解码结果如下，三次各字段一致：

| 请求 | 实际尺寸 | 实际Config | allocationByteCount | 容量 |
|------|----------|------------|---------------------|------|
| 原尺寸ARGB | 4000×3000 | ARGB_8888 | 48,000,000 B | 45.78 MiB |
| 原尺寸RGB565 | 4000×3000 | RGB_565 | 24,000,000 B | 22.89 MiB |
| inSampleSize=4 | 1000×750 | ARGB_8888 | 3,000,000 B | 2.86 MiB |

采样场景的像素容量是全尺寸ARGB场景的**1/16，减少93.75%**。这次结论来自真实JPEG解码，不再是创建不同大小缓冲的类比。不过，它仍只是返回Bitmap的allocation容量对比，**不等于进程PSS、解码峰值或GPU内存也减少同样比例**。进程内after读数发生在解码之后、显示之前，不是完整渲染链路的稳态或峰值。

原始证据：`MemoryDemo/results/review-retest/20261028-171754-device/bitmap_{argb,rgb565,sample4}_{1,2,3}/records.json`；同目录保存启动结果、UI层级与meminfo。

### Step 2：把“21倍”改成可复查的多轮观测

旧版曾在debug构建顺序点击两条路径，得到344ms/28次GC和16ms/0次GC。**这是一对单次记录，不足以说明生产环境固定快21倍，更不能把差值全算成GC耗时。** 原截图作为历史证据保留，不再作为性能结论图。

新版实验使用后台串行任务、单调时钟、预热、交替执行顺序和多轮统计，同时保存校验和、GC计数及可获得的累计分配字节差。指标不支持时标为unknown，不把两个`-1`相减写成0。

本次release-like补测每条路径各2轮预热、7轮有效测量，每轮100万次，两条路径都写入并读取64个字节，而不仅仅读取第一个字节。工作量和旧版不同，因此下面数字**不能拿来与旧版344ms/16ms计算版本优化比例**。

| 模式 | 7轮耗时中位数 | 耗时范围 | 每轮GC计数差 | 累计分配字节差范围（进程级） |
|------|---------------|----------|---------------|--------------------------------|
| 每次创建数组 | 198.160 ms | 194.477～369.738 ms | 0 / 5 / 3 / 4 / 4 / 4 / 3 | 80,019,456～80,216,064 B |
| 本轮复用一个数组 | 175.899 ms | 175.131～350.150 ms | 0 / 0 / 1 / 0 / 0 / 0 / 1 | 0～65,536 B |

两条路径所有有效轮次的校验和均为 `-31739904`。这批数据支持“本构建和负载下，重复创建路径产生了显著更多分配”，但不支持“复用一定零GC”或“固定快21倍”。预热之后前几轮仍有较大耗时，说明固定预热轮数不等于运行状态已经完全稳定。

`art.gc.bytes-allocated` 与 `art.gc.gc-count` 是进程累计计数；两次读取之间的差值包含框架、其他线程及采样影响，分配计数也有运行时统计粒度。因此复用路径读到0，不代表连循环外的那一个数组都没有创建；它也不是逐对象分配跟踪。GC可能延续到下一轮，不能把落在复用轮次中的GC直接归因于复用路径。

原始逐轮记录：`MemoryDemo/results/review-retest/20261028-171754-device/churn/records.json`。中位数和范围由 `summarize_review_evidence.py` 从全部有效轮次生成，没有删除偏慢轮次。要研究掉帧，下一步应结合具体页面的帧时间和trace，而不是从这个后台循环直接宣布UI性能提升。

### Step 3：先限制缓存，再验证清理

新版对同一有限请求序列比较两种策略：无上限地保留所有块，以及按字节淘汰的有界FIFO缓存。核心实现是先按实际payload大小计费，再淘汰到预算内：

```kotlin
fun add(payload: ByteArray) {
    entries.addLast(payload)
    payloadBytes += payload.size
    while (payloadBytes > capacityBytes && entries.isNotEmpty()) {
        payloadBytes -= entries.removeFirst().size
        evictions++
    }
}
```

这只是演示FIFO，不是假装实现LRU。实际项目可使用按字节计费的`LruCache`并评估访问模式；并发访问需要统一同步策略，本工程由`BigCache`同步包装。超大单条、在途请求和分配失败仍需另外控制。

每种策略独立重启进程，输入均为64个1 MiB数组，实际写入全部内容；分配结束后固定静置2秒，不强制GC，再采样相同的Runtime used字段。

| 观测 | 有限无界对照 | 16 MiB有界缓存 |
|------|---------------|----------------|
| 输入payload | 64 MiB | 64 MiB |
| 最终保留条目 | 64 | 16 |
| 最终保留payload | 64 MiB | 16 MiB |
| 淘汰条目数 | 0 | 48 |
| 分配前Runtime used | 12,327,280 B | 12,301,376 B |
| 静置2秒后Runtime used | 79,805,144 B | 79,770,880 B |

有界缓存首先满足了逻辑不变量：**每次添加结束后，保留payload不超过预算**。但这次Runtime used没有立刻拉开差距：两者仍接近76 MiB。淘汰的旧块可能仍待GC；只有引用已移除，并不意味着它们已经不占用已用堆。因为没有确认GC完成，不能据此宣称“有界缓存没有作用”，也不能只挑后来的低值说“内存立刻省了48 MiB”。即使后续对象被回收，分配器也未必立即归还物理页，那是PSS/RSS层面的另一个问题。

随后，对有界场景真正按HOME，观察到一次系统 `UI_HIDDEN` 回调：

| 回调内同口径观测 | 清理前 | 清理后即时 |
|------------------|--------|------------|
| 缓存payload | 16,777,216 B | 0 B |
| Runtime used | 19,603,072 B | 19,603,072 B |
| native allocated | 22,078,464 B | 22,078,464 B |
| PSS采样 | 56,762 KiB | 56,766 KiB |

这个结果同样诚实：**缓存引用确实被清除了，但回调内即时读数并没有立即下降。** 从分配后约79.77MB到回调前约19.60MB之间也有时间间隔，可能发生自然回收及其他工作，不能把先前下降归因于尚未执行的clear。`gc_confirmed=false` 随原始记录保存。

因此，这组实验验证的是“预算限制住了保留payload”和“本次退后台通知执行了清理”，不是“OOM前必达通知”或“清理即归还物理内存”。原始证据在同轮次 `cache_bounded/records.json`、`cache_unbounded/records.json` 及 `trim-records.json`；实际运行中的UI状态与逻辑断言一并保存。

---

## 四、总结

### 内存占用优化速查表

| 原则 | 落地方式 |
|------|----------|
| 先统一口径 | Runtime used/max、Heap Alloc、Summary和PSS分开记录 |
| 先减尺寸，再选格式 | 按显示需求解码；RGB_565先验画质；池也设预算 |
| 定位高频分配 | 多轮测量分配量/耗时/GC，结合trace判断帧影响 |
| 缓存主动限额 | 按字节计费、超限淘汰；生命周期清理是补充 |
| 故障分类 | Java OOM、native失败、LMK、FD/线程耗尽分别排查 |

### 和第四篇连起来看

- **第四篇**关注引用与生命周期：页面或旧View为什么还可达？
- **本篇**关注预算与频率：需要多大图、保留多少数据、每秒分配多少？

两者并非严格互斥，也没有一刀切的先后顺序。优先修复已经定位、对峰值和稳定性影响最大的来源；若有明显泄漏，应避免用缩小缓存去掩盖它。

### 下篇预告

内存里还有Code这一部分。R8、资源裁剪与native库整理首先作用于包体和构建产物，也可能影响运行时，但**APK少多少字节，不等于RSS就少多少字节**。

下一篇讲包体优化时，我们会把下载体积、安装体积、启动加载和实际驻留分开验收，而不是把“代码也是内存”当作一条自动换算公式。

---

### 附：环境、证据与复现边界

- 原始设备：小米13 Pro（2210132C / nuwa），Android16 / API36。AGP8.5.2、Kotlin2.0.21，minSdk26 / targetSdk34。
- 原始文件：`meminfo_full.txt`；`images/shot01_bitmap_argb8888.png`、`shot02_churn_reuse.png`、`shot03_oom.png`。前两张分别是像素容量和单轮debug演示，不用于证明真实解码峰值或稳定性能倍数。
- 审核后构建归档：`MemoryDemo/results/review-retest/20261028-164244-source/`，含代码备份、构建日志、APK与源码指纹。中文路径下JVM单测先遇到类加载失败，随后以同一源码的ASCII路径副本构建，3项JUnit测试及debug/release构建通过；失败记录没有删除。
- 本次真机补测：`MemoryDemo/results/review-retest/20261028-171754-device/`。release-like APK非debuggable、未开启R8；三种图片各3次独立启动，分配实验各2次预热加7次有效轮次，缓存每策略1次有限运行、固定静置2秒。没有将缓存单轮读数当作稳定分布或性能基准。
- 每个场景用独立`run_id`筛选结果，保存启动结果、完成日志、UI层级、meminfo及应用JSONL；最终采集脚本退出码为0，校验了返回配置、校验和、缓存上限/淘汰数及本次UI_HIDDEN清理。先前一次UI dump失败的运行保留在另一目录，不以失败当成功，也不清空设备logcat。
- `summarize_review_evidence.py` 从原始JSON生成 `20261028-171754-device/article-summary.json`，便于核对本文表格；脚本与原始记录均为交付物，不覆盖历史图片和数据。
- 本文未测native极限分配、系统级内存耗尽、LMK触发或线上OOM恢复，不从Java缓存实验外推这些结论。
- GC请求、回调到达、引用清除、对象回收、物理页归还，是不同阶段；任何一项没有证据，就不写成已完成。

### 参考资料

- [Android：Manage your app's memory](https://developer.android.com/topic/performance/memory)
- [Android：Manage bitmap memory](https://developer.android.com/topic/performance/graphics/manage-memory)
- [ComponentCallbacks2：各级别与版本说明](https://developer.android.com/reference/android/content/ComponentCallbacks2)
- [Bitmap.Config：RGB_565的画质权衡](https://developer.android.com/reference/android/graphics/Bitmap.Config)
- [Debug：运行时与内存统计API](https://developer.android.com/reference/android/os/Debug)
