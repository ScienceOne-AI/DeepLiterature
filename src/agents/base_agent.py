# encoding: utf-8

from abc import ABC, abstractmethod

class BaseAgent(ABC):
    
    @abstractmethod
    def run(self, query, *args, **kwargs):
        pass