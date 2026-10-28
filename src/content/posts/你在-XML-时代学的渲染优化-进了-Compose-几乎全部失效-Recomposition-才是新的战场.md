---
title: "你在 XML 时代学的渲染优化，进了 Compose 几乎全部失效——Recomposition 才是新的战场"
date: 2026-10-15
description: "发布前 TODO： 1. 替换全部「📷 截图位」为真机/Android Studio 真实截图 2. 填入「【待实测】」处的帧率、掉帧率（Release 包测量） 3."
tags: ['性能优化', 'Android', 'Compose']
category: "技术"
---
<!--
发布前 TODO：
1. 替换全部「📷 截图位」为真机/Android Studio 真实截图
2. 填入「【待实测】」处的帧率、掉帧率（Release 包测量）
3. 开头"官方文档观点"处补充官方文档原文链接
-->

# 你在 XML 时代学的渲染优化，进了 Compose 几乎全部失效——Recomposition 才是新的战场

> 本文是「Android 应用性能优化」系列第二篇。上一篇我们靠消灭 Overdraw、用 ConstraintLayout 压平层级，治好了商品列表的卡顿。这一篇迁移到 Jetpack Compose，你会发现：那套打法几乎用不上了，新的战场叫 **Recomposition（重组）**。
>
> 读完本文你将掌握：用 Layout Inspector 和 Compiler Report 定位重组问题 → 理解重组的触发机制与稳定性（包含 Strong Skipping 之后的新规则）→ 用四步修复一个搜索列表页。
>
> **环境说明**：本文基于 Kotlin 2.0.20+（Compose 编译器随 Kotlin 发布，Strong Skipping 默认开启）。查看重组计数用 Debug 包，测量帧率用 Release 包。

---

## 一、问题提出：Compose 写的列表，为什么还是卡？

产品又找过来了。

"搜索框输一个字，列表跟着抖一下，感觉比之前 XML 版本还卡。"

你的第一反应，大概率还是上一篇的思路：是不是 Overdraw？是不是层级太深？

**先排除 Overdraw。** 打开 Debug GPU Overdraw（设置 → 开发者选项 → 调试 GPU 过度绘制 → 显示过度绘制区域），看一眼色阶。

> 📷 **【截图位 1】** Debug GPU Overdraw 在搜索页上的真机截图（用来说明：Overdraw 不是主因）

**再排除层级深度。** 官方文档的观点是：Compose 能够高效处理较深的布局层级，这不再是需要刻意规避的问题。Compose 的布局系统要求每个子节点只被测量一次，层级再深，测量开销也是线性增长，不会像 RelativeLayout 嵌套那样成倍放大。

> 上一篇学的那一套（去背景、拍平层级），在这里基本帮不上忙。问题出在另一个地方。

新的性能杀手有一个新名字：**Recomposition（重组）**——CPU 在重复执行本不需要重新执行的 Composable 函数。要找到它，需要另一套工具。

---

### 打开 Layout Inspector，让问题现形

Android Studio 菜单栏：

```
View → Tool Windows → Layout Inspector
```

用 **Debug 包**运行 App 后，Layout Inspector 会自动连接。在组件树里开启 **Show Recomposition Counts**（这个开关在 Layout Inspector 的设置/视图选项里，不同 Android Studio 版本位置略有差异），操作前先点一下重置计数。

然后在搜索框里输入一个字符。

组件树里每个 Composable 后面会出现两列数字：

- **重组次数**：这个 Composable 被重新执行了几次，越小越好
- **跳过次数**：被 Compose 智能跳过了几次，越大越好

你会看到类似这样的输出（示意，以屏幕上可见 8 个 Item 为例）：

```
SearchScreen              重组: 1   跳过: 0
  ├─ SearchBar            重组: 1   跳过: 0
  └─ LazyColumn
       ├─ ProductItem     重组: 1   跳过: 0
       ├─ ProductItem     重组: 1   跳过: 0
       ... （屏幕上可见的 8 个 Item，全部：重组 1 / 跳过 0）
```

> 📷 **【截图位 2】** 输入一个字符后的 Layout Inspector 组件树，用红框标出 SearchScreen 的重组次数和 ProductItem 的「跳过: 0」

两个信号同时出现：

1. **`SearchScreen` 本身在重组**——它是这次重组的"震源"。
2. **`ProductItem` 的跳过次数是 0**——商品内容明明没变，每个 Item 还是被重新执行了。这是 Compose 的"智能重组"没有生效的直接证据。

