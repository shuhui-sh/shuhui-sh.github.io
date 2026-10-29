---
title: "你的 Activity 关了，为什么还活着？Android 内存泄漏从发现、定位到线上治理"
date: 2026-10-28
description: "用户反馈：'用久了越来越卡，有时候直接闪退回桌面。' 先别急着看代码，用最朴素的办法验证：反复进出同一个页面，看内存会不会回落。"
tags: ['性能优化', 'Android']
draft: true
category: "技术"
---
> 本文是「Android 应用性能优化」系列第四篇。前三篇优化的是"画面怎么渲染、App 怎么启动"，这一篇优化的是"App 用着用着为什么越来越卡、最后被系统杀掉"。
>
> 读完本文你将掌握：用 `dumpsys meminfo` 和 LeakCanary 发现泄漏 → 读懂引用链定位根因 → 现代项目里最常见的五类泄漏模式及修复 → 用本地仪器化测试构建回归门禁，并了解 CI 与线上接入边界。
>
> **环境说明**：文中数据来自配套演示工程 `LeakDemo` 在**小米 13 Pro（骁龙 8 Gen 2，Android 16 / API 36）** 真机上的实测，泄漏点是按真实项目里常见的模式刻意埋入的，每处修复对应一个独立的 git tag。LeakCanary 版本 2.14。详见文末「附：演示工程与测量环境」。

---

## 一、问题提出：页面进进出出，内存只增不减

用户反馈："用久了越来越卡，有时候直接闪退回桌面。"

先别急着看代码，用最朴素的办法验证：**反复进出同一个页面，看内存会不会回落。**

```bash
# 查看进程里 Activity / View 等对象的数量
adb shell dumpsys meminfo com.example.leakdemo
```

输出里有一段 `Objects`：

```
 Objects
               Views:      556         ViewRootImpl:        6
         AppContexts:       88           Activities:       41
```

操作步骤：进入详情页，返回，重复 20 次（每轮还各进出一次 Fragment 详情页与 Compose 页），然后尝试发送 GC 信号，等待 10 秒再查看。**旧脚本吞掉了 `kill -10` 的错误，也没有保存 GC 完成证据，因此这里不是“已确认 GC 后”的活堆测量。** 对这个演示场景，退出页面后的对象计数应向只保留主页面的基线靠近；其他 App 不能套用统一的个位数阈值。

而旧实验的实测是：进出 20 轮之后，`Activities` 停在了 **41**，三轮重复测量都是这个数字。**这是进程级总数，不是按 Activity 类名统计的实例清单**，不能据此断言恰好残留了 20 个 `DetailActivity` 和 20 个 `ComposeActivity`；具体哪个已销毁对象仍可达，要继续看 heap dump 和引用链。

再持续观察内存：修复前后 `dumpsys meminfo` 的 Summary Java Heap 私有归因趋势不同（见文末量化对比）。它能提供进一步排查的线索，但不能单靠这条曲线证明泄漏，更不能把它当作已确认 GC 后的 Java 活对象大小。

这是值得继续排查的典型信号。若 heap dump 进一步确认页面生命周期已结束、仍被不合理的强引用链保留，才能把问题定位为内存泄漏：**该被回收的对象没有被回收，反复进入可能不断累积。**

你可能会问：Java/Kotlin 有垃圾回收，怎么还会泄漏？

因为 GC 回收的标准不是"你还用不用它"，而是"**还有没有路径能从 GC Root 走到它**"。你以为已经关掉的页面，只要有一条引用链还连着它，GC 就不会动它。泄漏的本质不是"没释放"，而是"**还被引用**"。

---

## 二、相关知识点讲解

### 2.1 泄漏的本质：GC Root 可达性

GC 判断一个对象能不能回收，做的是一次"可达性分析"：从一批固定的起点（GC Root，比如运行中的线程、静态字段、系统持有的引用）出发，沿着引用往下找，**找得到的对象就是活的**。

```
GC Root（静态字段 / 线程 / 系统服务…）
   │
   └─→ 对象 A ─→ 对象 B ─→ 已经 finish() 的 DetailActivity   ← 本该被回收，却可达
```

所以排查泄漏的核心问题只有一个：**这条链上，哪一个引用是不该存在的？** 找到它、断开它，就修好了。

