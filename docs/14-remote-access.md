# 📱 Remote access + iOS web app
*tailscale on iOS · tailscale funnel · PWA install*

The dashboard runs on the Mac mini (Spellman Manor). This doc covers
the three ways to reach it from somewhere else, and how to install
**The Spellbook** as a real iOS web app on your home screen.

> **TL;DR for "I just want it on my phone"**: install the **Tailscale**
> app from the App Store, sign in with the same account as the mini.
> Then open `http://spellman-manor.<your-tailnet>.ts.net:18793` in
> Safari → Share button → **Add to Home Screen**. Done.

---

## Option 1 — Tailscale on iOS (recommended)

The simplest, most secure way. The iPhone joins the same private
network as the mini; nothing is exposed to the public internet.

**One-time setup (5 min):**
1. Install **[Tailscale](https://apps.apple.com/app/tailscale/id1470499037)** from the App Store.
2. Open the app, **Log in**, sign in with the same account as the mini.
3. Allow the VPN profile when iOS prompts.

**You're done.** The mini is now reachable from your phone whenever
Tailscale is "on." Test:
```
http://spellman-manor.<your-tailnet>.ts.net:3000     ← Homepage
http://spellman-manor.<your-tailnet>.ts.net:18793/   ← Spellbook
http://spellman-manor.<your-tailnet>.ts.net:8080     ← Magic Mirror
```

(Find `<your-tailnet>` from `./scripts/spellbook.sh tailnet` on the mini.)

**Pros:**
- Zero exposure to the public web
- Works from anywhere with internet
- Free for personal use (3+ users on free tier)
- Encrypts everything

**Cons:**
- Visitors who want to view the dashboard would also need Tailscale + an invite to your tailnet
- iOS battery: Tailscale uses VPN APIs, ~1-3% extra/day

---

## Option 2 — Tailscale Funnel (public URL, no client install)

If you want to share the dashboard with someone who doesn't have
Tailscale, Funnel exposes a service via Tailscale's edge servers and
gives you a public `https://...ts.net` URL.

**Set it up on the mini:**
```sh
# Enable Funnel on your tailnet (one-time, via the admin console):
#   https://login.tailscale.com/admin/settings/general → enable HTTPS + Funnel

# Expose Spellbook to the public web:
sudo tailscale funnel --bg --https=443 18793
# → "Available on the internet:
#    https://spellman-manor.<tailnet>.ts.net/"
```

That URL works in any browser, no Tailscale needed on the visitor side.

**Caveats:**
- **Public means public.** There's no app-level auth on the bridge.
  Anyone with the URL can read coven mail, send messages, etc.
  Either: (a) only enable Funnel temporarily when sharing, (b) put
  basic auth in front via `tailscale serve` + a reverse proxy, (c)
  build app-level auth into the bridge.
- Funnel has rate limits and is intended for low-traffic personal use.
- Only certain ports are allowed (443, 8443, 10000) — Tailscale
  handles the routing, you don't pick the external port.

**To revoke** when you're done sharing:
```sh
sudo tailscale funnel --bg --https=443 off
```

---

## Option 3 — `tailscale serve` (HTTPS within the tailnet, no Funnel)

A middle ground: clean `https://` URLs reachable only from devices on
your tailnet (no Funnel = no public exposure).

```sh
./scripts/tailscale-serve.sh
```

This maps the dashboard ports to clean HTTPS URLs on the tailnet:
- `https://spellman-manor.<tailnet>.ts.net/`        → Homepage
- `https://spellman-manor.<tailnet>.ts.net/spellbook` → Spellbook
- `https://spellman-manor.<tailnet>.ts.net/mirror`  → Magic Mirror

(The script's actual mappings depend on what you've configured — see
the script comments.)

Combine with Option 1: install Tailscale on iPhone, then bookmark the
HTTPS URL for the cleanest experience.

---

## Installing The Spellbook as an iOS web app (PWA)

Once you can reach the URL on your iPhone, install it as a real app:

1. Open Spellbook in **Safari** (not Chrome — only Safari can install
   PWAs on iOS):
   ```
   http://spellman-manor.<tailnet>.ts.net:18793/
   ```
2. Tap the **Share** button (square with up arrow).
3. Scroll down → **Add to Home Screen**.
4. Name it "Spellbook" → **Add**.

The app icon (gold sparkle on pink-violet gradient) appears on your
home screen. Tap to open. It launches **fullscreen** with no Safari
chrome — just the dashboard. Status bar matches the dark theme.

The same works for the Magic Mirror page (port 8080).

### What makes this work

The bridge serves three PWA assets:
- `/manifest.json` — declares it as an installable app with name, icon, theme
- `/icon-180.svg` — the apple-touch-icon (gold sparkle on pink-violet bg)
- `/favicon.svg` — small icon for the address bar

Plus meta tags in the HTML head:
```html
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#FF3FA4">
```

All served by the bridge itself — no extra setup.

### What it looks like installed

| Spec | Spellbook | Magic Mirror |
|---|---|---|
| Icon | Gold sparkle on pink-violet gradient | Gold crescent on midnight |
| Name on home screen | "Spellbook" | "Mirror" |
| Status bar | Translucent over dark | Translucent over dark |
| Display mode | `standalone` (no browser chrome) | `standalone` |
| Orientation | `portrait` | `any` |

### Troubleshooting iOS PWA install

- **"Add to Home Screen" missing** → you opened it in Chrome/Firefox, not Safari. Use Safari.
- **App icon shows as a screenshot of the page** → manifest didn't load. Confirm `/manifest.json` returns JSON: `curl http://spellman-manor.<tailnet>.ts.net:18793/manifest.json`
- **Opens in Safari with chrome instead of fullscreen** → `apple-mobile-web-app-capable` meta tag missing. Hard-refresh in Safari, then re-install.
- **Notch / home indicator overlapping content** → fixed via `viewport-fit=cover` + `env(safe-area-inset-*)` padding in CSS. Already handled.

---

## Android install

Same pattern, even cleaner:

1. Open the URL in Chrome
2. Menu → **Install app** (or **Add to Home Screen**)
3. Chrome installs it as a real app with the SVG icon.

---

## Desktop install

Chrome/Edge/Brave on macOS, Windows, Linux:
1. Open the URL
2. Address bar shows an "install" icon (computer with down arrow) → click
3. Becomes a standalone window app

---

## Picking a default access pattern

| Use case | Best option |
|---|---|
| You at home / on the road, your devices | Tailscale on iOS + Spellbook PWA |
| Show a friend without setup | Tailscale Funnel (turn off after) |
| Family member with a guest tailnet account | Standard Tailscale invite |
| Fully public dashboard for the world | Don't (no app-level auth) |

For Sabrina specifically: Tailscale on iPhone + install the Spellbook
PWA is the answer 95% of the time. Funnel is for the rare "let me
quickly show this to someone" moment.

---

## Future hardening (if you ever go fully public)

The bridge currently has zero app-level auth. Tailscale is the
boundary. If you ever expose anything beyond Tailscale, add:

1. **Basic auth via `tailscale serve` + a reverse proxy** (Caddy/nginx)
   sitting in front of the bridge.
2. **Per-endpoint bearer tokens** in the bridge code (most invasive).
3. **An auth proxy** like Authelia or Pomerium (overkill for a homelab
   but the proper enterprise pattern).

For now: Tailscale is enough.
