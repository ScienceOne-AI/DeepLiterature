# encoding: utf-8
import requests
from bs4 import BeautifulSoup
import html

from .base_engine import BaseEngine

class WikiEngine(BaseEngine):
    def clean_text(self, input_text):
        # 创建 BeautifulSoup 对象
        soup = BeautifulSoup(input_text, 'html.parser')

        # 移除所有 class="searchmatch" 的 span 标签
        for span in soup.find_all('span', class_='searchmatch'):
            span.unwrap()

        # 获取纯净的文本
        clean_text = html.unescape(soup.get_text())
        return clean_text

    def search_title_snippet(self, query, lang="en"):
        search_url = f"https://{lang}.wikipedia.org/w/api.php"
        
        search_params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": query,
            "utf8": True
        }
        
        search_response = requests.get(search_url, params=search_params)
        
        if search_response.status_code != 200:
            return f"搜索请求失败，状态码: {search_response.status_code}"
        
        search_results = search_response.json().get("query", {}).get("search", [])
        for idx, search_res in enumerate(search_results):
            now_title = search_res['title']
            whole_abstract = self.get_wiki_abstract(now_title, lang)
            search_results[idx]['abstract'] = whole_abstract

        return search_results

    
    def get_abstract(self, title, lang = "en"):
        search_url = f"https://{lang}.wikipedia.org/w/api.php"
        # 获取页面摘要
        extract_params = {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "extracts",
            "exintro": True,
            "explaintext": True
        }

        extract_response = requests.get(search_url, params=extract_params)
        
        if extract_response.status_code != 200:
            return f"摘要请求失败，状态码: {extract_response.status_code}"
        
        pages = extract_response.json().get("query", {}).get("pages", {})

        page_id = next(iter(pages))
        abstract = pages[page_id].get("extract", "摘要不可用")
        return html.unescape(abstract)