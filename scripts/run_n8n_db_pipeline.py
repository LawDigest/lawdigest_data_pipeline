#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""n8n 실행용 DB 모드 파이프라인 런처 (레거시).

Usage 예시:
  python scripts/run_n8n_db_pipeline.py --step bills_fetch --start-date 2025-12-01 --end-date 2025-12-07
  python scripts/run_n8n_db_pipeline.py --step bills_summarize --input-json '{"bill_id": "...", ...}'
"""

import json
import argparse
import os
import sys
import traceback
from typing import Any

# 프로젝트 루트를 패스에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="n8n에서 호출 가능한 Lawdigest DB 모드 파이프라인 실행 스크립트"
    )
    parser.add_argument(
        "--step",
        choices=["all", "lawmakers", "bills", "bills_fetch", "bills_summarize", "bills_upsert", "timeline", "result", "vote", "stats"],
        default="all",
        help="실행할 단계 (default: all)",
    )
    parser.add_argument(
        "--mode",
        choices=["remote", "db", "ai_test", "dry-run"],
        default="remote",
        help="실행 모드 (default: remote). remote=운영, ai_test=5건 요약 테스트, dry-run=적재 생략",
    )
    parser.add_argument("--start-date", help="수집 시작일 (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="수집 종료일 (YYYY-MM-DD)")
    parser.add_argument("--age", help="국회 대수 (예: 22)")
    parser.add_argument(
        "--input-json",
        help="이전 단계에서 넘어온 JSON 데이터 (문자열)",
    )
    parser.add_argument(
        "--skip-stats",
        action="store_true",
        help="all 실행 시 통계 업데이트를 건너뜜",
    )
    parser.add_argument(
        "--post-stats",
        action="store_true",
        help="각 단계 실행 직후 stats를 추가로 1회 실행 (step=stats 제외)",
    )
    parser.add_argument(
        "--run-id",
        help="n8n 등 외부 오케스트레이터에서 전달하는 실행 추적 ID",
    )
    return parser


def _run_step(wfm: Any, step: str, args: argparse.Namespace) -> None:
    if step == "lawmakers":
        print("[INFO] step=lawmakers 시작", file=sys.stderr)
        result = wfm.update_lawmakers_data(run_stats=not args.post_stats)
        count = len(result) if result is not None else 0
        print(f"[INFO] step=lawmakers 완료 ({count}건)", file=sys.stderr)
        return

    if step == "bills":
        print("[INFO] step=bills 시작", file=sys.stderr)
        result = wfm.update_bills_data(
            start_date=args.start_date,
            end_date=args.end_date,
            age=args.age,
            run_stats=not args.post_stats,
        )
        count = len(result) if result is not None else 0
        print(f"[INFO] step=bills 완료 ({count}건)", file=sys.stderr)
        return

    if step == "bills_fetch":
        df_bills = wfm.fetch_bills_step(
            start_date=args.start_date,
            end_date=args.end_date,
            age=args.age,
        )
        if df_bills is not None:
            print(df_bills.to_json(orient='records', force_ascii=False))
        else:
            print("[]")
        return

    if step == "bills_summarize":
        input_data = json.loads(args.input_json) if args.input_json else []
        summarized = wfm.summarize_bill_step(input_data)
        print(json.dumps(summarized, ensure_ascii=False))
        return

    if step == "bills_upsert":
        input_data = json.loads(args.input_json) if args.input_json else []
        count = wfm.upsert_bill_step(input_data)
        print(json.dumps({"upserted_count": count}, ensure_ascii=False))
        return

    if step == "timeline":
        print("[INFO] step=timeline 시작", file=sys.stderr)
        result = wfm.update_bills_timeline(
            start_date=args.start_date,
            end_date=args.end_date,
            age=args.age,
        )
        count = len(result) if result is not None else 0
        print(f"[INFO] step=timeline 완료 ({count}건)", file=sys.stderr)
        return

    if step == "result":
        print("[INFO] step=result 시작", file=sys.stderr)
        result = wfm.update_bills_result(
            start_date=args.start_date,
            end_date=args.end_date,
            age=args.age,
        )
        count = len(result) if result is not None else 0
        print(f"[INFO] step=result 완료 ({count}건)", file=sys.stderr)
        return

    if step == "vote":
        print("[INFO] step=vote 시작", file=sys.stderr)
        vote_df, vote_party_df = wfm.update_bills_vote(
            start_date=args.start_date,
            end_date=args.end_date,
            age=args.age,
        )
        vote_count = len(vote_df) if vote_df is not None else 0
        vote_party_count = len(vote_party_df) if vote_party_df is not None else 0
        print(f"[INFO] step=vote 완료 (본회의 {vote_count}건, 정당별 {vote_party_count}건)", file=sys.stderr)
        return

    if step == "stats":
        print("[INFO] step=stats 시작", file=sys.stderr)
        wfm.update_statistics()
        print("[INFO] step=stats 완료", file=sys.stderr)


def _is_data_step(step: str) -> bool:
    return step in {"lawmakers", "bills", "timeline", "result", "vote"}


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    print(
        "[WARN] run_n8n_db_pipeline.py는 레거시 경로입니다. "
        "운영 스케줄링은 Airflow DAG를 사용하세요.",
        file=sys.stderr,
    )

    if args.age is not None:
        os.environ["AGE"] = args.age

    if args.run_id:
        print(f"[INFO] run_id={args.run_id}", file=sys.stderr)

    # n8n에서 명시된 환경변수로 모드가 바뀌어도 강제적으로 지정된 모드로 동작시키기
    from src.lawdigest_data_pipeline.WorkFlowManager import WorkFlowManager

    workflow = WorkFlowManager(mode=args.mode)

    if args.step == "all":
        selected_steps = ["lawmakers", "bills", "timeline", "result", "vote"]
        if args.post_stats:
            print("[INFO] --post-stats 활성화: all 모드의 마지막 stats 단계는 생략됩니다.", file=sys.stderr)
        elif not args.skip_stats:
            selected_steps.append("stats")
    else:
        selected_steps = [args.step]

    try:
        for step in selected_steps:
            _run_step(workflow, step, args)
            if args.post_stats and _is_data_step(step):
                _run_step(workflow, "stats", args)
    except Exception as e:
        print(f"[ERROR] {step} 실행 중 오류가 발생했습니다: {type(e).__name__}: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        raise

    print(f"[INFO] 완료: step={args.step}", file=sys.stderr)


if __name__ == "__main__":
    main()
