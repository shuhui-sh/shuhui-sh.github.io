---
title: "Claude Code 实战：用 AI 重构遗留代码"
date: 2026-02-11
description: "假设我们接手了一个 5 年前的 Node.js 项目，代码存在以下问题： 与 Claude Code 协作，我们采用渐进式重构策略： 运行测试确保通过： 1. 渐进式重构：每次只改一个方面，降低风险"
tags: ['Claude Code', 'AI']
draft: true
category: "技术"
---
> 通过一个真实的遗留代码重构案例，展示如何利用 Claude Code 安全、高效地改善代码质量。

## 案例背景

假设我们接手了一个 5 年前的 Node.js 项目，代码存在以下问题：

- 📦 使用 CommonJS，需要迁移到 ES Modules
- 🔄 回调地狱，需要改为 async/await
- 🚫 没有 TypeScript 类型
- ❌ 缺少测试
- 📝 文档几乎没有

```javascript
// 原始代码示例：user.service.js
var mysql = require('mysql');
var bcrypt = require('bcrypt');

var connection = mysql.createConnection({
  host: process.env.DB_HOST,
  user: process.env.DB_USER,
  password: process.env.DB_PASS,
  database: process.env.DB_NAME
});

function createUser(userData, callback) {
  bcrypt.hash(userData.password, 10, function(err, hash) {
    if (err) {
      callback(err, null);
      return;
    }
    
    var sql = 'INSERT INTO users SET ?';
    connection.query(sql, {
      email: userData.email,
      password: hash,
      name: userData.name,
      created_at: new Date()
    }, function(err, result) {
      if (err) {
        callback(err, null);
        return;
      }
      callback(null, { id: result.insertId, email: userData.email });
    });
  });
}

function findUserByEmail(email, callback) {
  var sql = 'SELECT * FROM users WHERE email = ?';
  connection.query(sql, [email], function(err, results) {
    if (err) {
      callback(err, null);
      return;
    }
    callback(null, results[0] || null);
  });
}

module.exports = {
  createUser: createUser,
  findUserByEmail: findUserByEmail
};
```

## 重构策略

与 Claude Code 协作，我们采用**渐进式重构**策略：

```
┌────────────────────────────────────────────────────────────┐
│                     重构路线图                              │
├────────────────────────────────────────────────────────────┤
│  Phase 1: 添加类型 (保持运行时行为不变)                      │
│     ↓                                                      │
│  Phase 2: 提取接口，添加测试                                │
│     ↓                                                      │
│  Phase 3: 重构实现 (async/await)                           │
│     ↓                                                      │
│  Phase 4: 迁移到 ES Modules                                │
│     ↓                                                      │
│  Phase 5: 生成文档                                         │
└────────────────────────────────────────────────────────────┘
```

---

## Phase 1: 添加 TypeScript 类型

### 与 Claude Code 的对话

```
我有一个遗留的 user.service.js 文件，我想逐步添加 TypeScript 类型。
请先分析现有代码，然后创建类型定义文件。
要求：
1. 不修改运行时行为
2. 类型要尽可能精确
3. 为函数参数和返回值添加类型
```

### Claude Code 生成的类型文件

```typescript
// types/user.d.ts
export interface UserData {
  email: string;
  password: string;
  name: string;
}

export interface User {
  id: number;
  email: string;
  password: string;
  name: string;
  created_at: Date;
}

export interface CreateUserResult {
  id: number;
  email: string;
}

export type Callback<T> = (error: Error | null, result: T | null) => void;

export interface UserService {
  createUser(userData: UserData, callback: Callback<CreateUserResult>): void;
  findUserByEmail(email: string, callback: Callback<User>): void;
}
```

### 添加 JSDoc 注解

```javascript
// user.service.js (添加 JSDoc)
/**
 * @typedef {import('./types/user').UserData} UserData
 * @typedef {import('./types/user').User} User
 * @typedef {import('./types/user').CreateUserResult} CreateUserResult
 */

/**
 * 创建新用户
 * @param {UserData} userData - 用户数据
 * @param {function(Error|null, CreateUserResult|null): void} callback
 */
function createUser(userData, callback) {
  // ... 原有代码
}
```

