---
title: "你在 XML 时代学的渲染优化，进了 Compose 大多不再是重点——Recomposition 才是新的战场"
date: 2026-10-22
description: "XML 时代的过度绘制、层级压平，到了 Compose 大多不再是重点——新战场是重组。本文用 Layout Inspector 定位问题，讲清触发与稳定性规则，四步修复搜索列表页，真机数据验证。"
tags: ['Android', 'Compose']
category: "技术"
source: "https://juejin.cn/post/7699368463357755443"
---
## 你在 XML 时代学的渲染优化，进了 Compose 大多不再是重点——Recomposition 才是新的战场

> 本文是「Android 应用性能优化」系列第二篇。上一篇我们靠消灭 Overdraw、用 ConstraintLayout 压平层级，治好了商品列表的卡顿。这一篇迁移到 Jetpack Compose，你会发现：那套打法大多不再是重点，新的战场叫 **Recomposition（重组）**。
>
> 读完本文你将掌握：用 Layout Inspector 和 Compiler Report 定位重组问题 → 理解重组的触发机制与稳定性（包含 Strong Skipping 之后的新规则）→ 用四步修复一个搜索列表页，并用真机数据验证每一步的收益。
>
> **环境说明**：本文基于 Kotlin 2.0.20+（Compose 编译器随 Kotlin 发布，Strong Skipping 默认开启）。文中所有数据来自配套 Demo（`compose-recomposition-demo/`，Kotlin 2.0.21 + Compose BOM 2024.10.01），测试机为**小米 6**（骁龙 835，Android 9，60Hz）——一台 2017 年的老机器，更容易把重组开销放大成肉眼可见的掉帧。重组计数用 Release 包加计数器测得，帧率一律在 Release 包上测量。

---

### 一、问题提出：Compose 写的列表，为什么还是卡？

产品又找过来了。

"搜索框输一个字，列表跟着抖一下，滑起来也不跟手，感觉比之前 XML 版本还卡。"

你的第一反应，大概率还是上一篇的思路：是不是 Overdraw？是不是层级太深？

**先排除 Overdraw。** 打开 Debug GPU Overdraw（设置 → 开发者选项 → 调试 GPU 过度绘制 → 显示过度绘制区域），看一眼色阶。

![Debug GPU Overdraw 下的搜索页（小米 6）](/images/你在-XML-时代学的渲染优化-进了-Compose-大多不再是重点-Recomposition-才是新的战场/01.png)

页面背景是蓝色（1 层，来自 Window 背景上再铺一层 `Surface`），文字和标签底色是绿色（2 层），只有标签上的文字是粉色（3 层），没有任何红色（4 层以上）区域。Overdraw 在 Compose 里依然存在（叠多层 `background`、`Surface` 照样会产生），但这里显然不是主因。

