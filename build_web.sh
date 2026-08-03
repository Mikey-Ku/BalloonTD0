#!/usr/bin/env bash
#
# Build the browser version with pygbag and, by default, serve it locally.
#
#   ./build_web.sh            build and serve at http://localhost:8000
#   ./build_web.sh --build    build only, no server
#
# Output lands in build/web/. To publish on GitHub Pages, push the contents of
# build/web/ to a gh-pages branch (or copy them into docs/ and point Pages at
# that folder).
#
# This works because the game loop in btd/app.py is async and yields once per
# frame; pygbag needs an awaitable entry point and a loop that hands control
# back to the browser.

set -euo pipefail

cd "$(dirname "$0")"

if ! python3 -c "import pygbag" 2>/dev/null; then
  echo "pygbag is not installed. Installing it now..."
  python3 -m pip install --quiet pygbag
fi

# --ume_block 0 skips pygbag's "click to start" splash.
# --template default.tmpl keeps the stock shell; swap it for a custom one if
# you want the page around the canvas branded.
ARGS=(--ume_block 0 --title "Balloon TD")

if [[ "${1:-}" == "--build" ]]; then
  ARGS+=(--build)
  echo "Building browser bundle (no server)..."
else
  echo "Building and serving at http://localhost:8000 ..."
fi

python3 -m pygbag "${ARGS[@]}" .

echo
echo "Output: $(pwd)/build/web"
