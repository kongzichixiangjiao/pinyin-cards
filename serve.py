#!/usr/bin/env python3
"""静态预览服务器：比 python3 -m http.server 多一件事 —— 支持 HTTP Range。
iOS Safari 播 mp4 / 拖动音频进度都依赖 Range（206），原生 http.server 不支持。
零依赖，只用标准库。
"""
import argparse
import os
import posixpath
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")


class RangeHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        """有 Range 头就走分片，其余交给父类。"""
        rng = self.headers.get("Range")
        if not rng:
            return super().send_head()

        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()

        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(404, "File not found")
            return None

        size = os.fstat(f.fileno()).st_size
        m = RANGE_RE.fullmatch(rng.strip())
        if not m or not (m.group(1) or m.group(2)):
            f.close()
            self.send_error(400, "Bad Range")
            return None

        start_s, end_s = m.groups()
        if start_s:
            start = int(start_s)
            end = int(end_s) if end_s else size - 1
        else:  # bytes=-500 表示最后 500 字节
            start = max(0, size - int(end_s))
            end = size - 1
        if start >= size or start > end:
            f.close()
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return None

        end = min(end, size - 1)
        f.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Last-Modified", self.date_time_string(os.fstat(f.fileno()).st_mtime))
        self.end_headers()
        return _Slice(f, end - start + 1)

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        # 只打非 200/206 的，避免刷屏
        msg = fmt % args
        if " 200 " not in msg and " 206 " not in msg and " 304 " not in msg:
            sys.stderr.write(msg + "\n")


class _Slice:
    """只吐出前 n 字节的包装，供 copyfile 使用后自动关闭。"""

    def __init__(self, f, n):
        self.f, self.n = f, n

    def read(self, amt=-1):
        if self.n <= 0:
            return b""
        if amt < 0 or amt > self.n:
            amt = self.n
        data = self.f.read(amt)
        self.n -= len(data)
        return data

    def close(self):
        self.f.close()


class Server(ThreadingHTTPServer):
    daemon_threads = True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("port", nargs="?", type=int, default=8000)
    ap.add_argument("--dir", default=".")
    args = ap.parse_args()
    os.chdir(args.dir)
    httpd = Server(("0.0.0.0", args.port), RangeHandler)
    print(f"serving {os.getcwd()} on 0.0.0.0:{args.port} (Range 已支持)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
