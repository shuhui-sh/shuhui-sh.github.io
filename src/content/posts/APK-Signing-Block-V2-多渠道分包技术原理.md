---
title: "APK Signing Block V2 多渠道分包技术原理"
date: 2026-05-06
description: "APK V2签名块位于ZIP内容与Central Directory之间，利用其不参与签名验证的特性，可在不破坏签名的情况下注入渠道信息，实现秒级生成上千渠道包。"
tags: ['Android']
category: "技术"
source: "https://juejin.cn/post/7636666943860113418"
---
## 背景

在 Android 应用分发场景中，同一个 APK 往往需要分发到数十甚至上百个渠道（应用市场、广告平台、推广渠道等）。传统方案是为每个渠道重新签名打包，耗时且效率低下。

业界主流的多渠道分包工具（美团 Walle、腾讯 VasDolly、cpstool 等）都利用了 **APK Signing Block V2** 的结构特性，实现了"一次签名，秒级生成上千渠道包"的能力。

本文将深入分析这一技术的原理，并提供完整的代码实现。

---

## 一、APK 文件结构

APK 本质上是一个 ZIP 文件，但 Android 7.0 (API 24) 引入 V2 签名后，其结构变为：

```
┌─────────────────────────────────────┐
│                                     │
│         ZIP Entry Contents          │  ← 原始 ZIP 数据（classes.dex, resources.arsc, lib/, assets/ 等）
│                                     │
├─────────────────────────────────────┤
│                                     │
│         APK Signing Block           │  ← V2 签名块（Android 7.0+ 引入）
│                                     │
├─────────────────────────────────────┤
│                                     │
│        ZIP Central Directory        │  ← ZIP 中央目录
│                                     │
├─────────────────────────────────────┤
│    End of Central Directory (EOCD)  │  ← ZIP 结束标记
└─────────────────────────────────────┘
```

### 关键洞察

**APK Signing Block 位于 ZIP 内容和 Central Directory 之间**，这是一个 ZIP 规范之外的扩展区域。ZIP 解析器会忽略它，而 Android 系统会专门解析它来验证签名。

---

## 二、APK Signing Block 内部结构

APK Signing Block 的详细结构如下：

```
┌────────────────────────────────────────────────────────────────┐
│  Block Size (8 bytes, little-endian)                           │  ← 块大小（不含此字段本身）
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ID-Value Pairs:                                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Pair Size (8 bytes) = ID(4) + Value.length             │  │
│  │  ID (4 bytes, little-endian)                            │  │
│  │  Value (Pair Size - 4 bytes)                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Pair Size (8 bytes)                                     │  │
│  │  ID (4 bytes)                                            │  │
│  │  Value (Pair Size - 4 bytes)                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ... (更多 ID-Value 对)                                         │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  Block Size (8 bytes, little-endian)                           │  ← 重复块大小（用于反向定位）
├────────────────────────────────────────────────────────────────┤
│  Magic: "APK Sig Block 42" (16 bytes)                          │  ← 魔数标识
└────────────────────────────────────────────────────────────────┘
```

### 已知的 ID 值

| ID (十六进制) | ID (十进制) | 用途 | 来源 |
| --- | --- | --- | --- |
| `0x7109871A` | 1896449818 | APK Signature Scheme V2 Block | Android 官方 |
| `0xF05368C0` | -262969152 | APK Signature Scheme V3 Block | Android 官方 |
| `0x42726577` | 1114793335 | Padding Block（Verity 填充） | Android 官方 |
| `0x6DFF800D` | 1845051405 | Source Stamp V1 | Google Play |
| `0x2B09189E` | 722427038 | Source Stamp V2 | Google Play |
| `0x71777777` | 1903517559 | Walle / VasDolly 渠道信息 | 美团 / 腾讯 |
| `0xFF163163` | -15322781 | cpstool / 头条 渠道信息 | 头条 |
| `0x99666666` | -1721342362 | ByteDance 渠道信息 | 字节跳动 |
| `0x881155FF` | -2012129793 | Tencent GDT 渠道信息 | 腾讯广点通 |

---

## 三、为什么可以在不破坏签名的情况下写入渠道？

### V2 签名验证范围

V2 签名计算摘要时，覆盖的数据范围是：

1. **ZIP Entry Contents**（所有文件内容）
2. **ZIP Central Directory**
3. **End of Central Directory**

**关键点：V2 签名不覆盖 APK Signing Block 中的其他 ID-Value 对！**

Android 源码中的验证逻辑（`ApkSignatureSchemeV2Verifier.java`）：

```
// 验证时只关心 ID = 0x7109871A 的签名块
// 其他 ID 的块被忽略，不参与摘要计算
private static final int APK_SIGNATURE_SCHEME_V2_BLOCK_ID = 0x7109871a;
```

### 多渠道写入原理

