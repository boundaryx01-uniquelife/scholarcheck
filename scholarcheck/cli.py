from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from scholarcheck.output import (
    print_domestic_links,
    print_relaxation_suggestions,
    print_table,
    save_records,
)
from scholarcheck.pipeline import build_query, parse_keyword_argument, search_papers


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        prog="scholarcheck",
        description="Verified scholarly metadata search MVP.",
    )
    parser.add_argument("topic", help="Research topic or search phrase")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of records")
    parser.add_argument(
        "--required",
        default="",
        help="Comma-separated required keywords. Defaults to extracted topic keywords.",
    )
    parser.add_argument(
        "--helpful",
        default="",
        help="Comma-separated helpful keywords used as secondary ranking signals.",
    )
    parser.add_argument(
        "--exclude",
        default="",
        help="Comma-separated keywords that exclude records when found in title or abstract.",
    )
    parser.add_argument("--year-from", type=int, default=None, help="Publication year lower bound")
    parser.add_argument("--year-to", type=int, default=None, help="Publication year upper bound")
    parser.add_argument(
        "--format",
        choices=["csv", "json"],
        default="csv",
        help="Saved output format",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file path. Defaults to outputs/scholarcheck_TIMESTAMP.FORMAT",
    )
    args = parser.parse_args()

    if args.limit < 1:
        raise SystemExit("--limit must be 1 or greater")

    query = build_query(
        args.topic,
        required_keywords=parse_keyword_argument(args.required),
        helpful_keywords=parse_keyword_argument(args.helpful),
        excluded_keywords=parse_keyword_argument(args.exclude),
        year_from=args.year_from,
        year_to=args.year_to,
        limit=args.limit,
    )
    result = search_papers(query)

    print(f"Topic: {query.topic}")
    print(f"Keywords: {', '.join(query.keywords) if query.keywords else 'UNKNOWN'}")
    print(f"Required: {', '.join(query.required_keywords) if query.required_keywords else 'UNKNOWN'}")
    print(f"Helpful: {', '.join(query.helpful_keywords) if query.helpful_keywords else 'UNKNOWN'}")
    print(f"Excluded: {', '.join(query.excluded_keywords) if query.excluded_keywords else 'UNKNOWN'}")
    if result.warnings:
        print(f"Warnings: {' | '.join(result.warnings)}")
    print()
    print_table(result.records)
    print()
    print_relaxation_suggestions(result.relaxation_suggestions)
    print()
    print_domestic_links(result.domestic_links)

    output_path = args.output
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path("outputs") / f"scholarcheck_{timestamp}.{args.format}"

    saved_path = save_records(
        result.records,
        output_path,
        result.domestic_links,
        result.relaxation_suggestions,
    )
    print()
    print(f"Saved: {saved_path}")
