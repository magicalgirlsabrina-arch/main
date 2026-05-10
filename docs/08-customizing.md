# 🎨 Customizing — make it yours
*`.env` · `homepage/*.yaml` · `prometheus/prometheus.yml` · CSS variables*

## Adding a new familiar

Say you spin up a 5th familiar named **Drell** on a new Mac.

1. **Add credentials to `.env`:**
   ```
   DRELL_HOST=100.x.y.z
   DRELL_GATEWAY_PORT=18789
   DRELL_GATEWAY_TOKEN=...
   DRELL_HOOK_TOKEN=...
   ```

2. **Add a Prometheus scrape job** (`prometheus/prometheus.yml`):
   ```yaml
   - job_name: drell
     metrics_path: /api/diagnostics/prometheus
     authorization:
       type: Bearer
       credentials_file: /etc/prometheus/tokens/drell.token
     static_configs:
       - targets: ['100.x.y.z:18789']
         labels: { familiar: drell, host: drells-tower, role: council }
   ```
   And drop the token: `echo -n "..." > prometheus/tokens/drell.token`

3. **Add a tile** (`homepage/services.yaml`) — copy any existing familiar's
   block and rename. Pick an icon from https://pictogrammers.com/library/mdi/.

4. **Add to the bridge** — edit `coven-mail-bridge/server.py`:
   ```python
   FAMILIARS = {
       ...,
       "drell":  {"host": os.environ.get("DRELL_HOST", ""),
                  "port": os.environ.get("DRELL_GATEWAY_PORT", "18789"),
                  "token": os.environ.get("DRELL_HOOK_TOKEN", "")},
   }
   ```
   And in the bridge's HTML, add a `<select>` option.

5. **Add to docker-compose.yml** in the `coven-mail` env block.

6. Rebuild + restart: `docker compose up -d --build coven-mail`.

## Changing the color palette

All colors live in CSS variables at the top of two files:

- `homepage/custom.css` — Homepage theme
- `magic-mirror/style.css` — Android TV kiosk

Both define:
```css
:root, html, body {
  --ink:           #0F0524;   /* deep midnight bg */
  --hot-pink:      #FF1493;   /* OG Sabrina hot pink */
  --rose:          #FF80C8;
  --bubblegum:     #FFB3D9;
  --lavender:      #B19CD9;
  --gold:          #FFD700;   /* brightest gold */
  --mint:          #5FFFE6;   /* Salem's eyes */
  --cyan:          #5BE0FF;   /* Y2K electric */
  --text:          #FFF0F8;
  --shimmer:       linear-gradient(135deg, #FF1493 0%, #FF80C8 18%,
                                  #B19CD9 38%, #5BE0FF 58%,
                                  #FFD700 80%, #FF1493 100%);
  ...
}

/* Light mode is dramatically different — peachy cream bg, deep
   purple text, deeper accents for legibility on light */
html.light, body.light {
  --ink:           #FFE4F1;   /* peachy pink cream bg */
  --hot-pink:      #C2185B;   /* deeper magenta */
  --lavender:      #7B2FBE;   /* deep electric purple */
  --gold:          #B8860B;   /* dark goldenrod */
  --text:          #2A0D35;   /* near-black aubergine */
  ...
}
```

Change those, and the rest of the dashboard follows. Try a different palette:
- **Salem-noir:** swap `--hot-pink` for `#0A0A0A` and `--gold` for `#3F3F3F` for a black-cat vibe
- **Other Realm green:** swap `--hot-pink` for `#39FF14` and `--lavender` for `#76FF7A`
- **Sunset Witch:** swap to coral/peach (`#FF7E73`, `#FFCB7A`, `#FFB3D9`)
- **Coquette:** swap `--hot-pink` for `#FF8FB8`, `--gold` for `#F5E6BD`, `--lavender` for `#FAD0E5`
- **Lisa Frank:** ramp saturation everywhere — `--hot-pink:#FF00C8`, `--cyan:#00FFFF`, `--gold:#FFFF00`, `--mint:#00FF80`

The same vars are mirrored in `coven-mail-bridge/server.py` (Spellbook UI)
and `magic-mirror/style.css` (TV kiosk). Update all three for a coherent look.

### Changing the greeting font

The greeting "Welcome home, Sabrina" uses **Pacifico** (chunky bouncy
cursive — closest commercial match to the actual show logo). To swap:

1. Pick a font from https://fonts.google.com/?category=Handwriting
   that's chunky/bouncy — try **Lobster**, **Cookie**, **Sacramento**,
   **Caveat Brush**, or **Bilbo Swash Caps**
2. Update the `@import` URL at the top of `homepage/custom.css` (and
   the same `<link>` in `coven-mail-bridge/server.py` + `magic-mirror/index.html`)
3. Change `[id*="greeting"] { font-family: 'Pacifico', cursive; ... }`
   to your new font.

The same iridescent gradient text-fill works for any cursive script.

