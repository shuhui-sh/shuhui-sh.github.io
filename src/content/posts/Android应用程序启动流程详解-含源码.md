---
title: "Android应用程序启动流程详解（含源码）"
date: 2025-07-25
description: "Android应用程序启动流程详解（含源码） 概述 Android应用程序启动流程是理解壳程序加载被保护程序的核心知识。"
tags: []
category: "技术"
source: "https://juejin.cn/post/7530911563831296010"
---
## Android应用程序启动流程详解（含源码）

### 概述

Android应用程序启动流程是理解壳程序加载被保护程序的核心知识。该流程涉及4个关键进程的协同工作：

- **Launcher进程**：桌面启动器进程
- **Zygote进程**：负责创建新的应用程序进程
- **SystemServer进程**：包含AMS（ActivityManagerService）
- **应用程序进程**：目标应用程序运行的进程

整个启动流程可以分为三个核心部分：

1. 创建应用程序进程
2. 创建Application
3. 启动根Activity

### 总体启动流程时序图

```
sequenceDiagram
    participant User as 用户
    participant Launcher as Launcher进程
    participant AMS as AMS(SystemServer进程)
    participant Zygote as Zygote进程
    participant App as 应用程序进程
    
    User->>Launcher: 点击应用图标
    Launcher->>AMS: startActivity请求(Binder)
    AMS->>AMS: 判断应用程序进程是否存在
    
    alt 进程不存在
        AMS->>Zygote: 请求创建进程(Socket)
        Zygote->>Zygote: forkAndSpecialize创建进程
        Zygote->>App: 初始化应用程序进程
        App->>AMS: 通知进程创建完成
    end
    
    AMS->>App: scheduleLaunchActivity(Binder)
    App->>App: 处理LAUNCH_ACTIVITY消息
    App->>App: 创建Activity实例
    App->>App: 调用Activity.onCreate
    App->>User: 应用程序启动完成
```

### 一、创建应用程序进程

#### 流程概述

当用户点击应用图标时，首先需要确保目标应用程序进程存在。如果进程不存在，系统会通过AMS向Zygote发送请求创建新的应用程序进程。

#### AMS向Zygote发送请求流程

```
sequenceDiagram
    participant Launcher as Launcher
    participant AMS as ActivityManagerService（SystemServer进程）
    participant Zygote as Zygote进程
    
    Launcher->>Launcher: onClick触发
    Launcher->>AMS: ActivityStackSupervisor.startSpecificActivityLocked
    AMS->>AMS: 检查应用程序进程是否存在
    
    alt 进程不存在
        AMS->>AMS: ActivityManagerProxy.startProcessLocked
        AMS->>Zygote: zygoteSendArgsAndGetResult(Socket通信)
        Zygote->>Zygote: ZygoteInit.main
    end
```

##### 关键源码示例

###### 1. ActivityStackSupervisor.startSpecificActivityLocked

```
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

###### 2. ActivityManagerService.startProcessLocked

```
// frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java
private final void startProcessLocked(ProcessRecord app, String hostingType,
        String hostingNameStr, String abiOverride, String entryPoint, String[] entryPointArgs) {
    // ...省略部分代码...
    
    if (entryPoint == null) entryPoint = "android.app.ActivityThread";
    
    // 准备启动参数
    Process.ProcessStartResult startResult = Process.start(entryPoint,
            app.processName, uid, uid, gids, debugFlags, mountExternal,
            app.info.targetSdkVersion, app.info.seinfo, requiredAbi, instructionSet,
            app.info.dataDir, entryPointArgs);
            
    // Process.start最终会调用ZygoteProcess.startViaZygote
}
```

#### Zygote创建应用程序进程流程

```
sequenceDiagram
    participant AMS as ActivityManagerService（SystemServer进程）
    participant Zygote as Zygote进程
    participant NewApp as 新应用程序进程
    
    AMS->>Zygote: Socket请求创建进程
    Zygote->>Zygote: ZygoteConnection.handleChildProc
    Zygote->>Zygote: 配置子进程初始环境
    Zygote->>NewApp: ZygoteInit.zygoteInit初始化
    NewApp->>NewApp: ZygoteInit.nativeZygoteInit启动Binder线程池
    NewApp->>NewApp: RuntimeInit.applicationInit
    NewApp->>NewApp: invokeStaticMain抛出异常
    NewApp->>NewApp: 异常处理清空堆栈帧
    NewApp->>NewApp: ActivityThread.main启动主线程
