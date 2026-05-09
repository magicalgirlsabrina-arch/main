#!/usr/bin/env bash
# ✦ Broadcast a message to the entire coven via the Coven Mail Bridge ✦
#
# Usage:
#   ./scripts/coven-broadcast.sh "your message"
#   ./scripts/coven-broadcast.sh --from someone "your message"

set -euo pipefail
BRIDGE=${BRIDGE_URL:-http://localhost:18793}

from="sabrina"
if [ "${1:-}" = "--from" ]; then
  from="$2"; shift 2
fi

msg="${*:-}"
if [ -z "$msg" ]; then
  echo "Usage: $0 [--from <name>] <message>" >&2
  exit 1
fi

echo "🔮 Broadcasting from '$from': $msg"
curl -s -X POST "$BRIDGE/api/broadcast" \
  -H 'Content-Type: application/json' \
  -d "$(printf '{"message":%s,"from":%s}' "$(printf '%s' "$msg" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')" "$(printf '%s' "$from" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')")" \
  | python3 -m json.tool
