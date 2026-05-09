# OpenClaw Dashboard

A self-hosted dashboard for monitoring 4 ClawBoxes (Jetson Orin Nano) and your
other machines over Tailscale.

**Hardware**
- Mac mini — central hub (always on, runs the dashboard stack)
- 4 ClawBoxes — run OpenClaw + send metrics to the hub
- MacBook Pro / Mac Pro — show up in Beszel when online (optional)
- Android TV — bookmark the dashboard in a browser, view when you want

**Stack**
- **Homepage** — front-door dashboard with tiles per ClawBox
- **Beszel** — lightweight system monitoring (CPU/RAM/disk per host)
- **Prometheus + Grafana** — OpenClaw AI metrics + Jetson GPU/temps

Everything is reached over your tailnet — nothing exposed to the public internet.

---

## Setup walkthrough

### 1. On the Mac mini (the hub)

**Install Docker Desktop.** Download from https://www.docker.com/products/docker-desktop/,
double-click the `.dmg`, drag the whale icon to Applications, open it, click through
the prompts. You'll see a whale in your menu bar when it's running.

**Install Tailscale** if you haven't already: https://tailscale.com/download

**Get this folder onto the Mac mini.** Either clone the repo or copy the files.

**Set your gateway tokens.** Each ClawBox has an OpenClaw gateway token (from its
OpenClaw config). Copy the example env file and fill it in:

```sh
cp .env.example .env
# edit .env with your real tokens and tailnet hostnames
```

**Start the stack:**

```sh
docker compose up -d
```

That's it. Wait ~30 seconds, then visit:

- Homepage:   http://localhost:3000
- Beszel:     http://localhost:8090
- Grafana:    http://localhost:3001  (login: admin / admin, then change it)
- Prometheus: http://localhost:9090  (only needed for debugging)

To stop: `docker compose down`. To update: `docker compose pull && docker compose up -d`.

### 2. On each of the 4 ClawBoxes

Open the OpenClaw control panel and confirm the Prometheus diagnostics plugin
is enabled (it's in the gateway config — `"diagnostics-prometheus": { "enabled": true }`).
Note the gateway token; you'll need it for `.env` on the Mac mini.

Then SSH into each ClawBox and run:

```sh
curl -fsSL https://raw.githubusercontent.com/henrygd/beszel/main/supplemental/scripts/install-agent.sh | bash
```

When it prompts for the hub URL, enter your Mac mini's tailnet name, e.g.
`http://mac-mini.tailXXXX.ts.net:8090`. Copy the public key it shows you — you'll
paste it into the Beszel UI when adding the system.

For Jetson GPU + temps, install the Jetson stats exporter:

```sh
sudo pip3 install -U jetson-stats
sudo systemctl enable --now jtop.service
docker run -d --restart unless-stopped --name jetson-exporter \
  --device /dev/i2c-0 --device /dev/i2c-1 -p 9100:9100 \
  rbonghi/jetson_stats:prometheus-exporter
```

(If the ClawBox doesn't have Docker, install it first: `curl -fsSL https://get.docker.com | sh`.)

### 3. Add each ClawBox in Beszel

Open Beszel (http://mac-mini.tailXXXX.ts.net:8090), click "Add System", paste the
public key from each ClawBox, give it a name (e.g. "clawbox-1"). Repeat for the
other ClawBoxes, the Mac Pro, and the MacBook Pro.

### 4. On the Android TV

Install a browser (Brave, Firefox, etc. from the Play Store), bookmark the
Homepage URL. Open it whenever you want a glance.

---

## Customizing

- **Homepage tiles & layout** — edit `homepage/services.yaml` and `homepage/widgets.yaml`
- **Add/remove ClawBoxes from scraping** — edit `prometheus/prometheus.yml`
- **Grafana dashboards** — Jetson dashboard ID `22650` and the OpenClaw dashboard
  are auto-imported. Add more via the Grafana UI.

## Troubleshooting

- *"Can't reach a ClawBox"* — check Tailscale: `tailscale status` on the Mac mini.
- *"Prometheus shows the target as DOWN"* — bearer token wrong, or OpenClaw
  diagnostics plugin not enabled. `curl -H "Authorization: Bearer $TOKEN" http://CLAWBOX:18789/api/diagnostics/prometheus`
- *"Beszel says agent offline"* — agent service not running. On the ClawBox:
  `systemctl status beszel-agent`.
