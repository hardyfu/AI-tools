import argparse
import json
import os
import subprocess
import shutil
import sys
import threading
import traceback
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from runtime.project_root import resolve_project_root

PROJECT_ROOT = resolve_project_root(__file__)
os.environ["BASELINE_AGENT_PROJECT_ROOT"] = str(PROJECT_ROOT)
SKILLS_DIR = PROJECT_ROOT / "skills"

from skills.skill01_document_parse.scripts.run_parse import run as run_skill01
from skills.skill01_document_parse.scripts.run_parse import _validate_artifact as validate_skill01_artifact
from skills.skill02_baseline_generation.scripts.run_baseline_generation import run as run_skill02
from skills.skill02_baseline_generation.scripts.run_baseline_generation import _validate_analysis as validate_skill02_analysis
from skills.skill02_baseline_generation.scripts.run_baseline_generation import _validate_compatibility_analysis as validate_skill02_compatibility
from skills.skill03_baseline_finalize.scripts.run_finalize import run as run_skill03
from skills.skill03_baseline_finalize.scripts.run_finalize import validate_workbook as validate_skill03_workbook


class WorkflowStatus(str, Enum):
    BOOTSTRAP_PENDING = "BOOTSTRAP_PENDING"
    INPUTS_STAGED = "INPUTS_STAGED"
    SKILL01_PARTIAL = "SKILL01_PARTIAL"
    SKILL01_COMPLETE = "SKILL01_COMPLETE"
    SKILL02_COMPLETE = "SKILL02_COMPLETE"
    SKILL03_COMPLETE = "SKILL03_COMPLETE"


@dataclass(frozen=True)
class SkillSpec:
    name: str
    skill_dir: Path
    skill_md: Path
    script_path: Path


SKILL_REGISTRY: dict[str, SkillSpec] = {
    "skill01-document-parse": SkillSpec(
        name="skill01-document-parse",
        skill_dir=SKILLS_DIR / "skill01_document_parse",
        skill_md=SKILLS_DIR / "skill01_document_parse" / "SKILL.md",
        script_path=SKILLS_DIR / "skill01_document_parse" / "scripts" / "run_parse.py",
    ),
    "skill02-baseline-generation": SkillSpec(
        name="skill02-baseline-generation",
        skill_dir=SKILLS_DIR / "skill02_baseline_generation",
        skill_md=SKILLS_DIR / "skill02_baseline_generation" / "SKILL.md",
        script_path=SKILLS_DIR / "skill02_baseline_generation" / "scripts" / "run_baseline_generation.py",
    ),
    "skill03-baseline-finalize": SkillSpec(
        name="skill03-baseline-finalize",
        skill_dir=SKILLS_DIR / "skill03_baseline_finalize",
        skill_md=SKILLS_DIR / "skill03_baseline_finalize" / "SKILL.md",
        script_path=SKILLS_DIR / "skill03_baseline_finalize" / "scripts" / "run_finalize.py",
    ),
}


@dataclass
class CasePaths:
    case_name: str
    case_dir: Path
    input_dir: Path
    global_policy_dir: Path
    third_party_standard_dir: Path
    working_dir: Path
    project_profile: Path
    global_policy_parse: Path
    third_party_standard_parse: Path
    baseline_analysis: Path
    baseline_controls: Path
    baseline_report: Path
    priority_recommendations_cn: Path
    final_baseline_xlsx: Path
    skill02_debug: Path
    skill03_debug: Path
    workflow_state: Path



def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)



def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")



def build_case_paths(case_name: str) -> CasePaths:
    case_dir = PROJECT_ROOT / "cases" / case_name
    input_dir = case_dir / "input"
    working_dir = case_dir / "working"
    return CasePaths(
        case_name=case_name,
        case_dir=case_dir,
        input_dir=input_dir,
        global_policy_dir=input_dir / "global_policy",
        third_party_standard_dir=input_dir / "third_party_standard",
        working_dir=working_dir,
        project_profile=working_dir / "project_profile.json",
        global_policy_parse=working_dir / "global_policy_parse.json",
        third_party_standard_parse=working_dir / "third_party_standard_parse.json",
        baseline_analysis=working_dir / "baseline_analysis.json",
        baseline_controls=working_dir / "baseline_controls.md",
        baseline_report=working_dir / "baseline_report.md",
        priority_recommendations_cn=working_dir / "baseline_priority_recommendations_cn.md",
        final_baseline_xlsx=working_dir / "final_baseline.xlsx",
        skill02_debug=working_dir / "skill02_debug.json",
        skill03_debug=working_dir / "skill03_debug.json",
        workflow_state=working_dir / "workflow_state.json",
    )



