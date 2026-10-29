---
title: "快速Dump应用运行时内存"
date: 2022-12-04
description: "windows的cmd环境下，使用toybox ulimit命令快速进行对应用进行运行时内存core_dump。"
tags: []
category: "技术"
source: "https://juejin.cn/post/7173319078667354120"
---
# 一、前提条件

root环境，可以是模拟器或者root的手机

# 二、执行命令core\_dump命令

1、windows的cmd命令窗口下

adb 先连接上设备

然后执行adb shell连接进入设备的命令窗口

```
adb shell
```

再执行su获取设备的root的权限执行后续命令

```
su
```

然后先后执行

```
toybox ulimit -P $(pidof 应用包名) -c unlimited

sysctl kernel.core_pattern="data/data/应用包名/files/core.%p.%t"

kill -SIGXCPU $(pidof 应用包名)
```

其中**应用包名**替换为需要dump的应用包名，执行完最后一条命令后，则会在`data/data/应用包名/files/`目录下生成名为：`core.xxxx.xxxxxxx` 的core\_dump内存文件。

查看core文件，使用cd 命令到目录下

```
cd data/data/应用包名/files/
```

使用ls命令列出当前目录下的文件

```
ls
```

为了能在windows使用adb pull把文件拉到电脑中，需要先赋予文件的读写权限，使用chmod 777命令

```
chmod 777 要pull出来的文件（这里是core.xxxx.xxxxxxx文件）
```

在当前命令行下，先后执行2个exit命令回到windows的cmd环境

```
exit

exit
```

最后执行adb pull把core文件提取到电脑端D盘的files目录下

```
adb pull data/data/应用包名/files/core.xxxx.xxxxxxx D:\Files
```

# 三、使用010editor可以搜索并分析该应用的内存

则不在本文讨论范围内。

# 四、后记

由此可见，Android即使是运行时的内存都能很轻易地被dump出来，所以我们放在内存中的数据是不是要稍微考虑安全方面的情况？至少核心敏感内容千万不要明文。
