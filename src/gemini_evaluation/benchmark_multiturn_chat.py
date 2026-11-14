# Copyright (c) 2026 Yuichi Ito (yuichi@yuichi.com)
#
# This software is licensed under the Apache License, Version 2.0.
# For more information, please visit: https://github.com/yuichi110/drawlib
#
# This software is provided "as is", without warranty of any kind,
# express or implied, including but not limited to the warranties of
# merchantability, fitness for a particular purpose and noninfringement.

"""50-turn multi-turn Streaming latency benchmark on Google AI Studio (`gemini-3.8-flash`).

Unifies all multi-turn evaluations on Streaming (`generate_content_stream`) and compares
3 target configurations across a 50-turn PC troubleshooting conversation:
1. `streaming_low`: Fixed `gemini-3.8-flash` (`thinking_level=LOW`)
2. `streaming_high`: Fixed `gemini-3.8-flash` (`thinking_level=HIGH`)
3. `adaptive_pat_a`: Chapter 4 Adaptive Thinking Router Pattern A
   (`Stage 1: gemini-3.8-flash [low]` 2-field Pydantic `{thinking: bool, response: str}`
    -> if `thinking=True`, parallel `Stage 2: gemini-3.8-flash [high]`)

Across the 50 turns:
- 40 turns (80%) are routine troubleshooting procedures / status checks (`expected_thinking=False`).
- 10 turns (20%: Turns 5, 10, 15, 20, 25, 30, 35, 40, 45, 50 — 2 per 10-turn cohort) are
  multi-condition numerical calculations / cost-time comparisons (`expected_thinking=True`).
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
import time
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google import genai
from google.genai import types

from gemini_evaluation.adaptive_thinking import stream_adaptive_pydantic_integrated
from gemini_evaluation.llm_call import (
    MODEL,
    ThinkingOption,
    create_client,
    stream_text,
)
from gemini_evaluation.tracer import elapsed_ms, now_jst, save_yaml_report

DEFAULT_JSONL_PATH = Path(__file__).resolve().parent / "multiturn_chat_turns.jsonl"
DEFAULT_YAML_PATH = Path(__file__).resolve().parent / "multiturn_chat_log.yaml"
DEFAULT_JSON_PATH = Path(__file__).resolve().parent / "multiturn_chat_log.json"

USER_SYSTEM_INSTRUCTION = (
    "あなたは自宅や仕事で使っているノートパソコンが突然動かなくなり、困ってPCメーカーのサポート窓口にチャットで相談している顧客です。"
    "サポート担当者と順番に状況確認や復旧手順のやり取りをしています。"
    "以下のルールを厳守して、次の1回分の顧客メッセージ本文のみを出力してください。\n"
    "1. 文字数は60〜110文字程度（1〜2文）の簡潔で自然な質問・状況報告にすること（回答側より必ず短くする）。\n"
    "2. 会話を終わらせず、指定されたトピックについて具体的に質問・相談すること。\n"
    "3. マークダウン記号や見出しは使わず、自然な日本語のチャット文面のみを出力すること。"
)

AGENT_SYSTEM_INSTRUCTION = (
    "あなたはPCメーカーの丁寧で知識豊富なテクニカルサポート窓口担当者です。"
    "パソコンが動かなくなった顧客からの質問・相談に対し、以下のルールに従って回答してください。\n"
    "1. 丁寧で安心感のある挨拶や共感の一言から始めること。\n"
    "2. 顧客が安全に操作・確認できるよう、手順・注意点・判断基準・計算内訳を含めて8〜11行程度（380〜520文字前後）で"
    "詳しく丁寧に説明すること（顧客の短い質問に対して充実した回答を返すこと）。\n"
    "3. 過去の会話の流れを踏まえつつ、今回の質問に的確に答えること。"
)

# 10 Complex multi-condition calculation prompts placed at every 5th turn (2 per 10-turn cohort)
COMPLEX_CALC_PROMPTS: dict[int, str] = {
    5: (
        "バッテリー診断で設計容量60Whに対し現在の満充電容量が36Wh（60%）と出ました。"
        "停電時に消費電力45Wで作業しながら18GBの重要書類を外付けSSD（実効60MB/秒、1GB=1000MB換算）へ退避する場合、"
        "コピー完了までの所要時間（分）と完了時点のバッテリー残量（Whおよび%）を計算して間に合うか教えてください。"
    ),
    10: (
        "セーフモードで起動できたので重要データ450GBを退避したいです。"
        "外付けSSDへのコピー（実効150MB/秒、1GB=1000MB換算、ファイルシステムオーバーヘッド+20%）のあと、"
        "うち重要書類60GBをクラウドへアップロード（上り実効40Mbps、8bit=1Byte、暗号化効率80%）する場合の合計所要時間（分）を試算してください。"
    ),
    15: (
        "容量1.2TBのSSD（使用量720GB、小ファイル48万個）に対して chkdsk /r を実行したいです。"
        "セクタ走査（平均300MB/秒、1GB=1000MB換算）とファイルインデックス検証（1万個あたり15秒）に初期処理5分を加えると、"
        "完了まで合計何分かかるか内訳を計算してください。"
    ),
    20: (
        "メモリ診断でエラーが出たため交換を検討しています。"
        "①DDR5 16GB×1枚のみ購入交換（9,800円＋送料880円）、"
        "②16GB×2枚セットへ増設（18,400円送料無料、既存の正常な16GB×1枚を3,200円で売却）、"
        "③メーカー出張交換（部品14,500円＋技術料6,600円）の3案の実質負担額と有効容量1GBあたり単価を比較してください。"
    ),
    25: (
        "冷却不足でCPUが定格65W（処理速度100%）から35W（処理速度60%）に制限されています。"
        "通常1本36分かかる動画書き出し5本を①このまま制限状態で連続処理する場合と、"
        "②25分かけて冷却清掃とBIOS更新を行ってから定格速度の90%で5本処理する場合の合計所要時間（分）を比較し、どちらが何分速いか計算してください。"
    ),
    30: (
        "OS初期化で①クラウドダウンロード方式（16.8GBを実効28Mbpsで取得後に展開25分、1GB=1000MB・8bit=1Byte）と、"
        "②別PCで8GBの回復USBを作成（ダウンロード実効80Mbps＋USB書込20MB/秒＋本番インストール22分）の2方式について、"
        "完了までの合計時間（分）をそれぞれ計算してどちらが何分速いか教えてください。"
    ),
    35: (
        "診断でマザーボード交換（通常修理代58,000円＋往復送料2,200円）が必要と出ました。"
        "加入中の3年延長保証（年額4,800円×2年支払済、自己負担金は修理代の20%または上限8,000円の低い方、送料無償）を使う場合と、"
        "未加入で実費修理する場合の今回の支払額および2年分保証料込みの累計支出差額を試算してください。"
    ),
    40: (
        "SSD内の未バックアップ領域120GBについて、"
        "①専門業者の論理データ復旧（基本料19,800円＋10GBあたり3,300円、納期5営業日で業務停止損失1日6,000円）と、"
        "②クラウド履歴から手動再作成（作業28時間×時給換算2,200円＋有料補助ツール4,500円）の2案の総コスト（円）を比較し、どちらがいくら安いか計算してください。"
    ),
    45: (
        "今後3年間使う前提で、①現PCの修理継続（今回修理代42,000円、2年目にバッテリー交換16,500円、消費電力65Wで1日8時間×年300日稼働、電気代30円/kWh）と、"
        "②下取り買い替え（新品178,000円から下取り25,000円と本体10%ポイント還元を差し引き、消費電力35Wで同条件稼働）の3年間実質総費用を比較し、どちらがいくらお得か試算してください。"
    ),
    50: (
        "今後の自動バックアップ設計として、初期データ500GB＋毎週15GB増分（4週ごとにフルバックアップ500GBを2世代保持＋直近4週分の増分を保持、重複排除で全体を20%圧縮）を3年間（36ヶ月）運用する場合、"
        "①必要保存容量（GB）を算出したうえで、②外付け2TB SSD買切（19,800円）と③クラウド2TBプラン（月額1,300円×36ヶ月、初年度3ヶ月無料）の3年総額を比較してください。"
    ),
}

TURN_TOPICS: list[str] = [
    "パソコンの電源ボタンを押しても画面が真っ暗なままで動かなくなった状況を伝え、最初に何を確認すべきか聞く",
    "ACアダプターと電源ケーブルを別のコンセントに挿し直してみたが、充電ランプが点滅している状態の意味と対処法を聞く",
    "接続しているUSB機器や外付けモニターをすべて外してバッテリー放電（強制リセット）を行う具体的な手順と秒数を聞く",
    "放電後に電源長押しを試したらファンは回り始めたものの、メーカーロゴ画面で止まって進まない場合の切り分け方法を聞く",
    "停電時のバッテリー残量と外付けSSDへのデータ退避時間の計算について聞く",
    "BIOS画面で内蔵SSDが認識されているか確認する場所と、認識されていても起動しない場合に試すべき設定変更を聞く",
    "BIOSの設定を初期値（Load Setup Defaults）に戻して保存・再起動する手順と注意点を聞く",
    "再起動後に青い画面で「自動修復でPCを修復できませんでした（エラーコード 0xc0000001）」と表示された場合の対処法を聞く",
    "「詳細オプション」から「トラブルシューティング」に進み、セーフモードで起動できるか試す手順を聞く",
    "セーフモードでの450GB外付けSSD退避と60GBクラウドアップロードの合計所要時間の試算を聞く",
    "セーフモード中に外付けUSBメモリへ仕事用の重要書類フォルダをバックアップする際の注意点と安全な手順を聞く",
    "直近でインストールした更新プログラム（Windows Update）が原因かもしれない場合の確認・アンインストール手順を聞く",
    "デバイスマネージャーを開いて「！」マークが付いているグラフィックドライバーをロールバックまたは削除する手順を聞く",
    "コマンドプロンプト（管理者）からシステムファイル修復（sfc /scannow と DISM コマンド）を実行する手順と所要時間を聞く",
    "1.2TB SSDに対する chkdsk /r のセクタ走査とファイル検証の合計所要時間計算を聞く",
    "通常起動に戻したところログインできたが、数分操作すると画面が固まってマウスも動かなくなる症状の切り分けを聞く",
    "タスクマネージャーでCPU・メモリ・ディスク使用率が100%に張り付いている原因プロセスの特定方法を聞く",
    "バックグラウンドで常駐しているサードパーティ製ソフトを無効化する「クリーンブート（msconfig）」の設定手順を聞く",
    "本体の底面がかなり熱くなっておりファンが高速回転し続けているため、冷却不足（サーマルスロットリング）の確認と掃除方法を聞く",
    "メモリ交換3案（1枚交換・2枚増設＆売却・メーカー出張交換）の実質負担額と1GB単価の比較計算を聞く",
    "内蔵SSDの健康状態（S.M.A.R.T.情報や残り寿命・温度）を診断ツールで確認する際の異常値の目安を聞く",
    "イベントビューアーの「システム」ログで、フリーズ直前に記録されている重大エラー（Kernel-Power 41等）の確認手順を聞く",
    "電源プランの設定で「高速スタートアップ」を無効化するとフリーズや起動不良が改善するか、設定変更手順を聞く",
    "スリープから復帰した時だけ画面が真っ暗になる症状を防ぐためのPCI Express電源管理やスリープ設定の見直し方法を聞く",
    "サーマルスロットリング状態での動画書き出し5本と冷却清掃・BIOS更新後の処理時間の比較計算を聞く",
    "ドライバー更新後もブルースクリーン（MEMORY_MANAGEMENT）が再発したため、システムの復元ポイントへ戻す手順を聞く",
    "個人用ファイルを保持したままOSのみを再インストールする「このPCを初期状態に戻す」の手順と消えるアプリの範囲を聞く",
    "クラウドダウンロード方式とローカル再インストール方式のどちらを選んで初期化すべきか、違いと推奨条件を聞く",
    "初期化の途中で「問題が発生しました」と中断してしまう場合、別のPCで回復ドライブ（USBインストールメディア）を作成する手順を聞く",
    "クラウドダウンロード初期化と別PC回復USB作成＋インストールの合計所要時間の比較計算を聞く",
    "クリーンインストールを実行する前に、Officeライセンスや暗号化（BitLocker回復キー）を事前確認する方法を聞く",
    "BitLocker回復キーの入力画面が出てきた場合に、Microsoftアカウントから48桁のキーを探す手順を聞く",
    "OSを再インストールしてもインストール途中で止まるため、ハードウェア故障（マザーボードまたはメモリ）の可能性と診断テストを聞く",
    "メーカー標準のハードウェア自己診断機能（ePSA / Diagnostics）を起動画面から実行してエラーコードを確認する手順を聞く",
    "マザーボード交換における3年延長保証適用時と実費修理時の支払額および累計支出差額の試算を聞く",
    "購入から1年以内（メーカー標準保証期間内）の場合、無償修理の対象範囲と自然故障の判定基準について聞く",
    "延長保証（アクシデント・物損プラン）に加入しているかシリアル番号（製造番号）から確認する方法を聞く",
    "引き取り修理（ピックアップ修理）を申し込む際の梱包方法と、宅配業者が専用箱を持ってきてくれるかを聞く",
    "修理に出す前にACアダプターやマウスなどの付属品を同梱すべきか、本体のみ送るべきかのルールを聞く",
    "未バックアップ120GBの専門業者データ復旧とクラウド履歴からの手動再作成の総コスト比較計算を聞く",
    "電源が入らなくなる前に取り出せなかったデータがある場合、有償のデータ復旧サービスを併用できるか聞く",
    "修理期間中（目安7〜10営業日）に仕事が止まらないよう、代替機（レンタルPC）の貸出サービスがあるか聞く",
    "出張修理（オンサイト修理）に切り替えられる条件と、自宅にエンジニアが訪問して当日部品交換できるかを聞く",
    "もし保証対象外（水濡れや基板損傷）と判定された場合の見積もり連絡フローと、キャンセル時の診断料について聞く",
    "現PCの修理継続と下取り買い替えの3年間実質総費用（修理・バッテリー・電気代込み）の比較計算を聞く",
    "修理完了後にパソコンが返却された際、最初に確認すべき動作チェック項目と修理保証期間（再発時の保証）を聞く",
    "返却されたパソコンへ外付けUSBメモリからバックアップデータを戻す際のウイルスチェックとフォルダ配置の注意点を聞く",
    "今後また突然パソコンが動かなくなった時に備えて、外付けSSDへのシステムイメージバックアップを自動化する手順を聞く",
    "クラウドストレージ（OneDrive等）の自動同期を設定して、デスクトップや書類フォルダを常時保護する方法を聞く",
    "3年間の自動バックアップ必要容量（GB）と外付けSSD買切vsクラウド2TBプランの3年総額比較試算を聞く",
]

VARIANTS: list[str] = [
    "streaming_low",
    "streaming_high",
    "adaptive_pat_a",
]


async def generate_user_turn(
    client: genai.Client,
    turn_num: int,
    history: list[types.Content],
) -> tuple[str, float, int, int]:
    """Generate or return the simulated customer's input message for `turn_num`."""
    if turn_num in COMPLEX_CALC_PROMPTS:
        return COMPLEX_CALC_PROMPTS[turn_num], 0.0, 0, 0

    topic = TURN_TOPICS[(turn_num - 1) % len(TURN_TOPICS)]
    recent_turns = history[-6:] if len(history) > 6 else history
    recent_lines: list[str] = []
    for item in recent_turns:
        role_jp = "顧客" if item.role == "user" else "担当者"
        txt = "".join(p.text for p in (item.parts or []) if p.text)
        short_txt = txt[:120] + ("…" if len(txt) > 120 else "")
        recent_lines.append(f"{role_jp}: {short_txt}")

    context_summary = "\n".join(recent_lines) if recent_lines else "（会話開始・初回質問）"
    sim_prompt = (
        f"現在は第{turn_num}ターン目です。\n"
        f"直近のやり取り:\n{context_summary}\n\n"
        f"今回の質問テーマ: {topic}\n"
        "上記の質問テーマに沿って、担当者への自然な質問文（60〜110文字程度）を1つだけ出力してください。"
    )
    cfg = types.GenerateContentConfig(
        system_instruction=USER_SYSTEM_INSTRUCTION,
        thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
        temperature=0.4,
    )

    t0 = time.perf_counter()
    resp = await client.aio.models.generate_content(
        model=MODEL,
        contents=sim_prompt,
        config=cfg,
    )
    dur_ms = elapsed_ms(t0, time.perf_counter())
    user_text = (resp.text or "").strip().replace("\n", "")
    um = resp.usage_metadata
    p_tok = int(getattr(um, "prompt_token_count", 0) or 0) if um else 0
    o_tok = int(getattr(um, "candidates_token_count", 0) or 0) if um else 0
    return user_text, dur_ms, p_tok, o_tok


