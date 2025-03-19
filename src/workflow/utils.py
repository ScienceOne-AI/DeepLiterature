# encoding: utf-8
import io
import base64
import time
import concurrent.futures
import json
import re
import requests
import shortuuid

from agents import CodeAgent, OrchestratorAgent
from tools.executors import CodeExecutor, SearchExecutor
from config import JINA_API_KEY, JINA_API_URL, LANGUAGE
from utils.message_queue import WrapperQueue
from utils.logger import model_logger


mclick_tool = {
    "type": "function",
    "function": {
        "name": "mclick",
        "description": "当你获取的信息包含 link 的 URL 信息并希望深入获取更详细的内容时，使用此功能。将所有需要解析的 URL 根据 idx 形成索引列表，解析每个索引对应的 URL 并提取主要的文本信息。",
        "parameters": {
            "type": "object",
            "properties": {
                "idx_list": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "需要检索网页的索引 (idx) 列表。"
                },
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "要提取文本的HTML标签列表。默认值为['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']。"
                },
                "include_links": {
                    "type": "boolean",
                    "description": "是否在提取的文本中包含超链接。默认值为False。",
                    "default": False
                },
                "clean": {
                    "type": "boolean",
                    "description": "是否在解析返回文本之前，去除脚本、样式和其他非文本元素。默认值为True。",
                    "default": True
                }
            },
            "required": [
                "idx_list"
            ]
        }
    }
}

webSearch_tool = {
    "type": "function",
    "function": {
        "name": "webSearch",
        "description": "通过搜索引擎检索相关的页面的摘要或完整内容，适用于快速获取主题的简明概述。当你需要权威的简短总结而不需要深入分析或实时信息时，可以使用此功能。不适用于翻译或需要更详细、多样化的信息源的情况。",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "在网页上搜索的主要关键词或主题。"
                },
                "max_results": {
                    "type": "integer",
                    "description": "要检索的相关页面的最大数量。适用于限制搜索范围。",
                    "default": 10
                }
            },
            "required": [
                "keyword"
            ]
        }
    }
}

codeRunner_tool = {
    "type": "function",
    "function": {
        "name": "CodeRunner",
        "description": "This Plugin will be called to run python code and fetch results within 60s, especially processing math, computer, picture and file etc. Firstly, LLM will analyse the problem and output the steps of solving this problem with python. Secondly, LLM generates code to solve problems with steps immediately. LLM will adjust code referring to the error message until success. When LLM receives file links, put the file url and the file name in the parameter upload_file_url and upload_file_name, the plugin will save it to \"/mnt/data\", alse put code in the parameter code to output file basic info.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "description": "code",
                    "type": "string"
                },
                "upload_file_name": {
                    "description": "save the upload_file_url with the corresponding filename.",
                    "type": "string"
                },
                "upload_file_url": {
                    "description": "when recieve file link, then the plugin will save it to \"/mnt/data\"",
                    "type": "string"
                }
            },
            "required": [
                "code"
            ]
        }
    }
}


