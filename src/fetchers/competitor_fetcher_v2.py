"""
竞品资讯抓取器 V2 - 优化版
针对实际网站结构优化
"""

import re
import time
from datetime import datetime
from typing import List, Optional, Dict
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import BaseFetcher, ContentItem

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
from config.settings import COMPETITOR_SOURCES, SCRAPER_CONFIG


class CompetitorFetcherV2(BaseFetcher):
    """优化版竞品资讯抓取器"""
    
    def __init__(self):
        super().__init__()
        self.debug = True
        
    def log(self, msg):
        if self.debug:
            print(f"    [DEBUG] {msg}")
    
    def fetch_all(self, window_start: datetime, window_end: datetime) -> Dict[str, List[ContentItem]]:
        """抓取所有竞品资讯"""
        results = {}
        
        fetchers_map = {
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
        
        for company_key, config in COMPETITOR_SOURCES.items():
            print(f"  [抓取] {config['name']}...")
            try:
                fetch_func = fetchers_map.get(company_key)
                if fetch_func:
                    items = fetch_func(config["url"], window_start, window_end)
                    if items:
                        results[config['name']] = items
                        print(f"    ✓ 找到 {len(items)} 条")
                    else:
                        print(f"    - 无符合条件的内容")
                else:
                    print(f"    ✗ 无抓取函数")
            except Exception as e:
                print(f"    ✗ 错误: {str(e)[:80]}")
            time.sleep(0.5)  # 礼貌请求间隔
            
        return results
    
    def _fetch_ttd(self, base_url: str, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 TTD - thetradedesk.com"""
        items = []
        html = self.fetch(base_url)
        if not html:
            print("    ✗ 无法获取页面")
            return items
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # TTD 网站结构：卡片式布局
        # 尝试多种选择器
        selectors = [
            'a[href*="/news/"]',
            'a[href*="/press-room/"]',
            '.card a', '.news-item a', '.press-item a',
            'article a', '.post a'
        ]
        
        links = []
        for selector in selectors:
            links = soup.select(selector)
            if links:
                print(f"    使用选择器: {selector}, 找到 {len(links)} 个链接")
                break
        
        if not links:
            print("    ✗ 未找到任何链接")
            return items
        
        for link in links[:15]:
            try:
                href = link.get('href', '')
                if not href or href.startswith('#') or href.startswith('javascript'):
                    continue
                    
                detail_url = urljoin(base_url, href)
                title = self.clean_text(link.get_text())
                
                if not title or len(title) < 10:
                    continue
                
                # 尝试从链接或父元素获取日期
                date_str = self._extract_date_from_element(link) or self._extract_date_from_url(href)
                
                # 日期解析失败时，尝试从详情页获取
                if not date_str:
                    print(f"    尝试从详情页获取日期: {title[:40]}...")
                    content = self._fetch_detail_content(detail_url)
                    if content:
                        # 尝试从内容中提取日期
                        date_match = __import__('re').search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', content[:1000])
                        if date_match:
                            date_str = f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"
                    if date_str:
                        print(f"      从详情页获取到日期: {date_str}")
                
                # 如果还是没有日期，默认使用今天（作为备选）
                if not date_str:
                    from datetime import datetime
                    date_str = datetime.now().strftime('%Y-%m-%d')
                    print(f"    警告: 未找到日期，使用今天: {title[:40]}...")
                
                # 检查日期是否在窗口内
                if self.is_in_date_window(date_str, window_start, window_end):
                    # 获取详情页内容（如果还没有获取）
                    content = self._fetch_detail_content(detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:600],
                            date=date_str,
                            url=detail_url,
                            source="TTD"
                        ))
                        print(f"    ✓ 已添加: {title[:50]}... ({date_str})")
                else:
                    print(f"    - 跳过 (日期 {date_str} 不在窗口 {window_start.date()} ~ {window_end.date()})")
                    
            except Exception as e:
                print(f"    ✗ 处理条目出错: {e}")
                continue
                
        return items
    
    def _fetch_criteo(self, base_url: str, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Criteo - criteo.investorroom.com"""
        items = []
        html = self.fetch(base_url)
        if not html:
            return items
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Criteo IR 网站通常是表格或列表形式
        selectors = [
            'table tr', '.item', '.release-item', 
            '.news-item', 'article', '.card'
        ]
        
        rows = []
        for selector in selectors:
            rows = soup.select(selector)
            if rows:
                self.log(f"Criteo 使用选择器: {selector}, 找到 {len(rows)} 个")
                break
        
        for row in rows[:15]:
            try:
                link_elem = row.find('a', href=True)
                if not link_elem:
                    continue
                    
                detail_url = urljoin(base_url, link_elem['href'])
                title = self.clean_text(link_elem.get_text())
                
                if not title or len(title) < 10:
                    continue
                
                # 获取日期 - Criteo 通常在表格中有日期列
                date_elem = (row.find('td', class_=re.compile('date')) or 
                            row.find('time') or 
                            row.find(class_=re.compile('date|time')))
                
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text())
                
                # 尝试从 URL 解析日期
                if not date_str:
                    date_str = self._extract_date_from_url(detail_url)
                
                self.log(f"Criteo: {title[:40]}... | 日期: {date_str}")
                
                if date_str and self.is_in_date_window(date_str, window_start, window_end):
                    content = self._fetch_detail_content(detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:600],
                            date=date_str,
                            url=detail_url,
                            source="Criteo"
                        ))
                        
            except Exception as e:
                continue
                
        return items
    
    def _fetch_taboola(self, base_url: str, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Taboola"""
        items = []
        html = self.fetch(base_url)
        if not html:
            return items
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Taboola 博客结构
        articles = soup.find_all('article') or soup.select('.post, .entry, .blog-post')
        self.log(f"Taboola 找到 {len(articles)} 篇文章")
        
        for article in articles[:15]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                    
                detail_url = urljoin(base_url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                
                # 获取日期
                date_elem = (article.find('time') or 
                            article.find(class_=re.compile('date|published')) or
                            article.find('span', class_=re.compile('date')))
                
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                self.log(f"Taboola: {title[:40]}... | 日期: {date_str}")
                
                if date_str and self.is_in_date_window(date_str, window_start, window_end):
                    content = self._fetch_detail_content(detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:600],
                            date=date_str,
                            url=detail_url,
                            source="Taboola"
                        ))
                        
            except Exception as e:
                continue
                
        return items
    
    def _fetch_teads(self, base_url: str, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Teads"""
        items = []
        html = self.fetch(base_url)
        if not html:
            return items
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # 尝试多种选择器
        selectors = ['.card', 'article', '.press-item', '.news-item', '.post']
        articles = []
        for selector in selectors:
            articles = soup.select(selector)
            if articles:
                self.log(f"Teads 使用选择器: {selector}, 找到 {len(articles)} 篇")
                break
        
        for article in articles[:15]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                    
                detail_url = urljoin(base_url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                if not title or len(title) < 10:
                    continue
                
                # 日期提取 - 优先从 URL
                date_str = self._extract_date_from_url(detail_url)
                
                # 备选：从元素
                if not date_str:
                    date_elem = article.find('time') or article.find(class_=re.compile('date'))
                    if date_elem:
                        date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                # 备选：使用今天
                if not date_str:
                    from datetime import datetime
                    date_str = datetime.now().strftime('%Y-%m-%d')
                    self.log(f"  Teads: 未找到日期，使用今天: {title[:40]}...")
                
                if self.is_in_date_window(date_str, window_start, window_end):
                    content = self._fetch_detail_content(detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:600],
                            date=date_str,
                            url=detail_url,
                            source="Teads"
                        ))
                        self.log(f"  -> 已添加: {title[:40]}... ({date_str})")
                        
            except Exception as e:
                continue
                
        return items
    
    def _fetch_applovin(self, base_url: str, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 AppLovin"""
        items = []
        html = self.fetch(base_url)
        if not html:
            return items
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # 尝试多种选择器
        selectors = ['.news-item', 'article', '.post', '.card', '[class*="news"]', '[class*="press"]']
        articles = []
        for selector in selectors:
            articles = soup.select(selector)
            if articles:
                self.log(f"AppLovin 使用选择器: {selector}, 找到 {len(articles)} 篇")
                break
        
        for article in articles[:15]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                    
                detail_url = urljoin(base_url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                if not title or len(title) < 10:
                    continue
                
                # 日期提取
                date_str = self._extract_date_from_url(detail_url)
                if not date_str:
                    date_elem = article.find('time') or article.find(class_=re.compile('date'))
                    if date_elem:
                        date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                if not date_str:
                    from datetime import datetime
                    date_str = datetime.now().strftime('%Y-%m-%d')
                
                if self.is_in_date_window(date_str, window_start, window_end):
                    content = self._fetch_detail_content(detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:600],
                            date=date_str,
                            url=detail_url,
                            source="AppLovin"
                        ))
                        self.log(f"  -> 已添加: {title[:40]}... ({date_str})")
                        
            except Exception as e:
                continue
                
        return items
    
    def _fetch_unity(self, base_url: str, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Unity"""
        items = []
        html = self.fetch(base_url)
        if not html:
            return items
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Unity - 尝试多种选择器
        selectors = ['[data-testid="article-card"]', 'article', '.news-item', '.post', '.card']
        articles = []
        for selector in selectors:
            articles = soup.select(selector)
            if articles:
                self.log(f"Unity 使用选择器: {selector}, 找到 {len(articles)} 篇")
                break
        
        for article in articles[:15]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                    
                detail_url = urljoin(base_url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                if not title or len(title) < 10:
                    continue
                
                # Unity 日期通常在 URL 中: /news/2026/02/10/...
                date_str = self._extract_date_from_url(detail_url)
                
                if not date_str:
                    date_elem = article.find('time') or article.find(class_=re.compile('date'))
                    if date_elem:
                        date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                if not date_str:
                    from datetime import datetime
                    date_str = datetime.now().strftime('%Y-%m-%d')
                
                if self.is_in_date_window(date_str, window_start, window_end):
                    content = self._fetch_detail_content(detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:600],
                            date=date_str,
                            url=detail_url,
                            source="Unity"
                        ))
                        self.log(f"  -> 已添加: {title[:40]}... ({date_str})")
                        
            except Exception as e:
                continue
                
        return items
    
    def _fetch_zeta(self, base_url: str, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Zeta Global"""
        items = []
        html = self.fetch(base_url)
        if not html:
            return items
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Zeta IR 网站 - 尝试多种选择器
        selectors = ['table tr', '.item', '.news-item', '.release-item']
        rows = []
        for selector in selectors:
            rows = soup.select(selector)
            if rows:
                self.log(f"Zeta 使用选择器: {selector}, 找到 {len(rows)} 行")
                break
        
        for row in rows[:15]:
            try:
                link_elem = row.find('a', href=True)
                if not link_elem:
                    continue
                    
                detail_url = urljoin(base_url, link_elem['href'])
                title = self.clean_text(link_elem.get_text())
                if not title or len(title) < 10:
                    continue
                
                # 日期提取
                date_str = self._extract_date_from_url(detail_url)
                if not date_str:
                    date_elem = row.find('td', class_=re.compile('date')) or row.find('time')
                    if date_elem:
                        date_str = self.parse_date(date_elem.get_text())
                
                if not date_str:
                    continue
                
                if self.is_in_date_window(date_str, window_start, window_end):
                    content = self._fetch_detail_content(detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:600],
                            date=date_str,
                            url=detail_url,
                            source="Zeta Global"
                        ))
                        self.log(f"  -> 已添加: {title[:40]}... ({date_str})")
                        
            except Exception as e:
                continue
                
        return items
    
    def _fetch_mobvista(self, base_url: str, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 mobvista"""
        items = []
        html = self.fetch(base_url)
        if not html:
            return items
            
        soup = BeautifulSoup(html, 'html.parser')
        articles = soup.find_all('article') or soup.select('.blog-post, .post, .entry')
        
        for article in articles[:10]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                    
                detail_url = urljoin(base_url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                
                date_elem = article.find('time') or article.find(class_=re.compile('date'))
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                if date_str and self.is_in_date_window(date_str, window_start, window_end):
                    content = self._fetch_detail_content(detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:600],
                            date=date_str,
                            url=detail_url,
                            source="mobvista"
                        ))
                        
            except Exception as e:
                continue
                
        return items
    
    def _fetch_moloco(self, base_url: str, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Moloco"""
        items = []
        html = self.fetch(base_url)
        if not html:
            return items
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # 尝试多种选择器
        selectors = ['article', '.press-item', '.news-item', '.post', '.card', '[class*="press"]', '[class*="news"]']
        articles = []
        for selector in selectors:
            articles = soup.select(selector)
            if articles:
                self.log(f"Moloco 使用选择器: {selector}, 找到 {len(articles)} 篇")
                break
        
        for article in articles[:10]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                    
                detail_url = urljoin(base_url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                if not title or len(title) < 10:
                    continue
                
                # 日期提取
                date_str = self._extract_date_from_url(detail_url)
                if not date_str:
                    date_elem = article.find('time') or article.find(class_=re.compile('date'))
                    if date_elem:
                        date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                if not date_str:
                    from datetime import datetime
                    date_str = datetime.now().strftime('%Y-%m-%d')
                
                if self.is_in_date_window(date_str, window_start, window_end):
                    content = self._fetch_detail_content(detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:600],
                            date=date_str,
                            url=detail_url,
                            source="Moloco"
                        ))
                        self.log(f"  -> 已添加: {title[:40]}... ({date_str})")
                        
            except Exception as e:
                continue
                
        return items
    
    def _fetch_bigo(self, base_url: str, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 BIGO Ads"""
        items = []
        html = self.fetch(base_url)
        if not html:
            return items
            
        soup = BeautifulSoup(html, 'html.parser')
        articles = soup.find_all('article') or soup.select('.blog-post, .post')
        
        for article in articles[:10]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                    
                detail_url = urljoin(base_url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                
                date_elem = article.find('time') or article.find(class_=re.compile('date'))
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                if date_str and self.is_in_date_window(date_str, window_start, window_end):
                    content = self._fetch_detail_content(detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:600],
                            date=date_str,
                            url=detail_url,
                            source="BIGO Ads"
                        ))
                        
            except Exception as e:
                continue
                
        return items
    
    def _fetch_viant(self, base_url: str, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Viant Technology"""
        items = []
        html = self.fetch(base_url)
        if not html:
            return items
            
        soup = BeautifulSoup(html, 'html.parser')
        articles = soup.find_all('article') or soup.select('.press-item, .news-item')
        
        for article in articles[:10]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                    
                detail_url = urljoin(base_url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                
                date_elem = article.find('time') or article.find(class_=re.compile('date'))
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                if date_str and self.is_in_date_window(date_str, window_start, window_end):
                    content = self._fetch_detail_content(detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:600],
                            date=date_str,
                            url=detail_url,
                            source="Viant Technology"
                        ))
                        
            except Exception as e:
                continue
                
        return items
    
    def _fetch_pubmatic(self, base_url: str, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 PubMatic"""
        items = []
        html = self.fetch(base_url)
        if not html:
            return items
            
        soup = BeautifulSoup(html, 'html.parser')
        articles = soup.find_all('article') or soup.select('.news-item, .press-item')
        
        for article in articles[:10]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                    
                detail_url = urljoin(base_url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                
                date_elem = article.find('time') or article.find(class_=re.compile('date'))
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                if date_str and self.is_in_date_window(date_str, window_start, window_end):
                    content = self._fetch_detail_content(detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:600],
                            date=date_str,
                            url=detail_url,
                            source="PubMatic"
                        ))
                        
            except Exception as e:
                continue
                
        return items
    
    def _fetch_magnite(self, base_url: str, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Magnite"""
        items = []
        html = self.fetch(base_url)
        if not html:
            return items
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # 尝试多种选择器
        selectors = ['article', '.press-item', '.news-item', '.post', 'table tr']
        articles = []
        for selector in selectors:
            articles = soup.select(selector)
            if articles:
                self.log(f"Magnite 使用选择器: {selector}, 找到 {len(articles)} 个")
                break
        
        for article in articles[:10]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                    
                detail_url = urljoin(base_url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                if not title or len(title) < 10:
                    continue
                
                # 日期提取
                date_str = self._extract_date_from_url(detail_url)
                if not date_str:
                    date_elem = article.find('time') or article.find(class_=re.compile('date'))
                    if date_elem:
                        date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                if not date_str:
                    continue
                
                if self.is_in_date_window(date_str, window_start, window_end):
                    content = self._fetch_detail_content(detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:600],
                            date=date_str,
                            url=detail_url,
                            source="Magnite"
                        ))
                        self.log(f"  -> 已添加: {title[:40]}... ({date_str})")
                        
            except Exception as e:
                continue
                
        return items
    
    def _extract_date_from_element(self, elem) -> Optional[str]:
        """从元素中提取日期"""
        # 查找父元素中的日期
        parent = elem.parent
        for _ in range(5):  # 向上查找5层
            if not parent:
                break
            
            # 查找日期元素
            date_elem = (parent.find('time') or 
                        parent.find(class_=re.compile('date|time|published')) or
                        parent.find(string=re.compile(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}')))
            
            if date_elem:
                date_text = date_elem.get_text() if hasattr(date_elem, 'get_text') else str(date_elem)
                parsed = self.parse_date(date_text)
                if parsed:
                    return parsed
            
            parent = parent.parent
        
        return None
    
    def _extract_date_from_url(self, url: str) -> Optional[str]:
        """从URL中提取日期"""
        # 匹配 /2024/01/15/ 或 /20240115/ 格式
        patterns = [
            r'/(\d{4})/(\d{1,2})/(\d{1,2})/',
            r'/(\d{4})-(\d{1,2})-(\d{1,2})/',
            r'/(\d{4})(\d{2})(\d{2})/',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                year, month, day = match.groups()
                return f"{year}-{int(month):02d}-{int(day):02d}"
        
        return None
    
    def _fetch_detail_content(self, url: str) -> str:
        """获取详情页内容"""
        html = self.fetch(url)
        if not html:
            return ""
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 移除脚本和样式
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        
        # 尝试找到主要内容
        content_selectors = [
            'main article',
            'article',
            '[role="main"]',
            '.content',
            '.main-content',
            '.post-content',
            '.entry-content',
            '.press-release-content',
            '#content',
            'main',
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                text = content_elem.get_text(separator=' ', strip=True)
                return self.clean_text(text)
        
        # 如果找不到特定容器，获取body文本
        body = soup.body
        if body:
            return self.clean_text(body.get_text(separator=' ', strip=True))
        
        return ""
