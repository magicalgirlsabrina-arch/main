# 🏛 Architecture — who lives where
*hosts · ports · auth · data flow*

> **3 hosts, 4 familiars.** Salem and Hilda both run on the Mac mini
> (Spellman Manor) — they share the host but listen on different
> ports (`:18789` and `:18790`). Harvey runs on the Mac Pro, Zelda on
> the MacBook Pro. The Android TV doesn't host any familiar; it's a
> viewer for the Magic Mirror page. This colocation matters for
> debugging — if the mini sleeps, *both* Salem and Hilda go offline at
> once and the **Trapped in the Linen Closet** alert fires for half
> the coven.

## Hosts and ports

```
Spellman Manor (Mac mini)             100.106.134.96
├── Salem familiar                    :18789  /api/diagnostics/prometheus  ← scraped
├── Hilda familiar                    :18790  /api/diagnostics/prometheus  ← scraped
├── Coven Mailbox server              :18792  /mail (POST), /health
└── Dashboard stack (Docker)          local
    ├── Homepage                      :3000   web UI
    ├── The Veil (nginx PWA proxy)    :3030   PWA-installable wrapper for :3000
    ├── Coven Mail Bridge             :18793  web UI + /api/* + /manifest.json
    ├── Magic Mirror (nginx)          :8080   static page + manifest.json
    ├── Beszel hub                    :8090   web UI + agent ingest
    ├── Prometheus                    :9090   web UI + scrape
    ├── Alertmanager                  :9093   web UI + alert ingest
    └── Grafana                       :3001   web UI

Harvey's Big Game (Mac Pro)           100.79.115.101
└── Harvey familiar                   :18789  + Beszel agent + (optional) Claude bridge :18794

Zelda's Labtop (MacBook Pro)           100.112.73.96
└── Zelda familiar                    :18789  + Beszel agent + (optional) Claude bridge :18794

Magic Mirror (Android TV)             — (viewer only, no listening services)
```

> **The Veil** at `:3030` is a thin nginx reverse proxy that
> transparently forwards everything to Homepage on `:3000`, but
> overrides `/manifest.json` + `/apple-touch-icon` and injects iOS
> PWA meta tags into Homepage's `<head>`. Open `:3030` in iOS Safari
> to install Spellman Manor as a home-screen app with the gold-
> sparkle Sabrina icon. See [`14-remote-access.md`](14-remote-access.md).

## Data flow

### Metrics scrape (every 30s)

```
Prometheus  ─Bearer auth→  Salem  :18789/api/diagnostics/prometheus
            ─Bearer auth→  Hilda  :18790/api/diagnostics/prometheus
            ─Bearer auth→  Zelda  :18789/api/diagnostics/prometheus
            ─Bearer auth→  Harvey :18789/api/diagnostics/prometheus
            ─plain     →  Coven Mail Bridge :18793/metrics
```

### Mail send (you click "Cast" in Spellbook UI)

```
Browser  →  Bridge :18793/api/send/zelda
                    │
                    ├─ POSTs to http://100.112.73.96:18789/hooks/agent
                    │   Authorization: Bearer <zelda hook token>
                    │   {"message":"...","name":"coven-sabrina"}
                    │
                    └─ Increments coven_mail_sent_total
                        Updates circuit breaker state
```

### Mail read (you open Spellbook UI)

```
Browser  →  Bridge :18793/api/messages
                    │
                    └─ Reads /mailbox/inbox.jsonl directly (mounted volume)
                        + /mailbox/cursor.txt
                        Returns last N lines as JSON
```

### Alert path (when something's wrong)

```
Prometheus evaluates alerts.yml every 30s
   └─ Match? POSTs to Alertmanager :9093
              └─ Routes via config.yml
                  └─ Default: shows in :9093 UI only
                  └─ Configured: ntfy / Pushover / email
```

## Volume mounts

The dashboard stack only mounts what it needs:

| Container | Mount | Why |
|---|---|---|
| coven-mail | `${COVEN_MAILBOX_DIR}` → `/mailbox` (rw) | Read inbox.jsonl + write cursor.txt |
| coven-mail | `./docs/13-familiar-handbook.md` → `/app/handbook.md` (ro) | Served at `/api/handbook` |
| homepage | `./homepage` → `/app/config` (ro) | YAML config |
| homepage-pwa | `./homepage-pwa/nginx.conf` (ro) + `./homepage-pwa` → `/pwa` (ro) | PWA proxy config + assets |
| prometheus | `./prometheus/*.yml` (ro) + `./prometheus/tokens` (ro) | Config + bearer tokens |
| grafana | `./grafana/provisioning` + `./grafana/dashboards` | Auto-import |
| magic-mirror | `./magic-mirror` (ro) | Static HTML + PWA assets |

## Authentication summary

| Layer | Auth |
|---|---|
| **Tailnet boundary** | Tailscale ACLs (the foundation — nothing here is on the public internet) |
| **OpenClaw diagnostics** | Bearer (operator-scope) — per-familiar in `prometheus/tokens/*.token` |
| **OpenClaw hooks** | Bearer (hook token) — held by the bridge in `.env` |
| **Coven Mailbox POST /mail** | Bearer (mailbox token) — held by the existing mailbox-server.py |
| **Bridge UI** | None within tailnet — Tailscale is the boundary |
| **Grafana** | Local user (`admin` / `admin` — change on first login) |

If you ever expose any of these beyond the tailnet, every "no auth" line
above needs to change.
