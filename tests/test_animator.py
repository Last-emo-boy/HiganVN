from __future__ import annotations

from higanvn.engine.animator import Animator


def test_shake_x_offset_changes():
    a = Animator()
    actor = "zhangpeng"
    a.start(now_ms=0, actor=actor, kind="shake_x", duration_ms=1000, amp=50)
    dx0, dy0 = a.offset(now_ms=0, actor=actor, logical_w=1280, logical_h=720)
    dx1, dy1 = a.offset(now_ms=100, actor=actor, logical_w=1280, logical_h=720)
    assert dy1 == 0
    # at some point, horizontal offset should be non-zero
    assert dx0 == 0  # at exact start it's 0
    assert dx1 != 0


def test_slide_in_left_goes_towards_zero():
    a = Animator()
    actor = "xiaoma"
    dur = 800
    a.start(now_ms=0, actor=actor, kind="slide_in_l", duration_ms=dur, amp=0)
    dx_start, dy_start = a.offset(now_ms=0, actor=actor, logical_w=1000, logical_h=600)
    # start is off-screen to the left (negative)
    assert dx_start < 0
    # midway less negative (moving towards center)
    dx_mid, _ = a.offset(now_ms=dur // 2, actor=actor, logical_w=1000, logical_h=600)
    assert dx_mid > dx_start
    # near end very close to 0 (snapped by int)
    dx_end, _ = a.offset(now_ms=dur - 1, actor=actor, logical_w=1000, logical_h=600)
    assert abs(dx_end) <= abs(dx_mid)
    # after duration, animation pruned -> zero offset
    dx_after, dy_after = a.offset(now_ms=dur + 10, actor=actor, logical_w=1000, logical_h=600)
    assert (dx_after, dy_after) == (0, 0)


def test_clear_resets_all():
    a = Animator()
    actor = "npc"
    a.start(now_ms=0, actor=actor, kind="shake_y", duration_ms=500, amp=30)
    # sample at a time that is unlikely to land on a sine zero crossing
    dx, dy = a.offset(now_ms=200, actor=actor, logical_w=1280, logical_h=720)
    assert (dx, dy) != (0, 0)
    a.clear()
    dx2, dy2 = a.offset(now_ms=300, actor=actor, logical_w=1280, logical_h=720)
    assert (dx2, dy2) == (0, 0)


def test_trigger_by_effect_maps_keywords():
    a = Animator()
    actor = "hero"
    # Chinese keyword should trigger a shake
    a.trigger_by_effect(now_ms=0, actor=actor, effect="惊")
    dx, dy = a.offset(now_ms=100, actor=actor, logical_w=1280, logical_h=720)
    assert dx != 0 or dy != 0
