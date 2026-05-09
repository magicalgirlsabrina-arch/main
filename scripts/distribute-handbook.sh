#!/usr/bin/env bash
# ✦ Distribute the Familiar's Handbook to the coven ✦
#
# Sends a coven mail to every familiar pointing them at the bridge URL
# where the full handbook is served. The handbook itself is too long
# to fit comfortably in a mail body — better to point everyone at one
# canonical source.

set -euo pipefail

BRIDGE_INTERNAL=${BRIDGE_INTERNAL:-http://localhost:18793}
BRIDGE_TAILNET=${BRIDGE_TAILNET:-http://100.106.134.96:18793}

# Sanity check: the handbook is mounted into the bridge.
if ! curl -fs -o /dev/null "${BRIDGE_INTERNAL}/api/handbook"; then
  echo "✗ The handbook isn't being served by the bridge."
  echo "  Did docker-compose mount docs/13-familiar-handbook.md → /app/handbook.md?"
  echo "  Try: docker compose up -d --build coven-mail"
  exit 1
fi

MSG=$(cat <<EOF
Coven members — there's a new Familiar's Handbook for the v1 dashboard.

It covers: the bridge endpoints, how to send/broadcast/peer-ping, how to
report watchdog/cron heartbeats, how to log subagent activity, and how
to check available upgrades. Everything is plain HTTP — no new
dependencies.

Read it (markdown):
  curl ${BRIDGE_TAILNET}/api/handbook

Or pretty-printed if you have glow installed:
  curl -s ${BRIDGE_TAILNET}/api/handbook | glow -

Quick reference card is at the bottom. Etiquette section is short and
worth reading. Reply with questions.

— Sabrina
EOF
)

echo "🔮 Distributing the handbook to the coven..."
curl -fs -X POST "${BRIDGE_INTERNAL}/api/broadcast" \
  -H 'Content-Type: application/json' \
  -d "$(python3 -c '
import json, sys
print(json.dumps({"from": "sabrina", "message": sys.stdin.read()}))
' <<< "$MSG")" | python3 -m json.tool

echo ""
echo "✨ Each familiar can fetch the full handbook with:"
echo "   curl ${BRIDGE_TAILNET}/api/handbook"