```

##### 关键源码示例

###### 1. ZygoteConnection.handleChildProc

```
// frameworks/base/core/java/com/android/internal/os/ZygoteConnection.java
private void handleChildProc(Arguments parsedArgs, FileDescriptor[] descriptors,
        FileDescriptor pipeFd, PrintStream newStderr) throws MethodAndArgsCaller {
    // 关闭Zygote的socket连接
    closeSocket();
    ZygoteInit.closeServerSocket();

    // 设置进程名称
    if (parsedArgs.niceName != null) {
        Process.setArgV0(parsedArgs.niceName);
    }

    // 初始化子进程
    if (parsedArgs.invokeWith != null) {
        // 使用runtime启动
        WrapperInit.execApplication(parsedArgs.invokeWith, ...);
    } else {
        // 正常启动流程
        RuntimeInit.zygoteInit(parsedArgs.targetSdkVersion,
                parsedArgs.remainingArgs, null /* classLoader */);
    }
}
```

###### 2. RuntimeInit.zygoteInit

```
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

// native方法，在app_process中定义
private static final native void nativeZygoteInit();
```

###### 3. RuntimeInit.applicationInit

```
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

// MethodAndArgsCaller异常类
static class MethodAndArgsCaller extends Exception {
    private final Method mMethod;
    private final String[] mArgs;

    public MethodAndArgsCaller(Method method, String[] args) {
        mMethod = method;
        mArgs = args;
    }

    public void run() {
        try {
            // 调用ActivityThread.main方法
            mMethod.invoke(null, new Object[] { mArgs });
        } catch (Exception ex) {
            throw new RuntimeException(ex);
        }
    }
}
```

#### 关键步骤说明

1. **ZygoteConnection.handleChildProc**：配置子进程的初始环境
2. **ZygoteInit.nativeZygoteInit**：启动Binder线程池，使进程可以进行Binder通信
3. **RuntimeInit.applicationInit**：初始化运行时环境
4. **异常处理机制**：通过Zygote.MethodAndArgsCaller异常清空设置过程中的堆栈帧
5. **ActivityThread.main**：启动应用程序主线程管理类

### 二、创建Application

#### 流程概述

应用程序进程创建后，需要创建Application实例。Application是应用程序的描述类，每个应用程序只有一个全局单例。

#### Application创建流程时序图

```
sequenceDiagram
    participant ActivityThread as ActivityThread
    participant AMS as AMS
    participant Looper as 主线程Looper
    participant LoadedApk as LoadedApk
    participant Application as Application
    
    ActivityThread->>ActivityThread: main方法初始化
    ActivityThread->>Looper: 创建并启动主线程消息循环
    ActivityThread->>ActivityThread: attach方法
    ActivityThread->>AMS: 通知AMS附加ApplicationThread
    
    AMS->>ActivityThread: BIND_APPLICATION消息(IApplicationThread)
    ActivityThread->>ActivityThread: handleMessage处理消息
    ActivityThread->>ActivityThread: handleBindApplication
    
    ActivityThread->>LoadedApk: 1. getPackageInfoNoCheck创建LoadedApk
    ActivityThread->>ActivityThread: 2. ContextImpl.createAppContext创建上下文
    LoadedApk->>Application: 3. makeApplication创建Application
    Application->>Application: attachBaseContext方法
    ActivityThread->>Application: 4. Instrumentation.callApplicationOnCreate
    Application->>Application: onCreate方法
```

#### 关键源码示例

##### 1. ActivityThread.main

```
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

##### 2. ActivityThread.attach