async def run_streaming_variant_with_retry(
    client: genai.Client,
    *,
    variant_key: str,
    user_prompt: str,
    history: list[types.Content],
    call_order: int,
    max_retries: int = 3,
) -> tuple[str, dict[str, Any]]:
    """Run one of (`streaming_low`, `streaming_high`, `adaptive_pat_a`) with retry."""
    last_err: Exception | None = None

    for attempt in range(1, max_retries + 1):
        trace: dict[str, Any] = {}
        try:
            chunks: list[str] = []
            if variant_key == "streaming_low":
                attempt_cfg = types.GenerateContentConfig(
                    system_instruction=AGENT_SYSTEM_INSTRUCTION,
                    temperature=round(0.2 + 0.15 * (attempt - 1), 2),
                )
                async for ch in stream_text(
                    client,
                    user_prompt,
                    history=history,
                    thinking="low",
                    config=attempt_cfg,
                    trace=trace,
                ):
                    chunks.append(ch)
            elif variant_key == "streaming_high":
                attempt_cfg = types.GenerateContentConfig(
                    system_instruction=AGENT_SYSTEM_INSTRUCTION,
                    temperature=round(0.2 + 0.15 * (attempt - 1), 2),
                )
                async for ch in stream_text(
                    client,
                    user_prompt,
                    history=history,
                    thinking="high",
                    config=attempt_cfg,
                    trace=trace,
                ):
                    chunks.append(ch)
            elif variant_key == "adaptive_pat_a":
                async for ch in stream_adaptive_pydantic_integrated(
                    client,
                    user_prompt,
                    history=history,
                    fast_thinking="low",
                    deep_thinking="high",
                    stage2_system_instruction=AGENT_SYSTEM_INSTRUCTION,
                    trace=trace,
                ):
                    chunks.append(ch)
            else:
                raise ValueError(f"Unknown variant_key: {variant_key}")

            out_text = "".join(chunks)
            trace["variant_key"] = variant_key
            trace["mode"] = "streaming"
            trace["call_order_in_turn"] = call_order
            trace["attempt"] = attempt
            return out_text, trace
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt < max_retries:
                await asyncio.sleep(1.5 * attempt)
                continue
            raise

    raise RuntimeError(f"Failed variant {variant_key}: {last_err}")