def run_code(code_agent: CodeAgent, code_executor: CodeExecutor, meta_data, all_steps, step_idx, question, previous_reference, reference_list, verbose=False, context=dict(), queue=WrapperQueue(), api_queue=WrapperQueue(), request_id=None):
    now_step_keywords = all_steps[step_idx]['now_step_keywords']
    all_codes = []
    all_code_results = []
    if verbose:
        for new_keyword in now_step_keywords:
            # 生成对应的代码
            queue.put(["bar", f"🐍 智能体 · 生成代码：\n:grey-background[{new_keyword}]"])
            context["online_steps"].append(f"🐍 智能体 · 生成代码：\n:grey-background[{new_keyword}]")
            placeholder_think = None
            placeholder_answer = None
            _reasoning_content = ""
            now_code = ""
            now_messages = meta_data.get("messages", [])
            cur_size = len(now_messages)
            for label, _stream_text in code_agent.run(question, new_keyword, previous_reference, reference_list):
                if label == "think":
                    _reasoning_content += _stream_text
                    if placeholder_think is None:
                        queue.put(["placeholder_begin", None])
                        context["online_steps"].append("")
                        placeholder_think = "placeholder_begin"
                    queue.put(["placeholder_think_stream_markdown", convert_think_message_to_markdown(_reasoning_content)])
                    context["online_steps"][-1] = convert_think_message_to_markdown(_reasoning_content)
                    api_queue.put(format_data(reasoning_content=_stream_text, id=request_id, stage="create code"))
                elif label == "answer":
                    now_code += _stream_text
                    if placeholder_answer is None:
                        queue.put(["placeholder_begin", None])
                        context["online_steps"].append("")
                        placeholder_answer = "placeholder_begin"
                    queue.put(["placeholder_answer_plain_text", now_code])
                    context["online_steps"][-1] = now_code
                    api_queue.put(format_data(content=_stream_text, id=request_id, stage="create code"))
                elif label == "final_answer":
                    now_code = _stream_text
            now_messages.append({"reasoning_content": _reasoning_content, "content": now_code, "role": "assistant", "stage": "create code"})
            queue.put(["placeholder_answer_markdown", f"""```python\n\n{now_code}\n\n```"""])
            context["online_steps"][-1] = """```python\n\n{now_code}\n\n```"""
            all_codes.append(now_code)
            context["online_steps"].append(f"🐍 智能体 · 生成代码：\n:grey-background[{new_keyword}]\n\n" + "```python\n\n" + now_code + "\n\n```")
            # 执行代码
            queue.put(["placeholder_begin", None])
            queue.put(["placeholder_caption", "⏳ 调工具 · 代码执行中..."])
            context["online_steps"].append("⏳ 调工具 · 代码执行中...")
            code_results = code_executor.execute(now_code)
            all_code_results.append(code_results)
            queue.put(["placeholder_bar", "📊 调工具 · 代码结果为："])

            context["online_steps"].append("📊 调工具 · 代码结果为：")
            now_messages.append({"content": "", "img": "", "role": "assistant", "stage": "run code and get result"})
            api_queue.put(format_data(content="-"*20 + "\n\n", id=request_id, stage="run code and get result"))
            # 返回代码结果
            for code_result in code_results:
                if "text" in code_result:
                    queue.put(["code_result_text", code_result['text']])
                    context["online_steps"].append(code_result)
                    now_messages[-1]["content"] = code_result['text']
                    api_queue.put(format_data(content=code_result['text'] + "\n\n", id=request_id, stage="run code and get result"))
                if "img" in code_result:
                    queue.put(["code_result_image",code_result['img']])
                    context["online_steps"].append(code_result)
                    now_messages[-1]["imge"] = code_result['img']
                    api_queue.put(format_data(content="img:\n\n"+ str(code_result['img']) + "\n\n", id=request_id, stage="run code and get result"))

    queue.put(["divider", None])
    context["online_steps"].append("\n---\n")


    return all_codes,all_code_results




def fetch_search_result(all_steps, step_idx, old_raw_info, verbose=False, search_type="wiki", context=dict(), queue=WrapperQueue()):
    start_time = time.time()
    now_step_keywords = all_steps[step_idx]['now_step_keywords']
    now_step_keyword_idxs = all_steps[step_idx]['now_step_keyword_idxs']
    if verbose:
        render_text = ""
        for new_keyword in now_step_keywords:
            render_text += ":grey-background[" + new_keyword + "] "
        queue.put(["bar", "🤖 智能体 · 生成关键词：" + render_text])
        context["online_steps"].append("🤖 智能体 · 生成关键词：" + render_text)
        queue.put(["bar", "🔍 调工具 · 搜索引擎"])
        context["online_steps"].append("🔍 调工具 · 搜索引擎")
    # 构建新的 raw_info 
    # 新位置开始的 index
    start_index = now_step_keyword_idxs[0]
    start_doc_idx = 0
    new_raw_info = []
    for raw_idx, raw_info in enumerate(old_raw_info):
        # 之前的所有 raw_info 直接保留
        if raw_idx < start_index:
            new_raw_info.append(raw_info)
            start_doc_idx += len(raw_info)

    new_titles = set()
    is_empty_search = 0
    search_executor = SearchExecutor(search_type)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for new_keyword in now_step_keywords:
            futures.append(executor.submit(search_executor.execute, new_keyword, verbose))


        for future in concurrent.futures.as_completed(futures):
            new_keyword, empty_search, new_keyword_search_res = future.result()
            if not empty_search:
                queue.put(["bar", f"🧐 智能体 · 浏览关键词 :grey-background[{new_keyword}] 的搜索结果："])
                context["online_steps"].append(f"🧐 智能体 · 浏览关键词 :grey-background[{new_keyword}] 的搜索结果：")
                context["online_steps"].append([])
                queue.put(["container_begin", {"height":200}])
                for now_info_idx, now_info in enumerate(new_keyword_search_res):
                    new_keyword_search_res[now_info_idx]['title'] = new_keyword_search_res[now_info_idx]['title'].replace("\n", " ")
                    msg = "📃{idx} - {title} - 🔗 [click]({url}) \n> :grey[{snippet}]\n\n".format(idx=int(start_doc_idx + now_info_idx) + 1, title=new_keyword_search_res[now_info_idx]['title'], url=new_keyword_search_res[now_info_idx]['url'], snippet=new_keyword_search_res[now_info_idx].get("snippet"))
                    queue.put(["container_content", msg])
                    context["online_steps"][-1].append(msg)
            else:
                queue.put(["bar", f"⚠️ 调工具 · 搜索关键词 :grey-background[{new_keyword}] 失败"])
                context["online_steps"].append(f"⚠️ 调工具 · 搜索关键词 :grey-background[{new_keyword}] 失败")
                is_empty_search += 1

            # 添加新的检索结果
            new_raw_info.append(new_keyword_search_res)
            start_doc_idx += len(new_keyword_search_res)
            for search_doc in new_keyword_search_res:
                new_title = search_doc['title']
                new_titles.add(new_title)

    queue.put(["divider", None])
    context["online_steps"].append("\n---\n")
    new_titles = list(new_titles)


    # 打印日志
    empty_search = True if is_empty_search > len(now_step_keywords)/2 else False
    in_out = {"state": "update_raw_info", "input": {"all_steps": all_steps, "step_idx":step_idx, "old_raw_info": old_raw_info, "verbose": verbose,  "search_type": search_type}, \
                "output": {"empty_search": empty_search, "new_raw_info":new_raw_info}, "cost_time": str(round(time.time()-start_time, 3))}
    model_logger.info(json.dumps(in_out, ensure_ascii=False))
    return empty_search, new_raw_info

