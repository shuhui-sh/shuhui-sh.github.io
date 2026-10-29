#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从掘金抓取已发布文章（正文 + 图片），转成 Markdown 写入 Astro content/posts。"""
import os
import re
import json
import time
import subprocess
import sys
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding='utf-8')
from bs4 import BeautifulSoup
from markdownify import markdownify as md

ROOT = "D:/AgnetClaw/chenshuhui-blog"
TMP = os.path.join(ROOT, ".tmp", "juejin")
POSTS = os.path.join(ROOT, "src", "content", "posts")
IMGS = os.path.join(ROOT, "public", "images")
LIST = os.path.join(ROOT, ".tmp", "jj_list.json")

os.makedirs(TMP, exist_ok=True)
os.makedirs(IMGS, exist_ok=True)


def curl(args, timeout="40"):
    return subprocess.run(["curl", "-s", "-L", "--max-time", timeout] + args,
                          capture_output=True).stdout


def slugify(name):
    s = re.sub(r"[^一-鿿A-Za-z0-9]+", "-", name.strip())
    s = re.sub(r"-{2,}", "-", s).strip("-.")
    return s[:80] or "untitled"


def fetch_page(aid, retries=5):
    path = os.path.join(TMP, f"{aid}.html")
    if os.path.exists(path) and os.path.getsize(path) > 50000:
        cached = open(path, encoding="utf-8", errors="ignore").read()
        if "article-viewer" in cached:
            return cached
    for attempt in range(retries):
        html = curl([f"https://juejin.cn/post/{aid}",
                     "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
                     "-H", "Accept-Language: zh-CN,zh;q=0.9",
                     "-H", "Referer: https://juejin.cn/"]).decode("utf-8", errors="ignore")
        if "article-viewer" in html and len(html) > 50000:
            open(path, "w", encoding="utf-8").write(html)
            return html
        print(f"  · 风控/空页，第 {attempt+1} 次重试…")
        time.sleep(6 + attempt * 4)
    open(path, "w", encoding="utf-8").write(html)
    return html


def download_image(url, slug, idx):
    ext = os.path.splitext(urlparse(url).path)[1] or ".png"
    if ext.lower() not in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"):
        ext = ".png"
    name = f"{idx:02d}{ext}"
    out_dir = os.path.join(IMGS, slug)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, name)
    if not os.path.exists(out) or os.path.getsize(out) < 500:
        curl([url, "-o", out, "-H", "Referer: https://juejin.cn/",
              "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"])
    return out if os.path.exists(out) and os.path.getsize(out) > 500 else None


def code_lang(el):
    cls = " ".join(el.get("class", []))
    m = re.search(r"language-([\w-]+)", cls)
    return m.group(1) if m else None


def process(art):
    aid, title = art["id"], art["title"]
    slug = slugify(title)
    html = fetch_page(aid)
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one(".article-viewer")
    if not body:
        return None, "无正文容器"

    # 去掉干扰元素
    for sel in [".code-block-extension-header", ".copy-code-btn", ".article-end",
                ".follow-btn", "script", "style"]:
        for el in body.select(sel):
            el.decompose()

    # 图片本地化
    saved, missing = 0, 0
    for i, img in enumerate(body.find_all("img"), 1):
        src = img.get("data-src") or img.get("src") or ""
        if not src.startswith("http"):
            continue
        local = download_image(src, slug, i)
        if local:
            rel = f"/images/{slug}/{os.path.basename(local)}"
            img["src"] = rel
            if "data-src" in img.attrs:
                del img["data-src"]
            saved += 1
        else:
            missing += 1
            img.replace_with(soup.new_string(""))

    # 抓标签
    tags = [a.get_text(strip=True) for a in soup.select('a[href*="/tag/"]')][:5]
    tags = [t for t in dict.fromkeys(tags) if t]

    md_text = md(str(body), heading_style="ATX", code_language_callback=code_lang,
                 bullets="-", strip=["a"] if False else None)
    # markdownify 会保留 a 标签；去掉行首多余空行
    md_text = re.sub(r"\n{4,}", "\n\n\n", md_text).strip()

    return {
        "slug": slug, "title": title, "content": md_text,
        "tags": tags, "saved": saved, "missing": missing,
    }, None


def main():
    arts = json.load(open(LIST, encoding="utf-8"))
    report, ok = [], 0
    for a in arts:
        res, err = process(a)
        if err:
            print(f"✗ {a['title'][:40]} — {err}")
            report.append((a["title"], "FAILED", err))
            continue
        title = res["title"].replace('"', "'")
        desc = (a.get("brief") or "").replace('"', "'")[:110]
        date = __import__("datetime").datetime.fromtimestamp(a["ctime"]).strftime("%Y-%m-%d")
        tags_yaml = ", ".join(repr(t) for t in res["tags"]) if res["tags"] else ""
        fm = [
            "---", f'title: "{title}"', f"date: {date}",
            f'description: "{desc}"', f"tags: [{tags_yaml}]",
            'category: "技术"', f'source: "https://juejin.cn/post/{a["id"]}"', "---", "",
        ]
        path = os.path.join(POSTS, f"{res['slug']}.md")
        open(path, "w", encoding="utf-8").write("\n".join(fm) + res["content"] + "\n")
        ok += 1
        print(f"✓ {a['title'][:44]:<46} 图 {res['saved']} 存 / {res['missing']} 缺")
        report.append((a["title"], "OK", f"图{res['saved']}/{res['missing']}"))

    print(f"\n完成 {ok}/{len(arts)} 篇")
    json.dump(report, open(os.path.join(ROOT, ".tmp", "juejin_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
