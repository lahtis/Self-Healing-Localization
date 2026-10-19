"""
File: shl/extract/cli.py
Author: Tuomas Lähteenmäki
Version: 0.1.0
License: MIT
Description:
    Command line interface for shl-extract.

    Commands:
        extract   Scan source, optionally write keys to a file.
        check     Compare source keys against locale files.
        list      Print one key per line.

    Exit codes:
        0  success, no issues (or issues ignored)
        1  issues found (check mode, or extract with --check)
        2  fatal error (bad arguments, unreadable directory)
"""

import argparse
import json as _json
import sys
from pathlib import Path

from .scanner import DEFAULT_FUNCTION_NAMES, scan_tree
from .reporter import (
    collect_keys,
    write_json,
    write_list,
    write_paths,
    write_report,
)
from .checker import check_locales, format_check_report


def _parse_function_names(value: str) -> frozenset[str]:
    """Parse a comma-separated list of function names."""
    names = frozenset(
        name.strip()
        for name in value.split(",")
        if name.strip()
    )
    if not names:
        raise argparse.ArgumentTypeError(
            "function list cannot be empty"
        )
    return names


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shl-extract",
        description=(
            "Extract translation keys from Python source code "
            "without running the application."
        ),
    )

    parser.add_argument(
        "--version",
        action="version",
        version="shl-extract 0.1.0",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # ---------------------------------------------------------------
    # extract
    # ---------------------------------------------------------------
    extract = subparsers.add_parser(
        "extract",
        help="Scan source and write translation keys.",
    )

    extract.add_argument(
        "root",
        type=Path,
        help="Directory to scan.",
    )

    extract.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Write keys to a JSON file (Localizer format).",
    )

    extract.add_argument(
        "-f", "--format",
        choices=("json", "report", "list", "paths"),
        default="report",
        help="Output format when --output is not given (default: report).",
    )

    extract.add_argument(
        "--functions",
        type=_parse_function_names,
        default=DEFAULT_FUNCTION_NAMES,
        help=(
            "Comma-separated translation function names "
            f"(default: {','.join(sorted(DEFAULT_FUNCTION_NAMES))})."
        ),
    )

    extract.add_argument(
        "--check",
        action="store_true",
        help="Exit with code 1 if dynamic calls or errors are found.",
    )

    # ---------------------------------------------------------------
    # check
    # ---------------------------------------------------------------
    check = subparsers.add_parser(
        "check",
        help="Compare source keys against locale files.",
    )

    check.add_argument(
        "root",
        type=Path,
        help="Directory to scan.",
    )

    check.add_argument(
        "--locales",
        type=Path,
        required=True,
        help="Directory containing <lang>.json locale files.",
    )

    check.add_argument(
        "--base",
        default="en",
        help="Base language for missing/stale checks (default: en).",
    )

    check.add_argument(
        "--functions",
        type=_parse_function_names,
        default=DEFAULT_FUNCTION_NAMES,
        help="Comma-separated translation function names.",
    )

    check.add_argument(
        "--json",
        action="store_true",
        help="Emit the check report as JSON.",
    )

    check.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Also fail on stale keys and conflicting defaults. "
            "Without this flag only missing keys cause a failure."
        ),
    )

    # ---------------------------------------------------------------
    # list
    # ---------------------------------------------------------------
    list_cmd = subparsers.add_parser(
        "list",
        help="Print extracted keys, one per line.",
    )

    list_cmd.add_argument(
        "root",
        type=Path,
        help="Directory to scan.",
    )

    list_cmd.add_argument(
        "--functions",
        type=_parse_function_names,
        default=DEFAULT_FUNCTION_NAMES,
        help="Comma-separated translation function names.",
    )

    return parser


def _run_extract(args: argparse.Namespace) -> int:
    results = list(scan_tree(args.root, args.functions))
    collected = collect_keys(results)
    entries = [
        entry
        for result in results
        for entry in result.keys
    ]

    if args.output:
        with args.output.open("w", encoding="utf-8") as f:
            write_json(collected.keys, f)
        print(
            f"Wrote {len(collected.keys)} keys to {args.output}",
            file=sys.stderr,
        )
    elif args.format == "json":
        write_json(collected.keys, sys.stdout)
    elif args.format == "list":
        write_list(collected.keys, sys.stdout)
    elif args.format == "paths":
        write_paths(collected.keys, entries, sys.stdout)
    else:
        write_report(collected, entries)

    if args.check:
        return 0 if (not collected.dynamic and not collected.errors) else 1

    return 0


def _run_check(args: argparse.Namespace) -> int:
    results = list(scan_tree(args.root, args.functions))
    collected = collect_keys(results)

    report = check_locales(
        collected.keys,
        args.locales,
        base_language=args.base,
    )

    if args.json:
        payload = {
            "missing": report.missing,
            "stale": report.stale,
            "conflicting": report.conflicting,
            "coverage": {
                lang: {
                    "total": c.total_keys,
                    "translated": c.translated,
                    "missing": c.missing,
                    "empty": c.empty,
                    "stale": c.stale,
                    "percent": round(c.percent, 1),
                }
                for lang, c in report.language_coverage.items()
            },
            "errors": report.locale_errors,
        }
        _json.dump(payload, sys.stdout, indent=4, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        formatted = format_check_report(report)
        sys.stdout.write(formatted)
        if not formatted.endswith("\n"):
            sys.stdout.write("\n")

    if report.missing:
        return 1

    if args.strict and (report.stale or report.conflicting):
        return 1

    if report.locale_errors:
        return 2

    return 0


def _run_list(args: argparse.Namespace) -> int:
    results = list(scan_tree(args.root, args.functions))
    collected = collect_keys(results)
    write_list(collected.keys, sys.stdout)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.root.is_dir():
        print(
            f"error: {args.root} is not a directory",
            file=sys.stderr,
        )
        return 2

    if args.command == "extract":
        return _run_extract(args)
    if args.command == "check":
        return _run_check(args)
    if args.command == "list":
        return _run_list(args)

    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
