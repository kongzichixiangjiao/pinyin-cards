# -*- coding: utf-8 -*-
"""curriculum.json -> 卡片图（带答案 / 空白两版）+ 词语 A4 小纸条

支持的卡片类型（按 group.kind 分派）：
  letter   单个拼音：配图 + 大字母 + 呼读音 + 口诀
  blend    拼读：配图 + 拼音式（b — à → bà）+ 例词
  word     词语：图 + 汉字 + 拼音
  sentence 句子：拼音行 + 汉字行（预留）
  story    故事页：同句子 + 页码（预留）
"""
import json, os
from PIL import Image, ImageDraw
from common import (font, pick_image, fit_font, INK, INK_SOFT, GRID, BORDER,
                    BORDER_SOFT, ACCENT)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "curriculum.json")
CARD_DIR = os.path.join(ROOT, "assets", "cards")
SHEET_DIR = os.path.join(ROOT, "assets", "sheet")
RED = (204, 68, 56)
HL_FILL = (228, 242, 253)   # 高亮底
HL_LINE = ACCENT            # 高亮描边
S = 900


def _resolve(item):
    """assets/custom/003.png 存在则优先用你自己的配图"""
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = os.path.join(ROOT, "assets", "custom", f"{int(item['id']):03d}{ext}")
        if os.path.exists(p):
            d = dict(item); d["img"] = p
            return d
    return item


def frame_border(d, size, k=1.0):
    d.rounded_rectangle([18 * k, 18 * k, size - 18 * k, size - 18 * k], radius=46 * k,
                        outline=BORDER, width=max(2, int(5 * k)))
    d.rounded_rectangle([34 * k, 34 * k, size - 34 * k, size - 34 * k], radius=36 * k,
                        outline=BORDER_SOFT, width=max(1, int(3 * k)))


def chip(d, text, size, k=1.0, x=58, y=60):
    lf = font("sans", int(30 * k))
    tw = d.textlength(text, font=lf)
    d.rounded_rectangle([x * k, y * k, x * k + tw + 34 * k, y * k + 52 * k],
                        radius=26 * k, fill=(236, 245, 252))
    d.text((x * k + 17 * k, y * k + 27 * k), text, font=lf, fill=ACCENT, anchor="lm")


