---
title: "Claude Code 实战案例：从零构建完整应用"
date: 2026-04-02
description: "1. 案例概览 2. 案例一：CLI 工具开发 3. 案例二：全栈 Web 应用 4. 案例三：遗留代码重构"
tags: ['Claude Code']
draft: true
category: "技术"
---
> 汇总海外开发者使用 Claude Code 的真实项目案例

## 目录

1. [案例概览](#1-案例概览)
2. [案例一：CLI 工具开发](#2-案例一cli-工具开发)
3. [案例二：全栈 Web 应用](#3-案例二全栈-web-应用)
4. [案例三：遗留代码重构](#4-案例三遗留代码重构)
5. [案例四：MCP 服务器开发](#5-案例四mcp-服务器开发)
6. [通用最佳实践](#6-通用最佳实践)

---

## 1. 案例概览

| 案例 | 技术栈 | 复杂度 | 时间节省 |
|------|--------|--------|----------|
| CLI 工具 | TypeScript/Node.js | 初级 | 70% |
| 全栈应用 | Next.js/Prisma/PostgreSQL | 中级 | 60% |
| 遗留重构 | .NET/C# | 高级 | 50% |
| MCP 服务器 | Python/FastAPI | 中级 | 65% |

---

## 2. 案例一：CLI 工具开发

### 项目目标

构建一个温度转换 CLI 工具，支持：
- 摄氏度、华氏度、开尔文互相转换
- 错误处理和输入验证
- 彩色终端输出
- 帮助文档

### 完整对话流程

#### 步骤 1: 初始化项目

```bash
> 创建一个新的 TypeScript CLI 项目，使用现代工具链
```

Claude 的操作：
1. 创建项目结构
2. 配置 TypeScript
3. 设置 package.json
4. 添加必要的依赖

#### 步骤 2: 实现核心转换逻辑

```bash
> 实现温度转换函数，支持 Celsius、Fahrenheit、Kelvin
```

```typescript
// src/converters/temperature.ts
export type TemperatureUnit = 'C' | 'F' | 'K';

export interface ConversionResult {
  from: { value: number; unit: TemperatureUnit };
  to: { value: number; unit: TemperatureUnit };
}

export function celsiusToFahrenheit(celsius: number): number {
  return (celsius * 9/5) + 32;
}

export function celsiusToKelvin(celsius: number): number {
  return celsius + 273.15;
}

export function fahrenheitToCelsius(fahrenheit: number): number {
  return (fahrenheit - 32) * 5/9;
}

export function kelvinToCelsius(kelvin: number): number {
  return kelvin - 273.15;
}

export function convertTemperature(
  value: number,
  fromUnit: TemperatureUnit,
  toUnit: TemperatureUnit
): ConversionResult {
  // 首先转换为摄氏度（中间单位）
  let celsius: number;
  switch (fromUnit) {
    case 'C':
      celsius = value;
      break;
    case 'F':
      celsius = fahrenheitToCelsius(value);
      break;
    case 'K':
      celsius = kelvinToCelsius(value);
      break;
  }

  // 然后从摄氏度转换为目标单位
  let result: number;
  switch (toUnit) {
    case 'C':
      result = celsius;
      break;
    case 'F':
      result = celsiusToFahrenheit(celsius);
      break;
    case 'K':
      result = celsiusToKelvin(celsius);
      break;
  }

  return {
    from: { value, unit: fromUnit },
    to: { value: Number(result.toFixed(2)), unit: toUnit }
  };
}
```

#### 步骤 3: 添加 CLI 界面

```bash
> 使用 commander.js 创建 CLI 界面，支持彩色输出
```

```typescript
// src/index.ts
#!/usr/bin/env node

import { Command } from 'commander';
import chalk from 'chalk';
import { convertTemperature, TemperatureUnit } from './converters/temperature';

const program = new Command();

program
  .name('temp-convert')
  .description('Convert temperatures between Celsius, Fahrenheit, and Kelvin')
  .version('1.0.0')
  .argument('<value>', 'temperature value to convert')
  .option('-f, --from <unit>', 'source unit (C, F, K)', 'C')
  .option('-t, --to <unit>', 'target unit (C, F, K)', 'F')
  .action((valueStr: string, options) => {
    try {
      const value = parseFloat(valueStr);

      if (isNaN(value)) {
        console.error(chalk.red('Error: Invalid temperature value'));
        process.exit(1);
      }

      const fromUnit = options.from.toUpperCase() as TemperatureUnit;
      const toUnit = options.to.toUpperCase() as TemperatureUnit;

      if (!['C', 'F', 'K'].includes(fromUnit) || !['C', 'F', 'K'].includes(toUnit)) {
        console.error(chalk.red('Error: Unit must be C, F, or K'));
        process.exit(1);
      }

      const result = convertTemperature(value, fromUnit, toUnit);

      console.log(
        chalk.green(`${result.from.value}°${result.from.unit}`) +
        chalk.gray(' = ') +
        chalk.bold.yellow(`${result.to.value}°${result.to.unit}`)
      );

    } catch (error) {
      console.error(chalk.red('Conversion failed:'), error);
      process.exit(1);
    }
  });

program.parse();
```

#### 步骤 4: 添加测试

```bash
> 为温度转换函数编写单元测试
```

```typescript
// tests/temperature.test.ts
import { describe, it, expect } from 'vitest';
import { convertTemperature } from '../src/converters/temperature';

describe('Temperature Conversion', () => {
  it('should convert Celsius to Fahrenheit correctly', () => {
    const result = convertTemperature(0, 'C', 'F');
    expect(result.to.value).toBe(32);
  });

  it('should convert Celsius to Kelvin correctly', () => {
    const result = convertTemperature(0, 'C', 'K');
    expect(result.to.value).toBe(273.15);
  });

  it('should convert Fahrenheit to Celsius correctly', () => {
    const result = convertTemperature(32, 'F', 'C');
    expect(result.to.value).toBe(0);
  });

  it('should handle negative temperatures', () => {
    const result = convertTemperature(-40, 'C', 'F');
    expect(result.to.value).toBe(-40);
  });
});
```

### 关键学习点

1. **分步骤构建**: 不要一次性要求所有功能
2. **测试驱动**: 让 Claude 先写测试，再写实现
3. **错误处理**: 特别强调输入验证
4. **代码组织**: 让 Claude 建议合理的文件结构

---

## 3. 案例二：全栈 Web 应用

### 项目目标

构建一个完整的家务管理应用：
- 类似 Outlook 的日历视图
- 添加/删除家务
- 循环计划设置
- 团队成员分配

### Plan Mode 规划

```bash
> 进入 Plan Mode，规划这个应用的架构
```

Claude 的规划问题：

```
我需要了解一些细节：

1. 前端框架偏好？
   - React
   - Vue
   - Svelte
   - Next.js (推荐)

2. 数据存储方案？
   - 本地存储
   - PostgreSQL
   - MongoDB
   - Supabase (推荐)

3. UI 组件库？
   - shadcn/ui
   - Chakra UI
   - Material-UI
   - Tailwind CSS (推荐)

4. 认证需求？
   - 无需认证
   - Email/Password
   - OAuth (Google/GitHub)
   - Clerk/Auth0 (推荐)

5. 部署目标？
   - Vercel
   - Netlify
   - Railway
```

### 实现阶段

#### 第一阶段：项目初始化

```bash
> 使用 Next.js 15 + TypeScript + Tailwind 创建项目
> 集成 shadcn/ui 组件库
> 配置 Supabase 数据库连接
```

#### 第二阶段：数据模型

```bash
> 设计数据库 schema，包含：
- chores 表（家务项）
- assignments 表（分配关系）
- schedules 表（循环计划）
```

```sql
-- Supabase Schema
CREATE TABLE chores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT,
  category TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE schedules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chore_id UUID REFERENCES chores(id) ON DELETE CASCADE,
  frequency TEXT NOT NULL, -- 'daily', 'weekly', 'monthly'
  days_of_week TEXT[], -- [1,2,3,4,5] for weekdays
  start_date DATE NOT NULL,
  end_date DATE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE assignments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chore_id UUID REFERENCES chores(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  assigned_date DATE NOT NULL,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### 第三阶段：核心功能

```bash
> 实现家务 CRUD API 路由
> 创建日历视图组件
> 添加拖拽分配功能
```

```typescript
// app/api/chores/route.ts
import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs';
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

export async function GET() {
  const supabase = createRouteHandlerClient({ cookies });

  const { data, error } = await supabase
    .from('chores')
    .select('*, schedules(*), assignments(*)')
    .order('created_at', { ascending: false });

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 400 });
  }

  return NextResponse.json(data);
}

export async function POST(request: Request) {
  const supabase = createRouteHandlerClient({ cookies });
  const body = await request.json();

  const { data, error } = await supabase
    .from('chores')
    .insert(body)
    .select()
    .single();

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 400 });
  }

  return NextResponse.json(data, { status: 201 });
}
```

#### 第四阶段：日历视图

```bash
> 创建日历组件，显示每日家务
> 添加点击创建新家务功能
> 实现拖拽到日期重新分配
```

### 关键学习点

1. **Plan Mode 的价值**: 在开始编码前明确所有决策
2. **模块化开发**: 按功能模块而非文件结构组织任务
3. **数据库优先**: 先设计数据模型，再构建应用
4. **渐进式增强**: 从基础功能开始，逐步添加高级特性

---

## 4. 案例三：遗留代码重构

### 项目背景

一个 18,000 行的 React 组件需要拆分为可维护的模块。

### 分析阶段

```bash
> 分析这个巨型组件的职责
> 识别可以拆分的子组件
> 提取自定义 hooks
```

Claude 的分析：

```markdown
## 组件职责分析

