import argparse
from pathlib import Path

from agent01_runner import run as run_agent01
from agent02_runner import run as run_agent02


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def validate_case(case_name: str) -> Path:
    case_dir = PROJECT_ROOT / "cases" / case_name
    if not case_dir.exists():
        raise FileNotFoundError(f"Missing case directory: {case_dir}")
    return case_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Minimal gateway runner for policy localization agents.")
    parser.add_argument("--agent", required=True, choices=["agent01", "agent02"], help="Agent to run")
    parser.add_argument("--case", required=True, dest="case_name", help="Case name under cases/<case_name>")
    parser.add_argument("--policy-file", dest="policy_file", help="Policy file path for agent01")
    parser.add_argument("--max-results", type=int, default=5, help="Max Tavily results per query for agent02")
    args = parser.parse_args()

    try:
        validate_case(args.case_name)
        if args.agent == "agent01":
            if not args.policy_file:
                raise ValueError("agent01 requires --policy-file")
            output, converted = run_agent01(args.policy_file)
            print(f"Gateway completed {args.agent}: {output}")
            if converted:
                print(f"Converted Markdown: {converted}")
            return 0
        if args.agent == "agent02":
            output = run_agent02(args.case_name, args.max_results)
            print(f"Gateway completed {args.agent}: {output}")
            return 0
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
