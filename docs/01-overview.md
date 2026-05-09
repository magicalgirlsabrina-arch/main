# ✨ Overview — what this whole thing is

A self-hosted, themed dashboard for Sabrina's Spellman Manor setup. It does
four things:

1. **Shows the household at a glance** — which familiars are awake, what
   models they're running, how busy they are.
2. **Routes coven mail** — read Salem's mailbox + send messages to any
   familiar (or broadcast to all) from a web UI.
3. **Watches health & alerts** — system metrics (CPU/RAM/disk per Mac),
   OpenClaw API metrics (spells/sec, latency), and themed alerts when
   something goes wrong.
4. **Lets familiars debug each other** — peer-ping, circuit breakers,
   broadcast self-tests, an HTTP "ask Claude" endpoint each Mac can
   expose for the others.

## Mental model

```
                        ┌───────────────────────┐
                        │   Spellman Manor      │  Mac mini · always on
                        │   (the hub)           │
                        │                       │
                        │  Dashboard stack      │  ← Docker Compose
                        │   • Homepage          │
                        │   • Spellbook UI      │
                        │   • Magic Mirror      │
                        │   • Beszel hub        │
                        │   • Prometheus        │
                        │   • Alertmanager      │
                        │   • Grafana           │
                        │   • Coven Mail Bridge │
                        │                       │
                        │  Native services:     │  ← already exist
                        │   • Salem  :18789     │
                        │   • Hilda  :18790     │
                        │   • Mailbox:18792     │
                        └─────────┬─────────────┘
                                  │ Tailscale
              ┌───────────────────┼─────────────────┐
              │                   │                 │
       ┌──────▼─────┐      ┌──────▼─────┐    ┌──────▼─────┐
       │ Mac Pro    │      │ MacBook Pro│    │ Android TV │
       │ Harvey's   │      │ Zelda's    │    │ Magic      │
       │ Workshop   │      │ Study      │    │ Mirror     │
       │            │      │            │    │            │
       │ Harvey     │      │ Zelda      │    │ (viewer:   │
       │  :18789    │      │  :18789    │    │  port 8080)│
       │            │      │            │    │            │
       │ + Beszel   │      │ + Beszel   │    │            │
       │ + Claude   │      │ + Claude   │    │            │
       │   bridge   │      │   bridge   │    │            │
       └────────────┘      └────────────┘    └────────────┘
```

## Why these tools (in plain English)

- **Homepage** is a YAML-configured dashboard with widgets. We use it as
  the front door — clickable tiles, live status from each familiar.
- **Beszel** is a tiny monitoring tool. Each Mac runs a 10MB agent; the
  hub aggregates them. Way lighter than full-fat Grafana for this.
- **Prometheus** scrapes OpenClaw's built-in `/api/diagnostics/prometheus`
  endpoint every 30s and stores 30 days of metrics.
- **Alertmanager** routes alerts (handles deduping, grouping, sending
  to ntfy / email / Pushover when configured).
- **Grafana** draws the deep dashboards (uptime, throughput) on top of
  Prometheus data.
- **Docker Compose** wraps all the above into one file you start with
  `docker compose up -d`.
- **The Coven Mail Bridge** is custom — a tiny Python HTTP service
  written specifically for this dashboard. It reads Salem's existing
  mailbox file and exposes a friendlier API + a Spellbook web UI.

## What gets read vs. written

- The dashboard **reads** OpenClaw metrics, system stats, the mailbox file.
- The dashboard **writes** only when *you* click "Send" or "Broadcast" or
  "Mark all read" — in which case it uses the existing OpenClaw hook
  endpoints with the existing tokens.
- Nothing else on the Macs is touched. Coven Mail's underlying server,
  cursor file, and inbox file are all left exactly as designed.
