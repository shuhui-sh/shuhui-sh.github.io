---
title: "Jetpack Compose 常用组件与控件零基础入门指南"
date: 2026-09-04
description: "1. Compose 是什么 2. 环境准备 3. 第一个 Compose 界面 4. Modifier：组件的'装饰管道'"
tags: ['Compose']
draft: true
category: "技术"
---
> 本文面向**完全没接触过 Compose** 的读者。不需要任何 Compose 前置知识，只要会一点 Kotlin 基础语法（甚至只会别的编程语言）就能读懂。读完你将能够：
>
> - 理解声明式 UI 的核心思想，知道它和 XML 写界面有什么本质区别；
> - 熟练使用 `Text`、`Button`、`TextField`、`Image`、`Checkbox`、`Switch`、`RadioButton`、`Slider` 等常用控件；
> - 会用 `Row` / `Column` / `Box` 三大布局容器和 `Modifier` 排版；
> - 会用 `LazyColumn` 写长列表、用 `Scaffold` 搭页面骨架、用 `AlertDialog` 弹对话框；
> - 最后动手完成一个可运行的「待办清单」小 Demo。
>
> 全文代码基于 **Material 3**（`androidx.compose.material3`），这是目前 Compose 的默认 UI 库。

---

## 目录

1. [Compose 是什么](#一compose-是什么)
2. [环境准备](#二环境准备)
3. [第一个 Compose 界面](#三第一个-compose-界面)
4. [Modifier：组件的"装饰管道"](#四modifier组件的装饰管道)
5. [三大布局容器：Row / Column / Box](#五三大布局容器row--column--box)
6. [状态：Compose 的驱动力](#六状态compose-的驱动力)
7. [常用控件逐个讲](#七常用控件逐个讲)
8. [列表：LazyColumn / LazyRow](#八列表lazycolumn--lazyrow)
9. [页面骨架：Scaffold](#九页面骨架scaffold)
10. [对话框：AlertDialog](#十对话框alertdialog)
11. [实战：做一个待办清单](#十一实战做一个待办清单)
12. [新手常见坑清单](#十二新手常见坑清单)
13. [组件速查表](#十三组件速查表对照-view-系统)
14. [下一步学什么](#十四下一步学什么)

---

## 一、Compose 是什么

### 1.1 传统写法：命令式 UI

在 Compose 之前，Android 写界面是这样的：

1. 在 XML 里写好布局文件；
2. 在代码里 `findViewById` 找到控件；
3. 手动调用方法修改控件：

```kotlin
val textView = findViewById<TextView>(R.id.tv_title)
textView.text = "欢迎"
textView.visibility = View.GONE
button.setOnClickListener { ... }
```

这叫**命令式**：你要一步步告诉系统"先找到这个控件，再把它改成什么样"。业务一复杂，"改控件"的代码就会散落在各处，界面状态和数据显示很容易对不上，出 bug 还难查。

### 1.2 Compose：声明式 UI

Compose 的思路完全不同，只需记住一个公式：

```
UI = f(State)
```

**你只写一个函数，描述"界面长什么样"；状态（State）由你管理，状态一变，Compose 自动重新执行相关函数、刷新界面。** 你从此不再"找控件"，也不再手动"改控件"。

| 对比项 | 传统 View 体系 | Jetpack Compose |
|---|---|---|
| 布局写在哪 | XML 文件 | Kotlin 函数（`@Composable`） |
| 如何获取控件 | `findViewById` / ViewBinding | 不需要，UI 就是函数本身 |
| 如何更新界面 | 手动调用控件方法 | 改状态，Compose 自动刷新 |
| 界面嵌套 | XML 标签嵌套 | 函数调用嵌套 |
| 代码量 | 布局 + 胶水代码 | 通常少 30%~50% |

一句话总结：**Compose 里，控件不再是"对象"，而是"函数的调用结果"；你描述结果，框架负责过程。**

---

## 二、环境准备

**最简单的方式**：用 Android Studio 新建工程，选择 **Empty Activity** 模板（注意是带 Compose 图标的那个），它默认就配好了全部 Compose 依赖，可以直接跳到第三节。

如果你想手动给已有工程加 Compose，参考下面的最小配置：

```kotlin
// app/build.gradle.kts

plugins {
    id("com.android.application")
    kotlin("android")
    kotlin("plugin.compose") // Kotlin 2.0+ 用这个插件启用 Compose 编译器
}

android {
    compileSdk = 35          // 建议 35 及以上

    defaultConfig {
        minSdk = 24
    }

    buildFeatures {
        compose = true
    }
}

dependencies {
    // BOM：统一管理所有 Compose 库的版本，避免版本冲突
    // 版本号请以官方 BOM 映射表为准：
    // https://developer.android.com/develop/ui/compose/bom/bom-mapping
    val composeBom = platform("androidx.compose:compose-bom:2025.06.01")
    implementation(composeBom)

    implementation("androidx.activity:activity-compose:1.9.3") // setContent 扩展
    implementation("androidx.compose.ui:ui")                    // Compose 核心
    implementation("androidx.compose.material3:material3")      // Material 3 组件
    implementation("androidx.compose.ui:ui-tooling-preview")    // @Preview 支持
    debugImplementation("androidx.compose.ui:ui-tooling")       // 预览工具

    // 可选：加载网络图片用的 Coil（类似 View 时代的 Glide）
    implementation("io.coil-kt:coil-compose:2.7.0")
}
```

> 说明：BOM（Bill of Materials）本身不包含代码，它只是一张"版本对照表"。引入后，`ui`、`material3` 等库就不用各自写版本号了，BOM 会帮你配成互相兼容的版本。

---

## 三、第一个 Compose 界面

### 3.1 最小可运行示例

```kotlin
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {          // 从这里开始，进入 Compose 的世界
            MyApp()
        }
    }
}

@Composable                   // 关键注解：标记这是一个"可组合函数"
fun MyApp() {
    Text(text = "你好，Compose！")
}

@Preview(showBackground = true) // 不用运行 App，在 Android Studio 里直接预览
@Composable
fun MyAppPreview() {
    MyApp()
}
```

运行后屏幕中央会显示一行"你好，Compose！"。就这么几行，有几个**必须建立的概念**：

1. **`@Composable` 函数是"界面的积木"**。`Text(...)` 不是创建一个控件对象，而是"声明这里有一段文字"。
2. **可组合函数只能嵌套调用**：`@Composable` 函数只能在另一个 `@Composable` 函数里被调用，不能在普通函数里随便调。
3. **命名用大驼峰**（`MyApp`、`UserCard`），因为它代表一块 UI，视觉上和普通函数区分开。
4. **`@Preview` 是开发利器**：写完组件顺手加个预览函数，改完代码不用装机就能看效果。

### 3.2 内容 lambda：大括号里装子组件

很多组件（`Button`、`Card`、`Row`、`Column`、`Scaffold`…）的最后一个参数是一个 **`content` lambda**——用尾随大括号的语法写，里面放子组件：

```kotlin
Button(onClick = { /* 点击事件 */ }) {   // 大括号里的就是按钮的内容
    Text("点我")
}
```

这等价于 `Button(onClick = ..., content = { Text("点我") })`。**"参数在外层，孩子在括号里"** 这个模式会贯穿全文，先混个眼熟。

---

## 四、Modifier：组件的"装饰管道"

`Modifier` 是 Compose 里给组件设置尺寸、间距、背景、点击等属性的统一入口，几乎每个组件都有 `modifier` 参数。它用**链式调用**，像流水线一样一层层"装饰"组件：

```kotlin
Text(
    text = "Hello",
    modifier = Modifier
        .padding(16.dp)            // 第 1 层：外边距 16dp
        .background(Color.Yellow)  // 第 2 层：黄色背景
        .padding(8.dp)             // 第 3 层：背景之内再留 8dp
)
```

### ⚠️ 顺序很重要

Modifier 是**从外到内依次生效**的。上面例子里，黄色背景**不包含**第一个 `padding(16.dp)` 的区域，但**包含**第二个 `padding(8.dp)` 的区域。交换顺序 = 换了一种效果，这是新手最常困惑的点，建议配合 `@Preview` 亲手试一遍。

### 常用 Modifier 速查

| 写法 | 作用 |
|---|---|
| `Modifier.size(48.dp)` / `.width()` / `.height()` | 固定尺寸 |
| `.fillMaxWidth()` / `.fillMaxHeight()` / `.fillMaxSize()` | 占满父容器的宽/高/全部 |
| `.wrapContentSize()` | 内容多大就多大 |
| `.padding(12.dp)` / `.padding(horizontal = 16.dp, vertical = 8.dp)` | 内边距（注意顺序） |
| `.background(Color.Red)` / `.background(Color.Red, shape)` | 背景色 |
| `.clip(RoundedCornerShape(8.dp))` | 裁剪成圆角/圆形等形状 |
| `.clickable { ... }` | 让任意组件可点击 |
| `.offset(x = 4.dp, y = (-2).dp)` | 偏移 |
| `.weight(1f)` | 在 Row/Column 中占权重（只能在 Row/Column 内部用） |

> 小提示：`.dp` 是 Kotlin 扩展属性，`16.dp` 就是把数字转成密度无关像素。记得导入 `androidx.compose.ui.unit.dp`。

---

## 五、三大布局容器：Row / Column / Box

Compose 没有 `LinearLayout`、`FrameLayout` 这些类，取而代之的是三个更简单的函数。对照旧体系一秒理解：

| Compose | 相当于 View 体系的 | 排列方式 |
|---|---|---|
| `Column` | 垂直 LinearLayout | 子组件**从上到下** |
| `Row` | 水平 LinearLayout | 子组件**从左到右** |
| `Box` | FrameLayout | 子组件**层叠**（后写的在上层） |

```
   Column            Row                  Box
┌──────────┐   ┌──────────────────┐   ┌──────────┐
│    A     │   │  A    B    C     │   │   A      │
│    B     │   └──────────────────┘   │     B    │  ← B 叠在 A 上面
│    C     │                          │       C  │
└──────────┘                          └──────────┘
```

### 5.1 对齐与分布：两个维度，两套参数

每个容器都有两个方向的参数，记住口诀：**主轴用 arrangement（分布），交叉轴用 alignment（对齐）**。

以 `Column`（主轴是垂直方向）为例：

```kotlin
Column(
    modifier = Modifier
        .fillMaxWidth()
        .height(200.dp),
    verticalArrangement = Arrangement.SpaceBetween, // 主轴：垂直方向如何分布
    horizontalAlignment = Alignment.CenterHorizontally // 交叉轴：水平方向如何对齐
) {
    Text("第一行")
    Text("第二行")
    Text("第三行")
}
```

`Row` 正好反过来：主轴参数叫 `horizontalArrangement`，交叉轴叫 `verticalAlignment`。

**arrangement 常用值**：`Start` / `Center` / `End` / `SpaceBetween`（两端对齐）/ `SpaceAround` / `SpaceEvenly`（等距）。

**子组件单独对齐**：不想整批对齐、只想让某一个子组件靠边？用子组件自己的 `align`：

```kotlin
Column(modifier = Modifier.fillMaxWidth()) {
    Text("我靠左", modifier = Modifier.align(Alignment.Start))
    Text("我靠右", modifier = Modifier.align(Alignment.End))
}
```

### 5.2 Spacer：空白占位

`Spacer` 就是一块空白，常用来做间距：

```kotlin
Row(verticalAlignment = Alignment.CenterVertically) {
    Icon(Icons.Default.Star, contentDescription = null)
    Spacer(modifier = Modifier.width(8.dp))   // 图标和文字间隔 8dp
    Text("收藏")
}
```

### 5.3 weight：按比例分配空间

`weight` 只能在 `Row` / `Column` 内部使用（它是作用域扩展函数），用法和 LinearLayout 的 `layout_weight` 一样：

```kotlin
Row(modifier = Modifier.fillMaxWidth()) {
    Text("左侧固定内容")
    Text("我占据剩余全部宽度", modifier = Modifier.weight(1f))
}
```

---

## 六、状态：Compose 的驱动力

前面说过 `UI = f(State)`。在 Compose 里，"状态"就是**任何会随时间变化、且需要反映到界面上的数据**：输入框里的文字、勾选框是否选中、列表数据、加载中标记……

### 6.1 remember + mutableStateOf

看一个经典计数器：

```kotlin
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue

@Composable
fun Counter() {
    // remember：让值在"重组"之间保留下来
    // mutableStateOf：把这个值变成"可观察的状态"，它一变，UI 自动刷新
    var count by remember { mutableStateOf(0) }

    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text("已点击 $count 次")
        Button(onClick = { count++ }) {   // 改状态 → UI 自动更新，无需手动 setText
            Text("点我 +1")
        }
    }
}
```

点击按钮 → `count` 变化 → Compose 发现 `Counter` 用到了 `count` → **重新执行 `Counter` 函数**（这个过程叫**重组 / recomposition**）→ 界面显示新数字。

两个关键点：

- **为什么需要 `remember`？** 每次重组都会重新执行函数体，如果写 `var count = 0`，每次重组都会被重置为 0。`remember` 让值"存活"过重组。
- **`by` 是 Kotlin 属性委托**，让你直接写 `count` 而不用 `count.value`。需要导入 `getValue` / `setValue`（上面代码前两行）。不用委托的等价写法：`val countState = remember { mutableStateOf(0) }`，然后用 `countState.value` 读写。

### 6.2 "受控组件"思想

这是贯穿所有交互控件的核心模式：**组件自己不偷偷记状态，状态由你持有，组件只负责"显示状态"和"汇报变化"**。每个可交互组件几乎都长成一个样：

```
组件(value = 当前状态, onXxxChange = { 新值 -> 你更新状态 })
```

下面的 Checkbox、Switch、TextField、Slider 全是这个套路，学会一个就会全部。

---

## 七、常用控件逐个讲

> 以下示例默认已导入 `androidx.compose.material3.*`、`androidx.compose.foundation.layout.*`、`androidx.compose.runtime.*`、`androidx.compose.ui.*` 相关包。Android Studio 里按 `Alt + Enter` 会自动补全导入。

### 7.1 Text：文本显示

对应旧体系的 `TextView`，是最常用的组件。

```kotlin
// 最简写法
Text("你好，Compose")

// 完整写法
Text(
    text = "这是一段很长很长很长很长很长很长的文本，用来演示截断效果",
    style = MaterialTheme.typography.bodyLarge,  // 推荐：直接用主题的排版样式
    color = MaterialTheme.colorScheme.primary,   // 推荐：用主题色
    maxLines = 1,                                // 最多 1 行
    overflow = TextOverflow.Ellipsis,            // 超出显示 "…"
    textAlign = TextAlign.Center,                // 文字对齐（需要配合占满宽度）
    modifier = Modifier.fillMaxWidth()
)
```

**关于字体样式的最佳实践**：优先用 `MaterialTheme.typography.*`（`headlineMedium`、`titleLarge`、`bodyMedium`…一整套从大到小的语义化槽位），而不是到处手写 `fontSize = 16.sp, fontWeight = FontWeight.Bold`。统一走主题，将来改设计规范只用改一处。颜色同理，尽量用 `MaterialTheme.colorScheme.*` 或项目自定义的语义色，不要硬编码 `Color(0xFFxxxxxx)`。

### 7.2 Button 家族：按钮

Material 3 提供了一组按钮，按"视觉强度"从强到弱排列：

```kotlin
Button(onClick = { }) { Text("实心按钮（最重要）") }

OutlinedButton(onClick = { }) { Text("描边按钮（次要）") }

TextButton(onClick = { }) { Text("文字按钮（最弱）") }

IconButton(onClick = { }) {                     // 图标按钮
    Icon(Icons.Default.Favorite, contentDescription = "收藏")
}

Button(onClick = { }, enabled = false) { Text("禁用状态自动置灰") }
```

**按钮内容可以是任意组合**——想放"图标 + 文字"？直接在内容 lambda 里摆：

```kotlin
Button(onClick = { }) {
    Icon(Icons.Default.Add, contentDescription = null)
    Spacer(modifier = Modifier.width(6.dp))
    Text("新建")
}
```

> 补充：还有 `FilledTonalButton`（次级实心按钮）、`ElevatedButton`（带阴影的按钮），用法完全一样，只是视觉风格不同，按需取用。

### 7.3 TextField：输入框

对应旧体系的 `EditText`。这是理解"受控组件"的最佳例子：

```kotlin
var name by remember { mutableStateOf("") }   // ① 状态在你手里

OutlinedTextField(
    value = name,                             // ② 组件显示这个状态
    onValueChange = { name = it },            // ③ 用户打字 → 回调新值 → 你更新状态
    label = { Text("昵称") },
    placeholder = { Text("请输入昵称") },
    leadingIcon = { Icon(Icons.Default.Person, contentDescription = null) },
    singleLine = true,
    modifier = Modifier.fillMaxWidth()
)
```

把上面三步连起来读：**输入框显示 `name` → 用户敲键盘 → `onValueChange` 拿到新值写回 `name` → 重组 → 输入框显示新内容。** 如果你忘了在 `onValueChange` 里更新状态，输入框就会"打不进字"——这是新手最高频的 bug，本质是没理解受控模式。

两个常用变体：

| 组件 | 外观 |
|---|---|
| `TextField` | 实心填充背景 |
| `OutlinedTextField` | 描边样式（表单里最常用） |

密码输入框：

```kotlin
var password by remember { mutableStateOf("") }

OutlinedTextField(
    value = password,
    onValueChange = { password = it },
    label = { Text("密码") },
    singleLine = true,
    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password), // 弹出密码键盘
    visualTransformation = PasswordVisualTransformation()                      // 显示为小圆点
)
```

### 7.4 Image 与 Icon：图片和图标

**显示本地图片**（对应 `ImageView`）：

```kotlin
Image(
    painter = painterResource(id = R.drawable.avatar),  // res/drawable 下的图片
    contentDescription = "用户头像",   // 必填！供屏幕阅读器（无障碍）朗读
    modifier = Modifier
        .size(96.dp)
        .clip(CircleShape),            // 裁剪成圆形
    contentScale = ContentScale.Crop   // 缩放方式，类似 ImageView 的 scaleType
)
```

`contentScale` 常用值：`Crop`（裁剪填满）、`Fit`（完整显示留黑边）、`FillBounds`（拉伸变形）。

**显示矢量小图标**：

```kotlin
Icon(
    imageVector = Icons.Default.Favorite,
    contentDescription = "喜欢",
    tint = MaterialTheme.colorScheme.primary   // 图标着色
)
```

`Icons.Default.*` 自带了一批常用图标（`Add`、`Delete`、`Search`、`Settings`、`Close`、`Menu`、`Home`、`Person`、`Star` 等）；更多图标需要额外引入 `material-icons-extended` 依赖。

**显示网络图片**：Compose 不内置网络图片加载，一般用 Coil 库的 `AsyncImage`，用法和 `Image` 几乎一样：

```kotlin
AsyncImage(
    model = "https://example.com/pic.jpg",   // 直接给 URL
    contentDescription = "网络图片",
    modifier = Modifier
        .size(120.dp)
        .clip(RoundedCornerShape(12.dp)),
    contentScale = ContentScale.Crop
)
```

### 7.5 选择类控件：Checkbox / Switch / RadioButton / Slider

四个控件都是"受控组件"模式，一口气看完：

**复选框 Checkbox：**

```kotlin
var agreed by remember { mutableStateOf(false) }

Row(verticalAlignment = Alignment.CenterVertically) {
    Checkbox(checked = agreed, onCheckedChange = { agreed = it })
    Text("我已阅读并同意用户协议")
}
```

**开关 Switch：**

```kotlin
var notifyEnabled by remember { mutableStateOf(true) }

Row(verticalAlignment = Alignment.CenterVertically) {
    Text("接收推送通知", modifier = Modifier.weight(1f))
    Switch(checked = notifyEnabled, onCheckedChange = { notifyEnabled = it })
}
```

**单选组 RadioButton**：`RadioButton` 本身只管"我是否被选中"，"单选互斥"的逻辑要你自己用状态实现——这正是声明式的思路：

```kotlin
var platform by remember { mutableStateOf("Android") }

Row {
    listOf("Android", "iOS", "鸿蒙").forEach { option ->
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.clickable { platform = option } // 点文字也能选中
        ) {
            RadioButton(
                selected = platform == option,
                onClick = { platform = option }
            )
            Text(option)
        }
    }
}
```

**滑块 Slider：**

```kotlin
var volume by remember { mutableStateOf(0.5f) }   // 取值范围 0f..1f

Column {
    Text("音量：${(volume * 100).toInt()}%")
    Slider(
        value = volume,
        onValueChange = { volume = it },
        steps = 9    // 可选：在首尾之间再加 9 个刻度点
    )
}
```

### 7.6 进度指示器：ProgressIndicator

```kotlin
// 不确定进度（"加载中"转圈）
CircularProgressIndicator()

// 确定进度（需要 lambda 形式传进度值）
CircularProgressIndicator(progress = { 0.7f })
LinearProgressIndicator(
    progress = { 0.6f },
    modifier = Modifier.fillMaxWidth()
)
```

> 注：较老版本的 material3 用的是 `progress = 0.6f`（直接传 Float），新版本改成了 lambda 形式 `progress = { 0.6f }`，编译器报错时按提示改即可。

### 7.7 容器组件：Card / Surface / Divider

**Card 卡片**：自带圆角、阴影的容器，用来把一组内容"打包"成卡片：

```kotlin
Card(
    modifier = Modifier.fillMaxWidth(),
    shape = RoundedCornerShape(12.dp),
    elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
) {
    Column(modifier = Modifier.padding(16.dp)) {   // 卡片内部随便嵌套
        Text("卡片标题", style = MaterialTheme.typography.titleMedium)
        Spacer(modifier = Modifier.height(8.dp))
        Text("这里是卡片的正文内容……", style = MaterialTheme.typography.bodyMedium)
    }
}
```

**Surface**：比 Card 更基础的"主题表面"容器（可设背景色、形状、内容色），Scaffold 的底色就是 Surface。初学阶段知道它存在即可，用 Card 的场景更多。

**分割线：**

```kotlin
HorizontalDivider()          // 水平分割线（旧名 Divider 已废弃）
VerticalDivider()            // 垂直分割线
```

---

## 八、列表：LazyColumn / LazyRow

对应旧体系的 `RecyclerView`，但**不需要写 Adapter、ViewHolder**，几行代码搞定。

- `LazyColumn`：垂直滚动列表（最常用）
- `LazyRow`：水平滚动列表
- 前缀 **Lazy** 的含义：**只创建和渲染屏幕上可见的那几项**，滚出屏幕的会被回收。所以几百上千条数据也不卡。

### 8.1 基本用法

```kotlin
data class Contact(val id: Long, val name: String, val phone: String)

@Composable
fun ContactList(contacts: List<Contact>) {
    LazyColumn {
        items(contacts, key = { it.id }) { contact ->   // key：每项的唯一标识
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp)
            ) {
                Text(contact.name, style = MaterialTheme.typography.titleMedium)
                Text(contact.phone, style = MaterialTheme.typography.bodyMedium)
            }
            HorizontalDivider()
        }
    }
}
```

`LazyColumn` 的 content lambda 里有几种"声明条目"的函数：

| 函数 | 用途 |
|---|---|
| `item { ... }` | 声明**单个**条目（适合放标题、头部） |
| `items(list) { ... }` | 声明**一组**条目 |
| `itemsIndexed(list) { index, item -> ... }` | 一组条目，且能拿到下标 |

> **为什么要传 `key`？** 默认用位置当标识，列表增删项时容易触发不必要的重组和动画错乱。传一个稳定的唯一 id（数据库 id、业务 id），性能和动画都更稳。

### 8.2 网格：LazyVerticalGrid

```kotlin
LazyVerticalGrid(columns = GridCells.Fixed(2)) {   // 固定 2 列；自适应宽可用 GridCells.Adaptive(100.dp)
    items(photos) { photo ->
        AsyncImage(model = photo.url, contentDescription = null, modifier = Modifier.height(100.dp))
    }
}
```

### 8.3 现成的列表条目组件：ListItem

Material 3 提供了标准"列表项"排版，不用自己拼 Row/Column：

```kotlin
ListItem(
    headlineContent = { Text("陈小明") },
    supportingContent = { Text("138****8888") },
    leadingContent = { Icon(Icons.Default.Person, contentDescription = null) },
    trailingContent = { Text("昨天") }
)
```

---

## 九、页面骨架：Scaffold

`Scaffold` 是 Material 页面的"脚手架"，一次性提供：**顶栏（TopAppBar）、底栏（BottomBar）、浮动按钮（FAB）、Snackbar 提示位**，并自动为内容区计算留白。

```kotlin
@OptIn(ExperimentalMaterial3Api::class)   // 个别版本中 TopAppBar 仍是实验 API，按编译器提示加
@Composable
fun HomeScreen() {
    Scaffold(
        topBar = {
            TopAppBar(title = { Text("我的应用") })
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { /* 新建 */ }) {
                Icon(Icons.Default.Add, contentDescription = "新建")
            }
        }
    ) { innerPadding ->
        // ⚠️ 关键：必须把 innerPadding 应用到内容上，
        // 否则内容会钻到顶栏下面去
        LazyColumn(modifier = Modifier.padding(innerPadding)) {
            items(50) { index ->
                Text("第 $index 条内容", modifier = Modifier.padding(16.dp))
            }
        }
    }
}
```

**新手最容易忽略的就是 `innerPadding`**：Scaffold 的内容 lambda 会收到一个 `PaddingValues` 参数，代表"顶栏/底栏占了多高地盘"，你必须把它 `padding` 给内容，界面才不会被遮挡。

想弹底部提示条（Snackbar）？加两行：

```kotlin
val snackbarHostState = remember { SnackbarHostState() }
val scope = rememberCoroutineScope()

Scaffold(
    snackbarHost = { SnackbarHost(snackbarHostState) },
    floatingActionButton = {
        FloatingActionButton(onClick = {
            scope.launch { snackbarHostState.showSnackbar("操作成功") }
        }) {
            Icon(Icons.Default.Add, contentDescription = "新建")
        }
    }
    // ...其余同上
) { innerPadding -> ... }
```

---

## 十、对话框：AlertDialog

Compose 里对话框的显示/隐藏**完全由一个 Boolean 状态控制**——状态为 `true` 就把对话框"组合"出来，为 `false` 它就消失。没有 `show()` / `dismiss()` 方法。

```kotlin
var showDeleteDialog by remember { mutableStateOf(false) }

Button(onClick = { showDeleteDialog = true }) {
    Text("删除")
}

if (showDeleteDialog) {
    AlertDialog(
        onDismissRequest = { showDeleteDialog = false },  // 点击对话框外部时回调
        title = { Text("确认删除") },
        text = { Text("删除后无法恢复，确定要删除这条记录吗？") },
        confirmButton = {
            TextButton(onClick = {
                // 执行删除逻辑……
                showDeleteDialog = false
            }) { Text("确定") }
        },
        dismissButton = {
            TextButton(onClick = { showDeleteDialog = false }) { Text("取消") }
        }
    )
}
```

记住这个套路：**`if (状态) { 对话框 }` + 所有关闭入口都把状态置回 `false`**。底部弹窗 `ModalBottomSheet`、下拉菜单 `DropdownMenu` 的用法思路完全相同。

---

## 十一、实战：做一个待办清单

把前面学的东西全部串起来：Scaffold + TopAppBar + 输入框 + 按钮 + LazyColumn + Checkbox + IconButton。

```kotlin
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp

/** 数据模型：注意三个字段都是 val —— 状态尽量不可变，改动通过"生成新列表"实现 */
data class TodoItem(val id: Long, val text: String, val done: Boolean = false)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TodoScreen() {
    var input by remember { mutableStateOf("") }
    var todos by remember { mutableStateOf(emptyList<TodoItem>()) }

    Scaffold(
        topBar = { TopAppBar(title = { Text("待办清单") }) }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)          // 别忘了应用 innerPadding
        ) {
            // —— 输入区 ——
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                OutlinedTextField(
                    value = input,
                    onValueChange = { input = it },
                    modifier = Modifier.weight(1f),
                    placeholder = { Text("输入新的待办事项") },
                    singleLine = true
                )
                Spacer(modifier = Modifier.width(8.dp))
                Button(
                    onClick = {
                        if (input.isNotBlank()) {
                            // 用 + 生成新列表，而不是往旧列表里 add
                            todos = todos + TodoItem(
                                id = System.currentTimeMillis(),
                                text = input.trim()
                            )
                            input = ""   // 清空输入框
                        }
                    }
                ) {
                    Text("添加")
                }
            }

            // —— 列表区 ——
            if (todos.isEmpty()) {
                // 空状态提示
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    Text("暂无待办事项，先添加一条吧～")
                }
            } else {
                LazyColumn {
                    items(todos, key = { it.id }) { todo ->
                        TodoRow(
                            todo = todo,
                            onToggle = {
                                todos = todos.map {
                                    if (it.id == todo.id) it.copy(done = !it.done) else it
                                }
                            },
                            onDelete = {
                                todos = todos.filterNot { it.id == todo.id }
                            }
                        )
                        HorizontalDivider()
                    }
                }
            }
        }
    }
}

/** 单条待办：勾选切换完成状态，右侧删除 */
@Composable
fun TodoRow(
    todo: TodoItem,
    onToggle: () -> Unit,
    onDelete: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Checkbox(checked = todo.done, onCheckedChange = { onToggle() })
        Text(
            text = todo.text,
            modifier = Modifier.weight(1f),
            style = MaterialTheme.typography.bodyLarge,
            textDecoration = if (todo.done) TextDecoration.LineThrough else TextDecoration.None
        )
        IconButton(onClick = onDelete) {
            Icon(Icons.Default.Delete, contentDescription = "删除")
        }
    }
}
```

把这个 `TodoScreen()` 放进 `setContent { }` 里就能跑。代码里藏着两个**声明式思维的关键习惯**，值得反复体会：

1. **改列表不"修改原列表"，而是"生成新列表"**：`todos + 新项`、`todos.map { ... }`、`todos.filterNot { ... }`。配合 `data class` 的 `copy()`，状态变化清晰可追溯，也是 Compose 正确触发重组的前提。
2. **子组件不持有状态（状态提升 / State Hoisting）**：`TodoRow` 自己没有任何 `remember`，它只接收数据、通过回调"汇报"用户的动作。这样的组件是"无状态"的，好复用、好测试、好预览。

---

## 十二、新手常见坑清单

| # | 坑 | 现象 | 解法 |
|---|---|---|---|
| 1 | 状态没包 `remember` | 界面一刷新，计数器归零、输入清空 | `remember { mutableStateOf(...) }` |
| 2 | Modifier 顺序搞错 | 背景色范围不对、点击区域不对 | 记住"从外到内依次生效"，多预览尝试 |
| 3 | `onValueChange` 里没更新状态 | 输入框打不进字 | 受控组件：新值必须写回状态 |
| 4 | Scaffold 忘了 `innerPadding` | 内容被顶栏遮住一截 | `Modifier.padding(innerPadding)` |
| 5 | 长列表用 `Column + forEach` | 几百条数据直接卡死 | 换成 `LazyColumn { items(...) }` |
| 6 | LazyColumn 不传 `key` | 增删条目时动画错乱、状态串位 | `items(list, key = { it.id })` |
| 7 | 在 Composable 函数体里做副作用 | 随机数每次都变、网络请求重复发起 | 副作用放 `LaunchedEffect` / 事件回调里 |
| 8 | 颜色/字号到处硬编码 | 改设计规范时全局搜索替换到崩溃 | 统一走 `MaterialTheme.typography/colorScheme` |
| 9 | 直接 `list.add()` 改原列表 | 界面偶尔不刷新 | 用 `+` / `map` / `filter` 生成新列表 |
| 10 | 独立 ComposeView 不加主题 | 弹窗/浮窗样式回落到 Material 默认丑样式 | 内容外层显式包一层应用的 Theme Composable |

---

## 十三、组件速查表（对照 View 系统）

从 XML 时代过来的读者，拿这张表当字典查：

| Compose 组件 | View 体系对应物 | 用途 |
|---|---|---|
| `Text` | `TextView` | 文本显示 |
| `TextField` / `OutlinedTextField` | `EditText` | 文本输入 |
| `Image` / `Icon` | `ImageView` | 图片 / 矢量图标 |
| `Button` / `OutlinedButton` / `TextButton` | `Button` | 按钮 |
| `IconButton` | `ImageButton` | 图标按钮 |
| `FloatingActionButton` | `FloatingActionButton` | 悬浮操作按钮 |
| `Checkbox` | `CheckBox` | 多选框 |
| `Switch` | `SwitchCompat` | 开关 |
| `RadioButton` | `RadioButton` | 单选按钮（互斥逻辑自己写） |
| `Slider` | `SeekBar` | 滑块 |
| `CircularProgressIndicator` | 圆形 `ProgressBar` | 加载转圈 |
| `LinearProgressIndicator` | 水平 `ProgressBar` | 进度条 |
| `Row` / `Column` | `LinearLayout` | 线性排列 |
| `Box` | `FrameLayout` | 层叠布局 |
| `LazyColumn` / `LazyRow` | `RecyclerView` | 懒加载滚动列表 |
| `LazyVerticalGrid` | `RecyclerView + GridLayoutManager` | 网格 |
| `Card` | `CardView` | 卡片容器 |
| `Surface` | — | 主题化表面容器 |
| `Scaffold` | — | Material 页面骨架 |
| `AlertDialog` | `AlertDialog` | 对话框 |
| `HorizontalDivider` | 1dp 的 `View` | 分割线 |
| `Spacer` | 空 `View` 占位 | 空白间距 |

---

## 十四、下一步学什么

掌握本文内容后，你已经能用 Compose 搭出绝大多数页面。继续进阶的路线：

1. **状态提升（State Hoisting）与 ViewModel**：真实项目里状态不会都放在 `remember` 中，而是放进 `ViewModel`，用 `collectAsStateWithLifecycle()` 在界面里收集。这是 Compose 与业务层结合的标准姿势。
2. **Navigation 导航**：多页面跳转、传参、返回栈，学 Jetpack Navigation 的 Compose 版本。
3. **动画**：从最简单的 `animate*AsState`（颜色/尺寸渐变）、`AnimatedVisibility`（显示/隐藏动画）入手，再进阶 `AnimatedContent`、`Transition`。
4. **副作用 API**：`LaunchedEffect`、`DisposableEffect`、`rememberCoroutineScope`——理解"组合阶段不能做副作用"背后的原因。
5. **自定义绘制**：`Canvas` + `DrawScope`，像画板一样画任意图形。
6. **性能优化**：重组的范围控制、`@Stable` / `@Immutable` 注解、派生状态 `derivedStateOf`。

**官方资料**（遇到具体组件先查这里）：

- Compose 官方文档：<https://developer.android.com/develop/ui/compose>
- Compose 组件速查（JetBrains）：<https://www.jetbrains.com/help/kotlin-multiplatform-dev/foundation-components.html>
- Material 3 组件目录：<https://m3.material.io/components>

> 最后一句忠告：**学 Compose 最快的方式不是背 API，而是把每个组件都在 `@Preview` 里亲手改一遍。** 改参数、看效果、再改、再看——声明式 UI 的反馈循环极短，这是它给学习者最好的礼物。祝你写得开心！
