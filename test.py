import json

with open("/Users/ryan/Desktop/API.json", "r") as f:
    api_data = json.load(f)  # 只读取一次
    diffbot_api = api_data["DIFFBOT"]
    qwen_api = api_data["QWEN"]
    gemini_api = api_data["GEMINI"]

