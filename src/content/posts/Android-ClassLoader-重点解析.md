---
title: "Android ClassLoader 重点解析"
date: 2025-07-06
description: "主要讲解ClassLoader的机制，以及Android中的ClassLoader体系，以及他们的应用场景。"
tags: ['Android']
category: "技术"
source: "https://juejin.cn/post/7523509642178347018"
---
## Android ClassLoader 重点解析

### ClassLoader 概述

**ClassLoader** 是 Java 和 Android 中负责加载类文件的核心组件，它将字节码文件加载到 JVM/ART 运行时环境中，并转换为可执行的 Class 对象。

#### **核心职责**

- **类加载**：将 `.class` 文件或 `.dex` 文件加载到内存
- **命名空间隔离**：不同 ClassLoader 加载的同名类互不冲突
- **安全控制**：控制类的访问权限和加载范围
- **热更新支持**：动态加载新的类文件

### ClassLoader 核心机制

#### **1. 双亲委托机制**

**委托流程**

类加载请求按以下顺序处理：

- 当前加载器检查是否已加载该类（缓存机制）；
- 未加载则​**​委托父加载器​**​（递归至 Bootstrap）；
- 若所有父加载器均​**​加载失败​**​，才由当前加载器调用 `findClass()` 自行加载。
- 全部失败则抛出 `ClassNotFoundException`。

```
// 代码实现：java.lang.ClassLoader 的 loadClass 方法
protected Class<?> loadClass(String name, boolean resolve) throws ClassNotFoundException {
    synchronized (getClassLoadingLock(name)) {
        Class<?> c = findLoadedClass(name);  // 检查缓存
        if (c == null) {
            try {
                if (parent != null) {
                    c = parent.loadClass(name, false);  // 委托父加载器
                } else {
                    c = findBootstrapClassOrNull(name); // 启动类加载器
                }
            } catch (ClassNotFoundException e) {
                // 父加载器失败，继续尝试自行加载
            }
            if (c == null) {
                c = findClass(name);  // 自行加载
            }
        }
        return c;
    }
}
```

#### **2. 双亲委托机制的优点**

- **避免重复加载**

如果已经加载过Class则无需重复加载，只需要读取加载的Class即可

- **更加安全**

保证无法使用自定义的类替代系统类，并且只有两个类名一致并且被同一个加载器加载的类才会被认为是同一个类

### Android ClassLoader 类图结构

```
classDiagram
    class ClassLoader {
        <<abstract>>
        +Class<?> loadClass(String name)
        +Class<?> findClass(String name)
        +Class<?> defineClass(byte[] b, int off, int len)
        +URL findResource(String name)
        +ClassLoader getParent()
        #Class<?> findLoadedClass(String name)
    }
    
    class SecureClassLoader {
        +ProtectionDomain getProtectionDomain()
        +defineClass(String name, byte[] b, ProtectionDomain pd)
    }
    
    class URLClassLoader {
        -URL[] urls
        +URLClassLoader(URL[] urls)
        +addURL(URL url)
        #Class<?> findClass(String name)
    }
    
    class BaseDexClassLoader {
        <<abstract>>
        -DexPathList pathList
        -File optimizedDirectory
        +BaseDexClassLoader(String dexPath, File optimizedDirectory)
        #Class<?> findClass(String name)
        +String findLibrary(String name)
    }
    
    class PathClassLoader {
        +PathClassLoader(String dexPath, ClassLoader parent)
        +PathClassLoader(String dexPath, String libraryPath, ClassLoader parent)
    }
    
    class DexClassLoader {
        +DexClassLoader(String dexPath, String optimizedDirectory, String libraryPath, ClassLoader parent)
    }
    
    class InMemoryDexClassLoader {
        +InMemoryDexClassLoader(ByteBuffer[] dexBuffers, ClassLoader parent)
        +InMemoryDexClassLoader(ByteBuffer dexBuffer, ClassLoader parent)
    }
    
    class BootClassLoader {
        +getInstance()
        #Class<?> findClass(String name)
    }
    
    class DexPathList {
        -Element[] dexElements
        -NativeLibraryElement[] nativeLibraryPathElements
        +Class findClass(String name, List~Throwable~ suppressed)
        +String findLibrary(String libraryName)
    }
    
    class DexFile {
        -long mCookie
        +DexFile(File file)
        +Class loadClass(String name, ClassLoader loader)
        +Enumeration~String~ entries()
    }

    ClassLoader <|-- SecureClassLoader
    SecureClassLoader <|-- URLClassLoader
    ClassLoader <|-- BaseDexClassLoader
    BaseDexClassLoader <|-- PathClassLoader
    BaseDexClassLoader <|-- DexClassLoader
    BaseDexClassLoader <|-- InMemoryDexClassLoader
    ClassLoader <|-- BootClassLoader
    
    BaseDexClassLoader o-- DexPathList
    DexPathList o-- DexFile
```

