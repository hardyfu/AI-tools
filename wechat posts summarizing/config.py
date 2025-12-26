import os
import sys
import httpx
from dotenv import load_dotenv
from openai import OpenAI
from google import genai
from google.genai import types

# ----------------------------------------------------
# ❗ 第一步：加载 .env 文件中的环境变量
# ----------------------------------------------------
# 尝试加载项目根目录下的 .env 文件
load_dotenv()

# --- 配置信息 (现在从环境变量中读取) ---

# Diffbot 配置
DIFFBOT_API_TOKEN = os.getenv('DIFFBOT_API_TOKEN', 'd0cc70644a648dc5f848172e9cbdfcd2')

# LLM 配置
LLM_CONFIGS = {
    'qwen': {
        'type': 'openai',
        'api_key': os.getenv('DASHSCOPE_API_KEY', 'sk-9a91e09e3560466ea25b20054dce2957'),
        'base_url': os.getenv('QWEN_API_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1'),
        'model_id': os.getenv('QWEN_MODEL_ID', 'qwen-plus-2025-12-01'),
        'proxy': None,
        'extra_body': {}
    },
    'gemini': {
        'type': 'google',
        'api_key': os.getenv('GEMINI_API_KEY', 'AIzaSyAwubRFMgLZujiFgylHkJmSvWUEdTHzvsk'),
        'model_id': os.getenv('GEMINI_MODEL_ID', 'gemini-3-flash-preview'),
        'proxy': 'http://127.0.0.1:7890',
        'thinking_level': 'low'
    }
}

def get_llm_client(provider='qwen'):
    """
    根据指定的 provider 初始化并返回 LLM 客户端和相关配置
    返回: (client, model_id, provider_type, extra_config)
    """
    config = LLM_CONFIGS.get(provider.lower())
    if not config:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")

    api_key = config['api_key']
    if not api_key:
        error_msg = f"LLM 配置不完整：缺少 {provider.upper()} API KEY。请在 .env 文件中设置。"
        print(f"❌ {error_msg}", file=sys.stderr)
        return None, None, None, None

    provider_type = config['type']

    try:
        if provider_type == 'openai':
            http_client = None
            if config.get('proxy'):
                http_client = httpx.Client(proxy=config['proxy'])
            
            client = OpenAI(
                api_key=api_key,
                base_url=config['base_url'],
                http_client=http_client
            )
            return client, config['model_id'], 'openai', config.get('extra_body', {})
            
        elif provider_type == 'google':
             # google-genai SDK 代理设置
            proxy = config.get('proxy')
            httpx_client = None
            if proxy:
                httpx_client = httpx.Client(proxy=proxy)
            
            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(httpx_client=httpx_client)
            )
            
            # 构造 Gemini 特有的 config
            thinking_level = config.get('thinking_level')
            gemini_config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level=thinking_level) if thinking_level else None,
            )

            return client, config['model_id'], 'google', gemini_config
            
    except Exception as e:
        print(f"❌ {provider.upper()} 客户端初始化失败: {e}", file=sys.stderr)
        return None, None, None, None