def extract_compact_variant_metrics(trace: dict[str, Any]) -> dict[str, Any]:
    """Extract compact scalar metrics from a full `ExecutionTracer` trace dict."""
    ot = trace.get("overall_timing", {})
    gem = trace.get("breakdown", {}).get("gemini", {})
    gem_req = gem.get("request", {})
    gem_resp = gem.get("response", {})
    fin = trace.get("final_output", {})
    final_txt = str(fin.get("text", ""))
    adap = trace.get("adaptive", {})

    res: dict[str, Any] = {
        "status": trace.get("status", "UNKNOWN"),
        "call_order": trace.get("call_order_in_turn"),
        "ttft_ms": ot.get("time_to_first_token_ms"),
        "total_ms": ot.get("stream_completed_ms"),
        "prompt_tokens": gem_resp.get("prompt_token_count"),
        "cached_tokens": int(gem_resp.get("cached_content_token_count") or 0),
        "thoughts_tokens": int(gem_resp.get("thoughts_token_count") or 0),
        "output_tokens": gem_resp.get("output_token_count"),
        "output_chars": len(final_txt),
        "history_messages": gem_req.get("history_message_count"),
        "history_chars": gem_req.get("history_total_chars"),
    }
    if adap:
        res["thinking_triggered"] = bool(adap.get("thinking_triggered"))
        res["flag_decided_ms"] = adap.get("flag_decided_ms")
        res["stage2_first_chunk_ms"] = adap.get("stage2_first_chunk_ms")
        res["gemini_call_count"] = adap.get("gemini_call_count")
        res["stage1_thoughts_tokens"] = adap.get("stage1_thoughts_tokens")
        res["stage2_thoughts_tokens"] = adap.get("stage2_thoughts_tokens")
        res["stage1_cached_tokens"] = adap.get("stage1_cached_tokens")
        res["stage2_cached_tokens"] = adap.get("stage2_cached_tokens")
    return res


