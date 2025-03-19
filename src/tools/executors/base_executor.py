# encoding: utf-8

from abc import ABC, abstractmethod

class BaseExecutor(ABC):
    
    @abstractmethod
    def execute(self, query, *args, **kwargs):
        pass