# 🛠 Troubleshooting

For new-to-coding readers: most "broken" things in this stack are one of:
(1) Docker container not running, (2) Tailscale not connected, (3) wrong
token in `.env`. Check those three first.

## A familiar shows offline / "vanished" in the dashboard

```sh
# 1. Is Tailscale connected on the hub?
tailscale status

# 2. Can you actually reach that familiar?
curl http://harvey.tailXXXX.ts.net:18789/health

# 3. Check the familiar's log on its own host
ssh harveys-workshop "tail -50 ~/.openclaw/openclaw.log"
```

If `tailscale status` shows the host but the curl times out, the OpenClaw
gateway crashed. SSH in and restart it.

## Prometheus shows a target as DOWN

Most common cause: wrong bearer token in `prometheus/tokens/*.token`.

```sh
# Test the token by hand
curl -sH "Authorization: Bearer $(cat prometheus/tokens/salem.token)" \
  http://100.106.134.96:18789/api/diagnostics/prometheus | head
```

If you get HTML or `401`, the token is wrong or the diagnostics plugin is
disabled. Check the familiar's gateway config:

```jsonc
{
  "gateway": {
    "plugins": {
      "diagnostics-prometheus": { "enabled": true }
    }
  }
}
```

After fixing, hot-reload Prometheus:
```sh
./scripts/spellbook.sh reload-prometheus
```

## Coven Mail Bridge is empty / "consulting the book…" forever

The bridge mounts `~/.openclaw/workspace/coven-mailbox/` from your home.
If `COVEN_MAILBOX_DIR` is wrong, it sees no inbox file.

```sh
# Verify the mount works
docker exec coven-mail ls -la /mailbox

# Should show: inbox.jsonl  cursor.txt  outbox/
```

If it doesn't, fix `COVEN_MAILBOX_DIR` in `.env` and restart the bridge:
```sh
docker compose up -d coven-mail
```

## The Magic Mirror page is blank / shows "?"

The TV browser hits the bridge directly (port 18793). On the TV, open the
URL in the browser:

```
http://spellman-manor.tailXXXX.ts.net:18793/health
```

If that returns JSON, the bridge is fine — the issue is `BRIDGE_URL` in
`magic-mirror/app.js`. By default it's empty (same-origin), which only
works if the TV is hitting the bridge through the same hostname.

If the TV hits port 8080 (nginx) but the bridge is on 18793, set:

```js
const BRIDGE_URL = 'http://spellman-manor.tailXXXX.ts.net:18793';
```

Then `docker compose up -d magic-mirror` to reload nginx.

## Homepage tiles say "no data" / show errors

The widget is hitting an OpenClaw endpoint over the network. Check:

1. `.env` has the right `*_GATEWAY_TOKEN` and `*_HOST` values.
2. The widget URL works from the Mac mini's terminal:
   ```sh
   curl -sH "Authorization: Bearer $SALEM_GATEWAY_TOKEN" \
     http://$SPELLMAN_MANOR_IP:18789/api/diagnostics/summary
   ```
3. The fields (`model`, `tokens_per_sec`, `active_sessions`) actually exist
   in the response. If the field names differ, edit `homepage/services.yaml`
   `mappings:`.

## Grafana shows "no data" in panels

The panels reference metric names like `openclaw_gateway_requests_total`.
If your OpenClaw version exposes different names, update each panel's
`expr:` field. Find the actual names by hitting:

```sh
curl -sH "Authorization: Bearer $TOKEN" \
  http://100.106.134.96:18789/api/diagnostics/prometheus | grep -v '^#'
```

## "Permission denied" when starting Docker on the mini

Docker Desktop needs to be running (the whale in your menu bar). If the whale
isn't there, open Docker.app from Applications.

## Disk filling up (Prometheus / Beszel data)

Prometheus retains 30 days of metrics in a Docker volume. Check size:

```sh
docker system df -v | grep -E 'prometheus|grafana|alertmanager'
```

To shorten retention, edit `docker-compose.yml`:
```yaml
'--storage.tsdb.retention.time=7d'
```

## Nuclear option

```sh
./scripts/spellbook.sh down
docker volume ls -q | grep spellman | xargs docker volume rm
./scripts/spellbook.sh up
```

This wipes Prometheus + Grafana + Alertmanager data and starts fresh. Your
mailbox file is *not* affected (it's a host volume, not a Docker volume).
