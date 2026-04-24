import os
from audio import download_podcast_audio
from transcripts import transcribe_audio_with_whisper
from analysis import analyze_and_save


def main():
    temp_dir = "temp"
    output_dir = "output"
    for folder in [temp_dir, output_dir]:
        if not os.path.exists(folder):
            os.makedirs(folder)

    print("🎙️ Podcast 学习助手 - 稳定版工作流")
    print("-" * 40)

    url = input("🔗 1. 请输入 Podcast URL: ").strip()
    api_key = input("🔑 2. 请输入 Gemini API Key: ").strip()

    if not url or not api_key:
        return

    # 阶段 1: 下载
    audio_path = download_podcast_audio(url, temp_dir)
    if not audio_path: return

    # 阶段 2: 转录
    transcript_path = transcribe_audio_with_whisper(audio_path)
    if not transcript_path: return

    # 阶段 3: 循环分析
    current_transcript = transcript_path
    while True:
        print("\n" + "-" * 30)
        final_md = analyze_and_save(api_key, current_transcript, output_dir)

        if final_md:
            print(f"\n✅ 任务圆满完成！报告已存至: {final_md}")
            break
        else:
            print("\n❌ 分析中断。")
            retry = input("是否尝试重新分析？[R]重试当前文件 / [输入文件名]手动指定 / [Q]退出: ").strip()

            if retry.lower() == 'q':
                break
            elif retry.lower() == 'r':
                continue
            else:
                # 检查手动输入的文件
                potential_path = os.path.join(temp_dir, retry)
                if os.path.exists(potential_path):
                    current_transcript = potential_path
                elif os.path.exists(retry):
                    current_transcript = retry
                else:
                    print(f"⚠️ 找不到文件 {retry}，将继续尝试原文件...")


if __name__ == "__main__":
    main()