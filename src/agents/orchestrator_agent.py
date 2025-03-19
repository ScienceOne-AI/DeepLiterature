# encoding: utf-8
import time
import re
import json

from llms.base_llm import BaseLLM
from utils.logger import model_logger
from .base_agent import BaseAgent
from .prompts.orchestrator_agent_prompts import SYSTEM_PROMPT_ZH, SYSTEM_PROMPT_EN

class OrchestratorAgent(BaseAgent):
    def __init__(self, llm: BaseLLM, lang: str):
        self.llm = llm
        self.lang = lang

    @staticmethod
    def parse_keywords(text):
        pattern = r'webSearch\("([^"]+)"\)' 
        matches1 = re.findall(pattern, text)
        pattern2 = r'codeRunner\("([^"]+)"\)' 
        matches2 = re.findall(pattern2, text)
        matches = []
        if matches2:
            matches.extend(matches2)
        if matches1:
            matches.extend(matches1)
        return matches
    
    def postprocess(self, response_text):
        res = dict()
        if self.lang == "zh":
            res = self.postprocess_zh(response_text)
        elif self.lang == "en":
            res = self.postprocess_en(response_text)
        return res
    
    def postprocess_zh(self, response_text):
        keyword_list = OrchestratorAgent.parse_keywords(response_text)
        if_search = response_text.split("【搜索类型】")[0].split("【是否搜索】")[-1].strip()
        search_type= response_text.split("【是否执行代码】")[0].split("【搜索类型】")[-1].strip()
        if_code = response_text.split("【执行过程】")[0].split("【是否执行代码】")[-1].strip()
        search_process = response_text.split("【执行过程】")[-1].strip()
        if len(keyword_list) > 1 and search_type == "单步单次":
            search_type = "单步并发"
        if if_code not in ['是', '否']:
            if_code = '否'
        if if_search not in ['是', '否']:
            if_search = '否'
        res = {
            "keyword_list": keyword_list, # 对于问题拆分的关键词list
            "if_search": if_search, # 是否需要检索的判定
            "if_code": if_code, # 是否需要执行代码
            "search_type": search_type, # 检索的类型：单步单次，单步并发，多步多次
            "search_process": search_process # 预设的检索过程
        }
        return res

    def postprocess_en(self, response_text):
        keyword_list = OrchestratorAgent.parse_keywords(response_text)
        if_search = response_text.split("【Search Type】")[0].split("【Search Required】")[-1].strip().lower()
        search_type= response_text.split("【Code Execution Required】")[0].split("【Search Type】")[-1].strip()
        if_code = response_text.split("【Execution Process】")[0].split("【Code Execution Required】")[-1].strip().lower()
        search_process = response_text.split("【Execution Process】")[-1].strip()
        if len(keyword_list) > 1 and search_type == "Single-step Single-search":
            search_type = "Single-step Concurrent"
        if str(if_code) not in ['yes', 'no']:
            if_code = 'no'
        if str(if_search) not in ['yes', 'no']:
            if_search = 'no'
        res = {
            "keyword_list": keyword_list, # 对于问题拆分的关键词list
            "if_search": if_search, # 是否需要检索的判定
            "if_code": if_code, # 是否需要执行代码
            "search_type": search_type, # 检索的类型：单步单次，单步并发，多步多次
            "search_process": search_process # 预设的检索过程
        }
        return res

    def run(self, query, temperature=0.3, max_tokens=2048):
        start_time = time.time()
        user_prompt = ""
        systen_prompt = ""
        if self.lang == "zh":
            user_prompt = f"【问题】\n{query}"
            systen_prompt = SYSTEM_PROMPT_ZH
        elif self.lang == "en":
            user_prompt = f"【Question】\n{query}"
            systen_prompt = SYSTEM_PROMPT_EN
        now_keyword = ""
        reasoning_content = ""
        for label, cont in self.llm.stream_chat(systen_prompt, user_prompt, temperature, max_tokens, answer_sleep=0):
            if label == "think":
                reasoning_content = cont
                yield label, reasoning_content
            else:
                now_keyword += cont
        res = self.postprocess(now_keyword)
        in_out = {"state": "query_classify", "input": {"question": query, "temperature": temperature, "max_tokens": max_tokens}, \
                "output": res, "response": {"content": now_keyword, "reasoning_content": reasoning_content}, "user_prompt": user_prompt, "cost_time": str(round(time.time()-start_time, 3))}
        model_logger.info(json.dumps(in_out, ensure_ascii=False))
        yield "answer", res