# -*- coding: utf-8 -*-
"""curriculum.json + template.html -> 单文件离线 index.html（数据内嵌，双击即开）"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "build", "template.html")
DATA = os.path.join(ROOT, "data", "curriculum.json")
OUT = os.path.join(ROOT, "index.html")

with open(DATA, encoding="utf-8") as f:
    data = json.load(f)

# 校验：id 全局唯一、按层级递增；字母/词语必填 text + pinyin
seen, last = set(), 0
for lv in data["levels"]:
    for g in lv["groups"]:
        for it in g["items"]:
            assert it["id"] not in seen, f"id 重复: {it['id']}"
            assert it["id"] > last, f"id 必须全局递增: {it['id']} 出现在 {last} 之后"
            seen.add(it["id"]); last = it["id"]
            assert it.get("text") and it.get("pinyin"), f"缺少 text/pinyin: {it}"
            assert os.path.exists(os.path.join(ROOT, "assets", "cards", f"{it['id']:03d}_card.png")), \
                f"缺卡片图: {it['id']:03d}"
            assert os.path.exists(os.path.join(ROOT, "assets", "audio", f"{it['id']:03d}_hz.mp3")), \
                f"缺音频: {it['id']:03d}"

with open(TPL, encoding="utf-8") as f:
    html = f.read()

html = html.replace("/*__DATA__*/{}", json.dumps(data, ensure_ascii=False, separators=(",", ":")))

# 邀请码：data/invites.json -> 前端白名单
INV = os.path.join(ROOT, "data", "invites.json")
gate_on, codes = False, []
if os.path.exists(INV):
    with open(INV, encoding="utf-8") as f:
        inv = json.load(f)
    gate_on = bool(inv.get("enabled", True))
    codes = [c["code"].strip().upper() for c in inv.get("codes", []) if c.get("code")]

html = html.replace("/*__GATE__*/false", f"/*__GATE__*/{'true' if gate_on else 'false'}")
html = html.replace("/*__CODES__*/[]", json.dumps(codes))

with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)

total = sum(len(g["items"]) for lv in data["levels"] for g in lv["groups"])
print(f"index.html -> {os.path.getsize(OUT)/1024:.0f} KB，{len(data['levels'])} 级 / {total} 个单元"
      + (f"，邀请码 {len(codes)} 个" if gate_on else "，未启用邀请码"))
for lv in data["levels"]:
    n = sum(len(g["items"]) for g in lv["groups"])
    print(f"  {lv['code']} {lv['name']}: {n} 个" + ("（待开发）" if not n else ""))
