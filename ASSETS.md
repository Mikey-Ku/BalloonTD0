# Art assets

Every sprite in the game looks for a PNG at a predictable path and draws a
procedural fallback if it is absent. **Adding art is just saving a file to the
right path**, with no code change and no registration step.

Check status at any time:

```bash
python tools/asset_report.py
```

Right now: **16 of 31 slots use real artwork; the other 15 are drawn in code.**

---

## Rules that apply to everything

- **Format**: PNG with transparency (map backgrounds excepted, those are opaque).
- **Canvas**: square, and **256×256**. The game scales down with `smoothscale`,
  so anything past roughly 2× the on-screen size is thrown away. The sprites
  inherited from the original project were 1024×1024 at 1.3 MB each for a 40 px
  slot; `tools/optimize_assets.py` exists to fix exactly that.
- **Centre the subject** with even margins. Sprites are drawn centred on their
  position, so an off-centre subject looks off-centre in game.
- **Outline**: the procedural art uses a 2–4 px dark brown outline
  (`#342216`) on everything. Matching it will keep hand-drawn and generated
  sprites looking like one set while the two are mixed.

---

## 1. Balloons: 14 needed

`balloon_images/<name>.png`

**All eleven basic balloons render at exactly 36×36.** Uniform size is
deliberate: they used to vary between 30 and 42 px, which made a mixed stack
look ragged. Please keep every basic balloon on the same canvas and the same
body size. Differentiate by **colour and pattern only**, never by scale.

| Balloon | File | On-screen | What distinguishes it now |
|---|---|---|---|
| Red | `red.png` | 36×36 | plain red |
| Blue | `blue.png` | 36×36 | plain blue |
| Green | `green.png` | 36×36 | plain green |
| Yellow | `yellow.png` | 36×36 | plain yellow |
| Pink | `pink.png` | 36×36 | plain pink |
| Black | `black.png` | 36×36 | near-black, immune to explosives |
| White | `white.png` | 36×36 | white with a shaded lower half |
| Lead | `lead.png` | 36×36 | grey metallic sheen, immune to sharp |
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
> uniform. Flip it to `True` once all fourteen exist. Turning it on with a
> partial set is what produced the mismatched look in the first place.

The five old `<name>_balloon.png` files are no longer loaded. They are
inconsistent in size and style with each other; that is what prompted this.

## 2. Towers: complete

Each tower can have **two** pieces of art:

| File | Where | Rotated? |
|---|---|---|
| `monkey_images/<key>_logo.png` | shop rack in the sidebar, 46×46 | never |
| `monkey_images/<key>_overhead.png` | on the map, 48×48 | **yes**, to face its target |

Either may be missing. A tower with only one uses it in both places, so art
can land one piece at a time without breaking anything.

| Tower | key | logo | overhead |
|---|---|---|---|
| Dart Monkey | `dart` | art | art |
| Sniper Monkey | `sniper` | art | art |
| Tack Shooter | `tack` | art | art |
| Bomb Shooter | `bomb` | art | art |
| Ice Monkey | `ice` | art | art |
| Super Monkey | `super` | art | art |
| Banana Farm | `farm` | art | n/a, never rotates, logo is fine |

**Towers are complete.** Only balloons and a music track remain.

**Overheads must point up (north).** They are rotated by `angle - 90` to aim,
so north is the zero-rotation orientation. A tower drawn facing right will aim
90° off.

**A tower with no overhead is drawn upright and never rotated.** Spinning a
three-quarter portrait looks broken, so the game leaves it alone. Only the
Banana Farm relies on that now, and it never rotates anyway.

Two more things the map art should account for:

- Towers **recoil backwards** along their facing when they fire, and a muzzle
  flash draws 18 px out in the facing direction. Keep the barrel end pointing
  cleanly up so the flash lands at the muzzle.
- The Banana Farm never rotates or fires, so neither rule applies to it.

### Sizing and orientation are handled for you

You do not need to match canvas sizes, padding, or even get the rotation
right.

**Sizing** matches **visible pixel area**, not canvas and not bounding box.
Canvas is meaningless. The art delivered so far had subjects filling between
37% and 100% of their image. Bounding box seems right but breaks on
protrusions: the Sniper's diagonal rifle made its box half again as tall as
anything else, so fitting the box rendered the monkey at half the size of the
others. Matching area ignores thin protrusions, and every tower now lands
within a few percent of the rest.

