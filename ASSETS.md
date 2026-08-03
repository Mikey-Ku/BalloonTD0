# Art assets

Every sprite in the game looks for a PNG at a predictable path. If the file is
there it is used; if not, the game draws a procedural placeholder in a
matching style. **Adding art is just saving a file to the right path** — no
code change, no registration step, no rebuild.

Check what is still missing at any time:

```bash
python tools/asset_report.py
```

As of now: **11 of 24 slots have real artwork, 13 are placeholders.**

---

## Rules that apply to everything

- **Format**: PNG with a transparent background (map backgrounds excepted).
- **Source size**: draw larger than the on-screen size and let the game scale
  down — it uses `smoothscale`, so a 256×256 source looks better than an exact
  match. Square canvases only for sprites; the game scales to a square.
- **Anchor**: sprites are drawn centred on their position. Keep the subject
  centred in the canvas with even margins, or it will look off-centre in game.

---

## Balloons

`balloon_images/<name>.png`

Drawn upright, no rotation applied. The size column is the on-screen size —
draw at 4–8× that and let it scale.

| Balloon | File | On-screen | Status |
|---|---|---|---|
| Red | `balloon_images/red_balloon.png` | 30×30 | art |
| Blue | `balloon_images/blue_balloon.png` | 32×32 | art |
| Green | `balloon_images/green_balloon.png` | 34×34 | art |
| Yellow | `balloon_images/yellow_balloon.png` | 34×34 | art |
| Pink | `balloon_images/pink_balloon.png` | 36×36 | art |
| Black | `balloon_images/black.png` | 32×32 | **placeholder** |
| White | `balloon_images/white.png` | 32×32 | **placeholder** |
| Lead | `balloon_images/lead.png` | 34×34 | **placeholder** |
| Zebra | `balloon_images/zebra.png` | 34×34 | **placeholder** |
| Rainbow | `balloon_images/rainbow.png` | 38×38 | **placeholder** |
| Ceramic | `balloon_images/ceramic.png` | 42×42 | **placeholder** |
| MOAB | `balloon_images/moab.png` | 84×84 | art |
| BFB | `balloon_images/bfb.png` | 116×116 | **placeholder** |
| ZOMG | `balloon_images/zomg.png` | 148×148 | **placeholder** |

Notes:

- **MOAB-class** (MOAB, BFB, ZOMG) are the only balloons that rotate — they
  turn to face along the track. Draw them **pointing right** (east).
- **Camo, regrow, and fortified** are modifiers applied on top of the base
  sprite in code, not separate files. Camo gets a green wash, fortified gets a
  gold outline. If you would rather draw those variants yourself, say so and
  I will extend the lookup to check `<name>_camo.png` and friends first.
- The existing five basics use the `<name>_balloon.png` suffix from the
  original project. Both `<name>.png` and `<name>_balloon.png` are accepted;
  plain `<name>.png` wins if both exist.

## Towers

`monkey_images/<key>.png`

| Tower | File | On-screen | Status |
|---|---|---|---|
| Dart Monkey | `monkey_images/dart_monkey.png` | 40×40 | art |
| Sniper Monkey | `monkey_images/sniper_monkey.png` | 40×40 | art |
| Tack Shooter | `monkey_images/tac_tower.png` | 40×40 | art |
| Bomb Shooter | `monkey_images/bomb.png` | 40×40 | **placeholder** |
| Ice Monkey | `monkey_images/ice.png` | 40×40 | **placeholder** |
| Super Monkey | `monkey_images/super_monkey.png` | 40×40 | art |
| Banana Farm | `monkey_images/farm.png` | 40×40 | **placeholder** |

**Towers must be drawn facing up (north).** Sprites are rotated by
`angle - 90` to aim at their target, so north is the zero-rotation
orientation. A tower drawn facing right will aim 90° off.

The Banana Farm never rotates (it does not attack), so its orientation does
not matter.

The same sprite is reused for the sidebar shop icon at 26×26, so keep the
silhouette readable when small.

## Map backgrounds

`background_images/<key>.png` — must be **exactly 960×720**.

| Map | File | Status |
|---|---|---|
| Monkey Meadow | `background_images/Background.webp` | art |
| Switchback | `background_images/switchback.png` | **placeholder** |
| Coil | `background_images/spiral.png` | **placeholder** |

The painted track has to line up with where balloons actually walk, or tower
placement will look wrong. To get the exact geometry:

```bash
python tools/export_maps.py
```

That writes three references per map into `tools/map_export/`:

- `<key>_render.png` — what the game currently draws, as a starting point
- `<key>_guide.png` — the track centre line, walkable width, tower-clearance
  boundary, and entry/exit markers, for use as a tracing layer
- `<key>_buildable.png` — green where towers can go, red where they cannot

Paint over the guide, save to `background_images/<key>.png`, and the game
picks it up on next launch.

If you want to change a track's *shape* rather than just its art, edit the
control points in `btd/maps.py` — each map is about a dozen `(x, y)` points
that a Catmull-Rom spline smooths into the path. Re-run `export_maps.py`
afterwards to get an updated guide.

## Adding a whole new map

1. Add a `MapDef` to `btd/maps.py` with a new `key` and 8–14 control points.
2. Add the key to `MAP_ORDER`.
3. Run `python tools/export_maps.py` and draw over the guide.

The map picker, thumbnails, and per-map high scores all pick it up
automatically.

## Audio

| Slot | Location | Status |
|---|---|---|
| Music | `soundtrack/` — first `.ogg`/`.mp3`/`.wav` found | see below |
| Sound effects | generated in `btd/audio.py` | synthesised |

Music is a **directory scan**, not a hardcoded filename, so swapping the track
means dropping a file in `soundtrack/` and deleting the old one.

⚠️ The file currently in `soundtrack/` is
`SpotiDownloader.com - Main Theme - Tim Haywood.mp3` — a Spotify rip. It
should be replaced before this repository goes public. Good sources for
free-to-use game music: [Incompetech](https://incompetech.com),
[OpenGameArt](https://opengameart.org), or [Pixabay
Music](https://pixabay.com/music/).

Sound effects (pop, place, upgrade, sell, leak, round-complete) are
synthesised into raw PCM at startup rather than loaded from files, so there is
nothing to draw or license. If you would rather use recorded samples, they can
be swapped in `btd/audio.py`.
