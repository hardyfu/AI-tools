import requests
import os

ABBY_API_KEY = os.getenv("ABBY_API_KEY")

headers = {
    "X-ABBY-API-Key": ABBY_API_KEY,
    "Content-Type": "application/json"
}

response = requests.get(
    "https://api.abby.abb.com/api/v1/developers/models",
    headers=headers,
)
response.raise_for_status()

models = response.json()
if isinstance(models, dict):
    models = models.get("data", models.get("models", []))

for model in models:
    if isinstance(model, dict):
        print(model.get("name") or model.get("id"))
    else:
        print(model)
