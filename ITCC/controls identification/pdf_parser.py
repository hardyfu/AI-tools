import sys
import logging
import re
import unicodedata
from pathlib import Path
import numpy as np
import pdfplumber
import tkinter as tk
from tkinter import filedialog
try:
    from rapidocr_onnxruntime import RapidOCR
except ImportError:
    RapidOCR = None

# 屏蔽 pdfminer 的警告信息
logging.getLogger("pdfminer").setLevel(logging.ERROR)

# ================= 配置区域 =================
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)
OCR_TRIGGER_THRESHOLD = 50
DEFAULT_SECTION_PATTERN = re.compile(r"^第[一二三四五六七八九十百零〇两0-9]{1,10}节[:：\s]*")
DEFAULT_ARTICLE_PATTERN = re.compile(r"^第[一二三四五六七八九十百零〇两0-9]{1,10}条[:：\s]*")
DEFAULT_CHAPTER_PATTERN = re.compile(r"^第[一二三四五六七八九十百零〇两0-9]{1,10}章[:：\s]*")
DEFAULT_ITEM_PATTERN = re.compile(r"^（[一二三四五六七八九十百零〇两0-9]{1,3}）")
CHINESE_CHAR_PATTERN = re.compile(r"[\u4e00-\u9fa5]")
TOC_NOISE_PATTERNS = [
    re.compile(r"^\s*目录\s*$"),
    re.compile(r"^\s*来源[:：]"),
    re.compile(r"^\s*中华.*人民.*共和国.*法"),
]
PAGE_NUMBER_PATTERNS = [
    re.compile(r"^\s*\d+\s*/\s*\d+\s*$"),
    re.compile(r"^\s*[-－—]\s*\d+\s*[-－—]\s*$"),
    re.compile(r"^\s*\d+\s*$"),
]
ENTERPRISE_SUBJECT_KEYWORDS = (
    "网络运营者", "关键信息基础设施的运营者", "关键信息基础设施运营者",
    "数据处理者", "重要数据的处理者", "个人信息处理者", "服务提供者",
    "电子信息发送服务提供者", "应用软件下载服务提供者",
    "从事数据交易中介服务的机构", "机构提供服务"
)
AUTHORITY_SUBJECT_KEYWORDS = (
    "国家", "国务院", "人民政府", "主管部门", "网信部门",
    "国家网信部门", "公安机关", "国家安全机关", "行业组织",
    "国家机关", "中央国家安全领导机构", "有关部门"
)
PARSER_PROFILES = {
    "中华人民共和国网络安全法": {
        "trim_mixed_toc": True,
        "keep_section_title": True,
        "chapter_pattern": DEFAULT_CHAPTER_PATTERN,
        "section_pattern": DEFAULT_SECTION_PATTERN,
        "article_pattern": DEFAULT_ARTICLE_PATTERN,
        "item_pattern": DEFAULT_ITEM_PATTERN,
    },
    "中华人民共和国数据安全法": {
        "trim_mixed_toc": False,
        "keep_section_title": False,
        "chapter_pattern": DEFAULT_CHAPTER_PATTERN,
        "section_pattern": DEFAULT_SECTION_PATTERN,
        "article_pattern": DEFAULT_ARTICLE_PATTERN,
        "item_pattern": DEFAULT_ITEM_PATTERN,
        "normalize_heading_colon": True,
    },
    "中华人民共和国个人信息保护法": {
        "trim_mixed_toc": True,
        "keep_section_title": True,
        "chapter_pattern": DEFAULT_CHAPTER_PATTERN,
        "section_pattern": DEFAULT_SECTION_PATTERN,
        "article_pattern": DEFAULT_ARTICLE_PATTERN,
        "item_pattern": DEFAULT_ITEM_PATTERN,
        "mixed_toc_strategy": "last_heading",
    },
    "default": {
        "trim_mixed_toc": False,
        "keep_section_title": True,
        "chapter_pattern": DEFAULT_CHAPTER_PATTERN,
        "section_pattern": DEFAULT_SECTION_PATTERN,
        "article_pattern": DEFAULT_ARTICLE_PATTERN,
        "item_pattern": DEFAULT_ITEM_PATTERN,
        "normalize_heading_colon": False,
    },
}


