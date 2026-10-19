"""
File: shl/extract/scanner.py
Author: Tuomas Lähteenmäki
Version: 0.1.0
License: MIT
Description:
    AST-based scanner for SHL translation calls.

    Walks a Python source file's abstract syntax tree and records
    every call to a known translation function. Literal string
    arguments are extracted as keys and defaults. Non-literal
    arguments (f-strings, variables, concatenations) are recorded
    as dynamic and reported to the caller.

    The scanner never imports or executes the scanned code.
"""

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Sequence

logger = logging.getLogger(__name__)


# Function names treated as translation calls. Attribute access is
# stripped before comparison: engine.ui_text(...) matches "ui_text".
DEFAULT_FUNCTION_NAMES: frozenset[str] = frozenset({
    "ui_text",
    "L",
    "template",
    "ensure_ui_key",
    "ensure_template_key",
})


# Default arguments that hold the key and the fallback string.
_KEY_KEYWORDS = ("key",)
_DEFAULT_KEYWORDS = ("default", "default_value")


# Directories that are never scanned. These are common project
# layout names and are skipped to keep the scan fast.
DEFAULT_EXCLUDE_DIRS: frozenset[str] = frozenset({
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    ".eggs",
})


@dataclass(frozen=True)
class ExtractedKey:
    """One translation key found in source code."""

    key: str
    default: str | None
    file: str
    line: int
    column: int
    function: str


@dataclass
class DynamicCall:
    """A translation call whose key could not be resolved statically."""

    file: str
    line: int
    column: int
    function: str
    reason: str


@dataclass
class ScanResult:
    """Result of scanning one file."""

    file: str
    keys: list[ExtractedKey] = field(default_factory=list)
    dynamic: list[DynamicCall] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return not self.dynamic and not self.errors


class _CallVisitor(ast.NodeVisitor):
    """Collect translation calls from a module AST."""

    def __init__(
        self,
        file_path: str,
        function_names: frozenset[str],
    ) -> None:
        self.file_path = file_path
        self.function_names = function_names
        self.result = ScanResult(file=file_path)

    def visit_Call(self, node: ast.Call) -> None:
        name = self._call_name(node.func)

        if name in self.function_names:
            self._handle_call(name, node)

        self.generic_visit(node)

    @staticmethod
    def _call_name(func: ast.expr) -> str | None:
        """Return the trailing identifier of a call target.

        Matches:
            ui_text(...)              -> "ui_text"
            engine.ui_text(...)       -> "ui_text"
            self.localizer.L(...)     -> "L"
        """
        if isinstance(func, ast.Name):
            return func.id

        if isinstance(func, ast.Attribute):
            return func.attr

        return None

    def _handle_call(self, name: str, node: ast.Call) -> None:
        key_expr = self._extract_key_expr(node)
        default_expr = self._extract_default_expr(node)

        key = self._string_constant(key_expr)

        if key is None:
            self.result.dynamic.append(
                DynamicCall(
                    file=self.file_path,
                    line=node.lineno,
                    column=node.col_offset,
                    function=name,
                    reason=self._describe_key_expr(key_expr),
                )
            )
            return

        default = self._string_constant(default_expr)

        self.result.keys.append(
            ExtractedKey(
                key=key,
                default=default,
                file=self.file_path,
                line=node.lineno,
                column=node.col_offset,
                function=name,
            )
        )

    @staticmethod
    def _extract_key_expr(node: ast.Call) -> ast.expr | None:
        """Return the expression that supplies the key, or None."""
        if node.args:
            return node.args[0]

        for keyword in node.keywords:
            if keyword.arg in _KEY_KEYWORDS:
                return keyword.value

        return None

    @staticmethod
    def _extract_default_expr(node: ast.Call) -> ast.expr | None:
        """Return the expression that supplies the default, or None."""
        if len(node.args) >= 2:
            return node.args[1]

        for keyword in node.keywords:
            if keyword.arg in _DEFAULT_KEYWORDS:
                return keyword.value

        return None

    @staticmethod
    def _string_constant(node: ast.expr | None) -> str | None:
        """Return the value if node is a plain string literal."""
        if node is None:
            return None

        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value

        return None

    @staticmethod
    def _describe_key_expr(node: ast.expr | None) -> str:
        """Human-readable reason why a key could not be extracted."""
        if node is None:
            return "no key argument"

        if isinstance(node, ast.JoinedStr):
            return "f-string"

        if isinstance(node, ast.BinOp):
            return "concatenation"

        if isinstance(node, ast.Name):
            return f"variable '{node.id}'"

        if isinstance(node, ast.Attribute):
            return "attribute access"

        if isinstance(node, ast.Call):
            return "function call"

        return type(node).__name__


def scan_file(
    path: Path,
    function_names: frozenset[str] = DEFAULT_FUNCTION_NAMES,
) -> ScanResult:
    """
    Scan one Python file for translation calls.

    Never executes the file. Parse errors are recorded in
    ScanResult.errors and do not raise.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as error:
        return ScanResult(
            file=str(path),
            errors=[f"read failed: {error}"],
        )
    except UnicodeDecodeError as error:
        return ScanResult(
            file=str(path),
            errors=[f"decode failed: {error}"],
        )

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as error:
        location = f"line {error.lineno}" if error.lineno else "unknown line"
        return ScanResult(
            file=str(path),
            errors=[f"syntax error at {location}: {error.msg}"],
        )

    visitor = _CallVisitor(str(path), function_names)
    visitor.visit(tree)
    return visitor.result


def _is_excluded(
    path: Path,
    root: Path,
    exclude_dirs: frozenset[str],
) -> bool:
    """Return True if any directory in the relative path is excluded."""
    try:
        relative = path.relative_to(root)
    except ValueError:
        relative = path

    for part in relative.parts:
        if part in exclude_dirs:
            return True

    return False


def scan_tree(
    root: Path,
    function_names: frozenset[str] = DEFAULT_FUNCTION_NAMES,
    exclude_dirs: frozenset[str] = DEFAULT_EXCLUDE_DIRS,
) -> Iterator[ScanResult]:
    """
    Scan every .py file under root.

    Yields ScanResult per file. Excluded directories are skipped.
    Files that fail to parse are yielded with errors set.
    """
    if not root.is_dir():
        yield ScanResult(
            file=str(root),
            errors=["not a directory"],
        )
        return

    for path in sorted(root.rglob("*.py")):
        if _is_excluded(path, root, exclude_dirs):
            continue

        yield scan_file(path, function_names)


def merge_keys(
    results: Sequence[ScanResult],
) -> dict[str, str]:
    """
    Merge extracted keys from multiple files into a single map.

    When the same key is found in several places with different
    defaults, the first occurrence wins and the conflict is
    logged at debug level. Use check_locales() for a full
    report of conflicts.
    """
    merged: dict[str, str] = {}
    sources: dict[str, str] = {}

    for result in results:
        for entry in result.keys:
            default = entry.default or ""

            if entry.key in merged:
                if merged[entry.key] != default:
                    logger.debug(
                        "key %r: default %r (from %s:%d) overrides %r",
                        entry.key,
                        merged[entry.key],
                        sources[entry.key],
                        0,
                        default,
                    )
                continue

            merged[entry.key] = default
            sources[entry.key] = f"{entry.file}:{entry.line}"

    return merged
