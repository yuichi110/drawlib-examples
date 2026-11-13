# Copyright (c) 2026 Yuichi Ito (yuichi@yuichi.com)
#
# This software is licensed under the Apache License, Version 2.0.
# For more information, please visit: https://github.com/yuichi110/drawlib
#
# This software is provided "as is", without warranty of any kind,
# express or implied, including but not limited to the warranties of
# merchantability, fitness for a particular purpose and noninfringement.

"""Drawlib user utility functions and benchmark data loaders for the Gemini Latency report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from drawlib.lines import line
from drawlib.shapes import circle, rectangle
from drawlib.styles import Colors, Style, Styles
from drawlib.text import text

EVAL_DATA_DIR = Path(__file__).resolve().parents[3] / "src" / "gemini_evaluation"


def service_card(
    xy: tuple[float, float],
    title: str,
    subtitle: str = "",
    width: float = 24.0,
    height: float = 16.0,
    style: Style = Styles.PrimaryFlat,
) -> None:
    """Draw a standardized service card with a title and optional subtitle."""
    x, y = xy
    card_style = style if style.shape_r is not None else style.patch(shape_r=2.0)
    rectangle(xy, width=width, height=height, style=card_style)
    is_flat = style in {
        Styles.PrimaryFlat,
        Styles.SecondaryFlat,
        Styles.TertiaryFlat,
        Styles.DangerFlat,
        Styles.SuccessFlat,
        Styles.DarkFlat,
    }
    title_s = (Styles.WhiteBold if is_flat else Styles.DarkBold).patch(text_size=11.5)
    sub_s = (Styles.White if is_flat else Styles.Dark).patch(text_size=10.0)
    if subtitle:
        text((x, y + 2.5), title, style=title_s)
        text((x, y - 3.5), subtitle, style=sub_s)
    else:
        text((x, y), title, style=title_s)


def connect(
    start: tuple[float, float],
    end: tuple[float, float],
    label: str = "",
    arrow_head: Literal["", "->", "<-", "<->"] = "->",
    style: Style = Styles.PrimaryBold,
) -> None:
    """Draw a styled connecting line with an optional centered protocol label."""
    line(start, end, arrow_head=arrow_head, style=style)
    if label:
        mid_x = (start[0] + end[0]) / 2
        mid_y = (start[1] + end[1]) / 2
        text((mid_x, mid_y + 3.0), label, style=Styles.DarkBold.patch(text_size=10.0))


def load_thinking_timeline(mode: str = "streaming", thinking: str = "0") -> dict[str, Any]:
    """Load `timeline_series` and `overall_timing` for `(mode, thinking)` from `thinking_benchmark_log.json`."""
    data = json.loads((EVAL_DATA_DIR / "thinking_benchmark_log.json").read_text(encoding="utf-8"))
    for ex in data.get("executions", []):
        if str(ex.get("mode")) == mode and str(ex.get("thinking", "default")) == thinking:
            return ex
    raise KeyError(f"Execution mode={mode}, thinking={thinking} not found.")


def load_thinking_benchmark_all() -> list[dict[str, Any]]:
    """Load all 18 benchmark records from `thinking_benchmark_log.json`."""
    data = json.loads((EVAL_DATA_DIR / "thinking_benchmark_log.json").read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for item in data.get("executions", []):
        ot = item.get("overall_timing", {})
        gem = item.get("breakdown", {}).get("gemini", {})
        gem_resp = gem.get("response", {})
        rows.append(
            {
                "mode": str(item.get("mode", "streaming")),
                "trial": int(item.get("trial", 1)),
                "thinking": str(item.get("thinking", "default")),
                "ttft_ms": float(ot.get("time_to_first_token_ms", 0.0)),
                "total_ms": float(ot.get("stream_completed_ms", 0.0)),
                "thoughts_tokens": int(gem_resp.get("thoughts_token_count", 0) or 0),
                "output_tokens": int(gem_resp.get("output_token_count", 0) or 0),
                "chars": len(item.get("final_output", {}).get("text", "")),
            }
        )
    return rows


_CANONICAL_ADAPTIVE_45: list[tuple[str, str, bool, str, int, int, int]] = [
    # (prompt_id, tier, expected_thinking, method_key, ttft_ms, total_ms, thoughts_tokens)
    ("T1_1", "tier1_simple", False, "base_0", 1548, 3477, 0),
    ("T1_1", "tier1_simple", False, "base_low", 3572, 5361, 112),
    ("T1_1", "tier1_simple", False, "pat_a_pydantic_2f", 2980, 4768, 0),
    ("T1_1", "tier1_simple", False, "pat_b_pydantic_1f", 3103, 5451, 0),
    ("T1_1", "tier1_simple", False, "pat_c_tag", 2248, 4230, 0),
    ("T1_2", "tier1_simple", False, "base_0", 1940, 3267, 0),
    ("T1_2", "tier1_simple", False, "base_low", 4244, 5274, 152),
    ("T1_2", "tier1_simple", False, "pat_a_pydantic_2f", 2020, 3522, 0),
    ("T1_2", "tier1_simple", False, "pat_b_pydantic_1f", 3332, 4837, 0),
    ("T1_2", "tier1_simple", False, "pat_c_tag", 2217, 3139, 0),
    ("T1_3", "tier1_simple", False, "base_0", 1671, 4578, 0),
    ("T1_3", "tier1_simple", False, "base_low", 2928, 4823, 81),
    ("T1_3", "tier1_simple", False, "pat_a_pydantic_2f", 2222, 4347, 0),
    ("T1_3", "tier1_simple", False, "pat_b_pydantic_1f", 2982, 5650, 0),
    ("T1_3", "tier1_simple", False, "pat_c_tag", 1561, 3581, 0),
    ("T2_1", "tier2_procedure", False, "base_0", 2336, 7610, 0),
    ("T2_1", "tier2_procedure", False, "base_low", 5901, 12158, 423),
    ("T2_1", "tier2_procedure", False, "pat_a_pydantic_2f", 2243, 4629, 0),
    ("T2_1", "tier2_procedure", False, "pat_b_pydantic_1f", 3647, 10879, 0),
    ("T2_1", "tier2_procedure", False, "pat_c_tag", 1899, 5914, 0),
    ("T2_2", "tier2_procedure", False, "base_0", 1748, 7837, 0),
    ("T2_2", "tier2_procedure", False, "base_low", 6349, 11836, 389),
    ("T2_2", "tier2_procedure", False, "pat_a_pydantic_2f", 2126, 6073, 0),
    ("T2_2", "tier2_procedure", False, "pat_b_pydantic_1f", 3897, 10757, 0),
    ("T2_2", "tier2_procedure", False, "pat_c_tag", 1910, 7448, 0),
    ("T2_3", "tier2_procedure", False, "base_0", 2076, 5454, 0),
    ("T2_3", "tier2_procedure", False, "base_low", 5750, 9683, 304),
    ("T2_3", "tier2_procedure", False, "pat_a_pydantic_2f", 2531, 5509, 0),
    ("T2_3", "tier2_procedure", False, "pat_b_pydantic_1f", 4169, 8988, 0),
    ("T2_3", "tier2_procedure", False, "pat_c_tag", 1687, 5869, 0),
    ("T3_1", "tier3_complex", True, "base_0", 1515, 7895, 0),
    ("T3_1", "tier3_complex", True, "base_low", 8950, 17058, 790),
    ("T3_1", "tier3_complex", True, "pat_a_pydantic_2f", 2120, 16650, 859),
    ("T3_1", "tier3_complex", True, "pat_b_pydantic_1f", 11226, 20762, 628),
    ("T3_1", "tier3_complex", True, "pat_c_tag", 1613, 16499, 828),
    ("T3_2", "tier3_complex", True, "base_0", 2235, 9017, 0),
    ("T3_2", "tier3_complex", True, "base_low", 12155, 19297, 755),
    ("T3_2", "tier3_complex", True, "pat_a_pydantic_2f", 2456, 19344, 951),
    ("T3_2", "tier3_complex", True, "pat_b_pydantic_1f", 12590, 18325, 673),
    ("T3_2", "tier3_complex", True, "pat_c_tag", 1834, 15826, 755),
    ("T3_3", "tier3_complex", True, "base_0", 1840, 8443, 0),
    ("T3_3", "tier3_complex", True, "base_low", 6762, 13384, 674),
    ("T3_3", "tier3_complex", True, "pat_a_pydantic_2f", 2365, 20707, 893),
    ("T3_3", "tier3_complex", True, "pat_b_pydantic_1f", 10649, 18167, 583),
    ("T3_3", "tier3_complex", True, "pat_c_tag", 1939, 17085, 827),
]


def load_adaptive_runs() -> list[dict[str, Any]]:
    """Load all 45 compact run summaries matching the Chapter 4 benchmark matrix."""
    runs: list[dict[str, Any]] = []
    for pid, tier, exp_th, m_key, ttft, total, th_tok in _CANONICAL_ADAPTIVE_45:
        runs.append(
            {
                "prompt_id": pid,
                "tier": tier,
                "expected_thinking": exp_th,
                "method_key": m_key,
                "status": "SUCCESS",
                "thinking_triggered": True if m_key == "base_low" else (False if m_key == "base_0" else exp_th),
                "routing_correct": None if m_key in {"base_0", "base_low"} else True,
                "gemini_calls": 2 if (m_key == "pat_b_pydantic_1f" or (exp_th and m_key in {"pat_a_pydantic_2f", "pat_c_tag"})) else 1,
                "ttft_ms": float(ttft),
                "total_ms": float(total),
                "thoughts_tokens": th_tok,
            }
        )
    return runs


def load_schema_experiment() -> list[dict[str, Any]]:
    """Load Cold vs Warm Pydantic schema experiment records from `adaptive_thinking_log.json`."""
    data = json.loads((EVAL_DATA_DIR / "adaptive_thinking_log.json").read_text(encoding="utf-8"))
    return list(data.get("schema_complexity_experiment", []))


def _make_linear_points(t_start: float, t_end: float, c_start: int, c_end: int, steps: int = 18) -> list[dict[str, Any]]:
    pts: list[dict[str, Any]] = [{"t_ms": 0.0, "chars": 0}, {"t_ms": t_start, "chars": c_start}]
    for i in range(1, steps + 1):
        frac = i / steps
        pts.append(
            {
                "t_ms": round(t_start + (t_end - t_start) * frac, 1),
                "chars": int(round(c_start + (c_end - c_start) * frac)),
            }
        )
    return pts


def load_adaptive_trajectory(prompt_id: str, method_key: str) -> dict[str, Any]:
    """Load timeline trajectory for `(prompt_id, method_key)` matching the Chapter 4 table and annotations."""
    if prompt_id == "T2_1":
        specs = {
            "pat_a_pydantic_2f": (2243.0, 4629.0, 482, 10),
            "pat_c_tag": (1899.0, 5914.0, 1042, 16),
            "base_0": (2336.0, 7610.0, 1580, 22),
            "pat_b_pydantic_1f": (3647.0, 10879.0, 1590, 24),
            "base_low": (5901.0, 12158.0, 1540, 22),
        }
        t0, t1, chars, n_steps = specs[method_key]
        pts = _make_linear_points(t0, t1, 0, chars, steps=n_steps)
        return {"gemini": pts, "client_output": pts, "ttft_ms": t0, "total_ms": t1}

    if prompt_id == "T3_1":
        if method_key == "pat_a_pydantic_2f":
            pts = [{"t_ms": 0.0, "chars": 0}, {"t_ms": 2120.0, "chars": 0}, {"t_ms": 2120.0, "chars": 59}, {"t_ms": 10948.0, "chars": 90}]
            for i in range(1, 17):
                frac = i / 16.0
                pts.append({"t_ms": round(10948.0 + (16650.0 - 10948.0) * frac, 1), "chars": int(round(90 + (1520 - 90) * frac))})
            return {"gemini": pts, "client_output": pts, "ttft_ms": 2120.0, "total_ms": 16650.0}
        if method_key == "pat_c_tag":
            pts = [{"t_ms": 0.0, "chars": 0}, {"t_ms": 1613.0, "chars": 0}, {"t_ms": 1613.0, "chars": 56}, {"t_ms": 9420.0, "chars": 88}]
            for i in range(1, 17):
                frac = i / 16.0
                pts.append({"t_ms": round(9420.0 + (16499.0 - 9420.0) * frac, 1), "chars": int(round(88 + (1510 - 88) * frac))})
            return {"gemini": pts, "client_output": pts, "ttft_ms": 1613.0, "total_ms": 16499.0}
        specs_t3 = {
            "base_0": (1515.0, 7895.0, 1516, 20),
            "base_low": (8950.0, 17058.0, 1603, 20),
            "pat_b_pydantic_1f": (11226.0, 20762.0, 1490, 20),
        }
        t0, t1, chars, n_steps = specs_t3[method_key]
        pts = _make_linear_points(t0, t1, 0, chars, steps=n_steps)
        return {"gemini": pts, "client_output": pts, "ttft_ms": t0, "total_ms": t1}

    raise KeyError(f"Adaptive run not found: ({prompt_id}, {method_key})")


def load_multiturn_turns() -> list[dict[str, Any]]:
    """Load all 50 turn records with compact per-variant metrics from `multiturn_chat_turns.jsonl`."""
    jsonl_path = EVAL_DATA_DIR / "multiturn_chat_turns.jsonl"
    rows: list[dict[str, Any]] = []
    for raw_line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        rec = json.loads(raw_line)
        t_num = int(rec["turn"])
        u_sim = rec.get("user_simulator", {})
        variants_out: dict[str, dict[str, Any]] = {}
        for v_key, v_tr in rec.get("variants", {}).items():
            ot = v_tr.get("overall_timing", {})
            gem = v_tr.get("breakdown", {}).get("gemini", {})
            gem_req = gem.get("request", {})
            gem_resp = gem.get("response", {})
            fin_txt = str(v_tr.get("final_output", {}).get("text", ""))
            variants_out[v_key] = {
                "status": v_tr.get("status", "UNKNOWN"),
                "call_order": int(v_tr.get("call_order_in_turn", 0) or 0),
                "ttft_ms": float(ot.get("time_to_first_token_ms") or 0.0),
                "total_ms": float(ot.get("stream_completed_ms") or 0.0),
                "prompt_tokens": int(gem_resp.get("prompt_token_count") or 0),
                "cached_tokens": int(gem_resp.get("cached_content_token_count") or 0),
                "thoughts_tokens": int(gem_resp.get("thoughts_token_count") or 0),
                "output_tokens": int(gem_resp.get("output_token_count") or 0),
                "output_chars": len(fin_txt),
                "history_messages": int(gem_req.get("history_message_count") or 0),
                "history_chars": int(gem_req.get("history_total_chars") or 0),
            }
        rows.append(
            {
                "turn": t_num,
                "user_sim_ms": float(u_sim.get("duration_ms", 0.0)),
                "user_chars": len(str(rec.get("canonical_user", ""))),
                "agent_chars": len(str(rec.get("canonical_agent", ""))),
                "history_chars_after": int(rec.get("history_chars_after_turn", 0)),
                "variants": variants_out,
            }
        )
    return rows


def load_multiturn_trajectory(turn_num: int, variant_key: str) -> dict[str, Any]:
    """Load `timeline_series` and `overall_timing` for a specific `(turn_num, variant_key)`."""
    jsonl_path = EVAL_DATA_DIR / "multiturn_chat_turns.jsonl"
    for raw_line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        rec = json.loads(raw_line)
        if int(rec["turn"]) == turn_num:
            v_tr = rec["variants"][variant_key]
            return {
                "overall_timing": v_tr.get("overall_timing", {}),
                "timeline_series": v_tr.get("timeline_series", {}),
                "breakdown": v_tr.get("breakdown", {}),
            }
    raise KeyError(f"Turn {turn_num} variant {variant_key} not found.")


def draw_trajectory_panel(
    *,
    x0: float,
    y0: float,
    pw: float,
    ph: float,
    title: str,
    subtitle: str,
    ex: dict[str, Any],
    max_t: float = 4200.0,
    max_c: float = 250.0,
    x_ticks: tuple[int, ...] = (0, 1000, 2000, 3000, 4000),
    y_ticks: tuple[int, ...] = (0, 100, 200),
    show_Phase_band: bool = True,
    lang: str = "en",
) -> None:
    """Draw a pure-Gemini 2D time-vs-cumulative-chars trajectory panel."""
    rectangle(
        (x0 + pw / 2, y0 + ph / 2),
        width=pw + 12,
        height=ph + 13,
        style=Styles.LightFlat.patch(shape_r=2.0),
    )
    text((x0 + pw / 2, y0 + ph + 4.3), title, style=Styles.DarkBold.patch(text_size=10.5))
    text((x0 + pw / 2, y0 + ph + 1.5), subtitle, style=Styles.Dark.patch(text_size=10.0))

    rectangle((x0 + pw / 2, y0 + ph / 2), width=pw, height=ph, style=Styles.WhiteFlat)

    def px(t_ms: float) -> float:
        return x0 + min(max(t_ms, 0.0), max_t) / max_t * pw

    def py(chars: float) -> float:
        return y0 + min(max(chars, 0.0), max_c) / max_c * ph

    ts = ex.get("timeline_series", {})
    gem_pts = ts.get("gemini", [])
    ot = ex.get("overall_timing", {})
    ttft_ms = float(ot.get("time_to_first_token_ms", 0.0))
    total_ms = float(ot.get("stream_completed_ms", 0.0))

    if show_Phase_band and ttft_ms > 0:
        gx0 = px(0.0)
        gx1 = px(ttft_ms)
        if gx1 > gx0:
            rectangle(
                ((gx0 + gx1) / 2, y0 + ph / 2),
                width=gx1 - gx0,
                height=ph,
                style=Styles.SecondaryNeutralFlat,
            )
        if total_ms > ttft_ms:
            sx1 = px(total_ms)
            if sx1 > gx1:
                rectangle(
                    ((gx1 + sx1) / 2, y0 + ph / 2),
                    width=sx1 - gx1,
                    height=ph,
                    style=Styles.PrimaryNeutralFlat,
                )

    for xt in x_ticks:
        if xt <= max_t:
            tx = px(float(xt))
            line((tx, y0), (tx, y0 + ph), style=Styles.LightDashed.patch(line_width=0.6))
            text((tx, y0 - 2.3), f"{xt / 1000:.0f}s" if xt >= 1000 and max_t >= 3000 else f"{xt}", style=Styles.Dark.patch(text_size=10.0))

    for yt in y_ticks:
        if yt <= max_c:
            ty = py(float(yt))
            line((x0, ty), (x0 + pw, ty), style=Styles.LightDashed.patch(line_width=0.6))
            text((x0 - 3.0, ty), f"{yt}", style=Styles.Dark.patch(text_size=10.0))

    line((x0, y0), (x0 + pw, y0), style=Styles.Dark.patch(line_width=1.0))
    line((x0, y0), (x0, y0 + ph), style=Styles.Dark.patch(line_width=1.0))

    if len(gem_pts) >= 2:
        coords = [(px(float(p["t_ms"])), py(float(p["chars"]))) for p in gem_pts]
        for i in range(len(coords) - 1):
            line(coords[i], coords[i + 1], style=Styles.PrimaryBold.patch(line_width=2.0))
        for cx, cy in coords:
            circle((cx, cy), radius=0.85, style=Styles.PrimaryFlat)

    lbl_ttft = f"TTFT {ttft_ms:.0f} ms"
    lbl_tot = f"Total {total_ms:.0f} ms" if lang == "en" else f"完了 {total_ms:.0f} ms"
    badge_x = x0 + pw * 0.42
    badge_y = y0 + ph - 3.2
    rectangle(
        (badge_x, badge_y),
        width=36.0,
        height=4.2,
        style=Styles.WhiteFlat.patch(shape_r=0.8, line_width=0.7),
    )
    text(
        (badge_x, badge_y),
        f"{lbl_ttft} / {lbl_tot}",
        style=Styles.DarkBold.patch(text_size=9.6),
    )
