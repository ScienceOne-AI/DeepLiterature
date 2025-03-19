# encoding: utf-8
import time
import json

from llms.base_llm import BaseLLM
from utils.logger import model_logger
from .base_agent import BaseAgent
from .prompts.reorchestrator_agent_prompts import SYSTEM_PROMPT3, SYSTEM_PROMPT3_EN, SYSTEM_PROMPT3_6, SYSTEM_PROMPT3_6_EN
from config import MAX_CONTEXT_LENGTH

class ReorchestratorAgent(BaseAgent):
    def __init__(self, llm: BaseLLM, lang: str):
        self.llm = llm
        self.lang = lang
    
    def truncate_prompt(self, query, evidence_list, now_step, whole_step, user_prompt_tpl, max_input_length):
        is_truncated = False
        evidence = ""
        user_prompt = user_prompt_tpl.format(query=query, evidence=evidence, now_step=now_step, whole_step=whole_step)
        for idx in range(len(evidence_list)):
            tmp_evidence = "\n".join(evidence_list[:idx+1])
            tmp_user_prompt = user_prompt_tpl.format(query=query, evidence=tmp_evidence, now_step=now_step, whole_step=whole_step)
            if len(self.llm.tokenizer.tokenize(tmp_user_prompt)) > max_input_length:
                is_truncated = True
                break
            user_prompt = tmp_user_prompt
            evidence = tmp_evidence
        
        return is_truncated, evidence, user_prompt


    def postprocess(self, response_text):
        res = dict()
        if self.lang == "zh":
            res = self.postprocess_zh(response_text)
        elif self.lang == "en":
            res = self.postprocess_en(response_text)
        return res
    
    def postprocess_zh(self, response):
        update_now_step = response.split("【修改全流程】")[0].split("【修改当前步骤】")[-1].strip()
        update_whole_step = response.split("【修改全流程】")[-1].strip()
        if len(update_whole_step.split("【")) > 1: # 处理重复
            update_whole_step = update_whole_step.split("【")[0]

        res = {
            "update_now_step": update_now_step,
            "update_whole_step": update_whole_step,
        }
        return res

    def postprocess_en(self, response):
        update_now_step = response.split("【Modify Entire Process】")[0].split("【Modify Current Step】")[-1].strip()
        update_whole_step = response.split("【Modify Entire Process】")[-1].strip()
        if len(update_whole_step.split("【")) > 1: # 处理重复
            update_whole_step = update_whole_step.split("【")[0]

        res = {
            "update_now_step": update_now_step,
            "update_whole_step": update_whole_step,
        }
        return res

    def run(self, query, evidence_list, now_step, whole_step, temperature=0.7, max_tokens=2048, step_type="webSearch"):
        start_time = time.time()
        max_input_length = MAX_CONTEXT_LENGTH - max_tokens
        system_prompt = ""
        user_prompt_tpl = ""
        if self.lang == "zh":
            if step_type == "webSearch":
                system_prompt = SYSTEM_PROMPT3
                user_prompt_tpl = """【用户问题】\n{query}\n【查询结果】\n{evidence}\n【当前步骤】\n{now_step}\n【全流程】\n{whole_step}\n"""
            else:
                system_prompt = SYSTEM_PROMPT3_6
                user_prompt_tpl = """【用户问题】\n{query}\n【执行结果】\n {evidence}\n【当前步骤】\n{now_step}\n【全流程】\n {whole_step}\n"""
        elif self.lang == "en":
            if step_type == "webSearch":
                system_prompt = SYSTEM_PROMPT3_EN
                user_prompt_tpl = """【User Question】\n{query}\n【Search Results】\n{evidence}\n【Current Step】\n{now_step}\n【Entire Process】\n{whole_step}\n"""
            else:
                system_prompt = SYSTEM_PROMPT3_6_EN
                user_prompt_tpl = """【User Question】\n{query}\n【Execution Result】\n {evidence}\n【Current Step】\n{now_step}\n【Entire Process】\n {whole_step}\n"""
        is_truncated, evidence, user_prompt = self.truncate_prompt(query, evidence_list, now_step, whole_step, user_prompt_tpl, max_input_length)
        response = ""
        reasoning_content = ""
        for label, cont in self.llm.stream_chat(system_content=system_prompt, user_content=user_prompt, temperature=temperature, max_tokens=max_tokens, answer_sleep=0):
            if label == "think":
                reasoning_content = cont
                yield label, reasoning_content
            else:
                response += cont
        res = self.postprocess(response)
        in_out = {"state": "update_search_process", "input": {"question": query, "evidence": evidence, "now_step": now_step, "whole_step": whole_step, "temperature": temperature, "max_tokens": max_tokens}, \
                "output": res, "response": {"content": response, "reasoning_content": reasoning_content}, "user_prompt": user_prompt, "cost_time": str(round(time.time()-start_time, 3))}
        model_logger.info(json.dumps(in_out, ensure_ascii=False))
        yield "answer", res