# Contributing

Contributions are welcome, including from people who have never touched a game
engine. Most of this codebase is ordinary Python.

## Getting it running

```bash
git clone https://github.com/Mikey-Ku/BalloonTD0.git
cd BalloonTD0
pip install -r requirements.txt
python main.py
```

The only runtime dependency is pygame. If the game starts, you have everything
you need to work on it.

## Before you open a pull request

```bash
python -m unittest discover -s tests -t .
```

```bash
pip install pylint && python -m pylint btd main.py
```

Both run in CI on every push and pull request, and both currently pass with
nothing outstanding, so anything either one reports is something you added.

CI also boots the game headless. The test suite exercises systems in isolation
and never constructs the game itself, so an import cycle or a missing startup
asset passes all 117 tests and still fails on launch.

## The three ideas the code is built on

Worth knowing before changing anything in `btd/`, because a change that fights
one of these will look like it works and break subtly.

**The track is measured in distance, not waypoints.** A balloon stores how many
pixels it has travelled and advances by `speed * dt`. Any speed is
representable and movement does not depend on frame rate. An earlier version
advanced a waypoint index by `int(speed)`, which truncated three different
balloon speeds to the same value and made three balloon types identical.

**There is exactly one damage model.** A balloon has hit points, damage removes
them, at zero it pops, pays its reward once, and is replaced by its children.
Leftover damage carries into one child. If you find yourself adding a second
place where a balloon can die or pay out, that is the bug the rewrite existed
to fix.

**The simulation runs on a fixed 1/60 s timestep.** Real elapsed time is
accumulated and consumed in whole ticks. Fast-forward runs more ticks per
frame rather than raising the frame-rate cap, so 3x is exactly 3x and a 144 Hz
display plays identically to a 60 Hz one. There are tests asserting that ten
0.1 s frames produce the same state as a hundred 0.01 s frames. Please keep
them passing.

## Adding art

Every sprite looks for a PNG at a predictable path and falls back to drawing
itself procedurally if the file is missing, so adding art means saving a file
in the right place with no code change.

```bash
python tools/asset_report.py
```

That prints every slot, its expected filename and size, and whether something
is currently filling it. `ASSETS.md` has the orientation rules: towers face up,
MOAB-class balloons face right.

Balloons are deliberately procedural for now, so that all eleven basic types
share one silhouette and one outline weight. `USE_BALLOON_ART` in
`btd/config.py` switches them over once a complete, consistently sized set
exists. A partial set will look worse than the procedural version, not better.

## Adding a map

Map paths are derived from the artwork rather than hand-placed.
`tools/trace_map.py` colour-classifies the track pixels, distance-transforms
the mask, and runs a weighted search along the centre line. It reports how far
the resulting curve strays from the traced route and warns when that becomes a
significant fraction of the track width, so a map cannot quietly ship with
balloons cutting corners.

It needs numpy and Pillow, which are not in `requirements.txt` because playing
the game does not need them:

```bash
pip install numpy pillow
```

## Things worth knowing

- **Line length is 88** and pylint enforces it. There is no autoformatter
  configured; the repo previously carried a `black` config that was never
  installed or run, and it has been removed rather than left as decoration.
- **The soundtrack is not redistributable.** See LICENSE. It is also excluded
  from the browser build, because pygbag needs OGG and rejects filenames with
  spaces in them.
- **Do not commit `build/`.** It is gitignored. The browser bundle is built by
  CI, not checked in.

## Reporting a bug

A round number and a screenshot go a long way. Most of the subtle bugs in this
project's history were in balance or timing rather than in crashes, and those
are the ones that need the specifics: which map, which round, which towers.
