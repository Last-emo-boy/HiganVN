from __future__ import annotations

from typing import Optional
from higanvn.assets.actors import resolve_actor_folder
from higanvn.engine.placeholders import make_char_placeholder, make_pose_placeholder


def set_outfit(renderer, display: str, outfit: Optional[str]) -> None:
    folder = resolve_actor_folder(display, renderer.actor_map)
    if not folder:
        return
    renderer.char_layer.set_outfit(folder, None if (outfit and outfit.lower()=="none") else outfit)
    first_appear = folder not in renderer.char_layer.characters
    renderer.char_layer.ensure_loaded(folder, renderer._resolve_asset, lambda lbl: make_char_placeholder(lbl, renderer.font))
    if first_appear and not (renderer._suppress_anims_once or renderer._suppress_anims_replay):
        try:
            renderer.animator.start(__import__('pygame').time.get_ticks(), folder, "slide_in_d", 360, 120)
        except Exception:
            pass


def set_action(renderer, display: str, action: Optional[str]) -> None:
    folder = resolve_actor_folder(display, renderer.actor_map)
    if not folder:
        return
    renderer.char_layer.ensure_loaded(folder, renderer._resolve_asset, lambda lbl: make_char_placeholder(lbl, renderer.font))
    renderer.char_layer.set_action(folder, None if (action and action.lower()=="none") else action, renderer._resolve_asset, lambda emo: make_pose_placeholder(emo, renderer.font))


def hide_actor(renderer, display: str) -> None:
    folder = resolve_actor_folder(display, renderer.actor_map)
    if folder:
        renderer.char_layer.remove(folder)


def clear_stage(renderer) -> None:
    renderer.char_layer.clear()