## Swapping the SVG decorative assets

Sparkles, moons, butterflies live in `homepage/images/` — referenced
by `custom.css` via `url("/images/sparkle.svg")` etc. Each uses
`fill="currentColor"` as a fallback, but the CSS pattern below is
what actually controls the visible color.

### The mask-image pattern (important — there's a CSS gotcha)

If you do `background: url("/images/sparkle.svg")` and rely on the
SVG's `fill="currentColor"` to inherit the CSS `color:` value, **it
won't work** — `currentColor` does not inherit when SVG is used as a
background-image. The sparkle renders as black (the SVG document's
default color) on a dark background and is invisible.

The fix is to use **`mask-image`** instead, which silhouettes the SVG
shape against a CSS-controlled `background-color`:

```css
.my-sparkle {
  width: 22px; height: 22px;
  background-color: var(--gold);                              /* color */
  mask: url("/images/sparkle.svg") no-repeat center / contain;
  -webkit-mask: url("/images/sparkle.svg") no-repeat center / contain;
  filter: drop-shadow(0 0 12px var(--gold-glow));
}
```

`-webkit-mask` is included for Safari < 15.4. Modern Safari, Chrome,
and Firefox all support `mask` directly. With this pattern, you can
swap colors purely via CSS:

```css
.my-sparkle.pink   { background-color: var(--hot-pink); }
.my-sparkle.silver { background-color: #C0C0C0; }
```

To swap an asset wholesale:

```css
[class*="services-group"] h2::before {
  mask: url("/images/butterfly.svg") no-repeat center / contain;
  -webkit-mask: url("/images/butterfly.svg") no-repeat center / contain;
}
```

To add a new SVG asset:

1. Drop it in `homepage/images/yourthing.svg`. Use any colors you want
   inside the SVG — they'll be ignored when used via `mask-image`.
2. Reference in `homepage/custom.css`:
   ```css
   .my-element::before {
     content: '';
     width: 16px; height: 16px;
     display: inline-block;
     background-color: var(--gold);
     mask: url("/images/yourthing.svg") no-repeat center / contain;
     -webkit-mask: url("/images/yourthing.svg") no-repeat center / contain;
   }
   ```

For the Magic Mirror kiosk, copy the SVG into `magic-mirror/` too
(it's served by a separate nginx that doesn't see `homepage/images/`).

## Replacing the PWA app icons

To re-skin the iOS/Android home-screen icons:

| App | Icon source |
|---|---|
| **Spellman Manor** (`:3030`) | `homepage-pwa/apple-touch-icon.svg` |
| **The Spellbook** (`:18793`) | inline `_APP_ICON_SVG` in `coven-mail-bridge/server.py` |
| **The Magic Mirror** (`:8080`) | `magic-mirror/app-icon.svg` |

Edit the SVG (any vector tool — Figma, Affinity, even hand-edit), keep
512×512 viewBox + `rx="112"` rounded corner for non-iOS clients (iOS
auto-rounds), then `docker compose restart homepage-pwa coven-mail
magic-mirror` and re-install on the home screen.

## Adding a new dashboard tile that isn't a familiar

`homepage/services.yaml` — pick any section and add an entry:

```yaml
- The Other Realm:
    - My New Tool:
        href: http://localhost:1234
        description: 🌟 Whatever this is
        icon: mdi-book-music-#ff6ec7   # mdi icon + color suffix
        widget:
          type: customapi
          url: http://my-service:1234/status
          mappings:
            - field: someField
              label: My Label
```

## Renaming things

The themed names are decorative — the underlying technology doesn't care.
Search-and-replace any of these:
- "Spellman Manor", "Harvey's Workshop", "Zelda's Labtop"
- "The Discovery of Magic", "The Spellbook", "The Magic Mirror", etc.

You don't have to match the show — make it yours. The architecture
(3 hosts, 4 familiars, 1 mailbox) is what matters.

## Changing how often things update

| What | Where | Default |
|---|---|---|
| Prometheus scrape | `prometheus/prometheus.yml` `scrape_interval:` | 30s |
| Prometheus retention | `docker-compose.yml` `--storage.tsdb.retention.time=` | 30d |
| Homepage widget refresh | client-side, ~10s | — |
| Magic Mirror refresh | `magic-mirror/app.js` `setInterval(refreshAll, 10000)` | 10s |
| Spellbook history refresh | `coven-mail-bridge/server.py` HTML `setInterval(loadHistory, 5000)` | 5s |
| Alert evaluation | `prometheus/prometheus.yml` `evaluation_interval:` | 30s |

## Adding your own background image

Edit `homepage/custom.css`:

```css
body::before {
  background: url('https://your-image-url.jpg') center/cover no-repeat,
              linear-gradient(180deg, var(--midnight), var(--velvet));
}
```

For local images, drop them in `homepage/images/` and reference as
`/api/images/yours.jpg` (Homepage serves the `images/` folder automatically).
