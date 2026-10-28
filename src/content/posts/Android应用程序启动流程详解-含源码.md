---
title: "Android应用程序启动流程详解（含源码）"
date: 2026-04-02
description: "Android应用程序启动流程是理解壳程序加载被保护程序的核心知识。 Android应用程序启动流程是理解壳程序加载被保护程序的核心知识。"
tags: ['Android']
category: "技术"
---
> 作者：见前行
> 发布于：2025-07-25
> 原文链接：https://juejin.cn/post/7530911563831296010

Android应用程序启动流程是理解壳程序加载被保护程序的核心知识。

---

## 概述

Android应用程序启动流程是理解壳程序加载被保护程序的核心知识。该流程涉及4个关键进程的协同工作：

- **Launcher进程**：桌面启动器进程
- **Zygote进程**：负责创建新的应用程序进程
- **SystemServer进程**：包含AMS（ActivityManagerService）
- **应用程序进程**：目标应用程序运行的进程

整个启动流程可以分为三个核心部分：

1. 创建应用程序进程
2. 创建Application
3. 启动根Activity

---

## 总体启动流程时序图

```
用户点击应用图标
    ↓
Launcher进程 → startActivity请求(Binder) → AMS
    ↓
AMS判断应用程序进程是否存在
    ↓
    进程不存在？
    ↓ 是
AMS → 请求创建进程(Socket) → Zygote
    ↓
Zygote → forkAndSpecialize创建进程 → 应用程序进程
    ↓
应用程序进程 → 通知进程创建完成 → AMS
    ↓
AMS → scheduleLaunchActivity(Binder) → 应用程序进程
    ↓
应用程序进程：处理LAUNCH_ACTIVITY消息 → 创建Activity实例 → 调用Activity.onCreate → 应用程序启动完成
```

---

## 一、创建应用程序进程

### 流程概述

当用户点击应用图标时，首先需要确保目标应用程序进程存在。如果进程不存在，系统会通过AMS向Zygote发送请求创建新的应用程序进程。

### 关键源码示例

#### 1. ActivityStackSupervisor.startSpecificActivityLocked

```java
// frameworks/base/services/core/java/com/android/server/am/ActivityStackSupervisor.java
void startSpecificActivityLocked(ActivityRecord r, boolean andResume, boolean checkConfig) {
    // 获取应用程序进程信息
    ProcessRecord app = mService.getProcessRecordLocked(r.processName,
            r.info.applicationInfo.uid, true);

    // 判断进程是否存在且已启动
    if (app != null && app.thread != null) {
        try {
            // 进程已存在，直接启动Activity
            realStartActivityLocked(r, app, andResume, checkConfig);
            return;
        } catch (RemoteException e) {
            // 进程存在但无法通信，需要重新创建
        }
    }

    // 进程不存在，需要创建新进程
    mService.startProcessLocked(r.processName, r.info.applicationInfo, true, 0,
            "activity", r.intent.getComponent(), false, false, true);
}
```

#### 2. Zygote创建应用程序进程流程

```
AMS → Socket请求创建进程 → Zygote
    ↓
ZygoteConnection.handleChildProc → 配置子进程初始环境
    ↓
ZygoteInit.zygoteInit初始化 → 新应用程序进程
    ↓
nativeZygoteInit启动Binder线程池
    ↓
RuntimeInit.applicationInit
    ↓
invokeStaticMain抛出异常
    ↓
异常处理清空堆栈帧
    ↓
ActivityThread.main启动主线程
```

#### 3. RuntimeInit.zygoteInit

```java
// frameworks/base/core/java/com/android/internal/os/RuntimeInit.java
public static final void zygoteInit(int targetSdkVersion, String[] argv,
        ClassLoader classLoader) throws MethodAndArgsCaller {
    // 重定向日志输出
    redirectLogStreams();

    // 通用初始化
    commonInit();

    // 启动Binder线程池，使进程可以进行Binder通信
    nativeZygoteInit();

    // 应用程序初始化
    applicationInit(targetSdkVersion, argv, classLoader);
}
```

#### 4. RuntimeInit.applicationInit

```java
// frameworks/base/core/java/com/android/internal/os/RuntimeInit.java
private static void applicationInit(int targetSdkVersion, String[] argv,
        ClassLoader classLoader) throws MethodAndArgsCaller {
    // 设置虚拟机的targetSdkVersion
    VMRuntime.getRuntime().setTargetSdkVersion(targetSdkVersion);

    // 解析参数，获取要启动的类名和方法参数
    final Arguments args = new Arguments(argv);

    // 调用指定类的main方法
    invokeStaticMain(args.startClass, args.startArgs, classLoader);
}

private static void invokeStaticMain(String className, String[] argv,
        ClassLoader classLoader) throws MethodAndArgsCaller {
    Class<?> cl;

    // 加载目标类（通常是android.app.ActivityThread）
    cl = Class.forName(className, true, classLoader);

    // 获取main方法
    Method m = cl.getMethod("main", new Class[] { String[].class });

    // 通过抛出异常的方式清空堆栈帧
    throw new MethodAndArgsCaller(m, argv);
}
```

