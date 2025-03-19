# encoding: utf-8
import time
import json
import re

from llms.base_llm import BaseLLM
from utils.logger import model_logger
from .base_agent import BaseAgent
from .prompts.sufficiency_validator_agent_prompts import SYSTEM_PROMPT2, SYSTEM_PROMPT2_EN

class SufficiencyValidatorAgent(BaseAgent):
    def __init__(self, llm: BaseLLM, lang: str):
        self.llm = llm
        self.lang = lang

    def postprocess(self, response_text):
        res = dict()
        if self.lang == "zh":
            res = self.postprocess_zh(response_text)
        elif self.lang == "en":
            res = self.postprocess_en(response_text)
        return res
    
    def postprocess_zh(self, response):
        analysis_sentence = response.split("【过渡短语】")[0].split("【问题分析】")[-1].strip()
        trans_sentence = response.split("【快照分析】")[0].split("【过渡短语】")[-1].strip()
        snippet_sentence = response.split("【快照分析】")[-1].strip()
        if len(snippet_sentence.split("【")) > 1: # 处理重复
            snippet_sentence = snippet_sentence.split("【")[0]

        res = {
            "analysis_sentence": analysis_sentence,
            "trans_sentence": trans_sentence,
            "snippet_sentence": [sentence for sentence in snippet_sentence.split("\n") if len(sentence)>0 and sentence[0] in ['×', '√']]
        }
        return res

    def postprocess_en(self, response):
        analysis_sentence = response.split("【Transition Phrase】")[0].split("【Question Analysis】")[-1].strip()
        trans_sentence = response.split("【Snippet Analysis】")[0].split("【Transition Phrase】")[-1].strip()
        snippet_sentence = response.split("【Snippet Analysis】")[-1].strip()
        if len(snippet_sentence.split("【")) > 1: # 处理重复
            snippet_sentence = snippet_sentence.split("【")[0]

        res = {
            "analysis_sentence": analysis_sentence,
            "trans_sentence": trans_sentence,
            "snippet_sentence": [sentence for sentence in snippet_sentence.split("\n") if len(sentence)>0 and sentence[0] in ['×', '√']]
        }
        return res

    def run(self, query, snippet_list, temperature=0.3, max_tokens=2048):
        start_time = time.time()
        user_prompt = ""
        systemt_prompt = ""
        if self.lang == "zh":
            user_prompt = f"""【问题】\n以下信息能够满足当前这步 {query} 检索所需的所有信息吗?\n【快照】{snippet_list}\n"""
            systemt_prompt = SYSTEM_PROMPT2
        elif self.lang == "en":
            user_prompt = f"""【Question】\nCan the following information fulfill all the requirements needed for the current retrieval of {query} ?\n【Snippet】{snippet_list}\n"""
            systemt_prompt = SYSTEM_PROMPT2_EN

        response = ""
        reasoning_content = ""
        for label, cont in self.llm.stream_chat(system_content=systemt_prompt, user_content=user_prompt, temperature=temperature, max_tokens=max_tokens, answer_sleep=0):
            if label == "think":
                reasoning_content = cont
                yield label, reasoning_content
            else:
                response += cont
        res = self.postprocess(response)
        in_out = {"state": "parse_classify", "input": {"question": query, "snippet_list": snippet_list, "temperature": temperature, "max_tokens": max_tokens}, \
                "output": res, "response": {"content":response, "reasoning_content": reasoning_content}, "user_prompt": user_prompt, "cost_time": str(round(time.time()-start_time, 3))}
        model_logger.info(json.dumps(in_out, ensure_ascii=False))
        yield "answer", res