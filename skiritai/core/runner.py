"""Runner for Python-based test cases."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from skiritai.core.base_case import BaseCase
from skiritai.logger import logger


def discover_case_class(case_dir: Path) -> type[BaseCase]:
    """Discover and load the case class from a Python file.

    Looks for case.py in the case directory and finds the first class
    that inherits from BaseCase.
    """
    case_file = case_dir / "case.py"
    if not case_file.exists():
        has_yaml = (case_dir / "case.yaml").is_file() or (case_dir / "case.yml").is_file()
        hint = f" Found case.yaml — use 'skiritai run {case_dir}' to auto-detect YAML." if has_yaml else " Create a case.py or case.yaml in this directory."
        raise FileNotFoundError(f"No case.py found in {case_dir}.{hint}")

    # Load the module
    spec = importlib.util.spec_from_file_location(f"case_{case_dir.name}", case_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    # Find the BaseCase subclass
    for name, obj in vars(module).items():
        if (
                isinstance(obj, type)
                and issubclass(obj, BaseCase)
                and obj is not BaseCase
        ):
            return obj

    raise ValueError(f"No BaseCase subclass found in {case_file}")


async def run_case(
        case_dir: Path,
        on_log=None,
        execution_id: str | None = None,
        results_dir: Path | None = None,
        llm=None,
        step_filter: list[str] | None = None,
) -> dict:
    """Run a Python-based test case.

    Args:
        case_dir: Path to the case directory containing case.py
        on_log: Optional callback for real-time log streaming
        execution_id: Execution identifier for event publishing
        results_dir: Optional directory for saving screenshots/results
        llm: Optional LLM provider instance. If None, auto-detects from env.
        step_filter: Optional list of step names to run. None = run all.

    Returns:
        dict with case_name, status, total_steps, success_count, failed_count, steps
    """
    case_class = discover_case_class(case_dir)
    case_instance = case_class(
        case_dir=case_dir,
        execution_id=execution_id or case_dir.name,
        results_dir=results_dir,
        llm=llm,
    )

    logger.info(f"[PyRunner] Running {case_class.__name__} from {case_dir}")

    report = await case_instance.run(step_filter=step_filter)
    return report


def list_cases(cases_root: Path) -> list[dict]:
    """List all cases (Python + YAML) in the cases directory.

    Recursively scans subdirectories. Case IDs use leaf directory names,
    with ``parent__leaf`` disambiguation when leaf names collide.
    """
    cases = []
    if not cases_root.exists():
        return cases

    seen_dirs = set()

    # Python cases — resolve unique IDs (disambiguates duplicate leaf names)
    from skiritai.core._case_discovery import resolve_case_ids

    all_py_dirs = [d.parent for d in sorted(cases_root.rglob("case.py"))]
    case_id_map = resolve_case_ids(all_py_dirs, root=cases_root)

    for case_id, d in case_id_map.items():
        seen_dirs.add(str(d))
        try:
            case_class = discover_case_class(d)
            steps = case_class().get_step_methods()
            cases.append({
                "id": case_id,
                "name": case_class.__name__,
                "dir": str(d),
                "steps": steps,
                "source": "python",
            })
        except Exception as e:
            logger.warning(f"[PyRunner] Failed to load case {case_id}: {e}")

    # YAML cases
    try:
        from skiritai.core.yaml_runner import list_yaml_cases
        yaml_cases = list_yaml_cases(cases_root)
        for yc in yaml_cases:
            if yc["dir"] not in seen_dirs:
                cases.append(yc)
                seen_dirs.add(yc["dir"])
    except Exception as e:
        logger.debug(f"[Runner] YAML case listing skipped: {e}")

    return cases
