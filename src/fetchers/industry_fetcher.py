"""
行业资讯抓取器
针对 5 个子模块的抓取实现
"""

import re
from datetime import datetime
from typing import List, Dict

from bs4 import BeautifulSoup

from .base import BaseFetcher, ContentItem

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
from config.settings import INDUSTRY_SOURCES


class IndustryFetcher(BaseFetcher):
    """行业资讯抓取器"""
    
    def __init__(self):
        super().__init__()
    
    def fetch_all(self, window_start: datetime, window_end: datetime) -> Dict[str, List[ContentItem]]:
        """
        抓取所有行业资讯
        :param window_start: 窗口开始日期
        :param window_end: 窗口结束日期
        :return: {子模块名称: 内容列表}
        """
        results = {}
        
        for module_name, config in INDUSTRY_SOURCES.items():
            print(f"  [行业] {config['name']}...")
            try:
                items = self._fetch_module(config, window_start, window_end)
                results[config['name']] = items
                print(f"    ✓ {len(items)} 条")
            except Exception as e:
                print(f"    ✗ 失败: {str(e)[:80]}")
                results[config['name']] = []
        
        return results
    
    def _fetch_module(self, config: dict, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """
        抓取单个模块
        :param config: 模块配置
        :param window_start: 窗口开始日期
        :param window_end: 窗口结束日期
        :return: 内容列表
        """
        url = config["url"]
        max_items = config.get("max_items", 3)
        
        html = self.fetch(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        # 根据网站类型选择不同的解析策略
        if "adexchanger.com" in url:
            items = self._parse_adexchanger(soup, url, config["name"], window_start, window_end, max_items)
        elif "searchengineland.com" in url:
            items = self._parse_searchengineland(soup, url, config["name"], window_start, window_end, max_items)
        
        return items
    
    def _parse_adexchanger(self, soup: BeautifulSoup, base_url: str, module_name: str, 
                           window_start: datetime, window_end: datetime, max_items: int) -> List[ContentItem]:
        """
        解析 AdExchanger 网站
        """
        items = []
        
        # AdExchanger 的文章列表结构
        articles = soup.find_all('article', class_=re.compile('post|entry'))
        if not articles:
            # 尝试其他选择器
            articles = soup.find_all('div', class_=re.compile('post|entry|card|article'))
        if not articles:
            articles = soup.find_all('article')
        
        for article in articles:
            if len(items) >= max_items:
                break
            
            try:
                # 获取标题和链接
                title_elem = article.find(['h2', 'h3', 'h1'], class_=re.compile('title|heading'))
                if not title_elem:
                    title_elem = article.find(['h2', 'h3', 'h1'])
                
                if not title_elem:
                    continue
                
                link_elem = title_elem.find('a', href=True)
                if not link_elem:
                    # 尝试在其他位置找链接
                    link_elem = article.find('a', href=True, class_=re.compile('title|read|more'))
                
                if not link_elem:
                    continue
                
                title = self.clean_text(link_elem.get_text())
                detail_url = self.normalize_url(base_url, link_elem['href'])
                
                # 获取日期
                date_str = self._extract_adexchanger_date(article)
                
                if not date_str or not self.is_in_date_window(date_str, window_start, window_end):
                    continue
                
                # 获取详情页内容
                detail_html = self.fetch(detail_url)
                if detail_html:
                    content = self._extract_adexchanger_content(detail_html)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:500],
                            date=date_str,
                            url=detail_url,
                            source=module_name
                        ))
            except Exception as e:
                continue
        
        return items
    
    def _extract_adexchanger_date(self, article) -> str:
        """提取 AdExchanger 日期"""
        # 尝试多种日期选择器
        date_elem = (
            article.find('time', class_=re.compile('date|published')) or
            article.find('span', class_=re.compile('date|time')) or
            article.find(class_=re.compile('date|published|time'))
        )
        
        if date_elem:
            date_text = date_elem.get_text()
            return self.parse_date(date_text) or self.parse_date(date_elem.get('datetime', ''))
        
        return ""
    
    def _extract_adexchanger_content(self, html: str) -> str:
        """提取 AdExchanger 详情页内容"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # 移除脚本和样式
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()
        
        # 找到主要内容
        content_elem = (
            soup.find('div', class_=re.compile('entry-content|post-content|article-content')) or
            soup.find('article') or
            soup.find('main') or
            soup.find('div', class_=re.compile('content'))
        )
        
        if content_elem:
            # 获取段落文本
            paragraphs = content_elem.find_all(['p', 'h2', 'h3', 'h4'])
            if paragraphs:
                text = ' '.join([p.get_text(strip=True) for p in paragraphs[:10]])
                return self.clean_text(text)
            else:
                text = content_elem.get_text(separator=' ', strip=True)
                return self.clean_text(text)
        
        return ""
    
    def _parse_searchengineland(self, soup: BeautifulSoup, base_url: str, module_name: str,
                                window_start: datetime, window_end: datetime, max_items: int) -> List[ContentItem]:
        """
        解析 Search Engine Land 网站
        """
        items = []
        
        # Search Engine Land 的文章列表结构
        articles = soup.find_all('article', class_=re.compile('post|article'))
        if not articles:
            articles = soup.find_all('div', class_=re.compile('post|article|card'))
        
        for article in articles:
            if len(items) >= max_items:
                break
            
            try:
                # 获取标题和链接
                title_elem = article.find(['h2', 'h3', 'h1'])
                if not title_elem:
                    continue
                
                link_elem = title_elem.find('a', href=True)
                if not link_elem:
                    link_elem = article.find('a', href=True, class_=re.compile('title'))
                
                if not link_elem:
                    continue
                
                title = self.clean_text(link_elem.get_text())
                detail_url = self.normalize_url(base_url, link_elem['href'])
                
                # 获取日期
                date_str = self._extract_sel_date(article)
                
                if not date_str or not self.is_in_date_window(date_str, window_start, window_end):
                    continue
                
                # 获取详情页内容
                detail_html = self.fetch(detail_url)
                if detail_html:
                    content = self._extract_sel_content(detail_html)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:500],
                            date=date_str,
                            url=detail_url,
                            source=module_name
                        ))
            except Exception as e:
                continue
        
        return items
    
    def _extract_sel_date(self, article) -> str:
        """提取 Search Engine Land 日期"""
        date_elem = (
            article.find('time', class_=re.compile('date|published')) or
            article.find('span', class_=re.compile('date|time')) or
            article.find(class_=re.compile('date|published'))
        )
        
        if date_elem:
            date_text = date_elem.get_text()
            return self.parse_date(date_text) or self.parse_date(date_elem.get('datetime', ''))
        
        return ""
    
    def _extract_sel_content(self, html: str) -> str:
        """提取 Search Engine Land 详情页内容"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # 移除脚本和样式
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()
        
        # 找到主要内容
        content_elem = (
            soup.find('div', class_=re.compile('entry-content|post-content|article-body')) or
            soup.find('article') or
            soup.find('main') or
            soup.find('div', class_=re.compile('content'))
        )
        
        if content_elem:
            paragraphs = content_elem.find_all(['p', 'h2', 'h3', 'h4'])
            if paragraphs:
                text = ' '.join([p.get_text(strip=True) for p in paragraphs[:10]])
                return self.clean_text(text)
            else:
                text = content_elem.get_text(separator=' ', strip=True)
                return self.clean_text(text)
        
        return ""
