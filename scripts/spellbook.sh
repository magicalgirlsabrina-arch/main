#!/usr/bin/env bash
# ✦ The Spellbook — convenience commands for managing Spellman Manor ✦
#
# Usage:
#   ./scripts/spellbook.sh up        # start the whole stack
#   ./scripts/spellbook.sh down      # stop the stack
#   ./scripts/spellbook.sh restart   # rebuild & restart
#   ./scripts/spellbook.sh update    # pull new images and restart
#   ./scripts/spellbook.sh logs      # tail logs from all services
#   ./scripts/spellbook.sh status    # show what's running
#   ./scripts/spellbook.sh peer      # quick health check of all 4 ClawBots

set -euo pipefail
cd "$(dirname "$0")/.."

cmd=${1:-status}

case "$cmd" in
  up)
    echo "🔮 Opening the linen closet..."
    docker compose up -d
    echo "✨ The Discovery of Magic → http://localhost:3000"
    ;;
  down)
    echo "🌑 Sealing the linen closet..."
    docker compose down
    ;;
  restart)
    docker compose down && docker compose up -d
    ;;
  update)
    echo "📚 Updating spellbooks..."
    docker compose pull && docker compose up -d
    ;;
  logs)
    docker compose logs -f --tail=50
    ;;
  status)
    docker compose ps
    ;;
  peer)
    echo "🐈‍⬛ Pinging the coven..."
    set +e
    for bot in HILDA ZELDA SALEM HARVEY; do
      host_var="${bot}_HOST"
      token_var="${bot}_TOKEN"
      host=$(grep "^${host_var}=" .env 2>/dev/null | cut -d= -f2)
      token=$(grep "^${token_var}=" .env 2>/dev/null | cut -d= -f2)
      if [ -z "$host" ] || [ -z "$token" ]; then
        echo "  ${bot}: no .env entry"; continue
      fi
      code=$(curl -s -o /dev/null -w "%{http_code}" -m 5 \
        -H "Authorization: Bearer $token" \
        "http://${host}:18789/api/diagnostics/prometheus")
      if [ "$code" = "200" ]; then
        echo "  ${bot}: ✨ alive (${host})"
      else
        echo "  ${bot}: ✗ HTTP ${code} (${host})"
      fi
    done
    ;;
  *)
    echo "Usage: $0 {up|down|restart|update|logs|status|peer}"
    exit 1
    ;;
esac
