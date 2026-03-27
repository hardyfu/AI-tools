import argparse
import json
import shutil
from getpass import getpass
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any
import tkinter as tk
from tkinter import filedialog

PROJECT_ROOT = Path(__file__).resolve().parent
SKILLS_DIR = PROJECT_ROOT / "skills"
DEFAULT_API_CONFIG_PATH = Path.home() / "Desktop" / "API.json"
from skills.localization_intake.scripts.intake_helpers import (
    default_first_turn_questions,
    next_questions_from_answers,
    normalize_answers,
)
from skills.localization_design.scripts.agent03_runner import run as run_agent03
from skills.requirements_integration.scripts.agent04_runner import run as run_agent04
from skills.policy_parse.scripts.agent01_runner import run as run_agent01
from skills.regulatory_research.scripts.agent02_runner import run as run_agent02


class WorkflowStatus(str, Enum):
    BOOTSTRAP_PENDING = "BOOTSTRAP_PENDING"
    INTAKE_IN_PROGRESS = "INTAKE_IN_PROGRESS"
    INTAKE_COMPLETE = "INTAKE_COMPLETE"
    POLICY_PARSE_READY = "POLICY_PARSE_READY"
    POLICY_PARSE_COMPLETE = "POLICY_PARSE_COMPLETE"
    REGULATORY_RESEARCH_READY = "REGULATORY_RESEARCH_READY"
    REGULATORY_RESEARCH_COMPLETE = "REGULATORY_RESEARCH_COMPLETE"
    REQUIREMENTS_INTEGRATION_READY = "REQUIREMENTS_INTEGRATION_READY"
    LOCALIZATION_DESIGN_READY = "LOCALIZATION_DESIGN_READY"
    LOCALIZATION_DESIGN_COMPLETE = "LOCALIZATION_DESIGN_COMPLETE"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class SkillSpec:
    name: str
    skill_dir: Path
    skill_md: Path
    script_path: Path | None = None


SKILL_REGISTRY: dict[str, SkillSpec] = {
    "localization-intake": SkillSpec(
        name="localization-intake",
        skill_dir=SKILLS_DIR / "localization_intake",
        skill_md=SKILLS_DIR / "localization_intake" / "SKILL.md",
        script_path=SKILLS_DIR / "localization_intake" / "scripts" / "intake_helpers.py",
    ),
    "policy-parse": SkillSpec(
        name="policy-parse",
        skill_dir=SKILLS_DIR / "policy_parse",
        skill_md=SKILLS_DIR / "policy_parse" / "SKILL.md",
        script_path=SKILLS_DIR / "policy_parse" / "scripts" / "agent01_runner.py",
    ),
    "regulatory-research": SkillSpec(
        name="regulatory-research",
        skill_dir=SKILLS_DIR / "regulatory_research",
        skill_md=SKILLS_DIR / "regulatory_research" / "SKILL.md",
        script_path=SKILLS_DIR / "regulatory_research" / "scripts" / "agent02_runner.py",
    ),
    "requirements-integration": SkillSpec(
        name="requirements-integration",
        skill_dir=SKILLS_DIR / "requirements_integration",
        skill_md=SKILLS_DIR / "requirements_integration" / "SKILL.md",
        script_path=SKILLS_DIR / "requirements_integration" / "scripts" / "agent04_runner.py",
    ),
    "localization-design": SkillSpec(
        name="localization-design",
        skill_dir=SKILLS_DIR / "localization_design",
        skill_md=SKILLS_DIR / "localization_design" / "SKILL.md",
        script_path=SKILLS_DIR / "localization_design" / "scripts" / "agent03_runner.py",
    ),
}


@dataclass
class CasePaths:
    case_name: str
    case_dir: Path
    input_dir: Path
    global_policy_dir: Path
    local_regulations_dir: Path
    working_dir: Path
    scope_profile: Path
    policy_parse_result: Path
    regulatory_context: Path
    integrated_requirements: Path
    localized_standard_draft: Path
    workflow_state: Path
    intake_session: Path


