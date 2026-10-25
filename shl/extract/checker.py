"""
File: shl/extract/checker.py
Author: Tuomas Lähteenmäki
Version: 0.1.0
License: MIT
Description:
    Compare extracted keys against existing locale files.

    Reports four classes of issues:

        missing:   in source, not in base locale
        stale:     in base locale, not in source
        conflicting: same key, different default
        incomplete: key exists in target language but not in base

    The checker is language-agnostic: it treats the base locale as
    the source of truth and every other locale as a translation
    that must at least cover the base keys.

    The check exit code is controlled by the caller; the checker
    itself returns a data structure describing the findings.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

logger = logging.getLogger(__name__)


@dataclass
class LanguageCoverage:
    """Coverage statistics for one language file."""

    language: str
    total_keys: int = 0
    translated: int = 0
    missing: int = 0
    stale: int = 0
    empty: int = 0

    @property
    def percent(self) -> float:
        if self.total_keys == 0:
            return 100.0
        return (self.translated / self.total_keys) * 100.0


@dataclass
class CheckReport:
    """Full result of comparing source keys against locales."""

    missing: list[str] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)
    conflicting: list[tuple[str, str, str]] = field(default_factory=list)
    language_coverage: dict[str, LanguageCoverage] = field(default_factory=dict)
    locale_errors: list[tuple[str, str]] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        return bool(
            self.missing
            or self.stale
            or self.conflicting
            or self.locale_errors
        )


def _load_locale(
    path: Path,
    report: CheckReport,
) -> dict[str, str]:
    """Load a locale JSON file. Records errors in report."""
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as error:
        report.locale_errors.append((str(path), str(error)))
        return {}

    if not isinstance(data, dict):
        report.locale_errors.append(
            (str(path), "not a JSON object")
        )
        return {}

    return {
        str(key): str(value) if value is not None else ""
        for key, value in data.items()
    }


def check_locales(
    source_keys: Mapping[str, str],
    locales_dir: Path,
    base_language: str = "eng",
) -> CheckReport:
    """
    Compare source-extracted keys against locale files.

    Args:
        source_keys:  keys extracted from source (key -> default)
        locales_dir:  directory containing <lang>.json files
        base_language: which locale is treated as the base

    Returns:
        CheckReport with missing, stale, conflicting keys and
        per-language coverage statistics.
    """
    report = CheckReport()

    if not locales_dir.is_dir():
        report.locale_errors.append(
            (str(locales_dir), "not a directory")
        )
        return report

    locale_files = sorted(locales_dir.glob("*.json"))

    if not locale_files:
        report.locale_errors.append(
            (str(locales_dir), "no locale files found")
        )
        return report

    for locale_path in locale_files:
        language = locale_path.stem
        locale = _load_locale(locale_path, report)

        coverage = LanguageCoverage(language=language)
        coverage.total_keys = len(source_keys)

        for key, source_default in source_keys.items():
            if key not in locale:
                coverage.missing += 1
                continue

            value = locale[key]

            if not value.strip():
                coverage.empty += 1
                continue

            coverage.translated += 1

            if language == base_language and value != source_default:
                report.conflicting.append((key, source_default, value))

        # Stale keys: in the locale but not in source. Only
        # meaningful for the base locale; other languages may have
        # extra keys from a previous version that have not been
        # cleaned up yet. We still record them per language.
        for key in locale:
            if key not in source_keys:
                coverage.stale += 1

        report.language_coverage[language] = coverage

        if language == base_language:
            report.missing = sorted(
                key for key in source_keys if key not in locale
            )
            report.stale = sorted(
                key for key in locale if key not in source_keys
            )

    return report


def format_check_report(report: CheckReport) -> str:
    """Return a human-readable string for the check report."""

    lines: list[str] = []
    lines.append("SHL locale check")
    lines.append("================\n")

    if report.missing:
        lines.append(f"Missing from base locale ({len(report.missing)}):")
        for key in report.missing[:50]:
            lines.append(f"  {key}")
        if len(report.missing) > 50:
            lines.append(f"  ... and {len(report.missing) - 50} more")
        lines.append("")

    if report.stale:
        lines.append(f"Stale in base locale ({len(report.stale)}):")
        for key in report.stale[:50]:
            lines.append(f"  {key}")
        if len(report.stale) > 50:
            lines.append(f"  ... and {len(report.stale) - 50} more")
        lines.append("")

    if report.conflicting:
        lines.append(f"Conflicting defaults ({len(report.conflicting)}):")
        for key, expected, actual in report.conflicting[:20]:
            lines.append(f"  {key!r}: code={expected!r} locale={actual!r}")
        if len(report.conflicting) > 20:
            lines.append(f"  ... and {len(report.conflicting) - 20} more")
        lines.append("")

    if report.language_coverage:
        lines.append("Language coverage:")
        lines.append(
            f"  {'lang':<8} {'total':>6} {'done':>6} "
            f"{'missing':>8} {'empty':>6} {'stale':>6} {'%':>6}"
        )
        for language in sorted(report.language_coverage):
            coverage = report.language_coverage[language]
            lines.append(
                f"  {language:<8} "
                f"{coverage.total_keys:>6} "
                f"{coverage.translated:>6} "
                f"{coverage.missing:>8} "
                f"{coverage.empty:>6} "
                f"{coverage.stale:>6} "
                f"{coverage.percent:>5.1f}%"
            )
        lines.append("")

    if report.locale_errors:
        lines.append("Locale errors:")
        for path, message in report.locale_errors:
            lines.append(f"  {path}: {message}")
        lines.append("")

    if not report.has_issues:
        lines.append("No issues found.")

    return "\n".join(lines)
