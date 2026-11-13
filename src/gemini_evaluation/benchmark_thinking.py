# Copyright (c) 2026 Yuichi Ito (yuichi@yuichi.com)
#
# This software is licensed under the Apache License, Version 2.0.
# For more information, please visit: https://github.com/yuichi110/drawlib
#
# This software is provided "as is", without warranty of any kind,
# express or implied, including but not limited to the warranties of
# merchantability, fitness for a particular purpose and noninfringement.

"""Benchmark runner for Blocking and Streaming calls across all 6 ThinkingConfig options."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google import genai

from gemini_evaluation.llm_call import (
    MODEL,
    ThinkingOption,
    create_client,
    generate_text,
    resolve_thinking_config,
    stream_text,
)
from gemini_evaluation.main import DEFAULT_PROMPT
from gemini_evaluation.tracer import build_execution_report, now_jst, save_yaml_report

BENCHMARK_LOG_PATH = Path(__file__).resolve().parent / "thinking_benchmark_log.yaml"

THINKING_OPTIONS: list[ThinkingOption] = [0, 1, 2, 3, 4, None]
MODES: list[tuple[str, str, int]] = [
    ("blocking", "blocking", 1),
    ("streaming", "streaming", 1),
    ("streaming_trial2", "streaming", 2),
]


async def run_single_combination(
    client: genai.Client,
    mode_label: str,
    api_mode: str,
    trial: int,
    thinking: ThinkingOption,
    prompt: str,
) -> dict[str, Any]:
    """Execute one (mode, thinking) combination and return its trace dictionary."""
    trace: dict[str, Any] = {}
    if api_mode == "blocking":
        await generate_text(
            client,
            prompt,
            thinking=thinking,
            trace=trace,
        )
    elif api_mode == "streaming":
        async for _ in stream_text(
            client,
            prompt,
            thinking=thinking,
            trace=trace,
        ):
            pass
    else:
        raise ValueError(f"Unsupported mode: {api_mode}")
    trace["mode"] = mode_label
    trace["trial"] = trial
    return trace


def print_summary_table(executions: list[dict[str, Any]]) -> None:
    """Print a formatted summary table of all benchmark executions to stdout."""
    header = (
        f"{'Mode':<16} | {'Thinking':<8} | {'TTFT (ms)':>10} | {'Total (ms)':>10} | "
        f"{'ThTok':>6} | {'OutTok':>6} | {'Chars':>5}"
    )
    print("\n" + "=" * len(header))
    print(header)
    print("-" * len(header))
    for ex in executions:
        mode_lbl = str(ex.get("mode", ex.get("pattern", "")))[:16]
        t_lbl = str(ex.get("thinking", "default"))
        ot = ex.get("overall_timing", {})
        gem = ex.get("breakdown", {}).get("gemini", {})
        gem_resp = gem.get("response", {})
        chars = len(ex.get("final_output", {}).get("text", ""))
        print(
            f"{mode_lbl:<16} | {t_lbl:<8} | "
            f"{ot.get('time_to_first_token_ms', 0.0):10.2f} | "
            f"{ot.get('stream_completed_ms', 0.0):10.2f} | "
            f"{gem_resp.get('thoughts_token_count', 0) or 0:6d} | "
            f"{gem_resp.get('output_token_count', 0) or 0:6d} | "
            f"{chars:5d}"
        )
    print("=" * len(header) + "\n")


async def run_benchmark(only_specs: list[str] | None = None) -> None:
    """Run the 3x6 benchmark matrix (18 runs) and save `thinking_benchmark_log.yaml` and `.json`."""
    suite_started_at = now_jst()
    client = create_client()
    prompt = DEFAULT_PROMPT

    print("Warming up Google AI Studio Gemini connection...")
    await run_single_combination(client, "blocking", "blocking", 1, 0, prompt)
    print("Warm-up complete.\n")

    existing_map: dict[tuple[str, str], dict[str, Any]] = {}
    if only_specs and BENCHMARK_LOG_PATH.is_file():
        loaded = yaml.safe_load(BENCHMARK_LOG_PATH.read_text(encoding="utf-8")) or {}
        for item in loaded.get("executions", []):
            mode_val = str(item.get("mode", ""))
            t_lbl = str(item.get("thinking", "default"))
            if mode_val:
                existing_map[(mode_val, t_lbl)] = item

    target_set: set[tuple[str, str]] | None = None
    if only_specs:
        target_set = set()
        for spec in only_specs:
            m_str, _, t_str = spec.partition(":")
            t_label, _ = resolve_thinking_config(t_str if t_str != "" else None)  # type: ignore[arg-type]
            target_set.add((m_str, t_label))

    sem = asyncio.Semaphore(6)

    async def _run_cell(mode_label: str, api_mode: str, trial: int, t_opt: ThinkingOption) -> dict[str, Any]:
        t_label, _ = resolve_thinking_config(t_opt)
        key = (mode_label, t_label)
        if target_set is not None and key not in target_set and key in existing_map:
            return existing_map[key]
        async with sem:
            print(f"Running mode={mode_label} × thinking={t_label} ({t_opt!r})...", flush=True)
            trace = await run_single_combination(client, mode_label, api_mode, trial, t_opt, prompt)
            ot = trace.get("overall_timing", {})
            gem_resp = trace.get("breakdown", {}).get("gemini", {}).get("response", {})
            print(
                f"  [Done {mode_label}:{t_label}] TTFT={ot.get('time_to_first_token_ms')}ms, "
                f"Total={ot.get('stream_completed_ms')}ms, "
                f"ThTok={gem_resp.get('thoughts_token_count')}, "
                f"OutTok={gem_resp.get('output_token_count')}",
                flush=True,
            )
            return trace

    executions = list(
        await asyncio.gather(
            *(
                _run_cell(mode_label, api_mode, trial, t_opt)
                for mode_label, api_mode, trial in MODES
                for t_opt in THINKING_OPTIONS
            )
        )
    )

    suite_completed_at = now_jst()
    report = build_execution_report(
        suite_started_at=suite_started_at,
        suite_completed_at=suite_completed_at,
        model=MODEL,
        original_user_prompt=prompt,
        executions=executions,
    )
    save_yaml_report(report, BENCHMARK_LOG_PATH)
    print_summary_table(executions)
    print(f"Saved benchmark log to: {BENCHMARK_LOG_PATH}")


def main() -> None:
    """CLI entry point for running or re-testing benchmark combinations."""
    parser = argparse.ArgumentParser(description="Run Blocking & Streaming × thinking benchmark.")
    parser.add_argument(
        "--only",
        nargs="*",
        help="Optional list of 'mode:thinking' specs to re-run (e.g. streaming:0 blocking:minimal).",
    )
    args = parser.parse_args()
    asyncio.run(run_benchmark(args.only))


if __name__ == "__main__":
    main()
