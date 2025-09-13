from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Callable


class IAudio(ABC):
    @abstractmethod
    def play_bgm(self, path: Optional[str], volume: float | None = None) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    @abstractmethod
    def play_se(self, path: str, volume: float | None = None) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    @abstractmethod
    def prepare_voice(self, path: Optional[str], volume: float | None = None) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class PygameAudio(IAudio):
    """Adapter delegating to existing pygame audio utils via injected resolvers."""

    def __init__(self, resolve_bgm: Callable[[str], str], resolve_se: Callable[[str], str]) -> None:
        self._resolve_bgm = resolve_bgm
        self._resolve_se = resolve_se

    def play_bgm(self, path: Optional[str], volume: float | None = None) -> None:
        try:
            from higanvn.engine.audio_utils import play_bgm
            play_bgm(path, volume=volume, resolve_path=self._resolve_bgm)
        except Exception:
            pass

    def play_se(self, path: str, volume: float | None = None) -> None:
        try:
            from higanvn.engine.audio_utils import play_se
            play_se(path, volume=volume, resolve_path=self._resolve_se)
        except Exception:
            pass

    def prepare_voice(self, path: Optional[str], volume: float | None = None) -> None:
        try:
            from higanvn.engine.voice import prepare_voice
            # The renderer instance is expected to own the voice channel; this adapter is illustrative.
            # Keep no-op here; actual use stays in renderer for now.
            _ = (path, volume, prepare_voice)  # silence linters
        except Exception:
            pass
