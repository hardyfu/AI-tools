import os
import glob
import argparse


def get_local_cached_models():
    """扫描 Hugging Face 本地缓存，提取已下载的模型 ID。"""
    cache_dir = os.path.expanduser("~/.cache/huggingface/hub/")
    if not os.path.exists(cache_dir):
        return []

    model_dirs = glob.glob(os.path.join(cache_dir, "models--*"))
    local_models = []

    for d in model_dirs:
        folder_name = os.path.basename(d)
        parts = folder_name.replace("models--", "").split("--")
        if len(parts) >= 2:
            model_id = "/".join(parts)
            local_models.append(model_id)

    return local_models


def get_snapshot_path(model_id):
    """【新增】将模型 ID 转换为本地真实的哈希物理路径"""
    folder_name = "models--" + model_id.replace("/", "--")
    snapshot_dir = os.path.expanduser(f"~/.cache/huggingface/hub/{folder_name}/snapshots/")

    if os.path.exists(snapshot_dir):
        hashes = [h for h in os.listdir(snapshot_dir) if not h.startswith('.')]
        if hashes:
            # 返回内部真实哈希文件夹的完整绝对路径
            return os.path.join(snapshot_dir, hashes[0])
    return model_id  # 如果找不到路径，就原样返回 ID


def main():
    # 确保 main 函数的第一行是保存 parser 的结果
    parser = argparse.ArgumentParser(description="M1 Pro / MLX 本地模型启动器")
    args = parser.parse_args()

    print("=" * 50)
    print("🚀 M1 Pro / MLX 本地模型启动器")
    print("=" * 50)

    # 1. 扫描并展示本地模型
    local_models = get_local_cached_models()

    if local_models:
        print("\n📦 发现以下本地缓存模型：")
        for i, model in enumerate(local_models, 1):
            print(f"[{i}] {model}")
    else:
        print("\n⚠️ 未在默认路径发现本地缓存模型。")

    print("[0] 手动输入新的 Hugging Face 模型 ID")

    # 2. 用户选择模型
    model_id = ""
    while True:
        choice = input(f"\n请选择要加载的模型编号 (0-{len(local_models)}): ").strip()
        if choice == '0':
            model_id = input("请输入模型 ID: ").strip()
            if model_id:
                break
        elif choice.isdigit() and 1 <= int(choice) <= len(local_models):
            model_id = local_models[int(choice) - 1]
            break
        else:
            print("❌ 输入无效，请重新输入。")

    # 3. 用户选择是否开启离线模式
    print("\n🌐 网络通讯策略配置：")
    offline_choice = input("是否开启强制离线模式？(Y/n，默认开启): ").strip().lower()

    # 决定最终传给 load() 函数的是 ID 还是 绝对路径
    load_target = model_id

    if offline_choice != 'n':
        os.environ["HF_HUB_OFFLINE"] = "1"
        # 【核心逻辑】：将模型 ID 替换为底层绝对路径
        load_target = get_snapshot_path(model_id)
        print("✅ 已开启纯本地离线运行，将直接从物理路径加载：")
        print(f"📂 {load_target}")
    else:
        os.environ.pop("HF_HUB_OFFLINE", None)
        print("🔄 保持在线模式")

    print(f"\n⏳ 正在初始化 MLX 引擎并加载模型...")
    from mlx_lm import load, generate

    try:
        # 使用 load_target (可能是 ID，也可能是绝对路径) 加载模型
        model, tokenizer = load(load_target)
        print("🎉 模型加载成功！\n")
    except Exception as e:
        print(f"\n❌ 模型加载失败，错误信息：\n{e}")
        return

    # 5. 进入交互式对话
    print("-" * 50)
    print("💬 进入单轮对话模式 (输入 'quit' 或 'exit' 退出)")
    print("-" * 50)

    while True:
        user_input = input("\n👤 你: ").strip()
        if user_input.lower() in ['quit', 'exit']:
            print("👋 退出启动器。")
            break
        if not user_input:
            continue

        messages = [
            {"role": "system", "content": "你是一个有用的 AI 助手。"},
            {"role": "user", "content": user_input}
        ]

        try:
            prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
        except Exception:
            prompt = f"User: {user_input}\nAssistant:"

        print("🤖 AI: ", end="", flush=True)
        generate(
            model,
            tokenizer,
            prompt=prompt,
            verbose=True,
            max_tokens=1024
        )


if __name__ == "__main__":
    main()