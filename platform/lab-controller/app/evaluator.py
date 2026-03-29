import json
import re
from typing import List, Optional, Dict, Any
from anthropic import Anthropic
from openai import OpenAI

def build_system_prompt(scenario: Dict[str, Any], artifact_content: Optional[str], coach_mode: bool = False, coach_round: int = 0, compact_rubric: bool = False) -> str:
    schema_version = scenario.get('schema_version', 1.0)
    domain_name = scenario.get('domain_name', 'Unknown Domain')
    level = scenario.get('level', 0)
    title = scenario.get('title', 'Unknown Exercise')
    delivery_mode = scenario.get('delivery_mode')
    delivery_modes = scenario.get('delivery_modes', [])
    presentation = scenario.get('presentation', {})
    rubric = scenario.get('rubric', {})

    mode = delivery_mode or (delivery_modes[0] if delivery_modes else 'A')

    if schema_version >= 2.0 and 'modes' in presentation:
        active_presentation = presentation['modes'].get(mode) or presentation['modes'].get('A') or {}
    else:
        active_presentation = presentation

    presentation_type = active_presentation.get('type', 'text')
    presentation_context = active_presentation.get('context', '')

    def format_finding(f: Dict[str, Any]) -> str:
        block = f"[{f['id']}] (Severity: {f.get('type') or f.get('severity')}) {f['description'].strip()}"
        if not compact_rubric and f.get('miss_signal'):
            block += f"\nWATCH FOR (MISS SIGNAL): {f['miss_signal'].strip()}"
        return block

    if schema_version >= 2.0 and 'findings' in rubric:
        findings = rubric['findings']
        critical_block = "\n\n".join([format_finding(f) for f in findings if f.get('type') == 'critical'])
        secondary_block = "\n\n".join([format_finding(f) for f in findings if f.get('type') == 'secondary'])
    else:
        critical_block = "\n\n".join([format_finding(f) for f in rubric.get('critical_findings', [])])
        secondary_block = "\n\n".join([format_finding(f) for f in rubric.get('secondary_findings', [])])

    level_indicators = rubric.get('level_indicators', {})
    level_block = "\n\n".join([f"{k.replace('level_', 'Level ')}: {v.strip()}" for k, v in level_indicators.items()])

    mode_note = f"This is a Commission exercise (Mode B). The candidate has been asked to produce a specification or document - not to analyse a given artifact. Evaluate the completeness and quality of what they produced against the rubric findings, which represent required elements of a correct specification." if mode == 'B' else f"This is an Audit/Literacy exercise (Mode {mode}). The candidate has been asked to analyse the provided artifact and identify findings."

    artifact_block = f"ARTIFACT ({presentation_type}):\n```\n{artifact_content}\n```" if artifact_content else "(No artifact - Mode B commission exercise)"

    coach_json_fields = ""
    coach_instructions = ""

    if coach_mode:
        if coach_round == 0:
            coach_json_fields = ",\n  \"coach_question\": <string - a single Socratic question pointing to specific artifact evidence for the primary missed finding; omit this field entirely if all findings are caught>"
            coach_instructions = "\n\nCOACH MODE: After evaluating, if any findings were missed, include a \"coach_question\" field - a single Socratic question pointing to specific evidence in the artifact that would help the candidate discover their primary missed finding. Do not name the finding or reveal the correct answer. The question should be answerable from the artifact alone. Omit this field if no findings were missed."
        else:
            coach_json_fields = ",\n  \"resolved\": <true|false - whether the candidate has now identified the primary missed finding>,\n  \"coach_question\": <string - a more direct follow-up question; omit if resolved is true or if round >= 3>"
            coach_instructions = f"\n\nFOLLOW-UP COACHING (round {coach_round} of 3): The candidate has responded to a coaching question. The exchange history follows the initial response in the message thread. Determine whether they have now identified the primary missed finding:\n- If yes: set \"resolved\": true and complete all evaluation fields normally.\n- If no and round < 3: set \"resolved\": false and include a more direct \"coach_question\".\n- If no and round >= 3: set \"resolved\": false and omit \"coach_question\" - the UI will surface explanation content for the candidate."

    return f"""ROLE: You are an assessment evaluator for the Modern Systems Administration Competency Framework. You are evaluating a candidate's response to a scenario exercise. Do not provide the correct answer or reveal findings the candidate missed.

{mode_note}

DOMAIN: {domain_name} (Level {level})
EXERCISE: {title}

SCENARIO CONTEXT:
{presentation_context.strip()}

{artifact_block}

RUBRIC

Critical findings:
{critical_block or 'None'}

Secondary findings:
{secondary_block or 'None'}

Level indicators:
{level_block or 'Not specified'}

EVALUATION INSTRUCTIONS:
1. Assess the candidate's response against the rubric.
2. Identify which finding IDs were caught (clearly addressed) and which were missed.
3. Assess severity calibration - did they rate critical findings as critical?
4. Credit legitimate findings not in the rubric (note them as "unlisted_N").
5. Produce a level estimate (1–4) with specific evidence from the response.
6. If the candidate is between levels, describe the specific gap.
7. Do NOT reveal what was missed or provide the correct answer.

Respond with a single JSON object - no prose before or after it:
{{
  "level": <1|2|3|4>,
  "confidence": <"high"|"medium"|"low">,
  "caught": [<finding id strings>],
  "missed": [<finding id strings>],
  "almost_caught": [<finding id strings - findings that the candidate touched on or mentioned but did not describe with enough precision to be fully credited according to the rubric>],
  "unlisted": [<brief descriptions of valid unlisted findings>],
  "severity_calibration": <"accurate"|"understated"|"overstated"|"mixed">,
  "gap": <"prose description of what separates this response from the next level, or null if clearly at a level">,
  "narrative": <"1–2 paragraph assessment of the response, suitable for the candidate to read. Do not reveal missed findings or the correct answer.">{coach_json_fields}
}}{coach_instructions}"""

