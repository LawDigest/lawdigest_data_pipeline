#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""n8n bills 파이프라인용 단계 실행기.

현재는 fetch stage만 지원한다.
stdout에는 순수 JSON만 출력하고, 상세 로그는 stderr로 보낸다.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import json
import os
import sys
from typing import Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.lawdigest_data_pipeline.DataFetcher import DataFetcher
from src.lawdigest_data_pipeline.DataProcessor import DataProcessor


def _coerce_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _coerce_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return default


def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, tuple):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, (list, tuple)):
                return [str(v).strip() for v in parsed if str(v).strip()]
        except (ValueError, SyntaxError):
            pass
        return [part.strip() for part in text.split(",") if part.strip()]
    return [str(value).strip()] if str(value).strip() else []


def _normalize_proposer_kind(value: Any) -> str:
    text = _coerce_optional_text(value) or ""
    if text in {"의원", "CONGRESSMAN"}:
        return "의원"
    if text in {"위원장", "CHAIRMAN"}:
        return "위원장"
    if text in {"정부", "GOVERNMENT"}:
        return "정부"
    return "의원"


def _apply_congressman_enrichment(df_raw, fetcher: DataFetcher):
    processor = DataProcessor(fetcher)
    with contextlib.redirect_stdout(sys.stderr):
        df_cong = processor.process_congressman_bills(df_raw.copy())

    if df_cong is None or df_cong.empty or "billId" not in df_cong.columns:
        return df_raw

    merge_cols = [
        col
        for col in ["billId", "billName", "proposers", "publicProposerIdList", "rstProposerIdList"]
        if col in df_cong.columns
    ]
    if len(merge_cols) <= 1:
        return df_raw

    df_map = df_cong[merge_cols].drop_duplicates(subset=["billId"], keep="last")
    base = df_raw.copy()
    if "billId" not in base.columns:
        return base
    base = base.merge(df_map, on="billId", how="left", suffixes=("", "_enriched"))

    for col in ["billName", "proposers", "publicProposerIdList", "rstProposerIdList"]:
        enriched = f"{col}_enriched"
        if enriched in base.columns:
            base[col] = base[enriched].where(base[enriched].notna(), base.get(col))
            base.drop(columns=[enriched], inplace=True)

    return base


def _row_to_payload(row: dict[str, Any]) -> dict[str, Any]:
    proposer_kind = _normalize_proposer_kind(row.get("proposerKind"))
    bill_id = _coerce_optional_text(row.get("billId"))

    return {
        "billId": bill_id,
        "billName": _coerce_optional_text(row.get("billName")),
        "summary": _coerce_optional_text(row.get("summary")),
        "proposeDate": _coerce_optional_text(row.get("proposeDate")),
        "proposerKind": proposer_kind,
        "committee": _coerce_optional_text(row.get("committee")),
        "billNumber": _coerce_int(row.get("billNumber")),
        "bill_link": _coerce_optional_text(row.get("bill_link")) or _coerce_optional_text(row.get("billLink")),
        "billPdfUrl": _coerce_optional_text(row.get("billPdfUrl")),
        "proposers": _coerce_optional_text(row.get("proposers")),
        "stage": _coerce_optional_text(row.get("stage")),
        "billResult": _coerce_optional_text(row.get("billResult")),
        "publicProposerIdList": _coerce_list(row.get("publicProposerIdList")),
        "rstProposerIdList": _coerce_list(row.get("rstProposerIdList")),
    }


def run_fetch(start_date: str | None, end_date: str | None, age: str | None, limit: int | None = None) -> None:
    with contextlib.redirect_stdout(sys.stderr):
        fetcher = DataFetcher()
        df_bills = fetcher.fetch_bills_data(start_date=start_date, end_date=end_date, age=age)

    if df_bills is None or df_bills.empty:
        print("[]")
        return

    if "billId" in df_bills.columns:
        df_bills = df_bills.drop_duplicates(subset=["billId"], keep="last")

    df_bills = _apply_congressman_enrichment(df_bills, fetcher)
    records = df_bills.to_dict(orient="records")

    payload = []
    for row in records:
        item = _row_to_payload(row)
        if item["billId"]:
            payload.append(item)

    if limit is not None and limit > 0:
        payload = payload[:limit]

    print(json.dumps(payload, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="n8n bills stage runner")
    parser.add_argument("--stage", choices=["fetch"], default="fetch")
    parser.add_argument("--start-date", help="수집 시작일 (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="수집 종료일 (YYYY-MM-DD)")
    parser.add_argument("--age", help="국회 대수 (예: 22)")
    parser.add_argument("--limit", type=int, help="결과 최대 건수 제한")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.stage == "fetch":
        run_fetch(args.start_date, args.end_date, args.age, args.limit)
        return

    raise ValueError(f"지원하지 않는 stage: {args.stage}")


if __name__ == "__main__":
    main()
