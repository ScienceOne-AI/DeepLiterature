# encoding: utf-8

from abc import ABC, abstractmethod

class BaseTokenizer(ABC):
    @abstractmethod
    def tokenize(self, text):
        pass