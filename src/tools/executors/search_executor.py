# encoding: utf-8

from tools.search_engines import EngineFactory
from .base_executor import BaseExecutor

class SearchExecutor(BaseExecutor):
    def __init__(self, engine_name):
        self.search_engine = EngineFactory.construct(engine_name)

    def execute(self, keyword, verbose, *args, **kwargs):    
        empty_search, new_keyword_search_res =  self.search_engine.search_title_snippet(keyword, verbose=verbose)
        return keyword, empty_search, new_keyword_search_res