def draw_letter(item, show_answer=True, size=S, chip_text="", hl=False):
    img = Image.new("RGB", (size, size), "white")
    d = ImageDraw.Draw(img)
    k = size / S
    frame_border(d, size, k)
    if chip_text:
        chip(d, chip_text, size, k)

    # 记忆图（拼音卡片一定要有图，孩子先看图再看字母）
    pic, _src = pick_image(_resolve(item), int(272 * k))
    img.paste(pic, ((size - pic.width) // 2, int(72 * k)), pic)

    # 字母面板
    panel = [150 * k, 378 * k, size - 150 * k, 636 * k]
    d.rounded_rectangle(panel, radius=40 * k,
                        fill=HL_FILL if hl else (250, 253, 255),
                        outline=HL_LINE if hl else (226, 240, 250),
                        width=max(3, int(7 * k)) if hl else max(2, int(4 * k)))
    txt = item["text"]
    lf = fit_font("letter", txt, (panel[2] - panel[0]) - 80 * k, int(200 * k), int(56 * k))
    d.text(((panel[0] + panel[2]) / 2, (panel[1] + panel[3]) / 2), txt,
           font=lf, fill=HL_LINE if hl else INK, anchor="mm")

    if show_answer:
        d.text((size / 2, 700 * k), item["pinyin"], font=font("sans_bold", int(86 * k)),
               fill=ACCENT, anchor="mm")
        if item.get("tip"):
            d.text((size / 2, 792 * k), item["tip"], font=font("sans", int(38 * k)),
                   fill=INK_SOFT, anchor="mm")
    else:
        rng = 300 * k
        top, bottom = 660 * k, 800 * k
        for i in range(4):
            y = top + (bottom - top) * i / 3
            d.line([size / 2 - rng, y, size / 2 + rng, y], fill=GRID, width=max(2, int(4 * k)))
    return img


def draw_blend(item, show_answer=True, size=S, chip_text="", hl=False):
    """拼读卡：图 + 拼音式（b — à → bà）+ 例词；练习版换成四线格"""
    img = Image.new("RGB", (size, size), "white")
    d = ImageDraw.Draw(img)
    k = size / S
    frame_border(d, size, k)
    if chip_text:
        chip(d, chip_text, size, k)

    pic, _src = pick_image(_resolve(item), int(288 * k))
    img.paste(pic, ((size - pic.width) // 2, int(92 * k)), pic)

    if show_answer:
        eq = item.get("blend") or item["pinyin"]
        ef = fit_font("sans_bold", eq, 800 * k, int(112 * k), int(56 * k))
        if hl:
            tw = d.textlength(eq, font=ef)
            d.rounded_rectangle([size / 2 - tw / 2 - 34 * k, 548 * k - 74 * k,
                                 size / 2 + tw / 2 + 34 * k, 548 * k + 74 * k],
                                radius=74 * k, fill=HL_FILL)
        d.text((size / 2, 548 * k), eq, font=ef, fill=HL_LINE if hl else INK, anchor="mm")
        d.text((size / 2, 690 * k), item["text"],
               font=fit_font("sans", item["text"], 720 * k, int(88 * k)),
               fill=(74, 96, 120), anchor="mm")
    else:
        tf = fit_font("song_bold", item["text"], 760 * k, int(120 * k), int(64 * k))
        if hl:
            tw = d.textlength(item["text"], font=tf)
            d.rounded_rectangle([size / 2 - tw / 2 - 30 * k, 540 * k - 82 * k,
                                 size / 2 + tw / 2 + 30 * k, 540 * k + 82 * k],
                                radius=82 * k, fill=HL_FILL)
        d.text((size / 2, 540 * k), item["text"], font=tf, fill=HL_LINE if hl else INK, anchor="mm")
        rng = 300 * k
        top, bottom = 640 * k, 800 * k
        for i in range(4):
            y = top + (bottom - top) * i / 3
            d.line([size / 2 - rng, y, size / 2 + rng, y], fill=GRID, width=max(2, int(4 * k)))
    return img


def draw_word(item, show_answer=True, size=S, chip_text="", hl=False):
    img = Image.new("RGB", (size, size), "white")
    d = ImageDraw.Draw(img)
    k = size / S
    frame_border(d, size, k)
    if chip_text:
        chip(d, chip_text, size, k)

    pic, _src = pick_image(_resolve(item), int(360 * k))
    img.paste(pic, ((size - pic.width) // 2, int(100 * k)), pic)

    hz = item["text"]
    hsize = {1: 200, 2: 170, 3: 140, 4: 114}.get(len(hz), 96)
    hf = font("song_bold", int(hsize * k))
    if hl:
        tw = d.textlength(hz, font=hf)
        d.rounded_rectangle([size / 2 - tw / 2 - 32 * k, 582 * k - hsize * 0.60 * k,
                             size / 2 + tw / 2 + 32 * k, 582 * k + hsize * 0.60 * k],
                            radius=30 * k, fill=HL_FILL)
    d.text((size / 2, 582 * k), hz, font=hf, fill=HL_LINE if hl else INK, anchor="mm")

    top, bottom = 702 * k, 852 * k
    if show_answer:
        p = item["pinyin"]
        pf = fit_font("sans", p, 760 * k, int(104 * k), int(46 * k))
        d.text((size / 2, 768 * k), p, font=pf, fill=INK_SOFT, anchor="mm")
    else:
        rng = 380 * k
        for i in range(4):
            y = top + (bottom - top) * i / 3
            d.line([size / 2 - rng, y, size / 2 + rng, y], fill=GRID, width=max(1, int(3 * k)))
    return img


def draw_line_item(item, show_answer=True, size=S, chip_text="", hl=False, page=None):
    """句子 / 故事页：上方浅蓝块放图（可选），下方拼音 + 汉字"""
    img = Image.new("RGB", (size, size), "white")
    d = ImageDraw.Draw(img)
    k = size / S
    frame_border(d, size, k)
    if chip_text:
        chip(d, chip_text, size, k)
    if item.get("emoji") or item.get("img"):
        pic, _ = pick_image(_resolve(item), int(300 * k))
        img.paste(pic, ((size - pic.width) // 2, int(140 * k)), pic)
    if show_answer:
        d.text((size / 2, 600 * k), item["pinyin"], font=fit_font("sans", item["pinyin"], 740 * k, int(72 * k)),
               fill=INK_SOFT, anchor="mm")
    d.text((size / 2, 720 * k), item["text"], font=fit_font("song_bold", item["text"], 760 * k, int(96 * k)),
           fill=INK, anchor="mm")
    if page:
        d.text((size - 60 * k, size - 60 * k), f"{page}", font=font("sans", int(30 * k)),
               fill=INK_SOFT, anchor="rm")
    return img


RENDERERS = {"letter": draw_letter, "blend": draw_blend, "word": draw_word,
             "sentence": draw_line_item, "story": draw_line_item}


def draw_card(item, kind, show_answer=True, size=S, chip_text="", hl=False):
    fn = RENDERERS.get(kind, draw_word)
    if kind in ("sentence", "story", "blend", "letter", "word"):
        return fn(item, show_answer, size, chip_text, hl)
    return fn(item, show_answer, size, chip_text, hl)


# ---------------- 输出 ----------------

def iter_groups(data):
    for lv in data["levels"]:
        for g in lv["groups"]:
            yield lv, g


def build_cards(data):
    os.makedirs(CARD_DIR, exist_ok=True)
    for f in os.listdir(CARD_DIR):
        if f.endswith(".png"):
            os.remove(os.path.join(CARD_DIR, f))
    n = 0
    warn = []
    for lv, g in iter_groups(data):
        for it in g["items"]:
            a = draw_card(it, g["kind"], True, S, g["name"])
            b = draw_card(it, g["kind"], False, S, g["name"])
            a.save(os.path.join(CARD_DIR, f"{it['id']:03d}_card.png"))
            b.save(os.path.join(CARD_DIR, f"{it['id']:03d}_blank.png"))
            n += 1
            if g["kind"] == "word":
                _pic, src = pick_image(_resolve(it), 160)
                if src != "emoji":
                    warn.append((it["id"], it["text"], src))
    return n, warn


def build_sheets(data):
    os.makedirs(SHEET_DIR, exist_ok=True)
    for f in os.listdir(SHEET_DIR):
        if f.endswith(".png"):
            os.remove(os.path.join(SHEET_DIR, f))
    page_size = (3508, 2480)
    n = 0
    for lv, g in iter_groups(data):
        if g["kind"] != "word":
            continue
        for mode, show in (("answer", True), ("exercise", False)):
            page = Image.new("RGB", page_size, "white")
            d = ImageDraw.Draw(page)
            d.rounded_rectangle([60, 60, page_size[0] - 60, page_size[1] - 60], radius=50,
                                outline=BORDER, width=6)
            parts = [("一年级(上)语文 看图写拼音", INK), ("小纸条", RED), (f"（{g['name']}）", ACCENT)]
            tf = font("song_bold", 96)
            total = sum(d.textlength(t, font=tf) for t, _ in parts)
            x = (page_size[0] - total) / 2
            for t, c in parts:
                d.text((x, 165), t, font=tf, fill=c, anchor="lm")
                x += d.textlength(t, font=tf)
            d.text((150, 268), "给下列汉字注音", font=font("sans", 52), fill=ACCENT, anchor="lm")
            d.text((page_size[0] - 150, 268), f"{len(g['items'])} 个词",
                   font=font("sans", 44), fill=INK_SOFT, anchor="rm")

            cell, gap, cols = 580, 46, 5
            x0 = (page_size[0] - (cols * cell + (cols - 1) * gap)) // 2
            y0 = 320
            for i, it in enumerate(g["items"]):
                r, c = divmod(i, cols)
                page.paste(draw_word(it, show, cell), (x0 + c * (cell + gap), y0 + r * (cell + gap)))

            fy = y0 + 3 * (cell + gap) + 10
            d.line([150, fy, page_size[0] - 150, fy], fill=BORDER_SOFT, width=3)
            d.text((150, fy + 78), "姓名：______________", font=font("sans", 52), fill=INK_SOFT, anchor="lm")
            d.text((1000, fy + 78), "日期：______________", font=font("sans", 52), fill=INK_SOFT, anchor="lm")
            page.save(os.path.join(SHEET_DIR, f"{g['id']}_{mode}.png"))
            n += 1
    return n


if __name__ == "__main__":
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)
    n, warn = build_cards(data)
    ns = build_sheets(data)
    print(f"卡片 -> {n} 个单元 × 2 版 = {n*2} 张")
    for i, t, src in warn:
        print(f"  ! #{i:03d} {t}: 主图来源 = {src}")
    print(f"小纸条 -> {ns} 张 A4")
