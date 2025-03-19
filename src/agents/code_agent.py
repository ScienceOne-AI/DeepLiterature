# encoding: utf-8
import time
import json

from llms.base_llm import BaseLLM
from utils.logger import model_logger
from .base_agent import BaseAgent
from .prompts.code_agent_prompts import SYSTEM_PROMPT3_3, SYSTEM_PROMPT3_3_EN
from config import MAX_CONTEXT_LENGTH

class CodeAgent(BaseAgent):
    def __init__(self, llm: BaseLLM, lang:str):
        self.llm = llm
        self.lang = lang

    def run(self, query, now_code_step, previous_reference, reference_list, temperature=0.7, max_tokens=2048):
        start_time = time.time()
        max_input_length = MAX_CONTEXT_LENGTH - max_tokens
        cur_references = [previous_reference]
        reference_doc = "\n".join(cur_references)
        user_prompt_tpl = ""
        system_prompt = ""
        if self.lang == "zh":
            user_prompt_tpl = "【用户问题】\n{query}\n【当前步骤】\n{now_code_step}\n【参考信息】{reference_doc}\n【执行代码】\n"
            system_prompt = SYSTEM_PROMPT3_3
        elif self.lang == "en":
            user_prompt_tpl = "【Question】\n{query}\n【Current Step】\n{now_code_step}\n【Reference Information】{reference_doc}\n【Execution Code】\n"
            system_prompt = SYSTEM_PROMPT3_3_EN
        user_prompt = user_prompt_tpl.format(query=query, now_code_step=now_code_step, reference_doc=reference_doc)
        for ref in reference_list:
            cur_references.append(ref)
            tmp_ref_doc = "\n".join(cur_references)
            tmp_user_prompt = user_prompt_tpl.format(query=query, now_code_step=now_code_step, reference_doc=tmp_ref_doc)
            if len(self.llm.tokenizer.tokenize(tmp_user_prompt)) > max_input_length:
                break
            reference_doc = tmp_ref_doc
            user_prompt = tmp_user_prompt
        response = ""
        reasoning_content = ""
        for label, cont in self.llm.stream_chat(system_content=system_prompt, user_content=user_prompt, temperature=temperature, max_tokens=max_tokens):
            if label == "think":
                reasoning_content += cont
            else:
                response += cont
            yield label, cont
        cleaned_text = response.strip()
        lines = cleaned_text.splitlines()
        start_line = 0
        end_line = len(lines) - 1
        for line_idx, line in enumerate(lines):
            if line.startswith("```python"):
                start_line = line_idx
                break
            if line.startswith("```"):
                start_line = line_idx
                break

        while end_line > 0:
            if lines[end_line].startswith("```"):
                break    
            end_line -= 1

        in_out = {"state": "creat_code", "input": {"question": query, "now_code_step": now_code_step, "reference_doc": reference_doc,"temperature": temperature, "max_tokens":max_tokens}, \
                "output": lines, "response": {"content":response, "reasoning_content": reasoning_content}, "user_prompt": user_prompt, "cost_time": str(round(time.time()-start_time, 3))}
        model_logger.info(json.dumps(in_out, ensure_ascii=False))

        if start_line < end_line:
            yield "final_answer", "\n".join(lines[start_line + 1:end_line])
        else:
            yield "final_answer", "\n".join(lines)
        
