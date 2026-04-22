import base64
import json
import mimetypes
import os
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog

from openai import OpenAI

# 本地 oMLX OpenAI-compatible 服务
OMLX_BASE_URL = "http://127.0.0.1:8000/v1"

# 需要替换为 oMLX 中实际加载、且支持视觉输入的模型名称。
# 示例：
# MODEL_NAME = "gemma-4-e4b-it-4bit"
MODEL_NAME = "Qwen3.5-9B-MLX-4bit"

client = OpenAI(
    base_url=OMLX_BASE_URL,
    api_key="510918123Fu!",  # 本地服务通常只要求非空字符串
    timeout=180,
)


def encode_image_to_base64(image_path):
    """将本地图片转换为 Base64 编码。"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def build_image_data_url(image_path):
    """构造 OpenAI-compatible image_url data URL。"""
    mime_type = mimetypes.guess_type(image_path)[0] or "image/png"
    base64_image = encode_image_to_base64(image_path)
    return f"data:{mime_type};base64,{base64_image}"


def ask_model(messages, max_tokens=8192):
    """调用 oMLX，并返回模型输出文本。"""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.1,
        max_tokens=max_tokens,
    )
    message = response.choices[0].message
    return (message.content or getattr(message, "reasoning", "") or "").strip()


def parse_json_text(text):
    """解析模型返回的 JSON，兼容代码块或少量前后说明文字。"""
    clean_text = text.strip()
    if clean_text.startswith("```"):
        clean_text = clean_text.strip("`").strip()
        if clean_text.lower().startswith("json"):
            clean_text = clean_text[4:].strip()

    if not clean_text.startswith("{"):
        start = clean_text.find("{")
        end = clean_text.rfind("}")
        if start != -1 and end != -1 and end > start:
            clean_text = clean_text[start:end + 1]

    return json.loads(clean_text)


def identify_image(image_path):
    """第 1 步：识别图片中的可见配置文本。"""
    print(f"[*] Step 1/2: 使用 {MODEL_NAME} 识别截图内容...")
    image_data_url = build_image_data_url(image_path)

    return ask_model([
        {
            "role": "system",
            "content": "你是信息安全审计助手。只提取截图中的可见文字和配置，不做合规判断。",
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "请识别这张截图中可用于合规审计的内容。"},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ],
        },
    ])


def judge_compliance(extracted_config, control_point_desc):
    """第 2 步：根据识别结果判断控制点满足程度。"""
    print(f"[*] Step 2/2: 使用 {MODEL_NAME} 判断控制点满足程度...")

    result_text = ask_model([
        {
            "role": "system",
            "content": (
                "你是一名严谨的信息安全专家和 IT 合规审计员。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"【合规控制点要求】\n{control_point_desc}\n\n"
                f"【截图识别结果】\n{extracted_config}\n\n"
                "请判断截图识别结果是否满足控制点要求。"
                "输出格式为 JSON，字段为 extracted_config、analysis_process、"
                "compliance_status。其中compliance_status 只能是 Pass、Fail、Review。"
            ),
        },
    ])

    try:
        result = parse_json_text(result_text)
    except json.JSONDecodeError:
        print("[!] 第二步模型原始输出如下:")
        print(result_text)
        raise

    result.setdefault("extracted_config", extracted_config)
    return result


def evaluate_compliance(image_path, control_point_desc):
    """先识别图片内容，再判断合规性。"""
    extracted_config = identify_image(image_path)
    if not extracted_config:
        extracted_config = "未识别到清晰配置"
    return judge_compliance(extracted_config, control_point_desc)


def select_image_file():
    """弹出文件选择对话框，让用户手动选择图片。"""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    file_path = filedialog.askopenfilename(
        title="请选择要扫描的配置截图",
        filetypes=[
            ("图片文件", "*.png *.jpg *.jpeg *.bmp"),
            ("所有文件", "*.*"),
        ],
    )

    root.destroy()
    return file_path


def main():
    print("[*] 正在打开文件选择器，请选择截图...")
    image_path = select_image_file()

    if not image_path:
        print("[!] 取消了文件选择，程序退出。")
        return

    print(f"[+] 已选择截图: {image_path}")
    control_point = "就公众可访问的网站向所在地通信管理局办理ICP备案"

    start_time = time.perf_counter()
    result_data = evaluate_compliance(image_path, control_point)
    elapsed = time.perf_counter() - start_time

    print("\n[+] 判定完成，解析结果如下:")
    print(json.dumps(result_data, indent=4, ensure_ascii=False))
    print(f"\n[*] {MODEL_NAME} 本次调用耗时: {elapsed:.3f} 秒")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_filename = os.path.join(script_dir, f"omlx_compliance_result_{timestamp}.json")

    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(result_data, f, indent=4, ensure_ascii=False)

    print(f"[*] 结果已成功保存至: {output_filename}")

    if result_data.get("compliance_status") == "Fail":
        print("[!] 警告: 发现不合规项，建议启动安全例外或整改流程。")


if __name__ == "__main__":
    main()
