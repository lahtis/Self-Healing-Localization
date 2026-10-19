"""
File: shl/extract/reporter.py
Author: Tuomas Lähteenmäki
Version: 0.1.0
License: MIT
Description:
    Output formatting for shl-extract.

    Supports four formats:
        json:   Localizer-compatible dict, sorted keys
        list:   one key per line (for piping)
        report: human-readable summary with issues
        paths:  "file:line key" for editor navigation

    The json format is the same format Localizer writes, so the
    output can be renamed to locales/en.json and used directly.
"""

import json
import sys
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, TextIO

from .scanner import ExtractedKey, ScanResult, DynamicCall


@dataclass
class Collected:
    """Aggregated results across all scanned files."""

    keys: dict[str, str]
    duplicates: list[ExtractedKey]
    dynamic: list[DynamicCall]
    errors: list[tuple[str, str]]
    function_usage: Counter
    files_scanned: int


def collect_keys(results: Iterable[ScanResult]) -> Collected:
    """
    Merge scan results and aggregate all findings.

    Duplicates are kept only when the default differs, so a key
    that appears identically in multiple places is treated as a
    single entry. Conflicting defaults are reported so the caller
    can resolve them.
    """
    keys: dict[str, str] = {}
    duplicates: list[ExtractedKey] = []
    dynamic: list[DynamicCall] = []
    errors: list[tuple[str, str]] = []
    function_usage: Counter = Counter()
    files_scanned = 0

    for result in results:
        files_scanned += 1

        for message in result.errors:
            errors.append((result.file, message))

        for call in result.dynamic:
            dynamic.append(call)
            function_usage[call.function] += 1

        for entry in result.keys:
            function_usage[entry.function] += 1
            default = entry.default or ""

            if entry.key in keys:
                if keys[entry.key] != default:
                    duplicates.append(entry)
                continue

            keys[entry.key] = default

    return Collected(
        keys=keys,
        duplicates=duplicates,
        dynamic=dynamic,
        errors=errors,
        function_usage=function_usage,
        files_scanned=files_scanned,
    )


def write_json(keys: dict[str, str], out: TextIO) -> None:
    """Write Localizer-compatible JSON."""
    json.dump(
        keys,
        out,
        ensure_ascii=False,
        indent=4,
        sort_keys=True,
    )
    out.write("\n")


def write_list(keys: dict[str, str], out: TextIO) -> None:
    """Write one key per line, sorted."""
    for key in sorted(keys):
        out.write(key)
        out.write("\n")


def write_paths(
    keys: dict[str, str],
    entries: list[ExtractedKey],
    out: TextIO,
) -> None:
    """Write file:line key entries for editor navigation."""
    for entry in sorted(entries, key=lambda e: (e.file, e.line)):
        out.write(f"{entry.file}:{entry.line}: {entry.key}")
        out.write("\n")


def write_report(
    collected: Collected,
    entries: list[ExtractedKey],
    out: TextIO = sys.stdout,
) -> None:
    """Human-readable report for interactive use."""

    keys = collected.keys
    total = len(keys)
    with_default = sum(1 for value in keys.values() if value)

    out.write("SHL extraction report\n")
    out.write("=====================\n\n")
    out.write(f"Files scanned:     {collected.files_scanned}\n")
    out.write(f"Keys found:        {total}\n")
    out.write(f"  with default:    {with_default}\n")
    out.write(f"  without default: {total - with_default}\n")

    if collected.function_usage:
        out.write("\nFunction usage:\n")
        for name, count in collected.function_usage.most_common():
            out.write(f"  {name:<22} {count}\n")

    if collected.duplicates:
        out.write(f"\nConflicting defaults: {len(collected.duplicates)}\n")
        for entry in collected.duplicates:
            out.write(
                f"  {entry.file}:{entry.line}  "
                f"{entry.key!r} -> {entry.default!r}\n"
            )

    if collected.dynamic:
        out.write(
            f"\nDynamic calls (cannot be extracted): "
            f"{len(collected.dynamic)}\n"
        )
        shown = 0
        for call in collected.dynamic:
            out.write(
                f"  {call.file}:{call.line}  "
                f"{call.function}(...)  [{call.reason}]\n"
            )
            shown += 1
            if shown >= 30:
                remaining = len(collected.dynamic) - shown
                if remaining > 0:
                    out.write(f"  ... and {remaining} more\n")
                break

    if collected.errors:
        out.write(f"\nScan errors: {len(collected.errors)}\n")
        for file_path, message in collected.errors:
            out.write(f"  {file_path}  {message}\n")

    if (
        not collected.dynamic
        and not collected.errors
        and not collected.duplicates
    ):
        out.write("\nNo issues found.\n")
