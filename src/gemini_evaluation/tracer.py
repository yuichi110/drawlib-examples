# Copyright (c) 2026 Yuichi Ito (yuichi@yuichi.com)
#
# This software is licensed under the Apache License, Version 2.0.
# For more information, please visit: https://github.com/yuichi110/drawlib
#
# This software is provided "as is", without warranty of any kind,
# express or implied, including but not limited to the warranties of
# merchantability, fitness for a particular purpose and noninfringement.

"""Execution latency/timestamp tracer and YAML/JSONL exporter for Google AI Studio Gemini calls."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import time
from typing import Any

import yaml

_JST = timezone(timedelta(hours=9), name="JST")


def now_jst() -> str:
    """Return current time as a human-readable JST timestamp (`YYYY-MM-DD HH:MM:SS.fff JST`)."""
    return datetime.now(_JST).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " JST"


def elapsed_ms(start_perf: float, end_perf: float) -> float:
    """Convert `time.perf_counter()` delta into milliseconds rounded to 2 decimal places."""
    return round((end_perf - start_perf) * 1000.0, 2)


class _LiteralBlockDumper(yaml.SafeDumper):
    """YAML SafeDumper that renders multi-line strings with `|` and disables `&id` aliases."""

    def ignore_aliases(self, data: Any) -> bool:
        """Disable YAML anchor/alias references (`&id001` / `*id001`) for human readability."""
        return True


def _str_representer(dumper: yaml.SafeDumper, data: str) -> yaml.ScalarNode:
    """Represent strings containing newlines using YAML literal block style (`|`)."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_LiteralBlockDumper.add_representer(str, _str_representer)


def dump_yaml(data: dict[str, Any]) -> str:
    """Serialize a dictionary into a human-friendly YAML string via PyYAML."""
    return yaml.dump(
        data,
        Dumper=_LiteralBlockDumper,
        allow_unicode=True,
        sort_keys=False,
        width=120,
    )


