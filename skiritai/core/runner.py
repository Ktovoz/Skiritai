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
        raise FileNotFoundError(f"Case file not found: {case_file}")

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
) -> dict:
    """Run a Python-based test case.

    Args:
        case_dir: Path to the case directory containing case.py
        on_log: Optional callback for real-time log streaming
        execution_id: Execution identifier for event publishing
        results_dir: Optional directory for saving screenshots/results

    Returns:
        dict with case_name, status, total_steps, success_count, failed_count, steps
    """
    case_class = discover_case_class(case_dir)
    case_instance = case_class(
        case_dir=case_dir,
        execution_id=execution_id or case_dir.name,
        results_dir=results_dir,
    )

    logger.info(f"[PyRunner] Running {case_class.__name__} from {case_dir}")

    report = await case_instance.run()
    return report


def list_cases(cases_root: Path) -> list[dict]:
    """List all Python-based cases in the cases directory."""
    cases = []
    if not cases_root.exists():
        return cases

    for d in sorted(cases_root.iterdir()):
        if d.is_dir() and (d / "case.py").exists():
            try:
                case_class = discover_case_class(d)
                steps = case_class().get_step_methods()
                cases.append({
                    "id": d.name,
                    "name": case_class.__name__,
                    "dir": str(d),
                    "steps": steps,
                })
            except Exception as e:
                logger.warning(f"[PyRunner] Failed to load case {d.name}: {e}")

    return cases