# ===========================================

class PDFParser:
    def __init__(self):
        self.ocr_engine = None
        if RapidOCR is None:
            logger.warning("RapidOCR 未安装，低文本页将跳过 OCR。")
            return

        try:
            self.ocr_engine = RapidOCR(det_use_gpu=False, cls_use_gpu=False, rec_use_gpu=False)
        except Exception as exc:
            logger.error(f"初始化 OCR 引擎失败: {exc}")
            self.ocr_engine = None

    def _process_page_with_ocr(self, page_obj, page_num):
        """OCR 识别"""
        if self.ocr_engine is None:
            logger.warning(f"  -> 第 {page_num} 页未执行 OCR: OCR 引擎不可用")
            return ""

        try:
            pil_image = page_obj.to_image(resolution=300).original
            img_np = np.array(pil_image)
            ocr_result, _ = self.ocr_engine(img_np)
            if not ocr_result:
                logger.info(f"  -> 第 {page_num} 页 OCR 未识别到文本")
                return ""
            return "\n".join([item[1] for item in ocr_result])
        except Exception as exc:
            logger.warning(f"  -> 第 {page_num} 页 OCR 失败: {exc}")
            return ""

    def _is_front_matter_or_toc(self, line):
        line = line.strip()
        if not line:
            return False
        return any(pattern.search(line) for pattern in TOC_NOISE_PATTERNS)

    def _normalize_text(self, text):
        return unicodedata.normalize("NFKC", text)

    def _detect_profile(self, pdf_path):
        pdf_name = Path(pdf_path).stem
        for keyword, profile in PARSER_PROFILES.items():
            if keyword != "default" and keyword in pdf_name:
                logger.info(f"使用定制解析配置: {keyword}")
                return profile
        logger.info("使用默认解析配置")
        return PARSER_PROFILES["default"]

    def _extract_article_ref(self, article_text, profile):
        article_pattern = self._article_pattern(profile)
        for line in article_text.split("\n"):
            stripped = line.strip()
            match = article_pattern.match(stripped)
            if match:
                return re.sub(r"[:：\s]+$", "", match.group(0)).strip()
        return ""

    def _classify_subject_type(self, article_text):
        normalized = unicodedata.normalize("NFKC", article_text)
        has_enterprise = any(keyword in normalized for keyword in ENTERPRISE_SUBJECT_KEYWORDS)
        has_authority = any(keyword in normalized for keyword in AUTHORITY_SUBJECT_KEYWORDS)
        if has_enterprise and has_authority:
            return "mixed"
        if has_enterprise:
            return "enterprise"
        if has_authority:
            return "authority"
        return "generic"

    def _chapter_pattern(self, profile):
        return profile.get("chapter_pattern", DEFAULT_CHAPTER_PATTERN)

    def _section_pattern(self, profile):
        return profile.get("section_pattern", DEFAULT_SECTION_PATTERN)

    def _article_pattern(self, profile):
        return profile.get("article_pattern", DEFAULT_ARTICLE_PATTERN)

    def _item_pattern(self, profile):
        return profile.get("item_pattern", DEFAULT_ITEM_PATTERN)

    def _is_page_noise_line(self, line):
        if not line:
            return True
        if any(pattern.match(line) for pattern in PAGE_NUMBER_PATTERNS):
            return True
        return False

    def _looks_like_toc_page(self, lines, profile):
        meaningful_lines = [line for line in lines if line and not self._is_page_noise_line(line)]
        if not meaningful_lines:
            return False

        chapter_pattern = self._chapter_pattern(profile)
        section_pattern = self._section_pattern(profile)
        article_pattern = self._article_pattern(profile)

        chapter_hits = sum(1 for line in meaningful_lines if chapter_pattern.match(line))
        section_hits = sum(1 for line in meaningful_lines if section_pattern.match(line))
        article_hits = sum(1 for line in meaningful_lines if article_pattern.match(line))
        has_catalog = any(re.match(r"^\s*目\s*录\s*$", line) for line in meaningful_lines)

        if has_catalog and article_hits == 0:
            return True
        if article_hits == 0 and chapter_hits >= 3:
            return True
        if article_hits == 0 and chapter_hits >= 1 and section_hits >= 2:
            return True
        return False

    def _trim_mixed_toc_page(self, lines, profile):
        if not profile.get("trim_mixed_toc", False):
            return lines

        chapter_pattern = self._chapter_pattern(profile)
        section_pattern = self._section_pattern(profile)
        article_pattern = self._article_pattern(profile)
        strategy = profile.get("mixed_toc_strategy", "first_article")

        meaningful_lines = [line for line in lines if line]
        has_catalog = any(re.match(r"^\s*目\s*录\s*$", line) for line in meaningful_lines)
        article_positions = [
            idx for idx, line in enumerate(lines) if article_pattern.match(line)
        ]
        if not has_catalog:
            return lines

        if strategy == "last_heading" and not article_positions:
            heading_positions = [
                idx for idx, line in enumerate(lines)
                if chapter_pattern.match(line) or section_pattern.match(line)
            ]
            if heading_positions:
                trimmed = lines[heading_positions[-1]:]
                logger.info("   -> 🧹 识别为目录+标题混排页，已裁掉前置目录内容")
                return trimmed
            return lines

        if not article_positions:
            return lines

        first_article_idx = article_positions[0]
        start_idx = first_article_idx
        for idx in range(first_article_idx - 1, -1, -1):
            if chapter_pattern.match(lines[idx]) or section_pattern.match(lines[idx]):
                start_idx = idx
                break

        trimmed = lines[start_idx:]
        logger.info("   -> 🧹 识别为目录+正文混排页，已裁掉前置目录内容")
        return trimmed

    def _clean_wrapped_line(self, line):
        return re.sub(r"\s+", " ", line).strip()

    def _normalize_heading_line(self, line, profile):
        if not profile.get("normalize_heading_colon", False):
            return line

        line = re.sub(
            r"^(第[一二三四五六七八九十百零〇两0-9]{1,10}章)[:：]\s*",
            r"\1 ",
            line,
        )
        line = re.sub(
            r"^(第[一二三四五六七八九十百零〇两0-9]{1,10}节)[:：]\s*",
            r"\1 ",
            line,
        )
        line = re.sub(
            r"^(第[一二三四五六七八九十百零〇两0-9]{1,10}条)[:：]\s*",
            r"\1 ",
            line,
        )
        return line.strip()

    def _is_new_structure_line(self, line, profile):
        chapter_pattern = self._chapter_pattern(profile)
        section_pattern = self._section_pattern(profile)
        article_pattern = self._article_pattern(profile)
        item_pattern = self._item_pattern(profile)
        return bool(
            chapter_pattern.match(line)
            or section_pattern.match(line)
            or article_pattern.match(line)
            or item_pattern.match(line)
        )

    def _should_merge_line(self, current_buffer, next_line, profile):
        if not current_buffer:
            return False
        if self._is_new_structure_line(next_line, profile):
            return False
        if current_buffer.endswith(("。", "；", "：", "?", "？", "!", "！")):
            return False
        return True

    def _clean_page_noise(self, text, profile):
        """【增强版】单页噪声清洗函数"""
        if not text:
            return ""

        normalized_text = self._normalize_text(text)
        lines = [self._clean_wrapped_line(line) for line in normalized_text.split('\n')]
        lines = [self._normalize_heading_line(line, profile) for line in lines]

        lines = self._trim_mixed_toc_page(lines, profile)

        if self._looks_like_toc_page(lines, profile):
            logger.info("   -> 🧹 整页识别为目录/封面页，已跳过")
            return ""

        cleaned_lines = []

        for line in lines:
            line_stripped = line.strip()
            if self._is_page_noise_line(line_stripped):
                logger.info(f"   -> 🧹 已移除页脚: [{line_stripped}]")
                continue
            if self._is_front_matter_or_toc(line_stripped):
                logger.info(f"   -> 🧹 已移除目录/封面噪声: [{line_stripped}]")
                continue
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def parse_legal_articles(self, full_text, profile):
        """【层级化解析版】"""
        logger.info("正在进行层级化语义分段 (Chapter -> Articles)...")

        raw_lines = full_text.split('\n')
        structured_data = []
        chapter_pattern = self._chapter_pattern(profile)
        section_pattern = self._section_pattern(profile)
        article_pattern = self._article_pattern(profile)
        item_pattern = self._item_pattern(profile)

        current_chapter_title = "未归类章节"
        current_articles = []
        current_article_meta = []
        current_article_buffer = ""
        current_section_title = ""

        def flush_article():
            nonlocal current_article_buffer
            if current_article_buffer:
                article_text = current_article_buffer.strip()
                current_articles.append(article_text)
                current_article_meta.append({
                    "article_ref": self._extract_article_ref(article_text, profile),
                    "subject_type": self._classify_subject_type(article_text),
                    "paragraph_count": len([line for line in article_text.split("\n") if line.strip()]),
                    "has_section_context": bool(current_section_title),
                })
                current_article_buffer = ""

        def flush_chapter(new_title):
            nonlocal current_chapter_title, current_articles, current_article_meta, current_section_title
            flush_article()
            if current_articles:
                structured_data.append({
                    "chapter": current_chapter_title,
                    "articles": current_articles,
                    "article_meta": current_article_meta,
                })
            current_chapter_title = new_title
            current_articles = []
            current_article_meta = []
            current_section_title = ""

        def build_article_header(line):
            if profile.get("keep_section_title", True) and current_section_title:
                return f"{current_section_title}\n{line}"
            return line

        for line in raw_lines:
            line = line.strip()
            if not line:
                continue

            if chapter_pattern.match(line):
                flush_chapter(line)
                continue

            if section_pattern.match(line):
                flush_article()
                current_section_title = line
                logger.info(f"   -> 识别节标题: [{line}]")
                continue

            if article_pattern.match(line):
                flush_article()
                current_article_buffer = build_article_header(line)
            else:
                if current_article_buffer:
                    if item_pattern.match(line):
                        current_article_buffer += "\n" + line
                    elif self._should_merge_line(current_article_buffer, line, profile):
                        current_article_buffer += line
                    else:
                        current_article_buffer += "\n" + line

        flush_chapter("END")
        logger.info(f"层级解析完成：共识别出 {len(structured_data)} 个章节。")
        return structured_data

    def extract_content(self, pdf_path):
        print(f"处理文件: {pdf_path}")
        raw_pages_text = []
        profile = self._detect_profile(pdf_path)

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    raw_text = page.extract_text()
                    if not raw_text or len(raw_text.strip()) < OCR_TRIGGER_THRESHOLD:
                        print(f"  -> 第 {i + 1} 页 OCR识别中...")
                        text = self._process_page_with_ocr(page, i + 1)
                    else:
                        text = raw_text

                    if text:
                        cleaned_text = self._clean_page_noise(text, profile)
                        raw_pages_text.append(cleaned_text)

            full_text = "\n".join(raw_pages_text)
            return self.parse_legal_articles(full_text, profile)

        except Exception as e:
            print(f"错误: {e}")
            return []


