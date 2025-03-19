# encoding: utf-8
import requests

from config import SERPAPI_KEY, SERPAPI_URL, SERPAPI_GL, SERPAPI_HL
from .base_engine import BaseEngine

class SerpEngine(BaseEngine):
    def clean_text(self, input_text):
        return input_text

    def search_title_snippet(self, query, *args, gl=SERPAPI_GL, hl=SERPAPI_HL, **kwargs):
        """
{
    "position": 1,
    "title": "Coffee - Wikipedia",
    "link": "https://en.wikipedia.org/wiki/Coffee",
    "displayed_link": "https://en.wikipedia.org › wiki › Coffee",
    "snippet": "Coffee is a brewed drink prepared from roasted coffee beans, the seeds of berries from certain Coffea species. From the coffee fruit, the seeds are ...",
    "sitelinks": {
        "inline": [
            {
                "title": "History",
                "link": "https://en.wikipedia.org/wiki/History_of_coffee"
            },
            {
                "title": "Coffee bean",
                "link": "https://en.wikipedia.org/wiki/Coffee_bean"
            },
            {
                "title": "Coffee preparation",
                "link": "https://en.wikipedia.org/wiki/Coffee_preparation"
            },
            {
                "title": "Coffee production",
                "link": "https://en.wikipedia.org/wiki/Coffee_production"
            }
        ]
    },
    "rich_snippet": {
        "bottom": {
            "extensions": [
                "Region of origin: Horn of Africa and ‎South Ara...‎",
                "Color: Black, dark brown, light brown, beige",
                "Introduced: 15th century"
            ],
            "detected_extensions": {
                "introduced_th_century": 15
            }
        }
    },
    "about_this_result": {
        "source": {
            "description": "Wikipedia is a free content, multilingual online encyclopedia written and maintained by a community of volunteers through a model of open collaboration, using a wiki-based editing system. Individual contributors, also called editors, are known as Wikipedians.",
            "source_info_link": "https://en.wikipedia.org/wiki/Wikipedia",
            "security": "secure",
            "icon": "https://serpapi.com/searches/6165916694c6c7025deef5ab/images/ed8bda76b255c4dc4634911fb134de53068293b1c92f91967eef45285098b61516f2cf8b6f353fb18774013a1039b1fb.png"
        },
        "keywords": [
            "coffee"
        ],
        "languages": [
            "English"
        ],
        "regions": [
            "the United States"
        ]
    },
    "cached_page_link": "https://webcache.googleusercontent.com/search?q=cache:U6oJMnF-eeUJ:https://en.wikipedia.org/wiki/Coffee+&cd=4&hl=en&ct=clnk&gl=us",
    "related_pages_link": "https://www.google.com/search?q=related:https://en.wikipedia.org/wiki/Coffee+Coffee"
}
"""
        empty_search = False
        params = {
            "q": query,
            "api_key": SERPAPI_KEY,
            "engine": "google",
            "gl": gl,
            "hl": hl
        }
        
        search_response = requests.get(SERPAPI_URL, params=params)
        
        if search_response.status_code != 200:
            empty_search = True
            return empty_search, f"搜索请求失败，状态码: {search_response.status_code}"
        
        search_results = search_response.json().get("organic_results", [])
        for idx in range(len(search_results)):
            search_results[idx]["url"] = search_results[idx]["link"]
            if "snippet" not in search_results[idx]:
                search_results[idx]["snippet"] = search_results[idx]["title"]
        if len(search_results) == 0:
            empty_search = True
        return empty_search, search_results

    
