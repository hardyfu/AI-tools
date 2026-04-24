from mini_ecc.skills.load_skill import load_skill
from mini_ecc.llm import call_llm

def run_coder_for_task(user_input: str, goal: str, task: str) -> str:
    skill_text = load_skill("coding.md")

    prompt = f"""
{skill_text}

You are the coder agent.

User request:
{user_input}

Overall goal:
{goal}

Current task:
{task}

Strict rules:
- Implement only the current task
- Do not try to implement the entire project
- Keep the output focused on this task
- Output code only
"""

    return call_llm(prompt)