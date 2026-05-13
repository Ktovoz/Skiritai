"""Shared case directory discovery and ID resolution.

Used by both the CLI runner and the web API layer to ensure consistent
case ID generation, including duplicate leaf-name disambiguation.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from skiritai.logger import logger


def resolve_case_ids(all_dirs: list[Path], root: Path | None = None) -> dict[str, Path]:
    """Resolve case IDs from a list of case directories.

    Uses leaf directory names as IDs. When multiple directories share the
    same leaf name, disambiguates by prefixing with the parent directory
    name separated by ``__`` (e.g. ``baidu_search__01_basecase``).

    If the ``parent__leaf`` form still collides, falls back to the full
    path relative to *root* (or the absolute path if *root* is not given).

    Args:
        all_dirs: List of case directories (``case.py`` parent dirs).
        root: Optional root directory for relative-path fallback IDs.

    Returns:
        ``{case_id: directory_path}`` mapping, sorted by case_id.
    """
    name_counts = Counter(d.name for d in all_dirs)
    index: dict[str, Path] = {}
    for d in all_dirs:
        if name_counts[d.name] > 1:
            case_id = f"{d.parent.name}__{d.name}"
        else:
            case_id = d.name

        # Detect collisions that parent__leaf can't resolve
        if case_id in index:
            old = index.pop(case_id)
            logger.warning(
                f"[Cases] ID collision detected: {case_id!r} maps to both "
                f"{old} and {d}. Using relative paths as IDs."
            )
            # Re-insert the old entry with fallback ID
            old_id = _fallback_id(old, root)
            index[old_id] = old
            case_id = _fallback_id(d, root)

        index[case_id] = d
    return dict(sorted(index.items()))


def _fallback_id(d: Path, root: Path | None) -> str:
    """Generate a fallback ID from the path relative to root."""
    if root is not None:
        try:
            rel = d.relative_to(root)
            return str(rel).replace("/", "__").replace("\\", "__")
        except ValueError:
            pass
    # Absolute path fallback — use last 2 segments
    parts = d.parts
    if len(parts) >= 2:
        return "__".join(parts[-2:])
    return d.name
