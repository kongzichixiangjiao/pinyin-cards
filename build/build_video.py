# -*- coding: utf-8 -*-
"""卡片图 + 读音 -> 竖屏视频（每个单元一条 / 每组一条合集），全程本地 ffmpeg"""
import json, os, shutil, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter
from common import font, fit_font, INK_SOFT, ACCENT, BORDER
from build_cards import draw_card

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "curriculum.json")
AUDIO_DIR = os.path.join(ROOT, "assets", "audio")
FRAME_DIR = os.path.join(ROOT, "build", "frames")
TMP = os.path.join(ROOT, "build", "tmp")
V_SINGLE = os.path.join(ROOT, "output", "video", "single")
V_GROUP = os.path.join(ROOT, "output", "video", "group")
V_LEVEL = os.path.join(ROOT, "output", "video", "level")
V_ALL = os.path.join(ROOT, "output", "video", "all")
TITLE_DIR = os.path.join(ROOT, "build", "frames_title")

W, H = 1080, 1920
LEAD, GAP = 0.2, 0.35
MIN_DUR = 3.0


def sh(cmd):
    if isinstance(cmd, str):
        cmd = cmd.split()
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("ffmpeg 失败:\n%s\n%s" % (" ".join(cmd), p.stderr[-1200:]))
    return p


