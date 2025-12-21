import os
import sys
import json
import re
import asyncio
import smtplib
from datetime import datetime
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import List, Dict, Any, Optional

import requests
import markdown
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from urllib.parse import urljoin
from markdown_pdf import MarkdownPdf, Section

# 导入自定义模块
# 假设 llm.py, llm_text.py, formatter.py 存在
from llm import llm_call as llm_call_json
from llm_text import llm_call_text
from formatter import format_to_markdown, validate_data

# 【加载配置】
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

# --- 配置从环境变量获取 ---
SOURCE_URL = os.getenv('AI_NEWS_URL')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '.', 'daily_report')

# 邮件配置
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = os.getenv('SMTP_PORT')
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

# 【修改点 1】: 获取多个收件人地址，并将其转换为列表
RECIPIENT_EMAILS_STR = os.getenv('RECIPIENT_EMAILS')
RECIPIENT_EMAILS = [email.strip() for email in RECIPIENT_EMAILS_STR.split(',') if
                    email.strip()] if RECIPIENT_EMAILS_STR else []

SENDER_NICKNAME = os.getenv('SENDER_NICKNAME', 'AI Daily Reporter')


# -----------------------------

# --- 核心辅助函数 ---

def extract_and_clean_html(html: str) -> str:
    """提取并清理 HTML 内容，移除 <script> 标签并提取 <body> 内容。"""
    soup = BeautifulSoup(html, 'html.parser')
    for script in soup.find_all('script'):
        script.decompose()
    body_tag = soup.find('body')
    if body_tag:
        print('✓ 已提取 body 内容并移除 script 标签')
        return str(body_tag.decode_contents())
    else:
        print('⚠ 未找到 body 标签，使用完整 HTML')
        return html


def rewrite_relative_urls(html: str, base_url: str) -> str:
    """
    使用 BeautifulSoup 查找所有带有相对路径的链接，并将其转换为绝对路径。
    """
    soup = BeautifulSoup(html, 'html.parser')

    # 查找所有 a 标签并重写其 href 属性
    for tag in soup.find_all('a', href=True):
        original_url = tag['href']

        # 仅处理以 '/' 开头但不是 '//' 开头的相对路径
        if original_url.startswith('/') and not original_url.startswith('//'):
            absolute_url = urljoin(base_url, original_url)
            tag['href'] = absolute_url

    return str(soup)


def get_date_file_name() -> str:
    """获取当前日期的文件名 (YYYY-MM-DD.md)。"""
    if os.getenv('DATE'):
        return f"{os.getenv('DATE')}.md"
    now = datetime.now()
    return now.strftime('%Y-%m-%d.md')


def ensure_directory_exists(dir_path: str):
    """确保目录存在。"""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
        print(f'✓ 创建目录: {dir_path}')


def extract_json(content: str) -> object or None:
    """从 LLM 返回的内容中提取 JSON。"""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content) or \
                     re.search(r'```\s*([\s\S]*?)\s*```', content) or \
                     re.search(r'\{[\s\S]*\}', content)

        if json_match:
            json_str = json_match.group(1) if len(json_match.groups()) >= 1 and json_match.group(
                1) else json_match.group(0)
            json_str = json_str.strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e2:
                print(f'❌ JSON 解析失败 (提取后): {e2}', file=sys.stderr)
                return None
        return None


