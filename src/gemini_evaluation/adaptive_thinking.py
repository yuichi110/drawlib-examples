# Copyright (c) 2026 Yuichi Ito (yuichi@yuichi.com)
#
# This software is licensed under the Apache License, Version 2.0.
# For more information, please visit: https://github.com/yuichi110/drawlib
#
# This software is provided "as is", without warranty of any kind,
# express or implied, including but not limited to the warranties of
# merchantability, fitness for a particular purpose and noninfringement.

"""Adaptive Thinking + Pydantic Structured Streaming pipelines for Google AI Studio (`google-genai`).

Implements and instruments 3 adaptive routing architectures alongside fixed baselines:
- Pattern A (`stream_adaptive_pydantic_integrated`):
    Minimal 2-field Pydantic schema `{thinking: bool, response: str}` with `pydantic_core.from_json`
    incremental partial parsing (`allow_partial="trailing-strings"`).
    - `thinking == False`: Single API call streams `response` deltas immediately.
    - `thinking == True`: Emits 1-sentence acknowledgment immediately while launching Stage-2
      `thinking="low"` plain-text stream in parallel, chaining seamlessly.
- Pattern B (`stream_adaptive_pydantic_router`):
    Separate 1-field Pydantic router `{thinking: bool}` (`generate_content`) followed by
    standard plain-text `generate_content_stream` (`thinking=0` or `thinking="low"`).
- Pattern C (`stream_adaptive_tag_prefix`):
    Non-JSON plain-text `[DIRECT]` / `[THINK]` prefix self-routing stream + Stage-2 chaining.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from contextlib import aclosing
import time
from typing import Any, Literal

from google import genai
from google.genai import types
from pydantic import BaseModel
from pydantic_core import from_json

from gemini_evaluation.llm_call import (
    MODEL,
    ThinkingOption,
    _build_gemini_contents,
    _extract_finish_reason,
    _extract_usage_counts,
    resolve_thinking_config,
)
from gemini_evaluation.tracer import ExecutionTracer, elapsed_ms


class ThinkingDecision(BaseModel):
    """1-field Pydantic router schema for Pattern B."""

    thinking: bool


class AdaptiveStreamResponse(BaseModel):
    """Minimal 2-field Pydantic streaming schema (`{thinking: bool, response: str}`) for Pattern A."""

    thinking: bool
    response: str


class RichStreamResponse(BaseModel):
    """6-field richer Pydantic schema used to benchmark schema-complexity TTFT overhead."""

    thinking: bool
    category: Literal["greeting", "procedure", "simulation", "security", "other"]
    urgency: Literal["low", "normal", "high"]
    needs_human_escalation: bool
    response: str
    suggested_followups: list[str]


ADAPTIVE_STAGE1_JSON_INSTRUCTION = (
    "あなたはPCメーカーの丁寧なテクニカルサポートAIアシスタントです。\n"
    "ユーザーの入力内容に応じて、JSON の `thinking` と `response` を以下のルールで出力してください。\n"
    "1. 挨拶・お礼・窓口時間確認・定型トラブル対処案内（放電手順、セーフモード起動、コマンド修復など）のように、"
    "複数条件の算数計算や損益・時間比較を伴わない質問の場合は `thinking: false` とし、"
    "`response` に丁寧で分かりやすい回答全文をそのまま出力してください。\n"
    "2. 修理と新品買い替えの複数年総コスト比較、大容量データ退避・転送の所要時間試算、引取修理と出張修理の機会損失比較など、"
    "正確な数値計算や多段階の条件比較が必要な質問の場合は `thinking: true` とし、"
    "`response` には「ご質問ありがとうございます。ご提示いただいた条件を整理して詳しく試算いたします。」のような"
    "1文（45〜70文字程度）の受付メッセージのみを出力して直ちに終了してください（計算本文は書かないでください）。"
)

ADAPTIVE_STAGE2_CONTINUATION_INSTRUCTION = (
    "あなたはPCメーカーの丁寧なテクニカルサポートAIアシスタントです。\n"
    "ユーザーには既に冒頭の挨拶と「条件を整理して詳しく試算いたします」という受付の1文をお伝え済みです。\n"
    "冒頭の挨拶は繰り返さず、直ちに本題の計算ステップ・比較内訳・結論・注意点を分かりやすく丁寧に回答してください。"
)

ROUTER_ONLY_INSTRUCTION = (
    "ユーザーの質問に対して、複数条件の数値計算・コスト比較試算・多段階シミュレーションが必要な場合は `thinking: true`、"
    "挨拶・相槌・定型トラブル対処案内など通常の回答で十分な場合は `thinking: false` を返してください。"
)

ADAPTIVE_STAGE1_TAG_INSTRUCTION = (
    "あなたはPCメーカーの丁寧なテクニカルサポートAIアシスタントです。\n"
    "出力の先頭に必ず `[DIRECT]` または `[THINK]` のいずれか一方のタグを出力してください。\n"
    "1. 挨拶・お礼・定型トラブル対処案内の場合は `[DIRECT]` に続けて、丁寧な回答全文を出力してください。\n"
    "2. 複数条件の数値計算・修理買い替え比較・所要時間試算が必要な場合は `[THINK]` に続けて、"
    "「ご質問ありがとうございます。ご提示いただいた条件を整理して詳しく試算いたします。」のような"
    "1文（45〜70文字程度）の受付メッセージのみを出力して直ちに終了してください。"
)


def parse_partial_json_dict(raw_buf: str) -> dict[str, Any] | None:
    """Parse incomplete streaming JSON safely via `pydantic_core.from_json`."""
    if not raw_buf:
        return None
    try:
        parsed = from_json(raw_buf.encode("utf-8"), allow_partial="trailing-strings")
        return parsed if isinstance(parsed, dict) else None
    except ValueError:
        return None


async def stream_adaptive_pydantic_integrated(
    client: genai.Client,
    prompt: str,
    *,
    history: Sequence[types.Content] | None = None,
    fast_thinking: ThinkingOption = "low",
    deep_thinking: ThinkingOption = "high",
    schema_cls: type[BaseModel] = AdaptiveStreamResponse,
    stage2_system_instruction: str | None = None,
    trace: dict[str, Any] | None = None,
) -> AsyncIterator[str]:
    """Pattern A: Minimal 2-field Pydantic (`{thinking: bool, response: str}`) + incremental partial JSON stream.

    - If `thinking == False`: Completes in 1 Gemini API call (`fast_thinking`), streaming `response` deltas immediately.
    - If `thinking == True`: Immediately spawns Stage-2 (`deep_thinking`) plain-text stream in background,
      emits Stage-1's 1-sentence acknowledgment for fast TTFT, and seamlessly chains Stage-2.
    """
    fast_label, stage1_cfg = resolve_thinking_config(
        fast_thinking,
        types.GenerateContentConfig(
            system_instruction=ADAPTIVE_STAGE1_JSON_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=schema_cls,
            temperature=0.2,
        ),
    )
    s2_sys = stage2_system_instruction or ADAPTIVE_STAGE2_CONTINUATION_INSTRUCTION
    deep_label, deep_cfg = resolve_thinking_config(
        deep_thinking,
        types.GenerateContentConfig(
            system_instruction=s2_sys,
            temperature=0.2,
        ),
    )
    tracer = ExecutionTracer(
        pattern=f"Pattern A: Pydantic Integrated ({{thinking, response}} -> {fast_label} or {deep_label})",
        mode="streaming",
        target=trace,
        thinking=f"adaptive({fast_label}->{deep_label})",
    )

    contents_payload, hist_msg_cnt, hist_total_chars = _build_gemini_contents(prompt, history)
    if stage2_system_instruction is not None:
        s2_prompt = (
            f"{prompt}\n"
            "（注：冒頭の挨拶と受付の1文は表示済みのため、挨拶を繰り返さず直ちに本題の計算ステップと結論から回答してください。）"
        )
        stage2_contents, _, _ = _build_gemini_contents(s2_prompt, history)
    else:
        stage2_contents = contents_payload

    decided_thinking: bool | None = None
    flag_decided_ms: float | None = None
    stage2_launched_ms: float | None = None
    stage2_first_chunk_ms: float | None = None
    gemini_calls = 1
    total_gem_chunks = 0
    last_finish_reason = "STOP"
    s1_prompt_tok = 0
    s1_cached_tok = 0
    s1_thoughts_tok = 0
    s1_out_tok = 0
    s2_prompt_tok = 0
    s2_cached_tok = 0
    s2_thoughts_tok = 0
    s2_out_tok = 0
    emitted_chunks: list[str] = []

    stage2_queue: asyncio.Queue[str | BaseException | None] = asyncio.Queue()
    stage2_task: asyncio.Task[None] | None = None

    async def _produce_stage2() -> None:
        nonlocal s2_prompt_tok, s2_cached_tok, s2_thoughts_tok, s2_out_tok, stage2_first_chunk_ms, last_finish_reason
        try:
            st2 = await client.aio.models.generate_content_stream(
                model=MODEL,
                contents=stage2_contents,
                config=deep_cfg,
            )
            async with aclosing(st2):
                async for ch2 in st2:
                    last_finish_reason = _extract_finish_reason(ch2)
                    p_t, c_t, th_t, o_t = _extract_usage_counts(ch2)
                    if p_t is not None:
                        s2_prompt_tok = p_t
                    if c_t is not None:
                        s2_cached_tok = c_t
                    if th_t is not None:
                        s2_thoughts_tok = th_t
                    if o_t is not None:
                        s2_out_tok = o_t
                    if ch2.text:
                        if stage2_first_chunk_ms is None:
                            stage2_first_chunk_ms = tracer.rel_ms()
                        await stage2_queue.put(ch2.text)
            await stage2_queue.put(None)
        except BaseException as exc2:
            await stage2_queue.put(exc2)

    tracer.start_gemini()
    json_buf = ""
    emitted_resp_len = 0

    try:
        st1 = await client.aio.models.generate_content_stream(
            model=MODEL,
            contents=contents_payload,
            config=stage1_cfg,
        )
        async with aclosing(st1):
            async for ch1 in st1:
                last_finish_reason = _extract_finish_reason(ch1)
                p_t, c_t, th_t, o_t = _extract_usage_counts(ch1)
                if p_t is not None:
                    s1_prompt_tok = p_t
                if c_t is not None:
                    s1_cached_tok = c_t
                if th_t is not None:
                    s1_thoughts_tok = th_t
                if o_t is not None:
                    s1_out_tok = o_t
                if not ch1.text:
                    continue

                json_buf += ch1.text
                partial = parse_partial_json_dict(json_buf)
                if partial is None:
                    continue

                if decided_thinking is None and isinstance(partial.get("thinking"), bool):
                    decided_thinking = partial["thinking"]
                    flag_decided_ms = tracer.rel_ms()
                    if decided_thinking:
                        gemini_calls = 2
                        stage2_launched_ms = flag_decided_ms
                        stage2_task = asyncio.create_task(_produce_stage2())

                resp_so_far = partial.get("response")
                if isinstance(resp_so_far, str) and len(resp_so_far) > emitted_resp_len:
                    delta = resp_so_far[emitted_resp_len:]
                    emitted_resp_len = len(resp_so_far)
                    total_gem_chunks += 1
                    tracer.record_chunk(delta)
                    emitted_chunks.append(delta)
                    yield delta

        final_s1_obj = schema_cls.model_validate_json(json_buf)
        final_s1_resp = str(getattr(final_s1_obj, "response", ""))
        if len(final_s1_resp) > emitted_resp_len:
            rem = final_s1_resp[emitted_resp_len:]
            emitted_resp_len = len(final_s1_resp)
            total_gem_chunks += 1
            tracer.record_chunk(rem)
            emitted_chunks.append(rem)
            yield rem

        if decided_thinking and stage2_task is not None:
            sep = "\n\n"
            tracer.record_chunk(sep)
            emitted_chunks.append(sep)
            yield sep

            while True:
                item = await stage2_queue.get()
                if item is None:
                    break
                if isinstance(item, BaseException):
                    raise item
                total_gem_chunks += 1
                tracer.record_chunk(item)
                emitted_chunks.append(item)
                yield item
            await stage2_task
    finally:
        if stage2_task is not None and not stage2_task.done():
            stage2_task.cancel()
            await asyncio.gather(stage2_task, return_exceptions=True)

    full_text = "".join(emitted_chunks)
    res_dict = tracer.finalize(
        model=MODEL,
        prompt_sent=prompt,
        final_text=full_text,
        chunk_count=total_gem_chunks,
        finish_reason=last_finish_reason,
        thoughts_token_count=s1_thoughts_tok + s2_thoughts_tok,
        output_token_count=s1_out_tok + s2_out_tok,
        prompt_token_count=s1_prompt_tok,
        cached_content_token_count=max(s1_cached_tok, s2_cached_tok),
        history_message_count=hist_msg_cnt,
        history_total_chars=hist_total_chars,
    )
    adaptive_info = {
        "architecture": "A_pydantic_integrated",
        "schema_name": schema_cls.__name__,
        "thinking_triggered": bool(decided_thinking),
        "flag_decided_ms": flag_decided_ms,
        "stage2_launched_ms": stage2_launched_ms,
        "stage2_first_chunk_ms": stage2_first_chunk_ms,
        "gemini_call_count": gemini_calls,
        "stage1_prompt_tokens": s1_prompt_tok,
        "stage1_cached_tokens": s1_cached_tok,
        "stage1_thoughts_tokens": s1_thoughts_tok,
        "stage1_output_tokens": s1_out_tok,
        "stage2_prompt_tokens": s2_prompt_tok,
        "stage2_cached_tokens": s2_cached_tok,
        "stage2_thoughts_tokens": s2_thoughts_tok,
        "stage2_output_tokens": s2_out_tok,
        "total_billed_prompt_tokens": s1_prompt_tok + s2_prompt_tok,
    }
    res_dict["adaptive"] = adaptive_info
    if trace is not None:
        trace["adaptive"] = adaptive_info


async def stream_adaptive_pydantic_router(
    client: genai.Client,
    prompt: str,
    *,
    history: Sequence[types.Content] | None = None,
    fast_thinking: ThinkingOption = "low",
    deep_thinking: ThinkingOption = "high",
    trace: dict[str, Any] | None = None,
) -> AsyncIterator[str]:
    """Pattern B: 1-field Pydantic router `{thinking: bool}` followed by sequential plain-text stream."""
    fast_label, router_cfg = resolve_thinking_config(
        fast_thinking,
        types.GenerateContentConfig(
            system_instruction=ROUTER_ONLY_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=ThinkingDecision,
            temperature=0.0,
        ),
    )
    deep_label, _ = resolve_thinking_config(deep_thinking)
    tracer = ExecutionTracer(
        pattern=f"Pattern B: Pydantic 1-Field Router ({{thinking}}) + Stream ({fast_label} or {deep_label})",
        mode="streaming",
        target=trace,
        thinking=f"router({fast_label}->{deep_label})",
    )

    contents_payload, hist_msg_cnt, hist_total_chars = _build_gemini_contents(prompt, history)

    tracer.start_gemini()
    router_t0 = time.perf_counter()
    router_resp = await client.aio.models.generate_content(
        model=MODEL,
        contents=contents_payload,
        config=router_cfg,
    )
    router_dur_ms = elapsed_ms(router_t0, time.perf_counter())
    flag_decided_ms = tracer.rel_ms()
    decision_obj = ThinkingDecision.model_validate_json(router_resp.text or '{"thinking": false}')
    need_thinking = decision_obj.thinking
    r_p_tok, _, r_th_tok, r_o_tok = _extract_usage_counts(router_resp)

    chosen_thinking: ThinkingOption = deep_thinking if need_thinking else fast_thinking
    _, stream_cfg = resolve_thinking_config(
        chosen_thinking,
        types.GenerateContentConfig(
            system_instruction=(
                "あなたはPCメーカーの丁寧なテクニカルサポートAIアシスタントです。"
                "ユーザーの質問に分かりやすく丁寧に回答してください。"
            ),
            temperature=0.2,
        ),
    )

    chunks: list[str] = []
    gem_chunk_cnt = 0
    last_finish_reason = "STOP"
    s2_p_tok = 0
    s2_th_tok = 0
    s2_o_tok = 0

    st = await client.aio.models.generate_content_stream(
        model=MODEL,
        contents=contents_payload,
        config=stream_cfg,
    )
    async with aclosing(st):
        async for ch in st:
            last_finish_reason = _extract_finish_reason(ch)
            p_t, _, th_t, o_t = _extract_usage_counts(ch)
            if p_t is not None:
                s2_p_tok = p_t
            if th_t is not None:
                s2_th_tok = th_t
            if o_t is not None:
                s2_o_tok = o_t
            if ch.text:
                gem_chunk_cnt += 1
                tracer.record_chunk(ch.text)
                chunks.append(ch.text)
                yield ch.text

    full_text = "".join(chunks)
    res_dict = tracer.finalize(
        model=MODEL,
        prompt_sent=prompt,
        final_text=full_text,
        chunk_count=gem_chunk_cnt,
        finish_reason=last_finish_reason,
        thoughts_token_count=int(r_th_tok or 0) + s2_th_tok,
        output_token_count=int(r_o_tok or 0) + s2_o_tok,
        prompt_token_count=int(r_p_tok or 0) + s2_p_tok,
        history_message_count=hist_msg_cnt,
        history_total_chars=hist_total_chars,
    )
    adaptive_info = {
        "architecture": "B_pydantic_router",
        "schema_name": "ThinkingDecision",
        "thinking_triggered": need_thinking,
        "router_duration_ms": router_dur_ms,
        "flag_decided_ms": flag_decided_ms,
        "gemini_call_count": 2,
        "stage1_prompt_tokens": int(r_p_tok or 0),
        "stage1_thoughts_tokens": int(r_th_tok or 0),
        "stage1_output_tokens": int(r_o_tok or 0),
        "stage2_prompt_tokens": s2_p_tok,
        "stage2_thoughts_tokens": s2_th_tok,
        "stage2_output_tokens": s2_o_tok,
    }
    res_dict["adaptive"] = adaptive_info
    if trace is not None:
        trace["adaptive"] = adaptive_info


async def stream_adaptive_tag_prefix(
    client: genai.Client,
    prompt: str,
    *,
    history: Sequence[types.Content] | None = None,
    fast_thinking: ThinkingOption = "low",
    deep_thinking: ThinkingOption = "high",
    trace: dict[str, Any] | None = None,
) -> AsyncIterator[str]:
    """Pattern C: Non-JSON `[DIRECT]` / `[THINK]` plain-text prefix self-routing stream."""
    fast_label, stage1_cfg = resolve_thinking_config(
        fast_thinking,
        types.GenerateContentConfig(
            system_instruction=ADAPTIVE_STAGE1_TAG_INSTRUCTION,
            temperature=0.2,
        ),
    )
    deep_label, deep_cfg = resolve_thinking_config(
        deep_thinking,
        types.GenerateContentConfig(
            system_instruction=ADAPTIVE_STAGE2_CONTINUATION_INSTRUCTION,
            temperature=0.2,
        ),
    )
    tracer = ExecutionTracer(
        pattern=f"Pattern C: Plain-Text Tag Prefix ([DIRECT]/[THINK] -> {fast_label} or {deep_label})",
        mode="streaming",
        target=trace,
        thinking=f"tag({fast_label}->{deep_label})",
    )

    contents_payload, hist_msg_cnt, hist_total_chars = _build_gemini_contents(prompt, history)

    decided_thinking: bool | None = None
    flag_decided_ms: float | None = None
    stage2_first_chunk_ms: float | None = None
    gemini_calls = 1
    total_gem_chunks = 0
    last_finish_reason = "STOP"
    s1_p_tok = 0
    s1_th_tok = 0
    s1_o_tok = 0
    s2_p_tok = 0
    s2_th_tok = 0
    s2_o_tok = 0
    emitted_chunks: list[str] = []

    stage2_queue: asyncio.Queue[str | BaseException | None] = asyncio.Queue()
    stage2_task: asyncio.Task[None] | None = None

    async def _produce_stage2() -> None:
        nonlocal s2_p_tok, s2_th_tok, s2_o_tok, stage2_first_chunk_ms, last_finish_reason
        try:
            st2 = await client.aio.models.generate_content_stream(
                model=MODEL,
                contents=contents_payload,
                config=deep_cfg,
            )
            async with aclosing(st2):
                async for ch2 in st2:
                    last_finish_reason = _extract_finish_reason(ch2)
                    p_t, _, th_t, o_t = _extract_usage_counts(ch2)
                    if p_t is not None:
                        s2_p_tok = p_t
                    if th_t is not None:
                        s2_th_tok = th_t
                    if o_t is not None:
                        s2_o_tok = o_t
                    if ch2.text:
                        if stage2_first_chunk_ms is None:
                            stage2_first_chunk_ms = tracer.rel_ms()
                        await stage2_queue.put(ch2.text)
            await stage2_queue.put(None)
        except BaseException as exc2:
            await stage2_queue.put(exc2)

    tracer.start_gemini()
    raw_buf = ""
    body_start_offset = 0
    emitted_body_len = 0

    try:
        st1 = await client.aio.models.generate_content_stream(
            model=MODEL,
            contents=contents_payload,
            config=stage1_cfg,
        )
        async with aclosing(st1):
            async for ch1 in st1:
                last_finish_reason = _extract_finish_reason(ch1)
                p_t, _, th_t, o_t = _extract_usage_counts(ch1)
                if p_t is not None:
                    s1_p_tok = p_t
                if th_t is not None:
                    s1_th_tok = th_t
                if o_t is not None:
                    s1_o_tok = o_t
                if not ch1.text:
                    continue

                raw_buf += ch1.text
                if decided_thinking is None:
                    stripped = raw_buf.lstrip()
                    lead_ws = len(raw_buf) - len(stripped)
                    if stripped.startswith("[THINK]"):
                        decided_thinking = True
                        flag_decided_ms = tracer.rel_ms()
                        gemini_calls = 2
                        body_start_offset = lead_ws + len("[THINK]")
                        while (
                            body_start_offset < len(raw_buf)
                            and raw_buf[body_start_offset] in " \t\r\n"
                        ):
                            body_start_offset += 1
                        stage2_task = asyncio.create_task(_produce_stage2())
                    elif stripped.startswith("[DIRECT]"):
                        decided_thinking = False
                        flag_decided_ms = tracer.rel_ms()
                        body_start_offset = lead_ws + len("[DIRECT]")
                        while (
                            body_start_offset < len(raw_buf)
                            and raw_buf[body_start_offset] in " \t\r\n"
                        ):
                            body_start_offset += 1
                    elif len(stripped) >= 12:
                        decided_thinking = False
                        flag_decided_ms = tracer.rel_ms()
                        body_start_offset = 0

                if decided_thinking is not None and len(raw_buf) > body_start_offset:
                    body_so_far = raw_buf[body_start_offset:]
                    if len(body_so_far) > emitted_body_len:
                        delta = body_so_far[emitted_body_len:]
                        emitted_body_len = len(body_so_far)
                        total_gem_chunks += 1
                        tracer.record_chunk(delta)
                        emitted_chunks.append(delta)
                        yield delta

        if decided_thinking and stage2_task is not None:
            sep = "\n\n"
            tracer.record_chunk(sep)
            emitted_chunks.append(sep)
            yield sep

            while True:
                item = await stage2_queue.get()
                if item is None:
                    break
                if isinstance(item, BaseException):
                    raise item
                total_gem_chunks += 1
                tracer.record_chunk(item)
                emitted_chunks.append(item)
                yield item
            await stage2_task
    finally:
        if stage2_task is not None and not stage2_task.done():
            stage2_task.cancel()
            await asyncio.gather(stage2_task, return_exceptions=True)

    full_text = "".join(emitted_chunks)
    res_dict = tracer.finalize(
        model=MODEL,
        prompt_sent=prompt,
        final_text=full_text,
        chunk_count=total_gem_chunks,
        finish_reason=last_finish_reason,
        thoughts_token_count=s1_th_tok + s2_th_tok,
        output_token_count=s1_o_tok + s2_o_tok,
        prompt_token_count=s1_p_tok + s2_p_tok,
        history_message_count=hist_msg_cnt,
        history_total_chars=hist_total_chars,
    )
    adaptive_info = {
        "architecture": "C_tag_prefix",
        "thinking_triggered": bool(decided_thinking),
        "flag_decided_ms": flag_decided_ms,
        "stage2_first_chunk_ms": stage2_first_chunk_ms,
        "gemini_call_count": gemini_calls,
        "stage1_prompt_tokens": s1_p_tok,
        "stage1_thoughts_tokens": s1_th_tok,
        "stage1_output_tokens": s1_o_tok,
        "stage2_prompt_tokens": s2_p_tok,
        "stage2_thoughts_tokens": s2_th_tok,
        "stage2_output_tokens": s2_o_tok,
    }
    res_dict["adaptive"] = adaptive_info
    if trace is not None:
        trace["adaptive"] = adaptive_info
