# encoding: utf-8
import os
import re
import time
import pandas as pd
import json
from datetime import datetime
import pytz

from config import LANGUAGE

def get_real_time_str():
    now_utc = datetime.now(pytz.utc)
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now_beijing = now_utc.astimezone(beijing_tz)

    formatted_date = now_beijing.strftime("%Y-%m-%d")
    formatted_time = now_beijing.strftime("%H:%M:%S")
    return f"{formatted_date} {formatted_time}"

def get_location_by_ip():
    if LANGUAGE == "en":
        location_response = {
            "city": "Beijing",
            "regionName": "Beijing",
            "country": "China",
        }
    else:
        location_response = {
                "city": "北京",
                "regionName": "北京市",
                "country": "中国",
            }
    location_response = json.dumps(location_response)
    location_data = json.loads(location_response)
    
    
    city = location_data.get('city', '未知')
    region = location_data.get('regionName', '未知')
    country = location_data.get('country', '未知')

    return f"{city}, {region}, {country}"



def escape_ansi(line: str) -> str:
    # 删除文本中的 ANSI 转移序列(ANSI 转义序列通常用于控制终端文本的样式，如颜色、粗体、下划线等)
    ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', line)

def split_process_jsonl(search_process):
    process_list = []
    for search_stage in search_process:
        is_websearch = False
        is_coderunner = False
        is_mclick = False
        content = ""
        for fc_option in search_stage:
            if fc_option['name'] == "webSearch":
                is_websearch = True
                content += ":grey-background[" + fc_option['keyword'] +"] "
            elif fc_option['name'] == "mclick":
                is_mclick = True
                fc_option['keyword'] = [idx + 1 for idx in fc_option['keyword']]
                for keyword in fc_option['keyword']:
                    content += ":blue-background[" + "📃" + str(keyword) +"] "
            elif fc_option['name'] == "CodeRunner":
                is_coderunner = True
                if len(fc_option['keyword']) > 19:
                    plat_text = fc_option['keyword'][:19].replace("\n", " ").replace("\r", " ")
                else:
                    plat_text = fc_option['keyword'].replace("\n", " ").replace("\r", " ")
                content += ":grey-background[" + f"🐍 {plat_text}..." +"] "

        if is_websearch:   
            process_list.append("🤖 智能体 · 生成关键词：" + content)
            process_list.append("🔍 调工具 · 搜索引擎")

        if is_mclick:
            process_list.append("🤖 智能体 · 选择网页深入阅读：" + content)
            process_list.append("📖 调工具 · 网页阅读")
            # st.write("📖 打开：" + content)

        if is_coderunner:
            process_list.append("🤖 智能体 · 生成代码：" + content)
            process_list.append("🧩 调工具 · 代码执行")

    return process_list

def find_special_text_and_numbers(text):
    pattern = r'◥\[(\d+(?:[,\，]\s*\d+)*)\]◤'
    matches = re.findall(pattern, text)

    # 提取文本和数字列表
    special_texts = [f'◥[{nums}]◤' for nums in matches]
    number_lists = [[int(num) for num in re.split(r'[,\，]', nums)] for nums in matches]
    return special_texts, number_lists

def replace_ref_tag2md(origin_llm_answer, url_list):
    new_llm_answer = origin_llm_answer
    special_texts, special_numbers = find_special_text_and_numbers(origin_llm_answer)
    for special_id, numbers in enumerate(special_numbers):
        replace_str = ""
        # 遍历所有引用的标记
        for number in numbers:
            if number < len(url_list):
                new_title = url_list[number]['title'].replace('"', "'")
                replace_str += f" [:blue-background[{number + 1}]]({url_list[number]['url']} \"{new_title}\") "
            else:
                replace_str = ""
        new_llm_answer = new_llm_answer.replace(special_texts[special_id], replace_str)

    return new_llm_answer

def text_finish(idx, text):
    numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
    return "*:grey[" + numbers[idx-1] + " ~~" + text  + "~~]*  [:green[已完成]]"

def text_render(idx, text):
    numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
    if "已完成" in text:
        return text
    return numbers[idx-1] + " " + text

def is_mobile(user_agent):
    mobile_keywords = [
        'Android', 'iPhone', 'iPad', 'Windows Phone', 'Mobile', 'Symbian',
        'BlackBerry', 'Opera Mini', 'IEMobile', 'UCBrowser', 'MQQBrowser'
    ]
    
    # 检查User-Agent中是否包含手机端的关键词
    for keyword in mobile_keywords:
        if keyword.lower() in user_agent.lower():
            return True
    return False


def latex_render(text):
    text = text.replace("\\(","$").replace("\\)","$")  
    lines = text.splitlines()
    final_text = []
    for line in lines:
        if line[:6] == "![fig-":
            continue
        final_text.append(line)
    return "\n".join(final_text)

def yield_text(text, speed = 0.02):
    # 模拟流式输出
    i = 0  # 用来跟踪当前处理的字符位置
    while i < len(text):
        if text[i:i+17] == ":blue-background[" or text[i:i+17] == ":grey-background[":
            end_pos = i + 17  # 跳过 ":blue-background["
            while end_pos < len(text) and text[end_pos] not in [']']:
                end_pos += 1
            if end_pos < len(text):  # 找到匹配的结束符
                end_pos += 1  # 包含闭合符号
                yield text[i:end_pos]  # 一次性返回这一部分
                i = end_pos  # 更新 i 跳到下一个位置
        # 检查是否遇到以 http 开头的字符串
        elif text[i:i+4] == "http":
            end_pos = i + 4  # 跳过 "http"
            while end_pos < len(text) and text[end_pos] not in [")", "\n"]:
                end_pos += 1
            yield text[i:end_pos]  # 一次性返回这一段 URL，处理标题中乱码的问题
            i = end_pos  # 更新 i 跳到下一个位置
        else:
            # 如果没有特殊格式，逐字符返回
            yield text[i]
            i += 1
        time.sleep(speed)  # 模拟流式返回的延迟

def merge_jsonl(folder_path = "./datasets/web_8_turns"):
    # 初始化一个空的 DataFrame
    all_data = pd.DataFrame()

    # 遍历文件夹下所有的 .jsonl 文件
    for filename in os.listdir(folder_path):
        if filename.endswith('.jsonl'):
            file_path = os.path.join(folder_path, filename)
            df = pd.read_json(file_path, lines=True)
            df = df[df['messages'].apply(lambda x: len(x) >= 8)]
            all_data = pd.concat([all_data, df], ignore_index=True)

    return all_data
