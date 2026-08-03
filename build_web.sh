#!/usr/bin/env bash
#
# Build the browser version with pygbag and, by default, serve it locally.
#
#   ./build_web.sh            build, then serve at http://localhost:8000
#   ./build_web.sh --build    build only, no server
#
# Output lands in build/web/. To publish on GitHub Pages, push the contents of
# build/web/ to a gh-pages branch.
#
# This works because the game loop in btd/app.py is async and yields once per
# frame; pygbag needs an awaitable entry point and a loop that hands control
# back to the browser.
#
# What gets left out of the bundle is controlled by pygbag.ini, not by this
# script.

set -euo pipefail

cd "$(dirname "$0")"

OUT="build/web"

if ! python3 -c "import pygbag" 2>/dev/null; then
  echo "pygbag is not installed. Installing it now..."
  python3 -m pip install --quiet pygbag
fi

# pygbag rejects filenames containing spaces and refuses non-OGG audio. Warn
# about both up front, because its own error arrives hundreds of lines into
# the build output and it still exits 0.
if find balloon_images monkey_images background_images btd -name "* *" 2>/dev/null | grep -q .; then
  echo "WARNING: asset filenames contain spaces; pygbag will reject them:"
  find balloon_images monkey_images background_images btd -name "* *" 2>/dev/null | sed 's/^/  /'
fi

# Clear previous artefacts so a stale index.html cannot make a failed build
# look like it succeeded. The directory itself has to stay: pygbag writes the
# .apk straight into it without creating it first.
rm -rf "$OUT"
mkdir -p "$OUT"

# pygbag's click-to-start splash is kept rather than skipped with
# --ume_block 0, since it is what collects the user gesture browsers require
# before audio can start. (Tested both ways in a sandboxed in-app browser and
# the loader stalled either way -- see the note at the bottom of this file.)
ARGS=(--title "Balloon TD")

if [[ "${1:-}" == "--build" ]]; then
  ARGS+=(--build)
  echo "Building browser bundle (no server)..."
else
  echo "Building, then serving at http://localhost:8000 ..."
fi

python3 -m pygbag "${ARGS[@]}" . || true

# pygbag exits 0 even when packaging fails, so verify the artefacts itself.
if [[ ! -f "$OUT/index.html" ]]; then
  echo
  echo "BUILD FAILED: $OUT/index.html was not produced."
  echo "Check the output above for a RuntimeError from pygbag. Common causes:"
  echo "  - audio in a format other than OGG"
  echo "  - a file or folder name containing spaces"
  echo "  - an asset directory that should be listed in pygbag.ini"
  exit 1
fi

echo
echo "Build OK."
du -sh "$OUT" | sed 's/^/  total  /'
ls -la "$OUT" | sed 's/^/  /'

# NOTE ON RUNTIME VERIFICATION
#
# The bundle above is confirmed correct: index.html, the .apk, and the right
# set of game files, with dev tooling and the soundtrack excluded.
#
# Booting it has only been attempted inside a sandboxed in-app browser, where
# the pygbag loader stalls at "Loading, please wait ..." with a 1x1 canvas.
# It gets as far as starting the CPython WASM VM and fetching
# https://pygame-web.github.io/cdn/index-0.9.3-cp312.json (HTTP 200), then
# makes no further requests -- consistent with the follow-up wheel downloads
# being blocked in that sandbox, but not proven to be. Removing --ume_block 0
# did not change it.
#
# So: please open http://localhost:8000 in a normal browser to confirm it
# actually runs before publishing anywhere. If it stalls there too, the first
# thing to check is the browser console for a failed fetch to
# pygame-web.github.io.