#### 各个ClassLoader的作用:

**1.ClassLoader**

抽象类，定义了ClassLoader的主要功能

**2.BootClassLoader**

继承自ClassLoader，用于Android系统启动时预加载常用类

**3.SecureClassLoader**

继承自ClassLoader扩展了类权限方面的功能，加强了安全性

**4.URLClassLoader**

继承自SecureClassLoader，用于通过URL路径加载类和资源

**5.BaseDexClassLoader**

继承自ClassLoader，是抽象类ClassLoader的具体实现类

**6.InMemoryDexClassLoader（Android8.0新增）**

继承自BaseDexClassLoader，用于加载内存中的dex文件

**7.PathClassLoader**

继承自BaseDexClassLoader，用于加载已安装的apk的dex文件

**8.DexClassLoader**

继承自BaseDexClassLoader，用于加载已安装的apk的dex文件,以及从SD卡中加载未安装的apk的dex文件

### Android 部分核心ClassLoader 接口及应用

#### **1. BootClassLoader (引导类加载器)**

- ​**​职责​**​：加载Android框架核心类（如`android.*`、`java.*`），路径为`/system/framework`。
- ​**​特点​**​：由C++/Java实现，是所有ClassLoader的父加载器，应用层无法直接调用

```
/**
 * 系统核心类加载器
 * 负责加载 Android 框架核心类
 */
public class BootClassLoader extends ClassLoader {
    
    private static BootClassLoader instance;
    
    public static synchronized BootClassLoader getInstance() {
        if (instance == null) {
            instance = new BootClassLoader();
        }
        return instance;
    }
    
    @Override
    protected Class<?> findClass(String name) throws ClassNotFoundException {
        // 加载系统核心类：java.*, android.*, dalvik.* 等
        // 这里直接委托给Class.forName的native实现
        return Class.forName(name, false, null);
    }
}
```

#### **2. PathClassLoader (应用类加载器)**

- ​**​职责​**​：加载已安装APK中的`classes.dex`文件（路径为`/data/app/<package>/base.apk`）。
- ​**​特点​**​：继承`BaseDexClassLoader`，是应用默认的类加载器，​**​不支持动态加载外部文件**

```
/**
 * 应用默认类加载器
 * 用于加载应用 APK 中的类和系统 CLASSPATH 中的类
 */
public class PathClassLoader extends BaseDexClassLoader {
    
    /**
     * @param dexPath APK 文件路径
     * @param parent 父类加载器，通常是 BootClassLoader
     */
    public PathClassLoader(String dexPath, ClassLoader parent) {
        super(dexPath, null, null, parent);
    }
    
    /**
     * @param dexPath APK/JAR/DEX 文件路径
     * @param librarySearchPath 本地库搜索路径
     * @param parent 父类加载器
     */
    public PathClassLoader(String dexPath, String librarySearchPath, ClassLoader parent) {
        super(dexPath, null, librarySearchPath, parent);
    }
}

// 使用示例
public class ClassLoaderExample {
    
    public void demonstratePathClassLoader() {
        // 获取当前应用的类加载器
        ClassLoader appClassLoader = getClass().getClassLoader();
        System.out.println("App ClassLoader: " + appClassLoader);
        System.out.println("Parent: " + appClassLoader.getParent());
        
        try {
            // 加载应用中的类
            Class<?> myClass = appClassLoader.loadClass("com.example.MyActivity");
            System.out.println("Loaded class: " + myClass.getName());
        } catch (ClassNotFoundException e) {
            e.printStackTrace();
        }
    }
}
```

#### **3. DexClassLoader (动态类加载器)**