def ensure_case_structure(paths: CasePaths) -> None:
    for path in (
        paths.case_dir,
        paths.input_dir,
        paths.global_policy_dir,
        paths.third_party_standard_dir,
        paths.working_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)



def bootstrap_case(case_name: str) -> dict[str, Any]:
    paths = build_case_paths(case_name)
    ensure_case_structure(paths)
    if not paths.project_profile.exists():
        template = load_json(PROJECT_ROOT / "templates" / "project_profile.template.json")
        template["case_metadata"]["case_name"] = case_name
        template["case_metadata"]["case_directory"] = f"cases/{case_name}"
        template["inputs"]["global_policy_directory"] = f"cases/{case_name}/input/global_policy"
        template["inputs"]["third_party_standard_directory"] = f"cases/{case_name}/input/third_party_standard"
        write_json(paths.project_profile, template)
    return sync_workflow_state(paths)



def infer_status(paths: CasePaths) -> WorkflowStatus:
    if paths.final_baseline_xlsx.exists():
        return WorkflowStatus.SKILL03_COMPLETE
    if paths.baseline_controls.exists() and paths.baseline_report.exists():
        return WorkflowStatus.SKILL02_COMPLETE
    if paths.global_policy_parse.exists() and paths.third_party_standard_parse.exists():
        return WorkflowStatus.SKILL01_COMPLETE
    if paths.global_policy_parse.exists() or paths.third_party_standard_parse.exists():
        return WorkflowStatus.SKILL01_PARTIAL
    staged = any(paths.global_policy_dir.iterdir()) if paths.global_policy_dir.exists() else False
    staged = staged or (any(paths.third_party_standard_dir.iterdir()) if paths.third_party_standard_dir.exists() else False)
    if staged:
        return WorkflowStatus.INPUTS_STAGED
    return WorkflowStatus.BOOTSTRAP_PENDING



def sync_workflow_state(paths: CasePaths) -> dict[str, Any]:
    state = {
        "case_name": paths.case_name,
        "status": infer_status(paths).value,
        "artifacts": {
            "project_profile": str(paths.project_profile.relative_to(PROJECT_ROOT)),
            "global_policy_parse": str(paths.global_policy_parse.relative_to(PROJECT_ROOT)),
            "third_party_standard_parse": str(paths.third_party_standard_parse.relative_to(PROJECT_ROOT)),
            "baseline_analysis": str(paths.baseline_analysis.relative_to(PROJECT_ROOT)),
            "baseline_controls": str(paths.baseline_controls.relative_to(PROJECT_ROOT)),
            "baseline_report": str(paths.baseline_report.relative_to(PROJECT_ROOT)),
            "priority_recommendations_cn": str(paths.priority_recommendations_cn.relative_to(PROJECT_ROOT)),
            "final_baseline_xlsx": str(paths.final_baseline_xlsx.relative_to(PROJECT_ROOT)),
            "skill02_debug": str(paths.skill02_debug.relative_to(PROJECT_ROOT)),
            "skill03_debug": str(paths.skill03_debug.relative_to(PROJECT_ROOT)),
        },
        "skills": {
            name: {
                "skill_md": str(spec.skill_md.relative_to(PROJECT_ROOT)),
                "script_path": str(spec.script_path.relative_to(PROJECT_ROOT)),
            }
            for name, spec in SKILL_REGISTRY.items()
        },
    }
    write_json(paths.workflow_state, state)
    return state



def stage_input(case_name: str, source_file: str, target: str) -> Path:
    paths = build_case_paths(case_name)
    ensure_case_structure(paths)
    source = Path(source_file).expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"Missing input file: {source}")
    aliases = {
        "global_policy": paths.global_policy_dir,
        "third_party_standard": paths.third_party_standard_dir,
        "org": paths.global_policy_dir,
        "cis": paths.third_party_standard_dir,
    }
    if target not in aliases:
        raise ValueError(f"Unsupported target: {target}")
    destination = aliases[target] / source.name
    shutil.copy2(source, destination)
    sync_workflow_state(paths)
    return destination



