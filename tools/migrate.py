#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 Article 目录下的 Markdown 迁移到 Astro content/posts，自动去重、生成 frontmatter、处理图片。"""
import os
import re
import sys
import shutil
import hashlib
from collections import defaultdict
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

SRC_ROOT = r"D:/AgnetClaw/csh_workspace/Article"
DST_POSTS = r"D:/AgnetClaw/chenshuhui-blog/src/content/posts"
DST_PUBLIC_IMG = r"D:/AgnetClaw/chenshuhui-blog/public/images"
REPORT_PATH = r"D:/AgnetClaw/chenshuhui-blog/migration-report.md"

EXCLUDE_DIRS = {".claude", ".amazonq", "openspec", "node_modules", ".git", ".obsidian",
                "operations", "brainstorming", "results", "files", "backup", "课程原始资料", "images", "images_desensitized"}
EXCLUDE_NAMES = {
    "AGENTS.md", "CLAUDE.md", "README.md", "tasks.md", "spec.md",
    "proposal.md", "design.md", "project.md", "写文章工作流.md", "写作工作流.md",
    "article-template.md", "article-to-publish.md", "CHART_EXAMPLES.md",
    "config_files.md", "tool_list.md", "findings_notes.md", "device.md",
}
EXCLUDE_NAME_PREFIX = ("写作工作流",)
# 不是面向读者的文章：工程规格、审校说明、素材记录等
EXCLUDE_TITLE_KEYWORDS = (
    "工程规格", "审核修订", "证据说明", "事实笔记", "文章模板", "图表示例",
    "Instructions", "FINDINGS", "测量设备与构建环境", "真机验证记录", "验证记录",
    # 涉及公司项目/内部文档，不上公开博客
    "系列规划", "NativeGameUrl", "大神云游戏", "云游戏联调痛点", "云端串图",
    "APK Signing Block V2", "Unifix", "自主度",
)

# 版本优先级：目录/文件名命中的关键词权重
PRIORITY = [
    (100, ["已发布"]),
    (90, ["终稿", "终版", "定稿"]),
    (80, ["修订版"]),
    (70, ["待发布"]),
    (60, ["待审核"]),
    (50, ["草稿"]),
    (10, []),
]


def collect():
    out = []
    for dp, dns, fns in os.walk(SRC_ROOT):
        dns[:] = [d for d in dns if d not in EXCLUDE_DIRS]
        for fn in fns:
            if not fn.lower().endswith(".md"):
                continue
            if fn in EXCLUDE_NAMES or fn.startswith(EXCLUDE_NAME_PREFIX):
                continue
            out.append(os.path.join(dp, fn))
    return out


def read(path):
    with open(path, "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8", errors="ignore").lstrip("\ufeff")
    return text.replace("\r\n", "\n")


def strip_frontmatter(text):
    """返回 (frontmatter dict-ish raw, body)"""
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if not m:
        return {}, text
    fm_raw, body = m.group(1), text[m.end():]
    fm = {}
    for line in fm_raw.split("\n"):
        mm = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if mm:
            fm[mm.group(1)] = mm.group(2).strip().strip('"').strip("'")
    return fm, body


def get_title(body, path):
    m = re.search(r"^#\s+(.+)$", body, re.M)
    if m:
        return m.group(1).strip()
    return os.path.splitext(os.path.basename(path))[0]


def norm_title(title):
    t = title
    t = re.sub(r"[(（]\d+[)）]\s*$", "", t)
    t = re.sub(r"[-_ ]*(修订版|终稿|终版|定稿|校对版|优化版|微信校对版|微信终版|掘金校对版|掘金终版|最终版|发布版|脱敏版|备份版)\s*", "", t)
    # 归一化：下划线/连字符/空格/标点全部忽略，避免同一篇因文件名差异被当成两篇
    t = re.sub(r"[\s_\-—–·:：,，。！？!?、/\\|()（）\[\]【】\"“”'‘’]+", "", t)
    return t.lower()


