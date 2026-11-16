---
title: "你的 Activity 关了，为什么还活着？Android 内存泄漏从发现、定位到线上治理"
description: "Activity 关了为什么还活着？用 dumpsys 与堆曲线量化泄漏，读懂 LeakCanary 最短强引用链，根治单例、回调、Fragment 协程等五类泄漏，并接入 CI 自动化门禁。"
pubDate: "2026-11-11"
tags: ['Android']
heroImage: "/images/你的-Activity-关了-为什么还活着-Android-内存泄漏从发现-定位到线上治理/01.png"
---

> 本文同步自掘金首发：[juejin.cn/post/7706743522149646371](https://juejin.cn/post/7706743522149646371)

> 本文是「Android 应用性能优化」系列第四篇。前三篇优化的是「画面怎么高效渲染、App 怎么快速启动」，这一篇解决的是另一类更隐蔽的顽疾：**App 用着用着为什么越来越卡，最后在后台甚至前台被系统杀掉？**
>
> 读完本文你将掌握一套完整的内存泄漏工程治理闭环：**用 `dumpsys meminfo` 与堆曲线量化泄漏 → 理解 LeakCanary 与 Shark 引擎的自动捕获原理并精读引用链 → 根治现代 Android 项目中最常见的五大泄漏场景（单例 Context、回调监听、Fragment 协程与 `StateFlow`、自定义 Scope 挂起协程、Compose 系统回调） → 用 Instrumentation 自动化测试构建防回归门禁，并掌握线上三道防线的设计思路。**
>
> **环境说明**：文中所有实测数据与引用链均来自配套演示工程 `LeakDemo` 在**小米 13 Pro（骁龙 8 Gen 2，Android 16 / API 36）** 真机上的实测。五类典型泄漏与逐步修复分别对应独立的 Git Tag（`step0-leaky` 至 `step6-regression-test`），LeakCanary 版本为 `2.14`。详见文末「附：演示工程与测量环境」。

---

## 一、第一步：发现与量化——如何确认 App 存在内存泄漏？

用户反馈："App 用久了越来越卡，切几个页面之后有时候直接闪退回桌面。"

面对这类反馈，先不要盲目翻代码。最直接、成本最低的验证方式是：**反复进出可疑页面，观察进程内的核心组件计数与堆内存水位在 GC 后能否回落到基线。**

### 1.1 用 `dumpsys meminfo` 检查核心对象计数

无需打开 Android Studio，一条 ADB 命令即可查看当前进程中存活的 `Activities` 与 `Views` 数量：

```bash
adb shell dumpsys meminfo com.example.leakdemo
```

在输出的末尾有一段专门统计核心组件实例数的 `Objects` 面板：

```text
 Objects
               Views:      556         ViewRootImpl:        6
         AppContexts:       88           Activities:       41
```

**标准复现与验证流程**：

1. **记录基线**：冷启动应用停留在主页面 `MainActivity`，此时进程内 `Activities` 计数为 **1**，`Views` 计数为 **16**。
2. **执行压力循环**：依次进入商品详情页 `DetailActivity` → 返回、进入 `DetailFragment`（压入返回栈）→ 返回、进入 `ComposeActivity` → 返回，作为一个完整轮次，连续重复 **20 轮**后退回主页面。
3. **触发 GC 后复测**：触发垃圾回收并等待回收完成，再次执行 `dumpsys meminfo`。

正常情况下，所有二级页面都已经退出销毁，`Activities` 计数应当回落到 **1**（仅剩主页面 `MainActivity`）。但在未修复的基线版本（`step0-leaky`）中，连续 3 轮重复实验的结果完全一致：

- **`Activities` 停留在 41**：主页面 1 个 + 20 轮进出残留的 20 个 `DetailActivity` 与 20 个 `ComposeActivity`，一个都没有被 GC 回收。
- **`Views` 膨胀到 556**：被泄漏的 Activity 与 Fragment 视图树全部滞留在内存中。

### 1.2 观察 GC 后的堆内存水位趋势

除了看对象个数，我们在不含检测工具开销的 `release-like` 构建下，对 20 轮进出页面全过程进行每秒一次的内存采样，并在末尾触发 GC，对比修复前（`step0`）与全部修复后（`step5`）的 Java Heap 走势：

![修复前后堆内存趋势对比](/images/你的-Activity-关了-为什么还活着-Android-内存泄漏从发现-定位到线上治理/01.png)

两条曲线呈现出鲜明的对比：

- **修复前（红线 `step0`）**：呈现典型的"阶梯式锯齿抬升"——每进出一轮页面，内存底线就往上垫高一截，从初始的 **7.0 MB** 一路爬升至 **13.1 MB**，即便在末尾主动触发 GC，水位也完全无法回落。
- **修复后（蓝线 `step5`）**：在整个 20 轮反复进出过程中，内存始终平稳维持在 **7.9 ~ 8.4 MB** 的窄幅区间内，GC 后立即回落至基线。

### 1.3 泄漏的本质：GC Root 可达性与生命周期错配

为什么 Java / Kotlin 有自动垃圾回收（GC），已经执行了 `finish()` 和 `onDestroy()` 的 Activity 还是回收不掉？

因为 ART 虚拟机判断一个对象能否回收，依据的不是"业务上还用不用它"，而是**可达性分析（Reachability Analysis）**：GC 从一组固定的根节点（**GC Roots**，包括运行中的线程栈帧局部变量、已加载类的静态字段、JNI 全局引用、系统服务持有的引用等）出发向下遍历引用图——**只要还有任意一条强引用路径能从 GC Root 走到该对象，GC 就认为它仍在使用，绝不会回收它。**

```text
GC Root（静态字段 / 活跃线程 / 系统服务…）
   │
   └─→ 存活对象 A ─→ 存活对象 B ─→ 已经 finish() 的 DetailActivity  ← 本该被回收，却因强引用可达而滞留
```

因此，内存泄漏在工程上的核心矛盾只有一句话：**生命周期错配——长生命周期的对象，不合理地持有了短生命周期对象的强引用。**

| 对象层级 | 典型生命周期长度 | 常见代表 |
|---|---|---|
| **进程级（最长）** | 与 App 进程同生共死 | `Application`、`object` 单例、`companion object` 静态字段、系统服务回调表、全局 `CoroutineScope` |
| **页面 / 业务级（中等）** | 页面打开到彻底退出 | `Activity`、`Fragment` 实例、`ViewModel` |
| **视图 / 局部级（最短）** | 页面可见或单次交互期间 | `View`、`ViewBinding`、Fragment 的视图树、Compose 的单个 `Composition` |

只要上层（长寿命）持有下层（短寿命）的引用，且在下层执行销毁回调（`onDestroy` / `onDestroyView` / `onDispose`）时未及时断开，就会产生内存泄漏。排查内存泄漏的全部工作，就是**找出这条不该存在的引用边，并将其斩断**。

---

## 二、第二步：自动捕获与引用链精读——LeakCanary 与 Shark 机制

`dumpsys meminfo` 只能告诉你"有对象没回收"，但不会告诉你"是谁拽住了它"。要在开发阶段自动抓出真凶，行业标准工具是 Square 开源的 **[LeakCanary](https://square.github.io/leakcanary/)**。

### 2.1 LeakCanary 是如何自动发现泄漏的？

LeakCanary 的核心设计不是监控宏观内存水位，而是**在组件生命周期的终点精准盯防每一个本该消亡的对象**。其内部工作流分为五步：

```text
① 生命周期终点钩子（Activity#onDestroy / Fragment#onDestroyView / Fragment#onDestroy / ViewModel#onCleared）
   └─ ObjectWatcher 创建 KeyedWeakReference（带唯一 key 的弱引用）包裹目标对象，并关联 ReferenceQueue
        ↓
② 延迟等待（默认 5 秒）并由 GcTrigger 触发垃圾回收
        ↓
③ 检查 ReferenceQueue：
   ├─ 若弱引用已入队 → 说明对象已被 GC 正常回收，解除观察
   └─ 若弱引用未入队 → 判定该对象为 Retained（滞留对象）
        ↓
④ 累积达到阈值后导出堆快照：
   └─ App 在前台时，默认累积满 5 个 Retained 对象（logcat: "app is visible & >=5 threshold"），
      调用 Debug.dumpHprofData() 生成 .hprof 堆转储文件
        ↓
⑤ Shark 引擎离线解析 .hprof：
   └─ 采用广度优先搜索（BFS）计算从 GC Roots 到泄漏对象的最短强引用路径（Shortest Path），
      结合内置 Android 生命周期识别器（AndroidObjectInspectors）标注每个节点的 Leaking 状态
```

这里有三个在实战中非常关键的细节：

1. **自动监视的四大目标**：LeakCanary 默认自动监视销毁的 `Activity`、销毁的 `Fragment` 实例、**销毁的 `Fragment View`** 以及清除后的 `ViewModel`。其中对 **Fragment View** 的独立监视尤为重要——当 Fragment 因 `addToBackStack` 进入返回栈时，Fragment 本身还活着，但它的 View 已经销毁，这是日常开发中最容易漏查的重灾区。
2. **前台 5 个对象的 Dump 阈值**：为了避免每退一个页面就卡顿 Dump 一次，LeakCanary 在应用处于前台时会等待滞留对象达到 **5 个**才触发 Heap Dump（若未满 5 个，日志会提示 `Found N objects retained, not dumping heap yet`，或者将应用退到后台等待 5 秒也会触发 Dump）。
3. **区分 `Application Leak` 与 `Library Leak`**：Shark 引擎内置了已知的系统框架与第三方 SDK 泄漏特征库。匹配业务代码问题的归为 `Application Leak`，匹配已知系统/库级问题的归为 `Library Leak`，帮助开发者聚焦业务自身可修复的问题。

### 2.2 零代码接入背后的原理（呼应第三篇 `ContentProvider`）

在项目中引入 LeakCanary 只需在 `app/build.gradle.kts` 中加一行 `debugImplementation` 依赖，无需编写任何初始化代码：

```kotlin
// app/build.gradle.kts
dependencies {
    debugImplementation("com.squareup.leakcanary:leakcanary-android:2.14")
}
```

为什么一行 `LeakCanary.init(this)` 都不用写，它就能自动监听所有 Activity 和 Fragment？

这正好印证了我们在本系列第三篇《冷启动优化》中讲过的机制：打开 `debug` 构建产物的 **Merged Manifest**，可以看到 LeakCanary 自动合并进来的 `ContentProvider`：

```xml
<provider
    android:name="leakcanary.internal.MainProcessAppWatcherInstaller"
    android:authorities="${applicationId}.leakcanary-installer"
    android:exported="false" />
```

系统在启动进程执行 `ActivityThread.handleBindApplication()` 时，会在 `Application.onCreate()` 之前自动调用 `MainProcessAppWatcherInstaller.onCreate()`，通过 `Application.registerActivityLifecycleCallbacks` 完成所有生命周期监听器的挂载。又因为依赖声明用的是 `debugImplementation`，这套 Provider 和监控逻辑只会打进 Debug 包，**对线上 Release 包的包体积和冷启动速度是真正的零影响**。

### 2.3 三步读懂一份 Leak Trace（引用链精读法则）

拿到 LeakCanary 报告后，最核心的技能就是读懂 **Leak Trace（泄漏引用链）**。来看我们在 `LeakDemo` 中抓到的第一条真实报告：

![LeakCanary 报告界面与引用链标注](/images/你的-Activity-关了-为什么还活着-Android-内存泄漏从发现-定位到线上治理/02.png)

对应的文本导出如下：

```text
┬───
│ GC Root: Thread object
│
├─ android.net.ConnectivityThread instance
│    Leaking: NO (PathClassLoader↓ is not leaking)
│    Thread name: 'ConnectivityThread'
│    ↓ Thread.contextClassLoader
├─ dalvik.system.PathClassLoader instance
│    Leaking: NO (ImageHelper↓ is not leaking and A ClassLoader is never leaking)
│    ↓ ClassLoader.runtimeInternalObjects
├─ java.lang.Object[] array
│    Leaking: NO (ImageHelper↓ is not leaking)
│    ↓ Object[2155]
├─ com.example.leakdemo.util.ImageHelper class
│    Leaking: NO (a class is never leaking)
│    ↓ static ImageHelper.context
│                         ~~~~~~~
╰→ com.example.leakdemo.DetailActivity instance
     Leaking: YES (ObjectWatcher was watching this because com.example.leakdemo.DetailActivity received
     Activity#onDestroy() callback and Activity#mDestroyed is true)
     Retaining 65.7 kB in 1273 objects
```

无论一条引用链有多长，都只需按以下「**三步读链法**」定位根因：

1. **第一步：看首尾，定边界**

  - **首行（起点）**：`GC Root` 告诉你这条链靠什么保持存活。
  - **末行（终点）**：`╰→` 指向的是本该被回收的目标对象。Shark 已经根据内部字段帮你验明了正身：`Activity#mDestroyed is true`，且统计出它连带锁死了 `1273` 个对象、共 `65.7 kB` 内存。

2. **第二步：找状态跳变区间（最后一个 `Leaking: NO` 到第一个 `Leaking: YES`）**

  - 链路上的每个节点都有 Shark 推断的存活合理性标记：

    - `Leaking: NO`：该对象此刻活着是合理的（例如系统线程、`ClassLoader`、已加载的 `Class` 对象、尚未销毁的宿主 `Activity`）。
    - `Leaking: YES`：该对象生命周期已结束，不该继续存活。
    - `Leaking: UNKNOWN`：纯数据容器或中间对象（如 `ArrayList`、Lambda 实例、协程续体），其自身没有生命周期标志位。

  - **核心定责法则**：**导致泄漏的罪魁祸首，一定位于链路中最后一个 `Leaking: NO` 节点与第一个 `Leaking: YES` 节点之间的那段引用上！** Shark 还会贴心地用波浪线 `~~~~~~~` 把这一区间内的嫌疑引用全部标出来（上例中从 `ImageHelper class [NO]` 直接跳变到 `DetailActivity [YES]`，中间唯一的引用就是 `static ImageHelper.context`）。

3. **第三步：看懂 ART 静态字段的底层持有路径**

  - 很多同学第一次看 LeakCanary 报告会疑惑：*明明是静态变量 `ImageHelper.context` 泄漏，为什么顶部的 GC Root 写的是 `Thread object (ConnectivityThread)`？`ConnectivityThread` 跟我的代码有什么关系？*
  - 这是因为：在 ART 虚拟机中，一个类的 `static` 字段存放在该类的 `Class` 对象里，而 `Class` 对象又存放在加载它的 `PathClassLoader.runtimeInternalObjects` 数组中；进程里任何一个持有了 `contextClassLoader = PathClassLoader` 的活跃线程（如系统自动创建的 `ConnectivityThread` 或 `LeakCanary-Heap-Dump` 线程），都会作为 GC Root 连向 `PathClassLoader` 进而连向所有业务类。**因此，看到 `Thread → PathClassLoader → runtimeInternalObjects → 某业务 Class` 时，直接把前半截视为「静态字段 GC Root 的固定前导帧」，目光直接锁定 `↓ static 类名.字段名` 即可。**

### 2.4 内存泄漏诊断工具链分工

在实际工程中，我们将三类工具组合使用，各司其职：

| 工具 | 核心定位 | 适用阶段与优势 | 局限性 |
|---|---|---|---|
| **`adb shell dumpsys meminfo`** | **宏观定量筛查** | 几秒钟查看 `Activities` / `Views` 计数与堆内存变化，适合脚本自动化压测与快速冒烟 | 只反映数量异常，不提供具体是哪个类或哪条引用链导致的泄漏 |
| **LeakCanary (Shark)** | **微观定性溯源与门禁** | 自动监测 `Activity` / `Fragment` / `Fragment View` / `ViewModel`，直接给出最短强引用链；支持接入 JUnit 自动化测试 | 仅在 Debug 与测试构建开启；单条对象默认只报告最短的那条引用链 |
| **Android Studio Memory Profiler** | **交互式全堆深挖** | 手动抓取 `.hprof`，按类查看实例数、Shallow Size / Retained Size（支配树 Dominator Tree），适合排查非组件类（如巨型集合、缓存对象）的滞留 | 依赖人工交互操作，不适合无人值守的持续回归 |

---

## 三、第三步：定位与根治——现代 Android 项目五大高频泄漏场景实战

很多老旧教程还在讲 `AsyncTask` 或匿名 `Thread` 泄漏，但在全面普及 **Kotlin + 协程（Coroutines）+ Flow + ViewBinding + Jetpack Compose** 的现代 Android 架构中，内存泄漏早已换了新的面孔。

我们在配套工程 `LeakDemo` 中完整复现并根治了现代项目里最高频的 **5 类泄漏模式**（对应标签 `LEAK-1` ~ `LEAK-5`）。在压测基线版本时，LeakCanary 一举捕获了它们：

![LeakCanary 捕获的泄漏列表](/images/你的-Activity-关了-为什么还活着-Android-内存泄漏从发现-定位到线上治理/03.png)

下面我们逐一拆解每类场景的**问题代码、真实引用链（Leak Trace）、底层持有机制与标准修复方案**。

---

### 场景一：长寿命单例直接持有 Activity Context（`LEAK-1`）

#### 1. 问题代码

工具类或业务管理类做成 `object` 单例后，在初始化时直接把 `Activity` 赋给了成员变量：

```kotlin
// ❌ 错误写法：单例直接保存了外部传入的 Context
object ImageHelper {
    lateinit var context: Context

    fun init(context: Context) {
        this.context = context
    }
}

// 在 DetailActivity.onCreate() 中调用：
ImageHelper.init(this) // 传入的是 DetailActivity 实例本身！
```

#### 2. 真实引用链与机制解析

这正是 2.3 节展示的那条经典引用链：

```text
GC Root: Thread object
  └─ ... → PathClassLoader.runtimeInternalObjects
  └─ com.example.leakdemo.util.ImageHelper class  [Leaking: NO]
       ↓ static ImageHelper.context
                            ~~~~~~~
  ╰→ com.example.leakdemo.DetailActivity instance [Leaking: YES, mDestroyed = true]
```

`ImageHelper` 是进程级单例，它的静态字段 `context` 指向了 `DetailActivity`。当用户按返回键退出详情页后，哪怕 `DetailActivity` 已经走完 `onDestroy()`，它及其内部挂载的整棵 View 树（1273 个对象，65.7 kB）依然被 `ImageHelper.context` 死死锁在内存中。

#### 3. 标准修复方案（对应 Tag：`step1-fix-leak1`）

长寿命单例如果确实需要 `Context` 来访问资源、文件目录或系统服务，**必须在内部统一转化为 `applicationContext`**：

```kotlin
// ✅ 正确写法：防御性地提取 applicationContext，彻底与 Activity 解耦
object ImageHelper {
    lateinit var context: Context
        private set

    fun init(context: Context) {
        this.context = context.applicationContext
    }
}
```

> **💡 工程避坑要点**：
>
> 1. **何时不能用 `applicationContext`？** 凡涉及弹窗（`Dialog`）、启动特定主题的 UI 组件或需要读取 Activity 级 `Theme` 属性的操作，必须使用 Activity 的 UI Context；此时绝不能把该 Context 存入单例字段，而应作为方法局部参数即用即焚，或随生命周期销毁时清理。
> 2. **为什么有时修完一处泄漏，页面还是没被回收？** 在我们的实测中，修完 `LEAK-1` 后，`ImageHelper.context` 这条引用链彻底消失了，但 `dumpsys meminfo` 里的 `Activities` 计数依然是 41。原因很简单：**同一个 `DetailActivity` 同时被两条独立的引用链拽着（场景一的 `ImageHelper` + 场景四的挂起协程）**。砍断第一条链证明这处修复已经生效，但只有把指向它的最后一条链也砍断（见场景四），对象才能真正被 GC 释放。

---

### 场景二：单例 / Repository 持有 UI 回调 Lambda 未注销（`LEAK-2`）

#### 1. 问题代码

数据层（Repository / Manager）使用观察者模式维护监听器列表，UI 层在注册 Lambda 回调时直接访问了页面控件，但在页面销毁时忘记调用 `removeListener`：

```kotlin
// ❌ 错误写法：单例持有监听器列表，UI 层只管 add 不管 remove
object ProductRepository {
    private val listeners = mutableListOf<(List<Product>) -> Unit>()

    fun addListener(listener: (List<Product>) -> Unit) {
        listeners += listener
    }
}

// 在 ListFragment.onViewCreated() 中：
val binding = FragmentListBinding.bind(view)
ProductRepository.addListener { products ->
    binding.title.text = "共 ${products.size} 件" // Lambda 隐式捕获了局部变量 binding！
}
```

#### 2. 真实引用链与机制解析

当用户从 `ListFragment` 点击跳转到 `DetailFragment`（`addToBackStack`）时，`ListFragment` 的视图被销毁（执行了 `onDestroyView()`），LeakCanary 立即抓到了如下引用链：

```text
┬───
│ GC Root: Thread object
│
├─ ... → com.example.leakdemo.data.ProductRepository class
│    Leaking: NO (a class is never leaking)
│    ↓ static ProductRepository.listeners
│                               ~~~~~~~~~
├─ java.util.ArrayList instance
│    Leaking: UNKNOWN
│    ↓ ArrayList[1]
│               ~~~
├─ com.example.leakdemo.ListFragment$$ExternalSyntheticLambda0 instance
│    Leaking: UNKNOWN
│    ↓ ListFragment$$ExternalSyntheticLambda0.f$0
│                                             ~~~
├─ com.example.leakdemo.databinding.FragmentListBinding instance
│    Leaking: UNKNOWN
│    Retaining 185.8 kB in 1392 objects
│    ↓ FragmentListBinding.rootView
│                          ~~~~~~~~
╰→ android.widget.LinearLayout instance
     Leaking: YES (ObjectWatcher was watching this because com.example.leakdemo.ListFragment received
     Fragment#onDestroyView() callback (references to its views should be cleared to prevent leaks))
```

这条链路揭示了两个极易被忽视的底层细节：

1. **Kotlin Lambda 的隐式捕获机制**：在 `onViewCreated` 里写的 `{ products -> binding.title.text = ... }` 看起来很无害，但编译器在将其编译为合成类 `ListFragment$$ExternalSyntheticLambda0` 时，会把闭包内引用的外部变量 `binding` 作为合成类的成员字段 `f$0` 存起来！于是形成了 `ProductRepository.listeners → ArrayList → Lambda.f$0 → FragmentListBinding → rootView (LinearLayout)` 的强引用链。
2. **局部变量 `binding` 照样会泄漏**：很多人以为"不把 `binding` 声明成 Fragment 成员变量就不会泄漏"，实际上只要长寿命的回调或协程捕获了局部的 `binding`，整棵已销毁的 Fragment 视图树（1392 个对象，185.8 kB）照样被锁死。

#### 3. 标准修复方案（对应 Tag：`step2-fix-leak2`）

**方案 A（传统回调改造）**：如果必须保留回调接口，务必保存 Lambda 引用，并在对称的生命周期终点（`onDestroyView`）中显式调用 `removeListener`。

**方案 B（现代架构推荐）**：**彻底淘汰手动维护的 `listeners` 列表，改用 Kotlin `StateFlow` / `SharedFlow` 暴露响应式数据流**，从根源上消灭"忘记 `removeListener`"的隐患：

```kotlin
// ✅ 正确写法：Repository 只暴露只读的 StateFlow，不再维护 UI 回调集合
object ProductRepository {
    private val _products = MutableStateFlow<List<Product>>(emptyList())
    val products: StateFlow<List<Product>> = _products.asStateFlow()

    fun notifyLoaded() {
        _products.value = load()
    }
}
```

但请注意：**把回调改成 `StateFlow` 只解决了一半问题！** 如果 UI 层收集 `StateFlow` 时用错了协程作用域，会立刻掉进下一个更隐蔽的坑——这正是我们要讲的场景三。

---

### 场景三：Fragment 协程用错 `lifecycleScope` 导致已销毁 View 滞留（`LEAK-3`）

这是目前使用 Kotlin 协程 + ViewBinding 的项目中**出现频率最高**的一类泄漏。

#### 1. 问题代码

在 `Fragment.onViewCreated()` 中收集 `Flow` 更新 UI 时，顺手写了 `lifecycleScope.launch`：

```kotlin
// ❌ 错误写法：在 Fragment.onViewCreated 中直接使用 lifecycleScope 收集数据并操作 View
override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
    val binding = FragmentListBinding.bind(view)

    lifecycleScope.launch {
        ProductRepository.products.collect { products ->
            binding.title.text = "共 ${products.size} 件"
        }
    }
}
```

#### 2. 为什么会泄漏？真实引用链与 `StateFlow` 订阅槽机制

为什么在 `Activity` 里用 `lifecycleScope` 没问题，在 `Fragment.onViewCreated()` 里用就会泄漏？

因为 **Fragment 拥有两条不重合的生命周期**：

- **Fragment 实例自身的生命周期（`lifecycle`）**：从 `onCreate` 到 `onDestroy`。
- **Fragment 视图的生命周期（`viewLifecycleOwner.lifecycle`）**：从 `onCreateView` 到 `onDestroyView`。

当通过 `replace().addToBackStack(null)` 从 `ListFragment` 跳转到 `DetailFragment` 时，**`ListFragment` 实例还活在返回栈里（没有走 `onDestroy`），但它的旧 View 已经被彻底销毁了（走了 `onDestroyView`）！**

此时，`lifecycleScope`（绑定的是 Fragment 实例）根本不会取消！更精彩的是 LeakCanary 抓到的真实引用链，它把 **`StateFlow` 在底层是如何拽住旧 View 的**展现得淋漓尽致：

```text
┬───
│ GC Root: Thread object
│
├─ ... → com.example.leakdemo.data.ProductRepository class [Leaking: NO]
│    ↓ static ProductRepository._products
│                               ~~~~~~~~~
├─ kotlinx.coroutines.flow.StateFlowImpl instance
│    ↓ AbstractSharedFlow.slots
│                         ~~~~~
├─ kotlinx.coroutines.flow.StateFlowSlot[] array
│    ↓ StateFlowSlot[2]
│                   ~~~
├─ kotlinx.coroutines.flow.StateFlowSlot instance
│    ↓ StateFlowSlot._state
│                    ~~~~~~
├─ java.util.concurrent.atomic.AtomicReference instance
│    ↓ AtomicReference.value
│                      ~~~~~
├─ kotlinx.coroutines.CancellableContinuationImpl instance
│    ↓ CancellableContinuationImpl.delegate
│                                  ~~~~~~~~
├─ kotlinx.coroutines.internal.DispatchedContinuation instance
│    ↓ DispatchedContinuation.continuation
│                             ~~~~~~~~~~~~
├─ kotlinx.coroutines.flow.StateFlowImpl$collect$1 instance
│    Anonymous subclass of kotlin.coroutines.jvm.internal.ContinuationImpl
│    ↓ StateFlowImpl$collect$1.L$1
│                              ~~~
├─ com.example.leakdemo.ListFragment$onViewCreated$1$1 instance
│    Anonymous class implementing kotlinx.coroutines.flow.FlowCollector
│    ↓ ListFragment$onViewCreated$1$1.$binding
│                                     ~~~~~~~~
├─ com.example.leakdemo.databinding.FragmentListBinding instance
│    Retaining 185.8 kB in 1394 objects
│    ↓ FragmentListBinding.rootView
│                          ~~~~~~~~
╰→ android.widget.LinearLayout instance
     Leaking: YES (ListFragment received Fragment#onDestroyView() callback)
     mContext instance of com.example.leakdemo.MainActivity with mDestroyed = false
```

请仔细看这条硬核链路：

1. `StateFlow.collect` 是一个永不正常结束的挂起函数（返回值类型是 `Nothing`）。当没有新值发射时，收集协程会挂起在 `StateFlowSlot`（订阅槽）的 `AtomicReference` 上。
2. 订阅槽持有了挂起协程的续体 `CancellableContinuationImpl` → 续体持有了状态机 `StateFlowImpl$collect$1` → 状态机的局部变量槽位 `L$1` 持有了你传入的匿名收集器 `FlowCollector` → 而这个 `FlowCollector` 的 `$binding` 字段持有了 `FragmentListBinding`！
3. 只要收集协程没被取消，`StateFlow` 的订阅槽就会顺着这条链把已销毁的 `LinearLayout` 整棵视图树牢牢拴在内存里；每进出一次返回栈，就多攒一棵死掉的 View 树！

#### 3. 标准修复方案（对应 Tag：`step3-fix-leak3`）

在 Fragment 中凡是涉及操作 View / `ViewBinding` 的协程，**必须绑定 `viewLifecycleOwner.lifecycleScope`，并配合 `repeatOnLifecycle(Lifecycle.State.STARTED)`**：

```kotlin
// ✅ 正确写法：绑定 View 的生命周期，且仅在视图可见（STARTED）时收集
override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
    val binding = FragmentListBinding.bind(view)

    viewLifecycleOwner.lifecycleScope.launch {
        viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
            ProductRepository.products.collect { products ->
                binding.title.text = "共 ${products.size} 件"
            }
        }
    }
}
```

这样一来：

- 当页面退到后台或进入返回栈（低于 `STARTED` 状态）时，`repeatOnLifecycle` 会自动取消内部的 `collect` 协程，`StateFlowSlot` 中的续体引用立即清空；
- 当 `onDestroyView()` 触发时，`viewLifecycleOwner` 变为 `DESTROYED`，外层协程也彻底结束，旧 View 树得以瞬间回收（实测修复后，`Views` 计数直接从 **556** 降到了 **436**，`ProductRepository._products` 泄漏彻底清零）。

> **📝 补充规范**：如果 Fragment 中将 `binding` 声明为了类成员变量（`private var _binding: FragmentListBinding? = null`），必须在 `onDestroyView()` 中显式执行 `_binding = null`。而像上面代码那样使用 `Fragment(R.layout.fragment_list)` 并在 `onViewCreated` 中用局部变量 `val binding = FragmentListBinding.bind(view)` + `viewLifecycleOwner`，则连手动置空都省去了，更加安全。

---

### 场景四：自定义 `CoroutineScope` 中挂起的协程捕获 UI 回调（`LEAK-4`）

#### 1. 问题代码

很多团队在把老代码迁移到协程时，喜欢写一种"半协程半回调"的包装类——在单例内部自己 `new` 一个 `CoroutineScope`，对外依然提供传统的回调方法：

```kotlin
// ❌ 错误写法：单例内部维护永不取消的 Scope，启动协程后回调 UI
object LocationTracker {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    fun requestOnce(onResult: (String) -> Unit) {
        scope.launch {
            val result = FakeSdk.awaitResult() // 挂起等待定位或网络结果（可能超时或永不返回）
            onResult(result)                   // 回调 Lambda 捕获了 DetailActivity！
        }
    }
}

// 在 DetailActivity.onCreate() 中调用：
LocationTracker.requestOnce { text ->
    binding.status.text = text
}
```

#### 2. 真实引用链与机制解析

这类泄漏极具迷惑性：代码里既没有 `static var context`，也没有 `addListener` 忘记注销，为什么会泄漏？来看 LeakCanary 抓到的真实引用链：

```text
┬───
│ GC Root: Thread object
│
├─ ... → com.example.leakdemo.util.FakeSdk class [Leaking: NO]
│    ↓ static FakeSdk.pending
│                     ~~~~~~~
├─ kotlinx.coroutines.CompletableDeferredImpl instance
│    ↓ JobSupport._state$volatile → NodeList → ResumeAwaitOnCompletion.continuation
├─ kotlinx.coroutines.JobSupport$AwaitContinuation instance
│    ↓ CancellableContinuationImpl.delegate → DispatchedContinuation.continuation
├─ com.example.leakdemo.util.LocationTracker$requestOnce$1 instance
│    Anonymous subclass of kotlin.coroutines.jvm.internal.SuspendLambda
│    ↓ LocationTracker$requestOnce$1.$onResult
│                                    ~~~~~~~~~
├─ com.example.leakdemo.DetailActivity$$ExternalSyntheticLambda0 instance
│    ↓ DetailActivity$$ExternalSyntheticLambda0.f$0
│                                               ~~~
├─ com.example.leakdemo.databinding.ActivityDetailBinding instance
│    ↓ ActivityDetailBinding.rootView
├─ android.widget.LinearLayout instance [Leaking: YES (View.mContext references a destroyed activity)]
│    ↓ View.mContext
╰→ com.example.leakdemo.DetailActivity instance [Leaking: YES, mDestroyed = true]
```

**底层机制一目了然**： Kotlin 编译器会将 `scope.launch { ... }` 的协程体编译成一个状态机子类 `LocationTracker$requestOnce$1`（继承自 `SuspendLambda`）。因为挂起点 `FakeSdk.awaitResult()` 恢复之后还要接着调用 `onResult(result)`，**状态机对象必须把参数 `$onResult` 保存在自己的成员字段里**！

当异步操作迟迟没有返回（例如弱网超时、硬件定位未就绪，或第三方 SDK 异常未回调）时，这个挂起的续体就一直挂在异步源（如 `CompletableDeferred` 的等待链表 `NodeList`）上。由于 `LocationTracker.scope` 绑定的是永不取消的 `SupervisorJob()`，即便用户早就关掉了 `DetailActivity`，这个挂起协程也永远不会被取消，`$onResult` 也就一直拽着 `DetailActivity` 不放。

#### 3. 标准修复方案（对应 Tag：`step4-fix-leak4`）

遵循 Kotlin 协程的**结构化并发**（Structured Concurrency）原则：**单例 / 工具类不自己私建执行 UI 回调的 `CoroutineScope`，而是直接对外暴露 `suspend` 挂起函数，把协程的启动与生命周期管理权交给调用方（UI 层的 `lifecycleScope` 或 `viewModelScope`）**：

```kotlin
// ✅ 正确写法 1：工具类只暴露挂起函数，不持有 UI 回调，也不私建未绑定的 Scope
object LocationTracker {
    suspend fun awaitOnce(): String = FakeSdk.awaitResult()
}

// ✅ 正确写法 2：由 Activity 自己的 lifecycleScope 启动，页面销毁时协程自动取消
class DetailActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val binding = ActivityDetailBinding.inflate(layoutInflater)
        setContentView(binding.root)

        lifecycleScope.launch {
            binding.status.text = LocationTracker.awaitOnce()
        }
    }
}
```

```kotlin
suspend fun awaitLocation(): Location = suspendCancellableCoroutine { cont ->
    val callback = object : SdkCallback {
        override fun onSuccess(loc: Location) { cont.resume(loc) }
    }
    ThirdPartySdk.register(callback)
    // 关键：当外部 lifecycleScope 因页面销毁而 cancel 时，立即从 SDK 移除 callback
    cont.invokeOnCancellation { ThirdPartySdk.unregister(callback) }
}
```

> **💡 进阶要点：将第三方回调式 SDK 桥接为 `suspend` 函数时，务必用 `suspendCancellableCoroutine`** 如果底层是一个传统的回调式 SDK（如 `ThirdPartyLocation.request(callback)`），在将其封装为 `suspend` 函数时，必须在 `invokeOnCancellation` 中反注册该回调，确保外部 `lifecycleScope` 取消时，SDK 内部的回调引用同步清空：

修复场景四后，持有 `DetailActivity` 的最后一条引用链被彻底斩断，20 轮压测后的 `Activities` 计数直接从 **41 骤降到 22**（20 个 `DetailActivity` 全部被 GC 回收），`Views` 从 **436 骤降到 208**。

---

### 场景五：Jetpack Compose 中注册系统回调未清理（`LEAK-5`）

#### 1. 问题代码

进入 Jetpack Compose 时代后，很多开发者在 `@Composable` 函数里需要监听系统状态（网络变化、广播、传感器、生命周期等），习惯性地写在 `LaunchedEffect(Unit)` 里：

```kotlin
// ❌ 错误写法：在 LaunchedEffect 中向系统服务注册了回调，但离开组合时没有反注册
@Composable
fun NetworkBanner() {
    val context = LocalContext.current
    LaunchedEffect(Unit) {
        val cm = context.getSystemService(ConnectivityManager::class.java)
        cm.registerDefaultNetworkCallback(object : ConnectivityManager.NetworkCallback() {
            override fun onLost(network: Network) {
                Toast.makeText(context, "网络断开", Toast.LENGTH_SHORT).show()
            }
        })
    }
}
```

#### 2. 真实引用链与机制解析

当 `ComposeActivity` 退出销毁后，LeakCanary 给出了如下引用链：

```text
┬───
│ GC Root: System class
│
├─ android.net.ConnectivityManager class
│    Leaking: NO (a class is never leaking)
│    ↓ static ConnectivityManager.sCallbacks
│                                 ~~~~~~~~~~
├─ java.util.HashMap instance
│    Leaking: UNKNOWN
│    Retaining 878.2 kB in 17329 objects
│    ↓ HashMap[instance @113118880 of android.net.NetworkRequest]
│             ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
├─ com.example.leakdemo.ComposeActivityKt$NetworkBanner$1$1$1 instance
│    Leaking: UNKNOWN
│    Anonymous subclass of android.net.ConnectivityManager$NetworkCallback
│    $context instance of com.example.leakdemo.ComposeActivity with mDestroyed = true
│    ↓ ComposeActivityKt$NetworkBanner$1$1$1.$context
│                                            ~~~~~~~~
╰→ com.example.leakdemo.ComposeActivity instance
     Leaking: YES (ObjectWatcher was watching this because com.example.leakdemo.ComposeActivity received
     Activity#onDestroy() callback and Activity#mDestroyed is true)
     Retaining 110.1 kB in 2171 objects
```

这条链路非常典型：

- **GC Root 是 `System class`**：Android 系统的 `ConnectivityManager` 内部有一个静态的 `sCallbacks`（`HashMap<NetworkRequest, NetworkCallback>`），专门存放当前进程注册的所有网络监听回调以跨 Binder 接收系统通知。
- **匿名内部类捕获 `$context`**：我们在 `registerDefaultNetworkCallback` 里创建的匿名 `NetworkCallback` 子类，因为要在 `onLost` 里弹 Toast 而捕获了外部的 `context`（即宿主 `ComposeActivity`）。
- `LaunchedEffect` 在离开 Composition 时只会取消它自己的协程，**绝不会自动帮你调用系统的 `unregisterNetworkCallback`**。于是每一个打开又关闭的 `ComposeActivity`（每个重达 110.1 kB）都永远留在了 `ConnectivityManager.sCallbacks` 的静态哈希表里。

#### 3. 标准修复方案（对应 Tag：`step5-fix-leak5`）

在 Compose 中，**凡是需要"注册 + 反注册"成对清理的跨边界副作用，一律使用 `DisposableEffect`**，并在 `onDispose` 块中完成反注册：

```kotlin
// ✅ 正确写法：使用 DisposableEffect，在离开 Composition 时成对调用 unregisterNetworkCallback
@Composable
fun NetworkBanner() {
    val context = LocalContext.current
    DisposableEffect(context) {
        val cm = context.getSystemService(ConnectivityManager::class.java)
        val callback = object : ConnectivityManager.NetworkCallback() {
            override fun onLost(network: Network) {
                Handler(Looper.getMainLooper()).post {
                    Toast.makeText(context, "网络断开", Toast.LENGTH_SHORT).show()
                }
            }
        }
        cm.registerDefaultNetworkCallback(callback)
        onDispose {
            cm.unregisterNetworkCallback(callback)
        }
    }
}
```

#### 💡 高频误区辨析：在 Compose 里用 `remember` 记住 `Context` 会内存泄漏吗？

社区里有一种流传很广的说法：*"在 Composable 里把 `LocalContext.current` 存进 `remember` 会导致 Activity 内存泄漏。"*

**这个说法是错误的。** 我们从原理和实测两个维度直接给出定论：

```kotlin
@Composable
fun RememberContextScreen() {
    val context = LocalContext.current
    val heldContext = remember(context) { context }
    Text("Package: ${heldContext.packageName}")
}
```

1. **原理层面**：`remember` 并不是静态变量或全局单例，它只是把计算结果缓存在当前 `Composition` 的 **Slot Table（槽表）** 中。当 Composable 离开组合树，或者宿主 `Activity` 销毁触发 `Composition.dispose()` 时，整张 Slot Table 都会随之一同释放，根本不会产生跨生命周期的 GC Root。
2. **实测验证**：我们在 `LeakDemo` 中专门构建了独立页面验证该写法，反复进出并触发 LeakCanary 检测，**没有任何滞留对象产生（0 Leak）**。只有当你把 `context` 传给未注销的系统回调（如上面的 `ConnectivityManager`）或存入单例对象时，才会发生泄漏。

---

### 3.6 五步根治全流程量化对比总表

将 `LEAK-1` 至 `LEAK-5` 全部修复后，我们在小米 13 Pro 上用完全相同的 20 轮压测脚本（每步重复 3 轮取中位数）汇总演进数据：

| 阶段与 Git Tag | 修复内容 | `Activities` 计数（dumpsys） | `Views` 计数（dumpsys） | 剩余未修复的泄漏源 | Java Heap 水位（20 轮后 GC） |
|---|---|---|---|---|---|
| **Step 0 (`step0-leaky`)** | 初始问题基线（含 5 处泄漏） | **41** | **556** | `ImageHelper.context`、`ProductRepository.listeners`、Fragment `lifecycleScope`、`FakeSdk.pending`、`ConnectivityManager.sCallbacks` | **13.1 MB**（持续抬升） |
| **Step 1 (`step1-fix-leak1`)** | 修复 ①：`ImageHelper` 改存 `applicationContext` | 41（仍被 ④ 共同持有） | 556 | 剩余 ②、③、④、⑤ | — |
| **Step 2 (`step2-fix-leak2`)** | 修复 ②：`ProductRepository` 移除回调列表改为 `StateFlow` | 41 | 556 | 剩余 ③（`StateFlowSlot` 持有旧 View）、④、⑤ | — |
| **Step 3 (`step3-fix-leak3`)** | 修复 ③：Fragment 改用 `viewLifecycleOwner` + `repeatOnLifecycle` | 41 | **436**（旧 Fragment View 全部释放） | 剩余 ④、⑤ | — |
| **Step 4 (`step4-fix-leak4`)** | 修复 ④：`LocationTracker` 改为 `suspend` 函数交由 `lifecycleScope` 取消 | **22**（20 个 `DetailActivity` 全部释放） | **208** | 仅剩 ⑤（`ConnectivityManager.sCallbacks`） | — |
| **Step 5 (`step5-fix-leak5`)** | 修复 ⑤：Compose 改用 `DisposableEffect` 成对注销回调 | **1**（完全回落至主页面基线） | **16**（完全回落至主页面基线） | **0（全部清零）** | **7.9 MB**（平稳回落） |

从這张演进表可以清晰看到：

- **Step 3** 修好 Fragment 协程作用域后，滞留的 Fragment 旧视图树率先释放，`Views` 从 556 降至 436；
- **Step 4** 斩断持有 `DetailActivity` 的最后一条挂起协程链后，20 个 `DetailActivity` 一次性全部回收，`Activities` 从 41 降至 22；
- **Step 5** 补齐 Compose 的 `onDispose` 注销后，20 个 `ComposeActivity` 全部回收，`Activities` 精准回落到 **1**（仅剩 `MainActivity`），`Views` 回落到 **16**，所有泄漏彻底清零！

---

## 四、第四步：防回归门禁与线上监控——构建全链路治理闭环

把存量泄漏修完只是第一步。团队每天都在提交新代码，如何防止下周有人又随手写出一行 `ImageHelper.init(this)` 或 `lifecycleScope.launch`？

答案是：**在本地与 CI 构建自动化泄漏断言门禁，在线上建立低开销监控防线。**

### 4.1 本地与 CI 自动化门禁：把"无泄漏"变成 JUnit 断言

LeakCanary 官方提供了专门用于仪器化测试（Instrumentation Test）的依赖包 `leakcanary-android-instrumentation`：

```kotlin
// app/build.gradle.kts
dependencies {
    debugImplementation("com.squareup.leakcanary:leakcanary-android:2.14")
    androidTestImplementation("com.squareup.leakcanary:leakcanary-android-instrumentation:2.14")
}
```

它提供了两个核心武器，分别应对「**页面级销毁验证**」与「**Fragment 中间态视图销毁验证**」：

#### 武器 1：`DetectLeaksAfterTestSuccess` 规则（页面级自动门禁）

在测试类中声明 `@get:Rule val rule = DetectLeaksAfterTestSuccess()`。每当一个 `@Test` 用例执行通过后，该 Rule 会自动接管：等待受监视对象回收、触发 GC，一旦发现仍有未被回收的受监视对象（Activity / Fragment / View / ViewModel），立即在测试进程内用 Shark 解析堆并**直接让该 JUnit 用例报错失败，同时在控制台打印完整 Leak Trace**。

#### 武器 2：`LeakAssertions.assertNoLeaks(tag)`（中间生命周期定点断言）

对于像场景三那样"宿主 `MainActivity` 依然存活，但 `ListFragment` 进入返回栈导致旧 View 销毁"的场景，如果等整个测试结束、宿主 Activity 关闭后再检查，协程早就随宿主一起销毁了，会漏掉"返回栈滞留"问题。此时可以在宿主存活、Fragment 刚压入返回栈的时刻，直接调用 `LeakAssertions.assertNoLeaks()` 进行定点断言：

```kotlin
@RunWith(AndroidJUnit4::class)
class NoLeakTest {
    // 每个测试成功后，自动断言无受监视对象泄漏
    @get:Rule
    val rule = DetectLeaksAfterTestSuccess()

    @Test
    fun openAndCloseDetailActivity() {
        openAndFinishActivity("DetailActivity")
    }

    @Test
    fun openAndCloseComposeActivity() {
        openAndFinishActivity("ComposeActivity")
    }

    @Test
    fun fragmentOldViewReleasedWhileInBackStack() {
        // 1. 打开宿主 MainActivity，此时显示 ListFragment
        // 2. 点击进入 DetailFragment（ListFragment 压入返回栈，其旧 View 执行 onDestroyView）
        // 3. 在宿主 Activity 和 ListFragment 仍存活的状态下，立即定点断言旧 View 已无泄漏！
        LeakAssertions.assertNoLeaks("fragment-old-view-host-alive")
    }
}
```

在修复后的版本（`step6-regression-test`）上运行整套仪器化测试套件，5 个核心场景用例全部通过：

```bash
$ adb shell am instrument -w -e class com.example.leakdemo.NoLeakTest \\
    com.example.leakdemo.test/androidx.test.runner.AndroidJUnitRunner

Time: 10.563
OK (5 tests)
```

而一旦有代码提交引入了泄漏（例如未在 `onDispose` 中注销 `NetworkCallback`），门禁测试会立即拦截失败，并把精确到字段名的 Leak Trace 直接输出到构建日志中：

```text
Error in unregisteredNetworkCallbackMustFail(com.example.leakdemo.PositiveControlTest):
leakcanary.NoLeakAssertionFailedError: Application memory leaks were detected:
====================================
HEAP ANALYSIS RESULT
====================================
1 APPLICATION LEAKS

101520 bytes retained by leaking objects
┬───
│ GC Root: System class
│
├─ android.net.ConnectivityManager class
│    Leaking: NO (a class is never leaking)
│    ↓ static ConnectivityManager.sCallbacks
│                                 ~~~~~~~~~~
├─ java.util.HashMap instance
│    ↓ HashMap[instance @315524920 of android.net.NetworkRequest]
├─ com.example.leakdemo.ComposeActivityKt$NetworkBanner$1$1$1 instance
│    ↓ ComposeActivityKt$NetworkBanner$1$1$1.$context
│                                            ~~~~~~~~
╰→ com.example.leakdemo.ComposeActivity instance
     Leaking: YES (Activity#mDestroyed is true)

FAILURES!!!
Tests run: 1,  Failures: 1
```

将这条命令接入 CI 流水线（在 PR 合并或每晚构建时自动跑一遍核心页面进出用例），就能把绝大部分组件级内存泄漏直接拦截在合入主干之前。

---

### 4.2 线上怎么办？开发期之外的三道防线

既然 LeakCanary 这么好用，能不能直接把它开到线上正式包里？

**不能直接照搬开发期配置上生产。** 原因在于：

1. **主线程冻结（Freeze）**：调用 `Debug.dumpHprofData()` 导出堆文件时，ART 虚拟机会挂起所有线程数秒之久，线上用户会直接感受到严重的界面卡死甚至触发 ANR。
2. **文件体积与解析开销**：一个中大型 App 的原始 `.hprof` 文件动辄几百 MB，无论是本地磁盘占用、Shark 解析时的额外内存峰值，还是回传流量成本，都无法在线上全量承受。
3. **隐私合规风险**：完整的 `.hprof` 堆快照中包含内存中所有的字符串与业务对象明文，直接上传原始堆文件存在数据合规风险。

因此，成熟商业 App 在线上通常构建「**指标层 → 系统采样层 → 自研/开源 Dump 层**」三道防线：

#### 第一道防线（指标层）：[Android vitals](https://developer.android.com/topic/performance/vitals) 与 OOM / LMK 归因监控

在宏观层面，通过 Google Play Android vitals 或自建 APM 监控两项核心指标：

- **Java / Native OOM 崩溃率**：并在发生 OOM 捕获异常时（`UncaughtExceptionHandler`），附带上报当前的 `Runtime.totalMemory() - freeMemory()`、`dumpsys meminfo` 摘要指标、当前存活 Activity 栈列表与最近页面访问轨迹，辅助复现。
- **前台/后台异常终止率（`ApplicationExitInfo`）**：Android 11（API 30）引入了 `ActivityManager.getHistoricalProcessExitReasons()`，可在下次启动时查询上次进程退出的精确原因（如 `REASON_LOW_MEMORY` 被系统 LMK 杀掉、`REASON_CRASH`、`REASON_ANR`）以及当时的 PSS/RSS 水位。

#### 第二道防线（系统级现场层）：Android 15+ [`ProfilingManager`](https://developer.android.com/reference/android/os/ProfilingManager)

为了解决线上性能与内存问题难以复现的痛点，Android 15（API 35）正式引入了系统级受管采样 API `ProfilingManager`（通过 Jetpack `androidx.core.os.Profiling` 可简化调用）：

- 支持应用在线上向系统请求收集 **Java Heap Dump**、**Heap Profile**（采样堆分配）、**Stack Sampling** 与 **System Trace**。
- 由系统服务统一管控触发配额（Rate Limiting）并在后台完成采集与敏化处理，大幅降低了应用自建全量采集框架的门槛。在后续演进的 Android 版本中，还进一步扩展了基于异常事件（如 OOM 或高内存水位）的触发式采集能力（Trigger-based Profiling）。

#### 第三道防线（深度自研层）：基于 `fork` 子进程 Copy-on-Write 的高性能线上 Dump（以快手 [KOOM](https://github.com/KwaiAppTeam/KOOM) 为代表）

如果必须在全版本 Android 设备上拿到线上的 `.hprof` 引用链，工业界最经典的架构方案是利用 Linux 的 **`fork()` 写时复制（Copy-on-Write）机制**：

```text
① 阈值监控：后台线程周期性监控 Java 堆使用率（如超过 maxMemory 的 80% 持续超标）或 Activity 滞留数
        ↓
② 极短暂停与 fork：
   └─ 仅暂停 ART 虚拟机数毫秒 → 调用 Linux fork() 创建子进程 → 立即恢复主进程虚拟机运行！
   （主进程卡顿从数秒降至几十毫秒以内，用户几乎无感知）
        ↓
③ 子进程离线 Dump：
   └─ 子进程共享了 fork 瞬间主进程的内存镜像（Copy-on-Write），在子进程内安心执行 dumpHprofData()
        ↓
④ 堆文件裁剪与解析：
   └─ 剥离 .hprof 中的 Bitmap 像素数组、原始基本类型数组（byte[]/char[]）等敏感且庞大的纯数据段，
      仅保留对象引用图骨架（文件可从数百 MB 压缩至几 MB），或在端侧直接用 Shark 提取纯文本 Leak Trace 后上传
```

理解了这套 `Suspend VM → fork() → Resume VM → Child Process Dump & Strip` 的链路，你就掌握了大厂线上内存治理基础设施的核心设计精髓。

---

## 五、总结

### 速查表：5 条内存泄漏治理黄金法则

```text
✅ 1. 泄漏的本质是「生命周期错配」
      长寿命对象（单例 / 静态字段 / 系统服务 / 全局 Scope）持有了短寿命对象（Activity / View / Binding）。
      读 Leak Trace 只需锁定「最后一个 Leaking: NO」到「第一个 Leaking: YES」之间的波浪线引用（~~~~~~~）。

✅ 2. 单例与工具类严禁直接持有 Activity Context
      不需要 UI 主题能力的单例，在入口处统一转换为 context.applicationContext；
      记住：一个对象可能同时被多条引用链持有，单点修复以「该条引用链消失」为准，全部斩断后实例数才会回落。

✅ 3. Fragment 操作 View 的协程必须绑定 viewLifecycleOwner
      Fragment 的 lifecycleScope 活得比它的 View 更长（进入返回栈时 View 销毁但 Fragment 仍存活）；
      StateFlow 会通过订阅槽（StateFlowSlot）强引用挂起协程的 Continuation，进而拽住捕获的 ViewBinding，
      因此必须用 viewLifecycleOwner.lifecycleScope + repeatOnLifecycle(Lifecycle.State.STARTED)。

✅ 4. 异步等待遵循结构化并发，摒弃「私建 Scope + UI 回调」
      单例内不要用永不取消的自定义 CoroutineScope 启动协程再回调 UI；
      应直接对外暴露 suspend 函数（底层 SDK 用 suspendCancellableCoroutine 桥接并在取消时注销回调），
      交由 UI 层的 lifecycleScope 启动与自动取消。

✅ 5. 跨边界注册与注销必须成对，检测必须接入自动化闭环
      Compose 中注册系统回调必须用 DisposableEffect 并在 onDispose 中反注册（单纯 remember Context 不会泄漏）；
      开发期用 LeakCanary 自动捕获 → 本地与 CI 用 DetectLeaksAfterTestSuccess + LeakAssertions 做门禁 → 线上用三级防线兜底。
```

### 方法论升华

回顾本系列前四篇：前两篇让画面渲染不掉帧，第三篇让应用启动不白屏，而这一篇是**让应用在长时间高频使用下依然稳如磐石**。

内存泄漏最危险的地方在于它的**滞后性**——泄漏一个 Activity 只多占几十到几百 KB，开发自测点两下根本毫无察觉；但放到线上用户手里累加几十次，就会演变成频繁 GC 引起的卡顿（Jank），最终在某次加载图片或创建数组时引爆 OOM。把「**量化发现 → 读链定责 → 架构规范根治 → CI 门禁防回归**」做成工程习惯，才能真正终结猫鼠游戏式的修修补补。

### 下篇预告

这一篇我们解决的是「**不该活着的对象为什么没被回收**」（内存泄漏）。但内存治理还有同样关键的另一半战场：**所有对象都活得合情合理，一处泄漏都没有，为什么 App 内存依然居高不下、甚至直接触发 OOM？**

下一篇，我们将进入本系列第五篇——**《Android 内存占用优化与 OOM 治理实战》**：彻底看懂 `dumpsys meminfo` 的 PSS / RSS / Dalvik Heap / Native Heap 指标迷雾，实战演练大图采样解码、高频分配引起的内存抖动（Memory Churn）消除，以及有界缓存预算与系统低内存回调的协同机制。

---

## 附：演示工程与测量环境

1. **配套演示工程**：`LeakDemo`（包含 View + Fragment + ViewBinding 页面与 Jetpack Compose 页面，五处典型泄漏在源码中以 `LEAK-1` ~ `LEAK-5` 标记，修复处以 `FIXED LEAK-N` 对照说明）。
2. **演进 Git Tag 对照**：

  - `step0-leaky`：包含全部五处泄漏的初始基线版本
  - `step1-fix-leak1`：修复场景一（`ImageHelper` 改存 `applicationContext`）
  - `step2-fix-leak2`：修复场景二（`ProductRepository` 移除监听器列表，改为 `StateFlow`）
  - `step3-fix-leak3`：修复场景三（`ListFragment` 改用 `viewLifecycleOwner.lifecycleScope` + `repeatOnLifecycle`）
  - `step4-fix-leak4`：修复场景四（`LocationTracker` 改为 `suspend` 函数，交由 `DetailActivity.lifecycleScope` 调用）
  - `step5-fix-leak5`：修复场景五（`ComposeActivity` 的 `NetworkBanner` 改用 `DisposableEffect` 成对注销）
  - `step6-regression-test`：集成 `leakcanary-android-instrumentation` 自动化防回归测试套件

3. **测试设备与工具链版本**：

  - **测试真机**：小米 13 Pro（`2210132C / nuwa`），骁龙 8 Gen 2，Android 16 / API 36。
  - **构建与依赖版本**：JDK `17.0.0.1`、Gradle `8.7`、AGP `8.5.2`、Kotlin `2.0.21`、Compose BOM `2024.10.01`、LeakCanary `2.14`。
  - **构建分工**：`debug` 构建（集成 LeakCanary）用于采集 Leak Trace 与 `dumpsys meminfo` 组件计数；`release-like` 构建（不含 LeakCanary，开启 `<profileable android:shell="true"/>`）用于采集 20 轮进出页面的 Java Heap 内存趋势曲线。

4. **官方参考资料**：

  - [Manage your app's memory | Android Developers](https://developer.android.com/topic/performance/memory)
  - [LeakCanary Official Documentation](https://square.github.io/leakcanary/)
  - [Shark: Smart Heap Analysis Reports for Kotlin](https://square.github.io/leakcanary/shark/)
  - [ProfilingManager API Reference | Android Developers](https://developer.android.com/reference/android/os/ProfilingManager)
  - [KwaiAppTeam/KOOM: An OOM arbiter and memory monitoring solution](https://github.com/KwaiAppTeam/KOOM)