def get_skill_spec(name: str) -> SkillSpec:
    try:
        skill = SKILL_REGISTRY[name]
    except KeyError as exc:
        raise KeyError(f"Unknown skill: {name}") from exc
    if not skill.skill_md.exists():
        raise FileNotFoundError(f"Missing skill definition: {skill.skill_md}")
    if skill.script_path is not None and not skill.script_path.exists():
        raise FileNotFoundError(f"Missing skill script: {skill.script_path}")
    return skill


def build_case_paths(case_name: str) -> CasePaths:
    case_dir = PROJECT_ROOT / "cases" / case_name
    input_dir = case_dir / "input"
    working_dir = case_dir / "working"
    return CasePaths(
        case_name=case_name,
        case_dir=case_dir,
        input_dir=input_dir,
        global_policy_dir=input_dir / "global_policy",
        local_regulations_dir=input_dir / "local_regulations",
        working_dir=working_dir,
        scope_profile=working_dir / "scope_profile.json",
        policy_parse_result=working_dir / "policy_parse_result.json",
        regulatory_context=working_dir / "regulatory_context.json",
        integrated_requirements=working_dir / "integrated_requirements.md",
        localized_standard_draft=working_dir / "localized_standard_draft.md",
        workflow_state=working_dir / "workflow_state.json",
        intake_session=working_dir / "intake_session.json",
    )


