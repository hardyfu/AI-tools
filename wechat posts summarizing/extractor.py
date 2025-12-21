import requests
import sys
from config import DIFFBOT_API_TOKEN  # 从 config 模块导入配置


def extract_article_content(url: str, token: str) -> dict or None:
    """通过 Diffbot API 提取文章的文本内容"""

    # 检查 Token 是否被正确配置（检查是否为占位符）
    if not token or token == 'DIFFBOT_PLACEHOLDER':
        print("🔴 错误: Diffbot API Token 未设置或使用了占位符，请检查 .env 配置。", file=sys.stderr)
        return None

    # Diffbot 文章 API URL
    DIFFBOT_API_URL = f'https://api.diffbot.com/v3/article?token={token}&url={url}'
    print(f"-> 正在调用 Diffbot API 提取文章内容: {url}")

    try:
        response = requests.get(DIFFBOT_API_URL, timeout=30)

        # 检查 4xx/5xx 状态码 (Token 无效通常是 401/403)
        response.raise_for_status()

        data = response.json()

        if data.get('objects'):
            article_data = data['objects'][0]
            return {
                'title': article_data.get('title', '无标题'),
                'text': article_data.get('text', '')
            }
        else:
            print("🔴 警告: Diffbot 未能成功解析文章或返回空数据。")
            print(f"  API 原始响应: {response.text[:200]}...", file=sys.stderr)
            return None

    except requests.exceptions.HTTPError as e:
        print(f"🔴 错误: Diffbot API 调用失败 (HTTP {e.response.status_code})。请检查 Token 是否有效。", file=sys.stderr)
        return None
    except requests.exceptions.RequestException as e:
        print(f"🔴 错误: 请求 Diffbot API 时发生网络错误: {e}", file=sys.stderr)
        return None


# 封装使用默认配置的接口
def get_article(url: str) -> dict or None:
    return extract_article_content(url, DIFFBOT_API_TOKEN)