def process_message(content = "",role = "system", tool_calls = [] , tool_call_id = "", result_list = [], content_ref = ""):
    message = {}
    message['content'] = content
    if len(content_ref) > 0:
        message['content_ref'] = content_ref
    message['role'] = role
    if len(tool_calls) > 0:
        message['tool_calls'] = tool_calls
    if len(tool_call_id) > 0:
        message['tool_call_id'] = tool_call_id
    
    if len(result_list) > 0:
        message['result_list'] = result_list

    return message


def generate_call_id():
    short_uuid = shortuuid.uuid()
    # 自定义格式化，例如添加前缀和截取部分字符
    custom_id = f"call_{short_uuid[:24]}"
    return custom_id

def get_tool_list(use_tool_record):
    tool_list = []
    if "webSearch" in use_tool_record:
        tool_list.append(webSearch_tool)
    if "mclick" in use_tool_record:
        tool_list.append(mclick_tool)
    if "codeRunner" in use_tool_record:
        tool_list.append(codeRunner_tool)
    return tool_list


def count_token(tokenizer, text):
    now_inputs = tokenizer([text], return_tensors="pt")
    return len(now_inputs['input_ids'][0])


def step_by_step_process(search_process):
    if "->" in search_process:
        stage_list = [stage.strip() for stage in search_process.split("->")]
    else:
        stage_list = [search_process.strip()] # 说明是单步的

    key_stage = []
    start = -1
    end = -1
    for idx, stage in enumerate(stage_list):
        if "webSearch" in stage:
            start = idx
            if end < start:
                end = start
        else:
            end = idx
            key_stage.append([start,end])
            start = idx + 1
            end = idx + 1
    if start == end and start != -1:
        key_stage.append([start,end])
  

    step_process = []
    step_chain = ""
    keyword_idx = 0
    for start_end in key_stage:
        now_start = start_end[0]
        now_end = start_end[1]
        step_chain = " -> ".join(stage_list[now_start: now_end + 1])
        now_keywords = OrchestratorAgent.parse_keywords(" -> ".join(stage_list[now_start: now_end + 1]))
        now_idxs = [keyword_idx + i for i in range(len(now_keywords))]
        keyword_idx += len(now_keywords)
        tmp = {
            "step_desc": step_chain,
            "now_step_keywords": now_keywords,
            "now_step_keyword_idxs" : now_idxs
        }
        step_process.append(tmp)

    return step_process


