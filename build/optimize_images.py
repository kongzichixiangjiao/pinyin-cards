# -*- coding: utf-8 -*-
"""卡片图瘦身：PNG(900×900, ~100KB) -> WebP 缩略图 + 展示图

产出：
  assets/cards/thumb/007_card.webp   320×320  列表格子用（约 8~12 KB）
  assets/cards/web/007_card.webp     720×720  单卡大图用（约 25~40 KB）
原 PNG 全部保留，出片/打印流程继续用 png，不受影响。

用法：
  python3 build/optimize_images.py            # 增量，只处理缺的/过期的
  python3 build/optimize_images.py --force    # 全部重压
"""
import glob
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "cards")
THUMB = os.path.join(SRC, "thumb")
WEB = os.path.join(SRC, "web")

THUMB_SIZE = 320
WEB_SIZE = 720
THUMB_Q = 76
WEB_Q = 82


def stale(src, out, force):
    if force or not os.path.exists(out):
        return True
    return os.path.getmtime(out) < os.path.getmtime(src)


def main():
    force = "--force" in sys.argv
    os.makedirs(THUMB, exist_ok=True)
    os.makedirs(WEB, exist_ok=True)

    files = sorted(glob.glob(os.path.join(SRC, "*.png")))
    if not files:
        sys.exit(f"没找到卡片图: {SRC}")

    n_thumb = n_web = 0
    src_bytes = 0
    for p in files:
        name = os.path.splitext(os.path.basename(p))[0]
        src_bytes += os.path.getsize(p)
        with Image.open(p) as im:
            im = im.convert("RGB")

            t_out = os.path.join(THUMB, name + ".webp")
            if stale(p, t_out, force):
                im.resize((THUMB_SIZE, THUMB_SIZE), Image.LANCZOS).save(
                    t_out, "WEBP", quality=THUMB_Q, method=6
                )
                n_thumb += 1

            w_out = os.path.join(WEB, name + ".webp")
            if stale(p, w_out, force):
                im.resize((WEB_SIZE, WEB_SIZE), Image.LANCZOS).save(
                    w_out, "WEBP", quality=WEB_Q, method=6
                )
                n_web += 1

    t_bytes = sum(os.path.getsize(p) for p in glob.glob(os.path.join(THUMB, "*.webp")))
    w_bytes = sum(os.path.getsize(p) for p in glob.glob(os.path.join(WEB, "*.webp")))
    print(f"原 PNG : {len(files)} 张 {src_bytes/1e6:.1f} MB")
    print(f"缩略图 : {len(files)} 张 {t_bytes/1e6:.1f} MB  (本次新压 {n_thumb})")
    print(f"展示图 : {len(files)} 张 {w_bytes/1e6:.1f} MB  (本次新压 {n_web})")

    # 清掉源图已不存在的残留（改 id / 删单元之后会留下孤儿）
    alive = {os.path.splitext(os.path.basename(p))[0] for p in files}
    orphans = 0
    for d in (THUMB, WEB):
        for p in glob.glob(os.path.join(d, "*.webp")):
            if os.path.splitext(os.path.basename(p))[0] not in alive:
                os.remove(p)
                orphans += 1
    if orphans:
        print(f"清理残留: {orphans} 个 webp")


if __name__ == "__main__":
    main()
