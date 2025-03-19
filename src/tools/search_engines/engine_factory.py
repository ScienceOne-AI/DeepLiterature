# encoding: utf-8

from typing import Literal
from .bing_engine import BingEngine
from .wiki_engine import WikiEngine
from .serp_engine import SerpEngine

class EngineFactory(object):

    @staticmethod
    def construct(engine_name:Literal["wiki", "bing", "customized-search", "serp"]):
        search_engine = None
        if engine_name == "wiki":
            search_engine = WikiEngine()
        elif engine_name == "bing":
            search_engine = BingEngine()
        elif engine_name == "serp":
            search_engine = SerpEngine()
        return search_engine