import whisper
import os
import time
import warnings
from tqdm import tqdm
import threading

# 1. 忽略 CPU 运行时的 FP16 警告
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")


def transcribe_audio_with_whisper(audio_path: str, model_size: str = 'base'):
    if not os.path.exists(audio_path):
        print(f"❌ 错误：未找到文件 -> {audio_path}")
        return

    print("=" * 60)
    print(f"🤖 正在加载 Whisper 模型 ({model_size})...")

    # 记录开始时间
    start_time = time.time()

    try:
        model = whisper.load_model(model_size)
    except Exception as e:
        print(f"❌ 模型加载失败：{e}")
        return

    print(f"👂 正在转录：{os.path.basename(audio_path)}")

    # ----------------------------------------------------
    # 🎢 动感进度条逻辑
    # ----------------------------------------------------
    # 使用 total=None 创建一个不断流动的“跑马灯”进度条
    pbar = tqdm(
        total=None,
        desc="🚀 AI 正在深度处理中",
        bar_format='{l_bar}{bar}| {elapsed} [计算中...]'
    )

    def progress_spinner():
        """后台线程：每隔 0.1 秒刷新一次进度条动画"""
        while not stop_event.is_set():
            pbar.update(1)
            time.sleep(0.1)

    stop_event = threading.Event()
    spinner_thread = threading.Thread(target=progress_spinner)
    spinner_thread.start()

    try:
        # 执行核心转录任务
        result = model.transcribe(audio_path, verbose=None)
    except Exception as e:
        print(f"\n❌ 转录出错：{e}")
        return
    finally:
        # 任务结束，停止动画并关闭进度条
        stop_event.set()
        spinner_thread.join()
        pbar.close()

    # ----------------------------------------------------
    # 3. 保存文件
    # ----------------------------------------------------
    transcript_text = result["text"].strip()
    output_filename = os.path.splitext(audio_path)[0] + "_transcript.txt"

    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(transcript_text)

    end_time = time.time()
    print("-" * 60)
    print(f"🎉 处理完成！总耗时：{end_time - start_time:.2f} 秒")
    print(f"📁 文本已保存至：{output_filename}")
    print("=" * 60)


# 请确保此文件名正确
audio_file_name = "The_pattern_we_re_missing_in_the_AI_job_panic_Vlad_Tenev.mp3"

if __name__ == "__main__":
    transcribe_audio_with_whisper(audio_file_name, model_size='base')