```
// frameworks/base/core/java/android/app/ActivityThread.java
private void attach(boolean system) {
    sCurrentActivityThread = this;
    mSystemThread = system;
    
    if (!system) {
        // 应用程序进程
        ViewRootImpl.addFirstDrawHandler(new Runnable() {
            @Override
            public void run() {
                ensureJitEnabled();
            }
        });
        
        // 获取AMS的代理
        final IActivityManager mgr = ActivityManagerNative.getDefault();
        try {
            // 通知AMS，ApplicationThread已准备好
            mgr.attachApplication(mAppThread);
        } catch (RemoteException ex) {
            throw ex.rethrowFromSystemServer();
        }
        
        // 监听内存变化
        BinderInternal.addGcWatcher(new Runnable() {
            @Override public void run() {
                if (!mSomeActivitiesChanged) {
                    return;
                }
                Runtime runtime = Runtime.getRuntime();
                long dalvikMax = runtime.maxMemory();
                long dalvikUsed = runtime.totalMemory() - runtime.freeMemory();
                if (dalvikUsed > ((3*dalvikMax)/4)) {
                    mSomeActivitiesChanged = false;
                    try {
                        mgr.releaseSomeActivities(mAppThread);
                    } catch (RemoteException e) {
                        throw e.rethrowFromSystemServer();
                    }
                }
            }
        });
    } else {
        // 系统进程的处理逻辑
        // ...
    }
}
```

##### 3. ActivityThread.handleBindApplication

```
// frameworks/base/core/java/android/app/ActivityThread.java
private void handleBindApplication(AppBindData data) {
    // 设置进程名称
    Process.setArgV0(data.processName);
    
    // 设置时区和区域
    TimeZone.setDefault(null);
    LocaleList.setDefault(data.config.getLocales());

    // 设置Debug标志
    mBoundApplication = data;
    mConfiguration = new Configuration(data.config);
    
    // 创建LoadedApk对象
    data.info = getPackageInfoNoCheck(data.appInfo, data.compatInfo);

    // 创建应用程序上下文
    final ContextImpl appContext = ContextImpl.createAppContext(this, data.info);

    // 创建Instrumentation实例
    if (data.instrumentationName != null) {
        // 加载Instrumentation类
        java.lang.ClassLoader cl = appContext.getClassLoader();
        mInstrumentation = (Instrumentation)
            cl.loadClass(data.instrumentationName.getClassName()).newInstance();
    } else {
        mInstrumentation = new Instrumentation();
    }

    try {
        // 创建Application对象
        Application app = data.info.makeApplication(data.restrictedBackupMode, null);
        mInitialApplication = app;

        // 调用Application.onCreate
        if (!data.restrictedBackupMode) {
            List<ProviderInfo> providers = data.providers;
            if (providers != null) {
                installContentProviders(app, providers);
            }
        }
        
        // 调用Application.onCreate()
        mInstrumentation.callApplicationOnCreate(app);
        
    } catch (Exception e) {
        throw new RuntimeException(
            "Exception thrown in onCreate() of "
            + data.instrumentationName + ": " + e.toString(), e);
    }
}
```

#### 关键步骤详解

##### 1. ActivityThread.getPackageInfoNoCheck

```
// frameworks/base/core/java/android/app/ActivityThread.java
public final LoadedApk getPackageInfoNoCheck(ApplicationInfo ai,
        CompatibilityInfo compatInfo) {
    return getPackageInfo(ai, compatInfo, null, false, true, false);
}

private LoadedApk getPackageInfo(ApplicationInfo aInfo, CompatibilityInfo compatInfo,
        ClassLoader baseLoader, boolean securityViolation, boolean includeCode,
        boolean registerPackage) {
    final boolean differentUser = (UserHandle.myUserId() != 
            UserHandle.getUserId(aInfo.uid));
    synchronized (mResourcesManager) {
        WeakReference<LoadedApk> ref;
        if (differentUser) {
            ref = null;
        } else if (includeCode) {
            ref = mPackages.get(aInfo.packageName);
        } else {
            ref = mResourcePackages.get(aInfo.packageName);
        }

        LoadedApk packageInfo = ref != null ? ref.get() : null;
        if (packageInfo == null || (packageInfo.mResources != null
                && !packageInfo.mResources.getAssets().isUpToDate())) {
            // 创建LoadedApk对象
            packageInfo = new LoadedApk(this, aInfo, compatInfo, baseLoader,
                    securityViolation, includeCode &&
                    (aInfo.flags&ApplicationInfo.FLAG_HAS_CODE) != 0, registerPackage);

            if (differentUser) {
                // 不缓存不同用户的包
            } else if (includeCode) {
                // 加入缓存
                mPackages.put(aInfo.packageName,
                        new WeakReference<LoadedApk>(packageInfo));
            } else {
                mResourcePackages.put(aInfo.packageName,
                        new WeakReference<LoadedApk>(packageInfo));
            }
        }
        return packageInfo;
    }
}
```

