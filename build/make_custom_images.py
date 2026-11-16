# -*- coding: utf-8 -*-
"""给三个没有 emoji 的词语画简笔配图，输出到 assets/custom/

  236 鸵鸟 / 238 螳螂 / 245 蜻蜓

输出 512×512 RGBA（透明底），build_cards.py 会缩到 272 自动套进卡片。
风格刻意做成「扁平几何简笔」：纯色块 + 圆角，和卡片本身的浅蓝底协调。

用法： python3 build/make_custom_images.py [--force]
"""
import math
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "custom")
S = 512


def ellipse_rot(size, box, angle, fill, outline=None, width=3):
    """画一个能旋转的椭圆图层，用来做昆虫翅膀/花瓣"""
    w = int(size[0] * 1.6)
    h = int(size[1] * 1.6)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = w // 2, h // 2
    x0, y0, x1, y1 = box
    d.ellipse([cx + x0, cy + y0, cx + x1, cy + y1], fill=fill, outline=outline,
              width=width)
    return layer.rotate(angle, expand=True, resample=Image.BICUBIC)


def paste_center(base, layer, cx, cy):
    base.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))


# ---------------------------------------------------------------- 蜻蜓
def dragonfly():
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    wing = (206, 232, 245, 190)
    edge = (128, 178, 208, 235)

    # 四片翅膀：两长两短，左右各一对
    for ang, box, cx, cy in (
        (28, (-46, -150, 46, 10), 216, 236),
        (-28, (-46, -150, 46, 10), 296, 236),
        (48, (-40, -110, 40, 10), 208, 252),
        (-48, (-40, -110, 40, 10), 304, 252),
    ):
        paste_center(im, ellipse_rot((92, 320), box, ang, wing, edge, 4), cx, cy)

    # 腹部：由粗到细
    body = (74, 160, 132, 255)
    d.polygon([(238, 262), (274, 262), (268, 430), (244, 430)], fill=body)
    for y in range(276, 430, 26):                      # 环节
        d.line([(240, y), (272, y)], fill=(52, 128, 104, 255), width=4)

    # 胸
    d.ellipse([226, 208, 286, 270], fill=(88, 176, 146, 255))
    # 头 + 大复眼
    d.ellipse([228, 158, 284, 214], fill=(96, 186, 154, 255))
    for ex in (243, 269):
        d.ellipse([ex - 15, 172, ex + 15, 202], fill=(232, 250, 244, 255),
                  outline=(52, 128, 104, 255), width=3)
        d.ellipse([ex - 6, 182, ex + 6, 194], fill=(40, 60, 60, 255))
    # 触角
    for dx, sgn in ((0, -1), (0, 1)):
        d.line([(256 + sgn * 12, 166), (256 + sgn * 44, 132)], fill=(52, 128, 104, 255), width=4)

    # 六条细腿
    for y, w in ((300, 44), (322, 52), (344, 44)):
        d.line([(232, y), (232 - w, y + 34)], fill=(52, 128, 104, 255), width=5)
        d.line([(280, y), (280 + w, y + 34)], fill=(52, 128, 104, 255), width=5)
    return im


