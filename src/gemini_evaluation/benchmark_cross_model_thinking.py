# Copyright (c) 2026 Yuichi Ito (yuichi@yuichi.com)
#
# This software is licensed under the Apache License, Version 2.0.
# For more information, please visit: https://github.com/yuichi110/drawlib
#
# This software is provided "as is", without warranty of any kind,
# express or implied, including but not limited to the warranties of
# merchantability, fitness for a particular purpose and noninfringement.

"""Cross-model × thinking_level latency benchmark across 5 Simple and 5 Complex queries."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
import time
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google import genai
from google.genai import types

from gemini_evaluation.llm_call import create_client
from gemini_evaluation.tracer import now_jst

DIR_PATH = Path(__file__).resolve().parent
JSONL_PATH = DIR_PATH / "cross_model_thinking_runs.jsonl"
JSON_PATH = DIR_PATH / "cross_model_thinking_log.json"
YAML_PATH = DIR_PATH / "cross_model_thinking_log.yaml"

SYSTEM_INSTRUCTION = (
    "あなたはPCメーカーの丁寧なテクニカルサポート担当者です。"
    "パソコンのトラブルで困っている顧客の質問に分かりやすく簡潔かつ正確に回答してください。"
)

MODEL_THINKING_MATRIX: list[tuple[str, list[str]]] = [
    ("gemini-3.5-flash-lite", ["budget=0", "minimal", "low", "medium", "high"]),
    ("gemini-3.8-flash", ["budget=0", "low", "medium", "high"]),
    ("gemini-4-hydrogen", ["budget=0", "low", "medium", "high", "xhigh"]),
    ("gemini-4-argon", ["budget=0", "low", "medium", "high"]),
    ("gemini-4-carbon", ["budget=0", "low", "medium", "high"]),
]

QUERIES: list[dict[str, Any]] = [
    # ─── 5 Simple Queries (S1–S5) ───
    {
        "id": "S1",
        "category": "simple",
        "title": "初回挨拶（PC起動トラブル）",
        "prompt": "こんにちは！パソコンが急に動かなくなってしまったので相談させてください。",
    },
    {
        "id": "S2",
        "category": "simple",
        "title": "お礼・復旧報告への応答",
        "prompt": "先ほどの放電手順で無事に電源ランプがつきました。丁寧にご案内いただきありがとうございます！",
    },
    {
        "id": "S3",
        "category": "simple",
        "title": "サポート窓口受付時間の確認",
        "prompt": "パソコン修理サポートの電話窓口とチャット窓口の一般的な受付時間を教えてください。",
    },
    {
        "id": "S4",
        "category": "simple",
        "title": "フリーズ時の強制終了秒数",
        "prompt": "Windowsのパソコンが完全にフリーズしてマウスも動かない場合、電源ボタンを何秒ほど長押しすれば強制終了できますか？短く教えてください。",
    },
    {
        "id": "S5",
        "category": "simple",
        "title": "型番・シリアル番号の記載場所",
        "prompt": "ノートパソコンの型番（モデル番号）とシリアル番号は、本体のどのあたりに記載されていることが多いですか？",
    },
    # ─── 5 Complex Queries (C1–C5) ───
    {
        "id": "C1",
        "category": "complex",
        "title": "修理vs買い替え3年間総費用比較",
        "prompt": (
            "動かなくなったノートPCを修理する場合と新品へ買い替える場合の3年間（36ヶ月）の総コストを比較します。"
            "【修理プラン】マザーボード交換38,000円＋SSD交換22,000円（保証外のため全額自己負担）、修理後の消費電力に伴う月平均電気代は2,400円、さらに2年目にバッテリー交換16,000円が必要です。"
            "【買い替えプラン】新型PC本体168,000円、故障PCの下取り値引き25,000円、値引き後金額に対する10%ポイント還元（1pt=1円相当として実質差し引き）、省電力CPUにより月平均電気代は1,550円、3年保証込みで追加修理費は0円です。"
            "3年間の累計実質負担額はそれぞれ何円になり、どちらが何円お得か途中の計算式も含めて教えてください。"
        ),
    },
    {
        "id": "C2",
        "category": "complex",
        "title": "1.8TB退避＋クラウド転送時間試算",
        "prompt": (
            "故障しかけているPCから合計1.8TB（1,800GB）の業務データを退避します。"
            "内訳は、動画素材1,200GB（連続大ファイル、外付けSSDへの実効書込速度300MB/秒）と、"
            "小規模な設計ファイル600GB（多数の小ファイルのため実効書込速度50MB/秒）です。"
            "さらに外付けSSDへ退避完了後、そのうち重要データ360GBを社内クラウドへ実効アップロード速度40MB/秒で転送します。"
            "（1GB=1,000MBとして計算）ローカル退避にかかる合計分数と、クラウド転送まで含めた総合計時間（何時間何分）をステップ別の計算過程とともに教えてください。"
        ),
    },
    {
        "id": "C3",
        "category": "complex",
        "title": "代替機レンタルvs当日出張修理比較",
        "prompt": (
            "業務用PCが故障し、以下の2つの復旧プランの総費用（税込換算不要・そのまま計算）を比較します。"
            "【通常引取修理＋レンタルPC】引取修理代32,000円、修理完了まで8日間かかり、最初の2日間は予備機がなく業務停止による機会損失が1日あたり18,000円発生、3日目〜8日目の6日間は代替PCレンタル代が1日あたり3,500円＋初期設定費4,000円かかります。"
            "【オンサイト当日出張修理】基本修理代32,000円＋出張技術料22,000円＋特急部品手配料12,000円がかかりますが、当日4時間で復旧するため業務停止損失は半日分の9,000円のみで済みます。"
            "それぞれの合計実質コスト（修理費＋関連費用＋機会損失）は何円になり、どちらが何円有利か内訳とともに教えてください。"
        ),
    },
    {
        "id": "C4",
        "category": "complex",
        "title": "3台PC保守・増設・クラウド2年試算",
        "prompt": (
            "オフィス用のPC 3台について2年間（24ヶ月）の保守・アップグレード総額を計算してください。"
            "(1)基本保守契約：1台あたり月額600円×3台×24ヶ月、"
            "(2)期間中に訪問修理を合計2回利用（通常1回6,900円ですが保守契約により1回あたり3,300円割引）、"
            "(3)3台すべてに16GBメモリ増設を実施（通常1台10,400円ですが3台同時申込で1台あたり600円割引）、"
            "(4)クラウドバックアップ契約（3台まとめて1年目は月額550円×12ヶ月、2年目は月額600円×12ヶ月）。"
            "(1)〜(4)それぞれの小計と2年間の総合計金額を正確に算出してください。"
        ),
    },
    {
        "id": "C5",
        "category": "complex",
        "title": "RAID5 NAS 12TB再構築時間試算",
        "prompt": (
            "4台の4TB HDDで構成されたRAID 5のNAS（実効容量は (N-1)×4TB）において、現在使用率が75%です。"
            "1台のHDDが故障したため新品の4TB HDDへ交換しリビルド（再構築）を行います。"
            "リビルドでは全ドライブの総容量分（4TB×3台＝12TB、1TB=1,000GB、1GB=1,000MB）を読み書きする必要があり、"
            "昼間の業務時間帯（最初の5時間）は帯域制限により実効処理速度が100MB/秒に制限され、"
            "夜間の非業務時間帯（5時間経過後以降）は実効処理速度が250MB/秒に上がります。"
            "現在の保存データ量（TB）と、リビルド完了までにかかる合計時間（何時間何分）を計算過程とともに教えてください。"
        ),
    },
]


async def run_one_streaming_call(
    client: genai.Client,
    model_name: str,
    thinking_level: str,
    query: dict[str, Any],
) -> dict[str, Any]:
    """Run one streaming call for `(model_name, thinking_level, query)` with retry."""
    if thinking_level == "budget=0":
        thinking_cfg = types.ThinkingConfig(thinking_budget=0)
    else:
        thinking_cfg = types.ThinkingConfig(thinking_level=thinking_level)  # type: ignore[arg-type]

    cfg = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        thinking_config=thinking_cfg,
    )
    for attempt in range(4):
        try:
            t0 = time.perf_counter()
            ttft_ms: float | None = None
            text_chunks: list[str] = []
            last_usage = None

            stream = await client.aio.models.generate_content_stream(
                model=model_name,
                contents=query["prompt"],
                config=cfg,
            )
            async for chunk in stream:
                now_ms = (time.perf_counter() - t0) * 1000.0
                if chunk.usage_metadata is not None:
                    last_usage = chunk.usage_metadata
                c_text = chunk.text or ""
                if c_text:
                    if ttft_ms is None:
                        ttft_ms = now_ms
                    text_chunks.append(c_text)

            total_ms = (time.perf_counter() - t0) * 1000.0
            if ttft_ms is None:
                ttft_ms = total_ms
            full_text = "".join(text_chunks)
            prompt_tok = int(getattr(last_usage, "prompt_token_count", 0) or 0) if last_usage else 0
            thoughts_tok = int(getattr(last_usage, "thoughts_token_count", 0) or 0) if last_usage else 0
            out_tok = int(getattr(last_usage, "candidates_token_count", 0) or 0) if last_usage else 0

            return {
                "model": model_name,
                "thinking_level": thinking_level,
                "query_id": query["id"],
                "category": query["category"],
                "query_title": query["title"],
                "status": "OK",
                "ttft_ms": round(ttft_ms, 1),
                "total_ms": round(total_ms, 1),
                "prompt_tokens": prompt_tok,
                "thoughts_tokens": thoughts_tok,
                "output_tokens": out_tok,
                "chars": len(full_text),
            }
        except Exception as e:
            err_str = str(e)
            if "400" in err_str or "INVALID_ARGUMENT" in err_str:
                return {
                    "model": model_name,
                    "thinking_level": thinking_level,
                    "query_id": query["id"],
                    "category": query["category"],
                    "query_title": query["title"],
                    "status": "UNSUPPORTED_400",
                    "error": err_str,
                    "ttft_ms": 0.0,
                    "total_ms": 0.0,
                    "prompt_tokens": 0,
                    "thoughts_tokens": 0,
                    "output_tokens": 0,
                    "chars": 0,
                }
            if attempt == 3:
                raise
            wait_s = 2.0 * (attempt + 1)
            print(f"  [Retry {attempt + 1}] {model_name} {thinking_level} {query['id']}: {e}", flush=True)
            await asyncio.sleep(wait_s)
    raise RuntimeError("Unreachable")


async def main() -> None:
    """Execute the 22 (model × thinking_level/budget=0) × 10 queries = 220 streaming calls."""
    started_at = now_jst()
    client = create_client()
    sem = asyncio.Semaphore(15)

    existing_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    if JSONL_PATH.exists():
        for line in JSONL_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if "status" not in row:
                    row["status"] = "OK"
                existing_map[(row["model"], row["thinking_level"], row["query_id"])] = row

    tasks = []
    for model_name, levels in MODEL_THINKING_MATRIX:
        for lvl in levels:
            for q in QUERIES:
                key = (model_name, lvl, q["id"])
                if key in existing_map:
                    async def _cached(r: dict[str, Any] = existing_map[key]) -> dict[str, Any]:
                        return r
                    tasks.append(_cached())
                else:
                    async def _job(m: str = model_name, l: str = lvl, q_item: dict[str, Any] = q) -> dict[str, Any]:
                        async with sem:
                            res = await run_one_streaming_call(client, m, l, q_item)
                            status = res.get("status", "OK")
                            if status != "OK":
                                print(
                                    f"[Unsupported] {m:21s} | {l:8s} | {q_item['id']} ({q_item['category']:7s}) -> {status}",
                                    flush=True,
                                )
                            else:
                                print(
                                    f"[Done] {m:21s} | {l:8s} | {q_item['id']} ({q_item['category']:7s}) -> "
                                    f"TTFT={res['ttft_ms']:7.1f}ms, Total={res['total_ms']:7.1f}ms, "
                                    f"ThTok={res['thoughts_tokens']:4d}, OutTok={res['output_tokens']:4d}",
                                    flush=True,
                                )
                            return res

                    tasks.append(_job())

    print(f"Running benchmark across {len(tasks)} total combinations ({len(existing_map)} cached)...")
    results = list(await asyncio.gather(*tasks))
    completed_at = now_jst()

    # Aggregate summary per (model, thinking_level, category)
    aggregated: list[dict[str, Any]] = []
    for model_name, levels in MODEL_THINKING_MATRIX:
        for lvl in levels:
            cell_rows = [r for r in results if r["model"] == model_name and r["thinking_level"] == lvl]
            s_rows = [r for r in cell_rows if r["category"] == "simple"]
            c_rows = [r for r in cell_rows if r["category"] == "complex"]
            is_unsupported = bool(cell_rows) and all(r.get("status") == "UNSUPPORTED_400" for r in cell_rows)

            def _avg(rows: list[dict[str, Any]], key: str) -> float:
                return round(sum(float(r[key]) for r in rows) / len(rows), 1) if rows else 0.0

            aggregated.append(
                {
                    "model": model_name,
                    "thinking_level": lvl,
                    "status": "UNSUPPORTED_400" if is_unsupported else "OK",
                    "simple_ttft_avg_ms": _avg(s_rows, "ttft_ms"),
                    "simple_total_avg_ms": _avg(s_rows, "total_ms"),
                    "simple_thoughts_avg": _avg(s_rows, "thoughts_tokens"),
                    "simple_output_avg": _avg(s_rows, "output_tokens"),
                    "complex_ttft_avg_ms": _avg(c_rows, "ttft_ms"),
                    "complex_total_avg_ms": _avg(c_rows, "total_ms"),
                    "complex_thoughts_avg": _avg(c_rows, "thoughts_tokens"),
                    "complex_output_avg": _avg(c_rows, "output_tokens"),
                    "overall_ttft_avg_ms": _avg(cell_rows, "ttft_ms"),
                    "overall_total_avg_ms": _avg(cell_rows, "total_ms"),
                }
            )

    payload = {
        "suite_started_at": started_at,
        "suite_completed_at": completed_at,
        "total_runs": len(results),
        "queries": QUERIES,
        "aggregated": aggregated,
        "runs": results,
    }

    JSONL_PATH.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in results) + "\n",
        encoding="utf-8",
    )
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    YAML_PATH.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"\nSaved {len(results)} runs to {JSON_PATH} and {YAML_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