# ================= 补全：辅助函数 (Main.py 需要用到它！) =================
def select_pdf_file():
    """弹出系统文件选择框"""
    try:
        root = tk.Tk()
        root.withdraw()
        # 这一步是为了防止弹窗不置顶被挡住
        root.lift()
        root.attributes('-topmost', True)

        file_path = filedialog.askopenfilename(
            title="请选择法律法规 PDF 文件",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        root.destroy()
        return file_path
    except Exception as e:
        print(f"无法打开文件选择框: {e}")
        return None


# ================= 测试入口 =================
def main():
    # 这里我们直接调用上面定义好的 select_pdf_file，保持逻辑一致
    pdf_path = select_pdf_file()
    if not pdf_path: return

    parser = PDFParser()
    chapters_data = parser.extract_content(pdf_path)

    if chapters_data:
        output_file = "ocr_result_debug.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            for chapter_info in chapters_data:
                f.write("\n" + "=" * 80 + "\n")
                f.write(f"{chapter_info['chapter']}\n")
                f.write("=" * 80 + "\n")
                for article in chapter_info['articles']:
                    f.write(article + "\n")
                    f.write("-" * 40 + "\n")

        print(f"\n✅ 处理完成！共识别出 {len(chapters_data)} 个章节。")
        print(f"请检查 {output_file}。")
    else:
        print("❌ 解析失败。")


if __name__ == "__main__":
    main()
