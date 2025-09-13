from __future__ import annotations

"""Adapter interfaces and default implementations for pluggable engine backends.

Currently provides:
- ISaveStore: abstraction for save/load persistence
- IAssets: abstraction for resolving asset paths
- IAudio: abstraction for audio playback (bgm/se/voice)

Only ISaveStore is used by Engine in this iteration to avoid breaking public APIs.
"""

from .storage import ISaveStore, FileSaveStore  # noqa: F401
from .assets import IAssets, FileSystemAssets  # noqa: F401
from .audio import IAudio, PygameAudio  # noqa: F401
