#!/usr/bin/env bash
# ✦ Run this ON each familiar host (Mac mini, Mac Pro, MacBook Pro) ✦
#
# Installs (by default):
#   1. Tailscale (if missing)
#   2. Beszel agent (lightweight system metrics)
#
# Optional with --with-claude:
#   3. Claude Code bridge launchd service (lets familiars borrow Claude)
#      The familiars themselves don't need this — the Coven Mail Bridge
#      gives them everything they need over plain HTTP. Only install
#      this if you want to layer Claude on top later.
#
# Usage:
#   ./setup-familiar-host.sh <hub-tailscale-name> [--with-claude]
#   e.g. ./setup-familiar-host.sh spellman-manor.tailXXXX.ts.net

set -euo pipefail

HUB=""
INSTALL_CLAUDE=0
for arg in "$@"; do
  case "$arg" in
    --with-claude) INSTALL_CLAUDE=1 ;;
    *) [ -z "$HUB" ] && HUB="$arg" ;;
  esac
done

if [ -z "$HUB" ]; then
  echo "Usage: $0 <hub-tailscale-name> [--with-claude]" >&2
  echo "  e.g.  $0 spellman-manor.tailXXXX.ts.net" >&2
  exit 1
fi

echo "🌙 Setting up familiar host. Hub: $HUB"
[ $INSTALL_CLAUDE -eq 1 ] && echo "    (--with-claude: will also install the optional Claude bridge)"
echo ""

# 1. Tailscale
if ! command -v tailscale >/dev/null 2>&1; then
  echo "📡 Installing Tailscale..."
  if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "   Open https://tailscale.com/download/mac and install the app."
    echo "   Then re-run this script."
    exit 1
  else
    curl -fsSL https://tailscale.com/install.sh | sh
    sudo tailscale up
  fi
else
  echo "✓ Tailscale already installed."
fi

# 2. Beszel agent
if ! launchctl list 2>/dev/null | grep -q beszel-agent && ! systemctl is-active --quiet beszel-agent 2>/dev/null; then
  echo ""
  echo "💗 Installing Beszel agent..."
  echo "   When prompted for the hub URL, enter: http://${HUB}:8090"
  echo ""
  curl -fsSL https://raw.githubusercontent.com/henrygd/beszel/main/supplemental/scripts/install-agent.sh | bash
  echo ""
  echo "👉 Copy the public key it printed and paste it into Beszel UI:"
  echo "   http://${HUB}:8090  →  Add System"
else
  echo "✓ Beszel agent already running."
fi

# 3. Claude Code bridge — only if explicitly requested
if [ $INSTALL_CLAUDE -eq 1 ] && command -v claude >/dev/null 2>&1; then
  echo ""
  echo "🤖 Setting up Claude bridge (--with-claude requested)..."
  mkdir -p "$HOME/.openclaw/workspace/claude-bridge"
  cat > "$HOME/.openclaw/workspace/claude-bridge/bridge.py" <<'PY'
#!/usr/bin/env python3
"""Tiny HTTP wrapper over `claude -p` so peers can borrow this Mac's Claude."""
import http.server, json, os, subprocess, socketserver

PORT = int(os.environ.get("CLAUDE_BRIDGE_PORT", 18794))
TOKEN = os.environ.get("CLAUDE_BRIDGE_TOKEN", "")

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200); self.end_headers()
            self.wfile.write(b'{"ok":true,"service":"claude-bridge"}')
        else:
            self.send_response(404); self.end_headers()
    def do_POST(self):
        if TOKEN:
            auth = self.headers.get("Authorization", "")
            if auth != f"Bearer {TOKEN}":
                self.send_response(401); self.end_headers(); return
        if self.path != "/ask":
            self.send_response(404); self.end_headers(); return
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n)) if n else {}
        prompt = body.get("prompt", "")
        if not prompt:
            self.send_response(400); self.end_headers()
            self.wfile.write(b'{"error":"prompt required"}'); return
        try:
            r = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "json"],
                capture_output=True, text=True, timeout=120
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(r.stdout.encode())
        except subprocess.TimeoutExpired:
            self.send_response(504); self.end_headers()
            self.wfile.write(b'{"error":"timeout"}')

class T(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True; allow_reuse_address = True

T(("0.0.0.0", PORT), H).serve_forever()
PY
  chmod +x "$HOME/.openclaw/workspace/claude-bridge/bridge.py"

  cat > "$HOME/Library/LaunchAgents/ai.openclaw.claude-bridge.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>ai.openclaw.claude-bridge</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>$HOME/.openclaw/workspace/claude-bridge/bridge.py</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin</string>
    <key>CLAUDE_BRIDGE_PORT</key><string>18794</string>
  </dict>
  <key>KeepAlive</key><true/>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$HOME/.openclaw/workspace/claude-bridge/bridge.log</string>
  <key>StandardErrorPath</key><string>$HOME/.openclaw/workspace/claude-bridge/bridge.log</string>
</dict>
</plist>
EOF
  launchctl unload "$HOME/Library/LaunchAgents/ai.openclaw.claude-bridge.plist" 2>/dev/null || true
  launchctl load "$HOME/Library/LaunchAgents/ai.openclaw.claude-bridge.plist"
  echo "✓ Claude bridge running on :18794 (test: curl http://localhost:18794/health)"
elif [ $INSTALL_CLAUDE -eq 1 ]; then
  echo "⚠️  --with-claude was passed but the claude CLI isn't installed."
  echo "   Install with: npm install -g @anthropic-ai/claude-code"
  echo "   Then re-run this script."
fi

echo ""
echo "✨ This host is ready. The hub will start scraping it within 30s."
echo ""
echo "📜 Tell the OpenClaw familiar on this host about the bridge:"
echo "   The Coven Mail Bridge lives at http://${HUB%%.*}.tail*.ts.net:18793"
echo "   The Familiar's Handbook is fetchable at:"
echo "   curl http://${HUB%%.*}.tail*.ts.net:18793/api/handbook"
