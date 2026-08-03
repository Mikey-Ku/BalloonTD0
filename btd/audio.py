"""
Music playback and synthesised sound effects.

The repository ships one music track and no sound effects, so the effects here
are generated at startup into raw PCM buffers rather than loaded from disk.
That keeps the download small, avoids adding more third-party audio to a
public repository, and works in the browser build without bundling extra
files.

Everything degrades quietly: if the mixer cannot start -- which happens on
headless machines and in some browser contexts -- the game runs silently
instead of failing.
"""

from __future__ import annotations

import array
import math
import random

import pygame

from . import assets
from .config import DEFAULT_MUSIC_VOLUME, DEFAULT_SFX_VOLUME

SAMPLE_RATE = 44100
CHANNELS = 2


class Audio:
    """Owns the mixer, the music track, and the generated effect bank.

    Attributes:
        enabled: False when the mixer could not be initialised.
        music_volume: Current music volume in ``[0, 1]``.
        sfx_volume: Current effects volume in ``[0, 1]``.
    """

    def __init__(self):
        self.enabled = False
        self.music_volume = DEFAULT_MUSIC_VOLUME
        self.sfx_volume = DEFAULT_SFX_VOLUME
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self._music_loaded = False
        self._last_played: dict[str, int] = {}

        try:
            pygame.mixer.init(frequency=SAMPLE_RATE, size=-16,
                              channels=CHANNELS, buffer=512)
            pygame.mixer.set_num_channels(24)
            self.enabled = True
        except pygame.error:
            return

        self._build_bank()

    # -- setup ------------------------------------------------------------

    def _build_bank(self) -> None:
        """Synthesise every effect once at startup."""
        self.sounds = {
            "pop": _make(_pop, 0.09),
            "place": _make(_click, 0.09),
            "upgrade": _make(_rise, 0.26),
            "sell": _make(_fall, 0.20),
            "leak": _make(_thud, 0.28),
            "round": _make(_chime, 0.42),
        }
        self.apply_volumes()

    def start_music(self) -> None:
        """Begin looping the background track, if one is present."""
        if not self.enabled or self._music_loaded:
            return
        track = assets.find_music()
        if not track:
            return
        try:
            pygame.mixer.music.load(track)
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(loops=-1)
            self._music_loaded = True
        except pygame.error:
            self._music_loaded = False

    # -- control ----------------------------------------------------------

    def set_volumes(self, music: float, sfx: float) -> None:
        """Update both volumes and apply them immediately."""
        self.music_volume = max(0.0, min(1.0, music))
        self.sfx_volume = max(0.0, min(1.0, sfx))
        self.apply_volumes()

    def apply_volumes(self) -> None:
        """Push current volumes onto the mixer and every loaded sound."""
        if not self.enabled:
            return
        try:
            pygame.mixer.music.set_volume(self.music_volume)
        except pygame.error:
            pass
        for name, sound in self.sounds.items():
            scale = 0.32 if name == "pop" else 1.0
            sound.set_volume(self.sfx_volume * scale)

    def play(self, name: str) -> None:
        """Play an effect.

        Rate-limits repeats so a round with hundreds of simultaneous pops does
        not saturate every mixer channel with the same click.
        """
        if not self.enabled or self.sfx_volume <= 0:
            return
        sound = self.sounds.get(name)
        if sound is None:
            return

        now = pygame.time.get_ticks()
        gap = 45 if name == "pop" else 90
        if now - self._last_played.get(name, -9999) < gap:
            return
        self._last_played[name] = now

        try:
            sound.play()
        except pygame.error:
            pass


# --- waveform generators -------------------------------------------------
#
# Each returns a sample in [-1, 1] for a normalised time t in [0, 1].

def _envelope(t: float, attack: float = 0.02) -> float:
    """Simple attack/decay envelope."""
    if t < attack:
        return t / attack
    return max(0.0, (1.0 - t) ** 2)


def _pop(t: float) -> float:
    """A short filtered noise burst -- a balloon bursting."""
    return random.uniform(-1.0, 1.0) * _envelope(t, 0.005) ** 2


def _click(t: float) -> float:
    """A soft wooden click, for placing a tower."""
    return math.sin(t * 620 * math.tau) * _envelope(t, 0.004) ** 3


def _rise(t: float) -> float:
    """An ascending two-tone, for a purchased upgrade."""
    freq = 420 + 340 * t
    return math.sin(t * freq * math.tau) * _envelope(t, 0.02) * 0.7


def _fall(t: float) -> float:
    """A descending tone, for selling."""
    freq = 640 - 300 * t
    return math.sin(t * freq * math.tau) * _envelope(t, 0.02) * 0.6


def _thud(t: float) -> float:
    """A low hit, for losing lives."""
    freq = 150 - 60 * t
    return (math.sin(t * freq * math.tau) * 0.8
            + random.uniform(-0.15, 0.15)) * _envelope(t, 0.01)


def _chime(t: float) -> float:
    """A two-note chime, for completing a round."""
    first = math.sin(t * 523.25 * math.tau)
    second = math.sin(t * 783.99 * math.tau) * (1.0 if t > 0.35 else 0.0)
    return (first * 0.5 + second * 0.5) * _envelope(t, 0.03) * 0.7


def _make(generator, duration: float) -> pygame.mixer.Sound:
    """Render a generator into a stereo :class:`pygame.mixer.Sound`.

    Args:
        generator: Callable mapping normalised time to a sample in ``[-1, 1]``.
        duration: Length in seconds.

    Returns:
        A playable sound built from a raw 16-bit PCM buffer.
    """
    count = int(SAMPLE_RATE * duration)
    samples = array.array("h", bytes(4 * count))

    for i in range(count):
        value = generator(i / count)
        clipped = max(-1.0, min(1.0, value))
        pcm = int(clipped * 20000)
        samples[i * 2] = pcm
        samples[i * 2 + 1] = pcm

    return pygame.mixer.Sound(buffer=samples.tobytes())
