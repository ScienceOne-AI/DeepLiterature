# encoding: utf-8
import base64
import io
import json
import streamlit as st
st.set_page_config(page_title="DeepLiterature", page_icon="logo/icon-title.png")
import time
from utils.logger import model_logger

from utils.common_utils import *

from queue import Queue
import threading

from workflow import deepresearch_workflow
from utils.message_queue import WrapperQueue
from config import LANGUAGE

 
def page_chat():
    start_time = time.time()
    @st.cache_data
    def download_as_json(dict_record):
        return json.dumps(dict_record, indent=4, ensure_ascii=False)
    
    def show_jsonl_record():
        st.markdown("当前数据的整体格式如下: ")
        with st.container(height=600, border= False):
            with st.empty():
                st.write("⏳ 载入数据中...")
                st.write(st.session_state.new_record)
        st.download_button(":grey[下载]", key="download_json", icon="🧾", data= download_as_json(st.session_state.new_record), file_name="chat_record.json", use_container_width = True)


    if "online_answer" not in st.session_state:
        st.session_state.online_answer = ""

    if "online_code_results" not in st.session_state:
        st.session_state.online_code_results = []

    if "online_answer_stars" not in st.session_state:
        st.session_state.online_answer_stars = None

    if "new_record" not in st.session_state:
        st.session_state.new_record = None

    if "show_jsonl" not in st.session_state:
        st.session_state.show_jsonl = False
    st.image("logo/icon.png")
    st.divider()
    
    for msg in st.session_state.messages:
        with st.chat_message(name = msg["role"], avatar=msg["avatar"]):
            # 将中间过程还原
            if "step_record" in msg:
                with st.status("思考过程结束", state="complete", expanded=False):
                    for now_record in msg['step_record']:
                        if isinstance(now_record, str):
                            st.markdown(now_record, unsafe_allow_html=True) 
                        elif isinstance(now_record, list):
                            # 处理检索到的网页
                            with st.container(height=200):   
                                st.markdown("\n".join(now_record))
                        elif isinstance(now_record, dict):
                            if "text" in now_record:
                                st.code(now_record['text'])
                            if "img" in now_record:
                                st.image(io.BytesIO(base64.b64decode(now_record['img'])))   
            if "code_record" in msg:
                for code_results in msg['code_record']:
                    for code_result in code_results:
                        if "text" in code_result:
                            st.code(code_result['text'])
                        if "img" in code_result:
                            st.image(io.BytesIO(base64.b64decode(code_result['img'])))
            st.write(msg["content"])

    if prompt := st.chat_input("输入文本"):
        with st.chat_message(name = "user", avatar= "logo/user.svg"):
            st.write(prompt)
        # 大模型进行回复
        with st.chat_message(name = "assistant", avatar= "logo/icon-mini.gif"):
            # 每次运行前需要清空
            st.session_state.online_url_lists = []
            st.session_state.online_steps = []
            st.session_state.online_answer = ""
            st.session_state.online_code_results = []
            st.session_state.online_answer_stars = None


            context = dict()
            context["question"] = prompt
            context["online_url_lists"] = []
            context["online_steps"] = []
            context["online_answer"] = ""
            context["online_code_results"] = []
            context["online_answer_stars"] = None
            

            queue = Queue()
            wrapper_queue = WrapperQueue(queue)
            thread = threading.Thread(target=deepresearch_workflow.run, args=(prompt, wrapper_queue, WrapperQueue(), LANGUAGE), kwargs={"context": context})
            thread.start()
            with st.status("智能体思考中...", expanded=True, state="running") as status:
                placeholder = None
                container = None
                while True:
                    event, message = wrapper_queue.get()
                    if event == "bar":
                        st.write_stream(yield_text(message))
                    elif event == "placeholder_begin":
                        placeholder = st.empty()
                    elif event == "placeholder_think_stream_markdown":
                        placeholder.markdown(message, unsafe_allow_html=True)
                    elif event == "placeholder_caption":
                        placeholder.caption(message)
                    elif event == "placeholder_bar":
                        placeholder.write_stream(yield_text(message))
                    elif event == "placeholder_answer_plain_text":
                        placeholder.text(message)
                    elif event == "placeholder_answer_markdown":
                        placeholder.markdown(message)
                    elif event == "error":
                        st.error(message, icon= "🔥")
                    elif event == "divider":
                        st.divider()
                    elif event == "container_begin":
                        container = st.container(**message)
                    elif event == "container_bar":
                        container.write_stream(yield_text(message))
                    elif event == "container_content":
                        container.markdown(message, unsafe_allow_html=True)
                    elif event == "code_result_text":
                        st.markdown(message)
                    elif event == "code_result_image":
                        st.image(io.BytesIO(base64.b64decode(message)))
                    elif event == "finish":
                        break
                    elif event == "exception":
                        break
                status.update(
                    label="思考过程结束", state="complete", expanded=False
                )
            thread.join()

            # 将大模型执行过程中的信息写入session
            st.session_state.online_url_lists = context["online_url_lists"]
            st.session_state.online_steps = context["online_steps"]
            st.session_state.online_answer = context["online_answer"]
            st.session_state.online_code_results = context["online_code_results"]
            st.session_state.online_answer_stars = context["online_answer_stars"]
            st.session_state.new_record = context.get("new_record")
            st.session_state.online_answer = re.sub(r'◥\[.*?\]◤', '', st.session_state.online_answer)
            st.session_state.messages.append({"role": "user", "content": prompt, "avatar": "logo/user.svg"})
            st.session_state.messages.append({"role": "assistant", "content": st.session_state.online_answer, "avatar": "icon-mini.gif", "step_record": st.session_state.online_steps, "code_record": st.session_state.online_code_results})
            if len(st.session_state.online_answer) > 0:
                if len(st.session_state.online_code_results) > 0:
                    for code_results in st.session_state.online_code_results:
                        for code_result in code_results:
                            if "text" in code_result:
                                st.code(code_result['text'])
                            if "img" in code_result:
                                st.image(io.BytesIO(base64.b64decode(code_result['img'])))
                st.write_stream(yield_text(st.session_state.online_answer))
            else:
                st.error("当前发生了一些错误，请稍后重试...", icon= "😵")

      
    if len(st.session_state.online_answer) > 0 and st.session_state.online_answer_stars is None:
        col1, col2, col3 = st.columns([4,5,1], vertical_alignment="center")
        now_show_jsonl = col1.toggle("🧾 `JSON`", key="jsonl_show", disabled= False if st.session_state.new_record is not None else True, value = st.session_state.show_jsonl)
        if now_show_jsonl:
            show_jsonl_record()
            st.rerun()
    if prompt:
        in_out = {"state": "all", "input": {"question": prompt}, \
                  "output": "", "response": "", "user_prompt":"", "cost_time": str(round(time.time()-start_time, 3))}
        model_logger.info(json.dumps(in_out, ensure_ascii=False))



init_message = ""
if LANGUAGE == "zh":
    init_message = "你好，有什么需要帮忙的？"
elif LANGUAGE == "en":
    init_message = "Hello, what can I do for you?"
# 初始化状态
if "never_ask_again" not in st.session_state:
    st.session_state.never_ask_again = False
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": init_message, "avatar": "logo/icon-mini.gif"}]



def main():
    page_chat()


if __name__ == "__main__":
    main()
