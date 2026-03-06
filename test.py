# import openpyxl
#
# def excel_to_markdown(file_path, sheet_name=0):
#     # 加载 Excel 文件
#     wb = openpyxl.load_workbook(file_path, data_only=True)
#     # 获取指定的 sheet（默认第一个）
#     if isinstance(sheet_name, int):
#         sheet = wb.worksheets[sheet_name]
#     else:
#         sheet = wb[sheet_name]
#
#     # 获取合并单元格的映射关系
#     # merged_cells 存储了每个合并区域左上角的值
#     merged_ranges = sheet.merged_cells.ranges
#
#     def get_cell_value(row, col):
#         """获取单元格的值，如果是合并单元格，则返回该区域左上角的值"""
#         cell = sheet.cell(row=row, column=col)
#         for r in merged_ranges:
#             if cell.coordinate in r:
#                 # 返回合并区域左上角单元格的值
#                 return sheet.cell(row=r.min_row, column=r.min_col).value
#         return cell.value
#
#     # 读取所有数据
#     rows = []
#     max_row = sheet.max_row
#     max_col = sheet.max_column
#
#     for r in range(1, max_row + 1):
#         row_data = []
#         for c in range(1, max_col + 1):
#             val = get_cell_value(r, c)
#             if val is None:
#                 row_data.append("")
#             else:
#                 # 关键步骤：将单元格内的换行符 \n 替换为 HTML 的 <br>
#                 row_data.append(str(val).replace('\n', '<br>'))
#         rows.append(row_data)
#
#     # 转换为 Markdown 字符串
#     md_output = []
#     for i, row in enumerate(rows):
#         # 拼接一行数据
#         line = "| " + " | ".join(row) + " |"
#         md_output.append(line)
#
#         # 如果是表头行，添加分割线
#         if i == 0:
#             separator = "| " + " | ".join(["---"] * len(row)) + " |"
#             md_output.append(separator)
#
#     return "\n".join(md_output)
#
# # 使用示例
# if __name__ == "__main__":
#     # 请确保已安装 openpyxl: pip install openpyxl
#     file_name = "/Users/ryan/Desktop/Book1.xlsx"  # 替换为你的文件名
#     try:
#         markdown_text = excel_to_markdown(file_name)
#         print(markdown_text)
#
#         # 保存到文件
#         with open("/Users/ryan/Desktop/Book1.md", "w", encoding="utf-8") as f:
#             f.write(markdown_text)
#     except Exception as e:
#         print(f"处理出错: {e}")


# import json
#
# raw = input("Paste JSON here: ").strip()   # 用 input() 获取一行JSON（需要是一整行）
#
# data = json.loads(raw)
#
# for k in sorted(data.keys()):
#     print(f"{k}\t{repr(data[k])}")  # repr() 会把空值 "" 明确打印出来

import yt_dlp
import subprocess
import os


def download_and_process_video(video_url, output_path='.'):
    """
    下载 YouTube 视频。如果时长超过 1 小时，则按 30 分钟拆分。
    """
    ydl_opts = {
        'format': 'best',
        'outtmpl': f'{output_path}/%(title)s.%(ext)s',
        'noplaylist': True,
        # 'cookiesfrombrowser': ('chrome',),
    }

    try:
        print(f"⏳ 开始获取视频信息并下载: {video_url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # extract_info 会同时执行下载操作
            info_dict = ydl.extract_info(video_url, download=True)

            # 提取视频时长 (秒) 和下载到本地的完整文件路径
            duration = info_dict.get('duration', 0)
            downloaded_file = ydl.prepare_filename(info_dict)
            ext = info_dict.get('ext', 'mp4')

        print("🎉 视频下载完成！")

        # 判断时长是否超过 1 小时 (3600 秒)
        if duration > 3600:
            print(f"⏱️ 视频时长为 {duration} 秒 (超过 1 小时)，开始按每 30 分钟切片...")

            # 构建拆分后的文件名格式 (例如: 原视频名_part00.mp4)
            base_name = os.path.splitext(downloaded_file)[0]
            output_pattern = f"{base_name}_part%02d.{ext}"

            # 构建 FFmpeg 命令
            # 参数说明:
            # -c copy: 不重新编码，直接复制流，处理速度极快且不损失画质
            # -f segment -segment_time 1800: 每 1800 秒（30分钟）进行一次切割
            command = [
                'ffmpeg',
                '-i', downloaded_file,
                '-c', 'copy',
                '-map', '0',
                '-segment_time', '1800',
                '-f', 'segment',
                '-reset_timestamps', '1',
                output_pattern
            ]

            # 调用系统命令执行 FFmpeg
            subprocess.run(command, check=True)
            print(f"✂️ 拆分完成！视频已保存为多个 30 分钟的片段。")

        else:
            print(f"⏱️ 视频时长为 {duration} 秒 (未超过 1 小时)，无需拆分。")

    except FileNotFoundError:
        print("❌ 致命错误：系统未找到 FFmpeg。请确保已将其安装并添加到了系统环境变量中。")
    except Exception as e:
        print(f"❌ 运行过程中出现错误: {e}")


# ================= 运行示例 =================
if __name__ == "__main__":
    url = input("请输入 YouTube 视频链接: ")
    save_path = '.'

    download_and_process_video(url, save_path)