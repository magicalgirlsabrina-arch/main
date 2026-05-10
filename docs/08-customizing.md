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
  --ink:           #1A1B4B;   /* midnight navy bg */
  --hot-pink:      #FF3FA4;   /* Sabrina logo pink */
  --rose:          #FF6EC7;
  --bubblegum:     #FFB6D5;
  --lavender:      #C8A2DB;   /* show-accurate bedroom drape */
  --gold:          #E8C547;   /* spell gold */
  --mint:          #A8F0D0;   /* Salem's eyes */
  --holo-sky:      #A8E0FF;   /* Y2K iridescent stop */
  --text:          #F4EAFB;
  --shimmer:       linear-gradient(135deg, #FF3FA4 0%, #FF6EC7 18%,
                                  #C8A2DB 38%, #A8E0FF 58%,
                                  #E8C547 80%, #FF6EC7 100%);
  ...
}
```

Change those, and the rest of the dashboard follows. Try a different palette:
- **Salem-noir:** swap `--hot-pink` for `#0A0A0A` and `--gold` for `#3F3F3F` for a black-cat vibe
- **Other Realm green:** swap `--hot-pink` for `#39FF14` and `--lavender` for `#76FF7A`
- **Sunset Witch:** swap to coral/peach (`#FF7E73`, `#FFCB7A`, `#FFB3D9`)
- **Coquette:** swap `--hot-pink` for `#FF8FB8`, `--gold` for `#F5E6BD`, `--lavender` for `#FAD0E5`

The same vars are mirrored in `coven-mail-bridge/server.py` (Spellbook UI)
and `magic-mirror/style.css` (TV kiosk). Update all three for a coherent look.

## Swapping the SVG decorative assets

Sparkles, moons, butterflies live in `homepage/images/` — referenced
by `custom.css` via `url("/images/sparkle.svg")` etc. Each uses
`fill="currentColor"` so CSS controls the color via parent's `color:`.

To swap a sparkle for, say, a butterfly as the section heading
ornament:

```css
[class*="services-group"] h2::before {
  background: url("/images/butterfly.svg") no-repeat center / contain;
  /* color: still controls the fill */
}
```

To add a new SVG asset:
1. Drop it in `homepage/images/yourthing.svg` with `fill="currentColor"`
2. Reference in `homepage/custom.css`:
   ```css
   .my-element::before {
     content: '';
     width: 16px; height: 16px;
     display: inline-block;
     background: url("/images/yourthing.svg") no-repeat center / contain;
     color: var(--gold);
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
- "Spellman Manor", "Harvey's Workshop", "Zelda's Study"
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
