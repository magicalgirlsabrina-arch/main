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

## `error getting credentials - exec: "docker-credential-desktop"`

Docker Desktop installs `docker` and its credential helper at
`/Applications/Docker.app/Contents/Resources/bin`, but doesn't add that
to your shell PATH. Fix it once:

```sh
echo 'export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

`spellbook.sh` already auto-prepends this path so its commands work
even without the rc edit — but interactive `docker` / `docker compose`
won't work until you do.

## `brew install --cask docker` failed

It needs `sudo mkdir /usr/local/cli-plugins` which can fail silently on
managed Macs and non-TTY shells. Use the .dmg directly:

1. Download from https://docs.docker.com/desktop/install/mac-install/
2. Drag Docker.app into Applications, open it.

## Can't SSH into Zelda's Study or Harvey's Workshop

macOS doesn't enable Remote Login by default. On the host that needs
to be reachable:

- **GUI:** System Settings → General → Sharing → enable **Remote Login**
- **CLI:** `sudo systemsetup -setremotelogin on`

Once enabled, `ssh sabrinaryan@harveys-workshop.<your-tailnet>` works
over Tailscale.

## `exec format error` on Apple Silicon

You pulled an x86-only image. Either enable Rosetta in Docker Desktop
(Settings → General → "Use Rosetta for x86_64/amd64 emulation") or pin
the platform in `docker-compose.yml`:
```yaml
services:
  some-service:
    platform: linux/amd64
```
Everything in this repo is multi-arch (linux/arm64 + linux/amd64) so
you should never hit this with the bundled stack.

## `prometheus/tokens/*.token` keeps drifting from `.env`

Don't edit the token files directly anymore. They're auto-generated
from `.env` by `./scripts/sync-prometheus-tokens.sh`, which
`spellbook.sh up` calls automatically. Update `.env`, restart, done:

```sh
nano .env                          # update SALEM_GATEWAY_TOKEN, etc.
./scripts/spellbook.sh sync-tokens # or just `up` — same effect
./scripts/spellbook.sh reload-prometheus
```

## OpenClaw config has `token` (singular) not `tokens` (plural)

The OpenClaw config shape on the mini is `gateway.auth.token` — a single
string. `grab-gateway-token.sh` handles both shapes (and a scoped-tokens
variant). If your OpenClaw version uses something different again, edit
the python block in that script — it's only ~10 lines.

## The Veil (`:3030`) returns 502 Bad Gateway

The Veil is a reverse proxy in front of Homepage. 502 means Homepage
itself isn't running:

```sh
docker compose ps homepage
docker compose logs --tail=20 homepage
```

Restart it: `docker compose up -d homepage`. The Veil will start
proxying again automatically (30s health-check loop).

## iOS won't install the PWA / icon shows as page screenshot

Three checks, in order:

1. **You opened it in Chrome / Firefox / DuckDuckGo on iOS.** Only
   Safari can install PWAs on iOS — they all share Safari's WebKit
   under the hood, but `Add to Home Screen` is Safari-only.
2. **The manifest didn't load.** Test it directly:
   ```sh
   curl http://spellman-manor.<tailnet>.ts.net:3030/manifest.json
   curl http://spellman-manor.<tailnet>.ts.net:18793/manifest.json
   curl http://spellman-manor.<tailnet>.ts.net:8080/manifest.json
   ```
   Each should return JSON with a Sabrina-themed icon path. If 404,
   restart the relevant container.
3. **The injection didn't fire (Veil only).** View-source the page
   and look for `<link rel="manifest"` in the `<head>`. If missing,
   the nginx `sub_filter` couldn't see Homepage's `</head>` — usually
   because Homepage shipped a new gzip behavior. Fix: confirm
   `proxy_set_header Accept-Encoding "";` is still in
   `homepage-pwa/nginx.conf`.

## Theme color is wrong on installed iOS PWA

Means a stripped tag still made it to the head. View-source the
installed page (Settings → Safari → Web Inspector → connect to
Mac Console) and search for `theme-color`. If you see two `<meta>`
tags for it, one of them needs adding to the strip list in
`homepage-pwa/nginx.conf`. Restart `homepage-pwa` to apply.

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
