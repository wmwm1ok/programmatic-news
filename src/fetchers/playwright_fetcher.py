"""
使用 Playwright 的抓取器 - 处理 JavaScript 渲染的网站
"""

import re
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import ContentItem

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
from config.settings import COMPETITOR_SOURCES


class PlaywrightFetcher:
    """使用 Playwright 的抓取器"""
    
    def __init__(self):
        self.browser = None
        self.context = None
    
    def _init_browser(self):
        """初始化浏览器"""
        if self.browser is None:
            try:
                from playwright.sync_api import sync_playwright
                self.pw = sync_playwright().start()
                self.browser = self.pw.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
                )
                self.context = self.browser.new_context(
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={'width': 1920, 'height': 1080}
                )
            except ImportError:
                print("  [!] Playwright 未安装，使用 requests 模式")
                return False
            except Exception as e:
                print(f"  [!] Playwright 启动失败: {e}")
                return False
        return True
    
    def fetch_page(self, url: str, wait_for: str = None, timeout: int = 30000) -> str:
        """
        使用 Playwright 获取页面
        :param url: URL
        :param wait_for: 等待特定选择器
        :param timeout: 超时时间
        :return: HTML 内容
        """
        if not self._init_browser():
            return None
        
        page = self.context.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=timeout)
            
            if wait_for:
                page.wait_for_selector(wait_for, timeout=10000)
            
            # 等待 JavaScript 渲染
            page.wait_for_timeout(3000)
            
            html = page.content()
            page.close()
            return html
        except Exception as e:
            print(f"    [!] Playwright 错误: {e}")
            page.close()
            return None
    
    def close(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
        if hasattr(self, 'pw'):
            self.pw.stop()
    
    def parse_date(self, date_str: str) -> Optional[str]:
        """解析日期"""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # 常见日期格式
        patterns = [
            (r"(\d{4})-(\d{1,2})-(\d{1,2})", lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"),
            (r"(\d{1,2})/(\d{1,2})/(\d{4})", lambda m: f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"),
            (r"(\d{4})/(\d{1,2})/(\d{1,2})", lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"),
            (r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})", 
             lambda m: f"{m.group(3)}-{self._month_abbr_to_num(m.group(2)):02d}-{int(m.group(1)):02d}"),
            (r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2}),?\s+(\d{4})", 
             lambda m: f"{m.group(3)}-{self._month_abbr_to_num(m.group(1)):02d}-{int(m.group(2)):02d}"),
            (r"(\d{4}-\d{2}-\d{2})T", lambda m: m.group(1)),
        ]
        
        for pattern, formatter in patterns:
            match = re.search(pattern, date_str, re.IGNORECASE)
            if match:
                try:
                    return formatter(match)
                except:
                    continue
        
        return None
    
    def _month_abbr_to_num(self, month_abbr: str) -> int:
        """月份缩写转数字"""
        months = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        return months.get(month_abbr.lower()[:3], 1)
    
    def is_in_date_window(self, date_str: str, window_start: datetime, window_end: datetime) -> bool:
        """检查日期是否在窗口内"""
        if not date_str:
            return False
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return window_start.date() <= date_obj.date() <= window_end.date()
        except:
            return False
    
    def clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        return text.strip()
    
    def fetch_applovin(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 AppLovin"""
        items = []
        url = COMPETITOR_SOURCES["AppLovin"]["url"]
        
        print("  [Playwright] 抓取 AppLovin...")
        html = self.fetch_page(url, wait_for="article, .news-item, .post")
        if not html:
            return items
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 尝试多种选择器
        articles = (soup.find_all('article') or 
                   soup.select('.news-item') or 
                   soup.select('.post') or
                   soup.select('[class*="news"]') or
                   soup.select('[class*="post"]'))
        
        print(f"    找到 {len(articles)} 篇文章")
        
        for article in articles[:10]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                
                detail_url = urljoin(url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1', 'h4']) or link_elem
                title = self.clean_text(title_elem.get_text())
                
                if not title or len(title) < 10:
                    continue
                
                # 获取日期
                date_elem = (article.find('time') or 
                            article.find(class_=re.compile('date|time')) or
                            article.find(string=re.compile(r'\w+ \d{1,2},? \d{4}')))
                
                date_str = ""
                if date_elem:
                    date_text = date_elem.get_text() if hasattr(date_elem, 'get_text') else str(date_elem)
                    date_str = self.parse_date(date_text)
                
                print(f"    - {title[:40]}... | 日期: {date_str}")
                
                if date_str and self.is_in_date_window(date_str, window_start, window_end):
                    content = self._fetch_detail(detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:600],
                            date=date_str,
                            url=detail_url,
                            source="AppLovin"
                        ))
                        print(f"      -> 已添加")
                        
            except Exception as e:
                print(f"    处理出错: {e}")
                continue
        
        return items
    
    def fetch_unity(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Unity"""
        items = []
        url = COMPETITOR_SOURCES["Unity"]["url"]
        
        print("  [Playwright] 抓取 Unity...")
        html = self.fetch_page(url, wait_for="article, .news-item")
        if not html:
            return items
        
        soup = BeautifulSoup(html, 'html.parser')
        articles = soup.find_all('article') or soup.select('.news-item, .post')
        
        print(f"    找到 {len(articles)} 篇文章")
        
        for article in articles[:10]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                
                detail_url = urljoin(url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                
                date_elem = article.find('time') or article.find(class_=re.compile('date'))
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                if date_str and self.is_in_date_window(date_str, window_start, window_end):
                    content = self._fetch_detail(detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:600],
                            date=date_str,
                            url=detail_url,
                            source="Unity"
                        ))
                        
            except Exception as e:
                continue
        
        return items
    
    def fetch_criteo(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Criteo - 使用日历控件"""
        items = []
        url = COMPETITOR_SOURCES["Criteo"]["url"]
        
        print("  [Playwright] 抓取 Criteo...")
        
        if not self._init_browser():
            return items
        
        page = self.context.new_page()
        try:
            print(f"    访问 {url}...")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(8000)  # 等待日历控件加载
            
            # 查找所有可点击的日期按钮
            date_buttons = page.query_selector_all('button.wd_wai_dateButton:not([disabled])')
            print(f"    找到 {len(date_buttons)} 个可点击日期")
            
            for i, button in enumerate(date_buttons[:15]):  # 处理前15个日期
                try:
                    # 获取日期文本
                    date_text = button.inner_text().strip()
                    if not date_text.isdigit():
                        continue
                    
                    day = int(date_text)
                    now = datetime.now()
                    date_str = f"{now.year}-{now.month:02d}-{day:02d}"
                    
                    # 检查日期是否在窗口内
                    if not self.is_in_date_window(date_str, window_start, window_end):
                        continue
                    
                    print(f"    [{i+1}] 处理日期: {date_str}")
                    
                    # 先滚动到按钮可见
                    button.scroll_into_view_if_needed()
                    page.wait_for_timeout(500)
                    
                    # 使用 JavaScript 点击，更稳定
                    button.evaluate('el => el.click()')
                    page.wait_for_timeout(3000)  # 等待新闻加载
                    
                    # 获取显示的新闻
                    html = page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 查找新闻链接 - 更宽松的选择器
                    news_links = soup.find_all('a', href=re.compile(r'202[0-9]'))
                    print(f"      找到 {len(news_links)} 个链接")
                    
                    for link in news_links[:3]:
                        title = self.clean_text(link.get_text())
                        if not title or len(title) < 10 or 'photo' in title.lower():
                            continue
                        
                        href = link.get('href', '')
                        if not href.startswith('http'):
                            detail_url = urljoin(url, href)
                        else:
                            detail_url = href
                        
                        print(f"      找到新闻: {title[:50]}...")
                        
                        # 获取详情内容
                        content = self._fetch_detail(detail_url)
                        if content:
                            items.append(ContentItem(
                                title=title,
                                summary=content[:600],
                                date=date_str,
                                url=detail_url,
                                source="Criteo"
                            ))
                            print(f"        ✓ 已添加")
                            
                except Exception as e:
                    print(f"    处理日期出错: {e}")
                    continue
                    
        except Exception as e:
            print(f"    ✗ Playwright 错误: {e}")
        finally:
            page.close()
        
        print(f"    Criteo 总计: {len(items)} 条")
        return items
    
    def fetch_taboola(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Taboola"""
        items = []
        url = COMPETITOR_SOURCES["Taboola"]["url"]
        
        print("  [Playwright] 抓取 Taboola...")
        html = self.fetch_page(url, wait_for="article, .post")
        if not html:
            return items
        
        soup = BeautifulSoup(html, 'html.parser')
        articles = soup.find_all('article') or soup.select('.post, .entry')
        
        print(f"    找到 {len(articles)} 篇文章")
        
        for article in articles[:10]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                
                detail_url = urljoin(url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                
                date_elem = article.find('time') or article.find(class_=re.compile('date'))
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                if date_str and self.is_in_date_window(date_str, window_start, window_end):
                    content = self._fetch_detail(detail_url)
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
    
    def fetch_teads(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Teads"""
        items = []
        url = COMPETITOR_SOURCES["Teads"]["url"]
        
        print("  [Playwright] 抓取 Teads...")
        html = self.fetch_page(url, wait_for="article, .press-item")
        if not html:
            return items
        
        soup = BeautifulSoup(html, 'html.parser')
        articles = soup.find_all('article') or soup.select('.press-item')
        
        print(f"    找到 {len(articles)} 篇文章")
        
        for article in articles[:10]:
            try:
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                
                detail_url = urljoin(url, link_elem['href'])
                title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                title = self.clean_text(title_elem.get_text())
                
                date_elem = article.find('time') or article.find(class_=re.compile('date'))
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text()) or self.parse_date(date_elem.get('datetime', ''))
                
                if date_str and self.is_in_date_window(date_str, window_start, window_end):
                    content = self._fetch_detail(detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:600],
                            date=date_str,
                            url=detail_url,
                            source="Teads"
                        ))
                        
            except Exception as e:
                continue
        
        return items
    
    def fetch_zeta(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Zeta Global"""
        items = []
        url = COMPETITOR_SOURCES["Zeta Global"]["url"]
        
        print("  [Playwright] 抓取 Zeta Global...")
        html = self.fetch_page(url, wait_for="table, .item")
        if not html:
            return items
        
        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.find_all('tr') or soup.select('.item')
        
        print(f"    找到 {len(rows)} 行")
        
        for row in rows[:15]:
            try:
                link_elem = row.find('a', href=True)
                if not link_elem:
                    continue
                
                detail_url = urljoin(url, link_elem['href'])
                title = self.clean_text(link_elem.get_text())
                
                date_elem = row.find('td', class_=re.compile('date')) or row.find('time')
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text())
                
                if date_str and self.is_in_date_window(date_str, window_start, window_end):
                    content = self._fetch_detail(detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title,
                            summary=content[:600],
                            date=date_str,
                            url=detail_url,
                            source="Zeta Global"
                        ))
                        
            except Exception as e:
                continue
        
        return items
    
    def _fetch_detail(self, url: str) -> str:
        """获取详情页内容"""
        html = self.fetch_page(url, timeout=20000)
        if not html:
            return ""
        
        soup = BeautifulSoup(html, 'html.parser')
        
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        
        content_selectors = [
            'article',
            '.content',
            '.main-content',
            '.post-content',
            'main',
        ]
        
        for selector in content_selectors:
            elem = soup.select_one(selector)
            if elem:
                return self.clean_text(elem.get_text(separator=' ', strip=True))
        
        return ""
