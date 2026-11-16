#!/usr/bin/env bash
# 局域网预览：手机连同一个 WiFi，扫二维码即可打开拼音卡片
# 用法: ./serve.sh [端口]   默认 8000
set -euo pipefail
cd "$(dirname "$0")"

PORT="${1:-8000}"

IP="$(ipconfig getifaddr en0 2>/dev/null || true)"
[ -z "$IP" ] && IP="$(ipconfig getifaddr en1 2>/dev/null || true)"

URL="http://${IP:-127.0.0.1}:${PORT}"

echo "────────────────────────────────────────"
if [ -n "$IP" ]; then
  echo "📱 手机（同一 WiFi）打开:  $URL"
else
  echo "⚠️  没拿到局域网 IP，检查 Mac 是否连着 WiFi"
fi
echo "💻 本机预览:               http://localhost:${PORT}"
echo "────────────────────────────────────────"

python3 - "$URL" <<'PY' || true
import sys
url = sys.argv[1]
try:
    import qrcode
    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    qr.make()
    qr.make_image(fill_color="black", back_color="white").save(".serve-qr.png")
    print("🔳 二维码已保存: .serve-qr.png  (可以照着这个在手机扫码)")
except Exception as e:
    print(f"(二维码跳过: {e})")
PY

echo "按 Ctrl+C 停止服务"
exec python3 serve.py "$PORT"
