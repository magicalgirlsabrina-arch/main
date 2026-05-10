# 📚 Spellman Manor docs
*reading order + index*

Reading order if you're new:

1. [`01-overview.md`](01-overview.md) — what this whole thing is
2. [`00-glossary.md`](00-glossary.md) — terminology key
3. [`02-setup.md`](02-setup.md) — step-by-step install
4. [`03-architecture.md`](03-architecture.md) — who lives where + ports + data flow

For the familiars themselves:
- **[`13-familiar-handbook.md`](13-familiar-handbook.md)** — the manual
  you give to Salem to distribute. Covers every endpoint with Python
  snippets. Each familiar can also fetch it live:
  ```sh
  curl http://100.106.134.96:18793/api/handbook
  ```

For day-to-day:
- [`05-coven-mail.md`](05-coven-mail.md) — coven mail + the bridge API
- [`07-alerts.md`](07-alerts.md) — what each themed alert means
- [`09-debugging.md`](09-debugging.md) — peer debugging + workflows
- [`10-magic-mirror.md`](10-magic-mirror.md) — the TV kiosk
- [`12-watchdog-cron.md`](12-watchdog-cron.md) — wiring cron + watchdog heartbeats
- [`14-remote-access.md`](14-remote-access.md) — Tailscale on iOS + iOS web app install

When something breaks:
- [`04-troubleshooting.md`](04-troubleshooting.md)

When you're customizing or upgrading:
- [`08-customizing.md`](08-customizing.md) — adding familiars, changing colors, etc.
- [`11-upgrading.md`](11-upgrading.md) — safe upgrades, backups, rollbacks
- [`06-claude-on-macs.md`](06-claude-on-macs.md) — *optional* Claude Code integration (`--with-claude`)
