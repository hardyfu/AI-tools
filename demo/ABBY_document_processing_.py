import requests
import base64
import os

ABBY_API_KEY = os.getenv("ABBY_API_KEY")

headers = {
    "X-ABBY-API-Key": ABBY_API_KEY,
    "Content-Type": "application/json"
}

# Read file and encode as base64
with open("/Users/ryanfu/Desktop/AI Security Policy.pdf", "rb") as f:
    file_data = base64.b64encode(f.read()).decode()

data = {
    "model": "gemini-3.1-pro",
    "input": [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "Analyze this document and extract key information"
                },
                {
                    "type": "input_file",
                    "file": {
                        "data": file_data,
                        "mimetype": "application/pdf",
                        "title": "MyDocument"
                    }
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