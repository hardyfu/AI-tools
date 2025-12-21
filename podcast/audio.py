import subprocess
import os


def download_podcast_audio(url: str, temp_dir: str):
    proxy_address = "127.0.0.1:7897"
    os.environ['http_proxy'] = f"http://{proxy_address}"
    os.environ['https_proxy'] = f"http://{proxy_address}"

    # -o 参数指定下载到 temp 文件夹
    output_template = os.path.join(temp_dir, '%(title)s.%(ext)s')

    command = [
        'yt-dlp',
        '-x',
        '--audio-format', 'mp3',
        '--restrict-filenames',
        '-o', output_template,
        '--print', 'after_move:filepath',
        url
    ]

    try:
        print(f"🌍 正在下载音频至 {temp_dir}...")
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        final_path = result.stdout.strip().split('\n')[-1]
        return final_path
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return None