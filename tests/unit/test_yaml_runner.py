"""Unit tests for yaml_runner — YAML case loading, failure policies, listing."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


# ============================================================
# 1. load_yaml_case Tests
# ============================================================

class TestLoadYamlCase:
    """Test load_yaml_case() parsing and validation."""

    def test_loads_valid_case_yaml(self, tmp_path: Path):
        from skiritai.core.yaml_runner import load_yaml_case

        yaml_content = """
name: Test Case
steps:
  - action: open page
  - verify: page loaded
"""
        (tmp_path / "case.yaml").write_text(yaml_content, encoding="utf-8")
        data = load_yaml_case(tmp_path)
        assert data["name"] == "Test Case"
        assert len(data["steps"]) == 2
        assert data["steps"][0]["action"] == "open page"

    def test_loads_case_yml_extension(self, tmp_path: Path):
        from skiritai.core.yaml_runner import load_yaml_case

        yaml_content = "steps:\n  - action: do something\n"
        (tmp_path / "case.yml").write_text(yaml_content, encoding="utf-8")
        data = load_yaml_case(tmp_path)
        assert "steps" in data

    def test_prefers_case_yaml_over_yml(self, tmp_path: Path):
        from skiritai.core.yaml_runner import load_yaml_case

        (tmp_path / "case.yaml").write_text("steps:\n  - action: yaml\n", encoding="utf-8")
        (tmp_path / "case.yml").write_text("steps:\n  - action: yml\n", encoding="utf-8")
        data = load_yaml_case(tmp_path)
        assert data["steps"][0]["action"] == "yaml"

    def test_raises_file_not_found(self, tmp_path: Path):
        from skiritai.core.yaml_runner import load_yaml_case

        with pytest.raises(FileNotFoundError, match="No case.yaml/case.yml"):
            load_yaml_case(tmp_path)

    def test_raises_if_not_dict(self, tmp_path: Path):
        from skiritai.core.yaml_runner import load_yaml_case

        (tmp_path / "case.yaml").write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="must be a mapping"):
            load_yaml_case(tmp_path)

    def test_raises_if_missing_steps_key(self, tmp_path: Path):
        from skiritai.core.yaml_runner import load_yaml_case

        (tmp_path / "case.yaml").write_text("name: No steps\n", encoding="utf-8")
        with pytest.raises(ValueError, match="must contain a 'steps' key"):
            load_yaml_case(tmp_path)

    def test_raises_if_steps_not_list(self, tmp_path: Path):
        from skiritai.core.yaml_runner import load_yaml_case

        (tmp_path / "case.yaml").write_text("steps: not a list\n", encoding="utf-8")
        with pytest.raises(ValueError, match="'steps' must be a list"):
            load_yaml_case(tmp_path)

    def test_loads_all_step_types(self, tmp_path: Path):
        from skiritai.core.yaml_runner import load_yaml_case

        yaml_content = """
name: Full case
steps:
  - action: open page
  - verify: check something
  - screenshot: my_screen
  - analyze: true
  - page_info: true
"""
        (tmp_path / "case.yaml").write_text(yaml_content, encoding="utf-8")
        data = load_yaml_case(tmp_path)
        assert len(data["steps"]) == 5

    def test_loads_optional_fields(self, tmp_path: Path):
        from skiritai.core.yaml_runner import load_yaml_case

        yaml_content = """
name: With options
headless: true
max_steps: 10
url: https://example.com
steps:
  - action: do something
