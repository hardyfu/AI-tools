import os
from google import genai
from google.genai import types

# 1. 代理配置
proxy_address = "127.0.0.1:7890"
os.environ['http_proxy'] = f"http://{proxy_address}"
os.environ['https_proxy'] = f"http://{proxy_address}"


def run_gemini_audit():
    api_key = input("请输入你的 Gemini API Key: ").strip()
    if not api_key:
        print("错误：未输入 API Key")
        return

    client = genai.Client(api_key=api_key)

    print("\n" + "=" * 60)
    print(f"{'模型名称':<30} | {'实测状态':<15} | {'备注'}")
    print("-" * 60)

    try:
        # 获取所有模型列表
        models = client.models.list()

        for m in models:
            # 过滤：只测试支持文本生成的模型
            if 'generateContent' in m.supported_actions:
                model_id = m.name.split('/')[-1]

                # 排除掉一些特定用途或过时的模型，减少干扰
                if any(x in model_id for x in ['vision', 'embedding', 'aqa']):
                    continue

                try:
                    # 实测：发送一个极短的请求
                    response = client.models.generate_content(
                        model=model_id,
                        contents="ping"
                    )
                    # 如果能走到这里，说明请求成功
                    print(f"{model_id:<30} | ✅ 真正可用 | 响应成功")

                except Exception as e:
                    # 捕获错误，区分是配额问题还是其他问题
                    error_msg = str(e).lower()
                    if "429" in error_msg or "resource_exhausted" in error_msg:
                        status = "❌ 无额度"
                        note = "Free Tier 额度为 0 (需开启计费)"
                    elif "403" in error_msg or "permission_denied" in error_msg:
                        status = "🚫 无权限"
                        note = "账号或区域受限"
                    else:
                        status = "⚠️ 失败"
                        note = "其他 API 错误"

                    # 打印报错信息
                    # print(f"{model_id:<30} | {status:<15} | {note}")

    except Exception as fatal_e:
        print(f"初始化失败: {fatal_e}")

    print("=" * 60)
    print("测试完成。请优先选择标记为 '✅ 真正可用' 的模型进行开发。")


if __name__ == "__main__":
    run_gemini_audit()