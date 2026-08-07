# Balloon TD

A tower defence game in Python and Pygame. Seven towers with branching upgrade
paths, fourteen balloon types with damage-type immunities and camo/regrow/
fortified modifiers, three maps, and endless procedurally generated rounds.

Runs on the desktop, and compiles to WebAssembly so it can be played in a
browser with no install.

```bash
pip install -r requirements.txt
python main.py
```

---

## Playing

| | |
|---|---|
| `1` – `7` | select a tower to place |
| click map | place the selected tower, or inspect a placed one |
| right click / `Esc` | cancel placement or deselect |
| `Space` | start the next round |
| `F` | cycle speed (1× / 2× / 3×) |
| `P` | pause |
| `A` | toggle auto-start between rounds |
| `Tab` | cycle the selected tower's targeting priority |
| `U` / `I` | buy the next upgrade on path 1 / path 2 |
| `Delete` | sell the selected tower |

You have a fixed number of lives. Every balloon that reaches the end of the
track costs lives in proportion to how many balloons it contains, so letting a
ceramic through hurts far more than letting a red through. Clear the final
round to win.

### Things worth knowing

- **Damage types matter.** Lead balloons ignore sharp damage, black balloons
  ignore explosives. A defence built entirely from dart monkeys hits a wall the
  moment leads arrive.
- **Camo balloons** can only be targeted by towers with camo detection, which
  several upgrade paths grant.
- **Only one upgrade path per tower can be taken to its final tier.** The other
  is capped one tier below, so each tower is a decision rather than a savings
  goal.
- **Targeting priority** (first / last / close / strong) is per-tower and
  changes what a tower does far more than its stats suggest.

---

## How it is put together

```
main.py              entry point; async so the same file builds for the web
btd/
  config.py          tunable constants: layout, economy, difficulty tables
  path.py            arc-length parameterised track + spatial index
  balloons.py        balloon table, modifiers, and the damage model
  towers.py          tower table, upgrade paths, targeting
  projectiles.py     travelling shots, pierce, splash
  waves.py           authored rounds 1-40, procedural beyond
  maps.py            map definitions and background rendering
  game.py            the simulation: one run on one map
  effects.py         particles, floating text, screen shake
  audio.py           music plus synthesised sound effects
  sprites.py         character art: logos, overheads, size normalisation
  save.py            settings and records
  app.py             window, state machine, main loop
  ui/                widgets, woodwork chrome, in-game HUD, full screens
tools/               map tracing, asset reporting, image optimisation
tests/               117 unit and integration tests
```

Three decisions shape most of the code:

**The track is parameterised by distance, not by waypoint index.** A balloon
stores how many pixels it has travelled and advances by `speed * dt`. Any
speed is representable and travel is frame-rate independent. Tower placement
queries go through a uniform grid over the path rather than scanning every
waypoint.

**There is one damage model.** A balloon has hit points; damage removes them;
at zero it pops, pays its own reward exactly once, and is replaced by its
children. Leftover damage punches into one child, so a big shot tears through
a stack without the total ever exceeding what was dealt.

**The simulation runs on a fixed timestep.** Real elapsed time is accumulated
and consumed in whole 1/60 s ticks. Fast-forward runs more ticks per frame
rather than raising the frame-rate cap, so 3× is exactly 3× and a 144 Hz
display plays identically to a 60 Hz one. There are tests asserting that ten
0.1 s frames produce the same state as a hundred 0.01 s frames.

**Where balloons walk is measured from the artwork, not hand-placed.**
`tools/trace_map.py` classifies track pixels by colour, distance-transforms
the mask so every pixel knows how far it is from the track edge, and runs a
weighted Dijkstra search that hugs the centre line. It reports how far the
resulting curve strays from the traced route and warns if that becomes a
significant share of the track width, so a map cannot ship cutting corners.
The Sprint Track is a special case: a running track is a stadium curve by
construction, so its three lanes are generated analytically from measured
parameters rather than traced.

### Development

```bash
python -m unittest discover -s tests -t .
```

```bash
python tools/asset_report.py
```

```bash
python tools/export_maps.py
```

### Browser build

```bash
./build_web.sh
```

Builds with [pygbag](https://github.com/pygame-web/pygbag) into `build/web/`
and serves it at `http://localhost:8000`. Push the contents of `build/web/` to
a `gh-pages` branch to publish.

`pygbag.ini` controls what is left out of the bundle — the docs site, dev
tooling, tests, and the soundtrack. Without those exclusions the bundle is
40 MB; with them it is 2.3 MB.

> **Not yet verified end to end.** The bundle builds correctly and contains
> the right files, but it has only been loaded in a sandboxed browser where
> the pygbag runtime stalls partway through fetching its WASM wheels. Open
> `http://localhost:8000` in a normal browser and confirm it runs before
> publishing.

---

## Art

**Most sprites are drawn in code.** Every sprite looks for a PNG at a
predictable path and falls back to procedural drawing if the file is absent, so
adding real art means saving a file to the right place — no code change.

Balloons are deliberately procedural for now: all eleven basic types render at
exactly 36x36 and differ only by colour and pattern, which is what keeps a
mixed stack looking like one set. `USE_BALLOON_ART` in `btd/config.py` switches
them over once a complete set exists.

See [ASSETS.md](ASSETS.md) for every slot, its expected size, and the
orientation rules (towers face up; MOAB-class balloons face right).
`tools/export_maps.py` exports tracing guides showing exactly where each track
runs, so hand-drawn backgrounds line up with the real geometry.

`python tools/asset_report.py` prints what is still missing.

---

## Credits

This started as a team project at Olin College by **Hong Zhang**,
**Mikey Ku**, and **Jackson Gamache** — the original is at
[olincollege/BalloonTD0](https://github.com/olincollege/BalloonTD0), and its
README is kept here as [README_original.md](README_original.md). That version's
map art, balloon and monkey sprites, and overall shape carry over. The engine,
tower and balloon systems, waves, UI, and tooling were rewritten afterwards.

Inspired by Bloons TD by Ninja Kiwi. Built with [Pygame](https://www.pygame.org/).

The music is Tim Haywood's, carried over from the original project, and is not
mine to redistribute. It is excluded from the browser build and from the MIT
licence covering the source. Music loading is a directory scan, so swapping
`soundtrack/` for something you hold the rights to needs no code change.

Contributions welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).