---

## Phase 2: 添加测试

### 对话

```
现在为 user.service.js 添加单元测试。
要求：
1. 使用 Jest
2. Mock 数据库连接
3. 测试成功和失败场景
4. 测试边界条件
```

### Claude Code 生成的测试

```typescript
// __tests__/user.service.test.ts
import { createUser, findUserByEmail } from '../user.service';
import { connection } from '../db';
import bcrypt from 'bcrypt';

// Mock 依赖
jest.mock('../db');
jest.mock('bcrypt');

describe('UserService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('createUser', () => {
    const mockUserData = {
      email: 'test@example.com',
      password: 'password123',
      name: 'Test User',
    };

    it('should create user successfully', (done) => {
      // Arrange
      (bcrypt.hash as jest.Mock).mockImplementation((_, __, cb) => {
        cb(null, 'hashed_password');
      });
      (connection.query as jest.Mock).mockImplementation((_, __, cb) => {
        cb(null, { insertId: 1 });
      });

      // Act
      createUser(mockUserData, (err, result) => {
        // Assert
        expect(err).toBeNull();
        expect(result).toEqual({
          id: 1,
          email: 'test@example.com',
        });
        expect(bcrypt.hash).toHaveBeenCalledWith(
          'password123',
          10,
          expect.any(Function)
        );
        done();
      });
    });

    it('should handle bcrypt error', (done) => {
      const bcryptError = new Error('Bcrypt failed');
      (bcrypt.hash as jest.Mock).mockImplementation((_, __, cb) => {
        cb(bcryptError, null);
      });

      createUser(mockUserData, (err, result) => {
        expect(err).toBe(bcryptError);
        expect(result).toBeNull();
        done();
      });
    });

    it('should handle database error', (done) => {
      const dbError = new Error('DB connection failed');
      (bcrypt.hash as jest.Mock).mockImplementation((_, __, cb) => {
        cb(null, 'hashed');
      });
      (connection.query as jest.Mock).mockImplementation((_, __, cb) => {
        cb(dbError, null);
      });

      createUser(mockUserData, (err, result) => {
        expect(err).toBe(dbError);
        expect(result).toBeNull();
        done();
      });
    });
  });

  describe('findUserByEmail', () => {
    it('should return user when found', (done) => {
      const mockUser = {
        id: 1,
        email: 'test@example.com',
        name: 'Test',
      };
      (connection.query as jest.Mock).mockImplementation((_, __, cb) => {
        cb(null, [mockUser]);
      });

      findUserByEmail('test@example.com', (err, result) => {
        expect(err).toBeNull();
        expect(result).toEqual(mockUser);
        done();
      });
    });

    it('should return null when user not found', (done) => {
      (connection.query as jest.Mock).mockImplementation((_, __, cb) => {
        cb(null, []);
      });

      findUserByEmail('notfound@example.com', (err, result) => {
        expect(err).toBeNull();
        expect(result).toBeNull();
        done();
      });
    });
  });
});
```

运行测试确保通过：

```bash
npm test -- --coverage
```

---

## Phase 3: 重构为 async/await

### 对话

```
测试已经通过。现在请将 user.service.js 重构为使用 async/await。
要求：
1. 保持公共 API 兼容（同时支持回调和 Promise）
2. 内部使用 async/await
3. 添加适当的错误处理
4. 运行测试确保不破坏功能
```

### Claude Code 重构后的代码

