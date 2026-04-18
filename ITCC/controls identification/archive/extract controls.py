import pandas as pd
import os
import re # 导入正则表达式模块用于清理文件名

def sanitize_filename(filename):
    """
    清理文件名，移除或替换不合法的字符。
    Windows文件系统不允许以下字符： <> : " / \ | ? *
    """
    # 使用正则表达式替换非法字符为下划线或直接移除
    # 这里选择替换为下划线，保留更多信息
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # 移除开头和结尾的空白字符，防止文件名无效
    sanitized = sanitized.strip()
    # 确保文件名不为空
    if not sanitized:
        sanitized = "unnamed_file_part"
    return sanitized

def categorize_excel_rows(input_file_path):
    """
    根据Excel文件A列内容对行进行分类，并为每类创建独立的Excel文件。

    Args:
        input_file_path (str): 输入的Excel文件路径。
    """
    # 1. 定义分类字典
    # Key是A列中的关键词，Value是对应的新文件名
    category_mapping = {
        '云服务安全责任': '18.云服务安全责任',
        '互联网社区论坛': '14.互联网社区论坛',
        '其他网络安全保护措施': '05.其他网络安全保护措施',
        '国际专线/VPN适用': '16.国际专线_VPN适用', # 将 / 替换为 _
        '备份与加密': '04.备份与加密',
        '密码产品': '20.密码产品',
        '工业互联网': '15.工业互联网',
        '工业控制系统': '19.工业控制系统',
        '工业数据': '11.工业数据',
        '数据跨境传输': '12.数据跨境传输',
        '日志管理': '02.日志管理',
        '漏洞管理': '03.漏洞管理',
        '第三方服务商管理': '17.第三方服务商管理',
        '网站/APP备案': '13.网站_APP备案', # 将 / 替换为 _
        '网络关键设备及网络安全专用产品': '21.网络关键设备及网络安全专用产品',
        '网络安全等级保护': '06.网络安全等级保护',
        '网络安全管理制度': '07.网络安全管理制度',
        '网络安全管理机构': '08.网络安全管理机构',
        '访问控制': '01.访问控制',
        '数据保护-制度': '09.数据保护-制度',
        '数据保护-个人信息处理': '10.数据保护-个人信息处理',
        '关键信息基础设施运营者的特殊要求': '22.关键信息基础设施运营者的特殊要求'
    }

    # 2. 读取原始Excel文件
    try:
        df = pd.read_excel(input_file_path)
    except FileNotFoundError:
        print(f"错误：找不到文件 {input_file_path}")
        return
    except Exception as e:
        print(f"读取文件时发生错误: {e}")
        return

    if df.empty:
        print("输入的Excel文件为空。")
        return

    # 3. 创建一个字典来存储分类后的数据框
    categorized_dfs = {}

    # 遍历每一行
    for index, row in df.iterrows():
        # 获取A列的值
        cell_value = str(row.iloc[0]) # 假设A列是第一列 (索引0)

        # 初始化一个空列表来存储匹配的类别名
        matched_categories = []

        # 检查单元格内容是否包含分类字典中的关键词
        for keyword, category_name in category_mapping.items():
            if keyword in cell_value:
                matched_categories.append(category_name)

        # 如果找到了匹配的类别
        if matched_categories:
            for cat_name in matched_categories:
                # 在将cat_name用作文件名之前，先进行清理
                safe_cat_name = sanitize_filename(cat_name)
                
                if safe_cat_name not in categorized_dfs:
                    # 如果该类别还没有DataFrame，则创建一个
                    categorized_dfs[safe_cat_name] = pd.DataFrame(columns=df.columns)
                
                # 将当前行追加到对应类别的DataFrame中
                categorized_dfs[safe_cat_name] = pd.concat([categorized_dfs[safe_cat_name], row.to_frame().T], ignore_index=True)
        else:
            # 如果没有找到匹配的关键词，可以将其放入一个“未分类”文件中
            uncategorized_name = "Uncategorized"
            safe_uncat_name = sanitize_filename(uncategorized_name)
            if safe_uncat_name not in categorized_dfs:
                 categorized_dfs[safe_uncat_name] = pd.DataFrame(columns=df.columns)
            categorized_dfs[safe_uncat_name] = pd.concat([categorized_dfs[safe_uncat_name], row.to_frame().T], ignore_index=True)


    # 4. 保存分类后的数据框到新的Excel文件
    output_dir = os.path.dirname(input_file_path) or '.' # 输出目录为输入文件所在目录
    for category_name, data_df in categorized_dfs.items():
        if not data_df.empty: # 只保存非空的DataFrame
            # 现在category_name已经是安全的文件名了
            output_filename = f"{category_name}.xlsx"
            output_path = os.path.join(output_dir, output_filename)
            
            # 保存DataFrame到Excel，保持原始表头
            data_df.to_excel(output_path, index=False, engine='openpyxl')
            print(f"已创建文件: {output_path}")

if __name__ == "__main__":
    # 请将 'your_input_file.xlsx' 替换为您实际的Excel文件路径
    input_file_path = 'C:\\Users\\admin\\Downloads\\Book2.xlsx'
    
    categorize_excel_rows(input_file_path)