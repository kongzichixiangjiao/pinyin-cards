#!/usr/bin/env bash
# 公网隧道预览：给一个 https 链接，手机用 4G / 任何网络都能打开（不受局域网隔离影响）
# 用法: ./tunnel.sh [端口]   默认 8000
# 前提: 已装 cloudflared（brew install cloudflared）
set -euo pipefail

cd "$(dirname "$0")"
PORT="${1:-8000}"
QR=".serve-qr.png"
LOG="$(mktemp -t cf.XXXXXX)"

if command -v cloudflared >/dev/null 2>&1; then
  CF="$(command -v cloudflared)"
elif [ -x "$HOME/.local/bin/cloudflared" ]; then
  CF="$HOME/.local/bin/cloudflared"
else
  echo "❌ 没找到 cloudflared。先跑: brew install cloudflared"
  exit 1
fi

# 本地服务没起就先起一个
SERVER_PID=""
if ! nc -z 127.0.0.1 "$PORT" 2>/dev/null; then
  echo "▶ 本地服务未运行，先启动 serve.py:$PORT"
  python3 serve.py "$PORT" >/dev/null 2>&1 &
  SERVER_PID=$!
  sleep 1
fi

cleanup() {
  [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null || true
  rm -f "$LOG"
}
trap cleanup EXIT INT TERM

"$CF" tunnel --url "http://localhost:$PORT" --no-autoupdate >"$LOG" 2>&1 &
CF_PID=$!

# 等 URL 出现（最多 25 秒）
URL=""
for _ in $(seq 1 50); do
  URL="$(grep -Eo 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" | head -1 || true)"
  [ -n "$URL" ] && break
  kill -0 "$CF_PID" 2>/dev/null || break
  sleep 0.5
done

if [ -z "$URL" ]; then
  echo "❌ 隧道没起来，cloudflared 输出："
  tail -20 "$LOG"
  kill "$CF_PID" 2>/dev/null || true
  exit 1
fi

echo "────────────────────────────────────────"
echo "🌍 手机（任意网络 / 4G 都行）:  $URL"
echo "────────────────────────────────────────"

python3 - "$URL" "$QR" <<'PY' || true
import sys
url, out = sys.argv[1], sys.argv[2]
try:
    import qrcode
    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    qr.make()
    qr.make_image(fill_color="black", back_color="white").save(out)
    print(f"🔳 二维码已更新: {out}")
except Exception as e:
    print(f"(二维码跳过: {e})")
PY

echo "⚠️  这个链接是公网可访问的临时地址，Ctrl+C 就失效；Mac 睡眠/断网也会断"
echo "按 Ctrl+C 停止隧道"
wait "$CF_PID"
