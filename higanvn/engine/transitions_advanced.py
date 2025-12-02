"""
Advanced Transitions - 高级转场效果

Features:
- 溶解过渡 (Dissolve)
- 擦除过渡 (Wipe - 4方向)
- 百叶窗效果 (Blinds)
- 像素化过渡 (Pixelate)
- 圆形展开 (Circle Iris)
"""
from __future__ import annotations

import math
from typing import Tuple, Callable, Optional
from enum import Enum

import pygame
from pygame import Surface


class TransitionType(Enum):
    """转场类型"""
    FADE = "fade"
    DISSOLVE = "dissolve"
    WIPE_LEFT = "wipe_left"
    WIPE_RIGHT = "wipe_right"
    WIPE_UP = "wipe_up"
    WIPE_DOWN = "wipe_down"
    BLINDS_H = "blinds_h"
    BLINDS_V = "blinds_v"
    PIXELATE = "pixelate"
    CIRCLE_IN = "circle_in"
    CIRCLE_OUT = "circle_out"
    FLASH = "flash"


def ease_in_out_cubic(t: float) -> float:
    """缓入缓出三次曲线"""
    if t < 0.5:
        return 4 * t * t * t
    return 1 - pow(-2 * t + 2, 3) / 2


def ease_out_quad(t: float) -> float:
    """缓出二次曲线"""
    return 1 - (1 - t) ** 2


def ease_in_quad(t: float) -> float:
    """缓入二次曲线"""
    return t * t


