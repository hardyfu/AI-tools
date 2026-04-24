import json
import re
from mini_ecc.skills.load_skill import load_skill
from mini_ecc.llm import call_llm

PLANNER_SCHEMA = {
    "type": "object",
    "properties": {
        "goal": {"type": "string"},
        "tasks": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1
        },
        "validation": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1
        },
    },
    "required": ["goal", "tasks", "validation"],
    "additionalProperties": False,
}


def extract_json(text: str) -> dict:
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError(f"No JSON object found in model output:\n{text}")

    json_str = match.group(0)
    return json.loads(json_str)


def run_planner(user_input: str) -> dict:
    skill_text = load_skill("planning.md")

    prompt = f"""
{skill_text}

You are a planning agent.

User request:
{user_input}

Return only valid JSON using this schema:
{{
  "goal": "string",
  "tasks": ["string"],
  "validation": ["string"]
}}
"""

    response = call_llm(prompt)
    return extract_json(response)