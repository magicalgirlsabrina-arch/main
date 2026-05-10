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
http://spellman-manor.<your-tailnet>.ts.net:3000     ← Homepage (raw)
http://spellman-manor.<your-tailnet>.ts.net:3030     ← Spellman Manor (PWA-installable)
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

## Installing as an iOS web app (PWA)

Three apps are installable. Each has its own themed icon:

| App | URL | Icon | Use it for |
|---|---|---|---|
| **Spellman Manor** | `:3030` ← (PWA-wrapped Homepage) | crescent + sparkle on pink/violet | the full dashboard |
| **The Spellbook** | `:18793/` | gold sparkle on pink/violet | mail + console + surveillance |
| **The Magic Mirror** | `:8080` | gold crescent on midnight | TV / kiosk view |

> **Important on iOS**: open in **Safari** (not Chrome — only Safari
> can install PWAs on iOS).

For each one, the install flow is identical:

1. Open the URL in Safari
2. Tap the **Share** button (square with up arrow)
3. Scroll down → **Add to Home Screen**
4. Name it → **Add**

The app icon appears on your home screen. Tap → launches **fullscreen**
with no Safari chrome, status bar matches the dark theme, no address
bar visible. Native-app feel.

### Why the `:3030` proxy exists for Homepage

Homepage (the `:3000` dashboard at the heart of this stack) doesn't
expose enough config to fully customize its PWA manifest, apple-touch-icon,
or iOS-specific meta tags. So a small nginx container — **The Veil**
on `:3030` — sits in front of Homepage and:

1. Serves a custom `/manifest.json` with the Spellman Manor name + Sabrina theme
2. Overrides `/apple-touch-icon.png` (and `.svg` etc.) with our gold-sparkle icon
3. Injects iOS PWA meta tags into the `<head>` of every Homepage HTML response

The actual Homepage app at `:3000` keeps working unchanged. `:3030` is
just the "PWA-installable port" — open it for the install flow, then
it behaves identically to `:3000` in every other way (it's a transparent
reverse proxy).

If you don't care about the custom icon and just want install-as-app,
`:3000` will install with whatever favicon Homepage exposes — it works,
just looks generic.

### Why The Veil's nginx config strips tags before injecting

If we just *injected* PWA tags before `</head>`, you'd get duplicates
when Homepage already emits its own `<meta name="theme-color">` or
`<link rel="manifest">`. iOS Safari + Android Chrome handle duplicate
`apple-touch-icon` by picking the best size (so duplicates are
harmless), but `theme-color` duplicates pick the *first* — meaning
Homepage's default theme would win over our hot pink.

Fix: the nginx config does `sub_filter_once off` plus a list of
"strip" directives that rename Homepage's existing tags
(`name="theme-color"` → `name="theme-color-stripped"`) so browsers
ignore them. Then injects ours fresh before `</head>`. View-source
shows the originals preserved with `data-veil-stripped` attribute —
useful for debugging, invisible to browsers.

End result: no duplicates, no infinite-replace loops, no upstream
edit to Homepage.

### What makes this work

The bridge serves three PWA assets:
- `/manifest.json` — declares it as an installable app with name, icon, theme
- `/icon-180.svg` — the apple-touch-icon (gold sparkle on pink-violet bg)
- `/favicon.svg` — small icon for the address bar

Plus meta tags in the HTML head:
```html
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#FF1493">
```

All served by the bridge itself — no extra setup.

### What it looks like installed

| Spec | Spellman Manor (`:3030`) | Spellbook (`:18793`) | Magic Mirror (`:8080`) |
|---|---|---|---|
| Icon | Crescent + sparkle on pink/violet/midnight | Gold sparkle on pink/violet | Gold crescent on midnight |
| Name on home screen | "Spellman" | "Spellbook" | "Mirror" |
| Status bar | Translucent over dark | Translucent over dark | Translucent over dark |
| Display mode | `standalone` | `standalone` | `standalone` |
| Orientation | any | portrait | any |

### Troubleshooting iOS PWA install

- **"Add to Home Screen" missing** → you opened it in Chrome/Firefox, not Safari. Use Safari.
- **App icon shows as a screenshot of the page** → manifest didn't load.
  Confirm by hitting one of these in your browser:
  ```
  http://spellman-manor.<tailnet>.ts.net:3030/manifest.json    ← Homepage PWA
  http://spellman-manor.<tailnet>.ts.net:18793/manifest.json   ← Spellbook
  http://spellman-manor.<tailnet>.ts.net:8080/manifest.json    ← Magic Mirror
  ```
  Each should return JSON with a Sabrina-themed icon path.
- **The Veil (`:3030`) returns 502 Bad Gateway** → Homepage container (`:3000`) isn't running. `docker compose ps homepage` to check.
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