注意，LazyColumn 只会组合屏幕上可见的 Item，所以这里的数量是可见 Item 数，不是列表总长度。

接下来搞清楚两个问题：为什么 `SearchScreen` 会重组？为什么 `ProductItem` 跳不过去？

---

## 二、相关知识点讲解

### 2.1 Compose 渲染三阶段：和 XML 的关键区别

Compose 渲染一帧同样经过三个阶段：

```
① Composition（组合）：执行 @Composable 函数，决定"显示什么"
② Layout（布局）：测量并放置每个节点，决定"放在哪"
③ Drawing（绘制）：把节点画到 Canvas，提交给 GPU
```

和 XML 对比：

| | XML 时代 | Compose |
|--|---------|---------|
| 测量次数 | RelativeLayout 双重测量，权重二次测量 | 子节点只能被测量一次（显式使用 intrinsic 除外） |
| 层级影响 | 越深越慢，需要拍平 | 深层级不再是主要问题 |
| 优化主战场 | 减少 Measure/Draw 的无效工作 | **减少 Composition 阶段的无效执行** |

最后一行是关键：状态没变化的部分，Compose 可以**跳过 Composition**，直接复用上一次的结果。所以 Compose 性能优化的核心目标是：**让尽可能多的 Composable 在状态变化时被跳过，而不是被重新执行。**

---

### 2.2 谁触发了重组：状态读取的位置决定重组范围

Compose 用快照系统（Snapshot System）追踪状态的读写。每个 `@Composable` 函数执行时，系统会记录它读取了哪些状态。状态一旦变化：

```
状态 query 变化
   ↓
找到所有"读取过 query"的 Composable
   ↓
下一帧重新执行它们 = Recomposition
```

**核心规律：在哪里读取状态，哪里就是重组的震源。**

如果在 `SearchScreen` 的顶层读取了 `query`，那么 `SearchScreen` 整个函数体都会重新执行。它下面的子 Composable 能不能逃过去，取决于下一节的"稳定性"。

---

### 2.3 稳定性：子 Composable 能不能被跳过

父级重组时，Compose 会逐个检查子 Composable 的参数：**参数没变，就跳过**。判断"变没变"的方式，取决于参数类型是稳定的（Stable）还是不稳定的（Unstable）：

```kotlin
// ✅ 稳定：基础类型、String，以及所有属性都是 val 且类型稳定的 data class
data class A(val id: Int, val name: String)

// ❌ 不稳定：含 var 属性
data class B(val id: Int, var name: String)

// ❌ 不稳定：含 List 接口（编译器无法确认它不是 MutableList）
data class C(val id: Int, val tags: List<String>)
```

比较规则（**Kotlin 2.0.20+ 默认开启 Strong Skipping**）：

| | 稳定类型 | 不稳定类型 |
|--|---------|-----------|
| 比较方式 | `equals()` 内容相等 | `===` 实例相等 |
| Strong Skipping 之前 | 参数没变就跳过 | **永远不跳过** |
| Strong Skipping 之后 | 参数没变就跳过 | **实例没变才跳过，实例一变就跳不过** |

这张表是整篇文章的关键。Strong Skipping 让含不稳定参数的 Composable 也有了被跳过的资格，但这不等于"稳定性不重要了"：

- 稳定类型：即使每次重组都是**新创建的实例**，只要内容相等，照样能跳过。
- 不稳定类型：只要实例**换了一个新的**（哪怕内容一模一样），就跳不过。

所以 Strong Skipping 之后，新的问题模式是**实例抖动（instance churn）**：不稳定类型的对象，在每次重组时被重新创建。

**用 Compiler Report 看稳定性**

Compose 编译器可以把稳定性推断结果输出成报告。在模块的 `build.gradle.kts` 里（注意：`composeCompiler` 块在文件顶层，不在 `android {}` 里面；需要先应用 Compose 编译器插件）：

```kotlin
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

执行 `./gradlew assembleRelease`，在 `build/compose_compiler/` 下会生成报告文件，重点看两个：

```
*-composables.txt   每个 Composable 是否 skippable，参数是否稳定
*-classes.txt       每个类被推断为 stable 还是 unstable，以及原因
```

读报告时的要点（Strong Skipping 开启时）：

```
// composables.txt
restartable skippable scheme(...) fun ProductItem(
  unstable product: ProductUi      // ← 看参数前面的 unstable，而不是只看 skippable
)

