import json
import re

# 表头（制表符分隔）
headers = """Id	开始时间	完成时间	电子邮件	名称	Language	Department	Application Owner	iGAR ID	Application Name	Function Description	Categories	User Category	Number of Users	Can be accessed from the Internet?	Whether the personal information (e.g. name, phone number) is collected?	Involvement in Cross-Border Data Transfers or Access by Overseas Personnel	Availability of Internet Community or Forum Features	Maintenance	Infrastructure Deployment	User Category1	Number of Users1	Can be accessed from the Internet?1	Involvement in Cross-Border Data Transfers or Access by Overseas Personnel1	Maintenance1	Infrastructure Deployment1	User Category2	Number of Users2	Can be accessed from the Internet?2	Whether the personal information (e.g. name, phone number) is collected?1	Involvement in Cross-Border Data Transfers or Access by Overseas Personnel2	Maintenance2	User Category3	Number of Users3	Can be accessed from the Internet?3	Involvement in Cross-Border Data Transfers or Access by Overseas Personnel3	Maintenance3	User Category4	Number of Users4	Can be accessed from the Internet?4	Involvement in Industrial Data	Involvement in Cross-Border Data Transfers or Access by Overseas Personnel4	Availability of Internet Community or Forum Features1	Maintenance4	Infrastructure Deployment2	User Category5	Number of Users5	Can be accessed from the Internet?5	Involvement in Cross-Border Data Transfers or Access by Overseas Personnel5	Use of International Dedicated Lines or VPN Services	Maintenance5	Infrastructure Deployment3	User Category6	Number of Users6	Can be accessed from the Internet?6	Whether the personal information (e.g. name, phone number) is collected?2	Involvement in Cross-Border Data Transfers or Access by Overseas Personnel6	Classification as Industrial Internet	Maintenance6	The customer of the application or product is classified as Critical Information Infrastructure2	User Category7	Number of Users7	Can be accessed from the Internet?7	Whether the personal information (e.g. name, phone number) is collected?3	Involvement in Industrial Data1	Involvement in Cross-Border Data Transfers or Access by Overseas Personnel7	Use of / Reliance on Cryptographic Products or Critical Network Equipment	The customer of the application or product is classified as Critical Information Infrastructure	User Category8	Number of Users8	Can be accessed from the Internet?8	User Category9	Number of Users9	Can be accessed from the Internet?9	Whether the personal information (e.g. name, phone number) is collected?4	Involvement in Cross-Border Data Transfers or Access by Overseas Personnel8	Maintenance7	Use of / Reliance on Cryptographic Products or Critical Network Equipment1	The customer of the application or product is classified as Critical Information Infrastructure1"""

# Categories 映射规则
CATEGORY_RULES = {
    "01": ["01.访问控制", "02.日志管理", "03.漏洞管理", "04.备份与加密", "05.其他网络安全保护措施",
           "06.网络安全等级保护", "10.网站_APP"],
    "02": ["01.访问控制", "02.日志管理", "03.漏洞管理", "04.备份与加密", "05.其他网络安全保护措施",
           "06.网络安全等级保护", "07.数据保护-个人信息处理", "08.工业数据", "10.网站_APP"],
    "03": ["01.访问控制", "02.日志管理", "03.漏洞管理", "04.备份与加密", "05.其他网络安全保护措施",
           "06.网络安全等级保护", "08.工业数据"],
    "04": ["01.访问控制", "02.日志管理", "03.漏洞管理", "04.备份与加密", "05.其他网络安全保护措施",
           "06.网络安全等级保护", "08.工业数据"],
    "05": ["01.访问控制", "02.日志管理", "03.漏洞管理", "04.备份与加密", "05.其他网络安全保护措施",
           "06.网络安全等级保护", "07.数据保护-个人信息处理", "10.网站_APP"],
    "06": ["01.访问控制", "02.日志管理", "03.漏洞管理", "04.备份与加密", "05.其他网络安全保护措施",
           "06.网络安全等级保护"],
    "07": ["01.访问控制", "02.日志管理", "03.漏洞管理", "04.备份与加密", "05.其他网络安全保护措施",
           "06.网络安全等级保护", "08.工业数据", "15.云服务安全责任"],
    "08": ["01.访问控制", "02.日志管理", "03.漏洞管理", "04.备份与加密"],
    "09": ["01.访问控制", "02.日志管理", "03.漏洞管理", "04.备份与加密"],
    "10": ["01.访问控制", "02.日志管理", "03.漏洞管理", "04.备份与加密", "05.其他网络安全保护措施",
           "06.网络安全等级保护", "08.工业数据", "16.工业控制系统"],
}


