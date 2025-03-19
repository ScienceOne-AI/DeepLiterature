# encoding: utf-8

from abc import ABC, abstractmethod

class BaseLLM(ABC):

    @abstractmethod
    def stream_chat(self, system_content="", user_content="", *args, **kwargs):
        pass
    
    @abstractmethod
    def chat(self, system_content="", user_content="", *args, **kwargs):
        pass