async def perform_evaluation(
    api_key: str,
    model: str,
    scenario: Dict[str, Any],
    artifact_content: Optional[str],
    response_text: str,
    coach_mode: bool = False,
    coach_round: int = 0,
    coach_history: List[Dict[str, str]] = [],
    compact_rubric: bool = False,
    is_retry: bool = False
) -> Dict[str, Any]:
    system_prompt = build_system_prompt(scenario, artifact_content, coach_mode, coach_round, compact_rubric)

    messages = [
        {"role": "user", "content": response_text}
    ]
    # In OpenAI/Anthropic SDKs, we might handle history differently.
    # But for a simple proxy, we'll just append them.
    # Note: coachHistory in the JS version is already in {role, content} format.
    full_messages = messages + coach_history

    try:
        if "claude" in model.lower():
            client = Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                messages=full_messages
            )
            raw = response.content[0].text
        else:
            # Assume OpenAI or OpenAI-compatible local model
            # For local models, we might need a different base_url, but ARCH-09 
            # is primarily about securing the cloud keys.
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                max_tokens=4096,
                messages=[{"role": "system", "content": system_prompt}] + full_messages
            )
            raw = response.choices[0].message.content

        # Extract JSON
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw) or re.search(r'(\{[\s\S]*\})', raw)
        json_str = json_match.group(1) if json_match else raw

        try:
            parsed = json.loads(json_str.strip())
            return {"raw": raw, "parsed": parsed}
        except json.JSONDecodeError:
            if not is_retry:
                return await perform_evaluation(api_key, model, scenario, artifact_content, response_text, coach_mode, coach_round, coach_history, compact_rubric, is_retry=True)
            return {"raw": raw, "parsed": None, "error": "JSON parse failure after retry"}

    except Exception as e:
        return {"raw": "", "parsed": None, "error": str(e)}