def ensure_case_structure(paths: CasePaths) -> None:
    for path in (
        paths.case_dir,
        paths.input_dir,
        paths.global_policy_dir,
        paths.local_regulations_dir,
        paths.working_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def resolve_normalized_policy_markdown(paths: CasePaths) -> Path | None:
    if paths.policy_parse_result.exists():
        try:
            metadata = load_json(paths.policy_parse_result)
            relative = metadata.get("normalized_markdown_path")
            if isinstance(relative, str) and relative:
                resolved = PROJECT_ROOT / relative
                if resolved.exists():
                    return resolved
        except Exception:
            pass
    candidates = sorted(paths.global_policy_dir.glob("*.normalized.md"))
    return candidates[0] if candidates else None


def infer_status(paths: CasePaths) -> WorkflowStatus:
    if paths.localized_standard_draft.exists():
        return WorkflowStatus.LOCALIZATION_DESIGN_COMPLETE
    if paths.integrated_requirements.exists():
        return WorkflowStatus.LOCALIZATION_DESIGN_READY
    if paths.regulatory_context.exists():
        return WorkflowStatus.REQUIREMENTS_INTEGRATION_READY
    if paths.policy_parse_result.exists() or resolve_normalized_policy_markdown(paths):
        return WorkflowStatus.REGULATORY_RESEARCH_READY
    if paths.scope_profile.exists():
        return WorkflowStatus.POLICY_PARSE_READY
    return WorkflowStatus.INTAKE_IN_PROGRESS


def sync_workflow_state(paths: CasePaths) -> dict[str, Any]:
    status = infer_status(paths)
    state = {
        "case_name": paths.case_name,
        "status": status.value,
        "intake": load_json(paths.intake_session) if paths.intake_session.exists() else {},
        "artifacts": {
            "scope_profile": str(paths.scope_profile.relative_to(PROJECT_ROOT)),
            "policy_parse_result": str(paths.policy_parse_result.relative_to(PROJECT_ROOT)),
            "normalized_global_policy_markdown": str(resolve_normalized_policy_markdown(paths).relative_to(PROJECT_ROOT))
            if resolve_normalized_policy_markdown(paths)
            else "unknown",
            "regulatory_context": str(paths.regulatory_context.relative_to(PROJECT_ROOT)),
            "integrated_requirements": str(paths.integrated_requirements.relative_to(PROJECT_ROOT)),
            "localized_standard_draft": str(paths.localized_standard_draft.relative_to(PROJECT_ROOT)),
        },
        "skills": {
            name: {
                "skill_md": str(spec.skill_md.relative_to(PROJECT_ROOT)),
                "script_path": str(spec.script_path.relative_to(PROJECT_ROOT)) if spec.script_path else None,
            }
            for name, spec in SKILL_REGISTRY.items()
        },
    }
    write_json(paths.workflow_state, state)
    return state


def bootstrap_case(case_name: str) -> dict[str, Any]:
    paths = build_case_paths(case_name)
    ensure_case_structure(paths)
    return sync_workflow_state(paths)


def template_path(name: str) -> Path:
    return PROJECT_ROOT / "templates" / name


def load_template(name: str) -> dict[str, Any]:
    return load_json(template_path(name))


def replace_case_placeholders(scope_profile: dict[str, Any], case_name: str) -> None:
    metadata = scope_profile.get("case_metadata", {})
    metadata["case_name"] = case_name
    metadata["case_directory"] = f"cases/{case_name}"
    metadata["global_policy_input_directory"] = f"cases/{case_name}/input/global_policy"
    metadata["local_regulations_input_directory"] = f"cases/{case_name}/input/local_regulations"


def finalize_scope_profile(paths: CasePaths, intake_state: dict[str, Any], answers: dict[str, str]) -> dict[str, Any]:
    scope = load_template("scope_profile.template.json")
    replace_case_placeholders(scope, paths.case_name)
    scope["case_metadata"]["status"] = "intake_complete"
    scope["case_metadata"]["request_owner"] = answers.get("request_owner") or "unknown"
    scope["localization_scope"]["target_country_or_region"] = answers.get("jurisdiction") or "unknown"
    scope["localization_scope"]["target_audience"] = answers.get("audience") or "unknown"
    scope["localization_scope"]["target_team"] = answers.get("audience") or "unknown"
    scope["localization_scope"]["primary_language"] = answers.get("primary_language") or "unknown"
    scope["source_policy"]["document_title"] = answers.get("policy_title") or "unknown"
    scope["business_context"]["localization_objective"] = answers.get("objective") or "unknown"
    scope["intake_quality"]["handoff_ready"] = True
    scope["intake_quality"]["handoff_notes"] = "Agent00 intake completed through Python orchestrator."
    scope["intake_quality"]["missing_information"] = []
    scope["intake_quality"]["open_questions"] = []
    scope["intake_quality"]["critical_gaps_blocking_next_step"] = []
    write_json(paths.scope_profile, scope)

    intake_state["awaiting_user_answers"] = False
    intake_state["pending_questions"] = []
    intake_state["finalized"] = True
    write_json(paths.intake_session, intake_state)

    state = sync_workflow_state(paths)
    return {
        "case_name": paths.case_name,
        "status": WorkflowStatus.POLICY_PARSE_READY.value,
        "message": "Agent00 intake completed. scope_profile.json has been created.",
        "scope_profile_path": str(paths.scope_profile.relative_to(PROJECT_ROOT)),
        "global_policy_input_directory": str(paths.global_policy_dir.relative_to(PROJECT_ROOT)),
        "local_regulations_input_directory": str(paths.local_regulations_dir.relative_to(PROJECT_ROOT)),
        "workflow_state": state,
    }


def start_agent00(case_name: str, request: str) -> dict[str, Any]:
    intake_skill = get_skill_spec("localization-intake")
    paths = build_case_paths(case_name)
    ensure_case_structure(paths)
    intake_state = {
        "intake_round": 1,
        "awaiting_user_answers": True,
        "asked_questions": default_first_turn_questions(),
        "pending_questions": default_first_turn_questions(),
        "last_intake_summary": request.strip(),
        "answer_history": [],
    }
    write_json(paths.intake_session, intake_state)
    state = sync_workflow_state(paths)
    return {
        "case_name": case_name,
        "status": WorkflowStatus.INTAKE_IN_PROGRESS.value,
        "summary": request.strip(),
        "questions": intake_state["pending_questions"],
        "message": "Final scope_profile.json will be created only after the user answers the intake questions.",
        "skill": {
            "name": intake_skill.name,
            "skill_md": str(intake_skill.skill_md.relative_to(PROJECT_ROOT)),
            "script_path": str(intake_skill.script_path.relative_to(PROJECT_ROOT)) if intake_skill.script_path else None,
        },
        "workflow_state": state,
    }


def continue_agent00(case_name: str, answers_payload: dict[str, Any]) -> dict[str, Any]:
    paths = build_case_paths(case_name)
    if not paths.intake_session.exists():
        raise FileNotFoundError(f"Missing intake session: {paths.intake_session}")

    intake_state = load_json(paths.intake_session)
    if not intake_state.get("awaiting_user_answers", False):
        return {
            "case_name": case_name,
            "status": infer_status(paths).value,
            "message": "Agent00 is not currently waiting for user answers.",
            "workflow_state": sync_workflow_state(paths),
        }

    answers = normalize_answers(answers_payload)
    intake_state.setdefault("answer_history", []).append(answers)
    intake_state["intake_round"] = int(intake_state.get("intake_round", 1)) + 1

    pending = next_questions_from_answers(answers)
    intake_state["pending_questions"] = pending
    write_json(paths.intake_session, intake_state)

    if pending:
        state = sync_workflow_state(paths)
        return {
            "case_name": case_name,
            "status": WorkflowStatus.INTAKE_IN_PROGRESS.value,
            "questions": pending,
            "message": "More intake information is required before creating scope_profile.json.",
            "workflow_state": state,
        }

    return finalize_scope_profile(paths, intake_state, answers)


def run_agent01_step(case_name: str, policy_file: str) -> dict[str, Any]:
    parse_skill = get_skill_spec("policy-parse")
    paths = build_case_paths(case_name)
    if not paths.scope_profile.exists():
        raise FileNotFoundError(f"Missing scope profile: {paths.scope_profile}")

    output_path, normalized_markdown = run_agent01(policy_file)
    parse_output = load_json(output_path)
    state = sync_workflow_state(paths)
    result = {
        "case_name": case_name,
        "status": WorkflowStatus.REGULATORY_RESEARCH_READY.value,
        "message": "Agent01 policy normalization completed.",
        "policy_parse_result_path": str(output_path.relative_to(PROJECT_ROOT)),
        "normalized_markdown_path": str(normalized_markdown.relative_to(PROJECT_ROOT)),
        "normalization_mode": parse_output.get("normalization_mode", "unknown"),
        "normalization_warnings": parse_output.get("normalization_warnings", []),
        "skill": {
            "name": parse_skill.name,
            "skill_md": str(parse_skill.skill_md.relative_to(PROJECT_ROOT)),
            "script_path": str(parse_skill.script_path.relative_to(PROJECT_ROOT)) if parse_skill.script_path else None,
        },
        "workflow_state": state,
    }
    return result


def run_agent02_step(case_name: str, max_results: int, search_provider: str, tavily_api_key: str) -> dict[str, Any]:
    research_skill = get_skill_spec("regulatory-research")
    paths = build_case_paths(case_name)
    if not paths.scope_profile.exists():
        raise FileNotFoundError(f"Missing scope profile: {paths.scope_profile}")
    normalized_markdown = resolve_normalized_policy_markdown(paths)
    if not paths.policy_parse_result.exists() or not normalized_markdown:
        raise FileNotFoundError("Missing normalized global policy markdown or policy_parse_result.json")

    output_path = run_agent02(case_name, max_results, provider=search_provider, api_key=tavily_api_key)
    state = sync_workflow_state(paths)
    return {
        "case_name": case_name,
        "status": WorkflowStatus.REQUIREMENTS_INTEGRATION_READY.value,
        "message": "Agent02 regulatory research completed.",
        "regulatory_context_path": str(output_path.relative_to(PROJECT_ROOT)),
        "regulatory_research_markdown_path": str((paths.working_dir / "regulatory_research.md").relative_to(PROJECT_ROOT)),
        "skill": {
            "name": research_skill.name,
            "skill_md": str(research_skill.skill_md.relative_to(PROJECT_ROOT)),
            "script_path": str(research_skill.script_path.relative_to(PROJECT_ROOT)) if research_skill.script_path else None,
        },
        "workflow_state": state,
    }


def run_agent04_step(case_name: str) -> dict[str, Any]:
    integration_skill = get_skill_spec("requirements-integration")
    paths = build_case_paths(case_name)
    if not paths.scope_profile.exists():
        raise FileNotFoundError(f"Missing scope profile: {paths.scope_profile}")
    normalized_markdown = resolve_normalized_policy_markdown(paths)
    if not paths.policy_parse_result.exists() or not normalized_markdown:
        raise FileNotFoundError("Missing normalized global policy markdown or policy_parse_result.json")
    if not paths.regulatory_context.exists():
        raise FileNotFoundError(f"Missing regulatory context: {paths.regulatory_context}")

    output_path = run_agent04(case_name)
    state = sync_workflow_state(paths)
    return {
        "case_name": case_name,
        "status": WorkflowStatus.LOCALIZATION_DESIGN_READY.value,
        "message": "Requirements integration completed.",
        "integrated_requirements_path": str(output_path.relative_to(PROJECT_ROOT)),
        "skill": {
            "name": integration_skill.name,
            "skill_md": str(integration_skill.skill_md.relative_to(PROJECT_ROOT)),
            "script_path": str(integration_skill.script_path.relative_to(PROJECT_ROOT)) if integration_skill.script_path else None,
        },
        "workflow_state": state,
    }


def run_agent03_step(case_name: str) -> dict[str, Any]:
    design_skill = get_skill_spec("localization-design")
    paths = build_case_paths(case_name)
    if not paths.scope_profile.exists():
        raise FileNotFoundError(f"Missing scope profile: {paths.scope_profile}")
    if not paths.integrated_requirements.exists():
        raise FileNotFoundError(f"Missing integrated requirements: {paths.integrated_requirements}")

    output_path = run_agent03(case_name)
    state = sync_workflow_state(paths)
    return {
        "case_name": case_name,
        "status": WorkflowStatus.LOCALIZATION_DESIGN_COMPLETE.value,
        "message": "Agent03 localization design completed.",
        "localized_standard_draft_path": str(output_path.relative_to(PROJECT_ROOT)),
        "skill": {
            "name": design_skill.name,
            "skill_md": str(design_skill.skill_md.relative_to(PROJECT_ROOT)),
            "script_path": str(design_skill.script_path.relative_to(PROJECT_ROOT)) if design_skill.script_path else None,
        },
        "workflow_state": state,
    }


QUESTION_KEY_MAP = {
    "What is the title of the global policy or standard?": "policy_title",
    "Which country or region is this localization for?": "jurisdiction",
    "Who is the target team or audience?": "audience",
    "What practical outcome should the localized document help them achieve?": "objective",
}


def prompt_non_empty(prompt_text: str) -> str:
    while True:
        value = input(prompt_text).strip()
        if value:
            return value
        print("Input is required.")


def print_run_status(message: str) -> None:
    print(f"[workflow] {message}")


def summarize_file(path: Path, *, max_chars: int = 240) -> str:
    if not path.exists():
        return "file not found"
    if path.suffix == ".json":
        try:
            payload = load_json(path)
        except Exception:
            return "json summary unavailable"
        keys = ", ".join(payload.keys())
        return f"JSON keys: {keys}"
    try:
        text = path.read_text(encoding="utf-8").strip()
    except Exception:
        return "text summary unavailable"
    if not text:
        return "empty file"
    compact = " ".join(text.split())
    return compact[:max_chars] + ("..." if len(compact) > max_chars else "")


def load_tavily_api_key(api_config_path: Path = DEFAULT_API_CONFIG_PATH) -> str | None:
    if not api_config_path.exists():
        return None
    try:
        payload = json.loads(api_config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = payload.get("TAVILY")
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def resolve_tavily_api_key() -> str:
    configured = load_tavily_api_key()
    if configured:
        print(f"Using Tavily API key from {DEFAULT_API_CONFIG_PATH}")
        return configured
    tavily_api_key = getpass("Enter Tavily API key for this Agent02 run: ").strip()
    if not tavily_api_key:
        raise ValueError("Tavily API key input was empty.")
    return tavily_api_key


def existing_artifact_paths(paths: CasePaths) -> list[Path]:
    ordered = [
        paths.intake_session,
        paths.scope_profile,
        paths.policy_parse_result,
        paths.regulatory_context,
        paths.integrated_requirements,
        paths.localized_standard_draft,
        paths.workflow_state,
    ]
    normalized_markdown = resolve_normalized_policy_markdown(paths)
    if normalized_markdown and normalized_markdown not in ordered:
        ordered.insert(2, normalized_markdown)
    return [path for path in ordered if path.exists()]


def clear_previous_results(paths: CasePaths) -> None:
    for path in existing_artifact_paths(paths):
        if path.is_file():
            path.unlink(missing_ok=True)


def prompt_run_mode_for_existing_case(paths: CasePaths) -> str:
    state = sync_workflow_state(paths)
    existing = existing_artifact_paths(paths)
    print("Existing case data detected.")
    print(f"Case: {paths.case_name}")
    print(f"Current status: {state['status']}")
    print("Existing result files:")
    for path in existing:
        print(f"- {path.relative_to(PROJECT_ROOT)}")
    while True:
        choice = input(
            "Choose how to proceed: [R]esume previous run, start [N]ew run and delete previous results, or [C]ancel\n> "
        ).strip().lower()
        if choice in {"r", "resume"}:
            return "resume"
        if choice in {"n", "new"}:
            return "restart"
        if choice in {"c", "cancel"}:
            return "cancel"
        print("Please enter R, N, or C.")


def collect_agent00_answers_interactively(questions: list[str]) -> dict[str, str]:
    answers: dict[str, str] = {}
    for question in questions:
        key = QUESTION_KEY_MAP.get(question)
        if not key:
            continue
        answers[key] = prompt_non_empty(f"{question}\n> ")
    if "request_owner" not in answers:
        answers["request_owner"] = input("Who is requesting this localization work?\n> ").strip() or "unknown"
    if "primary_language" not in answers:
        answers["primary_language"] = input("What language should the localized guidance be written in?\n> ").strip() or "unknown"
    return answers


def prompt_policy_file(case_name: str) -> str:
    paths = build_case_paths(case_name)
    print(f"Place the global policy file under: {paths.global_policy_dir}")
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askopenfilename(
            title="Select global policy file for Agent01",
            filetypes=[
                ("Policy files", "*.md *.pdf"),
                ("Markdown", "*.md"),
                ("PDF", "*.pdf"),
                ("All files", "*.*"),
            ],
        )
        root.destroy()
        if selected:
            source_path = Path(selected).expanduser().resolve()
            destination = paths.global_policy_dir / source_path.name
            if source_path != destination:
                shutil.copy2(source_path, destination)
            return str(destination)
    except Exception:
        pass
    while True:
        provided = input("Enter the policy file path for Agent01:\n> ").strip()
        if not provided:
            print("Policy file path is required.")
            continue
        policy_path = Path(provided).expanduser().resolve()
        if policy_path.exists():
            destination = paths.global_policy_dir / policy_path.name
            if policy_path != destination:
                shutil.copy2(policy_path, destination)
            return str(destination)
        print(f"File not found: {policy_path}")


def run_workflow(case_name: str, request: str | None, policy_file: str | None, max_results: int, search_provider: str) -> dict[str, Any]:
    bootstrap_case(case_name)
    paths = build_case_paths(case_name)
    steps_run: list[str] = []

    existing = existing_artifact_paths(paths)
    if existing:
        decision = prompt_run_mode_for_existing_case(paths)
        if decision == "cancel":
            state = sync_workflow_state(paths)
            return {
                "case_name": case_name,
                "status": state["status"],
                "message": "Workflow run cancelled by user.",
                "steps_run": steps_run,
                "artifacts": state["artifacts"],
                "workflow_state_path": str(paths.workflow_state.relative_to(PROJECT_ROOT)),
            }
        if decision == "restart":
            clear_previous_results(paths)
            sync_workflow_state(paths)

    if not paths.scope_profile.exists():
        initial_request = request or prompt_non_empty("Enter the initial localization request:\n> ")
        start_result = start_agent00(case_name, initial_request)
        steps_run.append("localization-intake:start")
        print_run_status(f"Started localization-intake for case '{case_name}'.")
        print_run_status("Collecting scope information.")

        while not paths.scope_profile.exists():
            intake_state = load_json(paths.intake_session)
            pending_questions = intake_state.get("pending_questions", [])
            if not pending_questions:
                break
            answers = collect_agent00_answers_interactively([str(q) for q in pending_questions if isinstance(q, str)])
            continue_result = continue_agent00(case_name, answers)
            steps_run.append("localization-intake:continue")
            if continue_result.get("status") == WorkflowStatus.INTAKE_IN_PROGRESS.value:
                print_run_status("More intake information is required.")
            else:
                print_run_status("Intake completed. scope_profile.json created.")
                print_run_status(
                    f"Generated {paths.scope_profile.relative_to(PROJECT_ROOT)} | {summarize_file(paths.scope_profile)}"
                )
            if continue_result.get("status") != WorkflowStatus.INTAKE_IN_PROGRESS.value:
                break

    if not paths.scope_profile.exists():
        raise RuntimeError("Workflow stopped because scope_profile.json was not created.")

    if not paths.policy_parse_result.exists() or not resolve_normalized_policy_markdown(paths):
        resolved_policy_file = policy_file or prompt_policy_file(case_name)
        print_run_status("Running policy-parse.")
        parse_result = run_agent01_step(case_name, resolved_policy_file)
        steps_run.append("policy-parse")
        print_run_status("Policy normalization completed.")
        print_run_status(
            f"Generated {Path(parse_result['policy_parse_result_path'])} | {summarize_file(PROJECT_ROOT / parse_result['policy_parse_result_path'])}"
        )
        print_run_status(
            f"Generated {Path(parse_result['normalized_markdown_path'])} | {summarize_file(PROJECT_ROOT / parse_result['normalized_markdown_path'])}"
        )

    if not paths.policy_parse_result.exists() or not resolve_normalized_policy_markdown(paths):
        raise RuntimeError("Workflow stopped because normalized global policy markdown was not created.")

    if not paths.regulatory_context.exists():
        tavily_api_key = resolve_tavily_api_key()
        print_run_status("Running regulatory-research.")
        research_result = run_agent02_step(case_name, max_results, search_provider, tavily_api_key)
        steps_run.append("regulatory-research")
        print_run_status("Regulatory research completed.")
        print_run_status(
            f"Generated {Path(research_result['regulatory_context_path'])} | {summarize_file(PROJECT_ROOT / research_result['regulatory_context_path'])}"
        )
        print_run_status(
            f"Generated {Path(research_result['regulatory_research_markdown_path'])} | {summarize_file(PROJECT_ROOT / research_result['regulatory_research_markdown_path'])}"
        )

    if not paths.regulatory_context.exists():
        raise RuntimeError("Workflow stopped because regulatory_context.json was not created.")

    if not paths.integrated_requirements.exists():
        print_run_status("Running requirements-integration.")
        integration_result = run_agent04_step(case_name)
        steps_run.append("requirements-integration")
        print_run_status("Requirements integration completed.")
        print_run_status(
            f"Generated {Path(integration_result['integrated_requirements_path'])} | {summarize_file(PROJECT_ROOT / integration_result['integrated_requirements_path'])}"
        )

    if not paths.integrated_requirements.exists():
        raise RuntimeError("Workflow stopped because integrated_requirements.md was not created.")

    if not paths.localized_standard_draft.exists():
        print_run_status("Running localization-design.")
        design_result = run_agent03_step(case_name)
        steps_run.append("localization-design")
        print_run_status("Localized standard draft completed.")
        print_run_status(
            f"Generated {Path(design_result['localized_standard_draft_path'])} | {summarize_file(PROJECT_ROOT / design_result['localized_standard_draft_path'])}"
        )

    state = sync_workflow_state(paths)
    return {
        "case_name": case_name,
        "status": state["status"],
        "message": "Workflow run completed.",
        "steps_run": steps_run,
        "artifacts": state["artifacts"],
        "workflow_state_path": str(paths.workflow_state.relative_to(PROJECT_ROOT)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Policy localization orchestrator skeleton.")
    parser.add_argument("--case", required=True, dest="case_name", help="Case name under cases/<case_name>")
    parser.add_argument(
        "--action",
        required=True,
        choices=["run", "bootstrap", "status", "agent00_start", "agent00_continue", "agent01_run", "agent02_run", "agent04_run", "agent03_run"],
        help="Minimal orchestrator actions currently implemented",
    )
    parser.add_argument("--request", help="Initial user request for agent00_start or run")
    parser.add_argument("--answers-json", help="JSON object of intake answers for agent00_continue")
    parser.add_argument("--policy-file", help="Policy file path for agent01_run")
    parser.add_argument("--max-results", type=int, default=5, help="Max search results per query for agent02_run")
    parser.add_argument(
        "--search-provider",
        choices=["mcp", "api"],
        default="mcp",
        help="Preferred regulatory search provider for agent02_run",
    )
    args = parser.parse_args()

    if args.action == "bootstrap":
        state = bootstrap_case(args.case_name)
        print(json.dumps(state, indent=2))
        return 0
    if args.action == "run":
        try:
            result = run_workflow(args.case_name, args.request, args.policy_file, args.max_results, args.search_provider)
        except Exception as exc:
            raw_hint = PROJECT_ROOT / "cases" / args.case_name / "working" / "localized_standard_draft.raw.txt"
            if raw_hint.exists():
                print(f"[workflow] Debug artifact available: {raw_hint.relative_to(PROJECT_ROOT)}")
            print(f"ERROR: {exc}")
            return 1
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    if args.action == "status":
        paths = build_case_paths(args.case_name)
        if not paths.case_dir.exists():
            print(f"ERROR: Missing case directory: {paths.case_dir}")
            return 1
        state = sync_workflow_state(paths)
        print(json.dumps(state, indent=2))
        return 0
    if args.action == "agent00_start":
        if not args.request:
            print("ERROR: agent00_start requires --request")
            return 1
        result = start_agent00(args.case_name, args.request)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    if args.action == "agent00_continue":
        if not args.answers_json:
            print("ERROR: agent00_continue requires --answers-json")
            return 1
        try:
            answers_payload = json.loads(args.answers_json)
        except json.JSONDecodeError as exc:
            print(f"ERROR: Invalid --answers-json: {exc}")
            return 1
        result = continue_agent00(args.case_name, answers_payload)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    if args.action == "agent01_run":
        if not args.policy_file:
            print("ERROR: agent01_run requires --policy-file")
            return 1
        try:
            result = run_agent01_step(args.case_name, args.policy_file)
        except Exception as exc:
            print(f"ERROR: {exc}")
            return 1
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    if args.action == "agent02_run":
        try:
            tavily_api_key = resolve_tavily_api_key()
            result = run_agent02_step(args.case_name, args.max_results, args.search_provider, tavily_api_key)
        except Exception as exc:
            print(f"ERROR: {exc}")
            return 1
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    if args.action == "agent04_run":
        try:
            result = run_agent04_step(args.case_name)
        except Exception as exc:
            print(f"ERROR: {exc}")
            return 1
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    if args.action == "agent03_run":
        try:
            result = run_agent03_step(args.case_name)
        except Exception as exc:
            print(f"ERROR: {exc}")
            return 1
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
