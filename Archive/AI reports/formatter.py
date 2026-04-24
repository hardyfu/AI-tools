# formatter.py 文件

import re
import json
import sys
from typing import List, Dict, Any, Optional


# 【注意】不再需要导入 urllib.parse.urljoin

# --- 第 1 部分：JSON 结构验证 (匹配 LLM 输出的键名) ---

def validate_data(data: List[Dict[str, Any]]) -> bool:
    """
    验证 LLM 输出的 JSON 数据结构是否符合预期。
    匹配键名: 'category' / 'items' / 'content'
    """
    if not isinstance(data, list) or not data:
        return False

    # 匹配 LLM 实际返回的键名
    required_keys = ['category', 'items']
    article_keys = ['title', 'content', 'links']
    link_keys = ['text', 'url']

    for item in data:
        # 检查顶级键
        if not all(key in item for key in required_keys):
            print(f"Validation Error: Missing top-level keys in {item}", file=sys.stderr)
            return False

        # 检查文章列表 (现在是 'items')
        if not isinstance(item['items'], list) or not item['items']:
            print(f"Validation Error: 'items' is not a list or is empty in {item}", file=sys.stderr)
            return False

        for article in item['items']:
            # 检查文章键
            if not all(key in article for key in article_keys):
                print(f"Validation Error: Missing article keys in {article}", file=sys.stderr)
                return False

            # 检查链接列表
            if not isinstance(article['links'], list):
                print(f"Validation Error: 'links' is not a list in {article}", file=sys.stderr)
                return False

            for link in article['links']:
                # 检查链接键
                if not all(key in link for key in link_keys):
                    print(f"Validation Error: Missing link keys in {link}", file=sys.stderr)
                    return False

    return True


# --- 第 2 部分：Markdown 格式化 (匹配键名并使用绝对链接) ---

def format_to_markdown(data: List[Dict[str, Any]]) -> str:  # 【修改】移除 base_url 参数
    """
    将结构化数据转换为 Markdown 格式。
    由于 main.py 已经预处理了 HTML，LLM 输出的 URL 应该已经是绝对链接。
    """
    markdown_output = "# AI 日报\n\n"

    for category_item in data:
        # 获取分类名称和文章列表
        category_name = category_item.get('category', '未知分类')
        articles = category_item.get('items', [])

        markdown_output += f"## 📰 {category_name}\n\n"

        for article in articles:
            title = article.get('title', '无标题')
            # 获取内容，使用 'content' 键名
            summary = article.get('content', '无摘要')
            links = article.get('links', [])

            # 1. 输出标题和摘要
            markdown_output += f"### {title}\n"
            markdown_output += f"{summary}\n\n"

            # 2. 输出链接 (直接使用 LLM 提取到的绝对链接)
            if links:
                links_md = []
                for link in links:
                    link_text = link.get('text', '链接')
                    link_url = link.get('url', '#')

                    # 直接使用 LLM 返回的 URL (预期是绝对链接)
                    if link_url and link_url != '#':
                        # 使用绝对链接，并在URL外部添加尖括号以提高兼容性
                        link_md = f"[{link_text}](<{link_url}>)"
                    else:
                        link_md = link_text

                    links_md.append(link_md)

                # 合并所有链接
                links_output = " | ".join(links_md)
                markdown_output += f"**相关链接:** {links_output}\n\n"

    return markdown_output