// classes.txt
unstable class ProductUi {
  stable val id: Int
  stable val name: String
  unstable val tags: List<String>  // ← 罪魁祸首
  <runtime stability> = Unstable
}
```

在 Strong Skipping 下，`skippable` 几乎处处都有，**真正的预警信号是参数前的 `unstable`**。（如果你的项目 Kotlin 版本低于 2.0.20，或者手动关闭了 Strong Skipping，那么缺少 `skippable` 本身就是问题。）

---

### 2.4 两个关键工具：remember 与 derivedStateOf

**`remember`：跨重组缓存计算结果**

```kotlin
// ❌ 每次重组都重新排序
val sorted = contacts.sortedWith(comparator)

// ✅ 只有 contacts 或 comparator 变化时才重新计算
val sorted = remember(contacts, comparator) { contacts.sortedWith(comparator) }
```

**`derivedStateOf`：状态降频**

```kotlin
val listState = rememberLazyListState()

// ❌ firstVisibleItemIndex 每滚过一个 Item 就变一次，
//    读取它的 Composable 每次都要重组
val showFab = listState.firstVisibleItemIndex > 0

// ✅ 你关心的只是"是否大于 0"这个布尔值，
//    只有它真正翻转时才触发重组
val showFab by remember { derivedStateOf { listState.firstVisibleItemIndex > 0 } }
```

`derivedStateOf` 的本质：在频繁变化的输入状态和重组之间加一层过滤，**只有输出结果变化时才通知 UI**。

---

## 三、具体实例应用展示

**案例：商品搜索列表页**——顶部搜索框（实时过滤）+ LazyColumn 商品列表 + 右下角随滚动偏移的 FAB。

### Step 0：诊断现场，先看工具，再动代码

先把案例的完整基础代码列出来（后面每一步只展示改动的部分）。依赖：Compose Material3、Coil（`coil-compose`）。

```kotlin
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

```kotlin
// ===== 页面（问题版本）=====
@Composable
fun SearchScreen(viewModel: SearchViewModel) {
    val products by viewModel.products.collectAsState()
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
            SearchBar(query = query, onQueryChange = { query = it })
            LazyColumn(state = listState) {
                items(uiItems) { ProductItem(it) }              // ❌ ④ 没有 key
            }
        }
        if (showFab) {
            ScrollFab(listState, Modifier.align(Alignment.BottomEnd).padding(16.dp))
        }
    }
}

@Composable
fun SearchBar(query: String, onQueryChange: (String) -> Unit) {
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
        Icon(Icons.Default.ArrowUpward, contentDescription = "回到顶部")
    }
}
```

**先用 Layout Inspector 看**（见前文「截图位 2」）：`SearchScreen` 在重组，`ProductItem` 跳过次数为 0。

**再用 Compiler Report 找原因**：

```
// composables.txt
restartable skippable scheme(...) fun ProductItem(
  unstable product: ProductUi
)

// classes.txt
unstable class ProductUi {
  ...
  unstable val tags: List<String>
  <runtime stability> = Unstable
}
```

> 📷 **【截图位 3】** `composables.txt` 和 `classes.txt` 中 ProductItem / ProductUi 的真实片段，标出 `unstable product` 和 `unstable val tags`

两条证据拼起来，因果链就清楚了：

```
按键 → query 变化 → SearchScreen 重组（震源在顶层）
     → 函数体里重新 filter + map → 产生全新的 ProductUi 实例
     → ProductUi 不稳定，用 === 比较 → 新实例必然"不相等"
     → 所有可见的 ProductItem 都跳不过去
```

问题代码里一共埋了五个问题（代码注释里的 ①~⑤），接下来逐个解决。

---

### Step 1：缩小重组范围，把 query 状态下沉

**根因**：`query` 在 `SearchScreen` 顶层读取，整个页面函数是震源。

**修复**：把 `query` 和列表放进一个独立的 Composable，`SearchScreen` 不再读取 `query`。

```kotlin
@Composable
fun SearchScreen(viewModel: SearchViewModel) {
    val products by viewModel.products.collectAsState()
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
        SearchBar(query = query, onQueryChange = { query = it })
        LazyColumn(state = listState) {
            items(uiItems) { ProductItem(it) }
        }
    }
}
```

**Layout Inspector 验证**：输入字符时，`SearchScreen` 的重组次数不再增加。

> 📷 **【截图位 4】** Step 1 之后输入字符的 Layout Inspector：SearchScreen 不再变化，SearchContent 和 ProductItem 仍在重组

