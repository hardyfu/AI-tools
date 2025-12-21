import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

# ----------------------------------------------------
# ❗ 第一步：加载 .env 文件中的环境变量
# ----------------------------------------------------
# 尝试加载项目根目录下的 .env 文件
load_dotenv()

# --- 配置信息 (现在从环境变量中读取，使用通用占位符作为 Fallback) ---

# Diffbot 配置
DIFFBOT_API_TOKEN = os.getenv('DIFFBOT_API_TOKEN', 'd0cc70644a648dc5f848172e9cbdfcd2')

# LLM 配置 (通义千问兼容模式)
LLM_API_KEY = os.getenv('DASHSCOPE_API_KEY', 'sk-9a91e09e3560466ea25b20054dce2957')
LLM_API_URL = os.getenv('LLM_API_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
LLM_MODEL_ID = os.getenv('LLM_MODEL_ID', 'qwen-plus-2025-12-01')

# 应用配置
#ARTICLE_URL = os.getenv('ARTICLE_URL', input("输入需要总结的文章URL：\n"))

# --- 客户端初始化 ---

try:
    # 检查 LLM API KEY 是否为占位符或 None
    if LLM_API_KEY in ('QWEN_PLACEHOLDER', None) or not LLM_API_KEY:
        raise Exception("LLM 配置不完整：缺少 DASHSCOPE_API_KEY。请在 .env 文件中设置。")

    # 使用从环境变量中读取的值初始化客户端
    client = OpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_API_URL,
    )
    print("✅ LLM 客户端初始化成功。")
except Exception as e:
    print(f"❌ LLM 客户端初始化失败: {e}", file=sys.stderr)
    client = None