"""Shared case directory discovery and ID resolution.

Used by both the CLI runner and the web API layer to ensure consistent
case ID generation, including duplicate leaf-name disambiguation.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path


def resolve_case_ids(all_dirs: list[Path]) -> dict[str, Path]:
    """Resolve case IDs from a list of case directories.

    Uses leaf directory names as IDs. When multiple directories share the
    same leaf name, disambiguates by prefixing with the parent directory
    name separated by ``__`` (e.g. ``baidu_search__01_basecase``).

    Args:
        all_dirs: List of case directories (``case.py`` parent dirs).

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
        index[case_id] = d
    return dict(sorted(index.items()))