```
原始 APK:
┌─────────────────────┐
│   ZIP Contents      │ ─┐
├─────────────────────┤  │
│ ┌─────────────────┐ │  │
│ │ ID: 0x7109871A  │ │  │  签名覆盖范围
│ │ V2 Signature    │ │  │  （不包含 Signing Block 本身）
│ └─────────────────┘ │  │
├─────────────────────┤  │
│  Central Directory  │ ─┤
├─────────────────────┤  │
│       EOCD          │ ─┘
└─────────────────────┘

写入渠道后:
┌─────────────────────┐
│   ZIP Contents      │ ─┐
├─────────────────────┤  │
│ ┌─────────────────┐ │  │
│ │ ID: 0x7109871A  │ │  │  签名覆盖范围（不变）
│ │ V2 Signature    │ │  │
│ └─────────────────┘ │  │
│ ┌─────────────────┐ │  │
│ │ ID: 0xFF163163  │ │  │  ← 新增渠道块（不影响签名）
│ │ "channel_001"   │ │  │
│ └─────────────────┘ │  │
├─────────────────────┤  │
│  Central Directory  │ ─┤  ← 偏移量需要更新
├─────────────────────┤  │
│       EOCD          │ ─┘  ← Central Directory 偏移量需要更新
└─────────────────────┘
```

### 写入步骤

1. **定位 APK Signing Block**：从 EOCD 反向查找魔数 `APK Sig Block 42`
2. **解析现有 ID-Value 对**：保留原有签名块
3. **插入新的 ID-Value 对**：使用自定义 ID 写入渠道信息
4. **重建 APK Signing Block**：更新块大小
5. **更新 EOCD**：修正 Central Directory 的偏移量

---

## 四、业界主流工具对比

### 美团 Walle

