# encoding: utf-8
from fastapi import FastAPI, Request
import uvicorn, json
from fastapi.responses import StreamingResponse

from queue import Queue
import threading
import sys,os

ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_PATH)
from utils.message_queue import WrapperQueue
from workflow import deepresearch_workflow
from config import LANGUAGE

def generator(wrapper_queue):
    while True:
        message = wrapper_queue.get()
        if message == "finish":
            yield "data: [DONE]\n\n"
            return
        if message == "exception":
            yield "data: [ERROR]\n\n"
            return
        if type(message) == type(dict()):
            message = json.dumps(message, ensure_ascii=False)
        yield f"data: {message}\n\n"


app = FastAPI()

@app.post("/stream")
async def create_item(request: Request):
    json_post_raw = await request.json()
    query = json_post_raw.get("query")

    context = dict()
    context['question'] = query
    context["online_url_lists"] = []
    context["online_steps"] = []
    context["online_answer"] = ""
    context["online_code_results"] = []
    context["online_answer_stars"] = None
    

    queue = Queue()
    api_queue = WrapperQueue(queue)
    thread = threading.Thread(target=deepresearch_workflow.run, args=(query, WrapperQueue(), api_queue, LANGUAGE), kwargs={"context": context})
    thread.start()
    return StreamingResponse(generator(api_queue), media_type="text/event-stream")

@app.post("/v1/chat/completions")
async def create_item(request: Request):
    json_post_raw = await request.json()
    model = json_post_raw.get("model", "deepresearch")
    messages = json_post_raw.get("messages", [])
    temperature = json_post_raw.get("temperature", 0.7)
    max_tokens = json_post_raw.get("max_tokens", 2048)
    stream = json_post_raw.get("stream", False)

    user_content = ""
    for msg in messages:
        if msg["role"] == "system":
            system_content = msg["content"]
        elif msg["role"] == "user":
            user_content = msg["content"]


    context = dict()
    context['question'] = user_content
    context["online_url_lists"] = []
    context["online_steps"] = []
    context["online_answer"] = ""
    context["online_code_results"] = []
    context["online_answer_stars"] = None
    

    queue = Queue()
    api_queue = WrapperQueue(queue)
    thread = threading.Thread(target=deepresearch_workflow.run, args=(user_content, WrapperQueue(), api_queue, LANGUAGE), kwargs={"context": context})
    thread.start()
    return StreamingResponse(generator(api_queue), media_type="text/event-stream")



if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=36668, workers=1, timeout_keep_alive=60)