但请注意：**`ProductItem` 的跳过次数依然是 0。** 缩小震源范围，并不会自动让子节点被跳过。这一步的收益，是把页面上其他不相关的内容（FAB、以后可能加的顶栏和 Banner）从重组范围里拿了出去。真正拦住 `ProductItem` 的，是下一步。

---

### Step 2：修复实例抖动，让 ProductItem 真正被跳过

**根因**：`ProductUi` 不稳定，而每次重组都 `map` 出全新实例。两者叠加，`===` 永远不相等。

有两条路，建议两条都走：

**路线 A：让实例不抖。** `map` 不该放在 Composition 里，数据变了才映射一次，放进 ViewModel：

```kotlin
class SearchViewModel(repository: ProductRepository) : ViewModel() {
    // ✅ 数据源变化时才映射一次，之后实例保持不变
    val products: StateFlow<List<ProductUi>> = repository.productsFlow()
        .map { list -> list.map { it.toUi() } }
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

**路线 B：让类型稳定。** 把 `List` 换成 kotlinx 的不可变集合，这样比较方式从 `===` 变成 `equals()`，即使实例变了、内容相等也能跳过，等于给路线 A 加了一道保险：

```kotlin
// build.gradle.kts（版本号请使用 Maven Central 上的最新版）
implementation("org.jetbrains.kotlinx:kotlinx-collections-immutable:<最新版本>")
```

```kotlin
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

如果实在无法修改类型（比如来自第三方模块），可以用 `@Immutable` 注解向编译器"担保"不可变。但这是在覆盖编译器的判断，一旦你的担保不成立，UI 就会出现"该刷新却没刷新"的 Bug，而且很难排查，所以优先用不可变集合，注解作为退路。

**Compiler Report 验证**：

```
stable class ProductUi {
  ...
  stable val tags: ImmutableList<String>
  <runtime stability> = Stable
}
```

**Layout Inspector 验证**：如果这次输入没有改变结果集（例如输入空格，或者拼音输入法的中间状态），所有 `ProductItem` 的重组次数为 0，跳过次数增加。

> 📷 **【截图位 5】** Step 2 之后的 Layout Inspector：ProductItem 跳过次数增加；以及 classes.txt 中 `stable class ProductUi`

不过，当输入真的改变了结果集时，部分 Item 仍然会重组：没有 key 时，Compose 只能按位置匹配 Item，列表一变，位置上换了不同的商品，参数自然不同。这就是下一步要解决的。

---

### Step 3：LazyColumn 加 key，让 Item 按身份而非位置匹配

**根因**：LazyColumn 默认用位置（index）作为 Item 的标识。过滤或重排之后，原来在第 3 位的商品移动到了第 1 位，Compose 看到的是"第 1 位的参数变了"，只能重组。

```kotlin
LazyColumn(state = listState) {
    items(
        items = uiItems,
        key = { it.id }                 // ✅ 用业务 id 作为身份标识
    ) { ProductItem(it) }
}
```

有了 key，Compose 知道"这个 Item 只是换了位置"，内容没变就直接复用并跳过。

**踩坑记录**：

- `key = { index }` 等于没写。列表变化后 index 也变了，和默认行为一样。key 必须是和商品绑定的稳定业务 id。
- key 必须唯一，否则会崩溃；而且类型要能存进 Bundle（Int、Long、String 都可以）。

---

### Step 4：延迟状态读取，让滚动不再触发 Composition

前三步解决的是"输入时"的重组。还剩下"滚动时"的两个问题：问题 ③（`showFab` 让 `SearchScreen` 随 Item 切换而重组）和问题 ⑤（`ScrollFab` 每帧都在重组）。

**4.1 用 `derivedStateOf` 给显隐降频**（问题 ③）：

