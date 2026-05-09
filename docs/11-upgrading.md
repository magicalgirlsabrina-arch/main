# 🆙 Upgrading

How to safely update each piece without breaking the coven.

## Updating the dashboard stack (the easy case)

```sh
./scripts/spellbook.sh update
```

This runs `docker compose pull` (downloads latest images for Homepage,
Beszel, Prometheus, Alertmanager, Grafana, nginx) then restarts. Your
config files and data volumes survive untouched.

If something breaks, roll back to a specific image version by pinning
in `docker-compose.yml`:

```yaml
homepage:
  image: ghcr.io/gethomepage/homepage:v0.10.5   # pin to known-good
```

## Updating the Coven Mail Bridge (after editing server.py)

```sh
docker compose up -d --build coven-mail
```

The `--build` flag rebuilds the bridge from your edited `server.py` instead
of pulling. ~10s.

## Updating the Magic Mirror (after editing the HTML/CSS/JS)

The Magic Mirror is just nginx serving static files, mounted read-only.
Just refresh your browser — no rebuild needed.

If you change `docker-compose.yml` for the magic-mirror service, run
`docker compose up -d magic-mirror`.

## Updating OpenClaw on each familiar host

This is the riskier upgrade because it touches the actual familiars.

1. **Mail the coven first** — give yourself an audit trail:
   ```sh
   ./scripts/coven-broadcast.sh "Sabrina is upgrading OpenClaw on $(hostname). Expect 5min downtime."
   ```

2. **Upgrade one host at a time.** SSH in, follow OpenClaw's upgrade docs,
   then sanity-check from the hub:
   ```sh
   ./scripts/coven-status.sh
   ```

3. **Check the Coven Atlas** — Grafana → http://localhost:3001 →
   Coven Atlas. The "uptime" panel shows a gap during your upgrade.
   It should fill back in cleanly.

4. **Watch for breaking changes** in OpenClaw metric names. If
   `openclaw_gateway_requests_total` becomes
   `openclaw_v2_requests_total`, you'll see "no data" in Grafana. Update
   `prometheus/alerts.yml` and `grafana/dashboards/*.json` `expr:` fields.

## Updating Tailscale

Tailscale's auto-updater handles this on macOS. To force an update:
```sh
sudo tailscale update
```

If a Tailscale upgrade breaks routing temporarily, the dashboard will
fire **Trapped in the Linen Closet**. Wait ~2min for it to settle.

## Updating the Beszel agents on each Mac

```sh
# On each familiar host:
curl -fsSL https://raw.githubusercontent.com/henrygd/beszel/main/supplemental/scripts/install-agent.sh | bash
```

The installer detects the existing service and updates it.

## Updating Claude Code on each Mac

```sh
# On each Mac with claude installed:
npm update -g @anthropic-ai/claude-code
# or, if you used the install script:
curl -fsSL https://anthropic.com/install-claude-code | bash
```

Restart the Claude Bridge after upgrade:
```sh
launchctl unload ~/Library/LaunchAgents/ai.openclaw.claude-bridge.plist
launchctl load   ~/Library/LaunchAgents/ai.openclaw.claude-bridge.plist
```

## Backups

The mailbox file is the only piece of unique state worth backing up.

```sh
# Daily, on Spellman Manor:
rsync -a ~/.openclaw/workspace/coven-mailbox/ /Volumes/Katrina/coven-mailbox-backup/
```

Add to crontab:
```sh
0 3 * * * rsync -a ~/.openclaw/workspace/coven-mailbox/ /Volumes/Katrina/coven-mailbox-backup/
```

The dashboard's Prometheus + Grafana data are not worth backing up — they
re-populate from live scrapes within 30 days.

Your `.env` (with all the tokens) **is** worth backing up to a password
manager like 1Password.

## Rollback strategy

The `claude/openclaw-dashboard-research-GFWWK` branch is git-versioned.
To roll back to a prior commit:

```sh
git log --oneline                       # find a known-good commit
git checkout <commit-sha> -- .          # restore files (keeps your .env)
./scripts/spellbook.sh restart
```

To roll back a specific service while keeping the rest current:

```sh
docker compose stop homepage
docker pull ghcr.io/gethomepage/homepage:v0.10.4
# edit docker-compose.yml to pin that version
docker compose up -d homepage
```
