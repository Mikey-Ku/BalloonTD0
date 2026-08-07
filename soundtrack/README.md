# Soundtrack

This folder is empty on purpose. Drop a music file in and the game will loop it.

`assets.find_music()` scans this directory rather than naming a file, so adding a
track needs no code change. Supported extensions, in preference order:

```
.ogg   .mp3   .wav
```

If more than one file is present, the first match in that order wins. If the
folder is empty, `find_music()` returns `None` and `AudioManager.start_music()`
returns early, so the game runs silently rather than failing. Sound effects are
synthesised at runtime and do not depend on anything here.

## Why there is nothing here

The original 2025 team project shipped with a track ripped from Spotify, and the
filename said so. It was removed rather than shipped in a public repository.

If you want music, use something you are allowed to use. Reasonable sources:

- Your own recording.
- Public domain, for example a CC0 track from [Free Music Archive](https://freemusicarchive.org/)
  or [Incompetech](https://incompetech.com/) under the stated attribution terms.
- Anything under a Creative Commons licence that permits the use you intend.

If the track you add requires attribution, credit it here.
