import whisper
import os
import time
import warnings
from tqdm import tqdm
import threading
import ssl
import sys

ssl._create_default_https_context = ssl._create_unverified_context

warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")

def transcribe_audio_with_whisper(audio_path: str, model_size: str = 'base'):
    if not audio_path or not os.path.exists(audio_path):
        return None

    model = whisper.load_model(model_size)
    # 依然保存在 temp 目录下（由 audio_path 的路径决定）
    output_filename = os.path.splitext(audio_path)[0] + "_transcript.txt"

    pbar = tqdm(total=None, desc="🚀 AI 正在转录", bar_format='{l_bar}{bar}| {elapsed}')
    stop_event = threading.Event()
    def progress_spinner():
        while not stop_event.is_set():
            pbar.update(1)
            time.sleep(0.1)

    spinner_thread = threading.Thread(target=progress_spinner)
    spinner_thread.start()

    try:
        result = model.transcribe(audio_path, verbose=None)
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(result["text"].strip() if isinstance(result["text"], str) else str(result["text"]))
        return output_filename
    finally:
        stop_event.set()
        spinner_thread.join()
        pbar.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
    else:
        audio_path = input("请输入要处理的音频文件路径: ").strip()
    
    if not audio_path or not os.path.exists(audio_path):
        print("❌ 未提供有效的音频文件路径")
        sys.exit(1)
    
    model_size = input("选择模型大小 (tiny/base/small/medium/large, 默认 base): ").strip() or "base"
    result = transcribe_audio_with_whisper(audio_path, model_size)
    if result:
        print(f"✅ 转录完成: {result}")
    else:
        print("❌ 转录失败")
        sys.exit(1)