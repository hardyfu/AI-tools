import base64
import json
import os
import requests
import tkinter as tk
from tkinter import filedialog
from datetime import datetime

# Ollama API 的默认本地地址
OLLAMA_API_URL = "http://localhost:11434/api/chat"
JUDGE_MODEL_NAME = "qwen3.5:4b"


def encode_image_to_base64(image_path):
    """将本地图片转换为 Base64 编码"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def call_ollama(payload):
    """调用 Ollama API 并返回 message.content"""
    response = requests.post(OLLAMA_API_URL, json=payload, timeout=180)
    response.raise_for_status()
    return response.json().get("message", {}).get("content", "")


def parse_json_text(text):
    """兼容处理模型输出中可能存在的 Markdown 代码块"""
    clean_text = text.strip()
    if clean_text.startswith("```"):
        clean_text = clean_text.strip("`")
        if clean_text.lower().startswith("json"):
            clean_text = clean_text[4:].strip()
    return json.loads(clean_text)


def normalize_to_text(value):
    """将模型返回值归一化为字符串，避免类型不一致导致崩溃"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()


def extract_config_with_vision_model(image_path):
    """第 1 步：使用 qwen3-vl:8b 提取截图中的关键配置文本"""
    print(f"[*] Step 1/2: 使用 {JUDGE_MODEL_NAME} 识别截图内容...")
    base64_image = encode_image_to_base64(image_path)

    system_prompt = (
        "你是信息安全审计助手。"
        "请从截图中提取与系统配置、状态、参数相关的可见文本。"
        "必须输出 JSON，且仅包含字段 extracted_config。"
        "若看不清，请写明“未识别到清晰配置”。"
    )
    user_prompt = "请提取这张截图中可用于合规审计的配置文本。"

    payload = {
        "model": JUDGE_MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": user_prompt,
                "images": [base64_image]
            }
        ],
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.1}
    }
    result_text = call_ollama(payload)
    parsed_result = parse_json_text(result_text)
    return normalize_to_text(parsed_result.get("extracted_config", ""))


def judge_compliance_with_text_model(extracted_config, control_point_desc):
    """第 2 步：使用 qwen3:8b 判断控制点满足程度"""
    extracted_config = normalize_to_text(extracted_config)
    print(f"[*] Step 2/2: 使用 {JUDGE_MODEL_NAME} 判断控制点满足程度...")
    system_prompt = (
        "你是一名严谨的信息安全专家和 IT 合规审计员。"
        "你将根据“控制点要求”和“截图识别结果”判断满足程度。"
        "必须输出 JSON，包含以下字段："
        "1. extracted_config: 原样返回输入的截图识别结果；"
        "2. analysis_process: 给出比对分析过程；"
        "3. compliance_status: 只能是 Pass、Fail、Review。"
    )
    user_prompt = (
        f"【合规控制点要求】\n{control_point_desc}\n\n"
        f"【截图识别结果】\n{extracted_config}\n\n"
        "请判断是否满足控制点要求。"
    )

    try:
        payload = {
            "model": JUDGE_MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.1}
        }
        result_text = call_ollama(payload)
        parsed_result = parse_json_text(result_text)
        if "extracted_config" not in parsed_result:
            parsed_result["extracted_config"] = extracted_config
        return parsed_result

    except requests.exceptions.RequestException as e:
        print(f"[!] API 请求失败: {e}")
        return None
    except json.JSONDecodeError:
        print(f"[!] 模型返回的不是有效的 JSON 格式:\n{result_text}")
        return None


def evaluate_compliance(image_path, control_point_desc):
    """串行调用两个模型：先识别，再判定"""
    try:
        extracted_config = extract_config_with_vision_model(image_path)
        if not extracted_config:
            extracted_config = "未识别到清晰配置"
        return judge_compliance_with_text_model(extracted_config, control_point_desc)
    except requests.exceptions.RequestException as e:
        print(f"[!] API 请求失败: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"[!] 模型返回的不是有效的 JSON 格式: {e}")
        return None


def select_image_file():
    """弹出文件选择对话框，让用户手动选择图片"""
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口，只显示对话框

    # 强制窗口显示在最前（针对部分操作系统的问题）
    root.attributes('-topmost', True)

    file_path = filedialog.askopenfilename(
        title="请选择要扫描的配置截图",
        filetypes=[
            ("图片文件", "*.png *.jpg *.jpeg *.bmp"),
            ("所有文件", "*.*")
        ]
    )

    root.destroy()  # 选择完成后销毁实例
    return file_path


def main():
    # 1. 手动选择测试输入
    print("[*] 正在打开文件选择器，请选择截图...")
    sample_image_path = select_image_file()

    if not sample_image_path:
        print("[!] 取消了文件选择，程序退出。")
        return

    print(f"[+] 已选择截图: {sample_image_path}")

    # 模拟一个 IT 合规控制点（例如：SSH 登录策略）
    control_point = "就公众可访问的网站向所在地通信管理局办理ICP备案"

    # 2. 执行合规判定
    result_data = evaluate_compliance(sample_image_path, control_point)

    # 3. 确保主函数保存解析器的结果
    if result_data:
        print("\n[+] 判定完成，解析结果如下:")
        print(json.dumps(result_data, indent=4, ensure_ascii=False))

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_filename = os.path.join(
            script_dir,
            f"compliance_result_{timestamp}.json"
            )
        # output_filename = f"compliance_result_{timestamp}.json"

        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=4, ensure_ascii=False)

        print(f"\n[*] 结果已成功保存至: {output_filename}")

        if result_data.get("compliance_status") == "Fail":
            print("[!] 警告: 发现不合规项，建议启动安全例外或整改流程。")


if __name__ == "__main__":
    main()
