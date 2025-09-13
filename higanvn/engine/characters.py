from __future__ import annotations

from typing import Dict, Optional, Tuple, Callable
from pathlib import Path

import pygame
from pygame import Surface

from higanvn.engine.animator import Animator
from higanvn.engine.surface_utils import scale_to_height

LOGICAL_SIZE: Tuple[int, int] = (1280, 720)


class CharacterLayer:
    def __init__(self, slots: dict) -> None:
        self.characters: Dict[str, tuple[Surface | None, Surface | None]] = {}
        self.active_actor: Optional[str] = None
        self._slots = slots or {}
        # current outfit folder per actor (None -> default root)
        self._outfits = {}
        # current action overlay per actor (preloaded Surface)
        self._actions = {}
        # debug: last computed rects/centers
        self._last_rects = {}
        self._last_centers = {}

    def set_outfit(self, actor: str, outfit: Optional[str]) -> None:
        """Set current outfit folder for actor (subdirectory under ch/<actor>/). None resets to default.

        Clearing cached images for actor so it reloads on next ensure/set_pose.
        """
        self._outfits[actor] = outfit if outfit else None
        # drop cached images to reload from new outfit on next render
        if actor in self.characters:
            self.characters.pop(actor, None)
        # action overlay needs refresh as well under new outfit
        self._actions.pop(actor, None)

    def ensure_loaded(self, actor: str, resolve_path: Callable[[str], str], make_placeholder: Callable[[str], Surface]) -> None:
        if actor in self.characters:
            return
        outfit = self._outfits.get(actor)
        # prefer outfit subfolder if set
        base_path = None
        try:
            if outfit:
                base_path = resolve_path(f"ch/{actor}/{outfit}/base.png")
        except Exception:
            base_path = None
        if not base_path:
            base_path = resolve_path(f"ch/{actor}/base.png")
        try:
            base = pygame.image.load(base_path).convert_alpha()
        except Exception:
            base = make_placeholder(actor)
        self.characters[actor] = (base, None)

    def set_pose(self, actor: str, emotion: str, resolve_path: Callable[[str], str], make_pose_ph: Callable[[str], Surface]) -> None:
        base, _ = self.characters.get(actor, (None, None))
        outfit = self._outfits.get(actor)
        pose: Optional[Surface] = None
        # Try outfit-specific pose first
        if outfit:
            try:
                pose_path = resolve_path(f"ch/{actor}/{outfit}/pose_{emotion}.png")
                pose = pygame.image.load(pose_path).convert_alpha()
            except Exception:
                pose = None
        # Fallback to root pose if outfit-specific missing
        if pose is None:
            try:
                pose_path_root = resolve_path(f"ch/{actor}/pose_{emotion}.png")
                pose = pygame.image.load(pose_path_root).convert_alpha()
            except Exception:
                pose = make_pose_ph(str(emotion))
        self.characters[actor] = (base, pose)

    def set_action(self, actor: str, action: Optional[str], resolve_path: Callable[[str], str], make_pose_ph: Callable[[str], Surface]) -> None:
        """Set or clear an action overlay for actor.

        Loads ch/<actor>/action_<action>.png (or under outfit subfolder if set). None clears.
        """
        if not action:
            self._actions[actor] = None
            return
        outfit = self._outfits.get(actor)
        img: Optional[Surface] = None
        # Try outfit-specific action first
        if outfit:
            try:
                p1 = resolve_path(f"ch/{actor}/{outfit}/action_{action}.png")
                img = pygame.image.load(p1).convert_alpha()
            except Exception:
                img = None
        # Fallback to root action
        if img is None:
            try:
                p2 = resolve_path(f"ch/{actor}/action_{action}.png")
                img = pygame.image.load(p2).convert_alpha()
            except Exception:
                img = make_pose_ph(f"action:{action}")
        self._actions[actor] = img

    def remove(self, actor: str) -> None:
        """Remove an actor from the stage (and its action overlay)."""
        self.characters.pop(actor, None)
        self._actions.pop(actor, None)
        if self.active_actor == actor:
            self.active_actor = None

    def clear(self) -> None:
        """Clear all actors from the stage."""
        self.characters.clear()
        self._actions.clear()
        self.active_actor = None
        self._last_rects.clear()
        self._last_centers.clear()

    def render(self, canvas: Surface, animator: Animator, now_ms: int) -> None:
        if not self.characters:
            return
        slot_positions = self._slots.get("positions", [
            (int(LOGICAL_SIZE[0] * 0.2), int(LOGICAL_SIZE[1] * 0.64)),
            (int(LOGICAL_SIZE[0] * 0.5), int(LOGICAL_SIZE[1] * 0.64)),
            (int(LOGICAL_SIZE[0] * 0.8), int(LOGICAL_SIZE[1] * 0.64)),
        ])
        slot_scale = float(self._slots.get("scale", 0.9))
        # Preserve insertion order so script SHOW/HIDE controls layout deterministically
        order = list(self.characters.keys())
        # Slightly shrink when showing 3+ actors to reduce overlap
        eff_scale = slot_scale * (0.86 if len(order) >= 3 else 1.0)
        # Choose slot indices based on number of actors:
        # - 1 actor -> center (prefer middle of 3 presets)
        # - 2 actors -> left & right
        # - 3+ actors -> sequential (left, center, right, ...)
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
            # map logical order to chosen slot index
            si = slot_index_map[idx] if idx < len(slot_index_map) else (idx % pos_count)
            x, y = slot_positions[si]
            dx, dy = animator.offset(now_ms, actor, LOGICAL_SIZE[0], LOGICAL_SIZE[1])
            cx, cy = int(x + dx), int(y + dy)

            # Choose body: pose replaces base when present (design change)
            body = pose if pose is not None else base
            if body:
                b = scale_to_height(body, int(LOGICAL_SIZE[1] * eff_scale))
                rect = b.get_rect(center=(cx, cy))
                if self.active_actor and actor != self.active_actor:
                    dim = b.copy()
                    dim.fill((0, 0, 0, 80), special_flags=pygame.BLEND_RGBA_SUB)
                    canvas.blit(dim, rect)
                else:
                    canvas.blit(b, rect)
                # store last rect/center for debug
                try:
                    self._last_rects[actor] = rect.copy()
                    self._last_centers[actor] = (cx, cy)
                except Exception:
                    pass

            # Action overlay draws above the chosen body
            act = self._actions.get(actor)
            if act:
                a_s = scale_to_height(act, int(LOGICAL_SIZE[1] * eff_scale))
                recta = a_s.get_rect(center=(cx, cy))
                if self.active_actor and actor != self.active_actor:
                    dim_a = a_s.copy()
                    dim_a.fill((0, 0, 0, 80), special_flags=pygame.BLEND_RGBA_SUB)
                    canvas.blit(dim_a, recta)
                else:
                    canvas.blit(a_s, recta)
                    # update rect to include overlay bounds
                    try:
                        self._last_rects[actor] = recta.copy()
                    except Exception:
                        pass

    # debug helpers
    def last_rects(self) -> Dict[str, pygame.Rect]:
        return dict(self._last_rects)

    def last_centers(self) -> Dict[str, Tuple[int, int]]:
        return dict(self._last_centers)
