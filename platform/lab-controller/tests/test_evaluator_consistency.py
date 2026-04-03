import pytest
import subprocess
import json
import os
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.evaluator import build_system_prompt

# Shared test scenario — no hit_signal (baseline)
SCENARIO = {
    "schema_version": 2.0,
    "id": "test-consistency",
    "domain_name": "Test Domain",
    "level": 2,
    "title": "Consistency Test",
    "delivery_modes": ["A"],
    "presentation": {
        "modes": {
            "A": {
                "type": "script",
                "context": "Test context"
            }
        }
    },
    "rubric": {
        "findings": [
            {"id": "f1", "type": "critical", "description": "Critical finding", "miss_signal": "Miss 1"},
            {"id": "f2", "type": "secondary", "description": "Secondary finding", "miss_signal": "Miss 2"}
        ],
        "level_indicators": {
            "level_1": "Level 1 info",
            "level_4": "Level 4 info"
        }
    }
}

ARTIFACT = "Some artifact content"

# Scenario with hit_signal on one finding — used to test EVAL-07 field
SCENARIO_WITH_HIT_SIGNAL = {
    "schema_version": 2.0,
    "id": "test-hit-signal",
    "domain_name": "Test Domain",
    "level": 2,
    "title": "Hit Signal Test",
    "delivery_modes": ["A"],
    "presentation": {
        "modes": {
            "A": {
                "type": "script",
                "context": "Test context"
            }
        }
    },
    "rubric": {
        "findings": [
            {
                "id": "f1", "type": "critical", "description": "Critical finding",
                "miss_signal": "Miss 1", "hit_signal": "Candidate names the $newPassword variable"
            },
            {"id": "f2", "type": "secondary", "description": "Secondary finding", "miss_signal": "Miss 2"}
        ],
        "level_indicators": {
            "level_1": "Level 1 info",
            "level_4": "Level 4 info"
        }
    }
}

def get_js_prompt(scenario, artifact, coach_mode=False, coach_round=0, compact_rubric=False):
    # Get absolute path to the core evaluator
    core_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "core", "evaluator.js")).replace("\\", "/")
    
    # Call core/evaluator.js via Node
    # We'll use a small wrapper script to call the JS function
    js_code = f"""
    import {{ buildSystemPrompt }} from 'file:///{core_path}';
    const scenario = {json.dumps(scenario)};
    const artifact = {json.dumps(artifact)};
    const options = {{ 
        coachMode: {str(coach_mode).lower()}, 
        coachRound: {coach_round}, 
        compactRubric: {str(compact_rubric).lower()} 
    }};
    console.log(buildSystemPrompt(scenario, artifact, options));
    """
    
    # Write temp JS file in the same directory as the test or root
    temp_js = os.path.abspath(os.path.join(os.path.dirname(__file__), "temp_consistency.mjs"))
    with open(temp_js, "w", encoding="utf-8") as f:
        f.write(js_code)
    
    try:
        result = subprocess.run(
            ["node", temp_js],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8"
        )
        return result.stdout.strip()
    finally:
        if os.path.exists(temp_js):
            os.remove(temp_js)

def test_prompt_consistency_standard():
    py_prompt = build_system_prompt(SCENARIO, ARTIFACT)
    js_prompt = get_js_prompt(SCENARIO, ARTIFACT)
    
    assert py_prompt == js_prompt

def test_prompt_consistency_coach_round_0():
    py_prompt = build_system_prompt(SCENARIO, ARTIFACT, coach_mode=True, coach_round=0)
    js_prompt = get_js_prompt(SCENARIO, ARTIFACT, coach_mode=True, coach_round=0)
    
    assert py_prompt == js_prompt

def test_prompt_consistency_coach_round_1():
    py_prompt = build_system_prompt(SCENARIO, ARTIFACT, coach_mode=True, coach_round=1)
    js_prompt = get_js_prompt(SCENARIO, ARTIFACT, coach_mode=True, coach_round=1)
    
    assert py_prompt == js_prompt

def test_prompt_consistency_compact():
    py_prompt = build_system_prompt(SCENARIO, ARTIFACT, compact_rubric=True)
    js_prompt = get_js_prompt(SCENARIO, ARTIFACT, compact_rubric=True)

    assert py_prompt == js_prompt

def test_prompt_consistency_with_hit_signal():
    """EVAL-07: hit_signal field appears in both evaluators identically."""
    py_prompt = build_system_prompt(SCENARIO_WITH_HIT_SIGNAL, ARTIFACT)
    js_prompt = get_js_prompt(SCENARIO_WITH_HIT_SIGNAL, ARTIFACT)

    assert py_prompt == js_prompt
    assert "LOOK FOR (HIT SIGNAL)" in py_prompt
    assert "Candidate names the $newPassword variable" in py_prompt

def test_hit_signal_excluded_in_compact_mode():
    """EVAL-07: hit_signal is suppressed in compact mode, same as miss_signal."""
    py_prompt = build_system_prompt(SCENARIO_WITH_HIT_SIGNAL, ARTIFACT, compact_rubric=True)
    js_prompt = get_js_prompt(SCENARIO_WITH_HIT_SIGNAL, ARTIFACT, compact_rubric=True)

    assert py_prompt == js_prompt
    assert "LOOK FOR (HIT SIGNAL)" not in py_prompt
    assert "WATCH FOR (MISS SIGNAL)" not in py_prompt