class ExecutionTracer:
    """Recorder for Gemini request/response timestamps, TTFT, total duration, and character trajectories.

    Measures:
        - `ttft_ms`: Time to First Token/Chunk (identical to `total_ms` when `mode == "blocking"`).
        - `total_ms`: Total generation completion time from request start (`t = 0 ms`).
        - `timeline_series.gemini`: `(t_ms, chars)` trajectory points for plotting
          `Elapsed Time (x) vs Cumulative Characters (y)`.
        - Token usage breakdown (`prompt_token_count`, `cached_content_token_count`,
          `thoughts_token_count`, `output_token_count`).
    """

    def __init__(
        self,
        pattern: str,
        mode: str,
        target: dict[str, Any] | None = None,
        *,
        thinking: str = "default",
    ) -> None:
        """Initialize tracer and mark request start time (`t = 0 ms`)."""
        self.pattern = pattern
        self.mode = mode
        self.thinking = thinking
        self._target = target

        self.req_start_ts = now_jst()
        self.req_start_perf = time.perf_counter()
        self.first_chunk_ts: str | None = None
        self.first_chunk_perf: float | None = None
        self.end_ts: str | None = None
        self.end_perf: float | None = None

        self.gemini_data: dict[str, Any] = {}
        self._ts_gemini: list[dict[str, Any]] = []
        self._cum_chars: int = 0

    def rel_ms(self, perf: float | None = None) -> float:
        """Return elapsed milliseconds from `self.req_start_perf`."""
        return elapsed_ms(self.req_start_perf, perf if perf is not None else time.perf_counter())

    def start_gemini(self) -> None:
        """Mark the start of the Gemini API request (`t = 0 ms`)."""
        self.req_start_ts = now_jst()
        self.req_start_perf = time.perf_counter()
        self._cum_chars = 0
        self._ts_gemini = [{"t_ms": 0.0, "chars": 0, "event": "start"}]

    def record_chunk(self, chunk_text: str) -> None:
        """Record arrival of a streaming text chunk from Gemini for `(t_ms, chars)` plotting."""
        if not chunk_text:
            return
        now_p = time.perf_counter()
        t_now = elapsed_ms(self.req_start_perf, now_p)
        if self.first_chunk_perf is None:
            self.first_chunk_perf = now_p
            self.first_chunk_ts = now_jst()
            # Record end of thinking/prefill plateau at (t_first_chunk, 0) before stepping up
            self._ts_gemini.append({"t_ms": t_now, "chars": 0, "event": "thinking_end"})
        self._cum_chars += len(chunk_text)
        chunk_idx = sum(1 for pt in self._ts_gemini if str(pt.get("event", "")).startswith("chunk_")) + 1
        self._ts_gemini.append(
            {
                "t_ms": t_now,
                "chars": self._cum_chars,
                "event": f"chunk_{chunk_idx}",
            }
        )

    def stop_clock(self) -> None:
        """Mark the end of the Gemini generation request."""
        if self.end_perf is None:
            self.end_perf = time.perf_counter()
            self.end_ts = now_jst()

    def finalize(
        self,
        *,
        model: str,
        prompt_sent: str,
        final_text: str,
        chunk_count: int,
        finish_reason: str,
        thoughts_token_count: int | None = None,
        output_token_count: int | None = None,
        prompt_token_count: int | None = None,
        cached_content_token_count: int | None = None,
        history_message_count: int | None = None,
        history_total_chars: int | None = None,
    ) -> dict[str, Any]:
        """Finalize Gemini request/response metadata, timings, and trajectory series."""
        self.stop_clock()
        end_perf = self.end_perf or time.perf_counter()
        end_ts = self.end_ts or now_jst()
        total_ms = elapsed_ms(self.req_start_perf, end_perf)

        if self.mode == "blocking" or self.first_chunk_perf is None:
            first_ts = end_ts
            ttft_ms = total_ms
            self._ts_gemini.append({"t_ms": total_ms, "chars": 0, "event": "blocking_wait_end"})
            self._ts_gemini.append(
                {"t_ms": total_ms, "chars": len(final_text), "event": "blocking_completed"}
            )
        else:
            first_ts = self.first_chunk_ts or end_ts
            ttft_ms = elapsed_ms(self.req_start_perf, self.first_chunk_perf)

        req_info: dict[str, Any] = {
            "model": model,
            "thinking": self.thinking,
        }
        if history_message_count is not None:
            req_info["history_message_count"] = history_message_count
        if history_total_chars is not None:
            req_info["history_total_chars"] = history_total_chars
        req_info["prompt_sent"] = prompt_sent

        resp_meta: dict[str, Any] = {
            "text": final_text,
            "chars": len(final_text),
            "chunk_count": chunk_count,
            "finish_reason": finish_reason,
            "thoughts_token_count": int(thoughts_token_count or 0),
            "output_token_count": int(output_token_count or 0),
        }
        if prompt_token_count is not None:
            resp_meta["prompt_token_count"] = int(prompt_token_count)
        if cached_content_token_count is not None:
            resp_meta["cached_content_token_count"] = int(cached_content_token_count)

        self.gemini_data = {
            "started_at": self.req_start_ts,
            "first_chunk_at": first_ts,
            "completed_at": end_ts,
            "time_to_first_chunk_ms": ttft_ms,
            "ttft_ms": ttft_ms,
            "duration_ms": total_ms,
            "request": req_info,
            "response": resp_meta,
        }

        result: dict[str, Any] = {
            "pattern": self.pattern,
            "mode": self.mode,
            "thinking": self.thinking,
            "status": "SUCCESS",
            "overall_timing": {
                "started_at": self.req_start_ts,
                "first_token_at": first_ts,
                "completed_at": end_ts,
                "time_to_first_token_ms": ttft_ms,
                "stream_completed_ms": total_ms,
                "ttft_ms": ttft_ms,
                "total_ms": total_ms,
            },
            "timeline_series": {
                "gemini": self._ts_gemini,
                "client_output": self._ts_gemini,
            },
            "breakdown": {
                "gemini": self.gemini_data,
            },
            "final_output": {
                "text": final_text,
                "chars": len(final_text),
            },
        }
        if self._target is not None:
            self._target.update(result)
        return result


def build_execution_report(
    *,
    suite_started_at: str,
    suite_completed_at: str,
    model: str,
    original_user_prompt: str,
    executions: list[dict[str, Any]],
    scatter_trials: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the top-level structured report dictionary for YAML serialization."""
    summary_table = [
        {
            "pattern": p.get("pattern"),
            "mode": p.get("mode"),
            "thinking": p.get("thinking", "default"),
            "status": p.get("status"),
            "ttft_ms": p.get("overall_timing", {}).get("time_to_first_token_ms"),
            "total_ms": p.get("overall_timing", {}).get("stream_completed_ms"),
            "thoughts_token_count": p.get("breakdown", {})
            .get("gemini", {})
            .get("response", {})
            .get("thoughts_token_count"),
            "output_token_count": p.get("breakdown", {})
            .get("gemini", {})
            .get("response", {})
            .get("output_token_count"),
            "output_chars": p.get("final_output", {}).get("chars"),
        }
        for p in executions
    ]
    report: dict[str, Any] = {
        "execution_metadata": {
            "suite_started_at": suite_started_at,
            "suite_completed_at": suite_completed_at,
            "sdk": "google-genai (Google AI Studio)",
            "gemini_model": model,
            "original_user_prompt": original_user_prompt,
        },
        "summary": summary_table,
        "executions": executions,
    }
    if scatter_trials is not None:
        report["scatter_trials"] = scatter_trials
    return report


def save_yaml_report(report: dict[str, Any], output_path: Path) -> str:
    """Serialize `report` to YAML and JSON, write both to disk, and return the YAML string."""
    yaml_text = dump_yaml(report)
    output_path.write_text(yaml_text, encoding="utf-8")
    json_path = output_path.with_suffix(".json")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return yaml_text