一个常用的判断标准是"生命周期匹配"：**长寿命的对象不应该持有短寿命对象的引用。** 静态变量和单例活得和进程一样久，Activity 活得只有一个页面那么久；前者在页面销毁后仍不合理地强引用后者，才是需要治理的生命周期错配。短时间持有并及时解除，并不自动构成泄漏。Android 官方的 [Manage your app's memory](https://developer.android.com/topic/performance/memory) 也是按这个思路来讲的。

### 2.2 LeakCanary 是怎么发现泄漏的

LeakCanary 的思路不是盯着内存曲线，而是**盯着具体的对象**：

```
① 对象生命周期结束时（Activity.onDestroy、Fragment 视图销毁、ViewModel 清除…），
   交给 ObjectWatcher，用弱引用持有它
        ↓
② 等待一小段时间，并触发 GC
        ↓
③ 弱引用还没被清除 = 对象仍被保留（retained）
        ↓
④ 保留对象累积到阈值后，dump 堆（.hprof）
        ↓
⑤ 用 Shark 解析 hprof，找出从 GC Root 到该对象的最短引用链（leak trace）
```

几个要点，其中两条我们在实测中直接得到了印证：

- 默认自动监视的对象：销毁的 Activity、销毁的 Fragment、Fragment 的 View、清除的 ViewModel。对 **Fragment 的 View** 的覆盖，是 LeakCanary 相比 Android Studio 自带过滤的一个重要优势（后文 Step 3 会用到）。
- **dump 阈值**：为了不频繁打断你，它会等保留对象累积到一定数量才 dump。实测 logcat 里明确打印了 `Found 8 objects retained, dumping heap now (app is visible & >=5 threshold)`——**前台时的阈值就是 5 个**；之前一次 `Found 4 objects retained, not dumping heap yet` 则是没到阈值。
- 它会区分 **Application Leak** 和 **Library Leak**。后者表示引用链匹配了已知库或系统问题的规则，不等于“一定无法修复”：仍可评估升级、规避或库内修复；前者也不能直接等同于“已经证明是业务代码的错”。

引入方式很简单，只放进 debug 构建（[LeakCanary 官方文档](https://square.github.io/leakcanary/)）：

```kotlin
// app/build.gradle.kts
dependencies {
    debugImplementation("com.squareup.leakcanary:leakcanary-android:2.14")
}
```

不需要写任何初始化代码。这里正好呼应第三篇：LeakCanary 的自动安装靠的正是一个 ContentProvider。翻开 debug 包的 Merged Manifest，可以看到以下 Provider（合并结果不代表四者都由 LeakCanary 注入）：

```xml
<provider android:name="androidx.startup.InitializationProvider" ... />
<provider android:name="leakcanary.internal.LeakCanaryFileProvider" ... />
<provider android:name="leakcanary.internal.MainProcessAppWatcherInstaller" ... />
<provider android:name="leakcanary.internal.PlumberInstaller" ... />
```

其中 `androidx.startup.InitializationProvider` 属于 AndroidX Startup，具体由哪个依赖引入应查 Manifest 合并来源，不能一并归因给 LeakCanary。`MainProcessAppWatcherInstaller` 才是这里的 AppWatcher 自动安装入口——它在 `Application.onCreate()` 之前执行，这正符合第三篇讲的 ContentProvider 时序。而因为它只在 debug 构建里，不会影响线上的启动速度。

### 2.3 怎么读 leak trace

LeakCanary 报告里最重要的就是引用链。下面是实测抓到的第一条（已略去中间的数组下标等噪声）：

```
┬───
│ GC Root: Thread object
│
├─ android.os.HandlerThread instance
│    Thread name: 'LeakCanary-Heap-Dump'
│    ↓ Thread.contextClassLoader
├─ dalvik.system.PathClassLoader instance
│    ↓ ClassLoader.runtimeInternalObjects
├─ java.lang.Object[] array
│    ↓ Object[1533]
├─ com.example.leakdemo.util.ImageHelper class
│    Leaking: NO (a class is never leaking)
│    ↓ static ImageHelper.context
│                         ~~~~~~~
╰→ com.example.leakdemo.DetailActivity instance
     Leaking: YES (Activity#mDestroyed is true)
     Retaining 66.6 kB in 1297 objects
```

读法：

1. **从上往下读**，第一行是 GC Root，最后一行是被泄漏的对象。
2. 每个节点下面有 `Leaking: YES/NO/UNKNOWN`，LeakCanary 会根据对象状态推断。**先找最后一个 `Leaking: NO` 到第一个 `Leaking: YES` 之间的候选引用区间，再结合对象应有的生命周期判断责任边。** 中间可能夹着多个 `UNKNOWN`，不能机械认定紧邻首个 `YES` 的上一条边就是根因。 报告里还会用 `~~~~~~~` 直接把最可疑的字段标出来（这里是 `context`）。
3. 引用的写法（`↓ static ImageHelper.context`）直接告诉你是哪个类的哪个字段。

> 一个反直觉的细节：这条链的 GC Root 不是 `Application`，而是一个 `Thread`。因为 `ImageHelper` 是被 `PathClassLoader` 加载的类，类加载器又被某个线程的 `contextClassLoader` 持有——**静态字段的可达性，往往要追溯到"加载这个类的类加载器被谁持有"**。所以看到 `Thread` 作为 GC Root 不用奇怪，真正要看的是链路末端那个"不该活着"的对象。

![LeakCanary 报告：GC Root、Leaking: YES 与最可疑引用](/images/你的-Activity-关了-为什么还活着-Android-内存泄漏从发现-定位到线上治理/shot03_leakcanary_trace.png)

### 2.4 工具链：什么场景用什么

| 工具 | 适合做什么 | 局限 |
|------|-----------|------|
| `dumpsys meminfo` | 快速发现可疑增长：看 Activities / Views 数量和内存趋势 | 只是线索，不能独立确诊，也不提供按类实例归因 |
| LeakCanary | 自动发现并给出引用链 | 本文仅在 debug 集成；完整 dump 与分析有停顿、资源及隐私成本 |
| Memory Profiler | 手动抓 heap dump，看对象实例数、占用大小 | 需要手动操作 |
| 平台内存与 profiling 能力 | 按目标 API 和设备能力评估压力测试、现场采样 | 版本、权限和数据类型须核对官方文档，本文不作新版本实测结论 |

### 2.5 现代项目里的五类泄漏模式

网上很多文章把泄漏写成"症状清单"（Handler、AsyncTask……）。更有用的归类方式是**按架构模式**。下面是我们在演示工程里埋的五类，每类都是现代项目里真实会写出来的代码。

**① 长寿命对象持有 Activity / Context（最经典）**

```kotlin
// ❌ 单例里存了 Activity
object ImageHelper {
    lateinit var context: Context
    fun init(context: Context) { this.context = context }
}

// 在 DetailActivity.onCreate 里：
ImageHelper.init(this)     // 把 Activity 本身传了进去
```

```kotlin
// ✅ 只保存 Application Context
fun init(context: Context) { this.context = context.applicationContext }
```

仅当工作不依赖 Activity、窗口或 UI 主题时才适合这样替换；需要主题的 UI 操作应使用恰当的 UI Context，并把持有时间限制在对应生命周期内。

**② 单例 / Repository 持有 UI 回调，没有注销**

```kotlin
// ❌ 单例持有监听器，Fragment 销毁后没有 remove
object ProductRepository {
    private val listeners = mutableListOf<(List<Product>) -> Unit>()
    fun addListener(l: (List<Product>) -> Unit) { listeners += l }
}

// ListFragment.onViewCreated：
ProductRepository.addListener { products -> binding.title.text = "共 ${products.size} 件" }
// ↑ 这个 lambda 捕获了 binding → View → Activity
```

修复思路有两种：**成对注销**，或者**改成 Flow 并让 UI 层使用正确的生命周期作用域收集**（见 ③）。Flow 本身不会自动免疫泄漏：收集协程若活得过久，照样会保留它捕获的 View。

**③ 协程 / Flow 用错生命周期作用域（Fragment 里最常见）**

```kotlin
// ❌ lifecycleScope 是 Fragment 的生命周期，不是 View 的生命周期
override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
    val binding = FragmentListBinding.bind(view)
    lifecycleScope.launch {
        viewModel.uiState.collect { binding.title.text = it.title }   // 协程捕获了 binding
    }
}
```

Fragment 被放入返回栈时，它的 **View 被销毁（`onDestroyView`）但 Fragment 本身还活着**。此时这个协程还在运行，持有着已经销毁的 View。

```kotlin
// ✅ 用 View 的生命周期，并只在可见时收集
override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
    val binding = FragmentListBinding.bind(view)
    viewLifecycleOwner.lifecycleScope.launch {
        viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
            viewModel.uiState.collect { binding.title.text = it.title }
        }
    }
}
```

> 📝 同类问题还有：Fragment 把 `binding` 存成成员变量却不在 `onDestroyView` 里置空。

**④ 自定义 CoroutineScope 里挂起的协程，捕获了 UI 回调**

```kotlin
// ❌ 单例里的作用域永不取消，协程又在等一个"可能永远不会回来"的结果
object LocationTracker {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    fun requestOnce(onResult: (String) -> Unit) {
        scope.launch {
            val result = FakeSdk.awaitResult()    // 挂起，直到 SDK 回调
            onResult(result)                       // onResult 捕获了 Activity
        }
    }
}

// DetailActivity：
LocationTracker.requestOnce { text -> binding.status.text = text }
```

```kotlin
// ✅ 对外暴露挂起函数，由 UI 层的 lifecycleScope 调用，随生命周期取消
suspend fun awaitOnce(): String = FakeSdk.awaitResult()

lifecycleScope.launch { binding.status.text = LocationTracker.awaitOnce() }
```

这里还要求 `FakeSdk.awaitResult()` 支持协作式取消。真实 SDK 若用回调桥接为挂起函数，应通过 `suspendCancellableCoroutine` 等机制在取消时解除注册、释放捕获的 UI 引用；仅添加 `suspend` 修饰符或换一个 scope，并不会自动清理 SDK 内部的回调表。

**⑤ Compose 里注册了系统回调，没有清理**

```kotlin
// ❌ 注册之后没有注销，回调里还用到了 context
@Composable
fun NetworkBanner() {
    val context = LocalContext.current
    LaunchedEffect(Unit) {
        val cm = context.getSystemService(ConnectivityManager::class.java)
        cm.registerDefaultNetworkCallback(object : ConnectivityManager.NetworkCallback() {
            override fun onLost(network: Network) {
                Handler(Looper.getMainLooper()).post {
                    Toast.makeText(context, "网络断开", Toast.LENGTH_SHORT).show()
                }
            }
        })
    }
}
```

```kotlin
// ✅ DisposableEffect：离开 composition 时成对注销
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
        onDispose { cm.unregisterNetworkCallback(callback) }
    }
}
```

**一个需要先纠正写法、再独立验证的流行说法**

`remember { LocalContext.current }` 不是可直接使用的 Compose 写法：`LocalContext.current` 要在 composable 上下文读取，不能在 `remember` 的计算 lambda 中读取。正确的演示形式是：

```kotlin
@Composable
fun RememberContextScreen() {
    val context = LocalContext.current
    val rememberedContext = remember(context) { context }
    Text(rememberedContext.packageName)
}
```

这里使用 `remember(context)`，表示 Context 这个 key 变化时重新计算；`remember { context }` 则保存当前 composition 槽位首次计算时的值，两者对 Context 更新的语义不同，不应混为同一个测试条件。

从原理上说，`remember` 将值保存在对应 composition 的槽位中，并不会凭空增加一个进程级 GC Root。composition 正常销毁且没有其他长寿命持有者时，仅保存这个 Context 不足以证明 Activity 泄漏；反过来，值被转存到更长寿命对象，或 composition 本身没有正常释放，仍可能造成生命周期错配。

**旧结果不能充当独立阴性对照。** 旧 `RememberContextScreen` 与第 ⑤ 类系统回调共用 `ComposeActivity`，该 Activity 已因回调泄漏；“没有另一条 remember trace”无法区分 remember 的独立影响。

审核后增加 `RememberOnlyActivity`：只运行先读取 Context、再 `remember { context }` 的页面，不注册网络回调。测试先验证Activity实际启动及销毁，再让LeakCanary规则检查；独立运行得到 `OK (1 test)`。日志包含该Activity的 `onDestroy` watch，随后为 `No watched objects after triggering an explicit GC`。这表示**本场景、本次检测窗口中未留下待分析的受监视对象**，不是完成了一次“零泄漏HPROF”，也不能推广为任何remember用法都安全。完整证据见文末补测索引；另外用故意不注销网络回调的正对照确认同套检测确实能够报错。

另外，`NetworkCallback` 的回调不保证在主线程执行，上面的 Toast 示例显式切回 Main Looper；生产代码还要避免已投递的 UI 工作在页面退出后继续运行。

---

## 三、具体实例应用展示

**案例：商品浏览 App 的五处泄漏**

> **关于演示工程**：本文使用专门搭建的 `LeakDemo`，包含 View + Fragment 页面和 Compose 页面。五处泄漏是按上面的五类模式刻意埋入的，`FakeSdk` 用来模拟"可能永不回调"的第三方 SDK。它们在代码里都有 `LEAK-1` ~ `LEAK-5` 的标记，每个修复对应一个独立的 git tag（`step0-leaky` → `step5-fix-leak5`），方便对照。

### Step 0：复现与量化，先让泄漏"看得见"

用同一套脚本进出各个页面 20 轮（每轮各进出一次 `DetailActivity`、`DetailFragment`、`ComposeActivity`），结束后尝试发送 GC 信号、等待 10 秒，再测量。三轮重复取中位数；旧脚本未验证信号成功或 GC 完成：

| 指标 | 结果 |
|------|------|
| `dumpsys meminfo` 的 `Activities` | **41** |
| `dumpsys meminfo` 的 `Views` | **556** |
| 计数的解释边界 | **进程级 Activity 总数异常偏高**；不能由总数推算各 Activity 类的残留数量 |
| 人工归纳的关键持有字段 | **4 类**（`ImageHelper.context`、`ProductRepository.listeners`、`FakeSdk.pending`、`ConnectivityManager.sCallbacks`） |

![LeakCanary 泄漏列表](/images/你的-Activity-关了-为什么还活着-Android-内存泄漏从发现-定位到线上治理/shot04_leakcanary_list_step0.png)

**这里不能用“埋了 5 处、只看到 4 类”推导出“短链掩盖长链”。** 这 4 类是按关键字段人工归类，不是 LeakCanary 报告条数，更不是逐个缺陷的独立检出率。

更重要的是，Step 0 收集的是 **ViewModel 内的状态源**，Step 2 则在移除监听器的同时，改为收集 **单例 `ProductRepository._products`**。不仅移除了旧引用，还改变了 Flow 源的生命周期，是两个变量同时变化。后面出现新的 Flow trace，能证明新版本存在一条真实的持有路径，但不能倒推旧版本同一条路径一直存在、只是被短链挡住。要验证“掩盖”机制，必须固定状态源和其他代码，只切换某一条持有边；旧实验没有完成这个单变量对照。

---

### Step 1：修复 ① 单例持有 Activity

实测的 leak trace 就是 2.3 里那条：`static ImageHelper.context` 下方被 `~~~~~~~` 标为最可疑引用，末端是 `DetailActivity instance Leaking: YES (Activity#mDestroyed is true)`，保留 66.6 kB。

读 trace：`ImageHelper` 类标记为 `Leaking: NO`，`DetailActivity` 为 `YES`，两者之间的静态 `context` 是本例直接的候选责任边。结合 Activity 已销毁和单例仍存活的生命周期关系定位问题。修复见 2.5 ①：仅对不需要 UI 主题的工作保存 `applicationContext`。

**验证结果**：

```
Step 1 后：ImageHelper.context 这一类报告消失；
但 Activities 仍为 41（没有下降）
```

为什么修好了泄漏，`Activities` 却没降？因为 `DetailActivity` **同时被两条链持有**：① 的 `ImageHelper.context` 和 ④ 的挂起协程。修掉 ① 之后，④ 还拽着它。这提醒我们一个朴素的道理：**结合源代码、同类 trace 是否复现和实例是否释放来判断修复，不要只看总数降没降**——一个对象可能被多条链持有，断一条不等于释放。

---

### Step 2：修复 ② Repository 持有 UI 回调

我们的修复选择“**移除回调列表，改为 Flow，再修正收集作用域**”：

```kotlin
object ProductRepository {
    private val _products = MutableStateFlow<List<Product>>(emptyList())
    val products: StateFlow<List<Product>> = _products.asStateFlow()
}
```

回调列表不复存在，对这个列表忘记 `remove` 的问题被消除了；但 Flow 的订阅关系仍然必须在正确作用域内结束。

**接下来的结果恰好说明：改成 Flow 不等于修完泄漏。** Step 2 的旧记录中，`ProductRepository.listeners` 路径不再出现，却出现了 **`ProductRepository._products`**。这一步同时将收集源从 ViewModel 改为单例，因此这里把它作为新版本的真实持有链教学，不作为“旧链被掩盖”的实证。其引用链是：

```
GC Root: Thread object (ConnectivityThread)
  ↓ static ProductRepository._products
  ↓ StateFlowImpl（AbstractSharedFlow.slots）
  ↓ StateFlowSlot → AtomicReference.value
  ↓ CancellableContinuationImpl → DispatchedContinuation
  ↓ StateFlowImpl$collect$1.L$1
  ↓ ListFragment$onViewCreated$1$1.$binding   ← 收集 StateFlow 的匿名 FlowCollector
  ↓ FragmentListBinding.rootView
LinearLayout（ListFragment 已销毁的 View）  Leaking: YES
```

这条链把"Flow 用错作用域"的机制讲得清清楚楚：**StateFlow 会通过订阅槽（`StateFlowSlot`）持有正在收集它的协程续体（Continuation），续体上挂着那个匿名的 `FlowCollector`，而它捕获了 `$binding`。** 只要收集协程还在跑，StateFlow 就把你的 View 一起拽住。

```
Step 2 后：ProductRepository.listeners 消失；
新版本出现 ProductRepository._products（LEAK-3）持有链
```

---

### Step 3：修复 ③ Fragment 里的协程作用域

上一步的 trace 已经定位到了根因：收集 StateFlow 的协程用的是 **Fragment 的 `lifecycleScope`**，Fragment 进入返回栈、View 销毁后它还在收集。修复见 2.5 ③：改用 `viewLifecycleOwner.lifecycleScope` + `repeatOnLifecycle(STARTED)`，让收集只发生在 View 存活且可见的区间。

**这一步要注意：它是"滞留"而不是"永久泄漏"**。这个泄漏只在 Fragment 还在返回栈里时存在，Fragment 真正销毁后，协程被取消，引用链随之断开。但返回栈里的 Fragment 可能活很久，而且每个都背着一整棵已销毁的 View 树——这也解释了为什么 LeakCanary 会单独监视 **Fragment 的 View**：它的生命周期和 Fragment 本身并不同步，是 Android Studio 默认过滤容易漏掉的一类。

```
Step 3 后：ProductRepository._products 这一类消失；
剩余报告只剩 FakeSdk.pending 和 ConnectivityManager.sCallbacks 两类
```

---

### Step 4：修复 ④ 自定义 Scope 中挂起的协程

第 ④ 类的真实引用链（已略去中间一长串协程帧）：

```
GC Root: Thread object
  ↓ static FakeSdk.pending
  ↓ CompletableDeferredImpl → …（一串协程挂起帧）…
  ↓ LocationTracker$requestOnce$1.$onResult
  ↓ DetailActivity$$ExternalSyntheticLambda0.f$0
  ↓ ActivityDetailBinding.rootView
  ↓ LinearLayout（View.mContext）
DetailActivity instance  Leaking: YES (mDestroyed = true)
```

这类泄漏最隐蔽：**没有任何"忘记注销"的动作可以指给你看**，只是协程在等一个永远不来的结果。修复思路见 2.5 ④：**让异步结果的等待发生在有生命周期的作用域里**——`LocationTracker` 改成对外暴露 `suspend fun awaitOnce()`，由 `DetailActivity` 的 `lifecycleScope` 调用。

**验证结果**，这一次数量终于降了：

```
Step 4 后：FakeSdk.pending 全部消失；
Activities 的阶段中位数从 41 降到 22；Views 从上一步 436 降到 208（Step 0 为 556）
```

代码修复和 `FakeSdk.pending` 路径不再出现，与对象计数下降相互支持；但 **41 → 22 只减少了 19，而且是进程总数**，不能据此断言 20 个 `DetailActivity` 已全部回收。已销毁实例是否逐一释放，需要类级 heap 统计或独立 ObjectWatcher 证据。本阶段人工整理的 trace 中，剩余关键持有字段为第 ⑤ 类。

---

### Step 5：修复 ⑤ Compose 里的系统回调

第 ⑤ 类的真实引用链：

```
GC Root: System class
  ↓ static ConnectivityManager.sCallbacks
  ↓ HashMap（键为 NetworkRequest）
  ↓ ComposeActivityKt$NetworkBanner$1$1$1.$context   ← 匿名 NetworkCallback 子类
ComposeActivity instance  Leaking: YES (mDestroyed = true)，Retaining 110.1 kB
```

这条链证实了文章开头的猜想：系统的 `ConnectivityManager` 确实通过一张静态的 `sCallbacks` 回调表持有我们注册的 `NetworkCallback`，而匿名回调类又捕获了 `ComposeActivity` 的 `context`。注册时不注销，页面就永远回不了收。修复见 2.5 ⑤：`DisposableEffect` 里 `onDispose` 成对注销。

**验证结果**：

```
Step 5 旧数据库导出：返回错误文本，不能据此统计分析数或宣称报告归零；
Activities 中位数回落到 1，Views 回落到 16，计数接近主页面基线
```

**验证边界**：对象计数恢复接近基线，是修复有效的支持证据，不等于所有对象、所有路径均已证明无泄漏。Step 5 的旧数据库文件实际是错误文本，不能充当“零分析”或“零泄漏报告”证据；remember 独立对照亦不能由同 Activity 的旧 trace 推出，需另行测试。

---

### Step 6：防回归，先跑通本地门禁，再接入 CI

修好之后，怎么保证以后不会再引入？把"无泄漏"变成一条自动化断言。LeakCanary 提供了仪器化测试的集成：

```kotlin
// app/build.gradle.kts
dependencies {
    androidTestImplementation("com.squareup.leakcanary:leakcanary-android-instrumentation:2.14")
}
```

核心是一个 JUnit Rule——`DetectLeaksAfterTestSuccess`：每个测试**通过后**，按其检测配置检查被监视对象并执行泄漏分析，检测到符合失败条件的应用泄漏时让测试失败。它不是对整个进程所有对象的穷尽证明，监视范围、等待窗口和已知库匹配规则都会影响结果。

```kotlin
// 概念示意：完整状态断言见NoLeakTest.kt，不能只启动后sleep就算覆盖。
@get:Rule
val rule = DetectLeaksAfterTestSuccess()

@Test
fun rememberOnlyIsolated() {
    openAndClose("RememberOnlyActivity")
    // helper检查实际进入目标Activity、finish后有界等待isDestroyed。
    // 测试体成功后，Rule才执行受监视对象检测。
}
```

> **本机执行记录**：原先的ActivityScenario实验在本机同步启动/关闭路径出现挂起，根因没有独立隔离，不能据此认定所有MIUI或Android16都存在兼容问题。配套工程改用UiAutomator发起启动，Instrumentation主线程断言页面与生命周期，再主动finish并等待实际销毁；不是只靠固定sleep推断成功。

旧版在本机运行 instrumentation，两个用例通过；以下保留原始输出：

```
Time: 7.635
OK (2 tests)
```

然后我们**故意回退**第 ⑤ 处修复（`DisposableEffect` 改回注册后不注销），再跑——`ComposeActivity` 用例立刻按预期失败，而且失败输出里直接给出了那条我们熟悉的引用链：

```
Error in openAndCloseComposeActivity(com.example.leakdemo.NoLeakTest):
leakcanary.NoLeakAssertionFailedError: Application memory leaks were detected:
1 APPLICATION LEAKS
101520 bytes retained by leaking objects
│    ↓ static ConnectivityManager.sCallbacks
│    ↓ ComposeActivityKt$NetworkBanner$1$1$1.$context (mDestroyed = true)
╰→ com.example.leakdemo.ComposeActivity instance
     Leaking: YES (Activity#mDestroyed is true)

assertionTag: DetectLeaksAfterTestSuccess
Tests run: 2,  Failures: 1
```

这组旧实验只证明本地两条用例能够运行，并能拦截故意恢复的第⑤类泄漏。审核后补齐了状态与生命周期断言，真机重新运行：

| 本轮检测 | 结果 | 证据文件 |
|----------|------|----------|
| 默认修复版五项套件 | `OK (5 tests)`，10.563s | `fixed-followup-instrumentation.txt` |
| 独立remember-only | `OK (1 test)` | `remember-only-instrumentation.txt` |
| 故意不注销网络回调 | `Tests run: 1, Failures: 1`，确有泄漏断言与sCallbacks链 | `positive-instrumentation-2.txt` |

五项套件覆盖DetailActivity、ComposeActivity、MainActivity、独立remember页面，以及**Fragment进入返回栈时的旧View**。最后一项不是关闭整个宿主后才检查：测试在主线程确认宿主仍活着、ListFragment.view为null、旧viewLifecycleOwner已DESTROYED、返回栈数量为1，再在该状态调用：

```kotlin
LeakAssertions.assertNoLeaks("fragment-old-view-host-alive")
```

之后返回，验证新View非空、新viewLifecycleOwner与旧owner不同、状态为RESUMED，再关闭宿主并等待销毁。测试本身不跨检测强持有旧View；用于身份比较的旧owner只放在WeakReference中。

**正对照也要防空跑。** 首轮扩展测试曾因finish后立即检查而发生状态断言失败；首轮正对照也曾在尚未watch到销毁对象时意外通过。补上有界等待实际销毁后，修复版通过、代表性泄漏正对照失败。两次初始输出完整保留在同一归档，不把它们删掉再声称“一次全绿”。这个坑说明：泄漏门禁不仅要检查结果，还要确认对象真的走到了应被回收的生命周期边界。

这里的通过仅限已执行路径、版本和检测窗口；没有对五种错误逐一做独立回退，也没有证明所有对象都无泄漏。目前完成的是**本地instrumentation门禁验证**，尚未部署真实CI流水线。CI接入时不要只看adb退出码：本次成功与预期失败的adb进程退出码均为0，必须解析JUnit最终结果、每个用例状态以及崩溃/超时。

本轮归档位于 `LeakDemo/results/review-retest/20261028-164001/`。阴性日志显示无待分析的受监视对象，可能无需dump堆，因此不要为了凑“分析结果为0”去生成空数据库。

---

### 量化对比

> 说明：以下对象计数来自**历史 debug 构建（含 LeakCanary）**，每项均为进出 20 轮、尝试发送 GC 信号并等待 10 秒后的结果，重复 3 轮取中位数。旧脚本吞掉信号错误且无 GC 完成证据，所以不能称为 post-GC 活堆。Java Heap 趋势来自**不含 LeakCanary 的历史 release-like 构建**，两类数据不能直接混算。

| 指标 | Step 0 | Step 1 | Step 2 | Step 3 | Step 4 | Step 5 |
|------|--------|--------|--------|--------|--------|--------|
| `Activities`（dumpsys） | 41 | 41 | 41 | 41 | 22 | **1** |
| `Views`（dumpsys） | 556 | 556 | 556 | 436 | 208 | **16** |
| 人工归类的关键持有字段 | 4 类 | 3 类 | 3 类（状态源同时改变） | 2 类 | 1 类 | **不可统计：数据库导出为错误文本** |

历史三轮原始计数复核：Step 0 / 1 / 2 的 Views 均为 556、Activities 均为 41，三轮一致；Step 3 的 Views 为 **420 / 436 / 436**，中位数 **436**，Activities 为 **40 / 41 / 41**，中位数 **41**；Step 4 的 Views 为 208、Activities 为 22，三轮一致；Step 5 的 Views 为 16、Activities 为 1，三轮一致。表格列的是各自中位数，不代表每轮都相同。

表中 **4 / 3 / 3 / 2 / 1 是人工按关键字段分类的数量，不是分析次数、报告条数或泄漏对象数**，不能据此计算工具检出率。

下图按历史原始样本重新绘制，取的是 `dumpsys meminfo` **App Summary 的 Java Heap 私有内存归因**，不是明细区 `Dalvik Heap` 的 Heap Size / Heap Alloc，也不是 Java 活对象总大小。修复前、后各只有 **1 次运行**；循环间隔约 1 秒，另加每次命令执行耗时，并非严格 1 Hz。横轴使用原始样本的真实经过秒数；两次运行末值分别为修复前 **13.13 MiB**、修复后 **7.95 MiB**。它展示两次运行的趋势差异，不提供重复实验的置信区间，不支持“已确认 GC 后堆底抬升”的结论；也不等于 `Heap Alloc`、`Runtime used` 或 GC 后活对象大小。单位由 KiB 按 1024 KiB = 1 MiB 换算；LeakCanary trace 内原有 `kB` 保持原样。历史旧图保留为资料，不再用作当前论证图。

![历史样本复核：Summary Java Heap 私有内存归因趋势](/images/你的-Activity-关了-为什么还活着-Android-内存泄漏从发现-定位到线上治理/shot07_summary_java_heap_review.png)

---

## 四、总结

### 速查表：5 条内存泄漏治理原则

```
✅ 1. 泄漏 = 该回收的对象仍然被 GC Root 持有
      读 leak trace：最后一个 NO 到第一个 YES 之间是候选责任区间，
      结合 UNKNOWN、可疑字段标记和生命周期判断，不机械认定相邻边

✅ 2. 生命周期必须匹配：长寿命对象不持有短寿命对象
      静态变量 / 单例 / 自定义 Scope 里，不要存 Activity、View、
      以及捕获了它们的 lambda；不需 UI 主题的工作才用 applicationContext

✅ 3. Fragment 里的协程用 viewLifecycleOwner，并配合 repeatOnLifecycle
      lifecycleScope 是 Fragment 的，不是 View 的；
      StateFlow 会通过订阅槽持有收集协程，协程又拽住它捕获的 binding

✅ 4. 注册和注销必须成对
      Compose 用 DisposableEffect；Flow 不会自动免泄漏，
      收集方仍要选对 scope 并及时取消

✅ 5. 把检测接进流程，而不是靠人肉
      开发期 LeakCanary（debug）→ CI 用仪器化测试断言无泄漏 →
      线上用系统与平台能力兜底
```

### 一个容易被忽视的经验：先区分引用图变化与报告变化

同一个对象可能被多条路径持有，工具展示的路径不等于全部强引用图。但 **本文的 Step 0 → Step 2 同时改变监听器和状态源，不能证明“短链掩盖长链”**。从后一个版本的新 trace，不能反推前一个版本已存在完全相同的长链。

由此得到两条更可靠的经验：

- **不要把人工字段分类数当成缺陷数或工具报告数。** 固定构建、状态源、场景与检测窗口，每次尽量只改变一个因素，才有条件讨论因果。
- **单点修复要同时看代码、路径和实例证据。** 某类 trace 不再出现只能支持该路径的修复；计数没下降也不必然表示修改无效，因为对象可能仍被其他路径持有。最终还要验证应释放对象确实不再被保留。

### 线上怎么办：开发期之外的三道防线

本文仅在 debug 构建集成 LeakCanary，这不是技术上“只能用于 debug”的限制。但完整 heap dump 和分析涉及停顿、资源消耗与隐私，不应将开发期配置直接带入生产。线上应按成本和场景建立分层防线：

**1. 指标层：[Android vitals](https://developer.android.com/topic/performance/vitals)。** 在平台可提供相应数据时，关注低内存终止、崩溃和用户体验指标，结合版本、机型与场景定位回归。具体指标定义、统计分母和阈值以当前官方页面及控制台为准。

**2. 现场层：[ProfilingManager](https://developer.android.com/reference/android/os/ProfilingManager)。** 按目标 API、系统支持和官方文档评估可申请的 profiling 数据、采样限制与触发条件，缓解线上问题难复现的困难。不要默认它能在 OOM 之后补抓 heap dump，也不要把所有 profile 都当作堆快照。本文未实测该能力，不提供具体触发器或线上采集成功的结论；接入前还需评估隐私、授权、性能和回传成本。

**3. 自研层：参考成熟方案的设计。** 线上 dump 堆有几个老问题：文件大、上传成本高、分析耗时甚至可能再次 OOM。快手开源的 [KOOM](https://github.com/KwaiAppTeam/KOOM) 提供了通过 fork 子进程进行 dump 的思路，可作为架构参考。接入前仍需验证目标 Android 版本、ART 与厂商系统的兼容性，评估 fork、堆转储和分析过程的额外内存、主线程停顿与稳定性风险；不能把框架介绍中的性能预期直接当作自己应用的测量结果。

**关于新版本平台限制**：应用始终要在系统的内存与后台运行约束内工作，泄漏治理应该做在上线之前。本文未核实 Android 17 `memory-limiter` 的具体行为、适用版本与命令，不将未经验证的新版本说明写成既定事实；实际接入与压力测试请按目标版本的官方行为变更文档逐项验证。

### 方法论升华

前三篇是"让 App 做得更快"，这一篇是"让 App 活得更久"。两者的底层逻辑一致：**先让问题可见，再定位根因，最后用自动化防止回归。**

内存泄漏尤其如此：它不会立刻让你崩溃，所以最容易被忽视；等到线上 OOM 报警时，你面对的已经是一堆现场信息不全的崩溃。把"发现 → 定位 → 修复 → 防回归 → 线上监控"做成闭环，才是真正治好它。

### 下篇预告

这一篇我们盯的是"对象该不该被回收"（泄漏）。但内存问题还有另一面：**对象都该活，却占得太多、分配太勤**——没有泄漏的 App，照样会内存高企、被 LMK 盯上，甚至 OOM。

下一篇，我们就讲 **内存占用与 OOM 优化**：看懂 `dumpsys meminfo` 的各项指标、Bitmap 怎么省、内存抖动怎么消、大缓存与 `onTrimMemory` 怎么配合。

---

### 附：演示工程与测量环境

- **演示工程**：`LeakDemo`（本系列配套 demo），git 仓库，每个修复对应一个 tag：`step0-leaky`、`step1-fix-leak1`、`step2-fix-leak2`、`step3-fix-leak3`、`step4-fix-leak4`、`step5-fix-leak5`、`step6-regression-test`。五处泄漏在代码中以 `LEAK-1` ~ `LEAK-5` 注释标记，修复处保留 `FIXED LEAK-N` 说明。
- **设备**：小米 13 Pro（2210132C / nuwa），骁龙 8 Gen 2，Android 16 / API 36（`Build.VERSION.SDK_INT: 36`）。
- **工具版本**：LeakCanary **2.14**；AGP 8.5.2；Kotlin 2.0.21；Compose BOM 2024.10.01。
- **两类构建**（不混用）：**debug 构建（含 LeakCanary）** 用于泄漏报告与 `dumpsys` 对象计数；**release-like 构建（不含 LeakCanary，非 debuggable，`<profileable android:shell="true"/>`）** 用于 Java Heap 与堆曲线。
- **场景脚本**：`adb shell am start` + `input keyevent/tap`（UI Automator 定位），每轮各进出一次 `DetailActivity`、`DetailFragment`（`addToBackStack`）、`ComposeActivity`，共 20 轮；每步重复 3 轮取中位数。
- **历史 GC 尝试及局限**：旧脚本尝试 `adb shell kill -10 <pid>`，吞掉错误后等待 10 秒采样；未保留信号发送成功、目标进程处理信号或 GC 完成的证据。本文只称“尝试后等待 10 秒”，不把旧对象计数和内存样本称为已确认 GC 后的活堆。
- **`FakeSdk` 是模拟的**：用一个永不完成的 `CompletableDeferred` 模拟"可能永不回调"的第三方 SDK，仅用于复现第 ④ 类泄漏。
- **证据分界**：上文 step0～step5 对象计数、五类代表 trace、release-like 趋势原始样本，以及 `OK (2 tests)` / 故意恢复第 ⑤ 类后的失败输出，均属历史记录。本轮修订纠正口径、读取错误与混杂因素，不将重绘图当作新设备采样。Step 5 数据库导出是错误文本，无法从中得到分析次数或零报告结论。
- **本轮补测**：`LeakDemo/results/review-retest/20261028-164001/` 保存构建、APK指纹、状态断言日志、五项套件最终通过、独立remember阴性和网络回调泄漏正对照失败。数据库与测量错误分支11项Python单测通过；旧Step5错误文本被标记为invalid而非0。初始测试时序失败也保留。新结果不替换旧20×3计数，不代表已经接入实际CI。
- **未实测项**：平台新版本的内存限制、`ProfilingManager` 线上采集与触发条件均未实测，以目标版本官方文档与后续验证为准。
