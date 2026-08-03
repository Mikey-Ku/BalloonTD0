"""
Downscale oversized sprite art.

The sprites inherited from the original project are 1024x1024 PNGs of about
1.3 MB each, but the largest of them is drawn at 84 pixels on screen. Ten of
them add roughly 14 MB to the repository and to every browser build, for no
visible benefit -- the game scales them down at load time regardless.

This rewrites them at a sane resolution. Originals are recoverable from git
(``git checkout HEAD -- balloon_images monkey_images``), and a copy is written
to ``tools/asset_originals/`` as well.

    python tools/optimize_assets.py --dry-run     # report only
    python tools/optimize_assets.py               # rewrite at 256px
    python tools/optimize_assets.py --max 512     # rewrite at 512px

256 is the default because the largest sprite slot is the ZOMG placeholder at
148 pixels; anything beyond ~2x the on-screen size is invisible after
downscaling.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys

try:
    from PIL import Image
except ImportError:
    print("This tool needs Pillow:  python -m pip install pillow")
    raise SystemExit(1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP = os.path.join(ROOT, "tools", "asset_originals")

#: Directories scanned for sprite art. Map backgrounds are excluded because
#: they are drawn at full size and must stay at the map resolution.
SPRITE_DIRS = ("balloon_images", "monkey_images")


def targets() -> list[str]:
    """Collect every sprite file, relative to the project root."""
    found = []
    for folder in SPRITE_DIRS:
        full = os.path.join(ROOT, folder)
        if not os.path.isdir(full):
            continue
        for name in sorted(os.listdir(full)):
            if name.lower().endswith((".png", ".webp")):
                found.append(os.path.join(folder, name))
    return found


def optimize(rel_path: str, max_side: int, dry_run: bool) -> tuple[int, int]:
    """Downscale one image if it is larger than ``max_side``.

    Args:
        rel_path: Path relative to the project root.
        max_side: Longest permitted edge, in pixels.
        dry_run: Report only; do not write.

    Returns:
        ``(bytes_before, bytes_after)``. When nothing changes these are equal.
    """
    full = os.path.join(ROOT, rel_path)
    before = os.path.getsize(full)

    with Image.open(full) as img:
        img = img.convert("RGBA")
        width, height = img.size
        longest = max(width, height)

        if longest <= max_side:
            print(f"  keep    {rel_path:<40} {width}x{height}  "
                  f"{before / 1024:7.0f} KB")
            return before, before

        scale = max_side / longest
        new_size = (max(1, round(width * scale)), max(1, round(height * scale)))
        resized = img.resize(new_size, Image.LANCZOS)

        if dry_run:
            print(f"  WOULD   {rel_path:<40} {width}x{height} -> "
                  f"{new_size[0]}x{new_size[1]}  {before / 1024:7.0f} KB")
            return before, before

        os.makedirs(os.path.join(BACKUP, os.path.dirname(rel_path)), exist_ok=True)
        shutil.copy2(full, os.path.join(BACKUP, rel_path))
        resized.save(full, "PNG", optimize=True)

    after = os.path.getsize(full)
    saved = 100 * (1 - after / before) if before else 0
    print(f"  resize  {rel_path:<40} {width}x{height} -> "
          f"{new_size[0]}x{new_size[1]}  "
          f"{before / 1024:7.0f} -> {after / 1024:6.0f} KB  (-{saved:.0f}%)")
    return before, after


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max", type=int, default=256,
                        help="longest edge in pixels [default: 256]")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would change without writing")
    args = parser.parse_args()

    files = targets()
    if not files:
        print("No sprite files found.")
        return

    print(f"Scanning {len(files)} sprites, target max edge {args.max}px\n")

    total_before = total_after = 0
    for rel_path in files:
        before, after = optimize(rel_path, args.max, args.dry_run)
        total_before += before
        total_after += after

    print(f"\n  total   {total_before / 1024 / 1024:.1f} MB -> "
          f"{total_after / 1024 / 1024:.1f} MB")

    if args.dry_run:
        print("\nDry run; nothing was written.")
    elif total_after < total_before:
        print(f"\nOriginals copied to {BACKUP}")
        print("Also recoverable with:")
        print("  git checkout HEAD -- balloon_images monkey_images")


if __name__ == "__main__":
    sys.exit(main())