- **GitHub**: [github.com/Meituan-Dia…](https://link.juejin.cn?target=https%3A%2F%2Fgithub.com%2FMeituan-Dianping%2Fwalle "https://github.com/Meituan-Dianping/walle")
- **渠道 ID**: `0x71777777`
- **特点**:
  - 支持 JSON 格式存储多个键值对
  - 提供 Gradle 插件，打包时自动生成多渠道
  - 读取时使用 `ChannelReader.getChannel(context)`

### 腾讯 VasDolly

- **GitHub**: [github.com/Tencent/Vas…](https://link.juejin.cn?target=https%3A%2F%2Fgithub.com%2FTencent%2FVasDolly "https://github.com/Tencent/VasDolly")
- **渠道 ID**: `0x71777777`（与 Walle 相同）
- **特点**:
  - 同时支持 V1 和 V2 签名方案
  - V1 方案在 META-INF 目录写入空文件

### cpstool

- **渠道 ID**: `0xFF163163`（十进制 -15322781）
- **特点**:
  - 专为某 SDK 设计
  - 渠道值直接存储为 UTF-8 字符串
  - 集成在 SDK 内部，应用无感知

### 头条 / 字节跳动

- **渠道 ID 1**: `0xFF163163`（与 cpstool 共用）- 存储渠道字符串
- **渠道 ID 2**: `0x99666666` - 存储 JSON 格式的 `hume_channel_id`
- **特点**:
  - 同时使用两个渠道 ID
  - ID 1 存储渠道名如 `example.channel_toutiao_cps_dev`
  - ID 2 存储 JSON 如 `{"hume_channel_id": "sub29931_ydzx3_cpc_dev_"}`

### 对比表

| 工具 | 渠道 ID | 数据格式 | V1 支持 | V2 支持 | V3 支持 |
| --- | --- | --- | --- | --- | --- |
| Walle | 0x71777777 | JSON | ❌ | ✅ | ✅ |
| VasDolly | 0x71777777 | String | ✅ | ✅ | ✅ |
| cpstool | 0xFF163163 | UTF-8 String | ❌ | ✅ | ✅ |
| 头条 | 0xFF163163 + 0x99666666 | String + JSON | ❌ | ✅ | ✅ |
| 腾讯 GDT | 0x881155FF | String | ❌ | ✅ | ✅ |

---

## 五、安全性考量

### 这不是漏洞吗？

Google 在设计 V2 签名时，**有意**允许在 APK Signing Block 中添加自定义 ID-Value 对。原因：

1. **向前兼容**：未来可能引入新的签名方案（如 V3、V4）
2. **扩展性**：允许第三方工具添加元数据
3. **不影响安全性**：渠道信息不参与签名验证，攻击者无法篡改实际代码

### V3 签名的变化

Android 9.0 引入的 V3 签名增加了 **APK Key Rotation** 支持，但同样不覆盖其他 ID-Value 对。多渠道方案依然有效。

---

## 六、实际应用场景

### 场景 1：应用市场分发

```
base.apk (签名一次)
    ├── channel_huawei.apk  (写入渠道: huawei)
    ├── channel_xiaomi.apk  (写入渠道: xiaomi)
    ├── channel_oppo.apk    (写入渠道: oppo)
    └── channel_vivo.apk    (写入渠道: vivo)
```

### 场景 2：广告归因

```
base.apk (签名一次)
    ├── cps_toutiao_001.apk   (头条广告渠道 001)
    ├── cps_toutiao_002.apk   (头条广告渠道 002)
    ├── cps_tencent_001.apk   (腾讯广告渠道 001)
    └── cps_kuaishou_001.apk  (快手广告渠道 001)
```

### 场景 3：一次包渠道透传

在一次包场景中，第三方分包平台（头条、腾讯等）会向壳 APK 注入渠道信息。但 SDK 通过 `context.getPackageCodePath()` 读取渠道时，会被重定向到 assets\_ext.apk。

解决方案：从壳 APK 读取渠道，透传到 assets\_ext.apk。

```
壳 APK (base.apk)
    └── Signing Block
        └── ID: 0xFF163163 = "example.channel_cps_dev"
                    ↓
              读取并透传
                    ↓
assets_ext.apk
    └── Signing Block
        └── ID: 0xFF163163 = "example.channel_cps_dev"
                    ↓
              SDK 读取
                    ↓
            APP_CHANNEL = "example.channel_cps_dev"
```

---

## 七、完整代码实现

以下是经过生产验证的完整 Java 实现代码。

### 7.1 渠道读取器 (ApkChannelReader)

```
package com.example.channel.tools;

import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * APK Signing Block 渠道读取器
 * 
 * 用于读取 APK 中的所有渠道信息，支持多种渠道 ID：
 * - 0xFF163163: cpstool / 头条
 * - 0x99666666: 字节跳动 (ByteDance)
 * - 0x881155FF: 腾讯广点通 (GDT)
 * - 0x71777777: 美团 Walle / VasDolly
 */
public class ApkChannelReader {
    private static final String TAG = "ApkChannelReader";
    
    // V2 签名块魔数
    private static final byte[] APK_SIG_BLOCK_MAGIC = {
        'A', 'P', 'K', ' ', 'S', 'i', 'g', ' ',
        'B', 'l', 'o', 'c', 'k', ' ', '4', '2'
    };
    
    // 已知的渠道 ID
    public static final int ID_CPSTOOL = 0xFF163163;        // cpstool / 头条 (-15322781)
    public static final int ID_BYTEDANCE = 0x99666666;      // 字节跳动 (-1721342362)
    public static final int ID_TENCENT_GDT = 0x881155FF;    // 腾讯广点通 (-2012129793)
    public static final int ID_WALLE = 0x71777777;          // 美团 Walle / VasDolly (1903517559)
    
    // 所有渠道 ID 列表
    public static final int[] ALL_CHANNEL_IDS = {
        ID_CPSTOOL,
        ID_BYTEDANCE,
        ID_TENCENT_GDT,
        ID_WALLE
    };
    
    /**
     * 渠道信息
     */
    public static class ChannelInfo {
        public final int id;
        public final byte[] value;
        public final String valueAsString;
        
        public ChannelInfo(int id, byte[] value) {
            this.id = id;
            this.value = value;
            this.valueAsString = new String(value, StandardCharsets.UTF_8);
        }
        
        @Override
        public String toString() {
            return String.format("ChannelInfo{id=0x%08X, value='%s'}", id, valueAsString);
        }
    }
    
    /**
     * 读取 APK 中的所有渠道信息
     * @param apkFile APK 文件
     * @return 渠道信息列表，如果没有找到返回空列表
     */
    public static List<ChannelInfo> readAllChannels(File apkFile) {
        List<ChannelInfo> channels = new ArrayList<>();
        
        if (apkFile == null || !apkFile.exists()) {
            return channels;
        }
        
        RandomAccessFile raf = null;
        try {
            raf = new RandomAccessFile(apkFile, "r");
            
            // 1. 定位 EOCD
            long eocdOffset = findEocd(raf);
            if (eocdOffset < 0) {
                return channels;
            }
            
            // 2. 读取 Central Directory 偏移
            raf.seek(eocdOffset + 16);
            long cdOffset = readUint32(raf);
            
            // 3. 定位 APK Signing Block
            SigningBlockInfo blockInfo = findSigningBlock(raf, cdOffset);
            if (blockInfo == null) {
                return channels;
            }
            
            // 4. 读取所有 ID-Value 对
            Map<Integer, byte[]> idValues = readIdValuePairs(raf, blockInfo);
            
            // 5. 提取渠道信息
            for (int channelId : ALL_CHANNEL_IDS) {
                byte[] value = idValues.get(channelId);
                if (value != null && value.length > 0) {
                    channels.add(new ChannelInfo(channelId, value));
                }
            }
            
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            if (raf != null) {
                try { raf.close(); } catch (IOException ignored) {}
            }
        }
        
        return channels;
    }
    
    /**
     * 查找 EOCD (End of Central Directory)
     * EOCD 结构: 4字节签名 + 18字节固定数据 + 可变长度注释
     * 签名: 0x06054B50 (小端序为 50 4B 05 06)
     */
    private static long findEocd(RandomAccessFile raf) throws IOException {
        long fileSize = raf.length();
        
        // EOCD 最小 22 字节，最大 22 + 65535 字节（含注释）
        int maxCommentLen = 65535;
        int eocdMinLen = 22;
        int searchLen = Math.min((int) fileSize, eocdMinLen + maxCommentLen);
        long searchStart = fileSize - searchLen;
        
        raf.seek(searchStart);
        byte[] buffer = new byte[searchLen];
        raf.readFully(buffer);
        
        // 从后向前搜索 EOCD 签名 (0x06054B50, 小端序)
        for (int i = buffer.length - eocdMinLen; i >= 0; i--) {
            if (buffer[i] == 0x50 && buffer[i + 1] == 0x4B
                && buffer[i + 2] == 0x05 && buffer[i + 3] == 0x06) {
                return searchStart + i;
            }
        }
        
        return -1;
    }
    
    /**
     * 签名块信息
     */
    private static class SigningBlockInfo {
        long pairsStart;  // ID-Value 对起始位置
        long pairsEnd;    // ID-Value 对结束位置
    }
    
    /**
     * 查找 APK Signing Block
     * 通过魔数 "APK Sig Block 42" 反向定位
     */
    private static SigningBlockInfo findSigningBlock(RandomAccessFile raf, long cdOffset) throws IOException {
        if (cdOffset < 24) {
            return null;
        }
        
        // 读取 magic (位于 cdOffset - 16)
        raf.seek(cdOffset - 16);
        byte[] magic = new byte[16];
        raf.readFully(magic);
        
        if (!arrayEquals(magic, APK_SIG_BLOCK_MAGIC)) {
            return null;
        }
        
        // 读取 end size (位于 cdOffset - 24)
        raf.seek(cdOffset - 24);
        long endSize = readUint64(raf);
        
        // 计算 front size 位置
        // Block 结构: [front_size(8)] [pairs...] [end_size(8)] [magic(16)]
        // endSize = pairs.length + 8 + 16 = pairs.length + 24
        long frontSizePos = cdOffset - 24 - endSize;
        if (frontSizePos < 0) {
            return null;
        }
        
        // 验证 front size 与 end size 一致
        raf.seek(frontSizePos);
        long frontSize = readUint64(raf);
        
        if (frontSize != endSize) {
            return null;
        }
        
        SigningBlockInfo info = new SigningBlockInfo();
        info.pairsStart = frontSizePos + 8;
        info.pairsEnd = cdOffset - 24;
        
        return info;
    }
    
    /**
     * 读取所有 ID-Value 对
     */
    private static Map<Integer, byte[]> readIdValuePairs(RandomAccessFile raf, SigningBlockInfo blockInfo) throws IOException {
        Map<Integer, byte[]> result = new HashMap<>();
        
        long offset = blockInfo.pairsStart;
        long endOffset = blockInfo.pairsEnd;
        
        while (offset + 12 <= endOffset) {  // 最小 pair: 8(size) + 4(id) = 12 bytes
            raf.seek(offset);
            
            // 读取 pair length (8 bytes)
            long pairLength = readUint64(raf);
            
            if (pairLength < 4 || offset + 8 + pairLength > endOffset) {
                break;
            }
            
            // 读取 ID (4 bytes)
            int id = readUint32AsInt(raf);
            
            // 读取 value
            int valueSize = (int) (pairLength - 4);
            byte[] value = new byte[valueSize];
            raf.readFully(value);
            
            result.put(id, value);
            
            // 移动到下一个 pair
            offset += 8 + pairLength;
        }
        
        return result;
    }
    
    // ==================== 工具方法 ====================
    
    private static long readUint32(RandomAccessFile raf) throws IOException {
        byte[] bytes = new byte[4];
        raf.readFully(bytes);
        ByteBuffer buffer = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN);
        return buffer.getInt() & 0xFFFFFFFFL;
    }
    
    private static int readUint32AsInt(RandomAccessFile raf) throws IOException {
        byte[] bytes = new byte[4];
        raf.readFully(bytes);
        ByteBuffer buffer = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN);
        return buffer.getInt();
    }
    
    private static long readUint64(RandomAccessFile raf) throws IOException {
        byte[] bytes = new byte[8];
        raf.readFully(bytes);
        ByteBuffer buffer = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN);
        return buffer.getLong();
    }
    
    private static boolean arrayEquals(byte[] a, byte[] b) {
        if (a.length != b.length) return false;
        for (int i = 0; i < a.length; i++) {
            if (a[i] != b[i]) return false;
        }
        return true;
    }
}
```

### 7.2 渠道注入器 (ApkChannelInjector)

```
package com.example.channel.tools;

import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.charset.StandardCharsets;
import java.util.LinkedList;
import java.util.List;

/**
 * APK 渠道注入器
 * 
 * 技术原理：
 * - 将渠道信息写入 APK Signing Block 的 ID-Value 对中
 * - 使用自定义 ID（如 0xFF163163）
 * - 不影响 APK 签名验证
 * 
 * 支持两种写入模式：
 * 1. Padding 模式：如果 Signing Block 有足够的 Padding 空间，直接占用 Padding
 * 2. 扩展模式：扩展 Signing Block 大小，移动 Central Directory 和 EOCD
 */
public class ApkChannelInjector {
    private static final String TAG = "ApkChannelInjector";
    
    // 默认渠道 ID (cpstool)
    private static final int CUSTOM_CHANNEL_ID = 0xFF163163;
    // Padding 项 ID
    private static final int PADDING_ID = 0x42726577;  // "Brew" = Verity Padding
    // V2 签名块魔数
    private static final String V2_MAGIC = "APK Sig Block 42";
    // 4096 字节对齐
    private static final long ALIGNMENT = 4096L;
    
    /**
     * 向 APK 注入渠道（使用默认 ID 0xFF163163）
     */
    public static boolean inject(File apkFile, String channel) {
        return inject(apkFile, CUSTOM_CHANNEL_ID, channel);
    }
    
    /**
     * 向 APK 注入渠道（指定渠道 ID）
     */
    public static boolean inject(File apkFile, int channelId, String channel) {
        if (channel == null || channel.isEmpty()) {
            return false;
        }
        return inject(apkFile, channelId, channel.getBytes(StandardCharsets.UTF_8));
    }
    
    /**
     * 向 APK 注入渠道（指定渠道 ID 和原始字节值）
     * 
     * @param apkFile   APK 文件（会被原地修改）
     * @param channelId 渠道 ID
     * @param value     渠道值（原始字节）
     * @return true 成功，false 失败
     */
    public static boolean inject(File apkFile, int channelId, byte[] value) {
        if (apkFile == null || !apkFile.exists() || !apkFile.canWrite()) {
            return false;
        }
        if (value == null || value.length == 0) {
            return false;
        }
        
        RandomAccessFile raf = null;
        try {
            raf = new RandomAccessFile(apkFile, "rw");
            
            // 1. 定位并读取 EOCD
            ECDR ecdr = new ECDR(raf);
            if (ecdr.cdOffset <= 0) {
                return false;
            }
            
            // 2. 检查是否有 APK Signing Block（V2 签名）
            long magicPos = ecdr.cdOffset - 16;
            if (magicPos < 0) {
                return false;
            }
            raf.seek(magicPos);
            byte[] magicBytes = new byte[16];
            raf.readFully(magicBytes);
            String magic = new String(magicBytes, StandardCharsets.UTF_8);
            if (!V2_MAGIC.equals(magic)) {
                return false;  // 不是 V2 签名的 APK
            }
            
            // 3. 读取 APK Signing Block 大小
            long blockSizePos = ecdr.cdOffset - 24;
            raf.seek(blockSizePos);
            long blockSize = ByteUtils.readLong(raf);
            
            // 4. 计算 APK Signing Block 起始位置
            long blockStart = ecdr.cdOffset - blockSize - 8;
            if (blockStart < 0) {
                return false;
            }
            
            // 5. 解析 SignatureBlock 结构
            SignatureBlock sigBlock = new SignatureBlock(raf, blockStart);
            
            // 6. 检查是否已有该渠道 ID
            if (sigBlock.hasChannelId(channelId)) {
                return true;  // 已有渠道，视为成功
            }
            
            // 7. 创建新的 ID-Value 对
            IdValue channelItem = new IdValue(channelId, value);
            long addedSize = channelItem.totalSize();
            
            // 8. 处理 padding（保持 4096 字节对齐）
            if (sigBlock.isPadded()) {
                IdValue paddingItem = sigBlock.getPaddingItem();
                if (paddingItem != null && paddingItem.value.length > addedSize) {
                    // Padding 足够，直接占用
                    paddingItem.reduce((int) addedSize);
                    // sizeChanged = 0，总大小不变
                } else {
                    // Padding 不足，需要扩展文件
                    sigBlock.size1 += addedSize;
                    sigBlock.size2 += addedSize;
                    sigBlock.sizeChanged += (int) addedSize;
                }
            } else {
                // 没有 Padding，需要扩展文件
                sigBlock.size1 += addedSize;
                sigBlock.size2 += addedSize;
                sigBlock.sizeChanged += (int) addedSize;
            }
            sigBlock.idValuesList.add(channelItem);
            
            // 9. 更新 EOCD 中的 CD 偏移量
            ecdr.cdOffset += sigBlock.sizeChanged;
            
            // 10. 写入文件
            if (sigBlock.sizeChanged > 0) {
                // 扩展模式：需要移动 CD 和 EOCD
                long originalCdOffset = ecdr.cdOffset - sigBlock.sizeChanged;
                long newFileLength = raf.length() + sigBlock.sizeChanged;
                int ecdrSize = ecdr.contentBytes.length;
                
                // 先写 EOCD 到新位置
                raf.seek(newFileLength - ecdrSize);
                ecdr.write(raf);
                
                // 从后向前移动 CD 内容（避免覆盖未读取的数据）
                long cdSize = raf.length() - originalCdOffset - ecdrSize;
                byte[] buffer = new byte[2 * 1024 * 1024];  // 2MB buffer
                long remaining = cdSize;
                
                while (remaining > 0) {
                    int chunkSize = (int) Math.min(remaining, buffer.length);
                    long chunkSrcEnd = originalCdOffset + remaining;
                    long chunkSrcStart = chunkSrcEnd - chunkSize;
                    long chunkDstStart = chunkSrcStart + sigBlock.sizeChanged;
                    
                    raf.seek(chunkSrcStart);
                    int read = raf.read(buffer, 0, chunkSize);
                    raf.seek(chunkDstStart);
                    raf.write(buffer, 0, read);
                    
                    remaining -= chunkSize;
                }
                
                // 写 SignatureBlock
                raf.seek(blockStart);
                sigBlock.write(raf);
                raf.setLength(newFileLength);
            } else {
                // Padding 模式：直接覆盖写入
                long originalCdOffset = ecdr.cdOffset;
                long cdSize = raf.length() - originalCdOffset - ecdr.contentBytes.length;
                raf.seek(originalCdOffset);
                byte[] cdContent = new byte[(int) cdSize];
                raf.readFully(cdContent);
                
                raf.seek(blockStart);
                sigBlock.write(raf);
                raf.write(cdContent);
                ecdr.write(raf);
            }
            
            return true;
            
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        } finally {
            if (raf != null) {
                try { raf.close(); } catch (IOException ignored) {}
            }
        }
    }
    
    /**
     * 批量注入多个渠道信息
     * 
     * @param targetApk 目标 APK
     * @param channels  渠道信息列表
     * @return 成功注入的渠道数量
     */
    public static int injectAll(File targetApk, List<ApkChannelReader.ChannelInfo> channels) {
        if (targetApk == null || !targetApk.exists() || channels == null || channels.isEmpty()) {
            return 0;
        }
        
        int successCount = 0;
        for (ApkChannelReader.ChannelInfo info : channels) {
            if (inject(targetApk, info.id, info.value)) {
                successCount++;
            }
        }
        
        return successCount;
    }
    
    // ==================== 内部类 ====================
    
    /**
     * End of Central Directory Record
     */
    static class ECDR {
        private static final byte[] EOCD_MAGIC = {0x50, 0x4B, 0x05, 0x06};
        
        byte[] contentBytes;
        int cdOffset;  // Central Directory 偏移量
        
        ECDR(RandomAccessFile raf) throws IOException {
            int ecdrSize = 22;
            raf.seek(raf.length() - ecdrSize);
            contentBytes = new byte[ecdrSize];
            raf.readFully(contentBytes);
            
            if (contentBytes[0] != EOCD_MAGIC[0] || contentBytes[1] != EOCD_MAGIC[1] ||
                contentBytes[2] != EOCD_MAGIC[2] || contentBytes[3] != EOCD_MAGIC[3]) {
                throw new IOException("Invalid EOCD magic");
            }
            
            cdOffset = ByteUtils.byteArrayToInt(contentBytes, 16);
        }
        
        void write(RandomAccessFile raf) throws IOException {
            ByteUtils.intToByteArray(cdOffset, contentBytes, 16);
            raf.write(contentBytes);
        }
    }
    
    /**
     * APK Signing Block 结构
     */
    static class SignatureBlock {
        long size1;
        LinkedList<IdValue> idValuesList = new LinkedList<>();
        long size2;
        byte[] magic = new byte[16];
        int sizeChanged = 0;
        
        SignatureBlock(RandomAccessFile raf, long blockStart) throws IOException {
            raf.seek(blockStart);
            size1 = ByteUtils.readLong(raf);
            
            // 计算 ID-Value 对总大小
            // size1 包含: pairs + size2(8) + magic(16) = pairs + 24
            long remaining = size1 - 24;
            
            while (remaining > 0) {
                IdValue item = new IdValue(raf);
                remaining -= item.totalSize();
                idValuesList.add(item);
            }
            
            size2 = ByteUtils.readLong(raf);
            raf.readFully(magic);
        }
        
        boolean hasChannelId(int channelId) {
            for (IdValue item : idValuesList) {
                if (item.id == channelId) return true;
            }
            return false;
        }
        
        IdValue getPaddingItem() {
            for (IdValue item : idValuesList) {
                if (item.id == PADDING_ID) return item;
            }
            return null;
        }
        
        boolean isPadded() {
            return (size1 + 8) % ALIGNMENT == 0;
        }
        
        void write(RandomAccessFile raf) throws IOException {
            raf.write(ByteUtils.longToByteArray(size1));
            for (IdValue item : idValuesList) {
                item.write(raf);
            }
            raf.write(ByteUtils.longToByteArray(size2));
            raf.write(magic);
        }
    }
    
    /**
     * ID-Value 对结构
     * 格式：size(8 bytes) + id(4 bytes) + value(size-4 bytes)
     */
    static class IdValue {
        long size;  // = 4 + value.length
        int id;
        byte[] value;
        
        // 从文件读取
        IdValue(RandomAccessFile raf) throws IOException {
            size = ByteUtils.readLong(raf);
            id = ByteUtils.readInt(raf);
            value = new byte[(int) (size - 4)];
            raf.readFully(value);
        }
        
        // 创建新的渠道项
        IdValue(int channelId, byte[] rawValue) {
            value = rawValue;
            size = value.length + 4;
            id = channelId;
        }
        
        long totalSize() {
            return size + 8;  // size字段(8) + id(4) + value(size-4) = size + 8
        }
        
        void reduce(int delta) {
            int newValueLen = value.length - delta;
            if (newValueLen <= 0) {
                throw new IllegalStateException("Padding too small");
            }
            byte[] newValue = new byte[newValueLen];
            System.arraycopy(value, 0, newValue, 0, newValueLen);
            size -= delta;
            value = newValue;
        }
        
        void write(RandomAccessFile raf) throws IOException {
            raf.write(ByteUtils.longToByteArray(size));
            raf.write(ByteUtils.intToByteArray(id));
            raf.write(value);
        }
    }
    
    /**
     * 字节序转换工具（Little Endian）
     */
    static class ByteUtils {
        static long readLong(RandomAccessFile raf) throws IOException {
            byte[] bytes = new byte[8];
            raf.readFully(bytes);
            return (bytes[0] & 0xFFL) | ((bytes[1] & 0xFFL) << 8)
                 | ((bytes[2] & 0xFFL) << 16) | ((bytes[3] & 0xFFL) << 24)
                 | ((bytes[4] & 0xFFL) << 32) | ((bytes[5] & 0xFFL) << 40)
                 | ((bytes[6] & 0xFFL) << 48) | ((bytes[7] & 0xFFL) << 56);
        }
        
        static int readInt(RandomAccessFile raf) throws IOException {
            byte[] bytes = new byte[4];
            raf.readFully(bytes);
            return byteArrayToInt(bytes, 0);
        }
        
        static int byteArrayToInt(byte[] bytes, int offset) {
            return (bytes[offset] & 0xFF) | ((bytes[offset + 1] & 0xFF) << 8)
                 | ((bytes[offset + 2] & 0xFF) << 16) | ((bytes[offset + 3] & 0xFF) << 24);
        }
        
        static byte[] longToByteArray(long value) {
            return new byte[]{
                (byte) value, (byte) (value >> 8), (byte) (value >> 16), (byte) (value >> 24),
                (byte) (value >> 32), (byte) (value >> 40), (byte) (value >> 48), (byte) (value >> 56)
            };
        }
        
        static byte[] intToByteArray(int value) {
            return new byte[]{
                (byte) value, (byte) (value >> 8), (byte) (value >> 16), (byte) (value >> 24)
            };
        }
        
        static void intToByteArray(int value, byte[] dest, int offset) {
            dest[offset] = (byte) value;
            dest[offset + 1] = (byte) (value >> 8);
            dest[offset + 2] = (byte) (value >> 16);
            dest[offset + 3] = (byte) (value >> 24);
        }
    }
}
```

### 7.3 渠道透传调用示例

```
/**
 * 注入渠道到 assets_ext.apk
 * 
 * 渠道透传策略：
 * 1. 优先从壳 APK 的 Signing Block 读取所有渠道信息
 * 2. 将读取到的渠道信息按原始 ID 透传到 assets_ext.apk
 * 3. 如果壳 APK 没有渠道信息，则使用配置的默认渠道
 */
private static void injectChannelToAssetsExt(Context context, File assetsExtApk) {
    if (!assetsExtApk.exists()) {
        return;
    }

    // 1. 获取壳 APK 路径
    File shellApk = new File(context.getApplicationInfo().sourceDir);

    // 2. 从壳 APK 读取所有渠道信息
    List<ApkChannelReader.ChannelInfo> channels = ApkChannelReader.readAllChannels(shellApk);

    if (channels != null && !channels.isEmpty()) {
        // 3a. 透传壳 APK 的渠道到 assets_ext.apk
        int injected = ApkChannelInjector.injectAll(assetsExtApk, channels);
        Log.d(TAG, "Injected " + injected + "/" + channels.size() + " channels");
    } else {
        // 3b. 回退：使用默认渠道
        String defaultChannel = getDefaultChannel();
        if (defaultChannel != null && !defaultChannel.isEmpty()) {
            ApkChannelInjector.inject(assetsExtApk, defaultChannel);
        }
    }
}
```

---

## 八、查看 APK 渠道信息工具

本项目提供了一个 Java 工具 `ApkSigningBlockViewer`，可以查看任意 APK 的 APK Signing Block 内容。

### 使用

```
# 查看 APK 的 Signing Block 信息
java -cp build/classes com.example.channel.tools.ApkSigningBlockViewer <apk_path>

# 使用 cpstool.jar 读取渠道
java -jar cpstool.jar -get <apk_path>
```

### 示例输出

```
===================================================================
              APK Signing Block Viewer                             
===================================================================

APK File: test_channel.apk
File Size: 67,015,830 bytes (63.91 MB)

-------------------------------------------------------------------
              ID-Value Pairs (Total: 4)
-------------------------------------------------------------------

+-- #1 ---------------------------------------------------------------+
|  ID: 0x7109871A (1896449818)
|  Name: APK Signature Scheme V2
|  Size: 1,669 bytes
+---------------------------------------------------------------------+

+-- #2 ---------------------------------------------------------------+
|  ID: 0xF05368C0 (-262969152)
|  Name: APK Signature Scheme V3
|  Size: 1,685 bytes
+---------------------------------------------------------------------+

+-- #3 ---------------------------------------------------------------+
|  ID: 0xFF163163 (-15322781)
|  Name: cpstool / Toutiao Channel
|  Size: 44 bytes
|  Channel: "example.channel_toutiao_cps_dev"
+---------------------------------------------------------------------+

+-- #4 ---------------------------------------------------------------+
|  ID: 0x99666666 (-1721342362)
|  Name: ByteDance Channel
|  Size: 46 bytes
|  Channel: {"hume_channel_id": "sub29931_ydzx3_cpc_dev_"}
+---------------------------------------------------------------------+
```

---

## 九、测试验证

### 验证流程

1. 从头条分包的 APK 读取渠道信息
2. 复制一个目标 APK 作为测试目标
3. 向目标 APK 写入读取到的渠道信息
4. 使用 cpstool.jar 验证写入结果
5. 验证 APK 签名是否有效

### 验证结果

```
[1] 读取源 APK 渠道: 5ec33f28e52611f0a12b3436ac12004c.apk
    Found 2 channel(s):
    - ID: 0xFF163163 (cpstool/Toutiao): example.channel_toutiao_cps_dev
    - ID: 0x99666666 (ByteDance): {"hume_channel_id": "sub29931_ydzx3_cpc_dev_"}

[2] 注入渠道到目标 APK
    Injected ID 0xFF163163: success
    Injected ID 0x99666666: success

[3] cpstool.jar 验证
    $ java -jar cpstool.jar -get test_output.apk
    mark:CHANNEL
    v2
    example.channel_toutiao_cps_dev
    consume: 2ms

[4] 结论: 测试通过 ✓
```

### 真机日志验证

```
injectChannelToAssetsExt: shellApk=/data/app/.../base.apk
ApkChannelReader readAllChannels: found channel id=0xff163163, value=example.channel_cps_dev
injectChannelToAssetsExt: found 1 channels in shell APK
ApkChannelInjector inject(id) success: channelId=0xff163163, value=example.channel_cps_dev
ApkChannelInjector injectAll: 1/1 channels injected
injectChannelToAssetsExt: injected 1/1 channels
```

---

## 十、注意事项

1. **V1 签名兼容**：如果 APK 同时使用 V1 签名，需要确保不修改 META-INF 目录
2. **Zip64 格式**：超大 APK 可能使用 Zip64 格式，EOCD 定位逻辑需要适配
3. **块大小对齐**：某些工具要求 APK Signing Block 按特定字节对齐（常见 4096 字节）
4. **重复 ID 处理**：同一 ID 不应重复写入，代码已做去重检查
5. **Verity Padding**：写入时优先占用 Padding 空间，保持文件大小不变

---

## 参考资料

- [Android APK Signature Scheme v2](https://link.juejin.cn?target=https%3A%2F%2Fsource.android.com%2Fdocs%2Fsecurity%2Ffeatures%2Fapksigning%2Fv2 "https://source.android.com/docs/security/features/apksigning/v2")
- [美团 Walle 原理分析](https://link.juejin.cn?target=https%3A%2F%2Ftech.meituan.com%2F2017%2F01%2F13%2Fandroid-apk-v2-signature-scheme.html "https://tech.meituan.com/2017/01/13/android-apk-v2-signature-scheme.html")
- [APK Signature Scheme v3](https://link.juejin.cn?target=https%3A%2F%2Fsource.android.com%2Fdocs%2Fsecurity%2Ffeatures%2Fapksigning%2Fv3 "https://source.android.com/docs/security/features/apksigning/v3")
- [腾讯 VasDolly](https://link.juejin.cn?target=https%3A%2F%2Fgithub.com%2FTencent%2FVasDolly "https://github.com/Tencent/VasDolly")
