# encoding: utf-8
import requests
import traceback
import json
import time


from config.config import REMOTE_REASONING_LLM_API_URL, REMOTE_REASONING_LLM_API_KEY, REMOTE_REASONING_LLM_MODEL_NAME, LANGUAGE
from utils.common_utils import get_real_time_str, get_location_by_ip
from .base_llm import BaseLLM

class RemoteReasoningLLM(BaseLLM):
    def __init__(self, tokenizer=None, api_url=REMOTE_REASONING_LLM_API_URL, api_key=REMOTE_REASONING_LLM_API_KEY):
        self.api_url = api_url
        self.api_key = api_key
        self.tokenizer = tokenizer

    def stream_chat(self, system_content="", user_content="", temperature=0.7, max_tokens=2048, think_sleep=0.02, answer_sleep=0.02):
        if len(system_content) == 0:
            if LANGUAGE == "zh":
                system_content = f"你的身份是一个友善且乐于助人的智能体(agent)。你需要把自己作为智能体和用户进行友善问答。当前的时间为{get_real_time_str()}。当前所在地: {get_location_by_ip()}。"
            elif LANGUAGE == "en":
                system_content = f"Your identity is a friendly and helpful agent. You need to engage in friendly Q&A with users as a agent. The current time is{get_real_time_str()}. Current location: {get_location_by_ip()}."


        request_header = {
            'Content-Type':'application/json',
            "Authorization": f"Bearer {self.api_key}"
        }

        request_json={
            "model":REMOTE_REASONING_LLM_MODEL_NAME,
            "messages":[
                {"role":"system", "content":system_content},
                {"role":"user", "content":user_content},
            ],
            "temperature" : temperature,
            "max_tokens" : max_tokens,
            "stream": True
        }

        try:
            response = requests.post(self.api_url, headers=request_header, json=request_json)
        except Exception as e:
            traceback.print_exc()
            raise e
        if response.status_code == 200:
            for line in response.iter_lines():
                line = line.decode('utf-8').strip()
                if len(line) == 0:
                    continue
                line = line.lstrip("data:").strip()
                if line == "[DONE]":
                    break
                data = json.loads(line)
                if "reasoning_content" in data["choices"][0]["delta"]:
                    text = data["choices"][0]["delta"]["reasoning_content"]
                    if len(text) == 0:
                        continue
                    yield "think", text
                    if think_sleep > 0:
                        time.sleep(think_sleep)
                else:
                    text = data["choices"][0]["delta"]["content"]
                    if len(text) == 0:
                        continue
                    yield "answer", text
                    if answer_sleep > 0:
                        time.sleep(answer_sleep)
        else:
            raise Exception(f"Error: {response.status_code} - {response.text}")


    def chat(self, system_content="", user_content="", temperature=0.7, max_tokens=2048):
        if len(system_content) == 0:
            if LANGUAGE == "zh":
                system_content = f"你的身份是一个友善且乐于助人的智能体(agent)。你需要把自己作为智能体和用户进行友善问答。当前的时间为{get_real_time_str()}。当前所在地: {get_location_by_ip()}。"
            elif LANGUAGE == "en":
                system_content = f"Your identity is a friendly and helpful agent. You need to engage in friendly Q&A with users as a agent. The current time is{get_real_time_str()}. Current location: {get_location_by_ip()}."


        request_header = {
            'Content-Type':'application/json',
            "Authorization": f"Bearer {self.api_key}"
        }

        request_json={
            "model":"ep-20250225190058-sqzbc",
            "messages":[
                {"role":"system", "content":system_content},
                {"role":"user", "content":user_content},
            ],
            "temperature" : temperature,
            "max_tokens" : max_tokens
        }


        try:
            response = requests.post(self.api_url, headers=request_header, json=request_json)
        except:
            return "Error: 404 - None"
        if response.status_code == 200:
            response_content = ""
            for line in response.iter_lines():
                response_content += line.decode('utf-8') + "\n"
            return json.loads(response_content)["choices"][0]["message"]["content"]
        else:
            return f"Error: {response.status_code} - {response.text}"
    