```kotlin
@Composable
fun SearchScreen(viewModel: SearchViewModel) {
    val products by viewModel.products.collectAsState()
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

```kotlin
// ✅ 接收 () -> Int，而不是 Int
@Composable
fun ScrollFab(scrollOffset: () -> Int, modifier: Modifier = Modifier) {
    FloatingActionButton(
        onClick = { },
        modifier = modifier.offset { IntOffset(0, scrollOffset() / 2) }   // lambda 在 Layout 阶段执行
    ) {
        Icon(Icons.Default.ArrowUpward, contentDescription = "回到顶部")
    }
}
```

为什么这样就不重组了？因为状态是在 `Modifier.offset { }` 的 lambda 里读取的，这个 lambda 在 **Layout 阶段**执行，所以滚动偏移变化时，Compose 只需要重新布局，**不需要重新执行任何 Composable 函数**。对比之前：在函数体里直接读取 `firstVisibleItemScrollOffset`，是在 **Composition 阶段**读取，每一帧都要重组。

同样的思路也适用于 `Modifier.graphicsLayer { }`（在 Draw 阶段读取）。

---

### 量化对比

> 下表中的「重组次数」按代码逻辑推演得出，以屏幕可见 8 个 Item 为例，实际以你本机 Layout Inspector 为准。帧率和掉帧率必须在 **Release 包**上实测（Debug 包有额外开销，数值会明显偏低）。

| 指标 | Step 0 | Step 1 | Step 2 | Step 3 | Step 4 |
|------|--------|--------|--------|--------|--------|
| 每次按键，SearchScreen 重组 | 1 | **0** | 0 | 0 | 0 |
| 按键且结果集不变，ProductItem 重组 | 8 | 8 | **0** | 0 | 0 |
| 按键且结果集变化，ProductItem 重组 | 8 | 8 | 8 | **仅新进入的 Item** | 仅新进入的 Item |
| 滚动时，SearchScreen 重组 | 每滚过 1 个 Item 1 次 | 同左 | 同左 | 同左 | **仅 FAB 显隐翻转时** |
| 滚动时，ScrollFab 重组 | 每帧 | 每帧 | 每帧 | 每帧 | **0** |
| 平均帧率 | 【待实测】 | 【待实测】 | 【待实测】 | 【待实测】 | 【待实测】 |
| 掉帧率 | 【待实测】 | 【待实测】 | 【待实测】 | 【待实测】 | 【待实测】 |

> 📷 **【截图位 6】** 优化前后的 Profile GPU Rendering 柱状图对比，或 `dumpsys gfxinfo` 的 Janky frames 输出对比（Release 包）

---

## 四、总结

### XML 时代 vs Compose 时代：优化手段全对照

| 对比维度 | XML 时代（第一篇） | Compose 时代（本篇） |
|---------|----------------|-----------------|
| 性能敌人 | Overdraw + 层级过深 | 不必要的 Recomposition |
| 诊断工具 | Debug GPU Overdraw（色阶图） | Layout Inspector 重组/跳过计数 |
| 静态分析 | Layout Inspector 层级树 | Compose Compiler Report |
| 根因 | GPU 画了不该画的像素 | CPU 执行了不该执行的函数 |
| 解决方向 | 拍平层级 / 去掉重复背景 | 缩小重组范围 / 保证可跳过 |
| 核心手段 | ConstraintLayout | 状态下沉 / 稳定类型 / `derivedStateOf` / 延迟读取 |

### 速查表：5 条 Compose 渲染优化原则

```
✅ 1. 在哪里读状态，哪里就是重组震源
      把状态读取下沉到真正需要它的最小范围

✅ 2. 用 derivedStateOf 给频繁变化的状态降频
      你关心的是"结果"（如 index > 0），不是"过程"（index 本身）

✅ 3. 不稳定类型比较实例，实例一抖就跳不过
      · 别在 Composition 里为不稳定类型反复创建新对象（map 放进 ViewModel 或 remember）
      · 能让类型稳定就稳定：List → ImmutableList
      · 用 Compiler Report 里的 unstable 参数标记做检查，不要只看 skippable

✅ 4. LazyColumn 必须提供 key
      key = { item.id }，用业务 id，不要用 index

✅ 5. 高频状态的读取推迟到 Layout / Draw 阶段
      Modifier.offset { } / Modifier.graphicsLayer { } 的 lambda 形式
      → 状态变化只触发布局或绘制，不触发重组
```

### 方法论升华

XML 时代优化的是"画布"：让 GPU 少画几层不该画的像素。Compose 时代优化的是"决策"：让运行时少执行几个不该执行的函数。

两者思想一致，都是**减少无效工作**，只是执行者从 GPU 换成了 CPU，工具从色阶图换成了重组计数。理解了这一点，再遇到 Compose 的性能问题，就不要先问"这里有没有 Overdraw"，而要问："这个 Composable 是不是在本该被跳过的时候被迫执行了？它被跳过的条件是什么？"

### 下篇预告

渲染优化解决的是内容出现之后的流畅度。但在内容出现之前，用户还要经历一段等待——**冷启动**。

下一篇，我们来拆 Android 冷启动的全链路：从点击图标到第一帧出现，系统和 App 各自做了什么，每个环节怎么量化，优化的刀该怎么下。
