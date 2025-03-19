# encoding: utf-8

from typing import Literal
import importlib
from .remote_llm import RemoteLLM
from .remote_reasoning_llm import RemoteReasoningLLM
from config import REMOTE_LLM_TOKENIZER_NAME_OR_PATH, REMOTE_LLM_TOKENIZER_CLASS, REMOTE_REASONING_LLM_TOKENIZER_NAME_OR_PATH, REMOTE_REASONING_LLM_TOKENIZER_CLASS


class LLMFactory(object):
    @staticmethod
    def construct(model_name:Literal["remote-llm", "remote-reasoning-llm"]):
        llm = None
        if model_name == "remote-llm":
            tokenizer = getattr(importlib.import_module("tools.tokenizers"), REMOTE_LLM_TOKENIZER_CLASS)(REMOTE_LLM_TOKENIZER_NAME_OR_PATH)
            llm = RemoteLLM(tokenizer=tokenizer)
        elif model_name == "remote-reasoning-llm":
            tokenizer = getattr(importlib.import_module("tools.tokenizers"), REMOTE_REASONING_LLM_TOKENIZER_CLASS)(REMOTE_REASONING_LLM_TOKENIZER_NAME_OR_PATH)
            llm = RemoteReasoningLLM(tokenizer=tokenizer)
        return llm