# encoding: utf-8
import time
import json

from llms.base_llm import BaseLLM
from utils.logger import model_logger
from .base_agent import BaseAgent
from .prompts.optimizer_agent_prompts import SYSTEM_PROMPT4_EN, SYSTEM_PROMPT4_ZH

class OptimizerAgent(BaseAgent):
    def __init__(self, llm: BaseLLM, lang: str):
        self.llm = llm
        self.lang = lang

    def run(self, query, temperature=0.3, max_tokens=2048):
        start_time = time.time()
        user_prompt = ""
        if self.lang == "en":
            system_prompt = SYSTEM_PROMPT4_EN
            user_prompt = f"""【Full Process】\n{query}\n"""
        elif self.lang == "zh":
            system_prompt = SYSTEM_PROMPT4_ZH
            user_prompt = f"""【全流程】\n{query}\n"""
            
        response = ""
        reasoning_content = ""
        for label, cont in self.llm.stream_chat(system_content=system_prompt, user_content=user_prompt, temperature=temperature, max_tokens=max_tokens, answer_sleep=0):
            if label == "think":
                reasoning_content = cont
                yield label, reasoning_content
            else:
                response += cont

        optimize_process = response.split("】")[-1].strip()
        in_out = {"state": "optimize_search_process", "input": {"process":query, "lang":self.lang, "temperature":temperature, "max_tokens":max_tokens}, \
                "output": optimize_process, "response": {"content": response,"reasoning_content":reasoning_content}, "user_prompt": user_prompt, "cost_time": str(round(time.time()-start_time, 3))}
        model_logger.info(json.dumps(in_out, ensure_ascii=False))
        yield "answer", optimize_process