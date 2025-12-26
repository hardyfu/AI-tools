import whisper
import os
import time
import warnings
from tqdm import tqdm
import threading
import ssl

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
            f.write(result["text"].strip())
        return output_filename
    finally:
        stop_event.set()
        spinner_thread.join()
        pbar.close()