# encoding: utf-8
import os
from transformers import AutoTokenizer
from .base_tokenizer import BaseTokenizer
from config import RESOURCES_PATH

class TransformersTokenizer(BaseTokenizer):
    def __init__(self, tokenizer_name_or_path):
        _path = os.path.join(RESOURCES_PATH, tokenizer_name_or_path)
        if os.path.exists(_path):
            self.tokenizer = AutoTokenizer.from_pretrained(_path)
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name_or_path)
    
    def tokenize(self, text):
        model_inputs = self.tokenizer([text], return_tensors="pt")
        tokens = model_inputs["input_ids"].tolist()[0]
        return tokens