**再排除层级深度。** 官方文档的原话是："Compose handles nested layouts efficiently, making them a great way to design a complicated UI. This is an improvement from Android Views, where you need to avoid nested layouts for performance reasons."（[Compose 布局基础](https://link.juejin.cn?target=https%3A%2F%2Fdeveloper.android.com%2Fdevelop%2Fui%2Fcompose%2Flayouts%2Fbasics "https://developer.android.com/develop/ui/compose/layouts/basics")）。Compose 的布局系统不允许对子节点进行二次测量，层级再深，测量开销也是线性增长，不会像 RelativeLayout 嵌套那样成倍放大。

> 上一篇学的那一套（去背景、拍平层级），在这里基本帮不上忙。问题出在另一个地方。

新的性能杀手有一个新名字：**Recomposition（重组）**——CPU 在重复执行本不需要重新执行的 Composable 函数。要找到它，需要另一套工具。

---

#### 打开 Layout Inspector，让问题现形

Android Studio 菜单栏：

```
View → Tool Windows → Layout Inspector
```

用 **Debug 包**运行 App 后，Layout Inspector 会自动连接。在组件树里开启 **Show Recomposition Counts**（在 Component Tree 右上角的 View Options 里），操作前先点一下 `Reset` 重置计数。

> ⚠️ **前置条件**：重组计数需要 **API 29+** 才能显示（官方文档原文：*To view recomposition counts, make sure your app is using an API level of 29 or higher*）。本文的性能数据来自小米 6（Android 9 / API 28），它开不了重组计数——所以 **Layout Inspector 的截图取自另一台 API 29+ 的设备**（小米 13 Pro）。两台机器屏幕高度不同，截图上**可见的 Item 数量比小米 6 多几个**；文中所有具体数字，都以小米 6 的计数面板和文末实测表为准。

然后在搜索框里输入一个字符。

组件树里每个 Composable 后面会出现三列计数（新版 Layout Inspector 的列；官方文档目前仍写作两列 `recompositions` / `skips`）：

- **Recompositions**：这个 Composable 自己被重新执行了几次，越小越好
- **Child Recompositions**：它的子 Composable 被重新执行了几次
- **Skipped Recompositions**：被 Compose 智能跳过了几次，越大越好

本文主要看第一列和第三列：`SearchScreen` 自己重组了几次（用来找震源），`ProductItem` 被跳过了几次（用来判断智能重组有没有生效）。

你会看到类似这样的结构（示意，为简洁只列关键两列）：

```
SearchScreen              Recompositions 1   Skipped 0
  ├─ SearchInput          Recompositions 1   Skipped 0
  └─ LazyColumn
       ├─ ProductItem     Recompositions 1   Skipped 0
       ├─ ProductItem     Recompositions 1   Skipped 0
       ... （屏幕上可见的 6 个 Item，全部：Recompositions 1 / Skipped 0）
```

![Step 0 输入一个字符后的 Layout Inspector](/images/你在-XML-时代学的渲染优化-进了-Compose-大多不再是重点-Recomposition-才是新的战场/02.png)

> 上图是真实的 Layout Inspector 输出：`LazyColumn` 下面的 `ProductItem` 逐行都有重组计数，`Skipped Recompositions` 列为空（即 0）——可见的 Item 一个都没被跳过。这就是 Step 0 的病根。
>
> 图中多出来的 `ProductRow` 是 Demo 为五个版本复用抽出的公共布局函数（见文末附录），正文代码里 `ProductItem` 直接包 `Row`，没有这一层。

Layout Inspector 只能在 Debug 包上用，也不方便自动化。所以配套 Demo 在每个被测 Composable 开头加了一行计数：

```
SideEffect { RecompositionCounter.inc("ProductItem") }
```

`SideEffect` 本身不可跳过：函数体执行了它就一定执行，函数被跳过它就不执行，所以它统计的正是该函数的执行次数。下图是 Release 包里，在 "ph" 后面再输入一个 "o" 时的计数面板（左下角）：

![输入 "o" 时 Step 0 / 1 / 2 的执行次数对比](/images/你在-XML-时代学的渲染优化-进了-Compose-大多不再是重点-Recomposition-才是新的战场/03.png)

先只看最左边的 Step 0（问题版本），两个信号同时出现：

1. **`SearchScreen` 本身在重组**——它是这次重组的"震源"。
2. **6 个 `ProductItem` 全部被重新执行**——"ph" → "pho" 的结果集其实一模一样，商品内容一个都没变。这是 Compose 的"智能重组"没有生效的直接证据。

注意，LazyColumn 只会组合屏幕上可见的 Item，所以这里的数量是可见 Item 数，不是列表总长度（500）。

接下来搞清楚两个问题：为什么 `SearchScreen` 会重组？为什么 `ProductItem` 跳不过去？

---

### 二、相关知识点讲解

#### 2.1 Compose 渲染三阶段：和 XML 的关键区别

Compose 渲染一帧同样经过三个阶段：

```
① Composition（组合）：执行 @Composable 函数，决定"显示什么"
② Layout（布局）：测量并放置每个节点，决定"放在哪"
③ Drawing（绘制）：把节点画到 Canvas，提交给 GPU
```

和 XML 对比：

|  | XML 时代 | Compose |
| --- | --- | --- |
| 测量次数 | RelativeLayout 双重测量；LinearLayout 设置 weight 时二次测量 | 每个子节点只允许测量一次（intrinsic 是测量前的尺寸查询，不算二次测量） |
| 层级影响 | 越深越慢，需要拍平 | 深层级不再是主要问题 |
| 优化主战场 | 减少 Measure/Draw 的无效工作 | **减少 Composition 阶段的无效执行** |

最后一行是关键：状态没变化的部分，Compose 可以**跳过 Composition**，直接复用上一次的结果。所以 Compose 性能优化的核心目标是：**让尽可能多的 Composable 在状态变化时被跳过，而不是被重新执行。**

---

#### 2.2 谁触发了重组：状态读取的位置决定重组范围

Compose 用快照系统（Snapshot System）追踪状态的读写。每个 `@Composable` 函数执行时，系统会记录它读取了哪些状态。状态一旦变化：

```
状态 query 变化
   ↓
找到所有"读取过 query"的重组作用域（Recompose Scope）
   ↓
下一帧重新执行它们 = Recomposition
```

**核心规律：在哪里读取状态，哪里就是重组的震源。**

这里有一个容易踩的细节：**重组作用域是"最近的非 inline 的 Composable 函数"**。`Column`、`Row`、`Box` 都是 inline 函数，它们的内容 lambda 不构成独立的作用域。所以在 `Column { }` 里读取状态，重组的是包着这个 `Column` 的外层函数。想缩小重组范围，必须把读取状态的代码**抽成一个独立的 Composable 函数**，只套一层 `Column` 没有用——这也是后面 Step 1 的写法。

如果在 `SearchScreen` 的顶层读取了 `query`，那么 `SearchScreen` 整个函数体都会重新执行。它下面的子 Composable 能不能逃过去，取决于下一节的"稳定性"。

---

#### 2.3 稳定性：子 Composable 能不能被跳过

父级重组时，Compose 会逐个检查子 Composable 的参数：**参数没变，就跳过**。判断"变没变"的方式，取决于参数类型是稳定的（Stable）还是不稳定的（Unstable）：

```
// ✅ 稳定：基础类型、String、函数类型、枚举，
//    以及所有属性都是 val 且类型稳定的类（不限于 data class）
data class A(val id: Int, val name: String)

// ❌ 不稳定：含 var 属性
data class B(val id: Int, var name: String)

// ❌ 不稳定：含 List 接口（编译器无法确认它不是 MutableList）
data class C(val id: Int, val tags: List<String>)
```

比较规则（**Kotlin 2.0.20+ 默认开启 Strong Skipping**）：

|  | 稳定类型 | 不稳定类型 |
| --- | --- | --- |
| 比较方式 | `equals()` 内容相等 | `===` 实例相等 |
| Strong Skipping 之前 | 参数没变就跳过 | **只要有一个参数不稳定，整个函数都不可跳过** |
| Strong Skipping 之后 | 参数没变就跳过 | **实例没变才跳过，实例一变就跳不过** |

这张表是整篇文章的关键。Strong Skipping 让含不稳定参数的 Composable 也有了被跳过的资格，但这不等于"稳定性不重要了"：

- 稳定类型：即使每次重组都是**新创建的实例**，只要内容相等，照样能跳过。
- 不稳定类型：只要实例**换了一个新的**（哪怕内容一模一样），就跳不过。

所以 Strong Skipping 之后，新的问题模式是**实例抖动（instance churn）**：不稳定类型的对象，在每次重组时被重新创建。

**用 Compiler Report 看稳定性**

Compose 编译器可以把稳定性推断结果输出成报告。在模块的 `build.gradle.kts` 里（注意：`composeCompiler` 块在文件顶层，不在 `android {}` 里面；需要先应用 Compose 编译器插件）：

```
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.compose.compiler)   // org.jetbrains.kotlin.plugin.compose
}

composeCompiler {
    reportsDestination = layout.buildDirectory.dir("compose_compiler")
    metricsDestination = layout.buildDirectory.dir("compose_compiler")
}
```

执行 `./gradlew assembleRelease`，`build/compose_compiler/` 下会生成 4 个文件：

```
<模块>_release-composables.txt   每个 Composable 是否 skippable，每个参数是否稳定
<模块>_release-classes.txt       每个类被推断为 stable 还是 unstable，以及原因
<模块>_release-composables.csv   同上，表格形式，方便筛选
<模块>_release-module.json       模块级统计，包括编译器开关
```

先看 `module.json`，确认 Strong Skipping 确实开着（Demo 实际输出）：

```
"featureFlags": {
    "StrongSkipping": true,
    "IntrinsicRemember": true,
    "OptimizeNonSkippingGroups": false
}
```

再看问题版本的两份报告（Demo 实际输出，节选）：

```
// composables.txt
restartable skippable scheme("[androidx.compose.ui.UiComposable]") fun ProductItem(
  unstable product: ProductUi      // ← 看参数前面的 unstable，而不是只看 skippable
)

// classes.txt
unstable class ProductUi {
  stable val id: Int
  stable val name: String
  stable val price: String
  stable val imageUrl: String
  unstable val tags: List<String>  // ← 罪魁祸首
  <runtime stability> = Unstable
}
```

在 Strong Skipping 下，`skippable` 几乎处处都有：Demo 的 `composables.csv` 里 23 个具名 Composable 全部是 skippable，包括这个参数不稳定的 `ProductItem`。**真正的预警信号是参数前的 `unstable`**。（如果你的项目 Kotlin 版本低于 2.0.20，或者手动关闭了 Strong Skipping，那么缺少 `skippable` 本身就是问题。）

---

#### 2.4 两个关键工具：remember 与 derivedStateOf

**`remember`：跨重组缓存计算结果**

```
// ❌ 每次重组都重新排序
val sorted = contacts.sortedWith(comparator)

// ✅ 只有 contacts 或 comparator 变化时才重新计算
val sorted = remember(contacts, comparator) { contacts.sortedWith(comparator) }
```

**`derivedStateOf`：状态降频**

```
val listState = rememberLazyListState()

// ❌ firstVisibleItemIndex 每滚过一个 Item 就变一次，
//    读取它的 Composable 每次都要重组
val showFab = listState.firstVisibleItemIndex > 0

// ✅ 你关心的只是"是否大于 0"这个布尔值，
//    只有它真正翻转时才触发重组
val showFab by remember { derivedStateOf { listState.firstVisibleItemIndex > 0 } }
```

`derivedStateOf` 的本质：在频繁变化的输入状态和重组之间加一层过滤，**只有输出结果变化时才通知 UI**。

反过来，如果输出和输入变化得一样频繁，它就只剩额外开销。比如 `derivedStateOf { "$firstName $lastName" }`，两个名字一变结果就变，过滤不掉任何一次重组，直接写 `remember(firstName, lastName) { ... }` 或者干脆直接计算即可。

---

### 三、具体实例应用展示

**案例：商品搜索列表页**——顶部搜索框（实时过滤）+ LazyColumn 商品列表（500 个商品）+ 右下角随滚动偏移的 FAB。

#### Step 0：诊断现场，先看工具，再动代码

先把案例的完整基础代码列出来（后面每一步只展示改动的部分）。依赖：Compose Material3、`material-icons-core`、`lifecycle-runtime-compose`、Coil（`coil-compose`）。

```
// ===== 数据层 =====
data class Product(
    val id: Int,
    val name: String,
    val priceCent: Long,
    val imageUrl: String,
    val tags: List<String>
)

interface ProductRepository {
    fun productsFlow(): Flow<List<Product>>
}

// ===== UI 层模型：价格格式化好再给 UI 用 =====
data class ProductUi(
    val id: Int,
    val name: String,
    val price: String,
    val imageUrl: String,
    val tags: List<String>            // ← List 接口：编译器判定 Unstable
)

fun Product.toUi() = ProductUi(
    id = id,
    name = name,
    price = "¥%.2f".format(priceCent / 100.0),
    imageUrl = imageUrl,
    tags = tags
)

class SearchViewModel(repository: ProductRepository) : ViewModel() {
    val products: StateFlow<List<Product>> = repository.productsFlow()
        .stateIn(viewModelScope, SharingStarted.Lazily, emptyList())
}
```

```
// ===== 页面（问题版本）=====
@Composable
fun SearchScreen(viewModel: SearchViewModel) {
    val products by viewModel.products.collectAsStateWithLifecycle()
    var query by remember { mutableStateOf("") }               // ❌ ① query 在顶层读取
    val listState = rememberLazyListState()

    // ❌ ② 每次重组都重新 filter + map：产生全新的 ProductUi 实例
    val uiItems = products
        .filter { it.name.contains(query, ignoreCase = true) }
        .map { it.toUi() }

    // ❌ ③ 每滚过一个 Item，SearchScreen 就要重组一次
    val showFab = listState.firstVisibleItemIndex > 0

    Box(Modifier.fillMaxSize()) {
        Column {
            SearchInput(query = query, onQueryChange = { query = it })
            LazyColumn(state = listState) {
                items(uiItems) { ProductItem(it) }              // ❌ ④ 没有 key
            }
        }
        if (showFab) {
            ScrollFab(listState, Modifier.align(Alignment.BottomEnd).padding(16.dp))
        }
    }
}

// 命名为 SearchInput，避免和 Material3 自带的 SearchBar 重名
@Composable
fun SearchInput(query: String, onQueryChange: (String) -> Unit) {
    OutlinedTextField(
        value = query,
        onValueChange = onQueryChange,
        singleLine = true,
        placeholder = { Text("搜索商品") },
        modifier = Modifier.fillMaxWidth().padding(12.dp)
    )
}

@Composable
fun ProductItem(product: ProductUi) {
    Row(Modifier.fillMaxWidth().padding(12.dp)) {
        AsyncImage(
            model = product.imageUrl,
            contentDescription = null,
            modifier = Modifier.size(80.dp)
        )
        Column(Modifier.padding(start = 12.dp)) {
            Text(product.name, style = MaterialTheme.typography.bodyMedium, maxLines = 2)
            Text(
                product.price,
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.error
            )
            Row { product.tags.forEach { TagChip(it) } }
        }
    }
}

@Composable
fun TagChip(text: String) {
    Text(
        text = text,
        style = MaterialTheme.typography.labelSmall,
        modifier = Modifier
            .padding(end = 6.dp)
            .background(MaterialTheme.colorScheme.secondaryContainer, RoundedCornerShape(10.dp))
            .padding(horizontal = 6.dp, vertical = 2.dp)
    )
}

// ❌ ⑤ 在函数体里读取滚动偏移：滚动时每一帧都触发重组
@Composable
fun ScrollFab(listState: LazyListState, modifier: Modifier = Modifier) {
    val offsetPx = listState.firstVisibleItemScrollOffset
    val offsetDp = with(LocalDensity.current) { (offsetPx / 2).toDp() }
    FloatingActionButton(onClick = { }, modifier = modifier.offset(y = offsetDp)) {
        Icon(Icons.Default.KeyboardArrowUp, contentDescription = "回到顶部")   // core 图标集自带
    }
}
```

> 两处细节：收集 Flow 用 `collectAsStateWithLifecycle()`（页面不可见时自动停止收集），这是 Android 上的推荐写法；图标用 `KeyboardArrowUp` 而不是 `ArrowUpward`，后者不在 core 图标集里，需要额外引入体积很大的 `material-icons-extended`。

**先看运行时现象**（见前文对比图最左边）：`SearchScreen` 在重组，6 个 `ProductItem` 全部被重新执行。

**再用 Compiler Report 找原因**（2.3 节的实际输出）：`ProductItem` 的参数是 `unstable product: ProductUi`，而 `ProductUi` 不稳定的原因是 `unstable val tags: List<String>`。

两条证据拼起来，因果链就清楚了：

```
按键 → query 变化 → SearchScreen 重组（震源在顶层）
     → 函数体里重新 filter + map → 产生全新的 ProductUi 实例
     → ProductUi 不稳定，用 === 比较 → 新实例必然"不相等"
     → 所有可见的 ProductItem 都跳不过去
```

问题代码里一共埋了五个问题（代码注释里的 ①~⑤），接下来逐个解决。

---

#### Step 1：缩小重组范围，把 query 状态下沉

**根因**：`query` 在 `SearchScreen` 顶层读取，整个页面函数是震源。

**修复**：把 `query` 和列表放进一个独立的 Composable（注意是独立函数，见 2.2 节），`SearchScreen` 不再读取 `query`。

```
@Composable
fun SearchScreen(viewModel: SearchViewModel) {
    val products by viewModel.products.collectAsStateWithLifecycle()
    val listState = rememberLazyListState()
    val showFab = listState.firstVisibleItemIndex > 0           // Step 4 再处理

    Box(Modifier.fillMaxSize()) {
        SearchContent(products = products, listState = listState)
        if (showFab) {
            ScrollFab(listState, Modifier.align(Alignment.BottomEnd).padding(16.dp))
        }
    }
}

@Composable
private fun SearchContent(products: List<Product>, listState: LazyListState) {
    var query by remember { mutableStateOf("") }               // ✅ query 下沉到这里
    val uiItems = products
        .filter { it.name.contains(query, ignoreCase = true) }
        .map { it.toUi() }                                     // 仍在 Composition 里，Step 2 处理

    Column {
        SearchInput(query = query, onQueryChange = { query = it })
        LazyColumn(state = listState) {
            items(uiItems) { ProductItem(it) }
        }
    }
}
```

**验证（按键）**：前文对比图中间那张，输入字符时 `SearchScreen` 的执行次数是 0，震源变成了 `SearchContent`。

但请注意：**`ProductItem` 依然是 6 次，一个都没跳过。** 缩小震源范围，并不会自动让子节点被跳过。真正拦住 `ProductItem` 的，是下一步。

**意外收获（滚动）**：这一步在滚动场景下的收益，比在输入场景下大得多。下图是两个版本各上滑 10 次后的计数：

![滚动 10 次后 Step 0 与 Step 1 的执行次数对比](/images/你在-XML-时代学的渲染优化-进了-Compose-大多不再是重点-Recomposition-才是新的战场/04.png)

Step 0 里，`SearchScreen` 每滚过一个 Item 就重组一次（问题 ③），每次重组都重新 `map` 出一批新的 `ProductUi`，于是可见的 Item 全部跟着重组：`ProductItem` 执行了 431 次。Step 1 里，`SearchScreen` 照样重组，但 `filter + map` 已经搬进了 `SearchContent`，而 `SearchContent` 的两个参数（`products` 和 `listState`）都没变，整个函数被跳过。`ProductItem` 只剩新滑入屏幕时的 54 次。

5 轮实测平均下来（上滑、下滑各 10 次），`ProductItem` 从 785 次降到 106 次，**滚动掉帧率从 34.1% 降到 20.4%**。这也说明了状态下沉的价值不止于"把无关内容挪出去"：**震源函数体里写的每一行计算，都会跟着震源一起重复执行。**

---

#### Step 2：修复实例抖动，让 ProductItem 真正被跳过

**根因**：`ProductUi` 不稳定，而每次重组都 `map` 出全新实例。两者叠加，`===` 永远不相等。

有两条路，建议两条都走：

**路线 A：让实例不抖。** `map` 不该放在 Composition 里，数据变了才映射一次，放进 ViewModel：

```
class SearchViewModel(repository: ProductRepository) : ViewModel() {
    // ✅ 数据源变化时才映射一次，之后实例保持不变
    val products: StateFlow<List<ProductUi>> = repository.productsFlow()
        .map { list -> list.map { it.toUi() } }
        // 列表较大时可再加 .flowOn(Dispatchers.Default)，把映射挪出主线程
        .stateIn(viewModelScope, SharingStarted.Lazily, emptyList())
}

@Composable
private fun SearchContent(products: List<ProductUi>, listState: LazyListState) {
    var query by remember { mutableStateOf("") }
    // ✅ filter 只是挑选已有实例，不创建新的 ProductUi
    val uiItems = remember(products, query) {
        products.filter { it.name.contains(query, ignoreCase = true) }
    }
    // ... 其余不变
}
```

**路线 B：让类型稳定。** 把 `List` 换成 kotlinx 的不可变集合，这样比较方式从 `===` 变成 `equals()`，即使实例变了、内容相等也能跳过。比如数据源刷新、重新 `map` 出一批内容相同的新实例时，路线 A 拦不住，路线 B 能拦住，等于给路线 A 加了一道保险：

```
// build.gradle.kts（Demo 使用 0.3.8，请以 Maven Central 上的最新版为准）
implementation("org.jetbrains.kotlinx:kotlinx-collections-immutable:0.3.8")
```

```
data class ProductUi(
    val id: Int,
    val name: String,
    val price: String,
    val imageUrl: String,
    val tags: ImmutableList<String>      // ✅ 稳定
)

fun Product.toUi() = ProductUi(
    id = id, name = name,
    price = "¥%.2f".format(priceCent / 100.0),
    imageUrl = imageUrl,
    tags = tags.toImmutableList()
)
```

**改不了类型怎么办？** 分两种情况：

- **自己的类**：可以加 `@Immutable` 或 `@Stable` 注解，向编译器"担保"它不会变。
- **第三方类型**（改不了源码，自然也加不了注解），或者想让整个项目把 `List` 都当成稳定类型：用**稳定性配置文件**。

```
composeCompiler {
    // Kotlin 2.0.x 的写法；更新的版本改为复数形式 stabilityConfigurationFiles.add(...)
    stabilityConfigurationFile = rootProject.layout.projectDirectory.file("stability_config.conf")
}
```

```
// stability_config.conf：每行一个类名，支持通配符
kotlin.collections.List
com.thirdparty.model.*
```

在 Demo 里实测：加上 `kotlin.collections.List` 这一行后，Step 0 的报告就从 `unstable class ProductUi` 变成了 `stable class ProductUi`，`tags` 那一行变成 `stable val tags: List<String>`。

注解和配置文件本质上都是在**覆盖编译器的判断**：一旦担保不成立（比如真的传进来一个之后会被修改的 `MutableList`），UI 就会出现"该刷新却没刷新"的 Bug，而且很难排查。所以优先用不可变集合，注解和配置文件作为退路。

**Compiler Report 验证**（Demo 实际输出）：

```
// composables.txt
restartable skippable scheme("[androidx.compose.ui.UiComposable]") fun ProductItem(
  stable product: ProductUi
)

// classes.txt
stable class ProductUi {
  ...
  stable val tags: ImmutableList<String>
  <runtime stability> =
}
```

`<runtime stability>` 后面是空的，这是实际输出，不是漏写：稳定性在编译期就已经确定，不需要运行时再判断。不稳定的类这里才会写出 `Unstable`。

**运行时验证**：回到前文的对比图最右边。输入 "o" 之后结果集没变（"ph" 和 "pho" 匹配到的都是 Phone 和 Headphone），`ProductItem` 的执行次数是 **0**，6 个 Item 全部被跳过。

> ⚠️ 验证时要挑一个**确实不改变结果集**的输入。像"输入空格"或"拼音输入法的中间态"这类例子并不靠谱：`query` 变成 `"手机 "` 之后，名字里没有这个尾随空格的商品会被过滤掉；拼音输入法的组合文本（比如 `"shou"`）也会通过 `onValueChange` 传进 `query`，结果集通常会变成空。

不过，当输入真的改变了结果集时，仍然有一部分 Item 会重组：没有 key 时，Compose 只能按位置匹配 Item，列表一变，位置上换了不同的商品，参数自然不同。这就是下一步要解决的。

---

#### Step 3：LazyColumn 加 key，让 Item 按身份而非位置匹配

**根因**：LazyColumn 默认用位置（index）作为 Item 的标识。过滤或重排之后，原来在第 3 位的商品移动到了第 2 位，Compose 看到的是"第 2 位的参数变了"，只能重组。

```
LazyColumn(state = listState) {
    items(
        items = uiItems,
        key = { it.id }                 // ✅ 用业务 id 作为身份标识
    ) { ProductItem(it) }
}
```

有了 key，Compose 知道"这个 Item 只是换了位置"，内容没变就直接复用并跳过，只有新进入屏幕的 Item 需要组合。

**验证**：从 "p" 输入到 "ph"，结果集会变（Laptop、Speaker 被过滤掉）：

![从 "p" 输入到 "ph"：无 key 与有 key 的执行次数对比](/images/你在-XML-时代学的渲染优化-进了-Compose-大多不再是重点-Recomposition-才是新的战场/05.png)

逐个位置推演一下就能对上实测数字：

| 位置 | "p" 时 | "ph" 时 | 无 key（按位置比） | 有 key（按 id 比） |
| --- | --- | --- | --- | --- |
| 1 | Phone X1 | Phone X1 | 相同，跳过 | 已在屏幕上，跳过 |
| 2 | Laptop X1 | Headphone X1 | **不同，重组** | 已在屏幕上，跳过 |
| 3 | Headphone X1 | Phone X2 | **不同，重组** | 已在屏幕上，跳过 |
| 4 | Speaker X1 | Headphone X2 | **不同，重组** | **新进入，组合** |
| 5 | Phone X2 | Phone X3 | **不同，重组** | **新进入，组合** |
| 6 | Laptop X2 | Headphone X3 | **不同，重组** | **新进入，组合** |
| 合计 |  |  | **5 次** | **3 次** |

**踩坑记录**：

- `key = { index }` 等于没写。列表变化后 index 也变了，和默认行为一样。key 必须是和商品绑定的稳定业务 id。
- key 必须唯一，重复会直接崩溃（`IllegalArgumentException`）；而且类型要能存进 Bundle（Int、Long、String 都可以），因为滚动位置的保存会用到它。

---

#### Step 4：延迟状态读取，让滚动不再触发 Composition

前三步解决的是"输入时"的重组。还剩下"滚动时"的两个问题：问题 ③（`showFab` 让 `SearchScreen` 随 Item 切换而重组）和问题 ⑤（`ScrollFab` 每帧都在重组）。

**4.1 用 `derivedStateOf` 给显隐降频**（问题 ③）：

```
@Composable
fun SearchScreen(viewModel: SearchViewModel) {
    val products by viewModel.products.collectAsStateWithLifecycle()
    val listState = rememberLazyListState()

    // ✅ 只有 true/false 翻转时才触发 SearchScreen 重组
    val showFab by remember { derivedStateOf { listState.firstVisibleItemIndex > 0 } }

    Box(Modifier.fillMaxSize()) {
        SearchContent(products = products, listState = listState)
        if (showFab) {
            ScrollFab(
                scrollOffset = { listState.firstVisibleItemScrollOffset },   // 注意：传 lambda
                modifier = Modifier.align(Alignment.BottomEnd).padding(16.dp)
            )
        }
    }
}
```

**4.2 把偏移量的读取推迟到 Layout 阶段**（问题 ⑤）：

```
// ✅ 接收 () -> Int，而不是 Int
@Composable
fun ScrollFab(scrollOffset: () -> Int, modifier: Modifier = Modifier) {
    FloatingActionButton(
        onClick = { },
        modifier = modifier.offset { IntOffset(0, scrollOffset() / 2) }   // lambda 在 Layout 阶段执行
    ) {
        Icon(Icons.Default.KeyboardArrowUp, contentDescription = "回到顶部")
    }
}
```

为什么这样就不重组了？因为状态是在 `Modifier.offset { }` 的 lambda 里读取的，这个 lambda 在 **Layout 阶段**执行，所以滚动偏移变化时，Compose 只需要重新布局，**不需要重新执行任何 Composable 函数**。对比之前：在函数体里直接读取 `firstVisibleItemScrollOffset`，是在 **Composition 阶段**读取，每一帧都要重组。

同样的思路也适用于 Draw 阶段：在 `Modifier.drawBehind { }`、`Modifier.drawWithContent { }`、`Modifier.graphicsLayer { }` 的 lambda 里读取状态，状态变化时只会重绘，连布局都不需要重做。

**验证**：两个版本各上滑 10 次后的计数：

![滚动 10 次后 Step 3 与 Step 4 的执行次数对比](/images/你在-XML-时代学的渲染优化-进了-Compose-大多不再是重点-Recomposition-才是新的战场/06.png)

`SearchScreen` 从 53 次降到 1 次（FAB 出现那一次），`ScrollFab` 从 510 次降到 1 次（首次组合那一次）。滚动掉帧率从 17.9% 降到 **11.1%**。

> ⚠️ 这个例子只用来演示"读取时机"，不是推荐的交互效果。`firstVisibleItemScrollOffset` 每滚过一个 Item 就会归零，FAB 会周期性地"跳回原位"，视觉上是锯齿状的跳动。官方文档的同类示例用的是 `ScrollState.value`（单调递增的滚动距离）。真实项目里如果想让 FAB 随滚动变化，更常见的做法是用 `graphicsLayer { alpha = ... }` 渐隐。

---

#### 量化对比：真机实测

**测量方法**：小米 6（Android 9，60Hz，帧预算 16.7ms），Release 包（R8 开启），测量前用 `adb shell cmd package compile -m speed -f` 全量 AOT 编译，排除 JIT 预热的干扰。帧数据来自 `adb shell dumpsys gfxinfo`，每个 Step 先跑 1 轮预热（丢弃），再取 5 轮平均。按键和滑动都由 adb 注入，脚本和原始数据都在 `compose-recomposition-demo/` 目录里，可以完整复现。

**重组次数**

| 场景 | 指标 | Step 0 | Step 1 | Step 2 | Step 3 | Step 4 |
| --- | --- | --- | --- | --- | --- | --- |
| 单次按键 | SearchScreen | 1 | **0** | 0 | 0 | 0 |
| 按键且结果集不变（"ph"→"pho"） | ProductItem | 6 | 6 | **0** | 0 | 0 |
| 按键且结果集变化（""→"p"） | ProductItem | 6 | 6 | 3 | **2** | 2 |
| 按键且结果集变化（"p"→"ph"） | ProductItem | 6 | 6 | 5 | **3** | 3 |
| 滚动 20 次（上下各 10） | SearchScreen | 98 | 105 | 106 | 104 | **2** |
| 滚动 20 次 | ScrollFab | 799 | 982 | 987 | 981 | **1** |
| 滚动 20 次 | ProductItem | 785 | **106** | 107 | 105 | 107 |

> Step 0 的 SearchScreen、ScrollFab 次数反而比 Step 1 少，是因为 Step 0 太卡，同样的滑动手势惯性更短、滑过的 Item 更少、渲染的帧也更少。

**帧数据**

| 场景 | 指标 | Step 0 | Step 1 | Step 2 | Step 3 | Step 4 |
| --- | --- | --- | --- | --- | --- | --- |
| 滚动 | 掉帧率 | 34.1% | 20.4% | 20.0% | 17.9% | **11.1%** |
| 滚动 | P90 帧耗时 | 40.4ms | 19.4ms | 18.6ms | 18.2ms | **16.6ms** |
| 滚动 | P99 帧耗时 | 61.0ms | 24.8ms | 25.6ms | 24.4ms | **23.0ms** |
| 输入（40 次按键） | ProductItem 执行总数 | 204 | 209 | 64 | 40 | 40 |
| 输入 | 掉帧率 | 53.6% | 51.2% | 56.5% | 53.8% | 55.0% |
| 输入 | P90 帧耗时 | 57.0ms | 56.0ms | 43.6ms | 41.2ms | **40.0ms** |
| 输入 | P99 帧耗时 | 77.0ms | 79.4ms | 52.8ms | 53.6ms | 54.4ms |

![滚动场景掉帧率](/images/你在-XML-时代学的渲染优化-进了-Compose-大多不再是重点-Recomposition-才是新的战场/07.png)

![滚动场景 P90 帧耗时](/images/你在-XML-时代学的渲染优化-进了-Compose-大多不再是重点-Recomposition-才是新的战场/08.png)

![输入场景 P90 帧耗时](/images/你在-XML-时代学的渲染优化-进了-Compose-大多不再是重点-Recomposition-才是新的战场/09.png)

从数据里能读出三件事：

1. **滚动场景的两次大跳跃，分别来自 Step 1 和 Step 4。** Step 1 掐掉了"每滚过一个 Item 就重新 map 一遍、可见 Item 全部重组"的连锁反应；Step 4 掐掉了"每帧都重组 FAB"。Step 2、3 针对的是输入场景，滚动数据在它们之间的差异属于正常波动（同一 Step 各轮之间的掉帧率最多能相差 8 个百分点左右）。
2. **输入场景的长尾明显变短**：Step 2 之后 P90 从 57ms 降到 40ms 左右，P99 从约 77ms 降到约 53ms。
3. **但输入场景的掉帧率几乎没变，一直在 50%~56%。** 也就是说，在小米 6 上，即使所有 `ProductItem` 都被跳过，每次按键产生的帧仍然超出 16.7ms 的预算。剩下的开销不在本文讨论的重组范围内，需要抓 System Trace（Perfetto）继续拆分，才能确定落在哪里。**减少无效重组能削掉长尾，但不保证消灭掉帧**——这也是为什么每一步优化都要用真实数据验证，而不是只看重组计数。

---

### 四、总结

#### XML 时代 vs Compose 时代：优化手段全对照

| 对比维度 | XML 时代（第一篇） | Compose 时代（本篇） |
| --- | --- | --- |
| 性能敌人 | Overdraw + 层级过深 | 不必要的 Recomposition |
| 诊断工具 | Debug GPU Overdraw（色阶图） | Layout Inspector 重组/跳过计数 |
| 静态分析 | Layout Inspector 层级树 | Compose Compiler Report |
| 根因 | GPU 画了不该画的像素 | CPU 执行了不该执行的函数 |
| 解决方向 | 拍平层级 / 去掉重复背景 | 缩小重组范围 / 保证可跳过 |
| 核心手段 | ConstraintLayout | 状态下沉 / 稳定类型 / `derivedStateOf` / 延迟读取 |
| 效果验证 | Profile GPU Rendering | `dumpsys gfxinfo` / Macrobenchmark（Release 包） |

#### 速查表：5 条 Compose 渲染优化原则

```
✅ 1. 在哪里读状态，哪里就是重组震源
      把状态读取下沉到真正需要它的最小范围（抽成独立函数，inline 的 Column/Row/Box 不算）
      震源函数体里的计算，会跟着震源一起重复执行

✅ 2. 用 derivedStateOf 给频繁变化的状态降频
      你关心的是"结果"（如 index > 0），不是"过程"（index 本身）
      输出和输入变化一样频繁时，不要用它

✅ 3. 不稳定类型比较实例，实例一抖就跳不过
      · 别在 Composition 里为不稳定类型反复创建新对象（map 放进 ViewModel 或 remember）
      · 能让类型稳定就稳定：List → ImmutableList
      · 改不了的第三方类型用稳定性配置文件，自己的类可用 @Immutable / @Stable
      · 用 Compiler Report 里的 unstable 参数标记做检查，不要只看 skippable

✅ 4. LazyColumn 必须提供 key
      key = { item.id }，用业务 id，不要用 index

✅ 5. 高频状态的读取推迟到 Layout / Draw 阶段
      Modifier.offset { } / drawBehind { } / graphicsLayer { } 的 lambda 形式
      → 状态变化只触发布局或绘制，不触发重组
```

#### 方法论升华

XML 时代优化的是"画布"：让 GPU 少画几层不该画的像素。Compose 时代优化的是"决策"：让运行时少执行几个不该执行的函数。

两者思想一致，都是**减少无效工作**，只是执行者从 GPU 换成了 CPU，工具从色阶图换成了重组计数。理解了这一点，再遇到 Compose 的性能问题，就不要先问"这里有没有 Overdraw"，而要问："这个 Composable 是不是在本该被跳过的时候被迫执行了？它被跳过的条件是什么？"

最后，用帧数据收尾，而不是用重组计数收尾。本文的输入场景就是一个反例：重组次数降了 80%，掉帧率却纹丝不动。计数告诉你"有没有做无用功"，帧数据才告诉你"用户能不能感觉到"。

#### 下篇预告

渲染优化解决的是内容出现之后的流畅度。但在内容出现之前，用户还要经历一段等待——**冷启动**。

下一篇，我们来拆 Android 冷启动的全链路：从点击图标到第一帧出现，系统和 App 各自做了什么，每个环节怎么量化，优化的刀该怎么下。

---

### 附录：验证工程

配套工程已开源：[compose-recomposition-demo](https://link.juejin.cn?target=https%3A%2F%2Fgithub.com%2Fshuhui-sh%2Fcompose-recomposition-demo "https://github.com/shuhui-sh/compose-recomposition-demo")，`step0` ~ `step4` 五个包分别对应正文的五个版本。和正文代码相比，只有两处差别：每个被测 Composable 开头多了一行 `SideEffect` 计数；`ProductItem` 的布局抽成了公共函数 `ProductRow`，方便五个版本复用。

| 文件 | 作用 |
| --- | --- |
| `RecompositionCounter.kt` | 执行次数计数器，可以通过广播 `com.demo.RESET` / `com.demo.DUMP` 清零或输出到 logcat |
| `measure_typing.sh` | 逐键计数（"p" → "h" → "o"） |
| `measure_frames.sh` | 滚动 / 输入场景的计数和 `gfxinfo` 帧统计（含 AOT 编译和预热轮） |
| `analyze.py` | 求 5 轮平均、生成图表 |
| `compiler_reports/` | 正文引用的 Compose Compiler 报告原件，以及加上稳定性配置文件后的对比版本 |
| `results_*.txt` | 全部原始测量数据 |

**已知局限**：计数面板只统计执行次数，不统计跳过次数（Layout Inspector 有 `Recompositions` / `Skipped Recompositions` 两列计数）；`adb input` 偶尔会出现 `protocol fault` 并丢失按键，输入场景中 Step 4 的第 5 轮因此作废并补测，原始记录保留在数据文件里。
