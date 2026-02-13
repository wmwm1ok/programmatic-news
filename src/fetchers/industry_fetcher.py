"""
行业资讯抓取器
简化版：AdExchanger 抓 Popular Top 5，Search Engine Land 抓最新 3 条
"""

import re
from datetime import datetime
from typing import List, Dict
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseFetcher, ContentItem

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
from config.settings import INDUSTRY_SOURCES


class IndustryFetcher(BaseFetcher):
    """行业资讯抓取器 - 简化版"""
    
    def fetch_all(self, window_start: datetime, window_end: datetime) -> Dict[str, List[ContentItem]]:
        """
        抓取所有行业资讯
        :param window_start: 窗口开始日期
        :param window_end: 窗口结束日期
        :return: {子模块名称: 内容列表}
        """
        results = {}
        
        # 抓取 AdExchanger Popular
        print(f"  [行业] AdExchanger Popular...")
        try:
            items = self._fetch_adexchanger_popular(window_start, window_end)
            results['AdExchanger'] = items
            print(f"    ✓ {len(items)} 条")
        except Exception as e:
            print(f"    ✗ 失败: {str(e)[:80]}")
            results['AdExchanger'] = []
        
        # 抓取 Search Engine Land 最新
        print(f"  [行业] Search Engine Land...")
        try:
            items = self._fetch_searchengineland_latest(window_start, window_end)
            results['Search Engine Land'] = items
            print(f"    ✓ {len(items)} 条")
        except Exception as e:
            print(f"    ✗ 失败: {str(e)[:80]}")
            results['Search Engine Land'] = []
        
        return results
    
    def _fetch_adexchanger_popular(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 AdExchanger Popular 前 5 条"""
        url = 'https://www.adexchanger.com/'
        html = self.fetch(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        # 找 Popular 区块
        popular_heading = soup.find(['h2', 'h3', 'h4'], string=re.compile('popular', re.I))
        if not popular_heading:
            return []
        
        parent = popular_heading.find_parent(['aside', 'div', 'section'])
        if not parent:
            return []
        
        ol = parent.find('ol', class_=re.compile('list-ordered'))
        if not ol:
            return []
        
        # 取前 5 条
        lis = ol.find_all('li', limit=5)
        print(f"    找到 {len(lis)} 条 Popular 文章")
        
        for li in lis:
            try:
                # 在 h3 中找标题和链接
                h3 = li.find('h3')
                if not h3:
                    continue
                
                link = h3.find('a', href=True)
                if not link:
                    continue
                
                title = self.clean_text(link.get_text())
                if not title or len(title) < 10:
                    continue
                
                detail_url = link['href']
                
                # 获取分类
                category_elem = li.find('a', class_='link-label')
                category = category_elem.get_text(strip=True) if category_elem else ''
                
                print(f"    处理: {title[:50]}...")
                
                # 获取详情页内容和日期
                detail_html = self.fetch(detail_url)
                if not detail_html:
                    continue
                
                date_str = self._extract_adexchanger_date(detail_html)
                if not date_str:
                    continue
                
                # 检查日期窗口
                if not self.is_in_date_window(date_str, window_start, window_end):
                    print(f"      - 日期 {date_str} 不在窗口内")
                    continue
                
                content = self._extract_adexchanger_content(detail_html)
                if content:
                    # 在标题前加上分类
                    full_title = f"[{category}] {title}" if category else title
                    items.append(ContentItem(
                        title=full_title,
                        summary=content[:500],
                        date=date_str,
                        url=detail_url,
                        source='AdExchanger'
                    ))
                    print(f"      ✓ 已添加 ({date_str})")
                
            except Exception as e:
                continue
        
        return items
    
    def _extract_adexchanger_date(self, html: str) -> str:
        """从 AdExchanger 详情页提取日期"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # 方法1: time 标签
        time_elem = soup.find('time')
        if time_elem:
            datetime_attr = time_elem.get('datetime', '')
            if datetime_attr:
                match = re.match(r'(\d{4}-\d{2}-\d{2})', datetime_attr)
                if match:
                    return match.group(1)
            date_text = time_elem.get_text()
            parsed = self.parse_date(date_text)
            if parsed:
                return parsed
        
        return ""
    
    def _extract_adexchanger_content(self, html: str) -> str:
        """提取 AdExchanger 详情页内容"""
        soup = BeautifulSoup(html, 'html.parser')
        
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()
        
        content_elem = (
            soup.find('div', class_=re.compile('entry-content|post-content|article-content')) or
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
    
    def _fetch_with_playwright(self, url: str) -> Optional[str]:
        """使用 Playwright 抓取页面（用于反爬网站）"""
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                page = context.new_page()
                page.goto(url, wait_until='networkidle', timeout=30000)
                html = page.content()
                browser.close()
                return html
        except Exception as e:
            print(f"    Playwright 抓取失败: {e}")
            return None
    
    def _fetch_searchengineland_latest(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Search Engine Land 最新 3 条"""
        url = 'https://searchengineland.com/latest-posts'
        
        # 先尝试普通请求
        html = self.fetch(url)
        
        # 如果失败，使用 Playwright
        if not html:
            print(f"    普通请求失败，尝试 Playwright...")
            html = self._fetch_with_playwright(url)
        
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        # 找文章列表
        articles = soup.find_all('article', class_='stream-article', limit=3)
        print(f"    找到 {len(articles)} 篇文章")
        
        for article in articles:
            try:
                title_elem = article.find(['h2', 'h3'])
                if not title_elem:
                    continue
                
                link = title_elem.find('a', href=True)
                if not link:
                    continue
                
                title = self.clean_text(link.get_text())
                if not title or len(title) < 10:
                    continue
                
                detail_url = link['href']
                
                # 提取日期
                date_str = self._extract_sel_date(article)
                if not date_str:
                    continue
                
                # 检查日期窗口
                if not self.is_in_date_window(date_str, window_start, window_end):
                    print(f"    - 日期 {date_str} 不在窗口内: {title[:40]}...")
                    continue
                
                print(f"    处理: {title[:50]}... ({date_str})")
                
                # 获取详情页内容（先尝试普通请求，失败用 Playwright）
                detail_html = self.fetch(detail_url)
                if not detail_html:
                    detail_html = self._fetch_with_playwright(detail_url)
                
                if detail_html:
                    content = self._extract_sel_content(detail_html)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:500],
                            date=date_str,
                            url=detail_url,
                            source='Search Engine Land'
                        ))
                        print(f"      ✓ 已添加")
                
            except Exception as e:
                continue
        
        return items
    
    def _extract_sel_date(self, article) -> str:
        """提取 Search Engine Land 日期"""
        # 方法1: time 标签
        time_elem = article.find('time')
        if time_elem:
            datetime_attr = time_elem.get('datetime', '')
            if datetime_attr:
                match = re.search(r'(\d{4}-\d{2}-\d{2})', datetime_attr)
                if match:
                    return match.group(1)
            parsed = self.parse_date(time_elem.get_text())
            if parsed:
                return parsed
        
        # 方法2: 查找文本日期
        date_pattern = r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}'
        date_matches = article.find_all(string=re.compile(date_pattern, re.IGNORECASE))
        for match in date_matches:
            date_text = match.strip()
            if date_text:
                parsed = self.parse_date(date_text)
                if parsed:
                    return parsed
        
        # 方法3: 通用日期类
        date_elem = article.find(class_=re.compile('date|published|time'))
        if date_elem:
            parsed = self.parse_date(date_elem.get_text())
            if parsed:
                return parsed
        
        return ""
    
    def _extract_sel_content(self, html: str) -> str:
        """提取 Search Engine Land 详情页内容"""
        soup = BeautifulSoup(html, 'html.parser')
        
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()
        
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