### 关键步骤说明

1. **ZygoteConnection.handleChildProc**：配置子进程的初始环境
2. **ZygoteInit.nativeZygoteInit**：启动Binder线程池，使进程可以进行Binder通信
3. **RuntimeInit.applicationInit**：初始化运行时环境
4. **异常处理机制**：通过Zygote.MethodAndArgsCaller异常清空设置过程中的堆栈帧
5. **ActivityThread.main**：启动应用程序主线程管理类

---

## 二、创建Application

### 流程概述

应用程序进程创建后，需要创建Application实例。Application是应用程序的描述类，每个应用程序只有一个全局单例。

### Application创建流程

```
ActivityThread.main方法初始化
    ↓
创建并启动主线程消息循环 (Looper)
    ↓
attach方法 → 通知AMS附加ApplicationThread
    ↓
AMS → BIND_APPLICATION消息(IApplicationThread)
    ↓
handleMessage处理消息
    ↓
handleBindApplication
    ↓
1. getPackageInfoNoCheck创建LoadedApk
    ↓
2. ContextImpl.createAppContext创建上下文
    ↓
3. makeApplication创建Application
    ↓
Application.attachBaseContext方法
    ↓
4. Instrumentation.callApplicationOnCreate
    ↓
Application.onCreate方法
```

### 关键源码示例

#### 1. ActivityThread.main

```java
// frameworks/base/core/java/android/app/ActivityThread.java
public static void main(String[] args) {
    // 准备主线程的Looper
    Looper.prepareMainLooper();

    // 创建ActivityThread实例
    ActivityThread thread = new ActivityThread();

    // 执行attach方法，建立与AMS的通信
    thread.attach(false);

    // 获取主线程Handler
    if (sMainThreadHandler == null) {
        sMainThreadHandler = thread.getHandler();
    }

    // 启动消息循环
    Looper.loop();

    throw new RuntimeException("Main thread loop unexpectedly exited");
}
```

#### 2. LoadedApk.makeApplication

```java
// frameworks/base/core/java/android/app/LoadedApk.java
public Application makeApplication(boolean forceDefaultAppClass,
        Instrumentation instrumentation) {
    // 如果Application已经创建，直接返回
    if (mApplication != null) {
        return mApplication;
    }

    Application app = null;

    // 获取Application类名
    String appClass = mApplicationInfo.className;
    if (forceDefaultAppClass || (appClass == null)) {
        appClass = "android.app.Application";
    }

    try {
        // 获取ClassLoader
        java.lang.ClassLoader cl = getClassLoader();

        // 创建Application的Context
        ContextImpl appContext = ContextImpl.createAppContext(mActivityThread, this);

        // 创建Application实例
        app = mActivityThread.mInstrumentation.newApplication(
                cl, appClass, appContext);

        // 设置外部Context
        appContext.setOuterContext(app);
    } catch (Exception e) {
        throw new RuntimeException(
            "Unable to instantiate application " + appClass
            + ": " + e.toString(), e);
    }

    // 添加到Application列表
    mActivityThread.mAllApplications.add(app);
    mApplication = app;

    if (instrumentation != null) {
        // 调用Application.onCreate
        instrumentation.callApplicationOnCreate(app);
    }

    return app;
}
```

#### 3. Instrumentation.callApplicationOnCreate

```java
// frameworks/base/core/java/android/app/Instrumentation.java
public void callApplicationOnCreate(Application app) {
    app.onCreate();
}

public Application newApplication(ClassLoader cl, String className, Context context)
        throws InstantiationException, IllegalAccessException,
        ClassNotFoundException {
    return newApplication(cl.loadClass(className), context);
}

static public Application newApplication(Class<?> clazz, Context context)
        throws InstantiationException, IllegalAccessException,
        ClassNotFoundException {
    // 创建Application实例
    Application app = (Application)clazz.newInstance();
    // 绑定Context
    app.attach(context);
    return app;
}
```

---

## 三、启动根Activity

### 流程概述

Application创建完成后，系统开始启动根Activity。这个过程通过ApplicationThread的消息机制实现。

### 启动根Activity流程

```
AMS → ActivityStackSupervisor.realStartActivityLocked
    ↓
ApplicationThread.scheduleLaunchActivity
    ↓
sendMessage发送LAUNCH_ACTIVITY消息
    ↓
H类handleMessage接收消息
    ↓
handleLaunchActivity
    ↓
performLaunchActivity
    ↓
1. 获取ActivityInfo
    ↓
2. 获取LoadedApk
    ↓
3. 创建Activity上下文环境
    ↓
4. 通过ClassLoader创建Activity实例
    ↓
5. makeApplication(返回已存在的Application)
    ↓
6. Activity.attach初始化
    ↓
7. Instrumentation.callActivityOnCreate
    ↓
Activity.onCreate方法执行
```

### 关键源码示例

#### 1. ActivityThread.performLaunchActivity

