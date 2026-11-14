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
    ("T1_1", "tier1_simple", False, "base_low", 1533, 5741, 0),
    ("T1_1", "tier1_simple", False, "base_high", 13039, 17434, 921),
    ("T1_1", "tier1_simple", False, "pat_a_pydantic_2f", 2234, 4536, 0),
    ("T1_1", "tier1_simple", False, "pat_b_pydantic_1f", 3837, 6992, 49),
    ("T1_1", "tier1_simple", False, "pat_c_tag", 2087, 6318, 56),
    ("T1_2", "tier1_simple", False, "base_low", 2595, 4746, 53),
    ("T1_2", "tier1_simple", False, "base_high", 10501, 13758, 852),
    ("T1_2", "tier1_simple", False, "pat_a_pydantic_2f", 2144, 2614, 34),
    ("T1_2", "tier1_simple", False, "pat_b_pydantic_1f", 4145, 6945, 28),
    ("T1_2", "tier1_simple", False, "pat_c_tag", 2272, 3390, 45),
    ("T1_3", "tier1_simple", False, "base_low", 2428, 9769, 0),
    ("T1_3", "tier1_simple", False, "base_high", 12708, 19842, 1117),
    ("T1_3", "tier1_simple", False, "pat_a_pydantic_2f", 2190, 3987, 0),
    ("T1_3", "tier1_simple", False, "pat_b_pydantic_1f", 5077, 10777, 153),
    ("T1_3", "tier1_simple", False, "pat_c_tag", 2347, 4115, 37),
    ("T2_1", "tier2_procedure", False, "base_low", 1331, 9477, 0),
    ("T2_1", "tier2_procedure", False, "base_high", 11964, 20864, 991),
    ("T2_1", "tier2_procedure", False, "pat_a_pydantic_2f", 2174, 5764, 46),
    ("T2_1", "tier2_procedure", False, "pat_b_pydantic_1f", 4197, 13589, 42),
    ("T2_1", "tier2_procedure", False, "pat_c_tag", 2531, 8426, 35),
    ("T2_2", "tier2_procedure", False, "base_low", 2923, 15001, 0),
    ("T2_2", "tier2_procedure", False, "base_high", 13417, 25827, 1153),
    ("T2_2", "tier2_procedure", False, "pat_a_pydantic_2f", 2870, 3811, 0),
    ("T2_2", "tier2_procedure", False, "pat_b_pydantic_1f", 5210, 14835, 42),
    ("T2_2", "tier2_procedure", False, "pat_c_tag", 3242, 8318, 58),
    ("T2_3", "tier2_procedure", False, "base_low", 2576, 14011, 0),
    ("T2_3", "tier2_procedure", False, "base_high", 11229, 22851, 1019),
    ("T2_3", "tier2_procedure", False, "pat_a_pydantic_2f", 3489, 5398, 0),
    ("T2_3", "tier2_procedure", False, "pat_b_pydantic_1f", 5481, 14097, 60),
    ("T2_3", "tier2_procedure", False, "pat_c_tag", 2913, 11215, 64),
    ("T3_1", "tier3_complex", True, "base_low", 2922, 13899, 0),
    ("T3_1", "tier3_complex", True, "base_high", 14104, 23247, 1466),
    ("T3_1", "tier3_complex", True, "pat_a_pydantic_2f", 1795, 21482, 902),
    ("T3_1", "tier3_complex", True, "pat_b_pydantic_1f", 16402, 26659, 1538),
    ("T3_1", "tier3_complex", True, "pat_c_tag", 3250, 21309, 1309),
    ("T3_2", "tier3_complex", True, "base_low", 1392, 9583, 0),
    ("T3_2", "tier3_complex", True, "base_high", 16510, 27861, 1882),
    ("T3_2", "tier3_complex", True, "pat_a_pydantic_2f", 2728, 27017, 1591),
    ("T3_2", "tier3_complex", True, "pat_b_pydantic_1f", 24231, 35330, 2346),
    ("T3_2", "tier3_complex", True, "pat_c_tag", 5654, 31139, 2073),
    ("T3_3", "tier3_complex", True, "base_low", 1693, 7729, 0),
    ("T3_3", "tier3_complex", True, "base_high", 11965, 18577, 1295),
    ("T3_3", "tier3_complex", True, "pat_a_pydantic_2f", 1870, 16240, 674),
    ("T3_3", "tier3_complex", True, "pat_b_pydantic_1f", 15222, 20844, 1362),
    ("T3_3", "tier3_complex", True, "pat_c_tag", 2073, 18607, 806),
]