def dur_of(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    return float(out)


def vgrad(w, h, c1, c2):
    base = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        base.putpixel((0, y), tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
    return base.resize((w, h))


def paste_shadow(base, im, xy, blur=22, dy=10, alpha=46):
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([6, 6, im.width - 7, im.height - 7],
                                          radius=int(im.width * 0.05), fill=alpha)
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    layer.paste(Image.new("RGBA", im.size, (70, 100, 130, 255)), (xy[0], xy[1] + dy), mask)
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    base.paste(layer, (0, 0), layer)
    base.paste(im, xy)


def make_frame(item, kind, meta, group_name, pos, total, hl=False):
    img = vgrad(W, H, (232, 242, 251), (250, 252, 254))
    d = ImageDraw.Draw(img)
    d.text((W / 2, 120), meta["title"], font=font("sans", 46), fill=ACCENT, anchor="mm")
    d.text((W / 2, 186), f"{group_name}  ·  {pos+1} / {total}",
           font=font("sans", 34), fill=INK_SOFT, anchor="mm")

    # 卡面用「空白版」，答案放下面，避免重复；hl=True 时把正在读的那个字/字母圈出来
    card = draw_card(item, kind, False, 980, "", hl=hl)
    paste_shadow(img, card, ((W - 980) // 2, 250))

    pf = fit_font("sans_bold", item["pinyin"], 940, 128, 60)
    d.text((W / 2, 1372), item["pinyin"], font=pf,
           fill=(20, 96, 160) if hl else ACCENT, anchor="mm")
    d.line([W / 2 - 200, 1462, W / 2 + 200, 1462], fill=BORDER, width=3)
    if kind == "letter":
        hint = item.get("tip")
    elif kind == "blend":
        hint = item.get("blend")
    else:
        hint = "跟着读一遍"
    d.text((W / 2, 1544), hint or "跟着读一遍", font=font("sans", 44), fill=INK_SOFT, anchor="mm")

    if total:
        gap = 26
        x0 = W / 2 - (total - 1) * gap / 2
        for i in range(total):
            r = 7 if i == pos else 5
            c = ACCENT if i == pos else (196, 214, 230)
            d.ellipse([x0 + i * gap - r, 1700 - r, x0 + i * gap + r, 1700 + r], fill=c)
    return img


def build_frames(data):
    if os.path.isdir(FRAME_DIR):
        shutil.rmtree(FRAME_DIR)
    os.makedirs(FRAME_DIR, exist_ok=True)
    n = 0
    for lv in data["levels"]:
        for g in lv["groups"]:
            items = g["items"]
            for i, it in enumerate(items):
                for hl in (False, True):
                    make_frame(it, g["kind"], data["meta"], g["name"], i, len(items), hl).save(
                        os.path.join(FRAME_DIR, "%03d%s.png" % (it["id"], "_hl" if hl else "")))
                n += 1
    return n


def build_singles(data, only=None):
    os.makedirs(V_SINGLE, exist_ok=True)
    if not only:
        for f in os.listdir(V_SINGLE):
            if f.endswith(".mp4"):
                os.remove(os.path.join(V_SINGLE, f))
    n = 0
    for lv in data["levels"]:
        for g in lv["groups"]:
            for it in g["items"]:
                if only and it["id"] not in only:
                    continue
                out = os.path.join(V_SINGLE, f"{it['id']:03d}_{it['text']}.mp4")
                concat_video(out, item_seq(it, tail=1.0), "s_%03d" % it["id"])
                n += 1
    return n


def silence(path, seconds):
    if not os.path.exists(path):
        sh(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
            "-t", "%.2f" % seconds, "-q:a", "9", path])


def make_title_frame(title, sub, count):
    """合集里的章节页：一组一张"""
    img = vgrad(W, H, (226, 239, 250), (250, 252, 254))
    d = ImageDraw.Draw(img)
    d.text((W / 2, 760), title, font=font("sans_bold", 132), fill=ACCENT, anchor="mm")
    d.text((W / 2, 900), sub, font=font("sans", 48), fill=INK_SOFT, anchor="mm")
    d.line([W / 2 - 120, 1010, W / 2 + 120, 1010], fill=BORDER, width=4)
    d.text((W / 2, 1100), "%d 个" % count, font=font("sans", 56), fill=INK_SOFT, anchor="mm")
    return img


def concat_video(out, seq, tag):
    """seq: [(帧图路径, 音频路径或None, 时长秒)]"""
    os.makedirs(TMP, exist_ok=True)
    sil_lead = os.path.join(TMP, "sil_lead.mp3")
    sil_gap = os.path.join(TMP, "sil_gap.mp3")
    silence(sil_lead, LEAD)
    silence(sil_gap, GAP)

    def sil_for(sec):
        if sec <= 0.02:
            return None
        p = os.path.join(TMP, "sil_%.2f.mp3" % sec)
        silence(p, sec)
        return p

    lines, aud = [], ["file '%s'" % sil_lead]
    for frame, mp3, dur in seq:
        lines.append("file '%s'" % frame)
        lines.append("duration %.3f" % dur)
        if mp3:
            aud.append("file '%s'" % mp3)
            rest = dur - dur_of(mp3)
            tail = sil_for(round(rest, 2))
            if tail:
                aud.append("file '%s'" % tail)
        else:
            tail = sil_for(round(dur, 2))
            if tail:
                aud.append("file '%s'" % tail)
    # 末帧兜底，避免 concat 丢最后一帧
    lines.append("file '%s'" % seq[-1][0])

    img_list = os.path.join(TMP, "%s_img.txt" % tag)
    aud_list = os.path.join(TMP, "%s_aud.txt" % tag)
    open(img_list, "w").write("\n".join(lines) + "\n")
    open(aud_list, "w").write("\n".join(aud) + "\n")

    bed = os.path.join(TMP, "%s_audio.m4a" % tag)
    sh(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", aud_list,
        "-c:a", "aac", "-b:a", "128k", bed])
    sh(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", img_list, "-i", bed,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "25", "-r", "30",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart", out])


def item_dur(it):
    mp3 = os.path.join(AUDIO_DIR, "%03d_hz.mp3" % it["id"])
    return max(dur_of(mp3) + GAP, MIN_DUR)


def build_titles(data):
    if os.path.isdir(TITLE_DIR):
        shutil.rmtree(TITLE_DIR)
    os.makedirs(TITLE_DIR, exist_ok=True)
    for lv in data["levels"]:
        for g in lv["groups"]:
            if not g["items"]:
                continue
            make_title_frame(g["name"], "%s %s" % (lv["code"], lv["name"]), len(g["items"])).save(
                os.path.join(TITLE_DIR, "%s.png" % g["id"]))


def title_entry(g, sec=1.6):
    return (os.path.join(TITLE_DIR, "%s.png" % g["id"]), None, sec)


LEAD, GAP, TAIL = 0.30, 0.65, 1.10


def item_seq(it, gap=None, tail=None):
    """一个单元 = 读两遍；每遍配一张高亮帧，中间留空档，看得清在读哪个字"""
    gap = GAP if gap is None else gap
    tail = TAIL if tail is None else tail
    norm = os.path.join(FRAME_DIR, "%03d.png" % it["id"])
    hl = os.path.join(FRAME_DIR, "%03d_hl.png" % it["id"])
    mp3 = os.path.join(AUDIO_DIR, "%03d_hz.mp3" % it["id"])
    d = max(dur_of(mp3), 0.6) + 0.45      # 语音结束后多停 0.45 秒，留出反应时间
    return [(norm, None, LEAD),
            (hl, mp3, d),
            (norm, None, gap),
            (hl, mp3, d),
            (norm, None, tail)]


def _clean(d):
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.endswith(".mp4"):
                os.remove(os.path.join(d, f))


def build_groups(data, only=None):
    """每组一条：直接连读，不插章节页"""
    os.makedirs(V_GROUP, exist_ok=True)
    if not only:
        _clean(V_GROUP)
    n = 0
    for lv in data["levels"]:
        for g in lv["groups"]:
            if len(g["items"]) < 3:
                continue
            if only and not any(it["id"] in only for it in g["items"]):
                continue
            seq = []
            for it in g["items"]:
                seq += item_seq(it)
            concat_video(os.path.join(V_GROUP, "%s_%s_合集.mp4" % (g["id"], g["name"])),
                         seq, "g_%s" % g["id"])
            n += 1
    return n


def build_levels(data, only=None):
    """每级一条：组与组之间插章节页"""
    os.makedirs(V_LEVEL, exist_ok=True)
    if not only:
        _clean(V_LEVEL)
    n = 0
    for lv in data["levels"]:
        groups = [g for g in lv["groups"] if g["items"]]
        if not groups:
            continue
        if only and not any(it["id"] in only for g in groups for it in g["items"]):
            continue
        seq = []
        for g in groups:
            if len(groups) > 1:
                seq.append(title_entry(g))
            for it in g["items"]:
                seq += item_seq(it, gap=0.35, tail=0.55)
        concat_video(os.path.join(V_LEVEL, "%s_%s_整级合集.mp4" % (lv["code"], lv["name"])),
                     seq, "lv_%s" % lv["code"])
        n += 1
    return n


def build_all(data):
    """全库一条：所有级别、所有组连成一条"""
    os.makedirs(V_ALL, exist_ok=True)
    _clean(V_ALL)
    seq = []
    levels = [lv for lv in data["levels"] if any(g["items"] for g in lv["groups"])]
    for lv in levels:
        groups = [g for g in lv["groups"] if g["items"]]
        for g in groups:
            seq.append(title_entry(g))
            for it in g["items"]:
                seq += item_seq(it, gap=0.35, tail=0.55)
    if not seq:
        return 0
    n_items = sum(len(g["items"]) for lv in levels for g in lv["groups"])
    concat_video(os.path.join(V_ALL, "拼音全集_%d个.mp4" % n_items), seq, "all")
    return 1


if __name__ == "__main__":
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    mode = positional[0] if positional else "all"

    only = None
    if "--only" in sys.argv:
        i = sys.argv.index("--only")
        if i + 1 < len(sys.argv):
            only = {int(x) for x in sys.argv[i + 1].replace(" ", "").split(",") if x}
            print(f"只重出 {len(only)} 个单元相关的视频")

    print(f"底图 -> {build_frames(data)} 张 1080x1920")
    build_titles(data)
    if mode in ("all", "single"):
        print(f"单条视频 -> {build_singles(data, only)} 条")
    if mode in ("all", "group"):
        print(f"每组一条 -> {build_groups(data, only)} 条")
        print(f"每级一条 -> {build_levels(data, only)} 条")
    if mode in ("all", "group", "whole"):
        print(f"全库一条 -> {build_all(data)} 条")
