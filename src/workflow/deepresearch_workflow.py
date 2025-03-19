# encoding: utf-8
import time
import json
import re
import traceback

from agents import OrchestratorAgent, OptimizerAgent, SelectorAgent, SufficiencyValidatorAgent, ReorchestratorAgent, AssitantAgent, CodeAgent
from tools.executors import CodeExecutor
from llms import LLMFactory
from utils.common_utils import latex_render, replace_ref_tag2md, get_location_by_ip, get_real_time_str
from utils.logger import model_logger
import uuid

from .utils import run_code, fetch_search_result
from .utils import function_call_receive_code_results, step_by_step_process, process_message
from .utils import function_call_receive_document, function_call_receive_snippet, function_call_sent, generate_call_id, get_tool_list, remove_ref_tag, update_search_res
from .utils import convert_think_message_to_markdown, format_data
from config import LANGUAGE, SEARCH_ENGINE, LLM_MODEL

def run(question, queue, api_queue, lang, context=dict(), save_jsonl_path="", debug_verbose=True, meta_verbose=False):
    try:
        run_throw_exception(question, queue, api_queue, lang, context=context, save_jsonl_path=save_jsonl_path,  debug_verbose=debug_verbose, meta_verbose=meta_verbose)
    except Exception as e:
        traceback.print_exc()
        queue.put(["exception", None])
        api_queue.put("exception")
    return