# ---------------------------------------------------------------- 鸵鸟
def ostrich():
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    dark = (74, 68, 66, 255)
    legc = (226, 176, 148, 255)
    beakc = (240, 168, 78, 255)

    # 腿（先画，压在身体下面）
    for x0, x1 in ((238, 228), (268, 282)):
        d.line([(x0, 372), (x1, 470)], fill=legc, width=13)
        d.line([(x1 - 16, 470), (x1 + 12, 470)], fill=legc, width=11)
    d.ellipse([222, 452, 246, 476], fill=legc)
    d.ellipse([272, 452, 296, 476], fill=legc)

    # 尾羽（小扇形，收在身体右后方）
    for ang, cx, cy in ((26, 316, 330), (10, 326, 344), (-6, 318, 358)):
        paste_center(im, ellipse_rot((40, 74), (-20, -37, 20, 37), ang,
                                     (248, 246, 242, 255), (198, 188, 180, 255), 3), cx, cy)

    # 身体
    d.ellipse([168, 298, 334, 418], fill=dark)
    # 翅膀高光（贴身体左侧，做出体积）
    d.ellipse([186, 318, 286, 392], fill=(96, 88, 84, 255))
    d.ellipse([196, 330, 268, 380], fill=(112, 102, 96, 255))

    # 长脖子（两段折线 + 圆头）
    d.line([(252, 322), (234, 256), (252, 196), (266, 160)], fill=dark, width=24, joint="curve")
    d.ellipse([246, 130, 288, 172], fill=dark)
    # 嘴
    d.polygon([(286, 143), (324, 153), (286, 163)], fill=beakc)
    # 眼
    d.ellipse([258, 140, 276, 158], fill=(250, 250, 250, 255))
    d.ellipse([263, 145, 272, 154], fill=(30, 30, 30, 255))
    return im


# ---------------------------------------------------------------- 螳螂
def mantis():
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    green = (124, 184, 92, 255)
    dark = (78, 132, 60, 255)
    light = (170, 214, 132, 255)

    # 后腿 / 中腿（先画，从腹侧往外下方伸）
    for y, dx in ((334, 58), (356, 50)):
        for x0, sgn in ((244, -1), (268, 1)):
            d.line([(x0, y), (x0 + sgn * dx, y + 40)], fill=dark, width=7)
            d.line([(x0 + sgn * dx, y + 40), (x0 + sgn * (dx + 16), y + 62)], fill=dark, width=6)

    # 腹部（细长，尾端尖）
    d.polygon([(236, 300), (276, 300), (266, 452), (246, 452)], fill=green)
    for y in range(316, 452, 28):
        d.line([(242, y), (270, y)], fill=dark, width=3)

    # 翅膀：两片叶形盖在背上
    for sgn in (-1, 1):
        d.polygon([(256 + sgn * 6, 258), (256 + sgn * 44, 320), (256 + sgn * 8, 302)],
                  fill=light, outline=dark)
    d.ellipse([230, 286, 282, 332], fill=light, outline=dark, width=3)

    # 胸 + 头
    d.ellipse([228, 214, 284, 292], fill=green)
    d.ellipse([230, 176, 282, 228], fill=green)

    # 复眼
    for ex in (244, 268):
        d.ellipse([ex - 13, 184, ex + 13, 210], fill=(238, 250, 232, 255),
                  outline=dark, width=3)
        d.ellipse([ex - 5, 194, ex + 5, 204], fill=(42, 48, 42, 255))
    # 触角
    for sgn in (-1, 1):
        d.line([(256 + sgn * 16, 182), (256 + sgn * 52, 140)], fill=dark, width=4)

    # 两把大刀（前足：折起来举在胸前，带锯齿）
    for sgn in (-1, 1):
        sh = (256 + sgn * 30, 252)          # 肩
        elbow = (256 + sgn * 74, 236)       # 上臂外折
        tip = (256 + sgn * 46, 318)         # 下折的前足尖
        d.line([sh, elbow], fill=green, width=15)
        d.line([elbow, tip], fill=green, width=13)
        d.ellipse([elbow[0] - 9, elbow[1] - 9, elbow[0] + 9, elbow[1] + 9], fill=green)
        # 锯齿
        for i in range(4):
            t = i / 4
            px = elbow[0] + (tip[0] - elbow[0]) * t
            py = elbow[1] + (tip[1] - elbow[1]) * t
            d.line([(px, py), (px + sgn * 13, py - 3)], fill=dark, width=3)
    return im


def save(name, img, force):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name + ".png")
    if os.path.exists(p) and not force:
        print(f"跳过（已存在）{p}")
        return
    img.save(p)
    print(f"写出 {p}  {img.size[0]}×{img.size[1]}")


if __name__ == "__main__":
    force = "--force" in sys.argv
    save("236", ostrich(), force)
    save("238", mantis(), force)
    save("245", dragonfly(), force)