def run_transition(
    screen: Surface,
    clock: pygame.time.Clock,
    render_old: Callable[[], None],
    render_new: Callable[[], None],
    transition_type: TransitionType,
    duration_ms: int = 500,
    **kwargs
) -> None:
    """
    运行转场效果。
    
    Args:
        screen: 显示表面
        clock: pygame时钟
        render_old: 渲染旧画面的回调
        render_new: 渲染新画面的回调
        transition_type: 转场类型
        duration_ms: 持续时间(毫秒)
        **kwargs: 额外参数
    """
    # 捕获旧画面
    old_frame = screen.copy()
    render_old()
    old_surface = screen.copy()
    
    # 捕获新画面
    render_new()
    new_surface = screen.copy()
    
    start = pygame.time.get_ticks()
    size = screen.get_size()
    
    while True:
        # 处理事件
        cancel = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.VIDEORESIZE:
                size = screen.get_size()
                # 重新缩放捕获的表面
                old_surface = pygame.transform.scale(old_surface, size)
                new_surface = pygame.transform.scale(new_surface, size)
            # 用户操作取消转场
            if event.type in (pygame.MOUSEWHEEL, pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                if event.type == pygame.KEYDOWN and event.key in (
                    pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE
                ):
                    cancel = True
                elif event.type == pygame.MOUSEBUTTONDOWN and getattr(event, 'button', 0) == 1:
                    cancel = True
        
        if cancel:
            screen.blit(new_surface, (0, 0))
            pygame.display.flip()
            break
        
        now = pygame.time.get_ticks()
        t = (now - start) / max(1, duration_ms)
        t = max(0.0, min(1.0, t))
        
        # 根据转场类型渲染
        _render_transition(screen, old_surface, new_surface, transition_type, t, **kwargs)
        pygame.display.flip()
        
        if t >= 1.0:
            break
        
        clock.tick(60)


def _render_transition(
    screen: Surface,
    old_surf: Surface,
    new_surf: Surface,
    transition_type: TransitionType,
    t: float,
    **kwargs
) -> None:
    """渲染单帧转场"""
    
    if transition_type == TransitionType.FADE:
        _transition_fade(screen, old_surf, new_surf, t)
    
    elif transition_type == TransitionType.DISSOLVE:
        _transition_dissolve(screen, old_surf, new_surf, t)
    
    elif transition_type in (TransitionType.WIPE_LEFT, TransitionType.WIPE_RIGHT,
                             TransitionType.WIPE_UP, TransitionType.WIPE_DOWN):
        _transition_wipe(screen, old_surf, new_surf, t, transition_type)
    
    elif transition_type in (TransitionType.BLINDS_H, TransitionType.BLINDS_V):
        num_blinds = kwargs.get('num_blinds', 10)
        _transition_blinds(screen, old_surf, new_surf, t, 
                          horizontal=(transition_type == TransitionType.BLINDS_H),
                          num_blinds=num_blinds)
    
    elif transition_type == TransitionType.PIXELATE:
        max_pixel_size = kwargs.get('max_pixel_size', 32)
        _transition_pixelate(screen, old_surf, new_surf, t, max_pixel_size)
    
    elif transition_type in (TransitionType.CIRCLE_IN, TransitionType.CIRCLE_OUT):
        center = kwargs.get('center', None)
        _transition_circle(screen, old_surf, new_surf, t,
                          outward=(transition_type == TransitionType.CIRCLE_OUT),
                          center=center)
    
    elif transition_type == TransitionType.FLASH:
        flash_color = kwargs.get('flash_color', (255, 255, 255))
        _transition_flash(screen, old_surf, new_surf, t, flash_color)
    
    else:
        # 默认回退到淡入淡出
        _transition_fade(screen, old_surf, new_surf, t)


def _transition_fade(screen: Surface, old: Surface, new: Surface, t: float) -> None:
    """淡入淡出"""
    eased = ease_in_out_cubic(t)
    screen.blit(old, (0, 0))
    new_copy = new.copy()
    new_copy.set_alpha(int(255 * eased))
    screen.blit(new_copy, (0, 0))


def _transition_dissolve(screen: Surface, old: Surface, new: Surface, t: float) -> None:
    """溶解效果 - 使用噪点遮罩"""
    import random
    
    eased = ease_in_out_cubic(t)
    size = screen.get_size()
    
    # 创建遮罩
    mask = pygame.Surface(size, pygame.SRCALPHA)
    
    # 使用固定种子保证动画一致性
    random.seed(42)
    
    # 生成噪点遮罩 (简化版本)
    block_size = 8
    for y in range(0, size[1], block_size):
        for x in range(0, size[0], block_size):
            threshold = random.random()
            if threshold < eased:
                pygame.draw.rect(mask, (255, 255, 255, 255), 
                               (x, y, block_size, block_size))
    
    # 先画旧画面
    screen.blit(old, (0, 0))
    
    # 使用遮罩画新画面
    new_masked = new.copy()
    new_masked.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    screen.blit(new_masked, (0, 0))
    
    random.seed()  # 重置随机种子


def _transition_wipe(screen: Surface, old: Surface, new: Surface, t: float, 
                     direction: TransitionType) -> None:
    """擦除效果"""
    eased = ease_out_quad(t)
    w, h = screen.get_size()
    
    screen.blit(old, (0, 0))
    
    if direction == TransitionType.WIPE_LEFT:
        # 从右向左擦除
        reveal_x = int(w * (1 - eased))
        clip_rect = pygame.Rect(reveal_x, 0, w - reveal_x, h)
        screen.set_clip(clip_rect)
        screen.blit(new, (0, 0))
        screen.set_clip(None)
    
    elif direction == TransitionType.WIPE_RIGHT:
        # 从左向右擦除
        reveal_w = int(w * eased)
        clip_rect = pygame.Rect(0, 0, reveal_w, h)
        screen.set_clip(clip_rect)
        screen.blit(new, (0, 0))
        screen.set_clip(None)
    
    elif direction == TransitionType.WIPE_UP:
        # 从下向上擦除
        reveal_y = int(h * (1 - eased))
        clip_rect = pygame.Rect(0, reveal_y, w, h - reveal_y)
        screen.set_clip(clip_rect)
        screen.blit(new, (0, 0))
        screen.set_clip(None)
    
    elif direction == TransitionType.WIPE_DOWN:
        # 从上向下擦除
        reveal_h = int(h * eased)
        clip_rect = pygame.Rect(0, 0, w, reveal_h)
        screen.set_clip(clip_rect)
        screen.blit(new, (0, 0))
        screen.set_clip(None)


def _transition_blinds(screen: Surface, old: Surface, new: Surface, t: float,
                       horizontal: bool = True, num_blinds: int = 10) -> None:
    """百叶窗效果"""
    eased = ease_out_quad(t)
    w, h = screen.get_size()
    
    screen.blit(old, (0, 0))
    
    if horizontal:
        # 水平百叶窗
        blind_h = h // num_blinds
        for i in range(num_blinds):
            y = i * blind_h
            reveal_h = int(blind_h * eased)
            if reveal_h > 0:
                clip_rect = pygame.Rect(0, y, w, reveal_h)
                screen.set_clip(clip_rect)
                screen.blit(new, (0, 0))
    else:
        # 垂直百叶窗
        blind_w = w // num_blinds
        for i in range(num_blinds):
            x = i * blind_w
            reveal_w = int(blind_w * eased)
            if reveal_w > 0:
                clip_rect = pygame.Rect(x, 0, reveal_w, h)
                screen.set_clip(clip_rect)
                screen.blit(new, (0, 0))
    
    screen.set_clip(None)


def _transition_pixelate(screen: Surface, old: Surface, new: Surface, t: float,
                         max_pixel_size: int = 32) -> None:
    """像素化过渡"""
    w, h = screen.get_size()
    
    # 0-0.5: 旧画面像素化增加
    # 0.5-1: 新画面像素化减少
    if t < 0.5:
        source = old
        local_t = t * 2  # 0-1
        pixel_size = int(1 + (max_pixel_size - 1) * ease_in_quad(local_t))
    else:
        source = new
        local_t = (t - 0.5) * 2  # 0-1
        pixel_size = int(max_pixel_size - (max_pixel_size - 1) * ease_out_quad(local_t))
    
    pixel_size = max(1, pixel_size)
    
    if pixel_size > 1:
        # 缩小再放大实现像素化
        small_w = max(1, w // pixel_size)
        small_h = max(1, h // pixel_size)
        small = pygame.transform.scale(source, (small_w, small_h))
        pixelated = pygame.transform.scale(small, (w, h))
        screen.blit(pixelated, (0, 0))
    else:
        screen.blit(source, (0, 0))


def _transition_circle(screen: Surface, old: Surface, new: Surface, t: float,
                       outward: bool = False, center: Optional[Tuple[int, int]] = None) -> None:
    """圆形展开/收缩"""
    eased = ease_in_out_cubic(t)
    w, h = screen.get_size()
    
    if center is None:
        center = (w // 2, h // 2)
    
    # 计算最大半径 (屏幕对角线的一半)
    max_radius = int(math.sqrt(w ** 2 + h ** 2) / 2) + 10
    
    if outward:
        # 圆形展开: 新画面从中心向外展开
        radius = int(max_radius * eased)
        screen.blit(old, (0, 0))
        
        # 创建圆形遮罩
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), center, radius)
        
        new_masked = new.copy()
        new_masked.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(new_masked, (0, 0))
    else:
        # 圆形收缩: 旧画面从外向中心收缩
        radius = int(max_radius * (1 - eased))
        screen.blit(new, (0, 0))
        
        if radius > 0:
            # 创建圆形遮罩
            mask = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.circle(mask, (255, 255, 255, 255), center, radius)
            
            old_masked = old.copy()
            old_masked.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(old_masked, (0, 0))


def _transition_flash(screen: Surface, old: Surface, new: Surface, t: float,
                      flash_color: Tuple[int, int, int] = (255, 255, 255)) -> None:
    """闪白过渡"""
    w, h = screen.get_size()
    
    # 0-0.3: 旧画面淡出到白色
    # 0.3-0.7: 纯白色
    # 0.7-1.0: 白色淡入到新画面
    
    if t < 0.3:
        local_t = t / 0.3
        screen.blit(old, (0, 0))
        flash = pygame.Surface((w, h))
        flash.fill(flash_color)
        flash.set_alpha(int(255 * ease_in_quad(local_t)))
        screen.blit(flash, (0, 0))
    elif t < 0.7:
        screen.fill(flash_color)
    else:
        local_t = (t - 0.7) / 0.3
        screen.blit(new, (0, 0))
        flash = pygame.Surface((w, h))
        flash.fill(flash_color)
        flash.set_alpha(int(255 * (1 - ease_out_quad(local_t))))
        screen.blit(flash, (0, 0))


# ============================================================================
# 便捷函数
# ============================================================================

def dissolve(screen: Surface, clock: pygame.time.Clock, 
             render_old: Callable[[], None], render_new: Callable[[], None],
             duration_ms: int = 800) -> None:
    """溶解转场快捷方式"""
    run_transition(screen, clock, render_old, render_new, 
                   TransitionType.DISSOLVE, duration_ms)


def wipe_left(screen: Surface, clock: pygame.time.Clock,
              render_old: Callable[[], None], render_new: Callable[[], None],
              duration_ms: int = 500) -> None:
    """向左擦除转场"""
    run_transition(screen, clock, render_old, render_new,
                   TransitionType.WIPE_LEFT, duration_ms)


def wipe_right(screen: Surface, clock: pygame.time.Clock,
               render_old: Callable[[], None], render_new: Callable[[], None],
               duration_ms: int = 500) -> None:
    """向右擦除转场"""
    run_transition(screen, clock, render_old, render_new,
                   TransitionType.WIPE_RIGHT, duration_ms)


def blinds(screen: Surface, clock: pygame.time.Clock,
           render_old: Callable[[], None], render_new: Callable[[], None],
           duration_ms: int = 600, horizontal: bool = True, num_blinds: int = 10) -> None:
    """百叶窗转场"""
    t_type = TransitionType.BLINDS_H if horizontal else TransitionType.BLINDS_V
    run_transition(screen, clock, render_old, render_new,
                   t_type, duration_ms, num_blinds=num_blinds)


def flash_transition(screen: Surface, clock: pygame.time.Clock,
                    render_old: Callable[[], None], render_new: Callable[[], None],
                    duration_ms: int = 400, color: Tuple[int, int, int] = (255, 255, 255)) -> None:
    """闪白转场"""
    run_transition(screen, clock, render_old, render_new,
                   TransitionType.FLASH, duration_ms, flash_color=color)


def circle_in(screen: Surface, clock: pygame.time.Clock,
              render_old: Callable[[], None], render_new: Callable[[], None],
              duration_ms: int = 600, center: Optional[Tuple[int, int]] = None) -> None:
    """圆形收缩"""
    run_transition(screen, clock, render_old, render_new,
                   TransitionType.CIRCLE_IN, duration_ms, center=center)


def circle_out(screen: Surface, clock: pygame.time.Clock,
               render_old: Callable[[], None], render_new: Callable[[], None],
               duration_ms: int = 600, center: Optional[Tuple[int, int]] = None) -> None:
    """圆形展开"""
    run_transition(screen, clock, render_old, render_new,
                   TransitionType.CIRCLE_OUT, duration_ms, center=center)