##### 2. ContextImpl.createAppContext

```
// frameworks/base/core/java/android/app/ContextImpl.java
static ContextImpl createAppContext(ActivityThread mainThread, LoadedApk packageInfo) {
    if (packageInfo == null) throw new IllegalArgumentException("packageInfo");
    return new ContextImpl(null, mainThread,
            packageInfo, null, null, 0, null, null, Display.INVALID_DISPLAY);
}

private ContextImpl(ContextImpl container, ActivityThread mainThread,
        LoadedApk packageInfo, IBinder activityToken, UserHandle user, int flags,
        Display display, Configuration overrideConfiguration, int createDisplayWithId) {
    mOuterContext = this;
    
    mMainThread = mainThread;
    mActivityToken = activityToken;
    mFlags = flags;
    
    if (user == null) {
        user = Process.myUserHandle();
    }
    mUser = user;
    
    mPackageInfo = packageInfo;
    mContentResolver = new ApplicationContentResolver(this, mainThread, user);
    mDisplay = display;
    mOverrideConfiguration = overrideConfiguration;
}
```

##### 3. LoadedApk.makeApplication

```
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
        if (!mPackageName.equals("android")) {
            initializeJavaContextClassLoader();
        }
        
        // 创建Application的Context
        ContextImpl appContext = ContextImpl.createAppContext(mActivityThread, this);
        
        // 创建Application实例
        app = mActivityThread.mInstrumentation.newApplication(
                cl, appClass, appContext);
        
        // 设置外部Context
        appContext.setOuterContext(app);
    } catch (Exception e) {
        if (!mActivityThread.mInstrumentation.onException(app, e)) {
            throw new RuntimeException(
                "Unable to instantiate application " + appClass
                + ": " + e.toString(), e);
        }
    }
    
    // 添加到Application列表
    mActivityThread.mAllApplications.add(app);
    mApplication = app;

    if (instrumentation != null) {
        try {
            // 调用Application.onCreate
            instrumentation.callApplicationOnCreate(app);
        } catch (Exception e) {
            if (!instrumentation.onException(app, e)) {
                throw new RuntimeException(
                    "Unable to create application " + app.getClass().getName()
                    + ": " + e.toString(), e);
            }
        }
    }

    return app;
}
```

##### 4. Instrumentation.callApplicationOnCreate

```
// frameworks/base/core/java/android/app/Instrumentation.java
public void callApplicationOnCreate(Application app) {
    app.onCreate();
}

// Instrumentation.newApplication
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

### 三、启动根Activity

#### 流程概述

Application创建完成后，系统开始启动根Activity。这个过程通过ApplicationThread的消息机制实现。

#### 启动根Activity流程时序图

```
sequenceDiagram
    participant AMS as AMS
    participant ApplicationThread as ApplicationThread
    participant H as H类(消息管理)
    participant ActivityThread as ActivityThread
    participant Activity as Activity实例
    
    AMS->>AMS: ActivityStackSupervisor.realStartActivityLocked
    AMS->>ApplicationThread: scheduleLaunchActivity
    ApplicationThread->>H: sendMessage发送LAUNCH_ACTIVITY消息
    H->>ActivityThread: handleMessage接收消息
    ActivityThread->>ActivityThread: handleLaunchActivity
    ActivityThread->>ActivityThread: performLaunchActivity
    
    ActivityThread->>ActivityThread: 1. 获取ActivityInfo
    ActivityThread->>ActivityThread: 2. 获取LoadedApk
    ActivityThread->>ActivityThread: 3. 创建Activity上下文环境
    ActivityThread->>Activity: 4. 通过ClassLoader创建Activity实例
    ActivityThread->>ActivityThread: 5. makeApplication(返回已存在的Application)
    Activity->>Activity: 6. Activity.attach初始化
    ActivityThread->>Activity: 7. Instrumentation.callActivityOnCreate
    Activity->>Activity: onCreate方法执行
