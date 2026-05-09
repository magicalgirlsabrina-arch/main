# 🛠 Troubleshooting
*runbook for common failures*

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

## Familiar tiles say "API Error Information"

The familiar tiles route through the bridge at `http://coven-mail:18793/api/familiar/{name}` — the bridge handles auth and falls back to `/health` if `/api/diagnostics/summary` is unavailable. So a tile error usually means:

1. **The bridge can't reach the familiar.** Test directly:
   ```sh
   curl -sH "Authorization: Bearer $SALEM_GATEWAY_TOKEN" \
     http://100.106.134.96:18789/api/diagnostics/summary
   curl http://100.106.134.96:18789/health
   ```
   If the second one works but the first doesn't, your gateway token is wrong or the diagnostics plugin isn't enabled — the tile will still show "alive" via the fallback, just without the model/tokens.

2. **The bridge isn't running.** `docker compose ps coven-mail`. If down: `docker compose up -d coven-mail`.

3. **Tailscale.** From the bridge container: `docker exec coven-mail wget -qO- http://100.106.134.96:18789/health`. If that times out, the bridge container can't see the tailnet — check Docker host networking.

## Surveillance shows no cron / watchdog data

That's expected on first boot — those are heartbeats, not scrapes. They only show up after a job/watchdog has actively reported in. See [`12-watchdog-cron.md`](12-watchdog-cron.md) to wire up your first one.

## Upgrades panel slow / shows errors

`/api/upgrades` hits Docker Hub + GitHub on first load, then caches for an hour. If it errors, GitHub is rate-limiting unauthenticated calls (60/hr per IP). Either wait an hour or set `GITHUB_TOKEN` in `.env` and pass it through to the bridge (currently not wired — easy add if you need it).

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
