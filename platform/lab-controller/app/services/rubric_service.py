"""Server-side rubric and artifact loading.

Loads scenario YAML files from disk with LRU caching. This keeps rubric data
(miss_signal, level_indicators) server-side — the browser never sees it.
"""
import logging
from functools import lru_cache
from pathlib import Path

import yaml

from ..utils import sanitize_scenario_id, resolve_scenario_path

logger = logging.getLogger(__name__)


@lru_cache(maxsize=128)
def load_scenario_rubric(scenario_id: str) -> dict:
    """Load and parse a full scenario YAML, including rubric with miss_signal and level_indicators.

    Returns the parsed YAML dict. Raises HTTPException (via resolve_scenario_path)
    if the scenario_id is invalid or the file is missing.
    """
    scenario_id = sanitize_scenario_id(scenario_id)
    scenario_path = resolve_scenario_path(scenario_id)

    if not scenario_path.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found.")

    with open(scenario_path, "r", encoding="utf-8") as f:
        scenario = yaml.safe_load(f)

    scenario["_scenarios_path"] = str(scenario_path.parent.relative_to(scenario_path.parent.parent.parent))
    return scenario


def load_artifact_content(scenario_id: str, scenario: dict) -> str | None:
    """Load artifact file content for a scenario's active presentation mode.

    Returns the artifact text, or None if no artifact file is specified.
    """
    presentation = scenario.get("presentation", {})
    modes = presentation.get("modes", {})

    # Try Mode A first (most common), then fall back to first available mode
    mode_data = modes.get("A") or next(iter(modes.values()), {})
    artifact_file = mode_data.get("artifact_file")

    if not artifact_file:
        return None

    # Artifact paths are relative to the scenarios root
    scenario_path = resolve_scenario_path(scenario_id)
    scenarios_root = scenario_path.parent.parent.parent
    artifact_path = (scenarios_root / artifact_file).resolve()

    # Safety: ensure the artifact path stays within scenarios directory
    if not str(artifact_path).startswith(str(scenarios_root.resolve())):
        logger.warning("Artifact path traversal blocked: %s", artifact_file)
        return None

    if not artifact_path.exists():
        logger.warning("Artifact file not found: %s", artifact_path)
        return None

    return artifact_path.read_text(encoding="utf-8")


def get_learning_notes(scenario: dict) -> dict[str, str | None]:
    """Extract learning notes from a scenario's rubric findings.

    Returns a dict mapping finding_id to learning_note text (or None).
    """
    findings = scenario.get("rubric", {}).get("findings", [])
    return {
        f["id"]: f.get("learning_note")
        for f in findings
        if f.get("learning_note")
    }
