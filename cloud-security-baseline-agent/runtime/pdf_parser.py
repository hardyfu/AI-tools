import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

try:  # pragma: no cover - optional dependency
    import pdfplumber
except ImportError:  # pragma: no cover - optional dependency
    pdfplumber = None


PAGE_NUMBER_PATTERNS = [
    re.compile(r"^\s*\d+\s*/\s*\d+\s*$"),
    re.compile(r"^\s*[-－—]\s*\d+\s*[-－—]\s*$"),
    re.compile(r"^\s*\d+\s*$"),
    re.compile(r"^\s*Page\s+\d+\s*$", re.IGNORECASE),
]
TOC_NOISE_PATTERNS = [
    re.compile(r"^\s*contents\s*$", re.IGNORECASE),
    re.compile(r"^\s*table of contents\s*$", re.IGNORECASE),
    re.compile(r"^\s*recommendation definitions\s*$", re.IGNORECASE),
]


class PDFParser:
    def __init__(self):
        self._pdfplumber = pdfplumber

    def _normalize_line(self, line: str) -> str:
        line = unicodedata.normalize("NFKC", line)
        line = re.sub(r"\s+", " ", line).strip()
        line = re.sub(r"\s+\.\.+\s*\d+\s*$", "", line)
        line = re.sub(r"\s+\.\s*\d+\s*$", "", line)
        line = re.sub(r"\s+\.\.\s*\d+\s*$", "", line)
        return line.strip()

    def _is_noise_line(self, line: str) -> bool:
        if not line:
            return True
        if any(pattern.match(line) for pattern in PAGE_NUMBER_PATTERNS):
            return True
        if any(pattern.match(line) for pattern in TOC_NOISE_PATTERNS):
            return True
        return False

    def _clean_page_text(self, text: str) -> str:
        cleaned_lines: list[str] = []
        for raw_line in unicodedata.normalize("NFKC", text).splitlines():
            line = self._normalize_line(raw_line.replace("\f", " "))
            if self._is_noise_line(line):
                continue
            cleaned_lines.append(line)
        return "\n".join(line for line in cleaned_lines if line)

    def _extract_with_pdfplumber(self, source: Path) -> str:
        if self._pdfplumber is None:
            return ""
        pages: list[str] = []
        with self._pdfplumber.open(source) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                cleaned = self._clean_page_text(page_text)
                if cleaned:
                    pages.append(cleaned)
        return "\n".join(pages).strip()

    def _extract_with_pdftotext(self, source: Path) -> str:
        pdftotext_bin = _resolve_binary("pdftotext")
        result = subprocess.run(
            [pdftotext_bin, "-layout", str(source), "-"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return self._clean_page_text(result.stdout.replace("\r\n", "\n").replace("\r", "\n")).strip()

    def extract_text(self, source: Path) -> str:
        if source.suffix.lower() != ".pdf":
            return source.read_text(encoding="utf-8")
        text = self._extract_with_pdfplumber(source)
        if text:
            return text + "\n"
        text = self._extract_with_pdftotext(source)
        return text + "\n" if text else ""


def _resolve_binary(name: str) -> str:
    resolved = shutil.which(name)
    if resolved:
        return resolved
    candidates = [
        f"/opt/homebrew/bin/{name}",
        f"/usr/local/bin/{name}",
        f"/opt/homebrew/sbin/{name}",
        f"/usr/bin/{name}",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError(f"Required binary not found: {name}")
