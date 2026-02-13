#!/usr/bin/env python3
"""
Stealth Playwright 抓取器 - 模拟真人浏览器绕过反爬虫检测
"""
import re
import time
import random
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


class StealthFetcher:
    """使用 stealth 技术的抓取器"""
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.pw = None
    
    def _init_browser(self):
        """初始化 stealth 浏览器"""
        if self.browser is None:
            try:
                from playwright.sync_api import sync_playwright
                self.pw = sync_playwright().start()
                
                self.browser = self.pw.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-extensions',
                        '--disable-background-networking',
                        '--disable-background-timer-throttling',
                        '--disable-breakpad',
                        '--disable-features=TranslateUI',
                        '--disable-ipc-flooding-protection',
                        '--disable-renderer-backgrounding',
                        '--enable-features=NetworkService',
                        '--force-color-profile=srgb',
                        '--metrics-recording-only',
                        '--mute-audio',
                    ]
                )
                
                self.context = self.browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    locale='en-US',
                    timezone_id='America/New_York',
                )
                
                # 注入 stealth 脚本
                self.context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    window.chrome = {runtime: {}, loadTimes: function() {}, csi: function() {}, app: {}};
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                """)
                
            except Exception as e:
                print(f"  [!] Stealth 初始化失败: {e}")
                return False
        return True
    
    def _random_delay(self, min_ms=1000, max_ms=3000):
        time.sleep(random.uniform(min_ms, max_ms) / 1000)
    
    def fetch_page(self, url: str, wait_for: str = None, timeout: int = 60000) -> str:
        if not self._init_browser():
            return None
        
        page = self.context.new_page()
        try:
            print(f"    [Stealth] 访问: {url[:50]}...")
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            self._random_delay(3000, 5000)
            
            if wait_for:
                try:
                    page.wait_for_selector(wait_for, timeout=10000)
                except:
                    pass
            
            html = page.content()
            page.close()
            return html
        except Exception as e:
            print(f"    [Stealth] 错误: {e}")
            page.close()
            return None
    
    def close(self):
        if self.browser:
            self.browser.close()
        if self.pw:
            self.pw.stop()
    
    def parse_date(self, date_str: str) -> Optional[str]:
        if not date_str:
            return None
        date_str = date_str.strip()
        patterns = [
            (r"(\d{4})-(\d{1,2})-(\d{1,2})", lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"),
            (r"(\d{1,2})/(\d{1,2})/(\d{4})", lambda m: f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"),
            (r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})", 
             lambda m: f"{m.group(3)}-{self._month_abbr_to_num(m.group(2)):02d}-{int(m.group(1)):02d}"),
            (r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2}),?\s+(\d{4})", 
             lambda m: f"{m.group(3)}-{self._month_abbr_to_num(m.group(1)):02d}-{int(m.group(2)):02d}"),
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
        months = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                  'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
        return months.get(month_abbr.lower()[:3], 1)
    
    def is_in_date_window(self, date_str: str, window_start: datetime, window_end: datetime) -> bool:
        if not date_str:
            return False
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return window_start.date() <= date_obj.date() <= window_end.date()
        except:
            return False
    
    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text).strip()
    
    def _fetch_detail(self, url: str) -> str:
        html = self.fetch_page(url, timeout=30000)
        if not html:
            return ""
        soup = BeautifulSoup(html, 'html.parser')
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        for selector in ['article', '.content', '.main-content', 'main']:
            elem = soup.select_one(selector)
            if elem:
                return self.clean_text(elem.get_text(separator=' ', strip=True))
        return ""
    
    def fetch_criteo(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Criteo - 使用官网新闻列表"""
        items = []
        url = "https://www.criteo.com/news/"
        print("  [Stealth] 抓取 Criteo...")
        
        html = self.fetch_page(url, timeout=60000)
        if not html:
            return items
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 查找新闻链接 - 基于实际页面结构
        news_links = soup.find_all('a', href=re.compile(r'/news/press-releases/\d{4}/\d{2}/'))
        print(f"    找到 {len(news_links)} 个新闻链接")
        
        processed_urls = set()
        
        for link in news_links[:10]:
            try:
                href = link.get('href', '')
                print(f"    处理链接: {href[:60]}...")
                
                if not href:
                    print(f"      - 空href")
                    continue
                
                detail_url = urljoin(url, href)
                if detail_url in processed_urls:
                    print(f"      - 重复URL")
                    continue
                processed_urls.add(detail_url)
                
                # 获取标题 - 从链接文本或URL slug
                title = self.clean_text(link.get_text())
                print(f"      原标题: '{title[:50]}...'")
                
                # 如果标题为空或太短，从URL slug生成
                if not title or len(title) < 10:
                    # 从URL路径提取标题 /criteo-introduces-.../ -> Criteo Introduces ...
                    slug_match = re.search(r'/([^/]+)/?$', href)
                    if slug_match:
                        slug = slug_match.group(1)
                        # 替换连字符为空格，首字母大写
                        title = slug.replace('-', ' ').title()
                        print(f"      从URL生成标题: {title[:50]}...")
                
                # 如果标题是 "Read More" 或类似，需要从详情页获取真实标题
                is_read_more = 'read more' in title.lower() or len(title) < 20
                
                # 从URL提取日期 /2026/02/09/ -> 2026-02-09
                date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', href)
                if date_match:
                    date_str = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
                else:
                    date_str = datetime.now().strftime('%Y-%m-%d')
                
                print(f"      日期: {date_str}")
                
                if not self.is_in_date_window(date_str, window_start, window_end):
                    print(f"      - 日期不在窗口")
                    continue
                
                # 简化：不使用 _fetch_detail，直接用标题作为内容
                # Criteo 网站有反爬，详情页获取经常失败
                
                # 过滤非主体新闻
                if self._is_not_main_subject(title, 'Criteo'):
                    print(f"      - 跳过(非主体): {title[:50]}...")
                    continue
                
                # 使用 Google News 搜索标题找摘要
                summary = self._fetch_google_search_summary(title, "Criteo")
                if not summary:
                    summary = f"Criteo: {title}"
                
                print(f"      ✓ 成功: {title[:50]}...")
                items.append(ContentItem(
                    title=title, summary=summary[:600], date=date_str,
                    url=detail_url, source="Criteo"
                ))
                
                # 限制最多3条
                if len(items) >= 3:
                    break
                    
            except Exception as e:
                continue
        
        print(f"    Criteo: {len(items)} 条")
        return items
    
    def _fetch_google_search_summary(self, title: str, company: str) -> str:
        """使用 Google 搜索标题获取摘要 - 通过搜索结果页面"""
        try:
            # 提取标题前几个关键词搜索
            keywords = ' '.join(title.split()[:5])
            query = f"{company} {keywords}"
            
            # 使用 Google 搜索页面
            search_url = f"https://www.google.com/search?q={query}&num=3"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            response = self.session.get(search_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找搜索结果的摘要文本
            # 尝试多种可能的选择器
            for selector in ['.VwiC3b', '.s3v94d', '.yXK7lf', '[data-sokoban-container]']:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    text = desc_elem.get_text(strip=True)
                    if len(text) > 50:
                        return text[:500]
            
            # 备选：找任何包含关键词的段落
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                text = p.get_text(strip=True)
                if company.lower() in text.lower() and len(text) > 50:
                    return text[:500]
            
            return ""
        except Exception as e:
            return ""
    
    def fetch_teads(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Teads - 从 blog 页面获取标题，Google 搜索找摘要"""
        print("  [Stealth] 抓取 Teads...")
        
        items = []
        url = "https://www.teads.com/blog/"
        
        try:
            html = self.fetch_page(url, timeout=60000)
            if not html:
                return items
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找 blog 文章链接 (格式: /blog/title-slug/1234/)
            news_links = soup.find_all('a', href=re.compile(r'/blog/[^/]+/\d+'))
            print(f"    找到 {len(news_links)} 个 blog 链接")
            
            processed_urls = set()
            
            for link in news_links[:15]:
                try:
                    href = link.get('href', '')
                    if not href:
                        continue
                    
                    detail_url = urljoin(url, href)
                    if detail_url in processed_urls:
                        continue
                    processed_urls.add(detail_url)
                    
                    # 从 URL slug 提取标题
                    match = re.search(r'/blog/([^/]+)/\d+', href)
                    if not match:
                        continue
                    
                    slug = match.group(1)
                    title = slug.replace('-', ' ').title()
                    
                    # 过滤太短或太长的标题
                    if len(title) < 10 or len(title) > 200:
                        continue
                    
                    # Teads blog 没有日期，使用当前日期
                    date_str = datetime.now().strftime('%Y-%m-%d')
                    
                    # 过滤非主体新闻
                    if self._is_not_main_subject(title, 'Teads'):
                        continue
                    
                    # 用 Google 搜索标题找摘要
                    print(f"    ✓ {title[:50]}...")
                    summary = self._fetch_google_search_summary(title, "Teads")
                    if not summary:
                        summary = f"Teads: {title}"
                    
                    items.append(ContentItem(
                        title=title, summary=summary[:600], date=date_str,
                        url=detail_url, source="Teads"
                    ))
                    
                    # 限制最多3条
                    if len(items) >= 3:
                        break
                        
                except Exception as e:
                    continue
            
        except Exception as e:
            print(f"    ✗ Teads 错误: {e}")
        
        print(f"    Teads: {len(items)} 条")
        return items
    
    def fetch_applovin(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 AppLovin - 投资者网站
        日期在 evergreen-item-date-time / evergreen-news-date 类中，格式 "February 11, 2026"
        """
        items = []
        url = COMPETITOR_SOURCES["AppLovin"]["url"]
        print("  [Stealth] 抓取 AppLovin...")
        
        if not self._init_browser():
            return items
        
        page = self.context.new_page()
        processed_urls = set()
        
        try:
            # 使用较长超时和 load 等待，确保 Cloudflare 验证完成
            print("    访问投资者页面...")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找日期元素
            date_divs = soup.find_all('div', class_=re.compile('evergreen-item-date-time|evergreen-news-date'))
            print(f"    找到 {len(date_divs)} 个日期元素")
            
            for date_div in date_divs[:10]:
                try:
                    date_text = date_div.get_text(strip=True)
                    
                    # 解析日期 "February 11, 2026" -> "2026-02-11"
                    match = re.match(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})', date_text, re.IGNORECASE)
                    if not match:
                        continue
                    
                    months = {'january': '01', 'february': '02', 'march': '03', 'april': '04', 'may': '05', 'june': '06',
                             'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12'}
                    month_num = months.get(match.group(1).lower(), '01')
                    date_str = f"{match.group(3)}-{month_num}-{match.group(2).zfill(2)}"
                    
                    # 查找对应的新闻标题和链接
                    parent = date_div.find_parent()
                    if not parent:
                        continue
                    
                    link_elem = parent.find('a', href=True)
                    if not link_elem:
                        continue
                    
                    href = link_elem.get('href', '')
                    if not href or '/news/' not in href or '/events-and-presentations/' in href:
                        continue
                    
                    detail_url = urljoin(url, href)
                    
                    if detail_url in processed_urls:
                        continue
                    processed_urls.add(detail_url)
                    
                    title = self.clean_text(link_elem.get_text())
                    if not title or len(title) < 10:
                        continue
                    
                    print(f"    [{len(items)+1}] {title[:50]}... | 日期: {date_str}", end="")
                    
                    if not self.is_in_date_window(date_str, window_start, window_end):
                        print(f" - 不在时间窗口")
                        continue
                    
                    # 获取详情
                    content = self._fetch_detail(detail_url)
                    if content:
                        items.append(ContentItem(
                            title=title, summary=content[:600], date=date_str,
                            url=detail_url, source="AppLovin"
                        ))
                        print(f" ✓ 已添加")
                    else:
                        print(f" ✗ 无内容")
                    
                    # 限制最多3条
                    if len(items) >= 3:
                        break
                    
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"    ✗ AppLovin 错误: {e}")
        finally:
            page.close()
        
        print(f"    AppLovin: {len(items)} 条")
        return items
    
    def _is_unity_ad_related(self, title: str) -> bool:
        """检查 Unity 新闻是否与广告相关"""
        title_lower = title.lower()
        
        # 广告相关关键词
        ad_keywords = [
            'ad', 'ads', 'advertising', 'advertisement',
            'monetization', 'monetize', 'monetisation', 'monetise',
            'programmatic', 'dsp', 'ssp', 'exchange',
            'revenue', 'campaign', 'targeting', 'attribution',
            'banner', 'interstitial', 'rewarded',
            'mediation', 'bidding', 'ironsource',
            'user acquisition', 'ua', 'app store', 'aso',
            'vector', 'grow', 'levelplay', 'supersonic',
        ]
        
        # 排除游戏引擎/开发相关的新闻
        exclude_keywords = [
            'game engine', 'render', 'graphics', 'shader',
            'unity 6', 'unity 5', 'unity 3d', 'unity learn',
            'tutorial', 'asset store', 'indie game',
            'game development', 'unity forum', 'megacity',
        ]
        
        # 检查是否包含广告关键词
        is_ad = any(kw in title_lower for kw in ad_keywords)
        
        # 检查是否包含排除关键词
        is_excluded = any(kw in title_lower for kw in exclude_keywords)
        
        return is_ad and not is_excluded

    def fetch_unity(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Unity - 官网有反爬，使用 Google News RSS"""
        print("  [Stealth] 抓取 Unity...")
        print("    注意: 原网站有访问限制，使用 Google News RSS")
        
        items = self._fetch_google_news_rss(
            "Unity Technologies advertising monetization", 
            window_start, 
            window_end, 
            "Unity"
        )
        
        # 限制最多3条
        items = items[:3]
        
        print(f"    找到 {len(items)} 条在时间窗口内")
        for item in items[:5]:
            print(f"    ✓ {item.title[:50]}... ({item.date})")
        
        print(f"    Unity: {len(items)} 条")
        return items
    
    def fetch_zeta(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Zeta Global - 使用官网 Investor News"""
        items = []
        url = "https://investors.zetaglobal.com/news/default.aspx"
        print("  [Stealth] 抓取 Zeta Global...")
        
        if not self._init_browser():
            return items
        
        page = self.context.new_page()
        processed_urls = set()
        
        try:
            print("    访问 Zeta Global 投资者页面...")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找新闻项 - 使用多种可能的选择器
            news_items = soup.find_all('div', class_=re.compile('news|press|item|release'))
            print(f"    找到 {len(news_items)} 个新闻项")
            
            for item_elem in news_items[:10]:
                try:
                    # 查找标题和链接
                    link_elem = item_elem.find('a', href=True)
                    if not link_elem:
                        continue
                    
                    title = self.clean_text(link_elem.get_text())
                    if not title or len(title) < 10:
                        continue
                    
                    # 过滤非主体新闻
                    if self._is_not_main_subject(title, 'Zeta'):
                        print(f"    - 跳过(非主体): {title[:50]}...")
                        continue
                    
                    href = link_elem.get('href', '')
                    if not href:
                        continue
                    
                    detail_url = urljoin(url, href)
                    if detail_url in processed_urls:
                        continue
                    processed_urls.add(detail_url)
                    
                    # 尝试从元素中提取日期
                    date_str = ""
                    date_elem = item_elem.find(class_=re.compile('date|time'))
                    if date_elem:
                        date_str = self.parse_date(date_elem.get_text()) or ""
                    
                    if not date_str:
                        continue
                    
                    if not self.is_in_date_window(date_str, window_start, window_end):
                        continue
                    
                    # 从元素中提取摘要文本
                    content = ""
                    desc_elem = item_elem.find(class_=re.compile('desc|summary|content'))
                    if desc_elem:
                        content = self.clean_text(desc_elem.get_text())
                    if not content:
                        content = title
                    
                    print(f"    ✓ {title[:50]}... ({date_str})")
                    
                    items.append(ContentItem(
                        title=title,
                        summary=content[:600],
                        date=date_str,
                        url=detail_url,
                        source="Zeta Global"
                    ))
                    
                    # 限制最多3条
                    if len(items) >= 3:
                        break
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"    ✗ Zeta Global 错误: {e}")
        finally:
            page.close()
        
        print(f"    Zeta Global: {len(items)} 条")
        return items
    
    def fetch_bigo_ads(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 BIGO Ads - 从 blog 列表页获取链接，进入详情页提取日期
        日期格式: "2026-02-03" (在 span 标签中)
        """
        items = []
        url = COMPETITOR_SOURCES["BIGO Ads"]["url"]
        print("  [Stealth] 抓取 BIGO Ads...")
        
        if not self._init_browser():
            return items
        
        page = self.context.new_page()
        processed_urls = set()
        
        try:
            # 访问列表页
            page.goto(url, wait_until="load", timeout=120000)
            page.wait_for_timeout(5000)
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找博客链接
            blog_links = soup.find_all('a', href=re.compile('/resources/blog/\\d+'))
            print(f"    找到 {len(blog_links)} 个博客链接")
            
            # 去重并只取前3个
            seen_urls = set()
            unique_links = []
            for link in blog_links:
                href = link.get('href', '')
                if href and href not in seen_urls:
                    seen_urls.add(href)
                    unique_links.append(href)
            
            print(f"    去重后: {len(unique_links)} 个，检查前3个")
            
            for i, href in enumerate(unique_links[:3]):
                try:
                    detail_url = urljoin(url, href)
                    
                    # 去重检查
                    if detail_url in processed_urls:
                        continue
                    processed_urls.add(detail_url)
                    
                    print(f"\n    [{i+1}] 访问: {href}")
                    
                    # 进入详情页
                    detail_page = self.context.new_page()
                    try:
                        detail_page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
                        detail_page.wait_for_timeout(3000)
                        
                        detail_html = detail_page.content()
                        detail_soup = BeautifulSoup(detail_html, 'html.parser')
                        
                        # 获取标题
                        title = ""
                        h1 = detail_soup.find('h1')
                        if h1:
                            title = self.clean_text(h1.get_text())
                        else:
                            title_elem = detail_soup.find('title')
                            if title_elem:
                                title = title_elem.get_text(strip=True).replace(' - BIGO Ads', '')
                        
                        if not title:
                            detail_page.close()
                            continue
                        
                        # 获取日期 - 查找 YYYY-MM-DD 格式
                        date_str = ""
                        for elem in detail_soup.find_all(['span', 'time', 'div']):
                            text = elem.get_text(strip=True)
                            match = re.match(r'(\d{4})-(\d{2})-(\d{2})', text)
                            if match:
                                date_str = text
                                break
                        
                        if not date_str:
                            detail_page.close()
                            continue
                        
                        print(f"        标题: {title[:50]}...")
                        print(f"        日期: {date_str}", end="")
                        
                        # 检查日期窗口
                        if not self.is_in_date_window(date_str, window_start, window_end):
                            print(f" - 不在窗口")
                            detail_page.close()
                            continue
                        
                        print(f" ✅ 在窗口内")
                        
                        # 获取内容
                        content = ""
                        for selector in ['article', '.content', 'main', '.blog-content']:
                            elem = detail_soup.select_one(selector)
                            if elem:
                                text = elem.get_text(separator=' ', strip=True)
                                if len(text) > 200:
                                    content = self.clean_text(text)
                                    break
                        
                        if not content:
                            for script in detail_soup(["script", "style", "nav", "header"]):
                                script.decompose()
                            body = detail_soup.find('body')
                            if body:
                                content = self.clean_text(body.get_text(separator=' ', strip=True))
                        
                        if content:
                            items.append(ContentItem(
                                title=title,
                                summary=content[:600],
                                date=date_str,
                                url=detail_url,
                                source="BIGO Ads"
                            ))
                            print(f"        ✓ 已添加")
                        else:
                            print(f"        ✗ 无法提取内容")
                        
                        detail_page.close()
                        
                    except Exception as e:
                        print(f"        ✗ 详情页错误: {e}")
                        try:
                            detail_page.close()
                        except:
                            pass
                        continue
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"    ✗ BIGO Ads 错误: {e}")
        finally:
            page.close()
        
        print(f"\n    BIGO Ads: {len(items)} 条")
        return items
    
    def fetch_moloco(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Moloco - 从 newsroom 页面获取 press-releases 链接
        日期在详情页 time 标签中，格式 "January 21, 2026"
        """
        items = []
        url = COMPETITOR_SOURCES["Moloco"]["url"]
        print("  [Stealth] 抓取 Moloco...")
        
        if not self._init_browser():
            return items
        
        page = self.context.new_page()
        processed_urls = set()
        
        try:
            page.goto(url, wait_until="load", timeout=120000)
            self._random_delay(5000, 8000)
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找所有 press-releases 链接
            all_links = soup.find_all('a', href=True)
            press_links = [l for l in all_links if '/press-releases/' in l.get('href', '')]
            
            # 去重
            seen_urls = set()
            unique_links = []
            for link in press_links:
                href = link.get('href', '')
                if href and href not in seen_urls:
                    seen_urls.add(href)
                    unique_links.append(link)
            
            print(f"    找到 {len(unique_links)} 个 press-releases 链接")
            
            for link in unique_links[:10]:
                try:
                    href = link.get('href', '')
                    detail_url = urljoin(url, href)
                    
                    # 去重检查
                    if detail_url in processed_urls:
                        continue
                    processed_urls.add(detail_url)
                    
                    # 进入详情页获取标题和日期
                    detail_page = self.context.new_page()
                    try:
                        detail_page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
                        detail_page.wait_for_timeout(3000)
                        
                        detail_html = detail_page.content()
                        detail_soup = BeautifulSoup(detail_html, 'html.parser')
                        
                        # 获取标题
                        title = ""
                        for selector in ['h1', 'h2', '.title', '[class*="title"]']:
                            elem = detail_soup.select_one(selector)
                            if elem:
                                title = self.clean_text(elem.get_text())
                                if len(title) > 10:
                                    break
                        
                        if not title:
                            detail_page.close()
                            continue
                        
                        # 获取日期
                        date_str = ""
                        time_elem = detail_soup.find('time')
                        if time_elem:
                            datetime_attr = time_elem.get('datetime', '')
                            time_text = time_elem.get_text(strip=True)
                            
                            # 尝试标准格式
                            match = re.search(r'(\d{4})-(\d{2})-(\d{2})', datetime_attr)
                            if match:
                                date_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                            else:
                                # 尝试文本格式
                                match = re.match(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})', time_text, re.IGNORECASE)
                                if match:
                                    months = {'january': '01', 'february': '02', 'march': '03', 'april': '04', 'may': '05', 'june': '06',
                                             'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12'}
                                    month_num = months.get(match.group(1).lower(), '01')
                                    date_str = f"{match.group(3)}-{month_num}-{match.group(2).zfill(2)}"
                        
                        # 备选：从 body 文本查找
                        if not date_str:
                            body_text = detail_soup.get_text()[:3000]
                            match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})', body_text, re.IGNORECASE)
                            if match:
                                months = {'january': '01', 'february': '02', 'march': '03', 'april': '04', 'may': '05', 'june': '06',
                                         'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12'}
                                month_num = months.get(match.group(1).lower(), '01')
                                date_str = f"{match.group(3)}-{month_num}-{match.group(2).zfill(2)}"
                        
                        # 如果无法提取日期，使用当前日期
                        if not date_str:
                            date_str = datetime.now().strftime('%Y-%m-%d')
                        
                        print(f"    [{len(items)+1}] {title[:50]}... | 日期: {date_str}", end="")
                        
                        # 检查日期窗口
                        if not self.is_in_date_window(date_str, window_start, window_end):
                            print(f" - 不在窗口")
                            detail_page.close()
                            continue
                        
                        # 获取内容
                        content = ""
                        for selector in ['.content', 'article', '.post-content', '.press-content', 'main']:
                            elem = detail_soup.select_one(selector)
                            if elem:
                                text = elem.get_text(separator=' ', strip=True)
                                if len(text) > 200:
                                    content = self.clean_text(text)
                                    break
                        
                        if not content:
                            # 备选
                            for script in detail_soup(["script", "style", "nav", "header"]):
                                script.decompose()
                            body = detail_soup.find('body')
                            if body:
                                content = self.clean_text(body.get_text(separator=' ', strip=True))
                        
                        if content:
                            items.append(ContentItem(
                                title=title,
                                summary=content[:600],
                                date=date_str,
                                url=detail_url,
                                source="Moloco"
                            ))
                            print(f" ✓ 已添加")
                        else:
                            print(f" ✗ 无内容")
                        
                        detail_page.close()
                        
                    except Exception as e:
                        print(f" ✗ 详情页错误: {e}")
                        try:
                            detail_page.close()
                        except:
                            pass
                        continue
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"    ✗ Moloco 错误: {e}")
        finally:
            page.close()
        
        print(f"    Moloco: {len(items)} 条")
        return items
    
    def fetch_mobvista(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Mobvista - 投资者关系页面
        日期在 announce-item-time 类中，格式 "February 6, 2026"
        链接通常是外部 PDF (hkexnews.hk)
        """
        items = []
        url = COMPETITOR_SOURCES["mobvista"]["url"]
        print("  [Stealth] 抓取 Mobvista...")
        
        if not self._init_browser():
            return items
        
        page = self.context.new_page()
        
        try:
            page.goto(url, wait_until="load", timeout=120000)
            self._random_delay(5000, 8000)
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找公告项
            announce_items = soup.select('.announce-item')
            print(f"    找到 {len(announce_items)} 个公告")
            
            for item in announce_items[:10]:
                try:
                    # 获取标题
                    title_elem = item.find('h2', class_='announce-item-title')
                    title = self.clean_text(title_elem.get_text()) if title_elem else ""
                    if not title:
                        continue
                    
                    # 获取日期
                    time_elem = item.find('p', class_='announce-item-time')
                    date_text = time_elem.get_text(strip=True) if time_elem else ""
                    
                    # 解析日期 "February 6, 2026" -> "2026-02-06"
                    match = re.match(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})', date_text, re.IGNORECASE)
                    if not match:
                        continue
                    
                    months = {'january': '01', 'february': '02', 'march': '03', 'april': '04', 'may': '05', 'june': '06',
                             'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12'}
                    month_num = months.get(match.group(1).lower(), '01')
                    date_str = f"{match.group(3)}-{month_num}-{match.group(2).zfill(2)}"
                    
                    # 获取链接
                    link_elem = item.find('a', href=True)
                    detail_url = link_elem.get('href', '') if link_elem else ""
                    if not detail_url:
                        continue
                    
                    # 如果是相对链接，补全
                    if detail_url.startswith('/'):
                        detail_url = urljoin(url, detail_url)
                    
                    print(f"    [{len(items)+1}] {title[:50]}... | 日期: {date_str}", end="")
                    
                    # 检查日期窗口
                    if not self.is_in_date_window(date_str, window_start, window_end):
                        print(f" - 不在窗口")
                        continue
                    
                    # 对于外部 PDF 链接，使用标题作为内容摘要
                    # 也可以尝试获取页面上的描述文本
                    desc_elem = item.find('p', class_=re.compile('desc|summary'))
                    if desc_elem:
                        content = self.clean_text(desc_elem.get_text())
                    else:
                        # 使用标题生成摘要
                        content = f"Mobvista announcement: {title}"
                    
                    items.append(ContentItem(
                        title=title,
                        summary=content[:600],
                        date=date_str,
                        url=detail_url,
                        source="Mobvista"
                    ))
                    print(f" ✓ 已添加")
                    
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"    ✗ Mobvista 错误: {e}")
        finally:
            page.close()
        
        print(f"    Mobvista: {len(items)} 条")
        return items
    
    def fetch_viant(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Viant - 官网受限，使用 Google News RSS 作为备选"""
        print("  [Stealth] 抓取 Viant Technology...")
        print("    注意: 原网站有访问限制，使用 Google News RSS")
        
        items = self._fetch_google_news_rss(
            "Viant Technology news press release", 
            window_start, 
            window_end, 
            "Viant Technology"
        )
        
        # 限制最多3条
        items = items[:3]
        
        print(f"    找到 {len(items)} 条在时间窗口内")
        for item in items[:5]:
            print(f"    ✓ {item.title[:50]}... ({item.date})")
        
        print(f"    Viant Technology: {len(items)} 条")
        return items
    
    def _normalize_title_for_similarity(self, text: str) -> str:
        """标准化标题用于相似度比较"""
        text = text.lower()
        
        # 扩展同义词替换
        synonyms = {
            # 公司/品牌缩写
            'nyt': 'new york times',
            'goog': 'google',
            'fb': 'facebook',
            'meta': 'facebook',
            # 常见缩写
            'q1': 'quarter 1',
            'q2': 'quarter 2', 
            'q3': 'quarter 3',
            'q4': 'quarter 4',
            'fy': 'fiscal year',
            'yoy': 'year over year',
            'y/y': 'year over year',
            'mom': 'month over month',
            'm/m': 'month over month',
            # 货币/数字
            '1b': '1 billion',
            '1m': '1 million',
            '1k': '1000',
            '$1b': '1 billion dollars',
            '$1m': '1 million dollars',
            # Unity 相关
            'u': 'unity',
            'mgNI': 'magnite',
        }
        
        for abbr, full in synonyms.items():
            text = re.sub(r'\b' + re.escape(abbr) + r'\b', full, text)
        
        # 去除标点
        text = re.sub(r'[^\w\s]', ' ', text)
        # 去除停用词
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'as', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
        words = [w for w in text.split() if w not in stopwords and len(w) > 2]
        
        return ' '.join(words)
    
    def _title_similarity(self, title1: str, title2: str) -> float:
        """计算两个标题的相似度 (0-1)"""
        if not title1 or not title2:
            return 0.0
        
        t1 = self._normalize_title_for_similarity(title1)
        t2 = self._normalize_title_for_similarity(title2)
        
        if not t1 or not t2:
            return 0.0
        
        # 如果标准化后包含关系，认为是相似的
        if t1 in t2 or t2 in t1:
            return 0.85
        
        # 计算词集相似度 (Jaccard)
        words1 = set(t1.split())
        words2 = set(t2.split())
        
        if not words1 or not words2:
            return 0.0
        
        # 如果核心词（前3个关键词）相同，认为是相似的
        core1 = set(list(words1)[:3])
        core2 = set(list(words2)[:3])
        if len(core1 & core2) >= 2:
            return 0.75
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        similarity = intersection / union if union > 0 else 0.0
        
        # 如果有很多共同关键词，提高相似度
        if intersection >= 4:
            similarity = max(similarity, 0.7)
        
        return similarity
    
    def _dedupe_items(self, items: List[ContentItem], similarity_threshold: float = 0.6) -> List[ContentItem]:
        """根据标题相似度去重"""
        if not items:
            return items
        
        # 按日期排序（新的优先）
        sorted_items = sorted(items, key=lambda x: x.date, reverse=True)
        
        unique_items = []
        
        for item in sorted_items:
            is_duplicate = False
            
            for existing in unique_items:
                similarity = self._title_similarity(item.title, existing.title)
                if similarity >= similarity_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_items.append(item)
        
        return unique_items

    def _fetch_google_news_rss(self, query: str, window_start: datetime, window_end: datetime, source_name: str, filter_fn=None) -> List[ContentItem]:
        """使用 Google News RSS 抓取新闻
        
        Args:
            query: 搜索关键词
            window_start: 开始日期
            window_end: 结束日期
            source_name: 来源名称
            filter_fn: 可选的过滤函数，接收标题返回 bool
        """
        items = []
        
        try:
            from urllib.parse import quote_plus
            import requests
            
            url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en&gl=US&ceid=US:en"
            print(f"    使用 Google News RSS...")
            
            resp = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            })
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, 'xml')
            
            for item_elem in soup.find_all('item'):
                try:
                    title = item_elem.title.get_text() if item_elem.title else ""
                    link = item_elem.link.get_text() if item_elem.link else ""
                    pub_date = item_elem.pubDate.get_text() if item_elem.pubDate else ""
                    
                    if not title or not link:
                        continue
                    
                    # 应用自定义过滤
                    if filter_fn and not filter_fn(title):
                        continue
                    
                    # 解析日期
                    date_str = None
                    if pub_date:
                        try:
                            dt = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %Z')
                            date_str = dt.strftime('%Y-%m-%d')
                        except:
                            # 尝试其他格式
                            date_match = re.search(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})', pub_date)
                            if date_match:
                                months = {'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
                                         'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'}
                                date_str = f"{date_match.group(3)}-{months.get(date_match.group(2).lower(), '01')}-{date_match.group(1).zfill(2)}"
                    
                    if not date_str:
                        date_str = window_end.strftime('%Y-%m-%d')
                    
                    # 检查日期窗口
                    if not self.is_in_date_window(date_str, window_start, window_end):
                        continue
                    
                    # 尝试获取详情内容（使用 Google News 摘要作为内容）
                    content = title  # 使用标题作为内容摘要
                    
                    items.append(ContentItem(
                        title=self.clean_text(title),
                        summary=content[:600],
                        date=date_str,
                        url=link,
                        source=source_name
                    ))
                    
                except Exception as e:
                    continue
            
            # 去重
            original_count = len(items)
            items = self._dedupe_items(items, similarity_threshold=0.6)
            removed_count = original_count - len(items)
            
            if removed_count > 0:
                print(f"    去重: 移除 {removed_count} 条重复新闻")
                    
        except Exception as e:
            print(f"    Google News RSS 错误: {e}")
        
        return items

    def fetch_pubmatic(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 PubMatic - 官网受限，使用 Google News RSS 作为备选"""
        print("  [Stealth] 抓取 PubMatic...")
        print("    注意: 原网站有访问限制，使用 Google News RSS")
        
        items = self._fetch_google_news_rss(
            "PubMatic news press release", 
            window_start, 
            window_end, 
            "PubMatic"
        )
        
        # 限制最多3条
        items = items[:3]
        
        print(f"    找到 {len(items)} 条在时间窗口内")
        for item in items[:5]:
            print(f"    ✓ {item.title[:50]}... ({item.date})")
        
        print(f"    PubMatic: {len(items)} 条")
        return items
    
    def fetch_magnite(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Magnite - 使用官网标题 + Google 搜索找全文"""
        print("  [Stealth] 抓取 Magnite...")
        
        items = []
        url = "https://investor.magnite.com/press-releases"
        
        html = self.fetch_page(url, timeout=60000)
        if not html:
            return items
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 查找新闻链接
        news_links = soup.find_all('a', href=re.compile(r'/press-releases/'))
        print(f"    找到 {len(news_links)} 个新闻链接")
        
        processed_urls = set()
        
        for link in news_links[:10]:
            try:
                href = link.get('href', '')
                if not href:
                    continue
                
                detail_url = urljoin(url, href)
                if detail_url in processed_urls:
                    continue
                processed_urls.add(detail_url)
                
                # 获取标题
                title = self.clean_text(link.get_text())
                if not title or len(title) < 10:
                    slug_match = re.search(r'/([^/]+)/?$', href)
                    if slug_match:
                        slug = slug_match.group(1)
                        title = slug.replace('-', ' ').title()
                
                # 从URL提取日期
                date_str = self._extract_date_from_url(detail_url)
                if not date_str:
                    date_str = datetime.now().strftime('%Y-%m-%d')
                
                if not self.is_in_date_window(date_str, window_start, window_end):
                    continue
                
                # 过滤非主体新闻
                if self._is_not_main_subject(title, 'Magnite'):
                    continue
                
                # 用 Google 搜索标题找摘要
                print(f"    ✓ {title[:50]}... ({date_str})")
                summary = self._fetch_google_search_summary(title, "Magnite")
                if not summary:
                    summary = f"Magnite: {title}"
                
                items.append(ContentItem(
                    title=title, summary=summary[:600], date=date_str,
                    url=detail_url, source="Magnite"
                ))
                
                # 限制最多3条
                if len(items) >= 3:
                    break
                    
            except Exception as e:
                continue
        
        print(f"    Magnite: {len(items)} 条")
        return items
    
    def fetch_taboola(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Taboola - 日期在详情页 time 标签中，格式非标准"""
        items = []
        url = COMPETITOR_SOURCES["Taboola"]["url"]
        print("  [Stealth] 抓取 Taboola...")
        
        if not self._init_browser():
            return items
        
        page = self.context.new_page()
        processed_urls = set()
        
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            self._random_delay(5000, 7000)
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找文章链接
            articles = soup.find_all('article')
            if not articles:
                articles = soup.select('.post, .entry, .blog-post')
            print(f"    找到 {len(articles)} 篇文章")
            
            for article in articles[:15]:
                try:
                    link = article.find('a', href=True)
                    if not link:
                        continue
                    
                    detail_url = urljoin(url, link['href'])
                    if not '/press-releases/' in detail_url:
                        continue
                    
                    # 去重
                    if detail_url in processed_urls:
                        continue
                    processed_urls.add(detail_url)
                    
                    title = self.clean_text(link.get_text())
                    if not title or len(title) < 10:
                        continue
                    
                    # 进入详情页获取日期
                    detail_page = self.context.new_page()
                    try:
                        detail_page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
                        self._random_delay(2000, 4000)
                        
                        detail_html = detail_page.content()
                        detail_soup = BeautifulSoup(detail_html, 'html.parser')
                        
                        # 提取日期 - Taboola 使用非标准格式
                        date_str = None
                        time_elem = detail_soup.find('time')
                        
                        if time_elem:
                            datetime_attr = time_elem.get('datetime', '')
                            time_text = time_elem.get_text(strip=True)
                            
                            # 尝试标准格式
                            match = re.search(r'(\d{4})-(\d{2})-(\d{2})', datetime_attr)
                            if match:
                                date_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                            # 尝试非标准格式 "2026-Feb-Thu"
                            elif re.match(r'\d{4}-[A-Za-z]{3}-[A-Za-z]{3}', datetime_attr):
                                match = re.match(r'(\d{4})-([A-Za-z]{3})', datetime_attr)
                                if match:
                                    months = {'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
                                             'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'}
                                    month_num = months.get(match.group(2).lower(), '01')
                                    day_match = re.search(r'(\d{1,2})', time_text)
                                    if day_match:
                                        date_str = f"{match.group(1)}-{month_num}-{day_match.group(1).zfill(2)}"
                            # 尝试文本格式 "Feb 05 2026"
                            elif not date_str:
                                match = re.match(r'([A-Za-z]{3})\s+(\d{1,2})\s+(\d{4})', time_text, re.IGNORECASE)
                                if match:
                                    months = {'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
                                             'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'}
                                    date_str = f"{match.group(3)}-{months.get(match.group(1).lower(), '01')}-{match.group(2).zfill(2)}"
                        
                        if not date_str:
                            detail_page.close()
                            continue
                        
                        if not self.is_in_date_window(date_str, window_start, window_end):
                            detail_page.close()
                            continue
                        
                        # 获取内容
                        content = ""
                        for selector in ['article', '.content', '.main-content', 'main', '.post-content', '.entry-content']:
                            elem = detail_soup.select_one(selector)
                            if elem:
                                text = elem.get_text(separator=' ', strip=True)
                                if len(text) > 200:
                                    content = self.clean_text(text)
                                    break
                        
                        if content:
                            items.append(ContentItem(
                                title=title,
                                summary=content[:600],
                                date=date_str,
                                url=detail_url,
                                source="Taboola"
                            ))
                            print(f"    ✓ {title[:40]}... ({date_str})")
                        
                        detail_page.close()
                        
                    except Exception as e:
                        try:
                            detail_page.close()
                        except:
                            pass
                        continue
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"    ✗ Taboola 错误: {e}")
        finally:
            page.close()
        
        print(f"    Taboola: {len(items)} 条")
        return items
    
    def fetch_ttd(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 TTD - 使用官网标题 + Google 搜索找全文"""
        print("  [Stealth] 抓取 TTD...")
        
        items = []
        url = "https://www.thetradedesk.com/press-room"
        
        html = self.fetch_page(url, timeout=60000)
        if not html:
            return items
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 查找新闻链接
        news_links = soup.find_all('a', href=re.compile(r'/press-room/'))
        print(f"    找到 {len(news_links)} 个新闻链接")
        
        processed_urls = set()
        
        for link in news_links[:10]:
            try:
                href = link.get('href', '')
                if not href:
                    continue
                
                detail_url = urljoin(url, href)
                if detail_url in processed_urls:
                    continue
                processed_urls.add(detail_url)
                
                # 获取标题
                title = self.clean_text(link.get_text())
                if not title or len(title) < 10:
                    slug_match = re.search(r'/([^/]+)/?$', href)
                    if slug_match:
                        slug = slug_match.group(1)
                        title = slug.replace('-', ' ').title()
                
                # 从URL提取日期 (TTD格式: /YYYY/DD/MM/)
                date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', href)
                if date_match:
                    year, day, month = date_match.group(1), date_match.group(2), date_match.group(3)
                    date_str = f"{year}-{month}-{day}"
                else:
                    date_str = datetime.now().strftime('%Y-%m-%d')
                
                if not self.is_in_date_window(date_str, window_start, window_end):
                    continue
                
                # 过滤非主体新闻
                if self._is_not_main_subject(title, 'TTD'):
                    continue
                
                # 用 Google 搜索标题找摘要
                print(f"    ✓ {title[:50]}... ({date_str})")
                summary = self._fetch_google_search_summary(title, "The Trade Desk")
                if not summary:
                    summary = f"The Trade Desk: {title}"
                
                items.append(ContentItem(
                    title=title, summary=summary[:600], date=date_str,
                    url=detail_url, source="TTD"
                ))
                
                # 限制最多3条
                if len(items) >= 3:
                    break
                    
            except Exception as e:
                continue
        
        print(f"    TTD: {len(items)} 条")
        return items
    
    def _is_not_main_subject(self, title: str, company: str) -> bool:
        """检查新闻是否不是关于公司本身的主体新闻"""
        title_lower = title.lower()
        
        # 如果是关于基金/机构买卖股票的新闻，通常不是主体新闻
        fund_keywords = [
            'retirement fund', 'pension fund', 'etf', 'mutual fund', 
            'holdings', 'acquires shares', 'buys shares', 'sells shares',
            'stake in', 'position in', 'portfolio', 'retirement system',
            'california', 'texas', 'florida', 'new york', 'teacher',
            'public employees', 'state board'
        ]
        
        # 如果标题以这些词开头或包含这些词+公司股票，可能是非主体新闻
        for keyword in fund_keywords:
            if keyword in title_lower:
                # 检查是否包含公司股票相关
                if any(stock in title_lower for stock in ['shares', 'stock', 'position', 'stake']):
                    return True
        
        return False
    
    def _extract_date_from_url(self, url: str) -> str:
        """从URL提取日期 - 支持多种格式"""
        # TTD 格式: /YYYY/DD/MM/ (日在前)
        match = re.search(r'/\d{4}/\d{2}/\d{2}/', url)
        if match:
            parts = match.group(0).strip('/').split('/')
            if len(parts) == 3:
                year, day, month = parts[0], parts[1], parts[2]
                return f"{year}-{month}-{day}"
        return ""
    
    def _extract_date_from_element(self, elem) -> str:
        """从元素中提取日期"""
        # 查找时间标签
        time_tag = elem.find('time')
        if time_tag:
            datetime_attr = time_tag.get('datetime', '')
            if datetime_attr:
                match = re.search(r'(\d{4})-(\d{2})-(\d{2})', datetime_attr)
                if match:
                    return match.group(0)
        
        # 查找日期类
        date_elem = elem.find(class_=re.compile('date|time'))
        if date_elem:
            return self.parse_date(date_elem.get_text()) or ""
        
        return ""
    
    def fetch_generic(self, company_key: str, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """通用抓取方法"""
        url = COMPETITOR_SOURCES[company_key]["url"]
        print(f"  [Stealth] 通用抓取 {company_key}...")
        
        html = self.fetch_page(url, timeout=60000)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        # 尝试多种选择器
        selectors = ['article', 'div.post', 'div.card', '.news-item', '.press-item', 'tr']
        for selector in selectors:
            elems = soup.select(selector)
            if elems:
                print(f"    使用选择器: {selector}, 找到 {len(elems)} 个")
                for elem in elems[:5]:
                    try:
                        link = elem.find('a', href=True)
                        if not link:
                            continue
                        title = self.clean_text(link.get_text())
                        if not title or len(title) < 10:
                            continue
                        
                        detail_url = urljoin(url, link['href'])
                        date_match = re.search(r'/(\d{4})[-/](\d{2})[-/](\d{2})/', detail_url)
                        if date_match:
                            date_str = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
                            if self.is_in_date_window(date_str, window_start, window_end):
                                content = self._fetch_detail(detail_url)
                                if content:
                                    items.append(ContentItem(
                                        title=title, summary=content[:600], date=date_str,
                                        url=detail_url, source=company_key
                                    ))
                    except:
                        continue
                break
        
        print(f"    {company_key}: {len(items)} 条")
        return items