```typescript
// user.service.ts
import mysql from 'mysql2/promise';
import bcrypt from 'bcrypt';
import { UserData, User, CreateUserResult, Callback } from './types/user';

// 数据库连接池
const pool = mysql.createPool({
  host: process.env.DB_HOST,
  user: process.env.DB_USER,
  password: process.env.DB_PASS,
  database: process.env.DB_NAME,
  waitForConnections: true,
  connectionLimit: 10,
});

/**
 * 创建新用户（Promise 版本）
 */
export async function createUserAsync(userData: UserData): Promise<CreateUserResult> {
  const hash = await bcrypt.hash(userData.password, 10);
  
  const [result] = await pool.execute(
    'INSERT INTO users SET email = ?, password = ?, name = ?, created_at = ?',
    [userData.email, hash, userData.name, new Date()]
  );
  
  const insertResult = result as mysql.ResultSetHeader;
  
  return {
    id: insertResult.insertId,
    email: userData.email,
  };
}

/**
 * 创建新用户（回调版本，保持向后兼容）
 */
export function createUser(
  userData: UserData,
  callback: Callback<CreateUserResult>
): void {
  createUserAsync(userData)
    .then((result) => callback(null, result))
    .catch((error) => callback(error, null));
}

/**
 * 根据邮箱查找用户（Promise 版本）
 */
export async function findUserByEmailAsync(email: string): Promise<User | null> {
  const [rows] = await pool.execute(
    'SELECT * FROM users WHERE email = ?',
    [email]
  );
  
  const users = rows as User[];
  return users[0] || null;
}

/**
 * 根据邮箱查找用户（回调版本，保持向后兼容）
 */
export function findUserByEmail(
  email: string,
  callback: Callback<User>
): void {
  findUserByEmailAsync(email)
    .then((result) => callback(null, result))
    .catch((error) => callback(error, null));
}
```

---

## Phase 4: 迁移到 ES Modules

### 对话

```
现在将项目迁移到 ES Modules。
请更新：
1. package.json 添加 "type": "module"
2. 更新所有导入语句
3. 处理 __dirname 等 CommonJS 特有变量
```

### 关键更改

```json
// package.json
{
  "type": "module",
  "exports": {
    ".": "./dist/index.js",
    "./user": "./dist/user.service.js"
  }
}
```

```typescript
// 更新导入语句
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
```

---

## Phase 5: 生成文档

### 对话

```
最后，请为重构后的代码生成 API 文档。
格式：Markdown
包含：函数签名、参数说明、返回值、示例代码
```

### Claude Code 生成的文档

```markdown
# User Service API

## createUserAsync

创建新用户账户。

### 签名

\`\`\`typescript
async function createUserAsync(userData: UserData): Promise<CreateUserResult>
\`\`\`

### 参数

| 参数 | 类型 | 描述 |
|-----|------|------|
| userData.email | string | 用户邮箱地址 |
| userData.password | string | 用户密码（将自动加密） |
| userData.name | string | 用户显示名称 |

### 返回值

| 字段 | 类型 | 描述 |
|-----|------|------|
| id | number | 新创建用户的 ID |
| email | string | 用户邮箱 |

### 示例

\`\`\`typescript
import { createUserAsync } from './user.service';

const newUser = await createUserAsync({
  email: 'user@example.com',
  password: 'securePassword123',
  name: 'John Doe',
});

console.log(`Created user: ${newUser.id}`);
\`\`\`

### 错误处理

- `Error: Duplicate entry` - 邮箱已被注册
- `Error: Connection failed` - 数据库连接失败
```

---

## 重构成果对比

| 指标 | 重构前 | 重构后 | 改进 |
|-----|-------|-------|------|
| 类型覆盖 | 0% | 100% | ✅ |
| 测试覆盖 | 0% | 95% | ✅ |
| 模块系统 | CommonJS | ES Modules | ✅ |
| 异步模式 | 回调 | async/await | ✅ |
| 文档覆盖 | 无 | 完整 API 文档 | ✅ |
| 代码行数 | 45 | 80 | 类型+注释 |

---

## 经验总结

### ✅ 成功因素

1. **渐进式重构**：每次只改一个方面，降低风险
2. **测试先行**：在重构前添加测试，确保行为不变
3. **保持兼容**：提供向后兼容的 API，平滑迁移
4. **AI 协作**：让 Claude Code 处理重复性工作

### ⚠️ 注意事项

1. **审查 AI 输出**：始终检查生成的代码
2. **分步提交**：每个阶段单独提交，方便回滚
3. **集成测试**：除了单元测试，还需要集成测试
4. **团队沟通**：重大重构需要团队共识

---

## 下一步

- 🔄 继续重构其他模块
- 📈 添加性能监控
- 🔒 强化安全措施
- 📚 完善开发者文档

---

*重构不是一蹴而就的，而是持续改进的过程。Claude Code 是你最好的重构伙伴！*