"""
        (tmp_path / "case.yaml").write_text(yaml_content, encoding="utf-8")
        data = load_yaml_case(tmp_path)
        assert data["headless"] is True
        assert data["max_steps"] == 10
        assert data["url"] == "https://example.com"


# ============================================================
# 2. _step_failure_policy Tests
# ============================================================

class TestStepFailurePolicy:
    """Test _step_failure_policy() step-level failure control."""

    def test_default_is_abort(self):
        from skiritai.core.yaml_runner import _step_failure_policy
        assert _step_failure_policy({}) == ("abort", 0)

    def test_explicit_abort(self):
        from skiritai.core.yaml_runner import _step_failure_policy
        assert _step_failure_policy({"on_failure": "abort"}) == ("abort", 0)

    def test_explicit_skip(self):
        from skiritai.core.yaml_runner import _step_failure_policy
        assert _step_failure_policy({"on_failure": "skip"}) == ("skip", 0)

    def test_explicit_retry(self):
        from skiritai.core.yaml_runner import _step_failure_policy
        assert _step_failure_policy({"on_failure": "retry"}) == ("retry", 1)

    def test_retry_with_max_retries(self):
        from skiritai.core.yaml_runner import _step_failure_policy
        assert _step_failure_policy({"on_failure": "retry", "max_retries": 3}) == ("retry", 3)

    def test_case_insensitive(self):
        from skiritai.core.yaml_runner import _step_failure_policy
        assert _step_failure_policy({"on_failure": "SKIP"}) == ("skip", 0)
        assert _step_failure_policy({"on_failure": "Abort"}) == ("abort", 0)
        assert _step_failure_policy({"on_failure": "RETRY"}) == ("retry", 1)

    def test_invalid_value_defaults_to_abort(self):
        from skiritai.core.yaml_runner import _step_failure_policy
        assert _step_failure_policy({"on_failure": "continue"}) == ("abort", 0)

    def test_non_string_defaults_to_abort(self):
        from skiritai.core.yaml_runner import _step_failure_policy
        assert _step_failure_policy({"on_failure": 42}) == ("abort", 0)

    def test_none_defaults_to_abort(self):
        from skiritai.core.yaml_runner import _step_failure_policy
        assert _step_failure_policy({"on_failure": None}) == ("abort", 0)


# ============================================================
# 3. _STEP_EXECUTORS mapping Tests
# ============================================================

class TestStepExecutors:
    """Test _STEP_EXECUTORS mapping completeness."""

    def test_all_step_types_registered(self):
        from skiritai.core.yaml_runner import _STEP_EXECUTORS
        expected = {"action", "verify", "screenshot", "analyze", "page_info"}
        assert set(_STEP_EXECUTORS.keys()) == expected

    def test_all_executors_are_async(self):
        import asyncio
        from skiritai.core.yaml_runner import _STEP_EXECUTORS
        for name, executor in _STEP_EXECUTORS.items():
            assert asyncio.iscoroutinefunction(executor), f"{name} executor is not async"

    def test_each_executor_accepts_two_args(self):
        import inspect
        from skiritai.core.yaml_runner import _STEP_EXECUTORS
        for name, executor in _STEP_EXECUTORS.items():
            sig = inspect.signature(executor)
            assert len(sig.parameters) == 2, f"{name} executor should accept 2 params (ai, arg)"


# ============================================================
# 4. list_yaml_cases Tests
# ============================================================

class TestListYamlCases:
    """Test list_yaml_cases() directory scanning."""

    def test_empty_directory(self, tmp_path: Path):
        from skiritai.core.yaml_runner import list_yaml_cases
        cases = list_yaml_cases(tmp_path / "nonexistent")
        assert cases == []

    def test_finds_single_case(self, tmp_path: Path):
        from skiritai.core.yaml_runner import list_yaml_cases

        case_dir = tmp_path / "my_case"
        case_dir.mkdir()
        (case_dir / "case.yaml").write_text(
            "name: My Case\nsteps:\n  - action: test\n", encoding="utf-8"
        )
        cases = list_yaml_cases(tmp_path)
        assert len(cases) == 1
        assert cases[0]["id"] == "my_case"
        assert cases[0]["name"] == "My Case"
        assert cases[0]["source"] == "yaml"

    def test_finds_nested_cases(self, tmp_path: Path):
        from skiritai.core.yaml_runner import list_yaml_cases

        for name in ("case_a", "case_b", "case_c"):
            d = tmp_path / name
            d.mkdir()
            (d / "case.yaml").write_text(
                f"name: {name}\nsteps:\n  - action: test\n", encoding="utf-8"
            )

        cases = list_yaml_cases(tmp_path)
        assert len(cases) == 3
        ids = {c["id"] for c in cases}
        assert ids == {"case_a", "case_b", "case_c"}

    def test_deduplicates_by_resolved_path(self, tmp_path: Path):
        from skiritai.core.yaml_runner import list_yaml_cases

        case_dir = tmp_path / "dup_case"
        case_dir.mkdir()
        (case_dir / "case.yaml").write_text(
            "name: Dup\nsteps:\n  - action: test\n", encoding="utf-8"
        )
        # Both .yaml and .yml exist — should only list once
        (case_dir / "case.yml").write_text(
            "name: Dup\nsteps:\n  - action: test\n", encoding="utf-8"
        )
        cases = list_yaml_cases(tmp_path)
        assert len(cases) == 1

    def test_skips_invalid_yaml_gracefully(self, tmp_path: Path):
        from skiritai.core.yaml_runner import list_yaml_cases

        good_dir = tmp_path / "good"
        good_dir.mkdir()
        (good_dir / "case.yaml").write_text(
            "name: Good\nsteps:\n  - action: test\n", encoding="utf-8"
        )

        bad_dir = tmp_path / "bad"
        bad_dir.mkdir()
        (bad_dir / "case.yaml").write_text("not a valid yaml {{{{", encoding="utf-8")

        cases = list_yaml_cases(tmp_path)
        assert len(cases) == 1
        assert cases[0]["id"] == "good"

    def test_skips_dir_without_case_file(self, tmp_path: Path):
        from skiritai.core.yaml_runner import list_yaml_cases

        empty_dir = tmp_path / "no_case"
        empty_dir.mkdir()
        (empty_dir / "other.txt").write_text("hello", encoding="utf-8")

        cases = list_yaml_cases(tmp_path)
        assert cases == []

    def test_case_includes_dir_path(self, tmp_path: Path):
        from skiritai.core.yaml_runner import list_yaml_cases

        case_dir = tmp_path / "with_path"
        case_dir.mkdir()
        (case_dir / "case.yaml").write_text(
            "name: Path Test\nsteps:\n  - action: test\n", encoding="utf-8"
        )
        cases = list_yaml_cases(tmp_path)
        assert len(cases) == 1
        assert cases[0]["dir"] == str(case_dir.resolve())

    def test_returns_empty_for_nonexistent_root(self, tmp_path: Path):
        from skiritai.core.yaml_runner import list_yaml_cases
        cases = list_yaml_cases(tmp_path / "does_not_exist")
        assert cases == []


# ============================================================
# Run all tests
# ============================================================

if __name__ == "__main__":
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short", "--no-header"],
        cwd=Path(__file__).resolve().parent.parent.parent,
    )
    sys.exit(result.returncode)
