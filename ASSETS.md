# Art assets

Every sprite in the game looks for a PNG at a predictable path and draws a
procedural fallback if it is absent. **Adding art is just saving a file to the
right path** — no code change, no registration step.

Check status at any time:

```bash
python tools/asset_report.py
```

Right now: **5 of 24 slots use real artwork; the other 19 are drawn in code.**

---

## Rules that apply to everything

- **Format**: PNG with transparency (map backgrounds excepted — those are opaque).
- **Canvas**: square, and **256×256**. The game scales down with `smoothscale`,
  so anything past roughly 2× the on-screen size is thrown away. The sprites
  inherited from the original project were 1024×1024 at 1.3 MB each for a 40 px
  slot; `tools/optimize_assets.py` exists to fix exactly that.
- **Centre the subject** with even margins. Sprites are drawn centred on their
  position, so an off-centre subject looks off-centre in game.
- **Outline**: the procedural art uses a 2–4 px dark brown outline
  (`#34221 6`) on everything. Matching it will keep hand-drawn and generated
  sprites looking like one set while the two are mixed.

---

## 1. Balloons — 14 needed

`balloon_images/<name>.png`

**All eleven basic balloons render at exactly 36×36.** Uniform size is
deliberate: they used to vary between 30 and 42 px, which made a mixed stack
look ragged. Please keep every basic balloon on the same canvas and the same
body size — differentiate by **colour and pattern only**, never by scale.

| Balloon | File | On-screen | What distinguishes it now |
|---|---|---|---|
| Red | `red.png` | 36×36 | plain red |
| Blue | `blue.png` | 36×36 | plain blue |
| Green | `green.png` | 36×36 | plain green |
| Yellow | `yellow.png` | 36×36 | plain yellow |
| Pink | `pink.png` | 36×36 | plain pink |
| Black | `black.png` | 36×36 | near-black — immune to explosives |
| White | `white.png` | 36×36 | white with a shaded lower half |
| Lead | `lead.png` | 36×36 | grey metallic sheen — immune to sharp |
| Zebra | `zebra.png` | 36×36 | black and white vertical stripes |
| Rainbow | `rainbow.png` | 36×36 | six horizontal colour bands |
| Ceramic | `ceramic.png` | 36×36 | brown with plate seams |
| MOAB | `moab.png` | 80×80 | blimp, blue-purple |
| BFB | `bfb.png` | 108×108 | blimp, red |
| ZOMG | `zomg.png` | 140×140 | blimp, green |

**Orientation**: basics are drawn upright and never rotate. **MOAB-class rotate
to face along the track, so draw them pointing right (east).**

**Modifiers are applied in code, not drawn by you.** Camo gets a green wash,
fortified gets a gold band inside the outline, regrow is untinted. So you need
one file per balloon, not one per combination.

> ⚠️ Balloon art is currently **switched off**. `USE_BALLOON_ART = False` in
> [btd/config.py](btd/config.py) forces procedural drawing so the set stays
> uniform. Flip it to `True` once all fourteen exist — turning it on with a
> partial set is what produced the mismatched look in the first place.

The five old `<name>_balloon.png` files are no longer loaded. They are
inconsistent in size and style with each other; that is what prompted this.

## 2. Towers — 3 needed

`monkey_images/<key>.png`, all **40×40** on screen.

| Tower | File | Status |
|---|---|---|
| Dart Monkey | `dart_monkey.png` | art |
| Sniper Monkey | `sniper_monkey.png` | art |
| Tack Shooter | `tac_tower.png` | art |
| Super Monkey | `super_monkey.png` | art |
| **Bomb Shooter** | `bomb.png` | **needed** |
| **Ice Monkey** | `ice.png` | **needed** |
| **Banana Farm** | `farm.png` | **needed** |

**Towers must face up (north).** Sprites are rotated by `angle - 90` to aim, so
north is the zero-rotation orientation. A tower drawn facing right will aim 90°
off.

Two consequences of how towers animate, worth designing around:

- They **recoil backwards** along their facing when they fire, and a muzzle
  flash is drawn 18 px out from the centre in the facing direction. Leave the
  "barrel" end pointing cleanly up so the flash lands at the muzzle.
- The same sprite is reused as the shop icon at **28×28**, so the silhouette
  has to survive being small.

The Banana Farm never rotates or fires, so neither rule applies to it.

## 3. Map backgrounds — 2 needed

`background_images/<key>.png`, **exactly 960×720**, opaque.

| Map | File | Status |
|---|---|---|
| Monkey Meadow | `Background.webp` | art |
| **Switchback** | `switchback.png` | **needed** |
| **Coil** | `spiral.png` | **needed** |

The painted track has to line up with where balloons actually walk. Generate
tracing guides:

```bash
python tools/export_maps.py
```

That writes three references per map into `tools/map_export/`:

- `<key>_render.png` — what the game draws now, as a starting point
- `<key>_guide.png` — track centre line, walkable width, tower-clearance
  boundary, and entry/exit markers, for use as a tracing layer
- `<key>_buildable.png` — green where towers can go, red where they cannot

To change a track's *shape* rather than its art, edit the control points in
[btd/maps.py](btd/maps.py) — each map is about a dozen `(x, y)` points that a
Catmull-Rom spline smooths into the path. Re-run `export_maps.py` afterwards.

### Adding a whole new map

1. Add a `MapDef` to `btd/maps.py` with a new `key` and 8–14 control points.
2. Add the key to `MAP_ORDER`.
3. Run `python tools/export_maps.py` and draw over the guide.

The map picker, thumbnails, and per-map high scores pick it up automatically.

## 4. Audio

| Slot | Location | Status |
|---|---|---|
| Music | `soundtrack/` — first `.ogg`, then `.mp3`, then `.wav` | needs replacing |
| Sound effects | generated in `btd/audio.py` | synthesised, nothing needed |

Music is a directory scan, so swapping the track means dropping a file in and
deleting the old one.

⚠️ The current file is `SpotiDownloader.com - Main Theme - Tim Haywood.mp3`, a
Spotify rip. It should be replaced before this repository goes public. It is
also **excluded from browser builds** — pygbag rejects MP3 (browsers need OGG)
and rejects filenames containing spaces, so the web version currently ships
silent. **Prefer `.ogg`**; the loader checks for it first so one file can serve
both desktop and web.

Free-to-use sources: [Incompetech](https://incompetech.com),
[OpenGameArt](https://opengameart.org),
[Pixabay Music](https://pixabay.com/music/).

---

## UI theme reference

If you want hand-drawn UI pieces later — panel frames, button plates, a title
logo — these are the colours the interface uses, from
[btd/config.py](btd/config.py):

| Role | Colour |
|---|---|
| Panel fill (cream) | `#FCF5E2` |
| Panel fill, resting | `#E8DABE` |
| Frame / border (wood) | `#704A2C` |
| Sidebar backdrop | `#4A301E` |
| Primary text (ink) | `#3E291A` |
| Secondary text | `#7A5E46` |
| Accent (leaf) | `#68B648` |
| Money | `#CE8E16` |
| Lives / danger | `#C63634` |