- ​**​职责​**​：从外部路径（如SD卡）加载包含`.dex`的APK/JAR文件。
- ​**​特点​**​：继承`BaseDexClassLoader`，需指定`optimizedDirectory`（优化后的odex输出路径），​**​用于动态加载场景​**​

```
/**
 * 动态 DEX 类加载器
 * 可以加载外部 DEX/JAR/APK 文件中的类
 */
public class DexClassLoader extends BaseDexClassLoader {
    
    /**
     * @param dexPath DEX 文件路径，多个路径用 ":" 分隔
     * @param optimizedDirectory 优化后 DEX 文件存储目录
     * @param librarySearchPath 本地库搜索路径
     * @param parent 父类加载器
     */
    public DexClassLoader(String dexPath, String optimizedDirectory, 
                         String librarySearchPath, ClassLoader parent) {
        super(dexPath, new File(optimizedDirectory), librarySearchPath, parent);
    }
}

// 动态加载示例
public class DynamicClassLoader {
    
    private static final String TAG = "DynamicClassLoader";
    
    /**
     * 动态加载外部 DEX 文件中的类
     */
    public void loadExternalDex() {
        try {
            // 外部 DEX 文件路径
            String dexPath = "/sdcard/external.dex";
            
            // 优化目录（Android 8.0+ 可以为 null）
            String optimizedDir = getContext().getDir("dex", Context.MODE_PRIVATE).getAbsolutePath();
            
            // 创建 DexClassLoader
            DexClassLoader dexClassLoader = new DexClassLoader(
                dexPath,
                optimizedDir,
                null,
                getClass().getClassLoader()
            );
            
            // 加载指定类
            Class<?> externalClass = dexClassLoader.loadClass("com.external.ExternalClass");
            
            // 创建实例并调用方法
            Object instance = externalClass.newInstance();
            Method method = externalClass.getMethod("performAction");
            Object result = method.invoke(instance);
            
            Log.d(TAG, "External class result: " + result);
            
        } catch (Exception e) {
            Log.e(TAG, "Failed to load external dex", e);
        }
    }
    
    /**
     * 加载插件 APK 中的类
     */
    public void loadPluginApk(String apkPath) {
        try {
            // 获取应用私有目录
            File dexOutputDir = getContext().getDir("plugin_dex", Context.MODE_PRIVATE);
            
            // 创建类加载器加载插件 APK
            DexClassLoader pluginClassLoader = new DexClassLoader(
                apkPath,
                dexOutputDir.getAbsolutePath(),
                null,
                getClass().getClassLoader()
            );
            
            // 加载插件中的 Activity
            Class<?> pluginActivityClass = pluginClassLoader.loadClass("com.plugin.PluginActivity");
            
            // 获取插件资源
            AssetManager assetManager = AssetManager.class.newInstance();
            Method addAssetPath = AssetManager.class.getMethod("addAssetPath", String.class);
            addAssetPath.invoke(assetManager, apkPath);
            
            Resources pluginResources = new Resources(
                assetManager,
                getContext().getResources().getDisplayMetrics(),
                getContext().getResources().getConfiguration()
            );
            
            Log.d(TAG, "Plugin loaded successfully");
            
        } catch (Exception e) {
            Log.e(TAG, "Failed to load plugin", e);
        }
    }
}
```

#### **4. InMemoryDexClassLoader (内存类加载器)**

- ​**​职责​**​：直接从内存中的字节数组（`byte[]` 或 `ByteBuffer`）加载 DEX 文件，避免文件落盘，提升安全性和性能。
- ​**​特点​**​：继承`BaseDexClassLoader`，与 `DexClassLoader`、`PathClassLoader` 同属一类加载体系，但加载源为内存而非文件路径，用于热修复、插件化、动态功能模块等场景，允许在应用运行时注入新代码或修复现有逻辑，仅适用于 Android 8.0 及以上系统，低版本需降级为 `DexClassLoader`

