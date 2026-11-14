# Copyright (c) 2026 Yuichi Ito (yuichi@yuichi.com)
#
# This software is licensed under the Apache License, Version 2.0.
# For more information, please visit: https://github.com/yuichi110/drawlib
#
# This software is provided "as is", without warranty of any kind,
# express or implied, including but not limited to the warranties of
# merchantability, fitness for a particular purpose and noninfringement.

"""Benchmark runner for Adaptive Thinking + Pydantic Structured Streaming on Google AI Studio."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google import genai
from google.genai import types

from gemini_evaluation.adaptive_thinking import (
    AdaptiveStreamResponse,
    RichStreamResponse,
    stream_adaptive_pydantic_integrated,
    stream_adaptive_pydantic_router,
    stream_adaptive_tag_prefix,
)
from gemini_evaluation.llm_call import (
    MODEL,
    create_client,
    stream_text,
)
from gemini_evaluation.tracer import now_jst, save_yaml_report

JSONL_PATH = Path(__file__).resolve().parent / "adaptive_thinking_runs.jsonl"
YAML_PATH = Path(__file__).resolve().parent / "adaptive_thinking_log.yaml"
JSON_PATH = Path(__file__).resolve().parent / "adaptive_thinking_log.json"

BASELINE_SYS_INSTRUCTION = (
    "あなたはPCメーカーの丁寧なテクニカルサポート担当者です。"
    "パソコンのトラブルで困っている顧客の質問に分かりやすく丁寧に回答してください。"
)

PROMPTS: list[dict[str, Any]] = [
    # Tier 1: Ultra-simple greeting / acknowledgment / 1-liner (expected thinking=False)
    {
        "id": "T1_1",
        "tier": "tier1_simple",
        "tier_label": "Tier 1: 短文・挨拶",
        "expected_thinking": False,
        "title": "初回挨拶",
        "prompt": "こんにちは！パソコンが急に動かなくなってしまったので相談させてください。",
    },
    {
        "id": "T1_2",
        "tier": "tier1_simple",
        "tier_label": "Tier 1: 短文・挨拶",
        "expected_thinking": False,
        "title": "お礼・相槌",
        "prompt": "先ほどの放電手順で無事に電源ランプがつきました。丁寧にご案内いただきありがとうございます！",
    },
    {
        "id": "T1_3",
        "tier": "tier1_simple",
        "tier_label": "Tier 1: 短文・挨拶",
        "expected_thinking": False,
        "title": "修理窓口受付時間の確認",
        "prompt": "パソコン修理サポートの電話窓口とチャット窓口の一般的な受付時間を教えてください。",
    },
    # Tier 2: Standard PC troubleshooting procedures (expected thinking=False)
    {
        "id": "T2_1",
        "tier": "tier2_procedure",
        "tier_label": "Tier 2: 定型トラブル対処",
        "expected_thinking": False,
        "title": "電源が入らない時の放電手順",
        "prompt": "ノートパソコンの電源ボタンを押しても画面が真っ暗なまま起動しない場合、最初に試すべき放電とACアダプター確認の手順を教えてください。",
    },
    {
        "id": "T2_2",
        "tier": "tier2_procedure",
        "tier_label": "Tier 2: 定型トラブル対処",
        "expected_thinking": False,
        "title": "セーフモードでの起動とバックアップ",
        "prompt": "Windowsが通常起動せず自動修復画面になる場合、セーフモードで起動して外付けUSBメモリへ大事なデータを退避する手順を教えてください。",
    },
    {
        "id": "T2_3",
        "tier": "tier2_procedure",
        "tier_label": "Tier 2: 定型トラブル対処",
        "expected_thinking": False,
        "title": "システムファイル修復コマンドの実行",
        "prompt": "パソコンの動作が頻繁にフリーズする場合に、コマンドプロンプトから sfc /scannow と DISM コマンドでシステム修復を行う手順を教えてください。",
    },
    # Tier 3: Complex multi-condition math / PC repair vs replacement simulation (expected thinking=True)
    {
        "id": "T3_1",
        "tier": "tier3_complex",
        "tier_label": "Tier 3: 複雑計算・比較",
        "expected_thinking": True,
        "title": "修理vs新品買い替え3年間総コスト比較",
        "prompt": (
            "動かなくなったノートPCを修理する場合と新品へ買い替える場合の3年間（36ヶ月）の総コストを比較します。"
            "【修理プラン】マザーボード交換38,000円＋SSD交換22,000円（保証外のため全額自己負担）、修理後の消費電力に伴う月平均電気代は2,400円、さらに2年目にバッテリー交換16,000円が必要です。"
            "【買い替えプラン】新型PC本体168,000円、故障PCの下取り値引き25,000円、値引き後金額に対する10%ポイント還元（1pt=1円相当として実質差し引き）、省電力CPUにより月平均電気代は1,550円、3年保証込みで追加修理費は0円です。"
            "3年間の累計実質負担額はそれぞれ何円になり、どちらが何円お得か途中の計算式も含めて教えてください。"
        ),
    },
    {
        "id": "T3_2",
        "tier": "tier3_complex",
        "tier_label": "Tier 3: 複雑計算・比較",
        "expected_thinking": True,
        "title": "外付けSSDへのデータ退避・クラウド転送時間試算",
        "prompt": (
            "故障しかけているPCから合計1.8TB（1,800GB）の業務データを退避します。"
            "内訳は、動画素材1,200GB（連続大ファイル、外付けSSDへの実効書込速度300MB/秒）と、"
            "小規模な設計ファイル600GB（多数の小ファイルのため実効書込速度50MB/秒）です。"
            "さらに外付けSSDへ退避完了後、そのうち重要データ360GBを社内クラウドへ実効アップロード速度40MB/秒で転送します。"
            "（1GB=1,000MBとして計算）ローカル退避にかかる合計分数と、クラウド転送まで含めた総合計時間（何時間何分）をステップ別の計算過程とともに教えてください。"
        ),
    },
    {
        "id": "T3_3",
        "tier": "tier3_complex",
        "tier_label": "Tier 3: 複雑計算・比較",
        "expected_thinking": True,
        "title": "修理期間中の代替PCレンタルvs出張当日修理の損失比較",
        "prompt": (
            "業務用PCが故障し、以下の2つの復旧プランの総費用（税込換算不要・そのまま計算）を比較します。"
            "【通常引取修理＋レンタルPC】引取修理代32,000円、修理完了まで8日間かかり、最初の2日間は予備機がなく業務停止による機会損失が1日あたり18,000円発生、3日目〜8日目の6日間は代替PCレンタル代が1日あたり3,500円＋初期設定費4,000円かかります。"
            "【オンサイト当日出張修理】基本修理代32,000円＋出張技術料22,000円＋特急部品手配料12,000円がかかりますが、当日4時間で復旧するため業務停止損失は半日分の9,000円のみで済みます。"
            "それぞれの合計実質コスト（修理費＋関連費用＋機会損失）は何円になり、どちらが何円有利か内訳とともに教えてください。"
        ),
    },
]

METHODS: list[tuple[str, str]] = [
    ("base_low", "Baseline Low: 固定 thinking=low (Plain Stream)"),
    ("base_high", "Baseline High: 固定 thinking=high (Plain Stream)"),
    ("pat_a_pydantic_2f", "Pattern A: 2フィールド統合 {thinking, response} (low -> high)"),
    ("pat_b_pydantic_1f", "Pattern B: 1フィールド分離 {thinking} + Stream (low -> high)"),
    ("pat_c_tag", "Pattern C: 非JSON先頭タグ [DIRECT]/[THINK] (low -> high)"),
]


async def execute_method(
    client: genai.Client,
    method_key: str,
    prompt: str,
) -> dict[str, Any]:
    """Run one `(method_key, prompt)` execution with automatic retry on transient errors."""
    base_cfg = types.GenerateContentConfig(
        system_instruction=BASELINE_SYS_INSTRUCTION,
        temperature=0.2,
    )
    for attempt in range(1, 4):
        trace: dict[str, Any] = {}
        try:
            if method_key == "base_low":
                async for _ in stream_text(
                    client,
                    prompt,
                    thinking="low",
                    config=base_cfg,
                    trace=trace,
                ):
                    pass
                trace["adaptive"] = {
                    "architecture": "baseline_low",
                    "thinking_triggered": False,
                    "flag_decided_ms": None,
                    "gemini_call_count": 1,
                }
            elif method_key == "base_high":
                async for _ in stream_text(
                    client,
                    prompt,
                    thinking="high",
                    config=base_cfg,
                    trace=trace,
                ):
                    pass
                trace["adaptive"] = {
                    "architecture": "baseline_high",
                    "thinking_triggered": True,
                    "flag_decided_ms": None,
                    "gemini_call_count": 1,
                }
            elif method_key == "pat_a_pydantic_2f":
                async for _ in stream_adaptive_pydantic_integrated(
                    client,
                    prompt,
                    fast_thinking="low",
                    deep_thinking="high",
                    schema_cls=AdaptiveStreamResponse,
                    trace=trace,
                ):
                    pass
            elif method_key == "pat_b_pydantic_1f":
                async for _ in stream_adaptive_pydantic_router(
                    client,
                    prompt,
                    fast_thinking="low",
                    deep_thinking="high",
                    trace=trace,
                ):
                    pass
            elif method_key == "pat_c_tag":
                async for _ in stream_adaptive_tag_prefix(
                    client,
                    prompt,
                    fast_thinking="low",
                    deep_thinking="high",
                    trace=trace,
                ):
                    pass
            else:
                raise ValueError(f"Unknown method_key: {method_key}")
            trace["attempt"] = attempt
            return trace
        except Exception:  # noqa: BLE001
            if attempt < 3:
                await asyncio.sleep(1.5 * attempt)
                continue
            raise
    raise RuntimeError("Unreachable")


async def run_schema_complexity_experiment(
    client: genai.Client,
) -> list[dict[str, Any]]:
    """Measure Cold (#1) and Warm (#2, #3, #4) TTFT for Minimal 2-field vs Rich 6-field Pydantic schemas."""
    test_prompt = "ノートパソコンの電源ボタンを押しても画面が真っ暗なまま起動しない場合、最初に試すべき放電とACアダプター確認の手順を教えてください。"
    results: list[dict[str, Any]] = []

    for schema_label, schema_cls in [
        ("minimal_2field", AdaptiveStreamResponse),
        ("rich_6field", RichStreamResponse),
    ]:
        for run_idx in range(1, 5):
            trace: dict[str, Any] = {}
            async for _ in stream_adaptive_pydantic_integrated(
                client,
                test_prompt,
                fast_thinking="low",
                deep_thinking="high",
                schema_cls=schema_cls,
                trace=trace,
            ):
                pass
            ot = trace.get("overall_timing", {})
            gem = trace.get("breakdown", {}).get("gemini", {})
            ad = trace.get("adaptive", {})
            rec = {
                "schema_label": schema_label,
                "schema_class": schema_cls.__name__,
                "run_index": run_idx,
                "is_cold": run_idx == 1,
                "flag_decided_ms": ad.get("flag_decided_ms"),
                "ttft_ms": gem.get("time_to_first_chunk_ms"),
                "total_ms": ot.get("stream_completed_ms"),
                "output_chars": len(str(trace.get("final_output", {}).get("text", ""))),
            }
            results.append(rec)
            print(
                f"[SchemaExp {schema_label} #{run_idx}] "
                f"flag={rec['flag_decided_ms']:.0f}ms | ttft={rec['ttft_ms']:.0f}ms | "
                f"total={rec['total_ms']:.0f}ms",
                flush=True,
            )
    return results


def compact_run_summary(
    prompt_spec: dict[str, Any],
    method_key: str,
    method_label: str,
    trace: dict[str, Any],
) -> dict[str, Any]:
    """Extract clean scalar metrics from a full trace."""
    ot = trace.get("overall_timing", {})
    gem = trace.get("breakdown", {}).get("gemini", {})
    gem_resp = gem.get("response", {})
    fin = trace.get("final_output", {})
    ad = trace.get("adaptive", {})
    final_txt = str(fin.get("text", ""))
    trig = ad.get("thinking_triggered")
    exp = prompt_spec["expected_thinking"]

    return {
        "prompt_id": prompt_spec["id"],
        "tier": prompt_spec["tier"],
        "tier_label": prompt_spec["tier_label"],
        "title": prompt_spec["title"],
        "expected_thinking": exp,
        "method_key": method_key,
        "method_label": method_label,
        "status": trace.get("status", "UNKNOWN"),
        "thinking_triggered": trig,
        "routing_correct": (trig == exp) if method_key.startswith("pat_") else None,
        "flag_decided_ms": ad.get("flag_decided_ms"),
        "stage2_first_chunk_ms": ad.get("stage2_first_chunk_ms"),
        "gemini_calls": ad.get("gemini_call_count"),
        "ttft_ms": ot.get("time_to_first_token_ms"),
        "total_ms": ot.get("stream_completed_ms"),
        "prompt_tokens": gem_resp.get("prompt_token_count"),
        "thoughts_tokens": gem_resp.get("thoughts_token_count"),
        "stage1_thoughts_tokens": ad.get("stage1_thoughts_tokens"),
        "stage2_thoughts_tokens": ad.get("stage2_thoughts_tokens"),
        "output_tokens": gem_resp.get("output_token_count"),
        "output_chars": len(final_txt),
    }


async def main() -> None:
    """Run 9-Prompt × 5-Method Adaptive Thinking Benchmark (gemini-3.8-flash low + high)."""
    suite_started_at = now_jst()

    existing_schema_exp: list[dict[str, Any]] = []
    if JSON_PATH.is_file():
        try:
            old_data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
            existing_schema_exp = list(old_data.get("schema_complexity_experiment", []))
        except Exception:  # noqa: BLE001
            existing_schema_exp = []

    if JSONL_PATH.is_file():
        JSONL_PATH.unlink()

    client = create_client()

    if existing_schema_exp:
        print("=== Reusing existing Schema Cold/Warm Experiment & warming up schemas ===", flush=True)
        schema_exp_results = existing_schema_exp
        warmup_a: dict[str, Any] = {}
        async for _ in stream_adaptive_pydantic_integrated(
            client, "こんにちは！", fast_thinking="low", deep_thinking="high", trace=warmup_a
        ):
            pass
    else:
        print("=== Phase 1: Schema Cold vs Warm & Complexity Experiment ===", flush=True)
        schema_exp_results = await run_schema_complexity_experiment(client)

    # Warm up Pattern B's 1-field schema once as well so all 5 methods are warm-cached
    warmup_trace: dict[str, Any] = {}
    async for _ in stream_adaptive_pydantic_router(
        client, "こんにちは！", fast_thinking="low", deep_thinking="high", trace=warmup_trace
    ):
        pass

    print("\n=== Phase 2: 9 Prompts × 5 Methods Matrix (45 Runs: low -> high) ===", flush=True)
    sem = asyncio.Semaphore(15)

    async def _run_adaptive_cell(
        p_spec: dict[str, Any], m_key: str, m_label: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        async with sem:
            trace = await execute_method(client, m_key, p_spec["prompt"])
            comp = compact_run_summary(p_spec, m_key, m_label, trace)
            ttft_s = f"{comp['ttft_ms']:.0f}" if comp["ttft_ms"] is not None else "ERR"
            tot_s = f"{comp['total_ms']:.0f}" if comp["total_ms"] is not None else "ERR"
            print(
                f"[{p_spec['id']} | {m_key:<17}] "
                f"trig={str(comp['thinking_triggered']):<5} (exp={str(p_spec['expected_thinking']):<5}) | "
                f"calls={comp['gemini_calls']} | ttft={ttft_s:>5}ms | total={tot_s:>5}ms | "
                f"th={comp['thoughts_tokens']} | chars={comp['output_chars']}",
                flush=True,
            )
            jsonl_rec = {
                "prompt_id": p_spec["id"],
                "tier": p_spec["tier"],
                "expected_thinking": p_spec["expected_thinking"],
                "method_key": m_key,
                "summary": comp,
                "trace": trace,
            }
            return comp, jsonl_rec

    cell_results = await asyncio.gather(
        *(
            _run_adaptive_cell(p_spec, m_key, m_label)
            for p_spec in PROMPTS
            for m_key, m_label in METHODS
        )
    )
    summaries: list[dict[str, Any]] = []
    with JSONL_PATH.open("w", encoding="utf-8") as fp:
        for comp, jsonl_rec in cell_results:
            summaries.append(comp)
            fp.write(json.dumps(jsonl_rec, ensure_ascii=False) + "\n")

    report = {
        "benchmark_metadata": {
            "suite_started_at": suite_started_at,
            "suite_completed_at": now_jst(),
            "api_provider": "Google AI Studio (google-genai)",
            "model": MODEL,
            "stage1_thinking_level": "low",
            "stage2_thinking_level": "high",
        },
        "schema_complexity_experiment": schema_exp_results,
        "prompts": PROMPTS,
        "methods": [{"key": k, "label": lbl} for k, lbl in METHODS],
        "runs": summaries,
    }
    save_yaml_report(report, YAML_PATH)
    JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved {YAML_PATH}, {JSON_PATH}, and {JSONL_PATH} successfully!", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
