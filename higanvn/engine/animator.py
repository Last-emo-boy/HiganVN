from __future__ import annotations

import math
from typing import Dict, List, Tuple, Optional


class Animator:
    """Tiny helper to manage simple sprite animations per actor.

    Provides shake (x/y) and slide in/out offsets with easing.
    """

    def __init__(self) -> None:
        # actor -> list[anim]
        self._anims: Dict[str, List[dict]] = {}

    def start(self, now_ms: int, actor: str, kind: str, duration_ms: int = 400, amp: int = 24) -> None:
        kind_l = kind.strip().lower()
        mapping = {
            "惊讶": "shake_x",
            "震惊": "shake_y",
            "抖动": "shake_x",
            "左右抖": "shake_x",
            "上下抖": "shake_y",
            "滑入左": "slide_in_l",
            "滑入右": "slide_in_r",
            "滑入上": "slide_in_u",
            "滑入下": "slide_in_d",
            "滑出左": "slide_out_l",
            "滑出右": "slide_out_r",
            "滑出上": "slide_out_u",
            "滑出下": "slide_out_d",
        }
        kind_l = mapping.get(kind_l, kind_l)
        if kind_l in ("shakex", "shake-x"): kind_l = "shake_x"
        if kind_l in ("shakey", "shake-y"): kind_l = "shake_y"
        if kind_l in ("slideinleft", "slidein-l", "in-l"): kind_l = "slide_in_l"
        if kind_l in ("slideinright", "slidein-r", "in-r"): kind_l = "slide_in_r"
        if kind_l in ("slideinup", "slidein-u", "in-u"): kind_l = "slide_in_u"
        if kind_l in ("slideindown", "slidein-d", "in-d"): kind_l = "slide_in_d"
        if kind_l in ("slideoutleft", "slideout-l", "out-l"): kind_l = "slide_out_l"
        if kind_l in ("slideoutright", "slideout-r", "out-r"): kind_l = "slide_out_r"
        if kind_l in ("slideoutup", "slideout-u", "out-u"): kind_l = "slide_out_u"
        if kind_l in ("slideoutdown", "slideout-d", "out-d"): kind_l = "slide_out_d"
        anim = {"kind": kind_l, "start": int(now_ms), "dur": max(1, int(duration_ms)), "amp": int(amp)}
        self._anims.setdefault(actor, []).append(anim)

    def trigger_by_effect(self, now_ms: int, actor: str, effect: str) -> None:
        eff = (effect or "").strip()
        if not eff:
            return
        if any(k in eff for k in ("惊", "shock", "surprise")):
            self.start(now_ms, actor, "shake_x", 350, 20)
        elif any(k in eff.lower() for k in ("shakey", "updown")):
            self.start(now_ms, actor, "shake_y", 350, 18)
        elif "滑入" in eff or "slidein" in eff.lower():
            dir_map = {"左": "slide_in_l", "右": "slide_in_r", "上": "slide_in_u", "下": "slide_in_d"}
            chosen = next((dir_map[k] for k in dir_map if k in eff), "slide_in_l")
            self.start(now_ms, actor, chosen, 420, 0)
        elif "滑出" in eff or "slideout" in eff.lower():
            dir_map = {"左": "slide_out_l", "右": "slide_out_r", "上": "slide_out_u", "下": "slide_out_d"}
            chosen = next((dir_map[k] for k in dir_map if k in eff), "slide_out_r")
            self.start(now_ms, actor, chosen, 420, 0)

    def offset(self, now_ms: int, actor: str, logical_w: int, logical_h: int) -> Tuple[int, int]:
        lst = self._anims.get(actor)
        if not lst:
            return (0, 0)
        dx = dy = 0
        keep: List[dict] = []
        for anim in lst:
            start = int(anim.get("start", 0))
            dur = max(1, int(anim.get("dur", 1)))
            t = (now_ms - start) / dur
            if t >= 1.0:
                continue
            k = anim.get("kind")
            amp = int(anim.get("amp", 24))
            if k == "shake_x":
                phase = t * 8 * math.pi
                scale = (1.0 - t)
                dx += int(amp * scale * math.sin(phase))
            elif k == "shake_y":
                phase = t * 8 * math.pi
                scale = (1.0 - t)
                dy += int(amp * scale * math.sin(phase))
            elif k in ("slide_in_l", "slide_in_r", "slide_in_u", "slide_in_d", "slide_out_l", "slide_out_r", "slide_out_u", "slide_out_d"):
                tt = t
                ease = tt * tt * (3 - 2 * tt)
                # If amp > 0, treat as pixel distance for slide; else default to 60% of screen
                offx = int(amp) if amp and amp > 0 else int(logical_w * 0.6)
                offy = int(amp) if amp and amp > 0 else int(logical_h * 0.6)
                if k == "slide_in_l":
                    dx += int(-(1 - ease) * offx)
                elif k == "slide_in_r":
                    dx += int((1 - ease) * offx)
                elif k == "slide_in_u":
                    dy += int(-(1 - ease) * offy)
                elif k == "slide_in_d":
                    dy += int((1 - ease) * offy)
                elif k == "slide_out_l":
                    dx += int(ease * -offx)
                elif k == "slide_out_r":
                    dx += int(ease * offx)
                elif k == "slide_out_u":
                    dy += int(ease * -offy)
                elif k == "slide_out_d":
                    dy += int(ease * offy)
            keep.append(anim)
        if keep:
            self._anims[actor] = keep
        else:
            self._anims.pop(actor, None)
        return (dx, dy)

    def clear(self) -> None:
        self._anims.clear()

    # debug helpers
    def counts(self) -> dict:
        """Return a compact summary of active animations.

        Example:
            { 'actors': 2, 'total': 3, 'kinds': { 'shake_x': 2, 'slide_in_d': 1 } }
        """
        total = 0
        kinds: Dict[str, int] = {}
        for lst in self._anims.values():
            total += len(lst)
            for anim in lst:
                k = str(anim.get('kind', ''))
                if not k:
                    continue
                kinds[k] = kinds.get(k, 0) + 1
        return {
            'actors': len(self._anims),
            'total': total,
            'kinds': kinds,
        }
