# 碳基Agent · 个人技术博客

基于 Astro 的极简静态博客，文章源文件来自本地 Markdown 归档。

## 本地开发

```bash
pnpm install
pnpm dev        # http://localhost:4321
pnpm build      # 输出 dist/
pnpm preview    # 预览构建结果
```

## 写文章

在 `src/content/posts/` 下新建 `.md` 文件，头部 frontmatter：

```yaml
---
title: "文章标题"
date: 2026-10-28
description: "一句话摘要"
tags: ["Android", "逆向"]
category: "技术"   # 或 "生活"
---

正文……
```

## 迁移脚本

`tools/migrate.py` 会把 `D:/AgnetClaw/csh_workspace/Article` 下的 Markdown 批量导入，
自动做这几件事：

- 排除 OpenSpec 文档、README、工程产物（results/files/backup）
- 同一篇文章的多版本去重（已发布 > 终稿 > 修订版 > 待发布 > 待审核 > 草稿）
- 生成 frontmatter（标题、日期、摘要、标签、分类）
- 本地图片复制到 `public/images/<slug>/`，失效引用转为 HTML 注释
- 输出 `migration-report.md`（含缺失图片清单）

```bash
python tools/migrate.py
```

## 部署

推送到 `main` 分支后，GitHub Actions 自动构建并发布到 GitHub Pages。

首次使用需在仓库 **Settings → Pages → Source** 选择 **GitHub Actions**。