```java
// frameworks/base/core/java/android/app/ActivityThread.java
private Activity performLaunchActivity(ActivityClientRecord r, Intent customIntent) {
    // 1. 获取ActivityInfo
    ActivityInfo aInfo = r.activityInfo;
    if (r.packageInfo == null) {
        r.packageInfo = getPackageInfo(aInfo.applicationInfo, r.compatInfo,
                Context.CONTEXT_INCLUDE_CODE);
    }

    // 2. 获取LoadedApk
    LoadedApk packageInfo = r.packageInfo;

    // 3. 创建Activity上下文环境
    ContextImpl appContext = createBaseContextForActivity(r);
    Activity activity = null;
    try {
        // 4. 通过ClassLoader创建Activity实例
        ClassLoader cl = appContext.getClassLoader();
        activity = mInstrumentation.newActivity(
                cl, component.getClassName(), r.intent);
    } catch (Exception e) {
        throw new RuntimeException(
            "Unable to instantiate activity " + component
            + ": " + e.toString(), e);
    }

    try {
        // 5. makeApplication(返回已存在的Application)
        Application app = r.packageInfo.makeApplication(false, mInstrumentation);

        if (activity != null) {
            // 6. Activity.attach初始化
            appContext.setOuterContext(activity);

            activity.attach(appContext, this, getInstrumentation(), r.token,
                    r.ident, app, r.intent, r.activityInfo, title, r.parent,
                    r.embeddedID, r.lastNonConfigurationInstances, config,
                    r.referrer, r.voiceInteractor, window, r.configCallback);

            // 7. Instrumentation.callActivityOnCreate - 调用onCreate
            mInstrumentation.callActivityOnCreate(activity, r.state);

            r.activity = activity;
        }
        r.setState(ON_CREATE);

        mActivities.put(r.token, r);

    } catch (Exception e) {
        throw new RuntimeException(
            "Unable to start activity " + component
            + ": " + e.toString(), e);
    }

    return activity;
}
```

#### 2. Activity.performCreate

```java
// frameworks/base/core/java/android/app/Activity.java
final void performCreate(Bundle icicle) {
    restoreHasCurrentPermissionRequest(icicle);
    // 调用开发者重写的onCreate方法
    onCreate(icicle);
    mActivityTransitionState.readState(icicle);

    performCreateCommon();
}
```

---

## 四、关键类详解

### 4.1 ActivityThread

ActivityThread是Android应用程序的主线程管理类，负责管理应用程序的生命周期和各种组件。

```java
public final class ActivityThread {
    // 应用程序的Application对象
    Application mInitialApplication;

    // 所有创建的Application列表
    final ArrayList<Application> mAllApplications = new ArrayList<Application>();

    // Activity记录映射表
    final ArrayMap<IBinder, ActivityClientRecord> mActivities = new ArrayMap<>();

    // 主线程Handler
    final H mH = new H();

    // 应用程序的Instrumentation
    Instrumentation mInstrumentation;

    // 包信息缓存
    final ArrayMap<String, WeakReference<LoadedApk>> mPackages = new ArrayMap<>();
}
```

### 4.2 Application

Application是应用程序的基类，它的生命周期等同于整个应用程序。

```java
public class Application extends ContextWrapper implements ComponentCallbacks2 {
    private ArrayList<ComponentCallbacks> mComponentCallbacks =
            new ArrayList<ComponentCallbacks>();
    private ArrayList<ActivityLifecycleCallbacks> mActivityLifecycleCallbacks =
            new ArrayList<ActivityLifecycleCallbacks>();

    // 在Application创建时调用，早于onCreate
    protected void attachBaseContext(Context base) {
        super.attachBaseContext(base);
    }

    // Application创建完成后调用
    public void onCreate() {
    }
}
```

### 4.3 LoadedApk

LoadedApk代表一个已加载的APK文件，包含了APK的所有信息。

```java
public final class LoadedApk {
    // ActivityThread实例
    private final ActivityThread mActivityThread;

    // 应用信息
    private ApplicationInfo mApplicationInfo;

    // 包名
    final String mPackageName;

    // 类加载器
    private ClassLoader mClassLoader;

    // Application实例
    private Application mApplication;

    // 创建ClassLoader
    public ClassLoader getClassLoader() {
        synchronized (this) {
            if (mClassLoader == null) {
                createOrUpdateClassLoaderLocked(null);
            }
            return mClassLoader;
        }
    }
}
```

---

## 五、壳程序利用的关键点

基于以上分析，壳程序主要利用以下关键点：

1. **Application替换时机**：在Application.attachBaseContext中进行壳程序初始化
2. **ClassLoader替换**：在LoadedApk中替换ClassLoader以加载加密的dex
3. **Activity加载拦截**：通过替换Instrumentation来控制Activity的创建过程
4. **进程初始化控制**：在ActivityThread.main早期阶段进行必要的初始化

理解这些机制是实现加壳和脱壳的基础，壳程序通过在这些关键节点插入自己的逻辑，实现对被保护程序的加载和运行控制。
