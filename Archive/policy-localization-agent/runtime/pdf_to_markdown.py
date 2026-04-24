import argparse
import re
from pathlib import Path


def extract_text_with_pypdf(pdf_path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(f"## Page {index}\n\n{text}")
    return "\n\n".join(pages).strip()


def extract_text_with_pdfplumber(pdf_path: Path) -> str:
    import pdfplumber

    pages = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                pages.append(f"## Page {index}\n\n{text}")
    return "\n\n".join(pages).strip()


def normalize_extracted_text(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    cleaned: list[str] = []
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            merged = ""
            for part in paragraph:
                piece = part.strip()
                if not piece:
                    continue
                if merged.endswith("-") and piece[:1].islower():
                    merged = merged[:-1] + piece
                elif merged:
                    merged = f"{merged} {piece}"
                else:
                    merged = piece
            if merged:
                cleaned.append(merged)
            paragraph = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            cleaned.append("")
            continue
        if re.fullmatch(r"[-_=\s]{4,}", line):
            continue
        if line.startswith("## "):
            flush_paragraph()
            cleaned.append(line)
            continue
        if re.match(r"^([-*•]|\d+\.)\s+", line):
            flush_paragraph()
            cleaned.append(line.replace("•", "-"))
            continue
        paragraph.append(line)

    flush_paragraph()

    normalized: list[str] = []
    previous_blank = False
    for line in cleaned:
        if not line:
            if not previous_blank:
                normalized.append("")
            previous_blank = True
            continue
        normalized.append(line)
        previous_blank = False
    return "\n".join(normalized).strip()


def convert_pdf_to_markdown(pdf_path: Path, markdown_path: Path) -> None:
    text = ""
    last_error: Exception | None = None
    for extractor in (extract_text_with_pypdf, extract_text_with_pdfplumber):
        try:
            text = extractor(pdf_path)
            if text:
                text = normalize_extracted_text(text)
                break
        except Exception as exc:
            last_error = exc
    if not text:
        if last_error:
            raise RuntimeError(f"Failed to extract text from {pdf_path}: {last_error}") from last_error
        raise RuntimeError(f"Failed to extract text from {pdf_path}")

    title = pdf_path.stem.replace("_", " ").replace("-", " ").strip() or "Converted Policy"
    content = f"# {title}\n\n{text}\n"
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert a PDF policy document to Markdown.")
    parser.add_argument("--input", required=True, dest="input_path", help="Input PDF file path")
    parser.add_argument("--output", required=True, dest="output_path", help="Output Markdown file path")
    args = parser.parse_args()

    pdf_path = Path(args.input_path)
    markdown_path = Path(args.output_path)
    if not pdf_path.exists():
        print(f"ERROR: Missing input PDF: {pdf_path}")
        return 1

    try:
        convert_pdf_to_markdown(pdf_path, markdown_path)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"Wrote Markdown to {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