def priority_of(path):
    p = path.replace("\\", "/")
    best = 10
    for score, kws in PRIORITY:
        if any(k in p for k in kws):
            best = max(best, score)
    return best


def slugify(name):
    s = name.strip()
    # 只保留中文、字母、数字，其余（标点/空格/符号）统一转连字符，避免 URL 特殊字符
    s = re.sub(r"[^一-鿿A-Za-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s)
    s = s.strip("-.")
    return s[:80] or "untitled"


def guess_date(fm, path):
    for key in ("date", "updated"):
        v = fm.get(key, "")
        m = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", v)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                pass
    return datetime.fromtimestamp(os.path.getmtime(path))


def guess_tags(title, path):
    tags = []
    p = path.replace("\\", "/")
    mapping = [
        ("移动安全逆向", ["逆向", "Android"]),
        ("rea逆向", ["逆向", "REA"]),
        ("性能优化", ["性能优化", "Android"]),
        ("Tinker", ["插件化", "Android"]),
        ("插件化", ["插件化", "Android"]),
        ("CC-Switch", ["工具", "Claude Code"]),
        ("Ai实践", ["AI", "Agent"]),
        ("agent", ["AI", "Agent"]),
        ("生活中的经济学", ["经济学"]),
        ("CVD", ["云游戏"]),
        ("云游戏", ["云游戏"]),
        ("OpenClaw", ["OpenClaw"]),
    ]
    for key, ts in mapping:
        if key.lower() in p.lower():
            for t in ts:
                if t not in tags:
                    tags.append(t)
    for kw, tag in [("Claude Code", "Claude Code"), ("Android", "Android"), ("Compose", "Compose"),
                    ("逆向", "逆向"), ("插件化", "插件化"), ("性能", "性能优化"),
                    ("AI", "AI"), ("Agent", "Agent"), ("经济学", "经济学")]:
        if kw.lower() in title.lower() and tag not in tags:
            tags.append(tag)
    return tags[:5]


def make_description(body):
    # 跳过标题、引用、代码块、HTML 注释
    lines = []
    in_code = False
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not s or s.startswith(("#", ">", "<!--", "|", "!", "<", "- ", "* ", "---")):
            continue
        lines.append(s)
        if len("".join(lines)) > 90:
            break
    desc = " ".join(lines)
    desc = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", desc)
    desc = re.sub(r"[*_`]", "", desc)
    desc = desc.strip()
    if len(desc) > 100:
        # 优先在句末标点处截断，避免半句话
        cut = max(desc.rfind(p, 0, 100) for p in "。！？.!?")
        desc = desc[: cut + 1] if cut > 40 else desc[:100]
    return desc


def handle_images(body, slug, report):
    """返回处理后的正文；缺失图替换为注释并记录。"""
    missing = []
    copied = 0

    def repl(m):
        nonlocal copied
        alt, target = m.group(1), m.group(2).strip().strip("<>")
        if target.startswith(("http://", "https://")):
            return m.group(0)
        if target.startswith("data:"):
            return m.group(0)
        # Windows 绝对路径
        if re.match(r"^[A-Za-z]:[\\/]", target):
            missing.append(target)
            return f"<!-- 原图缺失: {target} -->"
        # 相对路径
        base = os.path.dirname(report["_src"])
        cand = os.path.normpath(os.path.join(base, target))
        if os.path.isfile(cand):
            dst_dir = os.path.join(DST_PUBLIC_IMG, slug)
            os.makedirs(dst_dir, exist_ok=True)
            fname = os.path.basename(cand)
            shutil.copy2(cand, os.path.join(dst_dir, fname))
            copied += 1
            return f"![{alt}](/images/{slug}/{fname})"
        missing.append(target)
        return f"<!-- 原图缺失: {target} -->"

    new = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", repl, body)
    return new, missing, copied


def main():
    os.makedirs(DST_POSTS, exist_ok=True)
    os.makedirs(DST_PUBLIC_IMG, exist_ok=True)
    # 清空上次生成的 md，避免残留旧文章
    for fn in os.listdir(DST_POSTS):
        if fn.endswith(".md"):
            os.remove(os.path.join(DST_POSTS, fn))

    files = collect()
    items = []
    for path in files:
        text = read(path)
        fm, body = strip_frontmatter(text)
        title = get_title(body, path)
        if title.strip() and len(text) >= 500:
            if any(k.lower() in title.lower() for k in EXCLUDE_TITLE_KEYWORDS):
                continue
            items.append({
                "_src": path, "fm": fm, "body": body, "title": title,
                "norm": norm_title(title), "prio": priority_of(path),
                "size": len(text),
            })

    groups = defaultdict(list)
    for it in items:
        groups[it["norm"]].append(it)

    chosen = []
    dup_groups = 0
    for k, v in groups.items():
        if len(v) > 1:
            dup_groups += 1
        v.sort(key=lambda x: (x["prio"], x["size"]), reverse=True)
        chosen.append(v[0])

    # 按日期倒序写出
    used_slugs = {}
    report_lines = []
    missing_total = 0
    copied_total = 0
    slug_map = []

    for it in sorted(chosen, key=lambda x: guess_date(x["fm"], x["_src"]), reverse=True):
        title = it["title"].strip()
        slug = slugify(title)
        if slug in used_slugs:
            slug = f"{slug}-{hashlib.md5(it['_src'].encode()).hexdigest()[:6]}"
        used_slugs[slug] = True

        date = guess_date(it["fm"], it["_src"])
        tags = guess_tags(title, it["_src"])
        desc = make_description(it["body"])
        category = "生活" if "/Life/" in it["_src"].replace("\\", "/") else "技术"

        report = {"_src": it["_src"]}
        body, missing, copied = handle_images(it["body"], slug, report)
        missing_total += len(missing)
        copied_total += copied

        # 去掉正文开头的 H1（模板已渲染标题）
        body = re.sub(r"^\s*#\s+.+\n+", "", body, count=1)
        # 去掉封面提示注释块
        body = re.sub(r"<!--\s*COVER_PROMPT_START.*?COVER_PROMPT_END\s*-->", "", body, flags=re.S)
        body = re.sub(r"\n{4,}", "\n\n\n", body).strip()

        fm_lines = [
            "---",
            f'title: "{title.replace(chr(34), chr(39))}"',
            f"date: {date.strftime('%Y-%m-%d')}",
            f'description: "{desc.replace(chr(34), chr(39))}"',
            f"tags: [{', '.join(repr(t) for t in tags)}]",
            f'category: "{category}"',
            "---",
            "",
        ]
        out_path = os.path.join(DST_POSTS, f"{slug}.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(fm_lines) + body + "\n")

        slug_map.append((title, slug, category, date.strftime("%Y-%m-%d"), len(missing), it["_src"]))
        if missing:
            report_lines.append(f"### {title}\n\n来源: `{it['_src']}`\n\n缺失图片 {len(missing)} 张:\n" +
                                "\n".join(f"- `{m}`" for m in missing) + "\n")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# 博客迁移报告\n\n")
        f.write(f"- 扫描 Markdown: {len(files)}\n")
        f.write(f"- 去重后文章: {len(chosen)}\n")
        f.write(f"- 合并重复组: {dup_groups}\n")
        f.write(f"- 复制本地图片: {copied_total}\n")
        f.write(f"- 缺失图片引用: {missing_total}\n\n")
        f.write("## 文章清单\n\n| 标题 | slug | 分类 | 日期 | 缺图 |\n|---|---|---|---|---|\n")
        for t, s, c, d, m, _ in slug_map:
            f.write(f"| {t} | `{s}` | {c} | {d} | {m} |\n")
        f.write("\n## 缺失图片明细\n\n")
        f.write("\n".join(report_lines) if report_lines else "无\n")

    print(f"扫描 {len(files)} 个 md → 去重后 {len(chosen)} 篇（合并 {dup_groups} 组重复）")
    print(f"复制本地图片 {copied_total} 张，缺失引用 {missing_total} 处")
    print(f"报告: {REPORT_PATH}")


if __name__ == "__main__":
    main()
