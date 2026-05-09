#!/usr/bin/env bash
# ✦ Health-check every familiar (peer-ping via the bridge) ✦

set -euo pipefail
BRIDGE=${BRIDGE_URL:-http://localhost:18793}

echo "🩺 Pinging the coven..."
curl -s "$BRIDGE/api/peer-ping" | python3 -c '
import json, sys
data = json.load(sys.stdin)
emoji = {"salem":"🐈‍⬛","hilda":"☕","zelda":"📖","harvey":"🛠"}
for name, info in data.items():
    e = emoji.get(name, "✨")
    if info.get("ok"):
        print(f"  {e} {name:8s} ✨ alive · {info.get(\"latency_ms\",\"?\")}ms")
    else:
        print(f"  {e} {name:8s} ✗ {info.get(\"error\",\"unknown error\")}")
'

echo ""
echo "💌 Mailbox:"
curl -s "$BRIDGE/api/unread-count" | python3 -c '
import json, sys
d = json.load(sys.stdin)
print(f"  {d[\"unread\"]} unread · {d[\"total\"]} total · cursor at {d[\"cursor\"]}")
'

echo ""
echo "🚫 Circuit breakers:"
curl -s "$BRIDGE/api/circuits" | python3 -c '
import json, sys
data = json.load(sys.stdin)
for name, c in data.items():
    state = c["state"]
    icon = "✨" if state == "closed" else ("⚠️ " if state == "half-open" else "🚫")
    print(f"  {icon} {name:8s} {state:9s} (failures: {c[\"failures\"]})")
'