```

#### 关键源码示例

##### 1. ActivityStackSupervisor.realStartActivityLocked

```
// frameworks/base/services/core/java/com/android/server/am/ActivityStackSupervisor.java
final boolean realStartActivityLocked(ActivityRecord r, ProcessRecord app,
        boolean andResume, boolean checkConfig) throws RemoteException {
    
    // 设置Activity所在的进程
    r.app = app;
    app.activities.add(r);
    
    // 更新进程优先级
    mService.updateLruProcessLocked(app, true, null);
    
    try {
        // 通知应用程序进程启动Activity
        app.thread.scheduleLaunchActivity(new Intent(r.intent), r.appToken,
                System.identityHashCode(r), r.info,
                new Configuration(mService.mConfiguration),
                new Configuration(task.mOverrideConfig), r.compat,
                r.launchedFromPackage, task.voiceInteractor, app.repProcState,
                r.icicle, r.persistentState, results, newIntents, !andResume,
                mService.isNextTransitionForward(), profilerInfo);
                
    } catch (RemoteException e) {
        // 远程调用失败处理
    }
    
    return true;
}
```

##### 2. ApplicationThread.scheduleLaunchActivity

```
// frameworks/base/core/java/android/app/ActivityThread.java
private class ApplicationThread extends ApplicationThreadNative {
    public final void scheduleLaunchActivity(Intent intent, IBinder token, int ident,
            ActivityInfo info, Configuration curConfig, Configuration overrideConfig,
            CompatibilityInfo compatInfo, String referrer, IVoiceInteractor voiceInteractor,
            int procState, Bundle state, PersistableBundle persistentState,
            List<ResultInfo> pendingResults, List<ReferrerIntent> pendingNewIntents,
            boolean notResumed, boolean isForward, ProfilerInfo profilerInfo) {

        updateProcessState(procState, false);

        ActivityClientRecord r = new ActivityClientRecord();

        r.token = token;
        r.ident = ident;
        r.intent = intent;
        r.referrer = referrer;
        r.voiceInteractor = voiceInteractor;
        r.activityInfo = info;
        r.compatInfo = compatInfo;
        r.state = state;
        r.persistentState = persistentState;

        r.pendingResults = pendingResults;
        r.pendingIntents = pendingNewIntents;

        r.startsNotResumed = notResumed;
        r.isForward = isForward;

        r.profilerInfo = profilerInfo;

        r.overrideConfig = overrideConfig;
        updatePendingConfiguration(curConfig);

        // 发送LAUNCH_ACTIVITY消息
        sendMessage(H.LAUNCH_ACTIVITY, r);
    }
}
```

##### 3. H类处理消息

```
// frameworks/base/core/java/android/app/ActivityThread.java
private class H extends Handler {
    public static final int LAUNCH_ACTIVITY         = 100;
    
