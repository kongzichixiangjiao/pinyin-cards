# -*- coding: utf-8 -*-
"""公共绘制工具：字体、emoji 渲染、汉字/拼音排版"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

EMOJI_FONT = "/System/Library/Fonts/Apple Color Emoji.ttc"
EMOJI_STRIKE = 160  # Apple Color Emoji 只允许 96 / 160 两档位图尺寸

FONTS = {
    "song_bold": ("/System/Library/Fonts/Supplemental/Songti.ttc", 1),
    "song_reg":  ("/System/Library/Fonts/Supplemental/Songti.ttc", 6),
    "sans":      ("/Users/afeng/Library/Fonts/Source_Han_Sans_SC_Regular.otf", 0),
    "sans_bold": ("/Users/afeng/Library/Fonts/Source_Han_Sans_SC_Bold.otf", 0),
    # 字母卡专用：Chalkboard SE 是单层 a / 单层 g，最像老师手写体
    "letter":    ("/System/Library/Fonts/Supplemental/ChalkboardSE.ttc", 0),
}

INK = (31, 45, 61)          # 主文字 深墨
INK_SOFT = (122, 143, 166)  # 拼音 灰蓝
GRID = (183, 214, 236)      # 四线三格
BORDER = (156, 200, 232)    # 卡片描边
BORDER_SOFT = (226, 240, 250)
ACCENT = (47, 124, 190)     # 强调蓝

_font_cache = {}


def font(key, size):
    key2 = (key, size)
    if key2 not in _font_cache:
        path, idx = FONTS[key]
        _font_cache[key2] = ImageFont.truetype(path, size, index=idx)
    return _font_cache[key2]


def render_emoji(ch, target_h):
    """把 emoji 渲成透明 PNG 图块；该 emoji 不存在时返回 None"""
    if not ch:
        return None
    try:
        f = ImageFont.truetype(EMOJI_FONT, EMOJI_STRIKE)
        canvas = Image.new("RGBA", (EMOJI_STRIKE * 2, EMOJI_STRIKE * 2), (0, 0, 0, 0))
        ImageDraw.Draw(canvas).text(
            (EMOJI_STRIKE // 2, EMOJI_STRIKE // 2), ch, font=f, embedded_color=True
        )
        bb = canvas.getbbox()
        if not bb:
            return None
        im = canvas.crop(bb)
        # 清掉 Apple Color Emoji 自带的极淡底色（alpha<12），否则白卡上会出现灰方块
        im.putalpha(im.split()[3].point(lambda v: 0 if v < 12 else v))
        scale = target_h / im.height
        im = im.resize((max(1, round(im.width * scale)), target_h), Image.LANCZOS)
        return im.filter(ImageFilter.UnsharpMask(radius=2, percent=90, threshold=2))
    except Exception:
        return None


def pick_image(word, target_h):
    """按 img -> emoji -> fallback -> 占位图 的顺序拿卡片主图，返回 (PIL图, 来源标记)"""
    if word.get("img") and os.path.exists(word["img"]):
        im = Image.open(word["img"]).convert("RGBA")
        im.thumbnail((target_h, target_h), Image.LANCZOS)
        return im, "img"
    for key in ("emoji", "fallback"):
        im = render_emoji(word.get(key, ""), target_h)
        if im is not None:
            return im, "emoji" if key == "emoji" else "fallback"
    return placeholder_image(target_h), "placeholder"


def placeholder_image(target_h):
    """没有配图时的占位图：虚线框 + 简笔照片图标 + 待配图"""
    s = target_h
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.10),
                        fill=(247, 251, 254, 255), outline=BORDER + (255,), width=max(2, s // 60))
    # 简笔照片图标
    w = int(s * 0.52)
    bx0, by0 = (s - w) // 2, int(s * 0.26)
    d.rounded_rectangle([bx0, by0, bx0 + w, by0 + int(w * 0.74)], radius=w // 12,
                        outline=(176, 203, 224, 255), width=max(2, s // 70))
    d.ellipse([bx0 + w * 0.14, by0 + w * 0.12, bx0 + w * 0.3, by0 + w * 0.28],
              fill=(176, 203, 224, 255))
    d.polygon([(bx0 + w * 0.08, by0 + w * 0.72), (bx0 + w * 0.42, by0 + w * 0.3),
               (bx0 + w * 0.72, by0 + w * 0.72)], fill=(176, 203, 224, 255))
    d.polygon([(bx0 + w * 0.52, by0 + w * 0.72), (bx0 + w * 0.7, by0 + w * 0.5),
               (bx0 + w * 0.92, by0 + w * 0.72)], fill=(176, 203, 224, 255))
    d.text((s / 2, int(s * 0.84)), "待配图", font=font("sans", max(14, int(s * 0.11))),
           fill=(168, 190, 209), anchor="mm")
    return im


def fit_font(key, text, max_w, start_size, min_size=20):
    """按最大宽度自动缩字号"""
    size = start_size
    while size > min_size:
        f = font(key, size)
        if ImageDraw.Draw(Image.new("RGB", (10, 10))).textlength(text, font=f) <= max_w:
            return f
        size -= 2
    return font(key, min_size)


def rounded_border(draw, box, radius, color, width):
    draw.rounded_rectangle(box, radius=radius, outline=color, width=width)