```
/**
 * 内存中的 DEX 类加载器 (Android 8.0+)
 * 直接从内存缓冲区加载 DEX 数据
 */
public class InMemoryDexExample {
    
    /**
     * 从内存中加载 DEX 数据
     */
    public void loadFromMemory() {
        try {
            // 读取 DEX 文件到内存
            byte[] dexBytes = readDexFileToBytes("/path/to/classes.dex");
            ByteBuffer dexBuffer = ByteBuffer.wrap(dexBytes);
            
            // 创建内存类加载器
            InMemoryDexClassLoader memoryClassLoader = new InMemoryDexClassLoader(
                dexBuffer,
                getClass().getClassLoader()
            );
            
            // 加载类
            Class<?> memoryClass = memoryClassLoader.loadClass("com.memory.MemoryClass");
            Object instance = memoryClass.newInstance();
            
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
    
    /**
     * 加载多个 DEX 缓冲区
     */
    public void loadMultipleDexBuffers() {
        try {
            ByteBuffer[] dexBuffers = {
                ByteBuffer.wrap(readDexFileToBytes("/path/to/classes1.dex")),
                ByteBuffer.wrap(readDexFileToBytes("/path/to/classes2.dex"))
            };
            
            InMemoryDexClassLoader multiDexLoader = new InMemoryDexClassLoader(
                dexBuffers,
                getClass().getClassLoader()
            );
            
            // 加载不同 DEX 中的类
            Class<?> class1 = multiDexLoader.loadClass("com.dex1.Class1");
            Class<?> class2 = multiDexLoader.loadClass("com.dex2.Class2");
            
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
    
    private byte[] readDexFileToBytes(String filePath) throws IOException {
        File file = new File(filePath);
        FileInputStream fis = new FileInputStream(file);
        byte[] bytes = new byte[(int) file.length()];
        fis.read(bytes);
        fis.close();
        return bytes;
    }
}
```

### 实际应用场景

#### **1. 热修复实现**

```
public class HotFixManager {
    
    private static final String TAG = "HotFixManager";
    
    /**
     * 应用热修复补丁
     */
    public static void applyHotFix(Context context, String patchPath) {
        try {
            // 获取当前应用的 ClassLoader
            ClassLoader appClassLoader = context.getClassLoader();
            
            // 获取 BaseDexClassLoader 的 pathList 字段
            Field pathListField = BaseDexClassLoader.class.getDeclaredField("pathList");
            pathListField.setAccessible(true);
            Object pathList = pathListField.get(appClassLoader);
            
            // 创建补丁 ClassLoader
            File dexOutputDir = context.getDir("hotfix", Context.MODE_PRIVATE);
            DexClassLoader patchClassLoader = new DexClassLoader(
                patchPath,
                dexOutputDir.getAbsolutePath(),
                null,
                appClassLoader
            );
            
            Object patchPathList = pathListField.get(patchClassLoader);
            
            // 合并 dexElements
            mergeDexElements(pathList, patchPathList);
            
            Log.d(TAG, "Hot fix applied successfully");
            
        } catch (Exception e) {
            Log.e(TAG, "Failed to apply hot fix", e);
        }
    }
    
    private static void mergeDexElements(Object originalPathList, Object patchPathList) 
            throws Exception {
        Field dexElementsField = originalPathList.getClass().getDeclaredField("dexElements");
        dexElementsField.setAccessible(true);
        
        Object[] originalElements = (Object[]) dexElementsField.get(originalPathList);
        Object[] patchElements = (Object[]) dexElementsField.get(patchPathList);
        
        // 将补丁元素插入到原始元素前面
        Object[] mergedElements = (Object[]) Array.newInstance(
            originalElements.getClass().getComponentType(),
            originalElements.length + patchElements.length
        );
        
        System.arraycopy(patchElements, 0, mergedElements, 0, patchElements.length);
        System.arraycopy(originalElements, 0, mergedElements, patchElements.length, originalElements.length);
        
        dexElementsField.set(originalPathList, mergedElements);
    }
}
```

#### **2. 插件化框架**

