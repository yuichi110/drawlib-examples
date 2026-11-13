# Copyright (c) 2026 Yuichi Ito (yuichi@yuichi.com)
#
# This software is licensed under the Apache License, Version 2.0.
# For more information, please visit: https://github.com/yuichi110/drawlib
#
# This software is provided "as is", without warranty of any kind,
# express or implied, including but not limited to the warranties of
# merchantability, fitness for a particular purpose and noninfringement.

"""Google AI Studio (`google-genai` SDK) Blocking & Streaming invocation patterns (`asyncio`).

Provides:
- `create_client()`: Initializes `genai.Client(api_key=GEMINI_KEY)` from `.env` or environment.
- `resolve_thinking_config()`: Maps 6 `thinking` levels (`0`, `minimal`, `low`, `medium`, `high`, `default`)
  into `types.ThinkingConfig`.
- `generate_text()`: Blocking unary generation via `client.aio.models.generate_content`.
- `stream_text()`: Progressive streaming generation via `client.aio.models.generate_content_stream`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import aclosing
import os
from pathlib import Path
from typing import Any, Literal

from google import genai
from google.genai import types

from gemini_evaluation.tracer import ExecutionTracer


def _load_dotenv() -> None:
    """Load key=value pairs from workspace `.env` into `os.environ` if not already set."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


_load_dotenv()

GEMINI_KEY: str = os.environ.get("GEMINI_KEY") or os.environ.get("GEMINI_API_KEY", "")
MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")

ThinkingOption = (
    Literal[
        0,
        1,
        2,
        3,
        4,
        "0",
        "1",
        "2",
        "3",
        "4",
        "minimal",
        "low",
        "medium",
        "high",
        "default",
    ]
    | None
)


def create_client(api_key: str | None = None) -> genai.Client:
    """Create a Google AI Studio `genai.Client` using `GEMINI_KEY` from `.env` or environment."""
    resolved_key = api_key or GEMINI_KEY
    if not resolved_key:
        raise RuntimeError(
            "GEMINI_KEY is not set. Add GEMINI_KEY=<your-api-key> to .env or environment."
        )
    return genai.Client(api_key=resolved_key)


def _extract_finish_reason(resp: types.GenerateContentResponse) -> str:
    """Extract the first candidate's `finish_reason` name from a Gemini response."""
    for cand in resp.candidates or []:
        if cand.finish_reason:
            return str(
                cand.finish_reason.name
                if hasattr(cand.finish_reason, "name")
                else cand.finish_reason
            )
    return "NONE"


def _extract_usage_counts(
    resp: types.GenerateContentResponse | None,
) -> tuple[int | None, int | None, int | None, int | None]:
    """Extract `(prompt_tok, cached_tok, thoughts_tok, out_tok)` from `usage_metadata`."""
    if resp is None or resp.usage_metadata is None:
        return None, None, None, None
    um = resp.usage_metadata
    return (
        getattr(um, "prompt_token_count", None),
        getattr(um, "cached_content_token_count", None),
        getattr(um, "thoughts_token_count", None),
        getattr(um, "candidates_token_count", None),
    )


def _build_gemini_contents(
    prompt: str,
    history: Sequence[types.Content] | None = None,
) -> tuple[str | list[types.Content], int | None, int | None]:
    """Combine conversation `history` (if provided) with the latest user `prompt`."""
    if history is None:
        return prompt, None, None
    contents_list: list[types.Content] = [
        *history,
        types.Content(role="user", parts=[types.Part.from_text(text=prompt)]),
    ]
    total_chars = 0
    for item in contents_list:
        for part in item.parts or []:
            if part.text:
                total_chars += len(part.text)
    return contents_list, len(contents_list), total_chars


def resolve_thinking_config(
    thinking: ThinkingOption = None,
    base_config: types.GenerateContentConfig | None = None,
) -> tuple[str, types.GenerateContentConfig | None]:
    """Normalize `thinking` option into `(label, GenerateContentConfig)`.

    Mapping:
        - `0` / `"0"`: `ThinkingConfig(thinking_budget=0)` -> `"0"`
        - `1` / `"1"` / `"minimal"`: `ThinkingConfig(thinking_budget=256)` -> `"minimal"`
        - `2` / `"2"` / `"low"`: `ThinkingConfig(thinking_level=LOW)` -> `"low"`
        - `3` / `"3"` / `"medium"`: `ThinkingConfig(thinking_level=MEDIUM)` -> `"medium"`
        - `4` / `"4"` / `"high"`: `ThinkingConfig(thinking_level=HIGH)` -> `"high"`
        - `None` / `"default"`: Server default thinking -> `"default"`
    """
    t_cfg: types.ThinkingConfig | None
    if thinking is None or (isinstance(thinking, str) and thinking.strip().lower() == "default"):
        label = "default"
        t_cfg = None
    elif thinking == 0 or (isinstance(thinking, str) and thinking.strip() == "0"):
        label = "0"
        t_cfg = types.ThinkingConfig(thinking_budget=0)
    elif thinking == 1 or (isinstance(thinking, str) and thinking.strip().lower() in {"1", "minimal"}):
        label = "minimal"
        t_cfg = types.ThinkingConfig(thinking_budget=256)
    elif thinking == 2 or (isinstance(thinking, str) and thinking.strip().lower() in {"2", "low"}):
        label = "low"
        t_cfg = types.ThinkingConfig(thinking_budget=4096)
    elif thinking == 3 or (isinstance(thinking, str) and thinking.strip().lower() in {"3", "medium"}):
        label = "medium"
        t_cfg = types.ThinkingConfig(thinking_level=types.ThinkingLevel.MEDIUM)
    elif thinking == 4 or (isinstance(thinking, str) and thinking.strip().lower() in {"4", "high"}):
        label = "high"
        t_cfg = types.ThinkingConfig(thinking_level=types.ThinkingLevel.HIGH)
    else:
        raise ValueError(
            f"Unsupported thinking option: {thinking!r}. "
            "Use 0 ('0'), 1 ('minimal'), 2 ('low'), 3 ('medium'), 4 ('high'), or None ('default')."
        )

    if base_config is None:
        if t_cfg is None:
            return label, None
        return label, types.GenerateContentConfig(thinking_config=t_cfg)

    merged = base_config.model_copy(deep=True)
    if t_cfg is not None:
        merged.thinking_config = t_cfg
    return label, merged


