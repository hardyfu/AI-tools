import argparse
import json
import sys
from getpass import getpass
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
RUNTIME_DIR = PROJECT_ROOT / "runtime"
SKILLS_DIR = PROJECT_ROOT / "skills"
SKILL_SCRIPT_DIRS = [
    SKILLS_DIR / "localization-intake" / "scripts",
    SKILLS_DIR / "policy-parse" / "scripts",
    SKILLS_DIR / "regulatory-research" / "scripts",
    SKILLS_DIR / "localization-design" / "scripts",
    RUNTIME_DIR,
]
for directory in SKILL_SCRIPT_DIRS:
    directory_str = str(directory)
    if directory_str not in sys.path:
        sys.path.insert(0, directory_str)

from agent01_runner import run as run_agent01
from agent02_runner import run as run_agent02
from agent03_runner import run as run_agent03
from intake_helpers import default_first_turn_questions, next_questions_from_answers, normalize_answers


class WorkflowStatus(str, Enum):
    BOOTSTRAP_PENDING = "BOOTSTRAP_PENDING"
    INTAKE_IN_PROGRESS = "INTAKE_IN_PROGRESS"
    INTAKE_COMPLETE = "INTAKE_COMPLETE"
    POLICY_PARSE_READY = "POLICY_PARSE_READY"
    POLICY_PARSE_COMPLETE = "POLICY_PARSE_COMPLETE"
    REGULATORY_RESEARCH_READY = "REGULATORY_RESEARCH_READY"
    REGULATORY_RESEARCH_COMPLETE = "REGULATORY_RESEARCH_COMPLETE"
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
        skill_dir=SKILLS_DIR / "localization-intake",
        skill_md=SKILLS_DIR / "localization-intake" / "SKILL.md",
        script_path=SKILLS_DIR / "localization-intake" / "scripts" / "intake_helpers.py",
    ),
    "policy-parse": SkillSpec(
        name="policy-parse",
        skill_dir=SKILLS_DIR / "policy-parse",
        skill_md=SKILLS_DIR / "policy-parse" / "SKILL.md",
        script_path=SKILLS_DIR / "policy-parse" / "scripts" / "agent01_runner.py",
    ),
    "regulatory-research": SkillSpec(
        name="regulatory-research",
        skill_dir=SKILLS_DIR / "regulatory-research",
        skill_md=SKILLS_DIR / "regulatory-research" / "SKILL.md",
        script_path=SKILLS_DIR / "regulatory-research" / "scripts" / "agent02_runner.py",
    ),
    "localization-design": SkillSpec(
        name="localization-design",
        skill_dir=SKILLS_DIR / "localization-design",
        skill_md=SKILLS_DIR / "localization-design" / "SKILL.md",
        script_path=SKILLS_DIR / "localization-design" / "scripts" / "agent03_runner.py",
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
    parsed_controls: Path
    regulatory_context: Path
    localization_plan: Path
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
        parsed_controls=working_dir / "parsed_controls.json",
        regulatory_context=working_dir / "regulatory_context.json",
        localization_plan=working_dir / "localization_plan.json",
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


def infer_status(paths: CasePaths) -> WorkflowStatus:
    if paths.localization_plan.exists():
        return WorkflowStatus.LOCALIZATION_DESIGN_COMPLETE
    if paths.regulatory_context.exists():
        return WorkflowStatus.LOCALIZATION_DESIGN_READY
    if paths.parsed_controls.exists():
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
            "parsed_controls": str(paths.parsed_controls.relative_to(PROJECT_ROOT)),
            "regulatory_context": str(paths.regulatory_context.relative_to(PROJECT_ROOT)),
            "localization_plan": str(paths.localization_plan.relative_to(PROJECT_ROOT)),
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

    output_path, converted_markdown = run_agent01(policy_file)
    state = sync_workflow_state(paths)
    result = {
        "case_name": case_name,
        "status": WorkflowStatus.REGULATORY_RESEARCH_READY.value,
        "message": "Agent01 policy parsing completed.",
        "parsed_controls_path": str(output_path.relative_to(PROJECT_ROOT)),
        "skill": {
            "name": parse_skill.name,
            "skill_md": str(parse_skill.skill_md.relative_to(PROJECT_ROOT)),
            "script_path": str(parse_skill.script_path.relative_to(PROJECT_ROOT)) if parse_skill.script_path else None,
        },
        "workflow_state": state,
    }
    if converted_markdown:
        result["converted_markdown_path"] = str(converted_markdown.relative_to(PROJECT_ROOT))
    return result


def run_agent02_step(case_name: str, max_results: int, search_provider: str, tavily_api_key: str) -> dict[str, Any]:
    research_skill = get_skill_spec("regulatory-research")
    paths = build_case_paths(case_name)
    if not paths.scope_profile.exists():
        raise FileNotFoundError(f"Missing scope profile: {paths.scope_profile}")
    if not paths.parsed_controls.exists():
        raise FileNotFoundError(f"Missing parsed controls: {paths.parsed_controls}")

    output_path = run_agent02(case_name, max_results, provider=search_provider, api_key=tavily_api_key)
    state = sync_workflow_state(paths)
    return {
        "case_name": case_name,
        "status": WorkflowStatus.LOCALIZATION_DESIGN_READY.value,
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


def run_agent03_step(case_name: str) -> dict[str, Any]:
    design_skill = get_skill_spec("localization-design")
    paths = build_case_paths(case_name)
    if not paths.scope_profile.exists():
        raise FileNotFoundError(f"Missing scope profile: {paths.scope_profile}")
    if not paths.parsed_controls.exists():
        raise FileNotFoundError(f"Missing parsed controls: {paths.parsed_controls}")
    if not paths.regulatory_context.exists():
        raise FileNotFoundError(f"Missing regulatory context: {paths.regulatory_context}")

    output_path = run_agent03(case_name)
    state = sync_workflow_state(paths)
    return {
        "case_name": case_name,
        "status": WorkflowStatus.LOCALIZATION_DESIGN_COMPLETE.value,
        "message": "Agent03 localization design completed.",
        "localization_plan_path": str(output_path.relative_to(PROJECT_ROOT)),
        "skill": {
            "name": design_skill.name,
            "skill_md": str(design_skill.skill_md.relative_to(PROJECT_ROOT)),
            "script_path": str(design_skill.script_path.relative_to(PROJECT_ROOT)) if design_skill.script_path else None,
        },
        "workflow_state": state,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Policy localization orchestrator skeleton.")
    parser.add_argument("--case", required=True, dest="case_name", help="Case name under cases/<case_name>")
    parser.add_argument(
        "--action",
        required=True,
        choices=["bootstrap", "status", "agent00_start", "agent00_continue", "agent01_run", "agent02_run", "agent03_run"],
        help="Minimal orchestrator actions currently implemented",
    )
    parser.add_argument("--request", help="Initial user request for agent00_start")
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
            tavily_api_key = getpass("Enter Tavily API key for this Agent02 run: ").strip()
            if not tavily_api_key:
                raise ValueError("Tavily API key input was empty.")
            result = run_agent02_step(args.case_name, args.max_results, args.search_provider, tavily_api_key)
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
