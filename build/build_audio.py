# -*- coding: utf-8 -*-
"""curriculum.json -> 每个单元一条朗读 mp3（edge-tts，本地免费）"""
import asyncio, json, os, shutil, subprocess, sys
import edge_tts

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "curriculum.json")
OUT = os.path.join(ROOT, "assets", "audio")

VOICE = "zh-CN-XiaoyiNeural"
RATE = "-18%"
SEM = asyncio.Semaphore(4)

# 人工/特殊录音放这里，会覆盖 TTS 结果（--force 也不会冲掉）
OVERRIDE = os.path.join(ROOT, "data", "audio_override")

# TTS 每条都会带 1 秒多的首尾静音，剪掉，「读两遍」的节奏才听得出来
TRIM_AF = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.02,"
           "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,"
           "areverse")


def trim_silence(path):
    tmp = path + ".trim.mp3"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path, "-af", TRIM_AF,
                    "-c:a", "libmp3lame", "-b:a", "96k", tmp], check=True)
    os.replace(tmp, path)


async def gen(text, path, retry=3, force=False):
    async with SEM:
        if not force and os.path.exists(path) and os.path.getsize(path) > 2000:
            return "skip"
        for i in range(retry):
            try:
                await edge_tts.Communicate(text, VOICE, rate=RATE).save(path)
                trim_silence(path)
                return "ok"
            except Exception as e:
                if i == retry - 1:
                    return f"fail:{e}"
                await asyncio.sleep(1.5)


async def main():
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)
    items = [it for lv in data["levels"] for g in lv["groups"] for it in g["items"]]

    os.makedirs(OUT, exist_ok=True)
    force = "--force" in sys.argv
    if force:
        for f in os.listdir(OUT):
            if f.endswith(".mp3"):
                os.remove(os.path.join(OUT, f))

    tasks = [gen(it.get("say") or it["text"], os.path.join(OUT, f"{it['id']:03d}_hz.mp3"), force=force)
             for it in items]
    res = await asyncio.gather(*tasks)

    # 覆盖录音优先
    used = 0
    if os.path.isdir(OVERRIDE):
        for f in os.listdir(OVERRIDE):
            if not f.endswith(".mp3"):
                continue
            dst = os.path.join(OUT, "%03d_hz.mp3" % int(os.path.splitext(f)[0]))
            shutil.copyfile(os.path.join(OVERRIDE, f), dst)
            used += 1

    bad = [(it["id"], it["text"], r) for it, r in zip(items, res) if r.startswith("fail")]
    print(f"音频 {len(items)} 条：新生成={res.count('ok')} 已有跳过={res.count('skip')} 失败={len(bad)}")
    if not force and res.count("skip"):
        print("  （改了 say 文本要重配？加 --force）")
    if used:
        print("  覆盖录音 %d 条（来自 data/audio_override/）" % used)
    for b in bad:
        print("  !", b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