```
public class PluginManager {
    
    private Map<String, PluginInfo> pluginMap = new HashMap<>();
    
    public static class PluginInfo {
        public String packageName;
        public ClassLoader classLoader;
        public Resources resources;
        public AssetManager assetManager;
    }
    
    /**
     * 加载插件
     */
    public boolean loadPlugin(Context context, String pluginPath, String packageName) {
        try {
            // 创建插件类加载器
            File dexOutputDir = context.getDir("plugin_" + packageName, Context.MODE_PRIVATE);
            DexClassLoader pluginClassLoader = new DexClassLoader(
                pluginPath,
                dexOutputDir.getAbsolutePath(),
                null,
                context.getClassLoader()
            );
            
            // 创建插件资源管理器
            AssetManager assetManager = AssetManager.class.newInstance();
            Method addAssetPath = AssetManager.class.getMethod("addAssetPath", String.class);
            addAssetPath.invoke(assetManager, pluginPath);
            
            Resources pluginResources = new Resources(
                assetManager,
                context.getResources().getDisplayMetrics(),
                context.getResources().getConfiguration()
            );
            
            // 保存插件信息
            PluginInfo pluginInfo = new PluginInfo();
            pluginInfo.packageName = packageName;
            pluginInfo.classLoader = pluginClassLoader;
            pluginInfo.resources = pluginResources;
            pluginInfo.assetManager = assetManager;
            
            pluginMap.put(packageName, pluginInfo);
            
            return true;
            
        } catch (Exception e) {
            Log.e("PluginManager", "Failed to load plugin: " + packageName, e);
            return false;
        }
    }
    
    /**
     * 启动插件 Activity
     */
    public void startPluginActivity(Context context, String packageName, String className) {
        PluginInfo pluginInfo = pluginMap.get(packageName);
        if (pluginInfo == null) {
            Log.e("PluginManager", "Plugin not loaded: " + packageName);
            return;
        }
        
        try {
            Class<?> activityClass = pluginInfo.classLoader.loadClass(className);
            
            // 创建代理 Activity 来启动插件 Activity
            Intent intent = new Intent(context, ProxyActivity.class);
            intent.putExtra("plugin_package", packageName);
            intent.putExtra("plugin_class", className);
            context.startActivity(intent);
            
        } catch (ClassNotFoundException e) {
            Log.e("PluginManager", "Plugin class not found: " + className, e);
        }
    }
}
```

#### **3、加固应用场景**

实现Android加固时，壳程序动态加载被保护程序的dex文件主要使用以下3个类加载器:

**1.DexClassLoader 可以加载未安装apk的dex文件**

它是一代加固——整体加固（落地加载）的核心之一

**2.InMemoryDexClassLoader 可以加载内存中的dex文件**

它是二代加固——整体加固（不落地加载）的核心之一

**3.BaseDexClassLoader是ClassLoader的具体实现类**

实际上DexClassLoader，PathClassLoader以及InMemoryDexClassLoader加载类时，均通过委托BaseDexClassLoader实现

### 总结

**Android ClassLoader 核心要点**：

1. **层次结构**：BootClassLoader → PathClassLoader → 自定义 ClassLoader
2. **主要类型**：

   - **PathClassLoader**：应用默认类加载器
   - **DexClassLoader**：动态 DEX 加载器
   - **InMemoryDexClassLoader**：内存 DEX 加载器
3. **关键应用场景**：

   - **热修复**：动态替换有问题的类
   - **插件化**：加载外部功能模块, 包括前2代应用加固
   - **组件化**：模块间类隔离，主要是使用`PathClassLoader`

**重点掌握**：

- 这节主要掌握`DexClassLoader`和`InMemoryDexClassLoader`的使用，这个是后续文章的基础

```
/*  
    参数一: String dexPath, Dex文件路径  
    参数二: String optimizedDirectory, 优化后的dex即Odex目录  
    Android中内存中不会出现上述参数一的Dex文件, 会先优化,然后运行,优化后为.odex文件  
    参数三: String librarySearchPath, lib库搜索路径  
    参数四: ClassLoader parent, 父类加载器  
*/  
public class DexClassLoader extends BaseDexClassLoader {  
public DexClassLoader(String dexPath, String optimizedDirectory, String librarySearchPath, ClassLoader parent) {  
super((String)null, (File)null, (String)null, (ClassLoader)null);  
throw new RuntimeException("Stub!");  
    }  
}
```

```
/*  
    参数一: DEX字节码缓冲区数组 
    参数二: 本地库搜索路径
    参数三: ClassLoader parent, 父类加载器  
*/
public final class InMemoryDexClassLoader extends BaseDexClassLoader {
    public InMemoryDexClassLoader(@NonNull ByteBuffer[] dexBuffers, @Nullable String librarySearchPath, @Nullable ClassLoader parent) {
        super((String)null, (File)null, (String)null, (ClassLoader)null);
        throw new RuntimeException("Stub!");
    }
```