def run_pipeline(case_name: str, progress: Callable[[str], None] | None = None) -> dict[str, str]:
    paths = build_case_paths(case_name)
    ensure_case_structure(paths)

    def emit(message: str) -> None:
        if progress is not None:
            progress(message)

    emit("  4.1/4: parse global policy")
    global_policy_parse = run_skill01(case_name, "global_policy")
    emit(f"  Completed global policy parse: {global_policy_parse}")

    emit("  4.2/4: parse third-party standard")
    third_party_parse = run_skill01(case_name, "third_party_standard")
    emit(f"  Completed third-party standard parse: {third_party_parse}")

    emit("  4.3/4: generate baseline analysis")
    baseline_analysis = run_skill02(case_name)
    emit(f"  Completed baseline generation: {baseline_analysis}")

    emit("  4.4/4: finalize workbook")
    final_workbook = run_skill03(case_name)
    emit(f"  Completed workbook finalization: {final_workbook}")

    sync_workflow_state(paths)
    return {
        "global_policy_parse": str(paths.global_policy_parse),
        "third_party_standard_parse": str(paths.third_party_standard_parse),
        "baseline_analysis": str(paths.baseline_analysis),
        "baseline_controls": str(paths.baseline_controls),
        "baseline_report": str(paths.baseline_report),
        "priority_recommendations_cn": str(paths.priority_recommendations_cn),
        "final_baseline_xlsx": str(paths.final_baseline_xlsx),
        "skill02_debug": str(paths.skill02_debug),
        "skill03_debug": str(paths.skill03_debug),
    }


def validate_case(case_name: str) -> dict[str, Any]:
    paths = build_case_paths(case_name)
    if not paths.case_dir.exists():
        raise FileNotFoundError(f"Missing case directory: {paths.case_dir}")

    global_artifact = load_json(paths.global_policy_parse)
    third_party_artifact = load_json(paths.third_party_standard_parse)
    validate_skill01_artifact(
        global_artifact,
        "global_policy",
        sorted(path for path in paths.global_policy_dir.iterdir() if path.is_file() and not path.name.endswith(".normalized.md")),
    )
    validate_skill01_artifact(
        third_party_artifact,
        "third_party_standard",
        sorted(path for path in paths.third_party_standard_dir.iterdir() if path.is_file() and not path.name.endswith(".normalized.md")),
    )

    analysis = load_json(paths.baseline_analysis)
    validate_skill02_analysis(
        analysis=analysis,
        third_party_requirements=third_party_artifact.get("requirements", []),
        global_requirements=global_artifact.get("requirements", []),
    )
    compatibility_analysis = load_json(paths.working_dir / "mapping_analysis.json")
    validate_skill02_compatibility(compatibility_analysis, analysis)

    validate_skill03_workbook(paths.final_baseline_xlsx)
    skill03_debug = load_json(paths.skill03_debug)
    if "source_artifacts" not in skill03_debug:
        raise RuntimeError("skill03_debug.json missing source_artifacts")

    workflow_state = load_json(paths.workflow_state)
    expected_status = infer_status(paths).value
    if workflow_state.get("status") != expected_status:
        raise RuntimeError(
            f"workflow_state status mismatch: expected {expected_status}, got {workflow_state.get('status')}"
        )

    return {
        "case_name": case_name,
        "status": expected_status,
        "validated_artifacts": {
            "global_policy_parse": str(paths.global_policy_parse),
            "third_party_standard_parse": str(paths.third_party_standard_parse),
            "baseline_analysis": str(paths.baseline_analysis),
            "mapping_analysis": str(paths.working_dir / "mapping_analysis.json"),
            "final_baseline_xlsx": str(paths.final_baseline_xlsx),
            "workflow_state": str(paths.workflow_state),
        },
    }


def validate_all_cases() -> dict[str, Any]:
    cases_root = PROJECT_ROOT / "cases"
    if not cases_root.exists():
        raise FileNotFoundError(f"Missing cases directory: {cases_root}")

    case_dirs = sorted(
        path
        for path in cases_root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )
    results: list[dict[str, Any]] = []
    passed = 0
    failed = 0
    for case_dir in case_dirs:
        case_name = case_dir.name
        try:
            result = validate_case(case_name)
            results.append({
                "case_name": case_name,
                "ok": True,
                "status": result.get("status", "unknown"),
            })
            passed += 1
        except Exception as exc:
            results.append({
                "case_name": case_name,
                "ok": False,
                "error": str(exc),
            })
            failed += 1

    return {
        "total_cases": len(case_dirs),
        "passed_cases": passed,
        "failed_cases": failed,
        "results": results,
    }


def copy_final_workbook_to_downloads(case_name: str) -> Path:
    paths = build_case_paths(case_name)
    if not paths.final_baseline_xlsx.exists():
        raise FileNotFoundError(f"Missing final workbook: {paths.final_baseline_xlsx}")
    downloads_dir = Path.home() / "Downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    target = downloads_dir / f"{case_name}-final_baseline.xlsx"
    shutil.copy2(paths.final_baseline_xlsx, target)
    return target