async def generate_text(
    client: genai.Client,
    prompt: str,
    *,
    history: Sequence[types.Content] | None = None,
    thinking: ThinkingOption = None,
    config: types.GenerateContentConfig | None = None,
    trace: dict[str, Any] | None = None,
) -> str:
    """Blocking unary generation via `client.aio.models.generate_content`.

    Waits until the entire response is generated before returning (`TTFT == Total`).
    """
    thinking_label, gen_cfg = resolve_thinking_config(thinking, config)
    tracer = ExecutionTracer(
        pattern="Blocking (generate_content)",
        mode="blocking",
        target=trace,
        thinking=thinking_label,
    )

    contents_payload, hist_msg_cnt, hist_total_chars = _build_gemini_contents(prompt, history)
    tracer.start_gemini()
    resp = await client.aio.models.generate_content(
        model=MODEL,
        contents=contents_payload,
        config=gen_cfg,
    )
    tracer.stop_clock()
    text = resp.text or ""
    prompt_tok, cached_tok, thoughts_tok, out_tok = _extract_usage_counts(resp)

    tracer.finalize(
        model=MODEL,
        prompt_sent=prompt,
        final_text=text,
        chunk_count=1,
        finish_reason=_extract_finish_reason(resp),
        thoughts_token_count=thoughts_tok,
        output_token_count=out_tok,
        prompt_token_count=prompt_tok,
        cached_content_token_count=cached_tok,
        history_message_count=hist_msg_cnt,
        history_total_chars=hist_total_chars,
    )
    return text


async def stream_text(
    client: genai.Client,
    prompt: str,
    *,
    history: Sequence[types.Content] | None = None,
    thinking: ThinkingOption = None,
    config: types.GenerateContentConfig | None = None,
    trace: dict[str, Any] | None = None,
) -> AsyncIterator[str]:
    """Progressive streaming generation via `client.aio.models.generate_content_stream`.

    Yields text chunks immediately as they arrive from Gemini after `TTFT`.
    """
    thinking_label, gen_cfg = resolve_thinking_config(thinking, config)
    tracer = ExecutionTracer(
        pattern="Streaming (generate_content_stream)",
        mode="streaming",
        target=trace,
        thinking=thinking_label,
    )

    contents_payload, hist_msg_cnt, hist_total_chars = _build_gemini_contents(prompt, history)
    chunks: list[str] = []
    chunk_count = 0
    last_finish_reason = "NONE"
    prompt_tok: int | None = None
    cached_tok: int | None = None
    thoughts_tok: int | None = None
    out_tok: int | None = None

    tracer.start_gemini()
    stream = await client.aio.models.generate_content_stream(
        model=MODEL,
        contents=contents_payload,
        config=gen_cfg,
    )
    async with aclosing(stream):
        async for chunk in stream:
            last_finish_reason = _extract_finish_reason(chunk)
            p_tok, c_tok, t_tok, o_tok = _extract_usage_counts(chunk)
            if p_tok is not None:
                prompt_tok = p_tok
            if c_tok is not None:
                cached_tok = c_tok
            if t_tok is not None:
                thoughts_tok = t_tok
            if o_tok is not None:
                out_tok = o_tok
            if chunk.text:
                chunk_count += 1
                tracer.record_chunk(chunk.text)
                chunks.append(chunk.text)
                yield chunk.text

    full_text = "".join(chunks)
    tracer.finalize(
        model=MODEL,
        prompt_sent=prompt,
        final_text=full_text,
        chunk_count=chunk_count,
        finish_reason=last_finish_reason,
        thoughts_token_count=thoughts_tok,
        output_token_count=out_tok,
        prompt_token_count=prompt_tok,
        cached_content_token_count=cached_tok,
        history_message_count=hist_msg_cnt,
        history_total_chars=hist_total_chars,
    )