当前组件承担了太多职责：

1. **数据获取**: 从多个 API 获取数据
2. **状态管理**: 复杂的本地状态
3. **UI 渲染**: 多种视图模式
4. **事件处理**: 用户交互逻辑
5. **数据转换**: 格式化和计算

## 建议的拆分方案

### 子组件
- `DataGrid.tsx` - 数据表格
- `FilterPanel.tsx` - 筛选器
- `ViewSwitcher.tsx` - 视图切换
- `ItemCard.tsx` - 单个项目卡片

### Hooks
- `useDataFetching.ts` - 数据获取逻辑
- `useFilters.ts` - 筛选状态管理
- `usePagination.ts` - 分页逻辑

### Utils
- `formatters.ts` - 数据格式化
- `validators.ts` - 数据验证
```

### 重构执行

#### 第一步：提取数据逻辑

```bash
> 创建 useDataFetching hook，将所有 API 调用移入
```

```typescript
// hooks/useDataFetching.ts
export function useDataFetching(filters: FilterState) {
  const [data, setData] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const response = await api.get('/items', { params: filters });
        setData(response.data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [filters]);

  return { data, loading, error, refetch: () => fetchData() };
}
```

#### 第二步：创建子组件

```bash
> 创建 DataGrid 组件，接收数据和回调作为 props
```

```typescript
// components/DataGrid.tsx
interface DataGridProps {
  data: Item[];
  columns: Column[];
  onSort: (column: string) => void;
  onRowClick: (item: Item) => void;
}

