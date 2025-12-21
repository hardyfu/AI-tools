import subprocess
import sys
import os

# ----------------------------------------------------
# 🎯 代理配置
# ----------------------------------------------------
proxy_address = "127.0.0.1:7897"
os.environ['http_proxy'] = f"http://{proxy_address}"
os.environ['https_proxy'] = f"http://{proxy_address}"


def download_podcast_audio(url: str, output_format: str = 'mp3'):
    """
    下载音频并自动净化文件名（去除特殊字符）。
    """

    # 检查依赖 (省略部分检查代码...)

    print("=" * 40)
    print(f"🌍 代理已就绪，准备下载并净化文件名...")
    print("=" * 40)

    # ----------------------------------------------------
    # 核心修改：添加 --restrict-filenames
    # ----------------------------------------------------
    command = [
        'yt-dlp',
        '-x',  # 提取音频
        '--audio-format', output_format,  # 转换为 mp3
        '--embed-metadata',  # 嵌入元数据
        '--embed-thumbnail',  # 嵌入封面
        '--restrict-filenames',  # 【关键】去除特殊字符，只保留 ASCII 和下划线
        # 使用下面的参数可以自定义保存的文件名格式
        '-o', '%(title)s.%(ext)s',
        url
    ]

    try:
        # 运行下载并捕获输出，以便我们可以知道最终生成的文件名
        result = subprocess.run(command, check=True, text=True)

        print("\n" + "#" * 40)
        print("🎉 下载成功！")
        print("💡 文件名已自动处理，不再包含特殊字符。")
        print("#" * 40)

    except subprocess.CalledProcessError as e:
        print(f"\n❌ 下载失败: {e}")


# 目标链接
podcast_url = input("input URL:\n")

if __name__ == "__main__":
    download_podcast_audio(podcast_url)