from typing import Any


def default_first_turn_questions() -> list[str]:
    return [
        "What is the title of the global policy or standard?",
        "Which country or region is this localization for?",
        "Who is the target team or audience?",
        "What practical outcome should the localized document help them achieve?",
    ]


def next_questions_from_answers(answers: dict[str, str]) -> list[str]:
    checks = [
        ("policy_title", "What is the title of the global policy or standard?"),
        ("jurisdiction", "Which country or region is this localization for?"),
        ("audience", "Who is the target team or audience?"),
        ("objective", "What practical outcome should the localized document help them achieve?"),
    ]
    pending = []
    for key, question in checks:
        value = answers.get(key, "").strip()
        if not value:
            pending.append(question)
    return pending


def normalize_answers(answer_payload: dict[str, Any]) -> dict[str, str]:
    return {
        "policy_title": str(answer_payload.get("policy_title", "")).strip(),
        "jurisdiction": str(answer_payload.get("jurisdiction", "")).strip(),
        "audience": str(answer_payload.get("audience", "")).strip(),
        "objective": str(answer_payload.get("objective", "")).strip(),
        "request_owner": str(answer_payload.get("request_owner", "")).strip(),
        "primary_language": str(answer_payload.get("primary_language", "")).strip(),
    }
