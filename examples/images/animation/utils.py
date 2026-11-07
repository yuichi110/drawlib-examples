# Copyright (c) 2026 Yuichi Ito (yuichi@yuichi.com)
#
# This software is licensed under the Apache License, Version 2.0.
# For more information, please visit: https://github.com/yuichi110/drawlib
#
# This software is provided "as is", without warranty of any kind,
# express or implied, including but not limited to the warranties of
# merchantability, fitness for a particular purpose and noninfringement.

"""Shared choreography, physics, and flat vector rendering helpers for GRIT COMPUTING animations."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Literal

from drawlib.anim import Animation
from drawlib.canvas import setup
from drawlib.fonts import FontFile
from drawlib.shapes import circle, ellipse, rectangle
from drawlib.styles import Styles
from drawlib.text import text

# Exact 550:355 (110:71) aspect ratio matching https://www.yuichi.com/img/logo.png
# 10.0 in * 110 dpi = 1100 x 710 px (2x Retina resolution)
CANVAS_W: int = 110
CANVAS_H: int = 71
CANVAS_DPI: int = 110

# Stage geometry (strictly >= 4.0 units margin on all 4 edges)
X_LEFT: float = 4.0
X_RIGHT: float = 106.0
STAGE_W: float = X_RIGHT - X_LEFT  # 102.0
CENTER_X: float = 55.0

FLOOR_Y: float = 15.2
CEIL_Y: float = 55.8
RAIL_H: float = 2.1

# 3x3 Docking Bay geometry (Left & Right)
TILE_SIZE: float = 8.0
GRID_PITCH: float = 9.2
ROW_YS: tuple[float, float, float] = (20.8, 30.0, 39.2)  # bottom, middle, top
LEFT_COL_XS: tuple[float, float, float] = (8.0, 17.2, 26.4)  # outer, mid (core), inner
RIGHT_COL_XS: tuple[float, float, float] = (83.6, 92.8, 102.0)  # inner, mid (core), outer

# Custom geometric sci-fi font from yuichi.com
_ASSETS_DIR = Path(__file__).resolve().parent / "_assets"
AVENGER_FONT = FontFile(str(_ASSETS_DIR / "avenger.ttf"))

# Relative uppercase bounding-box widths in Avenger Regular (measured from glyph metrics)
_GLYPH_WIDTH_RATIO: dict[str, float] = {
    "I": 14.0 / 49.0,
    "M": 58.0 / 49.0,
}

# Collision-free 9-cell migration order (col, row):
# Phase 1 (Right -> Left): peel inner col 0 -> mid col 1 -> outer col 2
PHASE1_ORDER: tuple[tuple[int, int], ...] = (
    (0, 0),  # Bottom  -> Jump
    (0, 2),  # Top     -> Overhead duck
    (0, 1),  # Middle  -> High jump
    (1, 2),  # Top     -> Overhead duck
    (1, 0),  # Bottom  -> Jump
    (1, 1),  # CORE    -> Hero high jump!
    (2, 0),  # Bottom  -> Jump
    (2, 2),  # Top     -> Overhead duck
    (2, 1),  # Middle  -> High jump
)

# Phase 2 (Left -> Right): peel inner col 2 -> mid col 1 -> outer col 0 (100% unobstructed)
PHASE2_ORDER: tuple[tuple[int, int], ...] = (
    (2, 2),  # Top     -> Overhead duck
    (2, 1),  # Middle  -> High jump
    (2, 0),  # Bottom  -> Jump
    (1, 0),  # Bottom  -> Jump
    (1, 2),  # Top     -> Overhead duck
    (1, 1),  # CORE    -> Hero high jump!
    (0, 0),  # Bottom  -> Jump
    (0, 2),  # Top     -> Overhead duck
    (0, 1),  # Middle  -> High jump
)

CellId = tuple[int, int]
RGB = tuple[int, int, int]


def _palette(*, is_dark: bool) -> dict[str, RGB]:
    """Return clean flat palette tokens optimized for APNG, WebP, and 256-color GIF."""
    if is_dark:
        return {
            "bg": (15, 23, 42),
            "ink": (226, 232, 240),
            "gold_fill": (245, 196, 24),
            "gold_border": (202, 146, 6),
            "gold_trail_1": (133, 111, 38),
            "gold_trail_2": (68, 63, 48),
            "core_outer": (226, 232, 240),
            "core_armor": (30, 41, 59),
            "core_fill": (239, 68, 68),
            "core_trail_1": (145, 52, 64),
            "core_trail_2": (72, 39, 56),
            "blue_fill": (56, 178, 246),
            "blue_border": (24, 132, 199),
            "shadow": (7, 11, 22),
        }
    return {
        "bg": (255, 255, 255),
        "ink": (44, 62, 80),
        "gold_fill": (241, 196, 15),
        "gold_border": (212, 166, 8),
        "gold_trail_1": (250, 228, 148),
        "gold_trail_2": (253, 242, 202),
        "core_outer": (44, 62, 80),
        "core_armor": (44, 62, 80),
        "core_fill": (231, 76, 60),
        "core_trail_1": (244, 172, 164),
        "core_trail_2": (250, 216, 212),
        "blue_fill": (52, 152, 219),
        "blue_border": (34, 124, 186),
        "shadow": (196, 206, 218),
    }


def setup_grit_canvas(
    *,
    is_dark: bool = False,
    transparent: bool = False,
    dpi: int = CANVAS_DPI,
) -> None:
    """Initialize the 110x71 GRIT COMPUTING canvas."""
    pal = _palette(is_dark=is_dark)
    bg_alpha = 0.0 if transparent else 1.0
    setup(
        width=CANVAS_W,
        height=CANVAS_H,
        dpi=dpi,
        background_color=pal["bg"],
        background_alpha=bg_alpha,
    )


def _draw_tracked_word(
    word: str,
    *,
    y_center: float,
    x_left: float,
    x_right: float,
    text_size: float,
    color: RGB,
) -> None:
    """Render an uppercase word in Avenger font with optically uniform glyph spacing."""
    base_glyph_w = 0.875 * (text_size * CANVAS_W / 720.0)
    widths = [base_glyph_w * _GLYPH_WIDTH_RATIO.get(ch, 1.0) for ch in word]
    total_glyph_w = sum(widths)
    gap = ((x_right - x_left) - total_glyph_w) / max(len(word) - 1, 1)

    char_style = Styles.Dark.patch(
        text_font=AVENGER_FONT,
        text_size=text_size,
        text_color=color,
        halign="center",
        valign="center",
    )
    cursor_x = x_left
    for ch, w in zip(word, widths, strict=True):
        cx = cursor_x + w / 2.0
        text((cx, y_center), ch, style=char_style)
        cursor_x += w + gap


def _draw_stage_frame(pal: dict[str, RGB]) -> None:
    """Draw flat GRIT / COMPUTING typography and clean horizontal ceiling/floor rails."""
    _draw_tracked_word(
        "GRIT",
        y_center=63.4,
        x_left=27.5,
        x_right=82.5,
        text_size=78.0,
        color=pal["ink"],
    )
    _draw_tracked_word(
        "COMPUTING",
        y_center=7.4,
        x_left=X_LEFT,
        x_right=X_RIGHT,
        text_size=76.0,
        color=pal["ink"],
    )

    rail_style = Styles.Neutral.patch(
        shape_fill_color=pal["ink"],
        shape_line_width=0,
        shape_r=0.45,
    )
    rectangle((CENTER_X, CEIL_Y), width=STAGE_W, height=RAIL_H, style=rail_style)
    rectangle((CENTER_X, FLOOR_Y), width=STAGE_W, height=RAIL_H, style=rail_style)


def _draw_module(
    xy: tuple[float, float],
    *,
    is_core: bool,
    pal: dict[str, RGB],
) -> None:
    """Draw a clean flat golden compute tile or flat crimson core."""
    cx, cy = xy
    if is_core:
        circle(
            (cx, cy),
            radius=TILE_SIZE / 2.0,
            style=Styles.Neutral.patch(
                shape_fill_color=pal["core_armor"],
                shape_line_color=pal["core_outer"],
                shape_line_width=1.4,
            ),
        )
        circle(
            (cx, cy),
            radius=2.55,
            style=Styles.Neutral.patch(shape_fill_color=pal["core_fill"], shape_line_width=0),
        )
        return

    rectangle(
        (cx, cy),
        width=TILE_SIZE,
        height=TILE_SIZE,
        style=Styles.Neutral.patch(
            shape_fill_color=pal["gold_fill"],
            shape_line_color=pal["gold_border"],
            shape_line_width=1.1,
            shape_r=1.65,
        ),
    )


def _draw_motion_trail(
    xy: tuple[float, float],
    *,
    direction: Literal[-1, 1],
    is_core: bool,
    pal: dict[str, RGB],
    transparent: bool = False,
) -> None:
    """Draw 2 subtle flat motion-wake echoes behind a fast-moving module."""
    cx, cy = xy
    c1 = pal["core_trail_1"] if is_core else pal["gold_trail_1"]
    c2 = pal["core_trail_2"] if is_core else pal["gold_trail_2"]
    a1 = 0.45 if transparent else 1.0
    a2 = 0.25 if transparent else 1.0

    dx1 = -direction * 4.4
    dx2 = -direction * 8.2
    if is_core:
        circle((cx + dx2, cy), radius=2.3, style=Styles.Neutral.patch(shape_fill_color=c2, shape_line_width=0, alpha=a2))
        circle((cx + dx1, cy), radius=3.1, style=Styles.Neutral.patch(shape_fill_color=c1, shape_line_width=0, alpha=a1))
    else:
        rectangle(
            (cx + dx2, cy),
            width=4.6,
            height=TILE_SIZE - 2.4,
            style=Styles.Neutral.patch(shape_fill_color=c2, shape_line_width=0, shape_r=1.2, alpha=a2),
        )
        rectangle(
            (cx + dx1, cy),
            width=6.0,
            height=TILE_SIZE - 1.2,
            style=Styles.Neutral.patch(shape_fill_color=c1, shape_line_width=0, shape_r=1.4, alpha=a1),
        )


def _draw_character(
    *,
    jump_y: float,
    squash: float,
    pal: dict[str, RGB],
    transparent: bool = False,
) -> None:
    """Draw the flat central blue character with subtle squash/stretch."""
    if not transparent:
        if jump_y > 12.0:
            sh_w, sh_h = 4.4, 0.70
        elif jump_y > 3.5:
            sh_w, sh_h = 6.2, 0.85
        else:
            sh_w, sh_h = 8.2, 0.95
        ellipse(
            (CENTER_X, FLOOR_Y + RAIL_H / 2.0 + 0.30),
            width=sh_w,
            height=sh_h,
            style=Styles.Neutral.patch(shape_fill_color=pal["shadow"], shape_line_width=0),
        )

    scale_x = 1.0 - 0.10 * squash
    scale_y = 1.0 + 0.12 * squash

    torso_w = TILE_SIZE * scale_x
    torso_h = TILE_SIZE * scale_y
    head_w = TILE_SIZE * (1.0 - 0.05 * squash)
    head_h = TILE_SIZE * (1.0 + 0.06 * squash)

    floor_contact_y = ROW_YS[0] - TILE_SIZE / 2.0
    torso_cy = floor_contact_y + jump_y + torso_h / 2.0
    gap = 1.15 * scale_y
    head_cy = torso_cy + torso_h / 2.0 + gap + head_h / 2.0

    body_style = Styles.Neutral.patch(
        shape_fill_color=pal["blue_fill"],
        shape_line_color=pal["blue_border"],
        shape_line_width=1.1,
        shape_r=1.85,
    )
    rectangle((CENTER_X, torso_cy), width=torso_w, height=torso_h, style=body_style)

    ellipse(
        (CENTER_X, head_cy),
        width=head_w,
        height=head_h,
        style=Styles.Neutral.patch(
            shape_fill_color=pal["blue_fill"],
            shape_line_color=pal["blue_border"],
            shape_line_width=1.1,
        ),
    )


def _ease_flight(u: float) -> float:
    """Smooth acceleration/deceleration curve with steady center cruise."""
    return 0.35 * u + 0.65 * 0.5 * (1.0 - math.cos(math.pi * u))


def _solve_u_at_center(x_start: float, x_end: float) -> float:
    """Find normalized time u in [0, 1] where block crosses CENTER_X via binary search."""
    target_s = (CENTER_X - x_start) / (x_end - x_start)
    lo, hi = 0.0, 1.0
    for _ in range(24):
        mid = 0.5 * (lo + hi)
        if _ease_flight(mid) < target_s:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def draw_grit_scene(
    *,
    left_cells: set[CellId],
    right_cells: set[CellId],
    flying_cell: tuple[CellId, float, float, Literal[-1, 1], bool] | None = None,
    jump_y: float = 0.0,
    squash: float = 0.0,
    is_dark: bool = False,
    transparent: bool = False,
) -> None:
    """Render one complete frame of the flat minimalist GRIT COMPUTING stage."""
    pal = _palette(is_dark=is_dark)
    _draw_stage_frame(pal)

    for col_idx, row_idx in sorted(left_cells):
        is_core = col_idx == 1 and row_idx == 1
        _draw_module((LEFT_COL_XS[col_idx], ROW_YS[row_idx]), is_core=is_core, pal=pal)

    for col_idx, row_idx in sorted(right_cells):
        is_core = col_idx == 1 and row_idx == 1
        _draw_module((RIGHT_COL_XS[col_idx], ROW_YS[row_idx]), is_core=is_core, pal=pal)

    if flying_cell is not None:
        (col_idx, row_idx), fx, fy, direction, show_trail = flying_cell
        is_core = col_idx == 1 and row_idx == 1
        if show_trail:
            _draw_motion_trail((fx, fy), direction=direction, is_core=is_core, pal=pal, transparent=transparent)
        _draw_module((fx, fy), is_core=is_core, pal=pal)

    _draw_character(jump_y=jump_y, squash=squash, pal=pal, transparent=transparent)


def build_grit_animation(
    *,
    is_dark: bool = False,
    transparent: bool = False,
    fps: float = 25.0,
    flight_frames: int = 10,
    dpi: int = CANVAS_DPI,
) -> Animation:
    """Build the full round-trip GRIT COMPUTING animation."""
    setup_grit_canvas(is_dark=is_dark, transparent=transparent, dpi=dpi)
    anim = Animation(fps=fps, loop=0)

    all_cells: set[CellId] = {(c, r) for c in range(3) for r in range(3)}
    left_cells: set[CellId] = set()
    right_cells: set[CellId] = set(all_cells)

    # Frame 0: Hero assembled state on Right (also serves as static thumbnail!)
    with anim.frame(duration=1.80):
        draw_grit_scene(
            left_cells=left_cells,
            right_cells=right_cells,
            is_dark=is_dark,
            transparent=transparent,
        )

    phases: tuple[tuple[tuple[CellId, ...], Literal[-1, 1]], ...] = (
        (PHASE1_ORDER, -1),  # Right -> Left
        (PHASE2_ORDER, 1),   # Left -> Right
    )

    for phase_idx, (order, direction) in enumerate(phases):
        for step_num, cell in enumerate(order):
            col_idx, row_idx = cell
            if direction == -1:
                right_cells.remove(cell)
                x_start = RIGHT_COL_XS[col_idx]
                x_end = LEFT_COL_XS[col_idx]
            else:
                left_cells.remove(cell)
                x_start = LEFT_COL_XS[col_idx]
                x_end = RIGHT_COL_XS[col_idx]

            y_pos = ROW_YS[row_idx]
            u_cross = _solve_u_at_center(x_start, x_end)
            half_win = 0.35

            # In-flight frames (1 .. flight_frames)
            for k in range(1, flight_frames + 1):
                u = k / (flight_frames + 1)
                s = _ease_flight(u)
                fx = x_start + (x_end - x_start) * s
                show_trail = 0.16 <= u <= 0.84

                jump_y = 0.0
                squash = 0.0
                dt = (u - u_cross) / half_win
                if row_idx in (0, 1):
                    peak_h = 12.2 if row_idx == 0 else 18.6
                    if abs(dt) < 1.0:
                        tau = 0.5 * (dt + 1.0)
                        jump_y = 4.0 * peak_h * tau * (1.0 - tau)
                        squash = 0.28 * math.sin(math.pi * tau)
                    elif -1.28 <= dt <= -1.0 or 1.0 <= dt <= 1.25:
                        squash = -0.45
                else:
                    if abs(dt) < 0.95:
                        tau = 0.5 * (dt + 0.95) / 0.95
                        squash = -0.85 * math.sin(math.pi * tau)

                with anim.frame():
                    draw_grit_scene(
                        left_cells=left_cells,
                        right_cells=right_cells,
                        flying_cell=(cell, fx, y_pos, direction, show_trail),
                        jump_y=jump_y,
                        squash=squash,
                        is_dark=is_dark,
                        transparent=transparent,
                    )

            # Arrival docking frame
            if direction == -1:
                left_cells.add(cell)
            else:
                right_cells.add(cell)

            is_phase_end = step_num == len(order) - 1
            if is_phase_end and phase_idx == 0:
                hold_dur = 1.60
            elif is_phase_end and phase_idx == 1:
                hold_dur = 0.08
            else:
                hold_dur = 0.16

            with anim.frame(duration=hold_dur):
                draw_grit_scene(
                    left_cells=left_cells,
                    right_cells=right_cells,
                    is_dark=is_dark,
                    transparent=transparent,
                )

    return anim
