import requests
import base64
import os

# ================= 配置 =================
API_URL = "https://elisecamea.services.ai.azure.com/mai/v1/images/generations?api-version=preview"
API_KEY = os.getenv("ABB_Foundry_API_KEY")

OUTPUT_FILE = "fifa.png"

# ================= 请求体 =================
payload = {
    "prompt": """
中国队勇夺世界杯！赛后集体捧杯大合照！注意每个人的头像不能一样，贴近真实。
    """,
    "width": 1366, # only 1024*1024 or 1366*768
    "height": 768,
    "n": 1,
    "model": "MAI-Image-2e"
}

headers = {
    "Content-Type": "application/json",
    "api-key": API_KEY
}

# ================= 发送请求 =================
response = requests.post(API_URL, json=payload, headers=headers)

if response.status_code != 200:
    print("❌ Request failed:", response.status_code, response.text)
    exit(1)

# ================= 解析返回 =================
result = response.json()

# 取出 base64 图像
image_base64 = result["data"][0]["b64_json"]

# ================= 解码并保存 =================
image_bytes = base64.b64decode(image_base64)

with open(OUTPUT_FILE, "wb") as f:
    f.write(image_bytes)

print(f"✅ Image saved to {OUTPUT_FILE}")