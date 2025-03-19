# encoding: utf-8
import time
import json


from llms.base_llm import BaseLLM
from utils.logger import model_logger
from .base_agent import BaseAgent
from .prompts.assitant_agent_prompts import SYSTEM_PROMPT6, SYSTEM_PROMPT6_EN
from config import MAX_CONTEXT_LENGTH

class AssitantAgent(BaseAgent):
    def __init__(self, llm: BaseLLM, lang: str):
        self.llm = llm
        self.lang = lang

    def run(self, query, search_process, evidence_list, code_evidence_list, temperature=1, max_tokens=4096):
        start_time = time.time()
        code_evidence = ""
        user_prompt = ""
        system_prompt = ""
        if self.lang == "zh":
            if len(code_evidence_list) > 0:
                code_evidence = '\n'.join(code_evidence_list)
            else:
                code_evidence = "无需代码"
            user_prompt = f"【问题】{query}\n【搜索过程】{search_process}【代码结果】\n{code_evidence}\n【相关内容】\n"
            system_prompt = SYSTEM_PROMPT6
        elif self.lang == "en":
            if len(code_evidence_list) > 0:
                code_evidence = '\n'.join(code_evidence_list)
            else:
                code_evidence = "No code is needed."
            user_prompt = f"【Question】{query}\n【Search Process】{search_process}【Code Results】\n{code_evidence}\n【Relevant Content】\n"
            system_prompt = SYSTEM_PROMPT6_EN

        max_input_length = MAX_CONTEXT_LENGTH - max_tokens
        for idx in range(len(evidence_list)):
            evidence = evidence_list[idx] + "\n"
            if len(self.llm.tokenizer.tokenize(user_prompt + evidence)) > max_input_length:
                break
            user_prompt += evidence

        
        has_cutted = False
        response =  ""
        reasoning_content = ""
        llm_answer = ""
        for label, cont in self.llm.stream_chat(system_prompt, user_prompt, temperature, max_tokens, answer_sleep=0):
            if label == "think":
                yield label, cont
            else:
                response += cont
                llm_answer += cont
                if not has_cutted:
                    if self.lang == "zh":
                        if "【答案】" in llm_answer:
                            llm_answer = llm_answer.split("【答案】")[-1].strip()
                            has_cutted = True
                    elif self.lang == "en":
                        if "【Answer】" in llm_answer:
                            llm_answer = llm_answer.split("【Answer】")[-1].strip()
                            has_cutted = True
                yield label, cont

        in_out = {"state": "create_answer", "input": {"question": query, "search_process": search_process, "evidence_list": evidence_list, "code_evidence_list":code_evidence_list,"temperature": temperature, "max_tokens":max_tokens}, \
                "output": llm_answer, "response": {"content":response, "reasoning_content": reasoning_content}, "user_prompt": user_prompt, "cost_time": str(round(time.time()-start_time, 3))}
        model_logger.info(json.dumps(in_out, ensure_ascii=False))