def update_home_json(new_entry: dict):
    """更新 dailyData.json 文件。"""
    home_json_path = os.path.join(os.path.dirname(__file__), '.', 'dailyData.json')
    home_data = []

    if os.path.exists(home_json_path):
        with open(home_json_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if content:
                try:
                    home_data = json.loads(content)
                except json.JSONDecodeError:
                    print("⚠ dailyData.json 文件格式错误，将重新创建。")
                    home_data = []

    existing_index = next((i for i, item in enumerate(home_data) if item.get('date') == new_entry.get('date')), -1)

    if existing_index != -1:
        home_data[existing_index] = new_entry
        print(f'✓ 更新已存在的日期条目: {new_entry.get("date")}')
    else:
        home_data.insert(0, new_entry)
        print(f'✓ 添加新条目: {new_entry.get("date")}')

    with open(home_json_path, 'w', encoding='utf-8') as f:
        json.dump(home_data, f, ensure_ascii=False, indent=4)


# 【修改点 2】: 接收 to_addrs 列表，并使用列表发送邮件
async def send_daily_report_email(subject: str, markdown_content: str, to_addrs: List[str],
                                  attachment_path: os.PathLike = None):
    """
    发送 AI 日报邮件，同时包含纯文本、HTML 正文和可选的 PDF 附件。
    """
    if not (SMTP_SERVER and SMTP_PORT and EMAIL_USER and EMAIL_PASSWORD):
        print("⚠ 邮件配置不完整，跳过邮件发送。", file=sys.stderr)
        return

    if not to_addrs:
        print("⚠ 收件人列表为空，跳过邮件发送。", file=sys.stderr)
        return

    try:
        clean_port = ''.join(filter(str.isdigit, SMTP_PORT.strip()))
        if not clean_port:
            raise ValueError("SMTP_PORT 无法解析为有效数字。")

        html_content = markdown.markdown(markdown_content, extensions=['extra'])

        msg = MIMEMultipart('mixed')

        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = formataddr((str(Header(SENDER_NICKNAME, 'utf-8')), EMAIL_USER))
        # 将收件人列表连接成逗号分隔的字符串，用于邮件头部 To 字段
        msg['To'] = ", ".join(to_addrs)

        msg_alternative = MIMEMultipart('alternative')
        part_text = MIMEText(markdown_content, 'plain', 'utf-8')
        part_html = MIMEText(html_content, 'html', 'utf-8')
        msg_alternative.attach(part_text)
        msg_alternative.attach(part_html)
        msg.attach(msg_alternative)

        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())

                encoders.encode_base64(part)

                file_name = os.path.basename(attachment_path)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{file_name}"',
                )
                msg.attach(part)
                print(f'✓ 已附加 PDF 文件: {file_name}')

        print('⚙️  尝试发送邮件...')

        server = smtplib.SMTP(SMTP_SERVER, int(clean_port), timeout=10)
        server.ehlo()
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)

        # 核心修改: 使用 to_addrs 列表作为 sendmail 的第二个参数
        server.sendmail(EMAIL_USER, to_addrs, msg.as_string())
        server.quit()

        print(f'✓ 邮件发送成功！已发送至 {", ".join(to_addrs)}')

    except Exception as e:
        print(f'❌ 邮件发送失败: {e}', file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)


# --- 主程序入口 ---

