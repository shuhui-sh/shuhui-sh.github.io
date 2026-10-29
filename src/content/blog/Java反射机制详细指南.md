---
title: "Java反射机制详细指南"
description: "Java反射机制详细指南 详细结算 反射的原理与本质 反射的优缺点分析 反射核心类详解 Class类详解 最后编写反射工具类"
pubDate: "2025-06-07"
tags: ['Android', 'Java']
---
## Java反射机制详细指南

### 目录

1. [反射机制概述](https://link.juejin.cn?target=https%3A%2F%2Fclaude.ai%2Fchat%2F7d77d235-1c47-4a0e-bbf2-0abc06e9ef39%23%25E5%258F%258D%25E5%25B0%2584%25E6%259C%25BA%25E5%2588%25B6%25E6%25A6%2582%25E8%25BF%25B0 "https://claude.ai/chat/7d77d235-1c47-4a0e-bbf2-0abc06e9ef39#%E5%8F%8D%E5%B0%84%E6%9C%BA%E5%88%B6%E6%A6%82%E8%BF%B0")
2. [反射的原理与本质](https://link.juejin.cn?target=https%3A%2F%2Fclaude.ai%2Fchat%2F7d77d235-1c47-4a0e-bbf2-0abc06e9ef39%23%25E5%258F%258D%25E5%25B0%2584%25E7%259A%2584%25E5%258E%259F%25E7%2590%2586%25E4%25B8%258E%25E6%259C%25AC%25E8%25B4%25A8 "https://claude.ai/chat/7d77d235-1c47-4a0e-bbf2-0abc06e9ef39#%E5%8F%8D%E5%B0%84%E7%9A%84%E5%8E%9F%E7%90%86%E4%B8%8E%E6%9C%AC%E8%B4%A8")
3. [反射的优缺点分析](https://link.juejin.cn?target=https%3A%2F%2Fclaude.ai%2Fchat%2F7d77d235-1c47-4a0e-bbf2-0abc06e9ef39%23%25E5%258F%258D%25E5%25B0%2584%25E7%259A%2584%25E4%25BC%2598%25E7%25BC%25BA%25E7%2582%25B9%25E5%2588%2586%25E6%259E%2590 "https://claude.ai/chat/7d77d235-1c47-4a0e-bbf2-0abc06e9ef39#%E5%8F%8D%E5%B0%84%E7%9A%84%E4%BC%98%E7%BC%BA%E7%82%B9%E5%88%86%E6%9E%90")
4. [反射核心类详解](https://link.juejin.cn?target=https%3A%2F%2Fclaude.ai%2Fchat%2F7d77d235-1c47-4a0e-bbf2-0abc06e9ef39%23%25E5%258F%258D%25E5%25B0%2584%25E6%25A0%25B8%25E5%25BF%2583%25E7%25B1%25BB%25E8%25AF%25A6%25E8%25A7%25A3 "https://claude.ai/chat/7d77d235-1c47-4a0e-bbf2-0abc06e9ef39#%E5%8F%8D%E5%B0%84%E6%A0%B8%E5%BF%83%E7%B1%BB%E8%AF%A6%E8%A7%A3")
5. [Class类详解](https://link.juejin.cn?target=https%3A%2F%2Fclaude.ai%2Fchat%2F7d77d235-1c47-4a0e-bbf2-0abc06e9ef39%23class%25E7%25B1%25BB%25E8%25AF%25A6%25E8%25A7%25A3 "https://claude.ai/chat/7d77d235-1c47-4a0e-bbf2-0abc06e9ef39#class%E7%B1%BB%E8%AF%A6%E8%A7%A3")
6. [获取Constructor构造方法](https://link.juejin.cn?target=https%3A%2F%2Fclaude.ai%2Fchat%2F7d77d235-1c47-4a0e-bbf2-0abc06e9ef39%23%25E8%258E%25B7%25E5%258F%2596constructor%25E6%259E%2584%25E9%2580%25A0%25E6%2596%25B9%25E6%25B3%2595 "https://claude.ai/chat/7d77d235-1c47-4a0e-bbf2-0abc06e9ef39#%E8%8E%B7%E5%8F%96constructor%E6%9E%84%E9%80%A0%E6%96%B9%E6%B3%95")
7. [获取Field字段](https://link.juejin.cn?target=https%3A%2F%2Fclaude.ai%2Fchat%2F7d77d235-1c47-4a0e-bbf2-0abc06e9ef39%23%25E8%258E%25B7%25E5%258F%2596field%25E5%25AD%2597%25E6%25AE%25B5 "https://claude.ai/chat/7d77d235-1c47-4a0e-bbf2-0abc06e9ef39#%E8%8E%B7%E5%8F%96field%E5%AD%97%E6%AE%B5")
8. [获取Method方法](https://link.juejin.cn?target=https%3A%2F%2Fclaude.ai%2Fchat%2F7d77d235-1c47-4a0e-bbf2-0abc06e9ef39%23%25E8%258E%25B7%25E5%258F%2596method%25E6%2596%25B9%25E6%25B3%2595 "https://claude.ai/chat/7d77d235-1c47-4a0e-bbf2-0abc06e9ef39#%E8%8E%B7%E5%8F%96method%E6%96%B9%E6%B3%95")
9. [反射创建对象](https://link.juejin.cn?target=https%3A%2F%2Fclaude.ai%2Fchat%2F7d77d235-1c47-4a0e-bbf2-0abc06e9ef39%23%25E5%258F%258D%25E5%25B0%2584%25E5%2588%259B%25E5%25BB%25BA%25E5%25AF%25B9%25E8%25B1%25A1 "https://claude.ai/chat/7d77d235-1c47-4a0e-bbf2-0abc06e9ef39#%E5%8F%8D%E5%B0%84%E5%88%9B%E5%BB%BA%E5%AF%B9%E8%B1%A1")
10. [反射操作属性](https://link.juejin.cn?target=https%3A%2F%2Fclaude.ai%2Fchat%2F7d77d235-1c47-4a0e-bbf2-0abc06e9ef39%23%25E5%258F%258D%25E5%25B0%2584%25E6%2593%258D%25E4%25BD%259C%25E5%25B1%259E%25E6%2580%25A7 "https://claude.ai/chat/7d77d235-1c47-4a0e-bbf2-0abc06e9ef39#%E5%8F%8D%E5%B0%84%E6%93%8D%E4%BD%9C%E5%B1%9E%E6%80%A7")
11. [反射调用方法](https://link.juejin.cn?target=https%3A%2F%2Fclaude.ai%2Fchat%2F7d77d235-1c47-4a0e-bbf2-0abc06e9ef39%23%25E5%258F%258D%25E5%25B0%2584%25E8%25B0%2583%25E7%2594%25A8%25E6%2596%25B9%25E6%25B3%2595 "https://claude.ai/chat/7d77d235-1c47-4a0e-bbf2-0abc06e9ef39#%E5%8F%8D%E5%B0%84%E8%B0%83%E7%94%A8%E6%96%B9%E6%B3%95")
12. [反射工具类封装](https://link.juejin.cn?target=https%3A%2F%2Fclaude.ai%2Fchat%2F7d77d235-1c47-4a0e-bbf2-0abc06e9ef39%23%25E5%258F%258D%25E5%25B0%2584%25E5%25B7%25A5%25E5%2585%25B7%25E7%25B1%25BB%25E5%25B0%2581%25E8%25A3%2585 "https://claude.ai/chat/7d77d235-1c47-4a0e-bbf2-0abc06e9ef39#%E5%8F%8D%E5%B0%84%E5%B7%A5%E5%85%B7%E7%B1%BB%E5%B0%81%E8%A3%85")
13. [反射的实际应用场景](https://link.juejin.cn?target=https%3A%2F%2Fclaude.ai%2Fchat%2F7d77d235-1c47-4a0e-bbf2-0abc06e9ef39%23%25E5%258F%258D%25E5%25B0%2584%25E7%259A%2584%25E5%25AE%259E%25E9%2599%2585%25E5%25BA%2594%25E7%2594%25A8%25E5%259C%25BA%25E6%2599%25AF "https://claude.ai/chat/7d77d235-1c47-4a0e-bbf2-0abc06e9ef39#%E5%8F%8D%E5%B0%84%E7%9A%84%E5%AE%9E%E9%99%85%E5%BA%94%E7%94%A8%E5%9C%BA%E6%99%AF")
14. [性能优化建议](https://link.juejin.cn?target=https%3A%2F%2Fclaude.ai%2Fchat%2F7d77d235-1c47-4a0e-bbf2-0abc06e9ef39%23%25E6%2580%25A7%25E8%2583%25BD%25E4%25BC%2598%25E5%258C%2596%25E5%25BB%25BA%25E8%25AE%25AE "https://claude.ai/chat/7d77d235-1c47-4a0e-bbf2-0abc06e9ef39#%E6%80%A7%E8%83%BD%E4%BC%98%E5%8C%96%E5%BB%BA%E8%AE%AE")

---

### 反射机制概述

#### 什么是反射

Java反射机制是指在程序运行期间，对于任意一个类，都能够知道这个类的所有属性和方法；对于任意一个对象，都能够调用它的任意属性和方法。这种动态获取类信息以及动态调用对象方法的功能称为Java语言的反射机制。

#### 反射的核心思想

反射的核心是**在程序运行时动态加载类并获取类的详细信息**，从而操作类或对象的属性和方法。它允许程序在运行时检查类、接口、字段和方法的信息，而无需在编译时知道它们的名字。

---

### 反射的原理与本质

#### 反射的基本原理

1. **Java反射机制的核心**：在程序运行时动态加载类并获取类的详细信息，从而操作类或对象的属性和方法
2. **本质机制**：JVM获得Class对象之后，再通过Class对象进行反编译，从而获取对象的各种信息
3. **技术背景**：Java属于先编译再运行的语言，程序中对象的类型在编译期就确定下来了

#### 正常类的加载过程

```
1. 执行 Student student = new Student()，向JVM请求创建student实例
2. JVM寻找Student.class文件并加载到内存中
3. JVM创建Student对应的Class对象（一个类只对应一个Class对象）
4. JVM创建student实例
```

**重要概念**：对于同一个类而言，无论有多少个实例，都只对应一个Class对象。

#### Java反射的本质

**反射的本质就是：获取Class对象后，反向访问实例对象**

反射允许程序在运行时：

- 动态加载某些类（这些类之前用不到，所以没有被加载到JVM）
- 动态地创建对象并调用其属性
- 不需要提前在编译期知道运行的对象是谁

---

### 反射的优缺点分析

#### 优点

1. **增强灵活性**：在运行时获得类的各种内容，进行反编译
2. **动态装配**：对于Java这种先编译再运行的语言，能够让我们很方便的创建灵活的代码，这些代码可以在运行时装配
3. **降低耦合度**：无需在组件之间进行源代码的链接，更加容易实现面向对象
4. **框架基础**：是许多Java框架（如Spring、Hibernate）的基础技术

#### 缺点

1. **性能开销**：反射会消耗一定的系统资源，因此如果不需要动态地创建一个对象，那么就不需要用反射
2. **安全风险**：反射调用方法时可以忽略权限检查，因此可能会破坏封装性而导致安全问题
3. **代码复杂性**：使用反射的代码通常比直接调用更复杂，可读性较差
4. **编译时检查缺失**：反射是在运行时解析，因此不能利用编译时检查，容易出现运行时错误

#### 反射的特殊作用

反射机制在实现壳程序动态加载被保护程序时非常关键，它可以突破默认的权限访问控制，访问系统默认情况下禁止用户代码访问的以及不公开的部分。

---

### 反射核心类详解

Java反射机制主要由以下几个核心类实现，这些类都位于`java.lang.reflect`包中：

| 类名 | 功能描述 |
| --- | --- |
| `Class` | 代表一个类，是Java反射机制的起源和入口 |
| `Constructor` | 代表类的构造方法 |
| `Field` | 代表类的成员变量（属性） |
| `Method` | 代表类的成员方法 |
| `Modifier` | 提供修饰符的静态方法和常量 |

#### 反射相关核心导入

```
import java.lang.Class;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
```

---

### Class类详解

#### Class类的特点

1. **Class类的对象称为类对象**
2. **Class类是Java反射机制的起源和入口**，用于获取与类相关的各种信息
3. **Class类提供了获取类信息的相关方法**
4. **Class类继承自Object类**
5. **Class类是所有类的共同图纸**

#### Class对象的理解

- 每个类有自己的对象，好比图纸和实物的关系
- 每个类也可看做是一个对象，有共同的图纸Class
- Class对象存放类的结构信息，比如类的名字、属性、方法、构造方法、父类和接口
- 能够通过相应方法取出相应信息

#### 获取Class对象的四种方式

##### 1. 动态加载方式

```
// 方式1：通过Class.forName()
Class<?> clazz = Class.forName("完整类名");

// 方式2：通过ClassLoader
Class<?> clazz2 = ClassLoader.getSystemClassLoader().loadClass("完整类名");
```

##### 2. 非动态加载方式

```
// 方式3：通过.class属性
Class<?> clazz3 = Person.class;

// 方式4：通过实例对象的getClass()方法
Class<?> clazz4 = new Person().getClass();
```

#### 示例：获取Class对象并获取基本信息

```
// 示例类
class Person implements Runnable {
    public String name;
    private int age;

    public Person() {}
    private Person(String str) {
        System.out.println("Private constructor:" + str);
    }
    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }

    public void introduce() {
        System.out.println("我是" + name + ",年龄" + age);
    }

    private void privateMethod(String name, int age) {
        System.out.println("这是Person的私有方法,name=" + name + ",age=" + age);
    }

    @Override
    public void run() {
        System.out.println("Hello World");
    }
}

// 获取Class对象示例
public class ReflectionExample {
    public static void main(String[] args) throws Exception {
        // 获取Class对象的四种方式
        Class<?> clazz = Class.forName("Person");
        Class<?> clazz2 = ClassLoader.getSystemClassLoader().loadClass("Person");
        Class<?> clazz3 = Person.class;
        Class<?> clazz4 = new Person().getClass();
        
        System.out.println("Load Class:");
        System.out.println(clazz);   // class Person
        System.out.println(clazz2);  // class Person
        System.out.println(clazz3);  // class Person
        System.out.println(clazz4);  // class Person
        
        // 获取类的基本信息
        System.out.println("Class info:");
        System.out.println(clazz.getName());        // 完整类名：Person
        System.out.println(clazz.getSimpleName());  // 类名：Person
        System.out.println(clazz.getSuperclass());  // 父类：class java.lang.Object
        System.out.println(Arrays.toString(clazz.getInterfaces())); // 接口：[interface java.lang.Runnable]
    }
}
```

**输出结果：**

```
Load Class:
class Person
class Person
class Person
class Person

Class info:
Person
Person
class java.lang.Object
[interface java.lang.Runnable]
```

---

### 获取Constructor构造方法

#### Constructor相关方法总览

| 方法 | 功能描述 |
| --- | --- |
| `getConstructor(Class<?>... parameterTypes)` | 获取指定参数类型的public构造方法 |
| `getConstructors()` | 获取所有public权限的构造方法 |
| `getDeclaredConstructor(Class<?>... parameterTypes)` | 获取指定参数类型的任意构造方法 |
| `getDeclaredConstructors()` | 获取所有构造方法 |

#### 详细示例

```
public class ConstructorExample {
    public static void main(String[] args) throws Exception {
        Class<?> clazz = Person.class;
        
        // 1. 获取无参构造方法(默认构造方法)
        System.out.println("Get constructor:");
        Constructor<?> constructor = clazz.getConstructor();
        System.out.println(constructor);
        
        // 2. 获取所有public构造方法
        System.out.println("Get public constructors:");
        Constructor<?>[] constructors = clazz.getConstructors();
        System.out.println(Arrays.toString(constructors));
        
        // 3. 获取所有构造方法（包括私有）
        System.out.println("Get all constructors:");
        constructors = clazz.getDeclaredConstructors();
        System.out.println(Arrays.toString(constructors));
        
        // 4. 详细打印所有构造方法信息
        System.out.println("Print All Constructors:");
        for (Constructor<?> cons : constructors) {
            System.out.println("constructor: " + cons);
            System.out.println("\tname: " + cons.getName() +
                    "\n\tModifiers: " + Modifier.toString(cons.getModifiers()) +
                    "\n\tParameterTypes: " + Arrays.toString(cons.getParameterTypes()));
        }
    }
}
```

**输出结果：**

```
Get constructor:
public Person()

Get public constructors:
[public Person(java.lang.String,int), public Person()]

Get all constructors:
[public Person(java.lang.String,int), private Person(java.lang.String), public Person()]

Print All Constructors:
constructor: public Person(java.lang.String,int)
    name: Person
    Modifiers: public
    ParameterTypes: [class java.lang.String, int]
constructor: private Person(java.lang.String)
    name: Person
    Modifiers: private
    ParameterTypes: [class java.lang.String]
constructor: public Person()
    name: Person
    Modifiers: public
    ParameterTypes: []
```

---

### 获取Field字段

#### Field相关方法总览

| 方法 | 功能描述 |
| --- | --- |
| `getField(String name)` | 获取指定名称的public属性 |
| `getFields()` | 获取所有public声明的属性 |
| `getDeclaredField(String name)` | 获取指定名称的任意属性 |
| `getDeclaredFields()` | 获取所有属性 |

#### 详细示例

```
public class FieldExample {
    public static void main(String[] args) throws Exception {
        Class<?> clazz = Person.class;
        
        // 1. 获取所有public属性
        System.out.println("Get public fields:");
        Field[] fields = clazz.getFields();
        System.out.println(Arrays.toString(fields));
        
        // 2. 获取所有属性（包括私有）
        System.out.println("Get all fields:");
        fields = clazz.getDeclaredFields();
        System.out.println(Arrays.toString(fields));
        
        // 3. 详细打印所有字段信息
        System.out.println("Print all fields:");
        for (Field field : fields) {
            System.out.println("field: " + field);
            System.out.println("\ttype: " + field.getType() +
                    "\n\tname: " + field.getName());
        }
        
        // 4. 获取指定字段
        System.out.println("Get specific field:");
        // 获取public权限的指定属性
        Field field = clazz.getField("name");
        System.out.println(field);
        // 获取任意权限的指定属性
        field = clazz.getDeclaredField("age");
        System.out.println(field);
    }
}
```

**输出结果：**

```
Get public fields:
[public java.lang.String Person.name]

Get all fields:
[public java.lang.String Person.name, private int Person.age]

Print all fields:
field: public java.lang.String Person.name
    type: class java.lang.String
    name: name
field: private int Person.age
    type: int
    name: age

Get specific field:
public java.lang.String Person.name
private int Person.age
```

---

### 获取Method方法

#### Method相关方法总览

| 方法 | 功能描述 |
| --- | --- |
| `getMethod(String name, Class<?>... parameterTypes)` | 获取指定方法名和参数类型的public方法 |
| `getMethods()` | 获取所有public方法（包括继承的） |
| `getDeclaredMethod(String name, Class<?>... parameterTypes)` | 获取指定方法名和参数类型的任意方法 |
| `getDeclaredMethods()` | 获取所有声明的方法 |

#### 详细示例

```
public class MethodExample {
    public static void main(String[] args) throws Exception {
        Class<?> clazz = Person.class;
        
        // 1. 获取所有public方法（注意会获取所实现接口和继承的public方法）
        System.out.println("Get public methods:");
        Method[] methods = clazz.getMethods();
        System.out.println(Arrays.toString(methods));
        
        // 2. 获取所有声明的方法
        System.out.println("Get all methods:");
        methods = clazz.getDeclaredMethods();
        System.out.println(Arrays.toString(methods));
        
        // 3. 详细打印所有方法信息
        System.out.println("Print all methods:");
        for (Method method : methods) {
            System.out.println("method: " + method);
            System.out.println("\tname: " + method.getName());
            System.out.println("\treturnType: " + method.getReturnType());
            System.out.println("\tparameterTypes: " + Arrays.toString(method.getParameterTypes()));
        }
        
        // 4. 获取指定方法
        // 获取public的指定方法
        Method method = clazz.getMethod("introduce");
        System.out.println(method);
        // 获取任意权限的指定方法
        method = clazz.getDeclaredMethod("privateMethod", String.class, int.class);
        System.out.println(method);
    }
}
```

**输出结果：**

```
Get public methods:
[public void Person.run(), public void Person.introduce(), 
 public final void java.lang.Object.wait(long,int) throws java.lang.InterruptedException, 
 ... (其他Object类的方法)]

Get all methods:
[public void Person.run(), public void Person.introduce(), 
 private void Person.privateMethod(java.lang.String,int)]

Print all methods:
method: public void Person.run()
    name: run
    returnType: void
    parameterTypes: []
method: public void Person.introduce()
    name: introduce
    returnType: void
    parameterTypes: []
method: private void Person.privateMethod(java.lang.String,int)
    name: privateMethod
    returnType: void
    parameterTypes: [class java.lang.String, int]

public void Person.introduce()
private void Person.privateMethod(java.lang.String,int)
```

---

### 反射创建对象

#### 创建对象的两种方式

##### 方式1：Class.newInstance()

- **特点**：调用无参构造方法创建实例，不能传递参数
- **限制**：要求Class对象对应的类有无参构造方法
- **注意**：此方法在Java 9中已被标记为过时

##### 方式2：Constructor.newInstance()

- **特点**：通过Class获取Constructor，再创建对象，可使用指定构造方法
- **优势**：可传递参数，更加灵活

#### 详细示例

```
public class CreateObjectExample {
    public static void main(String[] args) throws Exception {
        Class<?> clazz = Person.class;
        
        // 方式1：Class.newInstance() - 调用无参构造方法
        System.out.println("Create instance by Class.newInstance():");
        Object obj = clazz.newInstance();
        System.out.println(obj.toString());
        
        // 方式2：Constructor.newInstance() - 更灵活的方式
        System.out.println("Create instance by Constructor.newInstance():");
        
        // 使用无参构造方法
        Constructor<?> cons = clazz.getConstructor();
        obj = cons.newInstance();
        System.out.println(obj.toString());
        
        // 使用有参构造方法
        cons = clazz.getConstructor(String.class, int.class);
        obj = cons.newInstance("张三", 18);
        System.out.println(obj.toString());
        
        // 使用私有构造方法
        cons = clazz.getDeclaredConstructor(String.class);
        cons.setAccessible(true); // 突破访问权限
        obj = cons.newInstance("私有构造");
    }
}
```

**输出结果：**

```
Create instance by Class.newInstance():
Person@30dae81

Create instance by Constructor.newInstance():
Person@1b2c6ec2
Person@4edde6e5
Private constructor:私有构造
```

---

### 反射操作属性

#### 操作属性的核心方法

| 方法 | 功能描述 |
| --- | --- |
| `Field.get(Object obj)` | 获取指定实例的字段值 |
| `Field.set(Object obj, Object value)` | 设置指定实例的字段值 |
| `Field.setAccessible(true)` | 突破属性权限控制 |

#### 操作步骤

1. 获取Field对象：`Class.getField(fieldName)` 或 `Class.getDeclaredField(fieldName)`
2. 突破权限控制（如果是私有字段）：`Field.setAccessible(true)`
3. 获取或设置值：`Field.get(obj)` 或 `Field.set(obj, value)`

#### 详细示例

```
public class FieldOperationExample {
    public static void main(String[] args) throws Exception {
        Class<?> clazz = Person.class;
        Person person = new Person("李四", 25);
        
        System.out.println("Access field by reflection:");
        
        // 操作public字段
        Field nameField = clazz.getField("name");
        nameField.set(person, "王五");    // 修改指定对象的指定属性
        System.out.println("修改后的name: " + nameField.get(person));
        
        // 操作private字段
        Field ageField = clazz.getDeclaredField("age");
        ageField.setAccessible(true);    // 突破权限控制
        ageField.set(person, 20);
        System.out.println("修改后的age: " + ageField.get(person));
        
        // 验证修改结果
        person.introduce(); // 应该显示修改后的值
    }
}
```

**输出结果：**

```
Access field by reflection:
修改后的name: 王五
修改后的age: 20
我是王五,年龄20
```

---

### 反射调用方法

#### 调用方法的核心方法

| 方法 | 功能描述 |
| --- | --- |
| `Method.invoke(Object obj, Object... args)` | 调用指定实例的方法，可传递参数 |
| `Method.setAccessible(true)` | 突破访问权限控制 |

#### 调用步骤

1. 获取Method对象：`Class.getMethod(methodName, parameterTypes...)` 或 `Class.getDeclaredMethod(methodName, parameterTypes...)`
2. 突破权限控制（如果是私有方法）：`Method.setAccessible(true)`
3. 调用方法：`Method.invoke(obj, args...)`

#### 详细示例

```
public class MethodInvocationExample {
    public static void main(String[] args) throws Exception {
        Class<?> clazz = Person.class;
        Person person = new Person("赵六", 22);
        
        System.out.println("Run method by reflection:");
        
        // 调用public无参方法
        Method introduceMethod = clazz.getMethod("introduce");
        introduceMethod.invoke(person); // 等价于 person.introduce()
        
        // 调用private有参方法
        Method privateMethod = clazz.getDeclaredMethod("privateMethod", String.class, int.class);
        privateMethod.setAccessible(true); // 突破权限控制
        privateMethod.invoke(person, "赵四", 19); // 等价于 person.privateMethod("赵四", 19)
        
        // 调用实现接口的方法
        Method runMethod = clazz.getMethod("run");
        runMethod.invoke(person); // 等价于 person.run()
    }
}
```

**输出结果：**

```
Run method by reflection:
我是赵六,年龄22
这是Person的私有方法,name=赵四,age=19
Hello World
```

---

### 反射工具类封装

为了便于实际项目中使用反射，我们可以封装一个通用的反射工具类：

#### 完整的反射工具类

```
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;

/**
 * Java反射工具类
 * 提供便捷的反射操作方法，包括方法调用、字段访问、实例创建等
 * 
 * @author ReflectionUtil
 * @version 2.0
 */
public class ReflectionUtil {
    private static final String TAG = "ReflectionUtil";
    
    /**
     * 调用静态方法
     * 
     * @param fullClassName 完整类路径（包名.类名），如 "com.example.utils.StringHelper"
     * @param methodName 方法名
     * @param parameterTypes 参数类型数组，如果无参数则传null或空数组
     * @param parameterValues 参数值数组，如果无参数则传null或空数组
     * @return 方法返回值，如果方法无返回值则返回null
     * @throws IllegalArgumentException 当参数类型和参数值数组长度不匹配时抛出
     */
    public static Object invokeStaticMethod(String fullClassName, String methodName, 
                                          Class<?>[] parameterTypes, Object[] parameterValues) {
        if (fullClassName == null || fullClassName.trim().isEmpty()) {
            throw new IllegalArgumentException("完整类路径不能为空");
        }
        if (methodName == null || methodName.trim().isEmpty()) {
            throw new IllegalArgumentException("方法名不能为空");
        }
        
        // 参数校验
        validateParameters(parameterTypes, parameterValues);
        
        try {
            Class<?> clazz = Class.forName(fullClassName);
            Method method = findMethod(clazz, methodName, parameterTypes);
            
            if (!Modifier.isStatic(method.getModifiers())) {
                throw new IllegalArgumentException("方法 " + methodName + " 不是静态方法");
            }
            
            method.setAccessible(true);
            return method.invoke(null, parameterValues); // 静态方法第一个参数为null
        } catch (Exception e) {
            System.err.println("调用静态方法失败 [类: " + fullClassName + ", 方法: " + methodName + "]: " + e.getMessage());
            e.printStackTrace();
            return null;
        }
    }
    
    /**
     * 调用实例方法
     * 
     * @param fullClassName 完整类路径（包名.类名），如 "com.example.model.User"
     * @param methodName 方法名
     * @param instance 实例对象，不能为null
     * @param parameterTypes 参数类型数组，如果无参数则传null或空数组
     * @param parameterValues 参数值数组，如果无参数则传null或空数组
     * @return 方法返回值，如果方法无返回值则返回null
     * @throws IllegalArgumentException 当实例对象为null或参数不匹配时抛出
     */
    public static Object invokeInstanceMethod(String fullClassName, String methodName, Object instance,
                                            Class<?>[] parameterTypes, Object[] parameterValues) {
        if (fullClassName == null || fullClassName.trim().isEmpty()) {
            throw new IllegalArgumentException("完整类路径不能为空");
        }
        if (methodName == null || methodName.trim().isEmpty()) {
            throw new IllegalArgumentException("方法名不能为空");
        }
        if (instance == null) {
            throw new IllegalArgumentException("实例对象不能为null");
        }
        
        // 参数校验
        validateParameters(parameterTypes, parameterValues);
        
        try {
            Class<?> clazz = Class.forName(fullClassName);
            Method method = findMethod(clazz, methodName, parameterTypes);
            method.setAccessible(true);
            return method.invoke(instance, parameterValues);
        } catch (Exception e) {
            System.err.println("调用实例方法失败 [类: " + fullClassName + ", 方法: " + methodName + "]: " + e.getMessage());
            e.printStackTrace();
            return null;
        }
    }
    
    /**
     * 获取实例字段值
     * 
     * @param fullClassName 完整类路径（包名.类名），如 "com.example.model.User"
     * @param instance 实例对象，不能为null
     * @param fieldName 字段名
     * @return 字段值
     * @throws IllegalArgumentException 当实例对象为null时抛出
     */
    public static Object getInstanceField(String fullClassName, Object instance, String fieldName) {
        if (fullClassName == null || fullClassName.trim().isEmpty()) {
            throw new IllegalArgumentException("完整类路径不能为空");
        }
        if (instance == null) {
            throw new IllegalArgumentException("实例对象不能为null");
        }
        if (fieldName == null || fieldName.trim().isEmpty()) {
            throw new IllegalArgumentException("字段名不能为空");
        }
        
        try {
            Class<?> clazz = Class.forName(fullClassName);
            Field field = findField(clazz, fieldName);
            field.setAccessible(true);
            return field.get(instance);
        } catch (Exception e) {
            System.err.println("获取实例字段失败 [类: " + fullClassName + ", 字段: " + fieldName + "]: " + e.getMessage());
            e.printStackTrace();
            return null;
        }
    }
    
    /**
     * 获取静态字段值
     * 
     * @param fullClassName 完整类路径（包名.类名），如 "com.example.config.AppConfig"
     * @param fieldName 字段名
     * @return 字段值
     */
    public static Object getStaticField(String fullClassName, String fieldName) {
        if (fullClassName == null || fullClassName.trim().isEmpty()) {
            throw new IllegalArgumentException("完整类路径不能为空");
        }
        if (fieldName == null || fieldName.trim().isEmpty()) {
            throw new IllegalArgumentException("字段名不能为空");
        }
        
        try {
            Class<?> clazz = Class.forName(fullClassName);
            Field field = findField(clazz, fieldName);
            
            if (!Modifier.isStatic(field.getModifiers())) {
                throw new IllegalArgumentException("字段 " + fieldName + " 不是静态字段");
            }
            
            field.setAccessible(true);
            return field.get(null); // 静态字段第一个参数为null
        } catch (Exception e) {
            System.err.println("获取静态字段失败 [类: " + fullClassName + ", 字段: " + fieldName + "]: " + e.getMessage());
            e.printStackTrace();
            return null;
        }
    }
    
    /**
     * 设置实例字段值
     * 
     * @param fullClassName 完整类路径（包名.类名），如 "com.example.model.User"
     * @param fieldName 字段名
     * @param instance 实例对象，不能为null
     * @param value 新值
     * @return 是否设置成功
     * @throws IllegalArgumentException 当实例对象为null时抛出
     */
    public static boolean setInstanceField(String fullClassName, String fieldName, Object instance, Object value) {
        if (fullClassName == null || fullClassName.trim().isEmpty()) {
            throw new IllegalArgumentException("完整类路径不能为空");
        }
        if (fieldName == null || fieldName.trim().isEmpty()) {
            throw new IllegalArgumentException("字段名不能为空");
        }
        if (instance == null) {
            throw new IllegalArgumentException("实例对象不能为null");
        }
        
        try {
            Class<?> clazz = Class.forName(fullClassName);
            Field field = findField(clazz, fieldName);
            field.setAccessible(true);
            field.set(instance, value);
            return true;
        } catch (Exception e) {
            System.err.println("设置实例字段失败 [类: " + fullClassName + ", 字段: " + fieldName + "]: " + e.getMessage());
            e.printStackTrace();
            return false;
        }
    }
    
    /**
     * 设置静态字段值
     * 
     * @param fullClassName 完整类路径（包名.类名），如 "com.example.config.AppConfig"
     * @param fieldName 字段名
     * @param value 新值
     * @return 是否设置成功
     */
    public static boolean setStaticField(String fullClassName, String fieldName, Object value) {
        if (fullClassName == null || fieldName == null) {
            throw new IllegalArgumentException("完整类路径和字段名不能为空");
        }
        
        try {
            Class<?> clazz = Class.forName(fullClassName);
            Field field = findField(clazz, fieldName);
            
            if (!Modifier.isStatic(field.getModifiers())) {
                throw new IllegalArgumentException("字段 " + fieldName + " 不是静态字段");
            }
            
            field.setAccessible(true);
            field.set(null, value); // 静态字段第一个参数为null
            return true;
        } catch (Exception e) {
            System.err.println("设置静态字段失败 [类: " + fullClassName + ", 字段: " + fieldName + "]: " + e.getMessage());
            e.printStackTrace();
            return false;
        }
    }
    
    /**
     * 创建类实例
     * 
     * @param fullClassName 完整类路径（包名.类名），如 "com.example.model.User"
     * @param parameterTypes 构造方法参数类型数组，如果使用无参构造则传null或空数组
     * @param parameterValues 构造方法参数值数组，如果使用无参构造则传null或空数组
     * @return 实例对象，创建失败返回null
     */
    public static Object createInstance(String fullClassName, Class<?>[] parameterTypes, Object[] parameterValues) {
        if (fullClassName == null || fullClassName.trim().isEmpty()) {
            throw new IllegalArgumentException("完整类路径不能为空");
        }
        
        // 参数校验
        validateParameters(parameterTypes, parameterValues);
        
        try {
            Class<?> clazz = Class.forName(fullClassName);
            
            // 如果没有参数，使用无参构造
            if (parameterTypes == null || parameterTypes.length == 0) {
                return clazz.getDeclaredConstructor().newInstance();
            } else {
                Constructor<?> constructor = clazz.getDeclaredConstructor(parameterTypes);
                constructor.setAccessible(true);
                return constructor.newInstance(parameterValues);
            }
        } catch (Exception e) {
            System.err.println("创建实例失败 [类: " + fullClassName + "]: " + e.getMessage());
            e.printStackTrace();
            return null;
        }
    }
    
    /**
     * 检查类是否存在
     * 
     * @param fullClassName 完整类路径（包名.类名），如 "com.example.model.User"
     * @return 类是否存在
     */
    public static boolean classExists(String fullClassName) {
        if (fullClassName == null || fullClassName.trim().isEmpty()) {
            return false;
        }
        
        try {
            Class.forName(fullClassName);
            return true;
        } catch (ClassNotFoundException e) {
            return false;
        }
    }
    
    /**
     * 获取类的所有字段名（包括私有字段）
     * 
     * @param fullClassName 完整类路径（包名.类名）
     * @return 字段名数组，如果获取失败返回空数组
     */
    public static String[] getAllFieldNames(String fullClassName) {
        if (fullClassName == null || fullClassName.trim().isEmpty()) {
            return new String[0];
        }
        
        try {
            Class<?> clazz = Class.forName(fullClassName);
            Field[] fields = clazz.getDeclaredFields();
            String[] fieldNames = new String[fields.length];
            for (int i = 0; i < fields.length; i++) {
                fieldNames[i] = fields[i].getName();
            }
            return fieldNames;
        } catch (Exception e) {
            System.err.println("获取字段名失败 [类: " + fullClassName + "]: " + e.getMessage());
            return new String[0];
        }
    }
    
    // ======================== 私有辅助方法 ========================
    
    /**
     * 验证参数类型和参数值数组的有效性
     */
    private static void validateParameters(Class<?>[] parameterTypes, Object[] parameterValues) {
        if (parameterTypes == null && parameterValues == null) {
            return;
        }
        if (parameterTypes == null) {
            parameterTypes = new Class<?>[0];
        }
        if (parameterValues == null) {
            parameterValues = new Object[0];
        }
        if (parameterTypes.length != parameterValues.length) {
            throw new IllegalArgumentException("参数类型数组长度(" + parameterTypes.length + 
                                             ")与参数值数组长度(" + parameterValues.length + ")不匹配");
        }
    }
    
    /**
     * 查找方法，支持在父类中查找
     */
    private static Method findMethod(Class<?> clazz, String methodName, Class<?>[] parameterTypes) 
            throws NoSuchMethodException {
        if (parameterTypes == null) {
            parameterTypes = new Class<?>[0];
        }
        
        Class<?> currentClass = clazz;
        while (currentClass != null) {
            try {
                return currentClass.getDeclaredMethod(methodName, parameterTypes);
            } catch (NoSuchMethodException e) {
                currentClass = currentClass.getSuperclass();
            }
        }
        throw new NoSuchMethodException("找不到方法: " + methodName + " 在类 " + clazz.getName() + " 及其父类中");
    }
    
    /**
     * 查找字段，支持在父类中查找
     */
    private static Field findField(Class<?> clazz, String fieldName) throws NoSuchFieldException {
        Class<?> currentClass = clazz;
        while (currentClass != null) {
            try {
                return currentClass.getDeclaredField(fieldName);
            } catch (NoSuchFieldException e) {
                currentClass = currentClass.getSuperclass();
            }
        }
        throw new NoSuchFieldException("找不到字段: " + fieldName + " 在类 " + clazz.getName() + " 及其父类中");
    }
}
```

#### 工具类使用示例

```
// 调用静态方法
Object result = ReflectionUtil.invokeStaticMethod(
    "com.example.utils.StringHelper",  // 完整类路径
    "formatString", 
    new Class[]{String.class}, 
    new Object[]{"hello"}
);

// 创建实例
Object user = ReflectionUtil.createInstance(
    "com.example.model.User",  // 完整类路径
    new Class[]{String.class, int.class}, 
    new Object[]{"张三", 25}
);

// 检查类是否存在
boolean exists = ReflectionUtil.classExists("com.example.model.User");
```