def step_by_step_process(search_process):
    search_process = search_process.split("\n\n")[0]
    # 将 search_process 加工成多步的，后面的步骤需要 mask 掉
    if "->" in search_process:
        stage_list = [stage.strip() for stage in search_process.split("->")]
    elif "→" in search_process:
        stage_list = [stage.strip() for stage in search_process.split("→")]
    else:
        stage_list = [search_process.strip()] # 说明是单步的

    key_stage = []
    start = -1
    end = -1
    for idx, stage in enumerate(stage_list):
        if "webSearch" in stage or "codeRunner" in stage:
            # 处理上一个还是关键词的情况
            if start == end and end != -1 and start != idx:
                key_stage.append([start,end])
            start = idx
            if end < start:
                end = start
        else:
            end = idx
            key_stage.append([start,end])
            start = idx + 1
            end = idx + 1
    if start == end and start != -1:
        key_stage.append([start,end])
  
    step_process = []
    step_chain = ""
    keyword_idx = 0
    for start_end in key_stage:
        now_start = start_end[0]
        now_end = start_end[1]
        step_chain = " -> ".join(stage_list[now_start: now_end + 1])
        now_keywords = OrchestratorAgent.parse_keywords(" -> ".join(stage_list[now_start: now_end + 1]))
        now_idxs = [keyword_idx + i for i in range(len(now_keywords))]
        keyword_idx += len(now_keywords)
        tmp = {
            "step_desc": step_chain,
            "now_step_keywords": now_keywords,
            "now_step_keyword_idxs" : now_idxs
        }
        step_process.append(tmp)

    return step_process



def function_call_sent(argument_values_list, call_ids, function_name = "wikiSearch", argument_names = ["keyword"], content = ""):
    tool_calls = []
    for argument_values, call_id in zip(argument_values_list, call_ids):
        arguments = {}
        for argument_name, argument_value  in zip(argument_names, argument_values):
            arguments[argument_name] = argument_value
        tmp = {
            "id": call_id,
            "type": "function",
            "function": {
                "name": function_name,
                "arguments": json.dumps(arguments, ensure_ascii=False)
            }
        }
        tool_calls.append(tmp)
    return process_message(role = "assistant", tool_calls=tool_calls, content = content)


def function_call_receive_code_results(now_step_keywords, all_codes, call_ids, raw_code_results):
    now_messages = []
    evidences = []
    for idx, raw_code_result in enumerate(raw_code_results):
        code_result_text_list = ["Code:\n" + all_codes[idx] + "Result:\n"]
        img_idx = 1
        for code_idx, code_result in enumerate(raw_code_result):
            if "img" in code_result:
                code_result_text_list.append(f"![fig-{img_idx}]({now_step_keywords[idx]}_result_{call_ids[idx]}_{img_idx}.png)")
                raw_code_result[code_idx]['img_idx'] = img_idx
                raw_code_result[code_idx]['img_path'] = f"{now_step_keywords[idx]}_result_{call_ids[idx]}_{img_idx}.png"
                img_idx += 1
            else: 
                code_result_text_list.append(code_result['text'])
                
        now_messages.append(process_message(content = "\n\n".join(code_result_text_list), role = "tool", tool_call_id = call_ids[idx], result_list = raw_code_result))
        evidences.append("\n\n".join(code_result_text_list))
    return evidences, now_messages

def function_call_receive_snippet(keywords, call_ids, search_res, raw_info):
    now_messages = []
    for idx, keyword in enumerate(keywords):
        document_list = []
        for now_search in search_res[idx]:
            now_doc = {
                now_search['idx']:f"{now_search['title']}\nsnippet:{now_search['snippet']}\nlink:{now_search['url']}"
            }
            document_list.append(now_doc)
        now_messages.append(process_message(content = json.dumps(document_list, ensure_ascii=False), role = "tool", tool_call_id = call_ids[idx], result_list = raw_info[idx]))

    return now_messages

def function_call_receive_document(idx_list, call_ids, search_res, context=dict(), queue=WrapperQueue()):
    def receive_document(url, idx, title):
        return analysis_url_api(url), url, idx, title
    ii = 0
    document_list = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for mclick_idx in idx_list:
            for now_search in search_res:
                for doc_info in now_search:
                    if str(doc_info['idx']) == str(mclick_idx):
                        # time.sleep(1)
                        futures.append(executor.submit(receive_document, doc_info['url'], doc_info['idx'], doc_info['title']))
        
        queue.put(["container_begin", {"height": min(len(futures) * 60, 200)}])
        # 获取所有任务的结果并将其添加到 document_list 列表中
        for future in concurrent.futures.as_completed(futures):
            parse_response, now_url, now_idx, now_title = future.result()
            # 处理获取网页快照失败的情况
            if parse_response == "":
                parse_response = doc_info['snippet']
                queue.put(["container_bar", f"⚠️ 调工具 · 打不开 :blue-background[📃{now_idx + 1} {now_title}]  - 🔗[click]({now_url} \"{now_url}\")"])
                context["online_steps"].append(f"⚠️ 调工具 · 打不开 :blue-background[📃{now_idx + 1} {now_title}]  - 🔗[click]({now_url} \"{now_url}\")")
            else:
                queue.put(["container_bar", f"🤓 智能体 · 阅读完毕 :blue-background[📃{now_idx + 1} {now_title}]  - 🔗[click]({now_url} \"{now_url}\")"])
                context["online_steps"].append(f"🤓 智能体 · 阅读完毕 :blue-background[📃{now_idx + 1} {now_title}]  - 🔗[click]({now_url} \"{now_url}\")")
                    
                    
                now_doc = {
                    # content 通过 URL 解析获得
                    now_idx:f"{now_title}\n{parse_response}\nlink:{now_url}"
                }
                document_list.append(now_doc)
    queue.put(["divider", None])
    context["online_steps"].append("\n---\n")
    return process_message(content = json.dumps(document_list, ensure_ascii=False), role = "tool", tool_call_id = call_ids[ii])


