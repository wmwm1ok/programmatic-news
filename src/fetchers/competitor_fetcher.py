"""
竞品资讯抓取器
针对 13 家公司的抓取实现
"""

import re
from datetime import datetime
from typing import List, Optional, Dict, Callable
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseFetcher, ContentItem

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
from config.settings import COMPETITOR_SOURCES


class CompetitorFetcher(BaseFetcher):
    """竞品资讯抓取器"""
    
    def __init__(self):
        super().__init__()
        # 注册各公司的抓取函数
        self.fetchers: Dict[str, Callable] = {
            "TTD": self._fetch_ttd,
            "Criteo": self._fetch_criteo,
            "Taboola": self._fetch_taboola,
            "Teads": self._fetch_teads,
            "AppLovin": self._fetch_applovin,
            "mobvista": self._fetch_mobvista,
            "Moloco": self._fetch_moloco,
            "BIGO Ads": self._fetch_bigo,
            "Unity": self._fetch_unity,
            "Viant Technology": self._fetch_viant,
            "Zeta Global": self._fetch_zeta,
            "PubMatic": self._fetch_pubmatic,
            "Magnite": self._fetch_magnite,
        }
    
    def fetch_all(self, window_start: datetime, window_end: datetime) -> Dict[str, List[ContentItem]]:
        """
        抓取所有竞品资讯
        :param window_start: 窗口开始日期
        :param window_end: 窗口结束日期
        :return: {公司名称: 内容列表}
        """
        results = {}
        
        for company_key, config in COMPETITOR_SOURCES.items():
            print(f"正在抓取: {config['name']}...")
            fetch_func = self.fetchers.get(company_key)
            if fetch_func:
                try:
                    items = fetch_func(window_start, window_end)
                    if items:
                        results[config['name']] = items
                except Exception as e:
                    print(f"  抓取 {config['name']} 失败: {e}")
        
        return results
    
    def _fetch_ttd(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 TTD"""
        url = COMPETITOR_SOURCES["TTD"]["url"]
        html = self.fetch(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        # TTD press room 结构
        articles = soup.find_all('article', class_=re.compile('press-release|news'))
        if not articles:
            articles = soup.find_all('div', class_=re.compile('press-release|news|card'))
        
        for article in articles[:10]:  # 限制数量
            try:
                # 获取链接
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                
                detail_url = self.normalize_url(url, link_elem['href'])
                
                # 获取标题
                title_elem = article.find(['h2', 'h3', 'h4', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                
                # 获取日期
                date_elem = article.find('time') or article.find(class_=re.compile('date|time'))
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                # 验证日期窗口
                if not date_str or not self.is_in_date_window(date_str, window_start, window_end):
                    continue
                
                # 获取详情页内容
                detail_html = self.fetch(detail_url)
                if detail_html:
                    content = self._extract_content(detail_html, detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:500],  # 临时，会被 DeepSeek 重写
                            date=date_str,
                            url=detail_url,
                            source="TTD"
                        ))
            except Exception as e:
                continue
        
        return items
    
    def _fetch_criteo(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Criteo"""
        url = COMPETITOR_SOURCES["Criteo"]["url"]
        html = self.fetch(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        # Criteo investor room 结构
        rows = soup.find_all('tr', class_=re.compile('item|release'))
        if not rows:
            rows = soup.find_all('div', class_=re.compile('item|release|news'))
        
        for row in rows[:10]:
            try:
                link_elem = row.find('a', href=True)
                if not link_elem:
                    continue
                
                detail_url = self.normalize_url(url, link_elem['href'])
                title = self.clean_text(link_elem.get_text())
                
                # 获取日期
                date_elem = row.find('td', class_=re.compile('date')) or row.find('time')
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text())
                
                if not date_str or not self.is_in_date_window(date_str, window_start, window_end):
                    continue
                
                detail_html = self.fetch(detail_url)
                if detail_html:
                    content = self._extract_content(detail_html, detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:500],
                            date=date_str,
                            url=detail_url,
                            source="Criteo"
                        ))
            except Exception as e:
                continue
        
        return items
    
    def _fetch_taboola(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Taboola"""
        url = COMPETITOR_SOURCES["Taboola"]["url"]
        html = self.fetch(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        # Taboola press releases
        articles = soup.find_all('article') or soup.find_all('div', class_=re.compile('post|entry|card'))
        
        for article in articles[:10]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                
                detail_url = self.normalize_url(url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                
                date_elem = article.find('time') or article.find(class_=re.compile('date|published'))
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                if not date_str or not self.is_in_date_window(date_str, window_start, window_end):
                    continue
                
                detail_html = self.fetch(detail_url)
                if detail_html:
                    content = self._extract_content(detail_html, detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:500],
                            date=date_str,
                            url=detail_url,
                            source="Taboola"
                        ))
            except Exception as e:
                continue
        
        return items
    
    def _fetch_teads(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Teads"""
        url = COMPETITOR_SOURCES["Teads"]["url"]
        html = self.fetch(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        articles = soup.find_all('article') or soup.find_all('div', class_=re.compile('press|news|card'))
        
        for article in articles[:10]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                
                detail_url = self.normalize_url(url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                
                date_elem = article.find('time') or article.find(class_=re.compile('date'))
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                if not date_str or not self.is_in_date_window(date_str, window_start, window_end):
                    continue
                
                detail_html = self.fetch(detail_url)
                if detail_html:
                    content = self._extract_content(detail_html, detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:500],
                            date=date_str,
                            url=detail_url,
                            source="Teads"
                        ))
            except Exception as e:
                continue
        
        return items
    
    def _fetch_applovin(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 AppLovin"""
        url = COMPETITOR_SOURCES["AppLovin"]["url"]
        html = self.fetch(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        articles = soup.find_all('article') or soup.find_all('div', class_=re.compile('news|post|card'))
        
        for article in articles[:10]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                
                detail_url = self.normalize_url(url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                
                date_elem = article.find('time') or article.find(class_=re.compile('date'))
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                if not date_str or not self.is_in_date_window(date_str, window_start, window_end):
                    continue
                
                detail_html = self.fetch(detail_url)
                if detail_html:
                    content = self._extract_content(detail_html, detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:500],
                            date=date_str,
                            url=detail_url,
                            source="AppLovin"
                        ))
            except Exception as e:
                continue
        
        return items
    
    def _fetch_mobvista(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 mobvista"""
        url = COMPETITOR_SOURCES["mobvista"]["url"]
        html = self.fetch(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        articles = soup.find_all('article') or soup.find_all('div', class_=re.compile('blog|post|card|entry'))
        
        for article in articles[:10]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                
                detail_url = self.normalize_url(url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                
                date_elem = article.find('time') or article.find(class_=re.compile('date|time'))
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                if not date_str or not self.is_in_date_window(date_str, window_start, window_end):
                    continue
                
                detail_html = self.fetch(detail_url)
                if detail_html:
                    content = self._extract_content(detail_html, detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:500],
                            date=date_str,
                            url=detail_url,
                            source="mobvista"
                        ))
            except Exception as e:
                continue
        
        return items
    
    def _fetch_moloco(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Moloco"""
        url = COMPETITOR_SOURCES["Moloco"]["url"]
        html = self.fetch(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        articles = soup.find_all('article') or soup.find_all('div', class_=re.compile('press|news|card|entry'))
        
        for article in articles[:10]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                
                detail_url = self.normalize_url(url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                
                date_elem = article.find('time') or article.find(class_=re.compile('date'))
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                if not date_str or not self.is_in_date_window(date_str, window_start, window_end):
                    continue
                
                detail_html = self.fetch(detail_url)
                if detail_html:
                    content = self._extract_content(detail_html, detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:500],
                            date=date_str,
                            url=detail_url,
                            source="Moloco"
                        ))
            except Exception as e:
                continue
        
        return items
    
    def _fetch_bigo(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 BIGO Ads"""
        url = COMPETITOR_SOURCES["BIGO Ads"]["url"]
        html = self.fetch(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        articles = soup.find_all('article') or soup.find_all('div', class_=re.compile('blog|post|card|entry'))
        
        for article in articles[:10]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                
                detail_url = self.normalize_url(url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                
                date_elem = article.find('time') or article.find(class_=re.compile('date'))
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                if not date_str or not self.is_in_date_window(date_str, window_start, window_end):
                    continue
                
                detail_html = self.fetch(detail_url)
                if detail_html:
                    content = self._extract_content(detail_html, detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:500],
                            date=date_str,
                            url=detail_url,
                            source="BIGO Ads"
                        ))
            except Exception as e:
                continue
        
        return items
    
    def _fetch_unity(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Unity"""
        url = COMPETITOR_SOURCES["Unity"]["url"]
        html = self.fetch(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        articles = soup.find_all('article') or soup.find_all('div', class_=re.compile('news|post|card|entry'))
        
        for article in articles[:10]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                
                detail_url = self.normalize_url(url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                
                date_elem = article.find('time') or article.find(class_=re.compile('date'))
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                if not date_str or not self.is_in_date_window(date_str, window_start, window_end):
                    continue
                
                detail_html = self.fetch(detail_url)
                if detail_html:
                    content = self._extract_content(detail_html, detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:500],
                            date=date_str,
                            url=detail_url,
                            source="Unity"
                        ))
            except Exception as e:
                continue
        
        return items
    
    def _fetch_viant(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Viant Technology"""
        url = COMPETITOR_SOURCES["Viant Technology"]["url"]
        html = self.fetch(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        articles = soup.find_all('article') or soup.find_all('div', class_=re.compile('press|news|release'))
        
        for article in articles[:10]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                
                detail_url = self.normalize_url(url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                
                date_elem = article.find('time') or article.find(class_=re.compile('date'))
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                if not date_str or not self.is_in_date_window(date_str, window_start, window_end):
                    continue
                
                detail_html = self.fetch(detail_url)
                if detail_html:
                    content = self._extract_content(detail_html, detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:500],
                            date=date_str,
                            url=detail_url,
                            source="Viant Technology"
                        ))
            except Exception as e:
                continue
        
        return items
    
    def _fetch_zeta(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Zeta Global"""
        url = COMPETITOR_SOURCES["Zeta Global"]["url"]
        html = self.fetch(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        rows = soup.find_all('tr', class_=re.compile('item')) or soup.find_all('div', class_=re.compile('item|news'))
        
        for row in rows[:10]:
            try:
                link_elem = row.find('a', href=True)
                if not link_elem:
                    continue
                
                detail_url = self.normalize_url(url, link_elem['href'])
                title = self.clean_text(link_elem.get_text())
                
                date_elem = row.find('td', class_=re.compile('date')) or row.find('time')
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text())
                
                if not date_str or not self.is_in_date_window(date_str, window_start, window_end):
                    continue
                
                detail_html = self.fetch(detail_url)
                if detail_html:
                    content = self._extract_content(detail_html, detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:500],
                            date=date_str,
                            url=detail_url,
                            source="Zeta Global"
                        ))
            except Exception as e:
                continue
        
        return items
    
    def _fetch_pubmatic(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 PubMatic"""
        url = COMPETITOR_SOURCES["PubMatic"]["url"]
        html = self.fetch(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        articles = soup.find_all('article') or soup.find_all('div', class_=re.compile('news|release|item'))
        
        for article in articles[:10]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                
                detail_url = self.normalize_url(url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                
                date_elem = article.find('time') or article.find(class_=re.compile('date'))
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                if not date_str or not self.is_in_date_window(date_str, window_start, window_end):
                    continue
                
                detail_html = self.fetch(detail_url)
                if detail_html:
                    content = self._extract_content(detail_html, detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:500],
                            date=date_str,
                            url=detail_url,
                            source="PubMatic"
                        ))
            except Exception as e:
                continue
        
        return items
    
    def _fetch_magnite(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Magnite"""
        url = COMPETITOR_SOURCES["Magnite"]["url"]
        html = self.fetch(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        articles = soup.find_all('article') or soup.find_all('div', class_=re.compile('press|release|news|item'))
        
        for article in articles[:10]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                
                detail_url = self.normalize_url(url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                
                date_elem = article.find('time') or article.find(class_=re.compile('date'))
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                if not date_str or not self.is_in_date_window(date_str, window_start, window_end):
                    continue
                
                detail_html = self.fetch(detail_url)
                if detail_html:
                    content = self._extract_content(detail_html, detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:500],
                            date=date_str,
                            url=detail_url,
                            source="Magnite"
                        ))
            except Exception as e:
                continue
        
        return items
    
    def _extract_content(self, html: str, url: str) -> str:
        """
        从详情页提取正文内容
        :param html: HTML 内容
        :param url: 页面 URL（用于识别网站类型）
        :return: 正文文本
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # 移除脚本和样式
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        
        # 尝试找到主要内容区域
        content_selectors = [
            'main',
            'article',
            '[role="main"]',
            '.content',
            '.main-content',
            '.post-content',
            '.entry-content',
            '.press-release-content',
            '#content',
            '.container',
        ]
        
        content_elem = None
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                break
        
        if not content_elem:
            content_elem = soup.body
        
        if content_elem:
            text = content_elem.get_text(separator=' ', strip=True)
            return self.clean_text(text)
        
        return ""
