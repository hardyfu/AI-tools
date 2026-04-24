import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Minimal Ollama SDK smoke test.")
    parser.add_argument("--model", default="qwen3.5:4b", help="Ollama model name")
    parser.add_argument(
        "--prompt",
        default="Reply with exactly: OK",
        help="Prompt to send to the model",
    )
    args = parser.parse_args()

    try:
        from ollama import chat
    except ModuleNotFoundError:
        print(f"Python executable: {sys.executable}")
        print("ERROR: Python package 'ollama' is not installed in the current environment.")
        return 1

    try:
        response = chat(
            model=args.model,
            messages=[
                {
                    "role": "user",
                    "content": args.prompt,
                }
            ],
        )
    except Exception as exc:
        print(f"Python executable: {sys.executable}")
        print(f"ERROR: Ollama SDK call failed: {exc}")
        return 1

    content = response["message"]["content"]
    print(f"Python executable: {sys.executable}")
    print(f"Model: {args.model}")
    print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
