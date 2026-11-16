#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打印每个邀请码对应的专属链接，方便一个个发。

用法：
  python3 build/invite_links.py https://<用户名>.github.io/<仓库>/
  python3 build/invite_links.py https://xxx.github.io/pinyin/ --md   # 输出 Markdown 表格
"""
import json
import os
import sys
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INV = os.path.join(ROOT, "data", "invites.json")

args = [a for a in sys.argv[1:] if not a.startswith("--")]
base = (args[0] if args else "").strip()
if not base:
    sys.exit(__doc__)
if not base.endswith("/"):
    base += "/"

with open(INV, encoding="utf-8") as f:
    inv = json.load(f)

if not inv.get("enabled", True):
    print("⚠️  data/invites.json 里 enabled=false，现在没有邀请码门")

codes = inv.get("codes", [])
md = "--md" in sys.argv

if md:
    print("| # | 备注 | 邀请码 | 专属链接 |")
    print("|---|---|---|---|")
    for i, c in enumerate(codes, 1):
        print(f"| {i} | {c.get('note','')} | `{c['code']}` | {base}?k={c['code']} |")
else:
    print(f"站点：{base}\n")
    for i, c in enumerate(codes, 1):
        print(f"{i:>2}. {c.get('note',''):<10} {c['code']}   {base}?k={quote(c['code'])}")
    print(f"\n共 {len(codes)} 个码。直接发链接，家长点开就进，不用手输；")
    print("也可以只发 6 位码，让他自己在首页输入。")
