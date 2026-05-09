import requests
import os
import base64

ABBY_API_KEY = os.getenv("ABBY_API_KEY")

# 选择并编码本地图片
image_path = "/Users/ryanfu/Desktop/1.png"  # 替换为实际路径
with open(image_path, "rb") as f:
    image_base64 = base64.b64encode(f.read()).decode("utf-8")

headers = {
    "X-ABBY-API-Key": ABBY_API_KEY,
    "Content-Type": "application/json"
}
data = {
    "model": "gpt-5.4",
    "input": [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "What is in this image? Provide a detailed analysis."
                },
                {
                    "type": "input_image",
                    "image": image_base64
                }
            ]
        }
    ]
}
response = requests.post(
    "https://api.abby.abb.com/api/v1/developers/simple_chat",
    headers=headers,
    json=data
)
print(response.json().get("output").get("content"))