def export_reports(
    jsonl_path: Path,
    yaml_path: Path,
    json_path: Path,
    *,
    suite_started_at: str,
    total_turns_target: int,
) -> None:
    """Build and write clean YAML and JSON benchmark reports from the JSONL turn records."""
    records: list[dict[str, Any]] = []
    if jsonl_path.is_file():
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))

    snapshot_turns = {1, 10, 20, 25, 30, 40, 45, 50}
    turn_summaries: list[dict[str, Any]] = []
    timeline_snapshots: dict[str, Any] = {}

    for rec in records:
        t_num = int(rec["turn"])
        variants_compact = {
            v_key: extract_compact_variant_metrics(v_trace)
            for v_key, v_trace in rec["variants"].items()
        }
        turn_summaries.append(
            {
                "turn": t_num,
                "expected_thinking": bool(rec.get("expected_thinking", t_num in COMPLEX_CALC_PROMPTS)),
                "user_sim_ms": rec["user_simulator"]["duration_ms"],
                "user_chars": len(rec["canonical_user"]),
                "user_text": rec["canonical_user"],
                "agent_canonical_chars": len(rec["canonical_agent"]),
                "history_chars_after_turn": rec["history_chars_after_turn"],
                "variants": variants_compact,
            }
        )
        if t_num in snapshot_turns:
            timeline_snapshots[f"turn_{t_num}"] = {
                v_key: {
                    "overall_timing": v_trace.get("overall_timing"),
                    "timeline_series": v_trace.get("timeline_series"),
                }
                for v_key, v_trace in rec["variants"].items()
            }

    report = {
        "benchmark_metadata": {
            "suite_started_at": suite_started_at,
            "last_updated_at": now_jst(),
            "api_provider": "Google AI Studio (google-genai)",
            "model": MODEL,
            "target_turns": total_turns_target,
            "completed_turns": len(records),
            "design": (
                "Unified Streaming benchmark across 50 turns on shared history list[types.Content]; "
                "compares streaming_low (3.8-flash low), streaming_high (3.8-flash high), and "
                "adaptive_pat_a (Chapter 4 Pattern A: Stage 1 low -> Stage 2 high)."
            ),
        },
        "turns": turn_summaries,
        "timeline_snapshots": timeline_snapshots,
    }
    save_yaml_report(report, yaml_path)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