async def main():
    """主函数"""
    if not SOURCE_URL:
        print("❌ 错误: 环境变量 AI_NEWS_URL 未设置。请在 .env 文件中配置。", file=sys.stderr)
        sys.exit(1)

    try:
        print('========================================')
        print('🚀 开始生成 AI 日报...')
        print('========================================\n')

        # 1. 获取 HTML 内容
        print('📥 正在获取内容...')
        response = requests.get(SOURCE_URL, timeout=15)
        response.raise_for_status()
        html = response.text
        print(f'✓ 获取成功，内容长度: {len(html)} 字符\n')
        with open('html_original.html', 'w', encoding='utf-8') as f:
            f.write(html)

        # 2. 提取并清理 HTML
        print('🧹 正在清理 HTML...')
        html = extract_and_clean_html(html)

        # 2.5. 重写相对链接为绝对链接
        base_url_fixed = SOURCE_URL
        # 确保 SOURCE_URL 以斜杠结尾，以保证 urljoin 正确性
        if base_url_fixed and not base_url_fixed.endswith('/'):
            base_url_fixed += '/'

        print(f'🔗 正在重写相对链接，基准URL: {base_url_fixed}')
        html = rewrite_relative_urls(html, base_url_fixed)
        print(f'✓ 清理和链接重写完成，处理后长度: {len(html)} 字符\n')
        with open('html_final.html', 'w', encoding='utf-8') as f:
            f.write(html)

        # 3. 读取提示词 (prompt02.md)
        print('📝 正在读取提示词 (prompt02.md)...')
        prompt_path = os.path.join(os.path.dirname(__file__), 'prompt02.md')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt = f.read()
        print('✓ 提示词读取成功\n')

        # 4. 调用 LLM 生成结构化数据 (LLM 此时提取到的已经是绝对链接！)
        print('🤖 正在调用 LLM 生成结构化数据...')
        llm_response = await llm_call_json(prompt + html)
        print(f'✓ LLM 响应成功，长度: {len(llm_response)} 字符\n')
        with open('llm.md', 'w', encoding='utf-8') as f:
            f.write(llm_response)

        # 5. 解析 JSON 数据
        print('📊 正在解析 JSON 数据...')
        json_data = extract_json(llm_response)

        if not json_data:
            raise Exception('无法解析 LLM 返回的 JSON 数据')

        if not validate_data(json_data):
            raise Exception('JSON 数据结构验证失败')

        print(f'✓ JSON 数据解析成功，包含 {len(json_data)} 个分类\n')

        # 6. 格式化为 Markdown (不再需要 base_url 参数)
        print('📝 正在格式化为 Markdown...')
        markdown_output = format_to_markdown(json_data)
        print(f'✓ Markdown 格式化成功，长度: {len(markdown_output)} 字符\n')

        # 7. 保存日报到文件
        print('💾 正在保存日报文件...')
        ensure_directory_exists(OUTPUT_DIR)
        file_name = get_date_file_name()
        output_path = os.path.join(OUTPUT_DIR, file_name)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_output)
        print(f'✓ 日报文件已保存: {output_path}\n')

        # 8. 生成标题和标签 (prompt2.md)
        print('🏷️  正在生成标题和标签 (prompt2)...')
        prompt2_path = os.path.join(os.path.dirname(__file__), 'prompt2.md')
        with open(prompt2_path, 'r', encoding='utf-8') as f:
            prompt2 = f.read()

        title_and_tags_response = await llm_call_json(markdown_output + '\n\n' + prompt2)
        print('✓ 标题和标签生成成功\n')

        # 9. 解析并更新 dailyData.json
        print('📋 正在更新 dailyData.json...')
        title_and_tags = extract_json(title_and_tags_response)

        report_title = f"AI 日报 {file_name.replace('.md', '')}"

        if title_and_tags and title_and_tags.get('title') and title_and_tags.get('tags'):
            report_title = title_and_tags.get('title')
            title_and_tags['date'] = file_name.replace('.md', '')
            update_home_json(title_and_tags)
            print('✓ dailyData.json 更新成功')
            print(f'    标题: {report_title}')
            print(f'    标签: {", ".join(title_and_tags["tags"])}\n')
        else:
            print('⚠ 无法解析标题和标签，跳过 dailyData.json 更新\n')

        # --- 9.5. 生成 PDF 附件 ---
        print('📄 正在生成 PDF 附件...')
        pdf_file_name = file_name.replace('.md', '.pdf')
        pdf_output_path = os.path.join(OUTPUT_DIR, pdf_file_name)

        attachment_to_send = None
        try:
            pdf = MarkdownPdf()
            pdf.meta["title"] = report_title
            pdf.meta["author"] = SENDER_NICKNAME

            pdf.add_section(Section(markdown_output, toc=True))

            pdf.save(pdf_output_path)
            print(f'✓ PDF 文件已保存: {pdf_output_path}')
            attachment_to_send = pdf_output_path
        except Exception as e:
            print(f'❌ PDF 生成失败: {e}，将不发送附件。', file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)

        # --- 10. 生成邮件摘要 (prompt3.md) ---
        print('✉️  正在读取提示词 (prompt3.md) 并生成邮件摘要...')
        prompt3_path = os.path.join(os.path.dirname(__file__), 'prompt3.md')

        email_content = markdown_output
        email_subject = report_title

        email_date = get_date_file_name().replace('.md', '')

        if os.path.exists(prompt3_path):
            with open(prompt3_path, 'r', encoding='utf-8') as f:
                prompt3 = f.read()

            email_summary = await llm_call_text(markdown_output + '\n\n' + prompt3)

            email_content = email_summary
            email_subject = f"[{email_date} 摘要] {report_title}"

            print(f'✓ 邮件摘要生成成功，长度: {len(email_content)} 字符\n')
        else:
            print('⚠ 缺少 prompt3.md 文件，邮件正文将使用完整日报内容。')

        # --- 11. 发送邮件 ---
        # 【修改点 3】: 传入 RECIPIENT_EMAILS 列表
        if RECIPIENT_EMAILS:
            print('📧 正在发送日报邮件...')
            await send_daily_report_email(
                email_subject,
                email_content,
                RECIPIENT_EMAILS,  # 传入收件人列表
                attachment_path=attachment_to_send
            )
        else:
            print('⚠ 邮件收件人未设置，跳过邮件发送。')

        print('========================================')
        print('✅ AI 日报生成和发送完成！')
        print('========================================')

    except Exception as error:
        print(f'\n❌ 错误: {error}', file=sys.stderr)
        import traceback
        print('\n堆栈信息:')
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())