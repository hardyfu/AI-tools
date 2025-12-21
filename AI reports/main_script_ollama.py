import os
import sys
import json
import re
import asyncio
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 新增的邮件和 Markdown 模块
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from email.mime.multipart import MIMEMultipart
import markdown

# 导入自定义模块中的函数
from llm_ollama import llm_call
from formatter import format_to_markdown, validate_data

# 加载 .env 文件中的环境变量
load_dotenv()

# --- 配置从环境变量获取 ---
SOURCE_URL = os.getenv('AI_NEWS_URL')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '.', 'daily_report')

# 邮件配置
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = os.getenv('SMTP_PORT')
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')
SENDER_NICKNAME = os.getenv('SENDER_NICKNAME', 'AI Daily Reporter')


# --- 核心函数 ---

def extract_and_clean_html(html: str) -> str:
    """提取、清理并压缩 HTML 内容，移除 <script> 标签并提取 <body> 内容。"""
    soup = BeautifulSoup(html, 'html.parser')

    # 移除所有 script 标签
    for script in soup.find_all('script'):
        script.decompose()

    body_tag = soup.find('body')

    if not body_tag:
        print('⚠ 未找到 body 标签，使用完整 HTML')
        content = html
    else:
        print('✓ 已提取 body 内容并移除 script 标签')
        content = str(body_tag.decode_contents())

    # 🚀 核心优化：压缩空白字符 (将所有连续的空白替换为一个空格)
    content = re.sub(r'\s+', ' ', content).strip()

    return content


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


def _clean_json_str(content: str) -> str:
    """清理并提取 JSON 字符串中的代码块标记。"""
    json_str = content.strip()

    # 尝试处理代码块 (移除 ```json 或 ``` 标记)
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', json_str) or \
                 re.search(r'```\s*([\s\S]*?)\s*```', json_str)

    if json_match and json_match.group(1):
        return json_match.group(1).strip()

    return json_str


def extract_json(content: str) -> object or None:
    """
    【用途：提取日报内容】从 LLM 返回的内容中提取 JSON 数组。
    核心修正：尝试从最外层对象中提取目标数组。
    """
    json_str = _clean_json_str(content)

    try:
        data = json.loads(json_str)

        # 1. 修正：如果解析结果是字典，检查它是否是包含目标数组的字典
        if isinstance(data, dict):
            # 遍历字典的值，尝试找到最可能的目标数组 (即包含 "category" 键的数组)
            for value in data.values():
                # 检查是否为非空数组，且数组第一个元素是包含 'category' 键的字典
                if isinstance(value, list) and value and isinstance(value[0], dict) and 'category' in value[0]:
                    print("🔔 修正: 成功从 LLM 返回的最外层对象中提取到日报数组。")
                    return value

                    # 2. 如果是数组，直接返回
        if isinstance(data, list):
            return data

        print(f"❌ JSON 解析成功，但顶层结构不是数组或包含数组的字典: {type(data)}", file=sys.stderr)
        return None

    except json.JSONDecodeError as e:
        print(f'❌ 日报JSON最终解析失败: {e}', file=sys.stderr)
        return None


def extract_title_tags_json(content: str) -> dict or None:
    """
    【用途：提取标题和标签】从 LLM 返回的内容中提取 JSON 对象。
    """
    json_str = _clean_json_str(content)

    try:
        data = json.loads(json_str)

        # 强制要求返回的是字典 (对象) 且包含 'title' 键
        if isinstance(data, dict) and 'title' in data:
            print("🔔 修正: 成功解析标题/标签 JSON 对象。")
            return data

        print(f"❌ 标题/标签JSON解析失败，不是预期的字典或缺少'title'键。")
        return None

    except json.JSONDecodeError as e:
        print(f'❌ 标题/标签JSON最终解析失败: {e}', file=sys.stderr)
        return None


def update_home_json(new_entry: dict):
    """更新 dailyData.json 文件。"""
    # 路径：./dailyData.json
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

    # 检查是否已存在相同日期的条目
    existing_index = next((i for i, item in enumerate(home_data) if item.get('date') == new_entry.get('date')), -1)

    if existing_index != -1:
        home_data[existing_index] = new_entry
        print(f'✓ 更新已存在的日期条目: {new_entry.get("date")}')
    else:
        home_data.insert(0, new_entry)
        print(f'✓ 添加新条目: {new_entry.get("date")}')

    # 写入文件
    with open(home_json_path, 'w', encoding='utf-8') as f:
        json.dump(home_data, f, ensure_ascii=False, indent=4)


# --- 邮件发送函数 (包含所有修复) ---

