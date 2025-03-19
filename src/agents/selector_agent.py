# encoding: utf-8
import time
import json
import re

from llms.base_llm import BaseLLM
from utils.logger import model_logger
from .base_agent import BaseAgent
from .prompts.selector_agent_prompts import SYSTEM_PROMPT5, SYSTEM_PROMPT5_EN

class SelectorAgent(BaseAgent):
    def __init__(self, llm: BaseLLM, lang: str):
        self.llm = llm
        self.lang = lang

    def run(self, query, snippet_list, temperature=0.3, max_tokens=2048):
        start_time = time.time()
        snippet_str = "\n".join(snippet_list)
        system_prompt = ""
        user_prompt = ""
        if self.lang == "zh":
            user_prompt = f"【问题】\n以下信息和当前检索 {query} 相关的是哪几个快照？\n【快照】\n{snippet_str}\n【索引列表】\n"
            system_prompt = SYSTEM_PROMPT5
        elif self.lang == "en":
            user_prompt = f"【Question】\nWhich snippets are relevant to the current search {query} ?\n【Snippet】\n{snippet_str}\n【Index list】\n"
            system_prompt = SYSTEM_PROMPT5_EN

        response = ""
        reasoning_content = ""
        for label, cont in self.llm.stream_chat(system_content=system_prompt, user_content=user_prompt, temperature=temperature, max_tokens=max_tokens, answer_sleep=0):
            if label == "think":
                reasoning_content = cont
                yield label, reasoning_content
            else:
                response += cont
        try:
            response = re.sub(r"[^\[\]\d,]", "", response)
            related_snippet_idx_list = eval(response)
        except Exception as e:
            related_snippet_idx_list = [i for i in range(len(snippet_list))]
        in_out = {"state": "choose_snippet", "input": {"question": query, "snippet_str": snippet_str, "temperature": temperature, "max_tokens":max_tokens}, \
                "output": snippet_list, "response": {"content":response, "reasoning_content": reasoning_content}, "user_prompt": user_prompt, "cost_time": str(round(time.time()-start_time, 3))}
        model_logger.info(json.dumps(in_out, ensure_ascii=False))
        yield "answer", related_snippet_idx_list