    public void handleMessage(Message msg) {
        switch (msg.what) {
            case LAUNCH_ACTIVITY: {
                final ActivityClientRecord r = (ActivityClientRecord) msg.obj;
                
                r.packageInfo = getPackageInfoNoCheck(
                        r.activityInfo.applicationInfo, r.compatInfo);
                
                // 处理启动Activity
                handleLaunchActivity(r, null, "LAUNCH_ACTIVITY");
            } break;
            // 其他消息处理...
        }
    }
}
```

##### 4. ActivityThread.handleLaunchActivity

```
// frameworks/base/core/java/android/app/ActivityThread.java
private void handleLaunchActivity(ActivityClientRecord r, Intent customIntent,
        String reason) {
    // 确保我们运行在最新的配置下
    handleConfigurationChanged(null, null);

    // 初始化WindowManagerGlobal
    WindowManagerGlobal.initialize();

    // 执行启动Activity
    Activity a = performLaunchActivity(r, customIntent);

    if (a != null) {
        r.createdConfig = new Configuration(mConfiguration);
        Bundle oldState = r.state;
        
        // 处理Resume状态
        handleResumeActivity(r.token, false, r.isForward,
                !r.activity.mFinished && !r.startsNotResumed, r.lastProcessedSeq, reason);

        if (!r.activity.mFinished && r.startsNotResumed) {
            // 特殊情况处理
            performPauseActivityIfNeeded(r, reason);
        }
    } else {
        // 启动失败，通知AMS停止Activity
        try {
            ActivityManagerNative.getDefault()
                .finishActivity(r.token, Activity.RESULT_CANCELED, null,
                        Activity.DONT_FINISH_TASK_WITH_ACTIVITY);
        } catch (RemoteException ex) {
            throw ex.rethrowFromSystemServer();
        }
    }
}
```

##### 5. ActivityThread.performLaunchActivity详细实现

```
// frameworks/base/core/java/android/app/ActivityThread.java
private Activity performLaunchActivity(ActivityClientRecord r, Intent customIntent) {
    // 1. 获取ActivityInfo
    ActivityInfo aInfo = r.activityInfo;
    if (r.packageInfo == null) {
        r.packageInfo = getPackageInfo(aInfo.applicationInfo, r.compatInfo,
                Context.CONTEXT_INCLUDE_CODE);
    }

    // 获取组件名称
    ComponentName component = r.intent.getComponent();
    if (component == null) {
        component = r.intent.resolveActivity(mInitialApplication.getPackageManager());
        r.intent.setComponent(component);
    }

    if (r.activityInfo.targetActivity != null) {
        component = new ComponentName(r.activityInfo.packageName,
                r.activityInfo.targetActivity);
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
        StrictMode.incrementExpectedActivityCount(activity.getClass());
        r.intent.setExtrasClassLoader(cl);
        r.intent.prepareToEnterProcess();
        if (r.state != null) {
            r.state.setClassLoader(cl);
        }
    } catch (Exception e) {
        if (!mInstrumentation.onException(activity, e)) {
            throw new RuntimeException(
                "Unable to instantiate activity " + component
                + ": " + e.toString(), e);
        }
    }

    try {
        // 5. makeApplication(返回已存在的Application)
        Application app = r.packageInfo.makeApplication(false, mInstrumentation);

        if (activity != null) {
            // 创建上下文环境
            CharSequence title = r.activityInfo.loadLabel(appContext.getPackageManager());
            Configuration config = new Configuration(mCompatConfiguration);
            if (r.overrideConfig != null) {
                config.updateFrom(r.overrideConfig);
            }
            
            // 6. Activity.attach初始化
            Window window = null;
            if (r.mPendingRemoveWindow != null && r.mPreserveWindow) {
                window = r.mPendingRemoveWindow;
                r.mPendingRemoveWindow = null;
                r.mPendingRemoveWindowManager = null;
            }
            appContext.setOuterContext(activity);
            
            activity.attach(appContext, this, getInstrumentation(), r.token,
                    r.ident, app, r.intent, r.activityInfo, title, r.parent,
                    r.embeddedID, r.lastNonConfigurationInstances, config,
                    r.referrer, r.voiceInteractor, window, r.configCallback);

            if (customIntent != null) {
                activity.mIntent = customIntent;
            }
            r.lastNonConfigurationInstances = null;
            checkAndBlockForNetworkAccess();
            activity.mStartedActivity = false;
            
            // 设置主题
            int theme = r.activityInfo.getThemeResource();
            if (theme != 0) {
                activity.setTheme(theme);
            }

            activity.mCalled = false;
            
            // 7. Instrumentation.callActivityOnCreate - 调用onCreate
            if (r.isPersistable()) {
                mInstrumentation.callActivityOnCreate(activity, r.state, r.persistentState);
            } else {
                mInstrumentation.callActivityOnCreate(activity, r.state);
            }
            
            if (!activity.mCalled) {
                throw new SuperNotCalledException(
                    "Activity " + r.intent.getComponent().toShortString() +
                    " did not call through to super.onCreate()");
            }
            r.activity = activity;
        }
        r.setState(ON_CREATE);

        mActivities.put(r.token, r);

    } catch (SuperNotCalledException e) {
        throw e;
    } catch (Exception e) {
        if (!mInstrumentation.onException(activity, e)) {
            throw new RuntimeException(
                "Unable to start activity " + component
                + ": " + e.toString(), e);
        }
    }

    return activity;
}
```

##### 6. Activity.attach方法详解

```
// frameworks/base/core/java/android/app/Activity.java
final void attach(Context context, ActivityThread aThread,
        Instrumentation instr, IBinder token, int ident,
        Application application, Intent intent, ActivityInfo info,
        CharSequence title, Activity parent, String id,
        NonConfigurationInstances lastNonConfigurationInstances,
        Configuration config, String referrer, IVoiceInteractor voiceInteractor,
        Window window, ActivityConfigCallback activityConfigCallback) {
    
    // 设置基础上下文
    attachBaseContext(context);

    mFragments.attachHost(null /*parent*/);

    // 创建Window
    mWindow = new PhoneWindow(this, window, activityConfigCallback);
    mWindow.setWindowControllerCallback(this);
    mWindow.setCallback(this);
    mWindow.setOnWindowDismissedCallback(this);
    mWindow.getLayoutInflater().setPrivateFactory(this);
    
    if (info.softInputMode != WindowManager.LayoutParams.SOFT_INPUT_STATE_UNSPECIFIED) {
        mWindow.setSoftInputMode(info.softInputMode);
    }
    if (info.uiOptions != 0) {
        mWindow.setUiOptions(info.uiOptions);
    }
    
    // 设置UI线程
    mUiThread = Thread.currentThread();

    mMainThread = aThread;
    mInstrumentation = instr;
    mToken = token;
    mIdent = ident;
    mApplication = application;
    mIntent = intent;
    mReferrer = referrer;
    mComponent = intent.getComponent();
    mActivityInfo = info;
    mTitle = title;
    mParent = parent;
    mEmbeddedID = id;
    mLastNonConfigurationInstances = lastNonConfigurationInstances;
    if (voiceInteractor != null) {
        if (lastNonConfigurationInstances != null) {
            mVoiceInteractor = lastNonConfigurationInstances.voiceInteractor;
        } else {
            mVoiceInteractor = new VoiceInteractor(voiceInteractor, this, this,
                    Looper.myLooper());
        }
    }

    // 设置WindowManager
    mWindow.setWindowManager(
            (WindowManager)context.getSystemService(Context.WINDOW_SERVICE),
            mToken, mComponent.flattenToString(),
            (info.flags & ActivityInfo.FLAG_HARDWARE_ACCELERATED) != 0);
    
    if (mParent != null) {
        mWindow.setContainer(mParent.getWindow());
    }
    mWindowManager = mWindow.getWindowManager();
    mCurrentConfig = config;

    mWindow.setColorMode(info.colorMode);
}
```

##### 7. Instrumentation.callActivityOnCreate

```
// frameworks/base/core/java/android/app/Instrumentation.java
public void callActivityOnCreate(Activity activity, Bundle icicle) {
    prePerformCreate(activity);
    // 调用Activity的onCreate方法
    activity.performCreate(icicle);
    postPerformCreate(activity);
}