async def send_daily_report_email(subject: str, markdown_content: str, to_addr: str):
    """发送 AI 日报邮件，同时包含纯文本和 HTML 格式（Markdown 自动转 HTML）。"""
    if not (SMTP_SERVER and SMTP_PORT and EMAIL_USER and EMAIL_PASSWORD):
        print("⚠ 邮件配置不完整（缺少服务器或登录信息），跳过邮件发送。", file=sys.stderr)
        return

    try:
        # 1. 清理 SMTP_PORT 并确保是整数 (修复了 invalid literal for int() 错误)
        clean_port = ''.join(filter(str.isdigit, SMTP_PORT.strip()))
        if not clean_port:
            raise ValueError("SMTP_PORT 无法解析为有效数字。")

        # 2. 转换为 HTML
        html_content = markdown.markdown(markdown_content, extensions=['extra'])

        # 3. 创建 MIMEMultipart 容器，类型设置为 'alternative'
        msg = MIMEMultipart('alternative')

        # 4. 设置邮件头部 (修复了 "From" header is missing or invalid 错误)
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = formataddr((str(Header(SENDER_NICKNAME, 'utf-8')), EMAIL_USER))
        msg['To'] = to_addr

        # 5. 附加纯文本版本
        part_text = MIMEText(markdown_content, 'plain', 'utf-8')
        msg.attach(part_text)

        # 6. 附加 HTML 版本
        part_html = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(part_html)

        print('⚙️  尝试发送 HTML 格式邮件...')

        # 7. 连接并发送
        server = smtplib.SMTP(SMTP_SERVER, int(clean_port), timeout=10)
        server.ehlo()
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)

        server.sendmail(EMAIL_USER, [to_addr], msg.as_string())
        server.quit()

        print(f'✓ HTML 邮件发送成功！已发送至 {to_addr}')

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

        # 1. 获取 HTML 内容 (使用同步 requests)
        print('📥 正在获取内容...')
        print(f'    URL: {SOURCE_URL}')
        response = requests.get(SOURCE_URL, timeout=15)
        response.raise_for_status()
        html = response.text
        print(f'✓ 获取成功，内容长度: {len(html)} 字符\n')

        # 2. 提取并清理 HTML (已包含压缩空白)
        print('🧹 正在清理 HTML...')
        html = extract_and_clean_html(html)
        print(f'✓ 清理完成，处理后长度: {len(html)} 字符\n')

        # 🚨 核心修正：引入硬截断逻辑，避免 Ollama 因输入过长而崩溃 (返回长度0)
        MAX_LLM_INPUT = 30000
        input_html = html

        if len(html) > MAX_LLM_INPUT:
            input_html = html[:MAX_LLM_INPUT]
            print(f"⚠ HTML 输入长度 ({len(html)} 字符) 超过 {MAX_LLM_INPUT}，已截断为 {len(input_html)} 字符。")
        else:
            print(f"✓ HTML 长度 ({len(html)} 字符) 在安全范围内。")

        # 3. 读取提示词
        print('📝 正在读取提示词...')
        prompt_path = os.path.join(os.path.dirname(__file__), 'prompt02.md')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt = f.read()
        print('✓ 提示词读取成功\n')

        # 4. 调用 LLM 生成结构化数据 (异步调用)
        print('🤖 正在调用 LLM 生成结构化数据...')
        print('    (这可能需要一些时间，请耐心等待...)')
        llm_response = await llm_call(prompt + input_html)
        print(f'✓ LLM 响应成功，长度: {len(llm_response)} 字符\n')

        # 5. 解析 JSON 数据 (使用 extract_json，期望数组结构)
        print('📊 正在解析 JSON 数据...')
        print(f"DEBUG: LLM 原始响应内容: {llm_response[:500]}...", file=sys.stderr)
        json_data = extract_json(llm_response)

        if not json_data:
            # 如果解析失败，抛出异常，并打印原始响应的前 500 个字符进行调试
            raise Exception('无法解析 LLM 返回的 JSON 数据。请检查 Ollama 模型是否遵循提示词要求输出 JSON。')

        # 验证数据结构 (validate_data 期望顶层是数组)
        if not validate_data(json_data):
            raise Exception('JSON 数据结构验证失败')

        print(f'✓ JSON 数据解析成功，包含 {len(json_data)} 个分类\n')

        # 6. 格式化为 Markdown
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

        # 8. 生成标题和标签
        print('🏷️  正在生成标题和标签...')
        prompt2_path = os.path.join(os.path.dirname(__file__), 'prompt2.md')
        with open(prompt2_path, 'r', encoding='utf-8') as f:
            prompt2 = f.read()

        title_and_tags_response = await llm_call(markdown_output + '\n\n' + prompt2)
        print('✓ 标题和标签生成成功\n')

        # 9. 解析并更新 dailyData.json (使用 extract_title_tags_json，期望对象结构)
        print('📋 正在更新 dailyData.json...')
        # ⚠️ 使用专门的函数处理标题和标签的 JSON 对象
        title_and_tags = extract_title_tags_json(title_and_tags_response)

        report_title = f"AI 日报 {file_name.replace('.md', '')}"  # 默认标题

        if title_and_tags and title_and_tags.get('title') and title_and_tags.get('tags'):
            report_title = title_and_tags.get('title')
            # 兼容 LLM 可能多输出的 'summary' 或 'date' 键，但只使用 'title' 和 'tags'
            entry_data = {
                'title': report_title,
                'tags': title_and_tags.get('tags'),
                'date': file_name.replace('.md', '')
            }
            update_home_json(entry_data)
            print('✓ dailyData.json 更新成功')
            print(f'    标题: {report_title}')
            print(f'    标签: {", ".join(title_and_tags["tags"])}\n')
        else:
            print('⚠ 无法解析标题和标签，跳过 dailyData.json 更新\n')

        # 10. 发送邮件
        if RECIPIENT_EMAIL:
            print('✉️  正在发送日报邮件...')
            await send_daily_report_email(report_title, markdown_output, RECIPIENT_EMAIL)
        else:
            print('⚠ 邮件收件人未设置 (RECIPIENT_EMAIL)，跳过邮件发送。')

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
    # 使用 asyncio 启动异步主函数
    asyncio.run(main())