async def run_benchmark(
    *,
    turns: int,
    jsonl_path: Path,
    yaml_path: Path,
    json_path: Path,
    reset: bool,
) -> None:
    """Execute the 50-turn Streaming benchmark across the 3 target configurations."""
    suite_started_at = now_jst()
    client = create_client()

    # Load existing canonical_user / canonical_agent pairs if available so we can preserve conversation text
    seed_turns: dict[int, tuple[str, str]] = {}
    if jsonl_path.is_file():
        for ln in jsonl_path.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                r_old = json.loads(ln)
                t_old = int(r_old["turn"])
                if "canonical_user" in r_old and "canonical_agent" in r_old:
                    seed_turns[t_old] = (r_old["canonical_user"], r_old["canonical_agent"])

    if reset and jsonl_path.is_file():
        jsonl_path.unlink()

    completed_records: dict[int, dict[str, Any]] = {}
    if not reset and jsonl_path.is_file():
        for ln in jsonl_path.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                r_ex = json.loads(ln)
                v_keys = set(r_ex.get("variants", {}).keys())
                if set(VARIANTS).issubset(v_keys):
                    completed_records[int(r_ex["turn"])] = r_ex

    history: list[types.Content] = []
    write_lock = asyncio.Lock()
    bg_sem = asyncio.Semaphore(12)

    def _fmt(val: float | None) -> str:
        return f"{val:.0f}" if val is not None else "ERR"

    async def _run_remaining_variants_and_save(
        *,
        turn_num: int,
        turn_wall_t0: float,
        user_text: str,
        user_sim_ms: float,
        u_p_tok: int,
        u_o_tok: int,
        canonical_agent: str,
        slow_trace: dict[str, Any],
        history_snapshot: list[types.Content],
        hist_messages_after: int,
        hist_chars_after: int,
    ) -> None:
        async def _run_v(order_idx: int, v_key: str) -> tuple[str, dict[str, Any]]:
            async with bg_sem:
                _, v_tr = await run_streaming_variant_with_retry(
                    client,
                    variant_key=v_key,
                    user_prompt=user_text,
                    history=history_snapshot,
                    call_order=order_idx,
                )
                return v_key, v_tr

        other_pairs = await asyncio.gather(
            _run_v(2, "adaptive_pat_a"),
            _run_v(3, "streaming_high"),
        )
        variant_traces: dict[str, Any] = {"streaming_low": slow_trace}
        for v_key, v_tr in other_pairs:
            variant_traces[v_key] = v_tr

        canonical_traces = {v_key: variant_traces[v_key] for v_key in VARIANTS}
        exp_think = turn_num in COMPLEX_CALC_PROMPTS
        record = {
            "turn": turn_num,
            "expected_thinking": exp_think,
            "recorded_at": now_jst(),
            "user_simulator": {
                "text": user_text,
                "duration_ms": user_sim_ms,
                "prompt_tokens": u_p_tok,
                "output_tokens": u_o_tok,
            },
            "canonical_user": user_text,
            "canonical_agent": canonical_agent,
            "history_messages_after_turn": hist_messages_after,
            "history_chars_after_turn": hist_chars_after,
            "variants": canonical_traces,
        }

        async with write_lock:
            completed_records[turn_num] = record
            ordered_turns = [completed_records[k] for k in sorted(completed_records)]
            with jsonl_path.open("w", encoding="utf-8") as fp:
                for r in ordered_turns:
                    fp.write(json.dumps(r, ensure_ascii=False) + "\n")
            export_reports(
                jsonl_path,
                yaml_path,
                json_path,
                suite_started_at=suite_started_at,
                total_turns_target=turns,
            )

        m_low = extract_compact_variant_metrics(canonical_traces["streaming_low"])
        m_high = extract_compact_variant_metrics(canonical_traces["streaming_high"])
        m_adap = extract_compact_variant_metrics(canonical_traces["adaptive_pat_a"])
        in_tok_disp = m_low["prompt_tokens"] or m_adap["prompt_tokens"]
        cache_disp = max(
            m_low["cached_tokens"],
            m_high["cached_tokens"],
            m_adap["cached_tokens"],
        )
        wall_s = time.perf_counter() - turn_wall_t0
        trig_str = "T" if m_adap.get("thinking_triggered") else "F"
        exp_str = "T" if exp_think else "F"
        print(
            f"[Turn {turn_num:02d}/{turns:02d} exp={exp_str}] "
            f"in={in_tok_disp} (cache={cache_disp}) | "
            f"low={_fmt(m_low['ttft_ms'])}/{_fmt(m_low['total_ms'])}ms(th={m_low['thoughts_tokens']}) | "
            f"high={_fmt(m_high['ttft_ms'])}/{_fmt(m_high['total_ms'])}ms(th={m_high['thoughts_tokens']}) | "
            f"adap({trig_str})={_fmt(m_adap['ttft_ms'])}/{_fmt(m_adap['total_ms'])}ms(th={m_adap['thoughts_tokens']}) "
            f"[{wall_s:.1f}s]",
            flush=True,
        )

    bg_tasks: list[asyncio.Task[None]] = []
    for turn_num in range(1, turns + 1):
        if turn_num in completed_records:
            rec_done = completed_records[turn_num]
            history.append(types.Content(role="user", parts=[types.Part.from_text(text=rec_done["canonical_user"])]))
            history.append(types.Content(role="model", parts=[types.Part.from_text(text=rec_done["canonical_agent"])]))
            continue

        turn_wall_t0 = time.perf_counter()
        if turn_num in COMPLEX_CALC_PROMPTS:
            user_text = COMPLEX_CALC_PROMPTS[turn_num]
            user_sim_ms, u_p_tok, u_o_tok = 0.0, 0, 0
        elif turn_num in seed_turns:
            user_text = seed_turns[turn_num][0]
            user_sim_ms, u_p_tok, u_o_tok = 0.0, 0, 0
        else:
            user_text, user_sim_ms, u_p_tok, u_o_tok = await generate_user_turn(client, turn_num, history)

        history_snapshot = list(history)

        # Run streaming_low first to advance conversation history & warm implicit prefix cache
        canonical_agent, slow_trace = await run_streaming_variant_with_retry(
            client,
            variant_key="streaming_low",
            user_prompt=user_text,
            history=history_snapshot,
            call_order=1,
        )

        history.append(types.Content(role="user", parts=[types.Part.from_text(text=user_text)]))
        history.append(types.Content(role="model", parts=[types.Part.from_text(text=canonical_agent)]))

        hist_chars_now = sum(len(p.text) for c in history for p in (c.parts or []) if p.text)

        bg_tasks.append(
            asyncio.create_task(
                _run_remaining_variants_and_save(
                    turn_num=turn_num,
                    turn_wall_t0=turn_wall_t0,
                    user_text=user_text,
                    user_sim_ms=user_sim_ms,
                    u_p_tok=u_p_tok,
                    u_o_tok=u_o_tok,
                    canonical_agent=canonical_agent,
                    slow_trace=slow_trace,
                    history_snapshot=history_snapshot,
                    hist_messages_after=len(history),
                    hist_chars_after=hist_chars_now,
                )
            )
        )

    if bg_tasks:
        await asyncio.gather(*bg_tasks)


def parse_args() -> argparse.Namespace:
    """Parse CLI options."""
    parser = argparse.ArgumentParser(description="Run 50-turn Streaming Gemini latency benchmark.")
    parser.add_argument("--turns", type=int, default=50, help="Total conversation turns (default: 50).")
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL_PATH, help="Path to JSONL checkpoint file.")
    parser.add_argument("--yaml", type=Path, default=DEFAULT_YAML_PATH, help="Path to output YAML summary report.")
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON_PATH, help="Path to output JSON summary report.")
    parser.add_argument("--reset", action="store_true", help="Delete existing JSONL checkpoint before starting.")
    return parser.parse_args()


if __name__ == "__main__":
    cli_args = parse_args()
    asyncio.run(
        run_benchmark(
            turns=cli_args.turns,
            jsonl_path=cli_args.jsonl,
            yaml_path=cli_args.yaml,
            json_path=cli_args.json,
            reset=cli_args.reset,
        )
    )
