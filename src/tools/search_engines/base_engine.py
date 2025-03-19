# encoding: utf-8

from abc import ABC, abstractmethod

class BaseEngine(ABC):
    @abstractmethod
    def clean_text(self, input_text):
        pass

    @abstractmethod
    def search_title_snippet(self, query):
        pass