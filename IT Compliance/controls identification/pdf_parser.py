import sys
import time
import logging
import re
import numpy as np
import pdfplumber
import tkinter as tk
from tkinter import filedialog
from rapidocr_onnxruntime import RapidOCR

# 屏蔽 pdfminer 的警告信息
logging.getLogger("pdfminer").setLevel(logging.ERROR)

# ================= 配置区域 =================
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)
OCR_TRIGGER_THRESHOLD = 50


# ===========================================

class PDFParser:
    def __init__(self):
        try:
            self.ocr_engine = RapidOCR(det_use_gpu=False, cls_use_gpu=False, rec_use_gpu=False)
        except:
            sys.exit(1)

    def _process_page_with_ocr(self, page_obj, page_num):
        """OCR 识别"""
        try:
            pil_image = page_obj.to_image(resolution=300).original
            img_np = np.array(pil_image)
            ocr_result, _ = self.ocr_engine(img_np)
            if not ocr_result: return ""
            return "\n".join([item[1] for item in ocr_result])
        except:
            return ""

    def _clean_page_noise(self, text):
        """【增强版】单页噪声清洗函数"""
        if not text:
            return ""

        lines = text.split('\n')
        cleaned_lines = []

        # 模式1: "1 / 9"
        footer_pattern_1 = re.compile(r"^\s*\d+\s*/\s*\d+\s*$")
        # 模式2: "- 1 -"
        footer_pattern_2 = re.compile(r"^\s*[-－—]\s*\d+\s*[-－—]\s*$")

        for line in lines:
            line_stripped = line.strip()
            if footer_pattern_1.match(line_stripped):
                logger.info(f"   -> 🧹 已移除页脚: [{line_stripped}]")
                continue
            if footer_pattern_2.match(line_stripped):
                logger.info(f"   -> 🧹 已移除页脚: [{line_stripped}]")
                continue
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def parse_legal_articles(self, full_text):
        """【层级化解析版】"""
        logger.info("正在进行层级化语义分段 (Chapter -> Articles)...")

        raw_lines = full_text.split('\n')
        structured_data = []

        current_chapter_title = "未归类章节"
        current_articles = []
        current_article_buffer = ""

        # 正则定义
        article_pattern = re.compile(r"第.{1,10}条[:：\s]?")
        chapter_pattern = re.compile(r"第.{1,10}章[:：\s]?")
        chinese_char_pattern = re.compile(r"[\u4e00-\u9fa5]")

        def flush_article():
            nonlocal current_article_buffer
            if current_article_buffer:
                current_articles.append(current_article_buffer)
                current_article_buffer = ""

        def flush_chapter(new_title):
            nonlocal current_chapter_title, current_articles
            flush_article()
            if current_articles or current_chapter_title != "未归类章节":
                structured_data.append({
                    "chapter": current_chapter_title,
                    "articles": current_articles
                })
            current_chapter_title = new_title
            current_articles = []

        for line in raw_lines:
            line = line.strip()
            if not line: continue

            # 1. 章节检测
            is_chapter = False
            match_chapter = chapter_pattern.search(line)
            if match_chapter:
                prefix = line[:match_chapter.start()]
                if not chinese_char_pattern.search(prefix):
                    is_chapter = True

            if is_chapter:
                flush_chapter(line)
                continue

            # 2. 条款检测
            is_article = False
            match_article = article_pattern.search(line)
            if match_article:
                prefix = line[:match_article.start()]
                if not chinese_char_pattern.search(prefix):
                    is_article = True

            if is_article:
                flush_article()
                current_article_buffer = line
            else:
                # 3. 正文
                if current_article_buffer:
                    current_article_buffer += line
                else:
                    current_article_buffer = line

        flush_chapter("END")
        logger.info(f"层级解析完成：共识别出 {len(structured_data)} 个章节。")
        return structured_data

    def extract_content(self, pdf_path):
        print(f"处理文件: {pdf_path}")
        raw_pages_text = []

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
                        cleaned_text = self._clean_page_noise(text)
                        raw_pages_text.append(cleaned_text)

            full_text = "\n".join(raw_pages_text)
            return self.parse_legal_articles(full_text)

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