export function DataGrid({ data, columns, onSort, onRowClick }: DataGridProps) {
  return (
    <table className="w-full">
      <thead>
        <tr>
          {columns.map(col => (
            <th key={col.key} onClick={() => onSort(col.key)}>
              {col.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map(item => (
          <tr key={item.id} onClick={() => onRowClick(item)}>
            {columns.map(col => (
              <td key={col.key}>{item[col.key]}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

#### 第三步：简化主组件

```bash
> 重写主组件，组合新的子组件和 hooks
```

```typescript
// MassiveComponent.tsx (重构后)
export function MassiveComponent() {
  const filters = useFilterState();
  const { data, loading, error } = useDataFetching(filters);
  const pagination = usePagination(data);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <div className="container">
      <FilterPanel filters={filters} />
      <ViewSwitcher currentView={pagination.view} onChange={pagination.setView} />
      <DataGrid
        data={pagination.pageData}
        columns={COLUMNS}
        onSort={pagination.sort}
        onRowClick={handleRowClick}
      />
      <Pagination {...pagination} />
    </div>
  );
}
```

### 关键学习点

1. **Claude 的大文件处理能力**: 18,000 行文件也能正确分析
2. **渐进式重构**: 不要一次性重写所有内容
3. **保持功能等价**: 每一步都确保功能不变
4. **测试驱动**: 在重构前后运行相同的测试

---

## 5. 案例四：MCP 服务器开发

### 项目目标

创建一个连接 Notion 的 MCP 服务器，允许 Claude 搜索和创建 Notion 页面。

### 项目结构

```
notion-mcp-server/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts          # MCP 服务器入口
│   ├── notion.ts         # Notion API 客户端
│   └── tools.ts          # MCP 工具定义
└── README.md
```

### 实现

#### MCP 服务器主文件

```typescript
// src/index.ts
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { Client } from '@notionhq/client';

const notion = new Client({ auth: process.env.NOTION_API_KEY });

const server = new Server(
  { name: 'notion-mcp', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: 'search_pages',
      description: '在 Notion 中搜索页面',
      inputSchema: {
        type: 'object',
        properties: {
          query: { type: 'string', description: '搜索关键词' },
        },
        required: ['query'],
      },
    },
    {
      name: 'create_page',
      description: '在 Notion 中创建新页面',
      inputSchema: {
        type: 'object',
        properties: {
          parent_id: { type: 'string', description: '父页面 ID' },
          title: { type: 'string', description: '页面标题' },
          content: { type: 'string', description: '页面内容（Markdown）' },
        },
        required: ['parent_id', 'title'],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case 'search_pages':
      const search = await notion.search({
        query: args.query,
        filter: { value: 'page', property: 'object' },
      });
      return {
        content: [{ type: 'text', text: JSON.stringify(search.results, null, 2) }],
      };

    case 'create_page':
      const page = await notion.pages.create({
        parent: { page_id: args.parent_id },
        properties: {
          title: {
            title: [{ text: { content: args.title } }],
          },
        },
        children: [
          {
            object: 'block',
            type: 'paragraph',
            paragraph: {
              text: [{ type: 'text', text: { content: args.content || '' } }],
            },
          },
        ],
      });
      return {
        content: [{ type: 'text', text: JSON.stringify(page, null, 2) }],
      };

    default:
      throw new Error(`未知工具: ${name}`);
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Notion MCP Server running');
}

main().catch(console.error);
```

### 使用自定义 MCP

```bash
# 添加到 Claude Code
claude mcp add --transport stdio notion -- npx -y @username/notion-mcp-server

# 在 Claude Code 中使用
> 在 Notion 中搜索 "会议记录"
> 创建名为 "项目计划" 的 Notion 页面，包含以下内容...
```

---

## 6. 通用最佳实践

### 1. 总是从 CLAUDE.md 开始

为每个项目创建 CLAUDE.md 文件：

```markdown
# 项目名称

## 技术栈
- 前端: Next.js 15 + TypeScript
- 后端: Supabase
- UI: shadcn/ui + Tailwind

## 项目结构
- /app - Next.js App Router
- /components - React 组件
- /lib - 工具函数

## 命令
- dev: npm run dev
- build: npm run build
- test: npm test

## 规范
- 使用 TypeScript 严格模式
- 组件使用函数式 + hooks
- API 路由返回类型化响应
```

### 2. 使用 Plan Mode 处理复杂任务

对于涉及多个文件的更改：
1. 进入 Plan Mode
2. 让 Claude 分析当前代码
3. 讨论实施计划
4. 批准后执行

### 3. 频繁提交

让 Claude 在每个有意义的变化后提交：

```bash
> 完成登录功能后，创建 git commit
```

### 4. 编写测试

```bash
> 为这个功能编写单元测试
> 运行测试并修复任何失败
```

### 5. 代码审查

始终审查 Claude 的更改：

```bash
> 显示你计划的所有更改
> 逐文件审查差异
```

---

**最后更新**: 2026年2月 | **来源**: 汇总自海外开发者的真实项目经验