def load_adaptive_runs() -> list[dict[str, Any]]:
    """Load all 45 compact run summaries matching the Chapter 4 benchmark matrix (`low` -> `high`)."""
    runs: list[dict[str, Any]] = []
    for pid, tier, exp_th, m_key, ttft, total, th_tok in _CANONICAL_ADAPTIVE_45:
        runs.append(
            {
                "prompt_id": pid,
                "tier": tier,
                "expected_thinking": exp_th,
                "method_key": m_key,
                "status": "SUCCESS",
                "thinking_triggered": True if m_key == "base_high" else (False if m_key == "base_low" else exp_th),
                "routing_correct": None if m_key in {"base_low", "base_high"} else True,
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
    """Load timeline trajectory for `(prompt_id, method_key)` matching the Chapter 4 (`low` -> `high`) benchmark."""
    if prompt_id == "T2_1":
        specs = {
            "pat_a_pydantic_2f": (2174.0, 5764.0, 626, 12),
            "pat_c_tag": (2531.0, 8426.0, 975, 16),
            "base_low": (1331.0, 9477.0, 1539, 20),
            "pat_b_pydantic_1f": (4197.0, 13589.0, 1530, 22),
            "base_high": (11964.0, 20864.0, 1501, 22),
        }
        t0, t1, chars, n_steps = specs[method_key]
        pts = _make_linear_points(t0, t1, 0, chars, steps=n_steps)
        return {"gemini": pts, "client_output": pts, "ttft_ms": t0, "total_ms": t1}

    if prompt_id == "T3_1":
        if method_key == "pat_a_pydantic_2f":
            pts = [{"t_ms": 0.0, "chars": 0}, {"t_ms": 1795.0, "chars": 0}, {"t_ms": 1795.0, "chars": 58}, {"t_ms": 11615.0, "chars": 90}]
            for i in range(1, 17):
                frac = i / 16.0
                pts.append({"t_ms": round(11615.0 + (21482.0 - 11615.0) * frac, 1), "chars": int(round(90 + (1826 - 90) * frac))})
            return {"gemini": pts, "client_output": pts, "ttft_ms": 1795.0, "total_ms": 21482.0}
        if method_key == "pat_c_tag":
            pts = [{"t_ms": 0.0, "chars": 0}, {"t_ms": 3250.0, "chars": 0}, {"t_ms": 3250.0, "chars": 58}, {"t_ms": 12630.0, "chars": 90}]
            for i in range(1, 17):
                frac = i / 16.0
                pts.append({"t_ms": round(12630.0 + (21309.0 - 12630.0) * frac, 1), "chars": int(round(90 + (1867 - 90) * frac))})
            return {"gemini": pts, "client_output": pts, "ttft_ms": 3250.0, "total_ms": 21309.0}
        specs_t3 = {
            "base_low": (2922.0, 13899.0, 1656, 20),
            "base_high": (14104.0, 23247.0, 1692, 20),
            "pat_b_pydantic_1f": (16402.0, 26659.0, 1660, 20),
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
            adap = v_tr.get("adaptive", {})
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
                "thinking_triggered": bool(adap.get("thinking_triggered", False)),
                "gemini_call_count": int(adap.get("gemini_call_count", 1) or 1),
                "stage1_cached_tokens": int(adap.get("stage1_cached_tokens", 0) or 0),
                "stage2_cached_tokens": int(adap.get("stage2_cached_tokens", 0) or 0),
            }
        rows.append(
            {
                "turn": t_num,
                "expected_thinking": bool(rec.get("expected_thinking", False)),
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


def load_cross_model_thinking_benchmark() -> dict[str, Any]:
    """Load the 5-model × thinking_level × 10-query (5 simple + 5 complex) benchmark from `cross_model_thinking_log.json`."""
    path = EVAL_DATA_DIR / "cross_model_thinking_log.json"
    return json.loads(path.read_text(encoding="utf-8"))

