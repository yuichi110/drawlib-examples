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


def load_adaptive_runs() -> list[dict[str, Any]]:
    """Load all 45 compact run summaries from `adaptive_thinking_runs.jsonl`."""
    jsonl_path = EVAL_DATA_DIR / "adaptive_thinking_runs.jsonl"
    runs: list[dict[str, Any]] = []
    for ln in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        rec = json.loads(ln)
        s = rec["summary"]
        runs.append(
            {
                "prompt_id": s["prompt_id"],
                "tier": s["tier"],
                "tier_label": s["tier_label"],
                "title": s["title"],
                "expected_thinking": bool(s["expected_thinking"]),
                "method_key": s["method_key"],
                "method_label": s["method_label"],
                "status": s["status"],
                "thinking_triggered": bool(s["thinking_triggered"]),
                "routing_correct": s["routing_correct"],
                "flag_decided_ms": float(s["flag_decided_ms"]) if s["flag_decided_ms"] is not None else None,
                "stage2_first_chunk_ms": (
                    float(s["stage2_first_chunk_ms"]) if s["stage2_first_chunk_ms"] is not None else None
                ),
                "gemini_calls": int(s["gemini_calls"] or 1),
                "ttft_ms": float(s["ttft_ms"] or 0.0),
                "total_ms": float(s["total_ms"] or 0.0),
                "prompt_tokens": int(s["prompt_tokens"] or 0),
                "thoughts_tokens": int(s["thoughts_tokens"] or 0),
                "output_tokens": int(s["output_tokens"] or 0),
                "output_chars": int(s["output_chars"] or 0),
            }
        )
    return runs


def load_schema_experiment() -> list[dict[str, Any]]:
    """Load Cold vs Warm Pydantic schema experiment records from `adaptive_thinking_log.json`."""
    data = json.loads((EVAL_DATA_DIR / "adaptive_thinking_log.json").read_text(encoding="utf-8"))
    return list(data.get("schema_complexity_experiment", []))


def load_adaptive_trajectory(prompt_id: str, method_key: str) -> dict[str, Any]:
    """Load timeline trajectory for a given `(prompt_id, method_key)` from `adaptive_thinking_runs.jsonl`."""
    jsonl_path = EVAL_DATA_DIR / "adaptive_thinking_runs.jsonl"
    for ln in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        rec = json.loads(ln)
        if rec["prompt_id"] == prompt_id and rec["method_key"] == method_key:
            tr = rec["trace"]
            ts = tr.get("timeline_series", {})
            ot = tr.get("overall_timing", {})
            ad = tr.get("adaptive", {})
            return {
                "gemini": ts.get("gemini", []),
                "client_output": ts.get("client_output", []),
                "ttft_ms": float(ot.get("time_to_first_token_ms", 0.0)),
                "total_ms": float(ot.get("stream_completed_ms", 0.0)),
                "flag_decided_ms": ad.get("flag_decided_ms"),
                "stage2_first_chunk_ms": ad.get("stage2_first_chunk_ms"),
                "thinking_triggered": ad.get("thinking_triggered"),
                "summary": rec["summary"],
            }
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
                style=Styles.Secondary.patch(line_width=0, shape_r=0),
            )
        if total_ms > ttft_ms:
            sx1 = px(total_ms)
            if sx1 > gx1:
                rectangle(
                    ((gx1 + sx1) / 2, y0 + ph / 2),
                    width=sx1 - gx1,
                    height=ph,
                    style=Styles.Primary.patch(line_width=0, shape_r=0),
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

    lbl_ttft = f"TTFT {ttft_ms:.0f}ms"
    lbl_tot = f"Total {total_ms:.0f}ms" if lang == "en" else f"完了 {total_ms:.0f}ms"
    text(
        (x0 + pw * 0.34, y0 + ph - 3.0),
        f"{lbl_ttft} / {lbl_tot}",
        style=Styles.DarkBold.patch(text_size=10.0),
    )
