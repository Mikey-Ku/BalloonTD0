"""
Asset loading, path resolution, and caching.

The original code loaded images with bare relative paths, so the game only ran
if the working directory happened to be the repository root. Everything here
resolves against the project root instead, and every load is cached and
degrades to a visible placeholder rather than crashing.
"""

from __future__ import annotations

import os

import pygame

#: Project root, i.e. the directory containing this package.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_IMAGES: dict[tuple[str, tuple[int, int] | None], pygame.Surface] = {}
_FONTS: dict[tuple[str | None, int, bool], pygame.font.Font] = {}
_SOUNDS: dict[str, pygame.mixer.Sound | None] = {}

_MISSING: set[str] = set()


def path(*parts: str) -> str:
    """Resolve a path relative to the project root.

    Args:
        *parts: Path components, e.g. ``("balloon_images", "red.png")``.

    Returns:
        An absolute path.
    """
    return os.path.join(ROOT, *parts)


def _placeholder(size: tuple[int, int]) -> pygame.Surface:
    """Build a magenta/black checker so a missing asset is obvious on screen."""
    surf = pygame.Surface(size, pygame.SRCALPHA)
    surf.fill((255, 0, 220))
    step = max(4, min(size) // 4)
    for y in range(0, size[1], step):
        for x in range(0, size[0], step):
            if (x // step + y // step) % 2 == 0:
                pygame.draw.rect(surf, (20, 20, 20), (x, y, step, step))
    return surf


def image(rel_path: str, size: tuple[int, int] | None = None) -> pygame.Surface:
    """Load an image, scaled and cached.

    Args:
        rel_path: Path relative to the project root.
        size: Target ``(width, height)``, or ``None`` to keep native size.

    Returns:
        A cached surface. Callers must not mutate it; use :func:`image_copy`
        if a mutable surface is needed.
    """
    key = (rel_path, size)
    cached = _IMAGES.get(key)
    if cached is not None:
        return cached

    full = path(rel_path)
    try:
        surf = pygame.image.load(full)
        surf = surf.convert_alpha() if pygame.display.get_init() else surf
    except (pygame.error, FileNotFoundError):
        if rel_path not in _MISSING:
            _MISSING.add(rel_path)
            print(f"[assets] missing image: {rel_path}")
        surf = _placeholder(size or (32, 32))

    if size is not None and surf.get_size() != size:
        surf = pygame.transform.smoothscale(surf, size)

    _IMAGES[key] = surf
    return surf


def image_copy(rel_path: str, size: tuple[int, int] | None = None) -> pygame.Surface:
    """Return a mutable copy of a cached image."""
    return image(rel_path, size).copy()


def exists(rel_path: str) -> bool:
    """Whether an asset file is present on disk."""
    return bool(rel_path) and os.path.isfile(path(rel_path))


def optional(candidates, size: tuple[int, int] | None = None) -> pygame.Surface | None:
    """Load the first asset that exists, or ``None`` if none do.

    This is what makes artwork drop-in. Every sprite in the game asks for its
    art by a predictable filename first; if no file is there, the caller draws
    a procedural placeholder instead. Adding real art is therefore a matter of
    saving a PNG to the right path -- no code change, no registration step.
    See ``ASSETS.md`` for the full list of slots.

    Args:
        candidates: Paths to try, in priority order. ``None`` entries are
            skipped so callers can pass an optional declared path directly.
        size: Target size, or ``None`` to keep native size.

    Returns:
        The loaded surface, or ``None`` if no candidate exists.
    """
    for candidate in candidates:
        if candidate and exists(candidate):
            return image(candidate, size)
    return None


def font(size: int, bold: bool = False, name: str | None = None) -> pygame.font.Font:
    """Load a cached font.

    Falls back to pygame's default font, which is always available and is what
    the browser build ends up using.
    """
    key = (name, size, bold)
    cached = _FONTS.get(key)
    if cached is not None:
        return cached

    try:
        loaded = pygame.font.SysFont(name, size, bold=bold) if name else None
    except pygame.error:
        loaded = None
    if loaded is None:
        loaded = pygame.font.Font(None, int(size * 1.15))
        loaded.set_bold(bold)

    _FONTS[key] = loaded
    return loaded


def sound(rel_path: str) -> pygame.mixer.Sound | None:
    """Load a cached sound effect, or ``None`` if audio is unavailable."""
    if rel_path in _SOUNDS:
        return _SOUNDS[rel_path]

    result: pygame.mixer.Sound | None = None
    if pygame.mixer.get_init():
        try:
            result = pygame.mixer.Sound(path(rel_path))
        except (pygame.error, FileNotFoundError):
            result = None
    _SOUNDS[rel_path] = result
    return result


#: Music formats in preference order. OGG is first because it is the only one
#: browsers reliably decode, so a build that has both plays the same track on
#: the desktop and on the web.
MUSIC_FORMATS = (".ogg", ".mp3", ".wav")


def find_music() -> str | None:
    """Locate a background music track in ``soundtrack/``.

    A directory scan rather than a hardcoded filename, so swapping the track
    means dropping a file in and deleting the old one -- no code change.

    Returns:
        Path to the most preferred track present, or ``None``.
    """
    folder = path("soundtrack")
    if not os.path.isdir(folder):
        return None

    names = sorted(os.listdir(folder))
    for extension in MUSIC_FORMATS:
        for name in names:
            if name.lower().endswith(extension):
                return os.path.join(folder, name)
    return None