public void callActivityOnCreate(Activity activity, Bundle icicle,
        PersistableBundle persistentState) {
    prePerformCreate(activity);
    // 调用Activity的onCreate方法（带持久化状态）
    activity.performCreate(icicle, persistentState);
    postPerformCreate(activity);
}
```

##### 8. Activity.performCreate

```
// frameworks/base/core/java/android/app/Activity.java
final void performCreate(Bundle icicle) {
    restoreHasCurrentPermissionRequest(icicle);
    // 调用开发者重写的onCreate方法
    onCreate(icicle);
    mActivityTransitionState.readState(icicle);
    
    performCreateCommon();
}

final void performCreate(Bundle icicle, PersistableBundle persistentState) {
    restoreHasCurrentPermissionRequest(icicle);
    // 调用开发者重写的onCreate方法（带持久化状态）
    onCreate(icicle, persistentState);
    mActivityTransitionState.readState(icicle);
    
    performCreateCommon();
}

private void performCreateCommon() {
    mVisibleFromClient = !mWindow.getWindowStyle().getBoolean(
            com.android.internal.R.styleable.Window_windowNoDisplay, false);
    mFragments.dispatchActivityCreated();
    mActivityTransitionState.setEnterActivityOptions(this, getActivityOptions());
}
```

#### 创建Activity上下文环境详解

##### createBaseContextForActivity方法

```
// frameworks/base/core/java/android/app/ActivityThread.java
private ContextImpl createBaseContextForActivity(ActivityClientRecord r) {
    final int displayId;
    try {
        displayId = ActivityManagerNative.getDefault().getActivityDisplayId(r.token);
    } catch (RemoteException e) {
        throw e.rethrowFromSystemServer();
    }

    // 创建Activity的Context
    ContextImpl appContext = ContextImpl.createActivityContext(
            this, r.packageInfo, r.activityInfo, r.token, displayId, r.overrideConfig);

    final DisplayManagerGlobal dm = DisplayManagerGlobal.getInstance();
    
    // 对于分屏或多显示器支持
    String pkgName = SystemProperties.get("debug.second-display.pkg");
    if (pkgName != null && !pkgName.isEmpty()
            && r.packageInfo.mPackageName.contains(pkgName)) {
        for (int id : dm.getDisplayIds()) {
            if (id != Display.DEFAULT_DISPLAY) {
                Display display = dm.getCompatibleDisplay(id, appContext.getResources());
                appContext = (ContextImpl) appContext.createDisplayContext(display);
                break;
            }
        }
    }
    return appContext;
}
```

#### 总结

根Activity的启动过程涉及以下关键步骤：

1. **AMS通知应用进程**：通过ActivityStackSupervisor.realStartActivityLocked方法，AMS调用应用进程的ApplicationThread
2. **消息传递**：ApplicationThread将启动请求封装成ActivityClientRecord，通过Handler机制发送LAUNCH\_ACTIVITY消息
3. **消息处理**：H类接收消息，调用handleLaunchActivity方法
4. **执行启动**：handleLaunchActivity调用performLaunchActivity执行具体的启动逻辑
5. **创建实例**：通过ClassLoader创建Activity实例，设置上下文环境
6. **初始化**：调用Activity.attach方法初始化Window、WindowManager等组件
7. **生命周期回调**：通过Instrumentation调用Activity的onCreate方法

### 四、关键类详解

#### 4.1 ActivityThread

ActivityThread是Android应用程序的主线程管理类，负责管理应用程序的生命周期和各种组件。

```
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

#### 4.2 Application

Application是应用程序的基类，它的生命周期等同于整个应用程序。

```
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

#### 4.3 LoadedApk

LoadedApk代表一个已加载的APK文件，包含了APK的所有信息。

```
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

### 五、壳程序利用的关键点

基于以上分析，壳程序主要利用以下关键点：

1. **Application替换时机**：在Application.attachBaseContext中进行壳程序初始化
2. **ClassLoader替换**：在LoadedApk中替换ClassLoader以加载加密的dex
3. **Activity加载拦截**：通过替换Instrumentation来控制Activity的创建过程
4. **进程初始化控制**：在ActivityThread.main早期阶段进行必要的初始化

理解这些机制是实现加壳和脱壳的基础，壳程序通过在这些关键节点插入自己的逻辑，实现对被保护程序的加载和运行控制。
