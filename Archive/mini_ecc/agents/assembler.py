import json
from mini_ecc.skills.load_skill import load_skill
from mini_ecc.llm import call_llm

def run_assembler(user_input: str, plan: dict, task_outputs: list[dict]) -> str:
    skill_text = load_skill("assembling.md")

    formatted_outputs = []
    for i, item in enumerate(task_outputs, start=1):
        task = item.get("task", "")
        result = item.get("result", "")
        formatted_outputs.append(
            f"Task {i}: {task}\n\nOutput:\n{result}"
        )

    combined_task_outputs = "\n\n" + ("\n\n---\n\n".join(formatted_outputs))

    prompt = f"""
{skill_text}

You are the assembler agent.

User request:
{user_input}

Overall plan:
{json.dumps(plan, indent=2, ensure_ascii=False)}

Task outputs:
{combined_task_outputs}

Strict rules:
- Combine the task outputs into one single coherent implementation
- Preserve the required features from the plan
- Remove unnecessary duplication
- Prefer one complete HTML file with embedded CSS and JavaScript when appropriate
- Do not explain
- Output code only
"""

    return call_llm(prompt)