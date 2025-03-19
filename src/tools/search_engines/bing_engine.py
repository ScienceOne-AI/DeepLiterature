# encoding: utf-8
import requests
from bs4 import BeautifulSoup
import html

from .base_engine import BaseEngine

class BingEngine(BaseEngine):
    def clean_text(self, input_text):
        # 创建 BeautifulSoup 对象
        soup = BeautifulSoup(input_text, 'html.parser')

        # 获取纯净的文本
        clean_text = html.unescape(soup.get_text())
        return clean_text

    def search_title_snippet(self, query, lang = "zh", num_results = 10):
        url = f"https://www.bing.com/search?q={query}&count={num_results}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        search_response = requests.get(url, headers=headers)
            
        if search_response.status_code != 200:
            return f"搜索请求失败，状态码: {search_response.status_code}"
        
        soup = BeautifulSoup(search_response.text, 'html.parser')
    
        search_results = []
        for item in soup.find_all('li', class_='b_algo'):
            title = item.find('h2').get_text()
            url = item.find('a')['href']
            snippet = item.find('p').get_text() if item.find('p') else ''
            if len(snippet) > 2 and snippet[:2] == "网页":
                snippet = snippet[2:]
            search_results.append({'title': title, 'url': url, 'snippet': snippet})

        return search_results