def run_throw_exception(question, queue, api_queue, lang, context=dict(), save_jsonl_path="", debug_verbose=True, meta_verbose=False):
    llm = LLMFactory.construct(LLM_MODEL)
    orchestrator = OrchestratorAgent(llm=llm, lang=lang)
    optimizer = OptimizerAgent(llm=llm, lang=lang)
    selector = SelectorAgent(llm=llm, lang=lang)
    validator = SufficiencyValidatorAgent(llm=llm, lang=lang)
    reorchestrator = ReorchestratorAgent(llm=llm, lang=lang)
    assitant = AssitantAgent(llm=llm, lang=lang)
    code_agent = CodeAgent(llm=llm, lang=lang)

    code_executor = CodeExecutor()

    request_id = str(uuid.uuid4())
    now_messages = []
    meta_data = {
        "time_stamp":f"{get_real_time_str()}",
        "question": context['question'],
        "feedback": None,
        "messages" : now_messages
    }
    context["question"] = question
    queue.put(["bar", "🖥️ 智能体 · 路径规划"])
    context["online_steps"].append("🖥️ 智能体 · 路径规划")
    result = dict()
    queue.put(["placeholder_begin", None])
    context["online_steps"].append("")
    _reasoning_content = ""
    for label, _stream_text in orchestrator.run(question):
        if label == "think":
            _reasoning_content += _stream_text
            queue.put(["placeholder_think_stream_markdown", convert_think_message_to_markdown(_reasoning_content)])
            context["online_steps"][-1] = convert_think_message_to_markdown(_reasoning_content)
            api_queue.put(format_data(reasoning_content=_stream_text, id=request_id, stage="orchestrating"))
        else:
            result = _stream_text
    now_messages.append({"reasoning_content": _reasoning_content, "content": _stream_text, "role": "assistant", "stage": "orchestrating"})
    context["if_search"] = result['if_search']
    context["if_code"] = result['if_code']
    context["search_type"] = result['search_type']
    context["search_process"] = result['search_process']

    raw_infos = []
    all_steps = step_by_step_process(context['search_process'])
    raw_info = [[] for _ in range(len(all_steps))]
    raw_infos.append(raw_info)

    context['raw_info'] = raw_infos
    context['search_res'] = raw_infos
    context['llm_answer'] = None


    if context['if_search'] == "否" and context['if_code'] == '否' or LANGUAGE == "en" and str(context['if_search']).lower() == "no" and str(context['if_code']).lower() == 'no':
        if debug_verbose:
            queue.put(["bar", ":grey[🫢 智能体 · 当前问题无需 Function]"])
            context["online_steps"].append(":grey[🫢 智能体 · 当前问题无需 Function]")
            start_time = time.time()
            llm_answer = ""
            for label, _stream_text in llm.stream_chat(user_content=question):
                if label == "answer":
                    llm_answer += _stream_text
                    api_queue.put(format_data(content=_stream_text, id=request_id, stage="answering without function calling"))
                else:
                    result = _stream_text
            context["online_answer"] = llm_answer
            now_messages.append({"content": context["online_answer"], "role": "assistant", "stage": "answering without function calling"})
            in_out = {"state": "model_answer", "input": question, "output": context["online_answer"], "cost_time": str(round(time.time()-start_time, 3))}
            model_logger.info(json.dumps(in_out, ensure_ascii=False))
    else:
        all_evidences= [] # 将所有的证据（文本）信息都记录下来
        code_evidences = [] # 将所有代码证据(文本)信息都记录下来
        code_results_dict_list = [] # 把代码最原始的计算结果保存下来
        empty_search = True
        empty_code = True
        use_tool_record = set()
        process_pipeline = ['system', 'user','step_by_step', 'assistant']
        for now_stage in process_pipeline:
            if now_stage == 'system':
                now_messages.append(process_message(f"You are a helpful assistant. 当前的时间为{get_real_time_str()}。当前所在地: {get_location_by_ip()}。"))
            elif now_stage == 'user':
                now_messages.append(process_message(content = context['question'], role = "user"))
            elif now_stage == 'step_by_step':
                # 进行路径的优化过程
                queue.put(["bar", "✏️ 智能体 · 路径优化"])
                context["online_steps"].append("✏️ 智能体 · 路径优化")
                queue.put(["placeholder_begin", None])
                context["online_steps"].append("")
                optimize_search_process_text = ""
                _reasoning_content = ""
                for label, _stream_text in optimizer.run(context['search_process']):
                    if label == "think":
                        _reasoning_content += _stream_text
                        queue.put(["placeholder_think_stream_markdown", convert_think_message_to_markdown(_reasoning_content)])
                        context["online_steps"][-1] = convert_think_message_to_markdown(_reasoning_content)
                        api_queue.put(format_data(reasoning_content=_stream_text, id=request_id, stage="optimize search process"))
                    else:
                        optimize_search_process_text = _stream_text
                now_messages.append({"reasoning_content": _reasoning_content, "content": optimize_search_process_text, "role": "assistant", "stage": "optimize search process"})
                if len(optimize_search_process_text) != 0:
                    context['search_process'] = optimize_search_process_text


                all_steps = step_by_step_process(context['search_process'])
                latest_search_process = context['search_process'] # 记录上一步的search_process
                for step_idx, step in enumerate(all_steps):
                    if "webSearch" in all_steps[step_idx]['step_desc']:                      
                        now_step_keywords = all_steps[step_idx]['now_step_keywords']
                        if len(now_step_keywords) == 0:
                            break

                        use_tool_record.add("webSearch")
                        

                        empty_search, new_raw_info = fetch_search_result(all_steps, step_idx, context['raw_info'], debug_verbose, search_type=SEARCH_ENGINE, context=context, queue=queue)
                        context['raw_info'] = new_raw_info  

                        if empty_search:
                            if debug_verbose:
                                queue.put(["error", "当前访问人数过多，网页被挤爆啦，请稍后尝试..."])
                            break

                        # 更新 search_res (未下载正文)
                        new_search_res = update_search_res(all_steps, step_idx, context['search_res'], context['raw_info'], debug_verbose, context=context)
                        context['search_res'] = new_search_res

                        now_step_keywords = all_steps[step_idx]['now_step_keywords']
                        now_step_keyword_idxs = all_steps[step_idx]['now_step_keyword_idxs']
                        argument_values_list = [[now_step_keyword] for now_step_keyword in now_step_keywords]
                        call_ids = [generate_call_id() for _ in range(len(now_step_keywords))]
                        
                        # 整合关键词和对应的搜索结果
                        now_message = function_call_sent(argument_values_list, call_ids, "webSearch")
                        now_messages.append(now_message)
                        api_queue.put(format_data(reasoning_content="", id=request_id, stage="web search", tool_calls=now_message["tool_calls"]))
                        now_search_res = []
                        now_raw_info = []
                        for now_step_keyword_idx in now_step_keyword_idxs:
                            now_search_res.append(context['search_res'][now_step_keyword_idx])
                            now_raw_info.append(context['raw_info'][now_step_keyword_idx])
                        now_message = function_call_receive_snippet(now_step_keywords, call_ids, now_search_res, now_raw_info)
                        now_messages.extend(now_message)
                        api_queue.put(format_data(content=now_message, id=request_id, stage="web search"))

                        idx_list = [] # 记录所有需要 URL 解析的文章 idx
                        now_content = "" # CoT 过程
                        now_evidence = [] # 记录当前拥有的所有证据信息
                        snippet_list = []

                        # 筛选相关的网页快照
                        for keyword_idx, now_search in enumerate(now_search_res):
                            for doc_info in now_search:
                                now_title = doc_info['title']
                                now_snippet = doc_info['snippet'].replace("\n", " ").replace("\r","")
                                if len(now_snippet) == 0:
                                    now_snippet = doc_info['title']
                                
                                snippet_list.append(f"idx:{doc_info['idx']} snippet `{now_snippet}`")

                        choose_snippet_list = []
                        queue.put(["bar", "🔬 智能体 · 筛选相关网页"])
                        context["online_steps"].append("🔬 智能体 · 筛选相关网页")
                        queue.put(["placeholder_begin", None])
                        context["online_steps"].append("")
                        _reasoning_content = ""
                        for label, _stream_text in selector.run(all_steps[step_idx]['step_desc'], snippet_list):
                            if label == "think":
                                _reasoning_content += _stream_text
                                queue.put(["placeholder_think_stream_markdown", convert_think_message_to_markdown(_reasoning_content)])
                                context["online_steps"][-1] = convert_think_message_to_markdown(_reasoning_content)
                                api_queue.put(format_data(reasoning_content=_stream_text, id=request_id, stage="determine relevance"))
                            else:
                                choose_snippet_list = _stream_text
                        api_queue.put(format_data(content=choose_snippet_list, id=request_id, stage="determine relevance"))
                        now_messages.append({"reasoning_content": _reasoning_content, "content": choose_snippet_list, "role": "assistant", "stage": "determine relevance"})
                        new_snippet_list = []
                        if debug_verbose:
                            render_text = ""
                            for choose_snippet_idx in choose_snippet_list:
                                render_text += ":grey-background[" + "🔗" + str(choose_snippet_idx + 1) +"] "
                            if len(render_text) == 0:
                                render_text = ":grey-background[无]"
                            queue.put(["bar", "🤔 智能体 · 和问题相关的网页有：" + render_text])
                            context["online_steps"].append("🤔 智能体 · 和问题相关的网页有：" + render_text)
                            
                        for keyword_idx, now_search in enumerate(now_search_res):
                            for doc_info in now_search:
                                if doc_info['idx'] in choose_snippet_list:
                                    now_snippet = doc_info['snippet'].replace("\n", " ").replace("\r","")
                                    now_evidence.append({doc_info['idx']:f"{doc_info['title']}\nsnippet:{now_snippet}\nlink:{doc_info['url']}"})
                                    new_snippet_list.append(f"idx:{doc_info['idx']} snippet `{now_snippet}`")
                        snippet_list = new_snippet_list
                        
                        # 判断当前网页快照信息是否足够
                        if len(snippet_list) > 0: 
                            response = dict()
                            queue.put(["bar", "🔬 智能体 · 判断网页数据是否足够"])
                            context["online_steps"].append("🔬 智能体 · 判断网页数据是否足够")
                            queue.put(["placeholder_begin", None])
                            context["online_steps"].append("")
                            _reasoning_content = ""
                            for label, _stream_text in validator.run(all_steps[step_idx]['step_desc'], "\n".join(snippet_list)):
                                if label == "think":
                                    _reasoning_content += _stream_text
                                    queue.put(["placeholder_think_stream_markdown", convert_think_message_to_markdown(_reasoning_content)])
                                    context["online_steps"][-1] = convert_think_message_to_markdown(_reasoning_content)
                                    api_queue.put(format_data(reasoning_content=_stream_text, id=request_id, stage="sufficency validating"))
                                else:
                                    response = _stream_text
                            now_messages.append({"reasoning_content": _reasoning_content, "content": response, "role": "assistant", "stage": "sufficency validating"})
                            now_content += response['analysis_sentence'] + "\n"
                            now_content += response['trans_sentence'] + "\n"
                            for snippet_sentence in response['snippet_sentence']:
                                now_content += snippet_sentence[2:] + "\n"
                                match = re.search(r'idx:(\d+)', snippet_sentence)
                                if snippet_sentence[0] == '×':
                                    if match:
                                        idx_number = int(match.group(1))
                                        # 说明当前网页快照需要解析URL内容
                                        idx_list.append(idx_number)
                                else:
                                    if match:
                                        idx_number = int(match.group(1))

                        # 解析URL内容
                        if len(idx_list) != 0:
                            api_queue.put(format_data(content=idx_list, id=request_id, stage="sufficency validating"))
                            use_tool_record.add("mclick")
                            render_text = ""
                            for mclick_idx in idx_list:
                                render_text += ":blue-background[" + "📃" + str(mclick_idx + 1) +"] "
                            queue.put(["bar", ":grey[😮 智能体 · 当前网页的信息似乎不太够，打开网页看一看...]"])
                            context["online_steps"].append(":grey[😮 智能体 · 当前网页的信息似乎不太够，打开网页看一看...]")
                            
                            queue.put(["bar", "🤨 智能体 · 这些网页需要打开：" + render_text])
                            context["online_steps"].append("🤨 智能体 · 这些网页需要打开：" + render_text)

                            queue.put(["bar", "📖 调工具 · 网页阅读"])
                            context["online_steps"].append("📖 调工具 · 网页阅读")
                            argument_values_list = [idx_list]
                            call_ids = [generate_call_id()] 
                            # 整合URL和对应的解析内容
                            now_message = function_call_sent([argument_values_list], call_ids, "mclick", ["idx_list"], now_content)
                            now_messages.append(now_message)
                            api_queue.put(format_data(reasoning_content="", id=request_id, stage="fetch page body", tool_calls=now_message["tool_calls"]))
                            now_message = function_call_receive_document(idx_list, call_ids, now_search_res, context=context, queue=queue)
                            api_queue.put(format_data(content=now_message, id=request_id, stage="fetch page body"))
                            now_messages.append(now_message)
                            document_list = json.loads(now_message['content'])

                            # 更新evidence，将 document_list 中出现的，用正文信息代替原来证据句对应的网页快照
                            for i, evi_dict in enumerate(now_evidence):
                                key1 = next(iter(evi_dict))
                                for doc_dict in document_list:
                                    key2 = next(iter(doc_dict))
                                    if str(key1) == str(key2):
                                        now_evidence[i][key1] = doc_dict[key2]
                        else:
                            queue.put(["bar","😏 智能体 · 分析完毕"])
                            context["online_steps"].append("😏 智能体 · 分析完毕")
                            queue.put(["divider", None])
                            context["online_steps"].append("\n---\n")
                        now_evidence_list = [json.dumps(evi_dict,ensure_ascii=False) for evi_dict in now_evidence]
                        all_evidences.extend(now_evidence_list)
                        if len(now_evidence_list) > 0:
                            # 根据当前的状态信息（当前evidence、当前步骤、整体步骤）重新规划路径
                            if step_idx != len(all_steps) - 1:
                                response = dict()
                                queue.put(["bar","🔬 智能体 · 依据当前状态重新规划路径"])
                                context["online_steps"].append("🔬 智能体 · 依据当前状态重新规划路径")
                                queue.put(["placeholder_begin", None])
                                context["online_steps"].append("")
                                _reasoning_content = ""
                                for label, _stream_text in reorchestrator.run(context['question'], now_evidence_list, all_steps[step_idx]['step_desc'], latest_search_process):
                                    if label == "think":
                                        _reasoning_content += _stream_text
                                        queue.put(["placeholder_think_stream_markdown", convert_think_message_to_markdown(_reasoning_content)])
                                        context["online_steps"][-1] = convert_think_message_to_markdown(_reasoning_content)
                                        api_queue.put(format_data(reasoning_content=_stream_text, id=request_id, stage="reorchestrate"))
                                    else:
                                        response = _stream_text
                                now_messages.append({"reasoning_content": _reasoning_content, "content": response, "role": "assistant", "stage": "reorchestrate"})
                                latest_search_process = response['update_whole_step']
                                all_steps = step_by_step_process(latest_search_process)
                                queue.put(["bar",f"🔨更新为流程：{latest_search_process}"])
                                context["online_steps"].append(f"🔨更新为流程：{latest_search_process}")
                                api_queue.put(format_data(content=latest_search_process, id=request_id, stage="reorchestrate"))
                            else:
                                context['search_process'] = latest_search_process
                                break
                        else:
                            start_index = latest_search_process.find("-> " + all_steps[step_idx]['step_desc']) 
                            latest_search_process = latest_search_process[:start_index] + "-> " + all_steps[step_idx]['step_desc']
                            all_steps = step_by_step_process(latest_search_process)
                            context['search_process'] = latest_search_process
                            break

                    else:
                        empty_code = False
                        use_tool_record.add("codeRunner")
                        now_step_keywords = all_steps[step_idx]['now_step_keywords']
                        if len(now_step_keywords) == 0:
                            if debug_verbose:
                                pass
                            continue
                        # 构建参考信息
                        if step_idx == 0:
                            if LANGUAGE == "en":
                                previous_reference = "None"
                            else:
                                previous_reference = "无"
                        else:
                            previous_reference = all_steps[step_idx - 1]['step_desc'] # 把上一步作为参考信息
                        all_codes, all_code_results = run_code(code_agent, code_executor, meta_data,all_steps, step_idx, context['question'], previous_reference, all_evidences, debug_verbose, context=context, queue=queue, api_queue=api_queue, request_id=request_id)
                        code_results_dict_list.extend(all_code_results)
                        argument_values_list = [[all_code] for all_code in all_codes]
                        call_ids = [generate_call_id() for _ in range(len(now_step_keywords))]

                        # 整合生成代码和代码的执行结果
                        now_message = function_call_sent(argument_values_list, call_ids, "codeRunner", argument_names = ['code'])
                        now_messages.append(now_message)
                        code_evidence, now_message = function_call_receive_code_results(all_steps[step_idx]['now_step_keywords'], all_codes, call_ids, all_code_results)
                        now_messages.extend(now_message)
                        code_evidences.extend(code_evidence)
                        
                        # 根据当前的状态信息（当前代码执行结果、当前步骤、整体步骤）重新规划路径
                        if step_idx != len(all_steps) - 1:
                            all_code_results_list = []
                            for all_code_result in all_code_results:
                                all_code_results_list.append(str(all_code_result))
                            response = dict()
                            queue.put(["bar", "🔬 智能体 · 依据当前状态重新规划路径"])
                            context["online_steps"].append("🔬 智能体 · 依据当前状态重新规划路径")
                            queue.put(["placeholder_begin", None])
                            context["online_steps"].append("")
                            _reasoning_content = ""
                            for label, _stream_text in reorchestrator.run(context['question'], all_code_results_list, all_steps[step_idx]['step_desc'], latest_search_process):
                                if label == "think":
                                    _reasoning_content += _stream_text
                                    queue.put(["placeholder_think_stream_markdown", convert_think_message_to_markdown(_reasoning_content)])
                                    context["online_steps"][-1] = convert_think_message_to_markdown(_reasoning_content)
                                    api_queue.put(format_data(reasoning_content=_stream_text, id=request_id, stage="reorchestrate"))
                                elif label == "answer":
                                    response = _stream_text
                            now_messages.append({"reasoning_content": _reasoning_content, "content": "response", "role": "assistant", "stage": "reorchestrate"})
                            latest_search_process = response['update_whole_step']
                            all_steps = step_by_step_process(latest_search_process)
                            queue.put(["bar", f"🔨更新为流程：{latest_search_process}"])
                            context["online_steps"].append(f"🔨更新为流程：{latest_search_process}")
                            api_queue.put(format_data(content=latest_search_process, id=request_id, stage="reorchestrate"))
                        else:
                            context['search_process'] = latest_search_process
                            break
                        

            elif now_stage == 'assistant':
                if len(all_evidences) == 0 or empty_search == True:
                    if LANGUAGE == "en":
                        all_evidences.append("There is no evidence, please reject to answer.")
                    else:
                        all_evidences.append("当前无证据句子，请拒绝回答。")
                _reasoning_content = ""
                llm_answer = ""
                queue.put(["bar", "🖥️ 智能体 · 综合获取的信息"])
                context["online_steps"].append("🖥️ 智能体 · 综合获取的信息")
                queue.put(["placeholder_begin", None])
                context["online_steps"].append("")
                for label, _stream_text in assitant.run(context['question'], context['search_process'], all_evidences, code_evidences):
                    if label == "think":
                        _reasoning_content += _stream_text
                        queue.put(["placeholder_think_stream_markdown", convert_think_message_to_markdown(_reasoning_content)])
                        context["online_steps"][-1] = convert_think_message_to_markdown(_reasoning_content)
                        api_queue.put(format_data(reasoning_content=_stream_text, id=request_id, stage="answer with function call"))
                    elif label == "answer":
                        llm_answer += _stream_text
                        api_queue.put(format_data(content=_stream_text, id=request_id, stage="answer with function call"))
                    else:
                        llm_answer = _stream_text
                now_messages.append({"reasoning_content": _reasoning_content, "content": llm_answer, "role": "assistant", "stage": "answer with function call"})
                llm_no_ref_answer = remove_ref_tag(llm_answer)
                context['llm_answer'] = llm_answer
                if debug_verbose:
                    ref2md_answer = replace_ref_tag2md(llm_answer, context["online_url_lists"])
                    ref2md_answer = latex_render(ref2md_answer)
                    context["online_code_results"] = code_results_dict_list
                    context["online_answer"] = ref2md_answer
                now_messages.append(process_message(content = llm_no_ref_answer, role = "assistant", content_ref = llm_answer))

        meta_data = {
            "time_stamp":f"{get_real_time_str()}",
            "question": context['question'],
            "feedback": None,
            "messages" : now_messages,
            "tool_choice": "auto",
            "parallel_tool_calls": True,
            "tools": get_tool_list(use_tool_record)
        }
        # 将有效信息收集起来
        if empty_search == False or empty_code == False:
            context["new_record"] = meta_data
            if meta_verbose:
                print("### json 最后存储格式如下：")
                print(json.dumps(meta_data, indent=4, ensure_ascii=False))

            if len(save_jsonl_path) > 0:
                with open(save_jsonl_path, 'a', encoding='utf-8') as f:
                    json_line = json.dumps(meta_data, ensure_ascii=False)
                    f.write(json_line + '\n')
    queue.put(["finish", None])
    api_queue.put("finish")
    return
    