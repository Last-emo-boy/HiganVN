from typing import Dict, Optional, Tuple, Callable, List

import pygame
from pygame import Surface

from higanvn.engine.animator import Animator
from higanvn.engine.surface_utils import scale_to_height

LOGICAL_SIZE: Tuple[int, int] = (1280, 720)


class CharacterLayer:
    def __init__(self, slots: dict) -> None:
        # actor id -> (base body, pose overlay or replacement)
        self.characters = {}  # type: Dict[str, Tuple[Optional[Surface], Optional[Surface]]]
        self.active_actor = None  # type: Optional[str]
        self._slots = slots or {}
        # current outfit folder per actor (None -> root)
        self._outfits = {}  # type: Dict[str, Optional[str]]
        # current action overlay per actor
        self._actions = {}  # type: Dict[str, Optional[Surface]]
        # logical names for snapshot/rebuild
        self._pose_names = {}  # type: Dict[str, Optional[str]]
        self._action_names = {}  # type: Dict[str, Optional[str]]
        # debug caches
        self._last_rects = {}  # type: Dict[str, pygame.Rect]
        self._last_centers = {}  # type: Dict[str, Tuple[int, int]]
        # strict mode (disable asset fallbacks when True)
        self._strict_mode = False

    def set_strict_mode(self, strict: bool) -> None:
        self._strict_mode = bool(strict)

    def set_outfit(self, actor: str, outfit: Optional[str]) -> None:
        """Set current outfit subfolder for actor; None to reset to root.

        Clears cached images for that actor so they reload on next ensure/set.
        """
        self._outfits[actor] = outfit if outfit else None
        if actor in self.characters:
            self.characters.pop(actor, None)
        self._actions.pop(actor, None)
        self._pose_names.pop(actor, None)
        self._action_names.pop(actor, None)

    def ensure_loaded(
        self,
        actor: str,
        resolve_path: Callable[[str], str],
        make_placeholder: Callable[[str], Surface],
    ) -> None:
        if actor in self.characters:
            return
        outfit = self._outfits.get(actor)
        base: Optional[Surface] = None
        # Try outfit-specific base first if outfit provided
        if outfit:
            try:
                p1 = resolve_path(f"ch/{actor}/{outfit}/base.png")
                base = pygame.image.load(p1).convert_alpha()
            except Exception:
                base = None
            # In strict mode, do not fallback to root if an outfit was explicitly set
            if base is None and not self._strict_mode:
                try:
                    p2 = resolve_path(f"ch/{actor}/base.png")
                    base = pygame.image.load(p2).convert_alpha()
                except Exception:
                    base = None
        else:
            # No outfit specified: use root base directly
            try:
                p = resolve_path(f"ch/{actor}/base.png")
                base = pygame.image.load(p).convert_alpha()
            except Exception:
                base = None
        if base is None:
            base = make_placeholder(actor)
        self.characters[actor] = (base, None)

    def set_pose(
        self,
        actor: str,
        emotion: str,
        resolve_path: Callable[[str], str],
        make_pose_ph: Callable[[str], Surface],
    ) -> None:
        base, _ = self.characters.get(actor, (None, None))
        outfit = self._outfits.get(actor)
        pose = None  # type: Optional[Surface]
        if outfit:
            try:
                p1 = resolve_path(f"ch/{actor}/{outfit}/pose_{emotion}.png")
                pose = pygame.image.load(p1).convert_alpha()
            except Exception:
                pose = None
            # Only fallback to root pose when not strict
            if pose is None and not self._strict_mode:
                try:
                    p2 = resolve_path(f"ch/{actor}/pose_{emotion}.png")
                    pose = pygame.image.load(p2).convert_alpha()
                except Exception:
                    pose = None
        else:
            # No outfit specified: use root pose directly
            try:
                p2 = resolve_path(f"ch/{actor}/pose_{emotion}.png")
                pose = pygame.image.load(p2).convert_alpha()
            except Exception:
                pose = None
        if pose is None:
            # Fallback behavior: if not strict, use base (i.e., keep pose None). In strict, use placeholder.
            if self._strict_mode:
                pose = make_pose_ph(str(emotion))
            else:
                pose = None  # render will use base
        self.characters[actor] = (base, pose)
        self._pose_names[actor] = str(emotion)

    def set_action(
        self,
        actor: str,
        action: Optional[str],
        resolve_path: Callable[[str], str],
        make_pose_ph: Callable[[str], Surface],
    ) -> None:
        if not action:
            self._actions[actor] = None
            self._action_names.pop(actor, None)
            return
        outfit = self._outfits.get(actor)
        img = None  # type: Optional[Surface]
        if outfit:
            try:
                p1 = resolve_path(f"ch/{actor}/{outfit}/action_{action}.png")
                img = pygame.image.load(p1).convert_alpha()
            except Exception:
                img = None
            # Only fallback to root action when not strict
            if img is None and not self._strict_mode:
                try:
                    p2 = resolve_path(f"ch/{actor}/action_{action}.png")
                    img = pygame.image.load(p2).convert_alpha()
                except Exception:
                    img = None
        else:
            # No outfit specified: use root action directly
            try:
                p2 = resolve_path(f"ch/{actor}/action_{action}.png")
                img = pygame.image.load(p2).convert_alpha()
            except Exception:
                img = None
        if img is None:
            # Fallback: if not strict, use base/pose (i.e., do not set action image). In strict, show placeholder.
            if self._strict_mode:
                img = make_pose_ph(f"action:{action}")
            else:
                img = None
        self._actions[actor] = img
        self._action_names[actor] = str(action)

    def remove(self, actor: str) -> None:
        self.characters.pop(actor, None)
        self._actions.pop(actor, None)
        self._pose_names.pop(actor, None)
        self._action_names.pop(actor, None)
        if self.active_actor == actor:
            self.active_actor = None

    def clear(self) -> None:
        self.characters.clear()
        self._actions.clear()
        self._pose_names.clear()
        self._action_names.clear()
        self.active_actor = None
        self._last_rects.clear()
        self._last_centers.clear()

    def render(self, canvas: Surface, animator: Animator, now_ms: int) -> None:
        if not self.characters:
            return
        slot_positions = self._slots.get(
            "positions",
            [
                (int(LOGICAL_SIZE[0] * 0.2), int(LOGICAL_SIZE[1] * 0.64)),
                (int(LOGICAL_SIZE[0] * 0.5), int(LOGICAL_SIZE[1] * 0.64)),
                (int(LOGICAL_SIZE[0] * 0.8), int(LOGICAL_SIZE[1] * 0.64)),
            ],
        )
        slot_scale = float(self._slots.get("scale", 0.9))
        order = list(self.characters.keys())
        eff_scale = slot_scale * (0.86 if len(order) >= 3 else 1.0)
        n = len(order)
        pos_count = max(1, len(slot_positions))
        if n == 1:
            mid = 1 if pos_count >= 3 else (pos_count // 2)
            slot_index_map = [mid]
        elif n == 2:
            if pos_count >= 3:
                slot_index_map = [0, 2]
            elif pos_count >= 2:
                slot_index_map = [0, 1]
            else:
                slot_index_map = [0, 0]
        else:
            slot_index_map = [i % pos_count for i in range(n)]
        if self.active_actor in order:
            order = [a for a in order if a != self.active_actor] + [self.active_actor]
        self._last_rects.clear()
        self._last_centers.clear()
        for idx, actor in enumerate(order):
            base, pose = self.characters[actor]
            si = slot_index_map[idx] if idx < len(slot_index_map) else (idx % pos_count)
            x, y = slot_positions[si]
            dx, dy = animator.offset(now_ms, actor, LOGICAL_SIZE[0], LOGICAL_SIZE[1])
            cx, cy = int(x + dx), int(y + dy)

            # If action exists, render it INSTEAD of base/pose (hide base/pose)
            act = self._actions.get(actor)
            if act is not None:
                a_s = scale_to_height(act, int(LOGICAL_SIZE[1] * eff_scale))
                recta = a_s.get_rect(center=(cx, cy))
                if self.active_actor and actor != self.active_actor:
                    dim_a = a_s.copy()
                    dim_a.fill((0, 0, 0, 80), special_flags=pygame.BLEND_RGBA_SUB)
                    canvas.blit(dim_a, recta)
                else:
                    canvas.blit(a_s, recta)
                try:
                    self._last_rects[actor] = recta.copy()
                    self._last_centers[actor] = (cx, cy)
                except Exception:
                    pass
                continue  # skip rendering body when action is present

            # Otherwise, render base/pose as usual
            body = pose if pose is not None else base
            if body is not None:
                b = scale_to_height(body, int(LOGICAL_SIZE[1] * eff_scale))
                rect = b.get_rect(center=(cx, cy))
                if self.active_actor and actor != self.active_actor:
                    dim = b.copy()
                    dim.fill((0, 0, 0, 80), special_flags=pygame.BLEND_RGBA_SUB)
                    canvas.blit(dim, rect)
                else:
                    canvas.blit(b, rect)
                try:
                    self._last_rects[actor] = rect.copy()
                    self._last_centers[actor] = (cx, cy)
                except Exception:
                    pass

    def last_rects(self) -> Dict[str, pygame.Rect]:
        return dict(self._last_rects)

    def last_centers(self) -> Dict[str, Tuple[int, int]]:
        return dict(self._last_centers)

    def snapshot_characters(self) -> List[dict]:
        data: List[dict] = []
        for actor in self.characters.keys():
            data.append(
                {
                    "id": actor,
                    "outfit": self._outfits.get(actor),
                    "pose": self._pose_names.get(actor),
                    "action": self._action_names.get(actor),
                }
            )
        return data