def check_field_with_suffix(data_dict, base_field, check_value, is_yes_check=True):
    """检查带数字后缀的字段"""
    pattern = re.compile(rf"^{re.escape(base_field)}\d*$")
    for key, value in data_dict.items():
        if pattern.match(key):
            if is_yes_check and value.strip().lower() == "yes":
                return True
            elif not is_yes_check and value.strip() == check_value:
                return True
    return False


def get_checklists(data_dict):
    """根据JSON数据获取检查表列表"""
    output = set()

    # === General 规则 ===
    categories = data_dict.get("Categories", "")
    if categories:
        # 提取前两位数字作为类别编号
        match = re.match(r"^(\d{2})\.", categories)
        if match:
            category_code = match.group(1)
            if category_code in CATEGORY_RULES:
                output.update(CATEGORY_RULES[category_code])

    # === Specific 规则 ===
    # 1. 个人信息收集
    if check_field_with_suffix(data_dict, "Whether the personal information (e.g. name, phone number) is collected?",
                               "yes"):
        output.add("07.数据保护-个人信息处理")

    # 2. 工业数据
    if check_field_with_suffix(data_dict, "Involvement in Industrial Data", "yes"):
        output.add("08.工业数据")

    # 3. 数据跨境传输
    if check_field_with_suffix(data_dict, "Involvement in Cross-Border Data Transfers or Access by Overseas Personnel",
                               "yes"):
        output.add("09.数据跨境传输")

    # 4. 互联网社区论坛
    if check_field_with_suffix(data_dict, "Availability of Internet Community or Forum Features", "yes"):
        output.add("11.互联网社区论坛")

    # 5. 工业互联网
    if check_field_with_suffix(data_dict, "Classification as Industrial Internet", "yes"):
        output.add("12.工业互联网")

    # 6. 国际专线/VPN
    if check_field_with_suffix(data_dict, "Use of International Dedicated Lines or VPN Services", "yes"):
        output.add("13.国际专线_VPN适用")

    # 7. 第三方服务商管理
    if check_field_with_suffix(data_dict, "Maintenance", "Third-party vendor managed", is_yes_check=False):
        output.add("14.第三方服务商管理")

    # 8. 云服务安全责任
    if check_field_with_suffix(data_dict, "Infrastructure Deployment", "Public Cloud", is_yes_check=False):
        output.add("15.云服务安全责任")

    # 9. 密码产品/网络关键设备
    pattern = re.compile(r"^Use of / Reliance on Cryptographic Products or Critical Network Equipment\d*$")
    for key, value in data_dict.items():
        if pattern.match(key):
            if value.strip() == "Critical Network Equipment":
                output.add("18.网络关键设备及网络安全专用产品")
            elif value.strip() == "Cryptographic Product":
                output.add("17.密码产品")

    # 10. 关键信息基础设施
    if check_field_with_suffix(data_dict,
                               "The customer of the application or product is classified as Critical Information Infrastructure",
                               "yes"):
        output.add("19.关键信息基础设施运营者的特殊要求")

    # 按编号排序输出
    return sorted(output, key=lambda x: int(re.match(r"(\d+)", x).group(1)))


# === 主程序 ===
# 数据由用户输入（制表符分隔）
data = input("请粘贴从Excel复制的数据行：")

# 按制表符分割
header_list = headers.split('\t')
data_list = data.split('\t')

# 检查字段数量是否匹配
if len(header_list) != len(data_list):
    print(f"警告：表头有 {len(header_list)} 个字段，数据有 {len(data_list)} 个字段，数量不匹配！")
else:
    print(f"字段数量匹配：{len(header_list)} 个字段")

# 创建字典，仅保留有数据的键值对
result_dict = {}
for key, value in zip(header_list, data_list):
    if value.strip():
        result_dict[key] = value

# 转为 JSON 字符串（格式化输出）
json_str = json.dumps(result_dict, ensure_ascii=False, indent=2)

print(f"\n有效字段数量：{len(result_dict)} 个")
print("=== JSON 数据 ===")
print(json_str)

# 获取检查表列表
checklists = get_checklists(result_dict)

print("\n=== 需要推送的检查表 ===")
for item in checklists:
    print(f"  • {item}")
print(f"\n总计 {len(checklists)} 个检查表需要推送。")