def open_path_in_finder(path: Path) -> None:
    target = path.expanduser().resolve()
    subprocess.run(["open", str(target)], check=True)


def launch_gui() -> int:
    import queue
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk

    class BaselineAgentApp:
        def __init__(self, root: tk.Tk):
            self.root = root
            self.root.title("Cloud Security Baseline Agent")
            self.root.geometry("1080x720")
            self.root.minsize(920, 620)
            self.queue: queue.Queue[tuple[str, str]] = queue.Queue()
            self.is_running = False
            self.current_case: str | None = None

            container = ttk.Frame(root, padding=12)
            container.pack(fill="both", expand=True)
            container.rowconfigure(0, weight=1)
            container.columnconfigure(0, weight=1)

            self.log_widget = scrolledtext.ScrolledText(
                container,
                wrap="word",
                font=("Menlo", 12),
                state="disabled",
                height=28,
            )
            self.log_widget.grid(row=0, column=0, sticky="nsew")

            button_frame = ttk.Frame(container, padding=(0, 12, 0, 0))
            button_frame.grid(row=1, column=0, sticky="ew")
            for index in range(3):
                button_frame.columnconfigure(index, weight=1)

            self.new_button = ttk.Button(button_frame, text="New Instance", command=self.handle_new_instance)
            self.new_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
            self.validate_button = ttk.Button(button_frame, text="Validate", command=self.handle_validate)
            self.validate_button.grid(row=0, column=1, sticky="ew", padx=8)
            self.open_button = ttk.Button(button_frame, text="Open Folder", command=self.handle_open_folder)
            self.open_button.grid(row=0, column=2, sticky="ew", padx=(8, 0))

            self.log("GUI ready.")
            self.log(f"Project root: {PROJECT_ROOT}")
            self.root.after(150, self.poll_queue)

        def log(self, message: str) -> None:
            self.log_widget.configure(state="normal")
            self.log_widget.insert("end", message.rstrip() + "\n")
            self.log_widget.see("end")
            self.log_widget.configure(state="disabled")

        def poll_queue(self) -> None:
            while True:
                try:
                    event_type, payload = self.queue.get_nowait()
                except queue.Empty:
                    break
                if event_type == "log":
                    self.log(payload)
                elif event_type == "done":
                    self.set_running(False)
                elif event_type == "error":
                    self.log(payload)
                    self.set_running(False)
            self.root.after(150, self.poll_queue)

        def set_running(self, running: bool) -> None:
            self.is_running = running
            state = "disabled" if running else "normal"
            self.new_button.configure(state=state)
            self.validate_button.configure(state=state)

        def run_async(self, fn: Any) -> None:
            if self.is_running:
                messagebox.showinfo("Busy", "A task is already running.")
                return
            self.set_running(True)

            def worker() -> None:
                try:
                    fn()
                    self.queue.put(("done", ""))
                except Exception as exc:
                    self.queue.put(("error", f"ERROR: {exc}"))
                    self.queue.put(("log", traceback.format_exc()))

            threading.Thread(target=worker, daemon=True).start()

        def handle_new_instance(self) -> None:
            case_name = simpledialog.askstring("New Instance", "Enter case name:", parent=self.root)
            if not case_name:
                return
            case_name = case_name.strip()
            if not case_name:
                messagebox.showerror("Invalid case name", "Case name cannot be empty.")
                return
            global_file = filedialog.askopenfilename(
                parent=self.root,
                title="Select Global Policy Document",
                filetypes=[("Documents", "*.pdf *.md *.txt"), ("All files", "*.*")],
            )
            if not global_file:
                return
            third_party_file = filedialog.askopenfilename(
                parent=self.root,
                title="Select Third-Party Standard Document",
                filetypes=[("Documents", "*.pdf *.md *.txt"), ("All files", "*.*")],
            )
            if not third_party_file:
                return

            def task() -> None:
                self.queue.put(("log", f"[new-instance] case={case_name}"))
                self.queue.put(("log", "Step 1/5: bootstrap case"))
                bootstrap_result = bootstrap_case(case_name)
                self.queue.put(("log", json.dumps(bootstrap_result, indent=2, ensure_ascii=False)))

                self.queue.put(("log", "Step 2/5: stage global policy"))
                staged_global = stage_input(case_name, global_file, "global_policy")
                self.queue.put(("log", f"Staged global policy: {staged_global}"))

                self.queue.put(("log", "Step 3/5: stage third-party standard"))
                staged_third = stage_input(case_name, third_party_file, "third_party_standard")
                self.queue.put(("log", f"Staged third-party standard: {staged_third}"))

                self.queue.put(("log", "Step 4/5: run analysis pipeline"))
                run_result = run_pipeline(case_name, progress=lambda message: self.queue.put(("log", message)))
                self.queue.put(("log", json.dumps(run_result, indent=2, ensure_ascii=False)))

                self.queue.put(("log", "Step 5/5: copy final workbook to Downloads"))
                downloaded = copy_final_workbook_to_downloads(case_name)
                self.current_case = case_name
                self.queue.put(("log", f"Downloaded final workbook: {downloaded}"))
                self.queue.put(("log", f"Instance complete: {case_name}"))

            self.run_async(task)

        def handle_validate(self) -> None:
            answer = messagebox.askyesnocancel(
                "Validate",
                "Validate all cases?\nYes = all cases\nNo = single case\nCancel = abort",
                parent=self.root,
            )
            if answer is None:
                return
            if answer:
                def task() -> None:
                    self.queue.put(("log", "[validate] all cases"))
                    result = validate_all_cases()
                    self.queue.put(("log", json.dumps(result, indent=2, ensure_ascii=False)))
                self.run_async(task)
                return

            default_case = self.current_case or ""
            case_name = simpledialog.askstring("Validate Case", "Enter case name:", initialvalue=default_case, parent=self.root)
            if not case_name:
                return
            case_name = case_name.strip()
            if not case_name:
                messagebox.showerror("Invalid case name", "Case name cannot be empty.")
                return

            def task() -> None:
                self.queue.put(("log", f"[validate] case={case_name}"))
                result = validate_case(case_name)
                self.current_case = case_name
                self.queue.put(("log", json.dumps(result, indent=2, ensure_ascii=False)))

            self.run_async(task)

        def handle_open_folder(self) -> None:
            try:
                if self.current_case:
                    downloads_target = Path.home() / "Downloads" / f"{self.current_case}-final_baseline.xlsx"
                    if downloads_target.exists():
                        open_path_in_finder(downloads_target.parent)
                        self.log(f"Opened Downloads folder: {downloads_target.parent}")
                        return
                    case_working = build_case_paths(self.current_case).working_dir
                    if case_working.exists():
                        open_path_in_finder(case_working)
                        self.log(f"Opened case working folder: {case_working}")
                        return
                downloads_dir = Path.home() / "Downloads"
                open_path_in_finder(downloads_dir)
                self.log(f"Opened Downloads folder: {downloads_dir}")
            except Exception as exc:
                messagebox.showerror("Open Folder Error", str(exc), parent=self.root)

    root = tk.Tk()
    style = ttk.Style(root)
    if "aqua" in style.theme_names():
        style.theme_use("aqua")
    app = BaselineAgentApp(root)
    root.mainloop()
    return 0