def update_search_res(all_steps, step_idx, old_search_res, raw_infos, verbose=False, context=dict()):
    start_time = time.time()
    now_step_keywords = all_steps[step_idx]['now_step_keywords']
    now_step_keyword_idxs = all_steps[step_idx]['now_step_keyword_idxs']
    start_index = now_step_keyword_idxs[0]
    new_search_res = []
    start_doc_idx = 0
    
    # 更新 search_res
    for search_idx, search_res in enumerate(old_search_res):
        # 跳过之前的所有 search_res
        if search_idx < start_index:
            new_search_res.append(search_res)
            start_doc_idx += len(search_res)

    for raw_idx, raw_info in enumerate(raw_infos):
        if raw_idx < start_index:
            continue
        this_time_search = []
        title_set = set()
        for i, doc_info in enumerate(raw_info):

            now_content = ""

            tmp = {
                "title": doc_info['title'],
                'snippet': doc_info['snippet'],
                'content': now_content,
                'url': doc_info['url'],
                'idx': start_doc_idx,
            }
            
            # 根据网页title去重
            if doc_info['title'] not in title_set:
                title_set.add(doc_info['title'])
                this_time_search.append(tmp)
                if verbose:
                    context["online_url_lists"].append(tmp)
                start_doc_idx += 1
            # 最多 10 篇文章
            if i == 9:
                break
        new_search_res.append(this_time_search)


    in_out = {"state": "update_search_res", "input": {"all_steps": all_steps, "step_idx":step_idx, "old_search_res": old_search_res, "verbose": verbose,  "raw_infos": raw_infos}, \
                "output": {"new_search_res": new_search_res}, "cost_time": str(round(time.time()-start_time, 3))}
    model_logger.info(json.dumps(in_out, ensure_ascii=False))

    return new_search_res

def find_special_text_and_numbers(text):
    # 定义正则表达式模式
    pattern = r'◥\[(\d+(?:[,\，]\s*\d+)*)\]◤'
    matches = re.findall(pattern, text)
    # 提取文本和数字列表
    special_texts = [f'◥[{nums}]◤' for nums in matches]
    number_lists = [[int(num) for num in re.split(r'[,\，]', nums)] for nums in matches]
    
    return special_texts, number_lists

def remove_ref_tag(origin_llm_answer):
    new_llm_answer = origin_llm_answer
    special_texts, special_numbers = find_special_text_and_numbers(origin_llm_answer)
    for special_id, numbers in enumerate(special_numbers):
        new_llm_answer = new_llm_answer.replace(special_texts[special_id], "")
    return new_llm_answer


def analysis_url_api(analysis_url):
    if JINA_API_URL.endswith("/"):
        url = f"{JINA_API_URL}{analysis_url}"
    else:
        url = f"{JINA_API_URL}/{analysis_url}"
    headers = {
    "Authorization": f"Bearer {JINA_API_KEY}"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return ""
    return response.text


def convert_think_message_to_markdown(message):
    lines = message.split("\n")
    if LANGUAGE == "zh":
        markdown_text = """> <font color=grey size=2>深度思考...</font><br>\n"""
    elif LANGUAGE == "en":
        markdown_text = """> <font color=grey size=2>Deep Thingking...</font><br>\n"""
    markdown_text += "<br>\n".join([f"""> <font color=grey size=2>{line}</font>""" for line in lines])
    return markdown_text


def format_data(reasoning_content=None, content=None, id="", finish=False, **kwargs):
    result = {
        "id": id,
        "created": int(time.time()),
        "choices": [
            {
                "index": 0,
                "delta": {}
            }
        ]
    }
    for key, item in kwargs.items():
        if key in result:
            continue
        result[key] = item
    if finish:
        result["choices"][0]["finish_reason"] = "stop"
    elif reasoning_content is not None:
        result["choices"][0]["delta"]["reasoning_content"] = reasoning_content
    elif content is not None:
        result["choices"][0]["delta"]["content"] = content
    return result