**Orientation** is corrected in code. If a sprite does not face up, add an
entry to `ORIENTATION` in [btd/sprites.py](btd/sprites.py) rather than
re-exporting. The Bomb Shooter and Ice Monkey arrived facing down, and the
Sniper's rifle pointed up-left, and all three are fixed with one line each.

Filenames follow `<key>_logo.png` / `<key>_overhead.png`. Descriptive names
like `Cannon-Overhead.png` or `Ice-Monkey-Logo.png` are also accepted (see
`ALIASES` in [btd/sprites.py](btd/sprites.py)), but the key form is preferred
It is case-exact, and macOS will happily match a mis-cased filename that
then fails on Linux and in the browser build.

## 3. Map backgrounds: all covered

`background_images/<key>.png`, **exactly 960×720**, opaque.

| Map | File | Status |
|---|---|---|
| Sprint Track | `sprint.png` | art |
| Monkey Meadow | `Background.webp` | art |
| Park Path | `park.png` | art |

Nothing needed here unless you want more maps. **To add one, send the artwork
and I will trace it**. `tools/trace_map.py` derives where balloons walk from
the image itself, so the path can never drift off the painted track.

If you want to build one without artwork, the game will paint a background
from the path instead; see the fallback note below.

The painted track has to line up with where balloons actually walk. Generate
tracing guides:

```bash
python tools/export_maps.py
```

That writes three references per map into `tools/map_export/`:

- `<key>_render.png`: what the game draws now, as a starting point
- `<key>_guide.png`: track centre line, walkable width, tower-clearance
  boundary, and entry/exit markers, for use as a tracing layer
- `<key>_buildable.png`: green where towers can go, red where they cannot

To change a track's *shape* rather than its art, edit the control points in
[btd/maps.py](btd/maps.py). Each map is about a dozen `(x, y)` points that a
Catmull-Rom spline smooths into the path. Re-run `export_maps.py` afterwards.

### Adding a whole new map

1. Add a `MapDef` to `btd/maps.py` with a new `key` and 8–14 control points.
2. Add the key to `MAP_ORDER`.
3. Run `python tools/export_maps.py` and draw over the guide.

The map picker, thumbnails, and per-map high scores pick it up automatically.

## 4. Audio

| Slot | Location | Status |
|---|---|---|
| Music | `soundtrack/`, first `.ogg`, then `.mp3`, then `.wav` | needs replacing |
| Sound effects | generated in `btd/audio.py` | synthesised, nothing needed |

Music is a directory scan, so swapping the track means dropping a file in and
deleting the old one.

⚠️ The current file is `SpotiDownloader.com - Main Theme - Tim Haywood.mp3`, a
Spotify rip. It should be replaced before this repository goes public. It is
also **excluded from browser builds**, because pygbag rejects MP3 (browsers need OGG)
and rejects filenames containing spaces, so the web version currently ships
silent. **Prefer `.ogg`**; the loader checks for it first so one file can serve
both desktop and web.

Free-to-use sources: [Incompetech](https://incompetech.com),
[OpenGameArt](https://opengameart.org),
[Pixabay Music](https://pixabay.com/music/).

---

## UI theme reference

If you want hand-drawn UI pieces later, such as panel frames, button plates or a title
logo, these are the colours the interface uses, from
[btd/config.py](btd/config.py):

| Role | Colour | Used for |
|---|---|---|
| Wood highlight | `#C0884A` | lit top bevel |
| Wood face | `#925E2E` | cabinet frame, plaques |
| Wood shade | `#5C391B` | bottom bevel, rack backing |
| Wood recess | `#321F10` | inside of the tower cubbies |
| Panel fill (cream) | `#FCF5E2` | detail panels, buttons |
| Panel fill, resting | `#E8DABE` | button faces |
| Primary text (ink) | `#3E291A` | text on cream |
| Secondary text | `#7A5E46` | labels on cream |
| Display gold | `#FFD44A` | money, prices, outlined |
| Display white | `#FFFCF2` | lives, tower names, outlined |
| Text outline | `#301C0E` | 2 px outline on all display text |
| Accent (leaf) | `#68B648` | selection, upgrade pips |
| Lives / danger | `#C63634` | health bar, menu button |
| Button blue | `#3E9AE4` | speed and pause controls |
| Button red | `#E24E42` | menu control |

The sidebar is drawn as a wooden cabinet: a beveled outer frame, a raised
plaque for money and lives, a sunken rack holding one recessed cubby per
tower, a cream detail panel, and glossy circular controls along the bottom.
All of it is drawn with primitives in [btd/ui/chrome.py](btd/ui/chrome.py),
there is no UI artwork to produce unless you want to replace it.
