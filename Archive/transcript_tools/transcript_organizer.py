#!/usr/bin/env python3
"""
Interactive transcript organizer.

What it does:
1) Ask user for output file name (markdown)
2) Repeatedly ask for transcript title + raw transcript block
3) Append each transcript block into the same markdown file
4) Ask user to continue or stop
5) On stop, generate a summary section in markdown
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class TranscriptEntry:
    title: str
    content: str


def normalize_space(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    return text


def parse_transcript(raw: str) -> str:
    """Remove timestamps and merge transcript into continuous text."""
    lines = [ln.rstrip() for ln in raw.splitlines()]
    chunks: List[str] = []
    current_lines: List[str] = []

    def flush_current() -> None:
        nonlocal current_lines
        text = normalize_space(" ".join(x.strip() for x in current_lines if x.strip()))
        if text:
            chunks.append(text)
        current_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if re.match(r"^\d{1,2}:\d{2}$", stripped) or re.match(r"^\d{1,2}:\d{2}:\d{2}$", stripped):
            flush_current()
        else:
            current_lines.append(stripped)

    flush_current()
    return normalize_space(" ".join(chunks))


def ask_output_path() -> Path:
    while True:
        name = input("请输入输出文件名（不含扩展名也可以）: ").strip()
        if not name:
            print("文件名不能为空，请重新输入。")
            continue

        path = Path(name)
        if path.suffix.lower() != ".md":
            path = path.with_suffix(".md")

        return path


def ask_title() -> str:
    while True:
        title = input("请输入这段 transcript 的标题: ").strip()
        if title:
            return title
        print("标题不能为空，请重新输入。")


def ask_transcript_block() -> str:
    print("请粘贴 transcript 原文。输入完成后，单独输入 END 并回车结束：")
    lines: List[str] = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


def ask_continue() -> bool:
    while True:
        choice = input("是否继续输入下一段 transcript？(y/n): ").strip().lower()
        if choice in {"y", "yes"}:
            return True
        if choice in {"n", "no"}:
            return False
        print("请输入 y 或 n。")


def append_entry(md_path: Path, entry: TranscriptEntry) -> None:
    with md_path.open("a", encoding="utf-8") as f:
        f.write(f"## {entry.title}\n\n")
        f.write(f"{entry.content}\n\n")


def write_summary(md_path: Path, entries: List[TranscriptEntry]) -> None:
    with md_path.open("a", encoding="utf-8") as f:
        f.write("## 汇总\n\n")
        f.write(f"- 总段数: {len(entries)}\n")
        for i, entry in enumerate(entries, start=1):
            f.write(f"- {i}. {entry.title}\n")


def main() -> None:
    print("=== Transcript 整理工具（Markdown 输出）===")
    output_path = ask_output_path()

    # Initialize file with top-level heading matching output filename.
    output_path.write_text(f"# {output_path.stem}\n\n", encoding="utf-8")
    print(f"输出文件已创建: {output_path.resolve()}")

    entries: List[TranscriptEntry] = []

    while True:
        title = ask_title()
        raw_block = ask_transcript_block()
        content = parse_transcript(raw_block)

        if not content:
            print("检测到空内容（可能未粘贴有效 transcript），本段已跳过。")
        else:
            entry = TranscriptEntry(title=title, content=content)
            entries.append(entry)
            append_entry(output_path, entry)
            print(f"已保存段落: {title}")

        if not ask_continue():
            break

    write_summary(output_path, entries)
    print(f"\n已完成，Markdown 文件: {output_path.resolve()}")


if __name__ == "__main__":
    main()
