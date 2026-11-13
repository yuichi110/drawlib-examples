# Copyright (c) 2026 Yuichi Ito (yuichi@yuichi.com)
#
# This software is licensed under the Apache License, Version 2.0.
# For more information, please visit: https://github.com/yuichi110/drawlib
#
# This software is provided "as is", without warranty of any kind,
# express or implied, including but not limited to the warranties of
# merchantability, fitness for a particular purpose and noninfringement.

"""Entry point demonstrating Google AI Studio (google-genai) call patterns with YAML execution logging."""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gemini_evaluation.llm_call import (
    MODEL,
    create_client,
    generate_text,
    stream_text,
)
from gemini_evaluation.tracer import build_execution_report, now_jst, save_yaml_report

DEFAULT_LOG_PATH = Path(__file__).resolve().parent / "execution_log.yaml"
DEFAULT_PROMPT = (
    "パソコンが突然起動しなくなり、電源ボタンを押してもランプが一瞬光って消えてしまいます。"
    "原因の切り分け手順と対処法を、5行程度で分かりやすく丁寧に教えてください。"
)


async def main() -> None:
    """Execute the Google AI Studio blocking and streaming call patterns and output YAML logs."""
    suite_started_at = now_jst()
    client = create_client()
    prompt = DEFAULT_PROMPT
    patterns_log: list[dict[str, Any]] = []

    # 1. Blocking (generate_content) × thinking=0
    trace_1: dict[str, Any] = {}
    await generate_text(client, prompt, thinking=0, trace=trace_1)
    patterns_log.append(trace_1)

    # 2. Streaming (generate_content_stream) × thinking=0
    trace_2: dict[str, Any] = {}
    async for _ in stream_text(client, prompt, thinking=0, trace=trace_2):
        pass
    patterns_log.append(trace_2)

    # 3. Blocking (generate_content) × thinking=default
    trace_3: dict[str, Any] = {}
    await generate_text(client, prompt, thinking=None, trace=trace_3)
    patterns_log.append(trace_3)

    # 4. Streaming (generate_content_stream) × thinking=default
    trace_4: dict[str, Any] = {}
    async for _ in stream_text(client, prompt, thinking=None, trace=trace_4):
        pass
    patterns_log.append(trace_4)

    suite_completed_at = now_jst()

    report = build_execution_report(
        suite_started_at=suite_started_at,
        suite_completed_at=suite_completed_at,
        model=MODEL,
        original_user_prompt=prompt,
        executions=patterns_log,
    )
    yaml_output = save_yaml_report(report, DEFAULT_LOG_PATH)
    print(yaml_output)


if __name__ == "__main__":
    asyncio.run(main())
