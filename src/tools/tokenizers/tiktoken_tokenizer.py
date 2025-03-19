# encoding: utf-8

import tiktoken
from .base_tokenizer import BaseTokenizer


class TikTokenTokenizer(BaseTokenizer):
    def __init__(self, model_name):
        self.enc = tiktoken.encoding_for_model(model_name)

    def tokenize(self, text):
        return self.enc.encode(text)