def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        return launch_gui()
    parser = argparse.ArgumentParser(description="Cloud security baseline agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap_parser = subparsers.add_parser("bootstrap", help="Create case structure")
    bootstrap_parser.add_argument("--case", required=True, dest="case_name")

    stage_parser = subparsers.add_parser("stage-input", help="Copy source documents into a case")
    stage_parser.add_argument("--case", required=True, dest="case_name")
    stage_parser.add_argument("--target", required=True, choices=["global_policy", "third_party_standard", "org", "cis"])
    stage_parser.add_argument("--file", required=True, dest="source_file")

    run_parser = subparsers.add_parser("run", help="Run the full skill01 -> skill02 pipeline")
    run_parser.add_argument("--case", required=True, dest="case_name")

    validate_parser = subparsers.add_parser("validate-case", help="Validate existing case artifacts without re-running the pipeline")
    validate_parser.add_argument("--case", required=True, dest="case_name")

    subparsers.add_parser("validate-all-cases", help="Validate all cases under cases/ without re-running the pipeline")

    args = parser.parse_args(argv)
    try:
        if args.command == "bootstrap":
            print(json.dumps(bootstrap_case(args.case_name), indent=2, ensure_ascii=False))
        elif args.command == "stage-input":
            print(stage_input(args.case_name, args.source_file, args.target))
        elif args.command == "run":
            print(json.dumps(run_pipeline(args.case_name), indent=2, ensure_ascii=False))
        elif args.command == "validate-case":
            print(json.dumps(validate_case(args.case_name), indent=2, ensure_ascii=False))
        elif args.command == "validate-all-cases":
            print(json.dumps(validate_all_cases(), indent=2, ensure_ascii=False))
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
