#!/usr/bin/env bash
# ✦ Expose The Discovery of Magic on a clean tailnet HTTPS URL ✦
# Run this once on Spellman Manor (the Mac mini) after `docker compose up -d`.
#
# Result: https://spellman-manor.tailXXXX.ts.net  →  Homepage (port 3000)
# (Other services stay on localhost ports; only the front door is exposed.)

set -euo pipefail

if ! command -v tailscale >/dev/null; then
  echo "✗ Tailscale CLI not found. Install Tailscale on this Mac first." >&2
  exit 1
fi

echo "🌙 Conjuring HTTPS for The Discovery of Magic..."
sudo tailscale serve --bg --https=443 --set-path=/ http://127.0.0.1:3000

echo ""
echo "✨ Done. Visit:"
tailscale status --self --peers=false --json 2>/dev/null \
  | grep -E '"DNSName"' \
  | head -1 \
  | sed -E 's/.*"DNSName": "([^"]+)".*/   https:\/\/\1/'

echo ""
echo "To take it down later:  sudo tailscale serve reset"
