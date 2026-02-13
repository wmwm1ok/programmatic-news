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
        """抓取 Criteo - 增强版，处理 Cloudflare"""
        items = []
        url = COMPETITOR_SOURCES["Criteo"]["url"]
        print("  [Stealth] 抓取 Criteo...")
        
        if not self._init_browser():
            return items
        
        page = self.context.new_page()
        try:
            # 增加超时到 120 秒
            print("    访问主页建立会话...")
            page.goto("https://www.criteo.com", wait_until="domcontentloaded", timeout=120000)
            self._random_delay(3000, 5000)
            
            print("    访问投资者页面...")
            page.goto(url, wait_until="domcontentloaded", timeout=120000)
            self._random_delay(8000, 10000)  # 等待日历加载
            
            # 检查是否有 Cloudflare 挑战
            content = page.content()
            if 'cloudflare' in content.lower() or 'checking your browser' in content.lower():
                print("    ⚠️ 检测到 Cloudflare，等待挑战完成...")
                page.wait_for_timeout(15000)  # 额外等待
            
            date_buttons = page.query_selector_all('button.wd_wai_dateButton:not([disabled])')
            print(f"    找到 {len(date_buttons)} 个日期")
            
            if len(date_buttons) == 0:
                print("    ⚠️ 未找到日期按钮，可能页面结构已改变")
                # 截图调试
                try:
                    page.screenshot(path='/tmp/criteo_screenshot.png')
                    print("    已截图保存到 /tmp/criteo_screenshot.png")
                except:
                    pass
                return items
            
            for i, button in enumerate(date_buttons[:20]):  # 增加到20个日期
                try:
                    date_text = button.inner_text().strip()
                    if not date_text.isdigit():
                        continue
                    
                    day = int(date_text)
                    now = datetime.now()
                    date_str = f"{now.year}-{now.month:02d}-{day:02d}"
                    
                    if not self.is_in_date_window(date_str, window_start, window_end):
                        continue
                    
                    print(f"    [{i+1}] 处理日期: {date_str}")
                    
                    # 使用 JavaScript 点击
                    button.evaluate('el => { el.scrollIntoView({block: "center"}); el.click(); }')
                    self._random_delay(4000, 6000)
                    
                    html = page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 更宽松的新闻链接查找
                    news_links = soup.find_all('a', href=re.compile(r'/news/|/press/|/release/'))
                    print(f"      找到 {len(news_links)} 个新闻链接")
                    
                    for link in news_links[:3]:
                        title = self.clean_text(link.get_text())
                        if not title or len(title) < 10 or 'photo' in title.lower():
                            continue
                        
                        href = link.get('href', '')
                        detail_url = urljoin(url, href)
                        
                        content = self._fetch_detail(detail_url)
                        if content:
                            items.append(ContentItem(
                                title=title, summary=content[:600], date=date_str,
                                url=detail_url, source="Criteo"
                            ))
                            print(f"        ✓ {title[:40]}...")
                            
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"    ✗ Criteo 错误: {e}")
        finally:
            page.close()
        
        print(f"    Criteo: {len(items)} 条")
        return items
    
    def fetch_teads(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Teads"""
        items = []
        url = COMPETITOR_SOURCES["Teads"]["url"]
        print("  [Stealth] 抓取 Teads...")
        
        html = self.fetch_page(url, wait_for=".card", timeout=60000)
        if not html:
            return items
        
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.find_all('div', class_='card')
        print(f"    找到 {len(cards)} 个卡片")
        
        for card in cards[:10]:
            try:
                link = card.find('a', href=True)
                if not link:
                    continue
                
                title = self.clean_text(link.get_text())
                if not title or len(title) < 10:
                    continue
                
                detail_url = urljoin(url, link['href'])
                
                # 从URL提取日期
                date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', detail_url)
                if date_match:
                    date_str = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
                else:
                    continue
                
                if not self.is_in_date_window(date_str, window_start, window_end):
                    continue
                
                content = self._fetch_detail(detail_url)
                if content:
                    items.append(ContentItem(
                        title=title, summary=content[:600], date=date_str,
                        url=detail_url, source="Teads"
                    ))
                    print(f"    ✓ {title[:40]}... ({date_str})")
                    
            except Exception as e:
                continue
        
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
                    
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"    ✗ AppLovin 错误: {e}")
        finally:
            page.close()
        
        print(f"    AppLovin: {len(items)} 条")
        return items
    
    def fetch_unity(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Unity
        
        策略:
        1. Unity 主站 (unity.com/news) 是客户端渲染，curl 无法获取文章列表
        2. 使用 curl 直接访问已知的文章链接
        3. 链接列表需要定期更新（建议每周检查一次）
        
        TODO: 考虑使用 Puppeteer/Selenium 等更强大的浏览器自动化工具
              或者寻找 Unity RSS/API 端点
        """
        items = []
        print("  [Stealth] 抓取 Unity...")
        print("    注意: Unity 网站需要定期更新链接列表")
        
        import subprocess
        
        # 已知的新闻链接列表 - 需要定期更新
        # 建议每周访问 https://unity.com/news 获取最新链接
        news_urls = [
            "https://unity.com/news/unitys-fourth-quarter-and-fiscal-year-2025-financial-results-are-available",
            "https://unity.com/news/unity-appoints-bernard-kim-to-its-board-of-directors-and-announces-board-transitions",
            # 添加更多链接...
        ]
        
        for i, detail_url in enumerate(news_urls):
            try:
                print(f"    [{i+1}] 访问: {detail_url[:70]}...")
                
                # 使用 curl 获取页面（绕过 Playwright 限制）
                result = subprocess.run([
                    'curl', '-s', detail_url,
                    '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    '-H', 'Accept-Language: en-US,en;q=0.9',
                ], capture_output=True, text=True, timeout=30)
                
                html = result.stdout
                
                if 'Access Denied' in html:
                    print(f"        ⚠️ Access Denied")
                    continue
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # 获取标题
                title = ""
                h1 = soup.find('h1')
                if h1:
                    title = self.clean_text(h1.get_text())
                else:
                    title_elem = soup.find('title')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                
                if not title:
                    print(f"        ✗ 无法获取标题")
                    continue
                
                # 获取日期 - 从文本查找
                date_str = ""
                body_text = soup.get_text()[:5000]
                date_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})', body_text, re.IGNORECASE)
                if date_match:
                    months = {'january': '01', 'february': '02', 'march': '03', 'april': '04', 'may': '05', 'june': '06',
                             'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12'}
                    month_num = months.get(date_match.group(1).lower(), '01')
                    day = date_match.group(2).zfill(2)
                    year = date_match.group(3)
                    date_str = f"{year}-{month_num}-{day}"
                
                if not date_str:
                    print(f"        ✗ 无法获取日期")
                    continue
                
                print(f"        标题: {title[:50]}...")
                print(f"        日期: {date_str}", end="")
                
                # 检查日期窗口
                if not self.is_in_date_window(date_str, window_start, window_end):
                    print(f" - 不在窗口")
                    continue
                
                print(f" ✅ 在窗口内")
                
                # 获取内容
                content = ""
                for selector in ['article', '.content', 'main', '[role="main"]']:
                    elem = soup.select_one(selector)
                    if elem:
                        text = elem.get_text(separator=' ', strip=True)
                        if len(text) > 200:
                            content = self.clean_text(text)
                            break
                
                if not content:
                    for script in soup(["script", "style", "nav", "header"]):
                        script.decompose()
                    body = soup.find('body')
                    if body:
                        content = self.clean_text(body.get_text(separator=' ', strip=True))
                
                if content:
                    items.append(ContentItem(
                        title=title,
                        summary=content[:600],
                        date=date_str,
                        url=detail_url,
                        source="Unity"
                    ))
                    print(f"        ✓ 已添加 ({len(content)} 字符)")
                else:
                    print(f"        ✗ 无法提取内容")
                
            except Exception as e:
                print(f"        ✗ 错误: {e}")
                continue
        
        print(f"    Unity: {len(items)} 条")
        
        # 提示更新链接
        if len(items) == 0:
            print("    ⚠️ 未抓取到任何新闻，可能需要更新链接列表")
            print("       请访问 https://unity.com/news 获取最新链接")
        
        return items
    
    def fetch_zeta(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Zeta Global"""
        items = []
        url = COMPETITOR_SOURCES["Zeta Global"]["url"]
        print("  [Stealth] 抓取 Zeta Global...")
        
        html = self.fetch_page(url, wait_for="table", timeout=60000)
        if not html:
            return items
        
        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.find_all('table') or soup.find_all('tr')
        print(f"    找到 {len(rows)} 行")
        
        for row in rows[:15]:
            try:
                link = row.find('a', href=True)
                if not link:
                    continue
                
                title = self.clean_text(link.get_text())
                if not title or len(title) < 10:
                    continue
                
                detail_url = urljoin(url, link['href'])
                
                # 获取日期
                date_elem = row.find('td', class_=re.compile('date')) or row.find('time')
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text())
                
                if not date_str:
                    continue
                
                if not self.is_in_date_window(date_str, window_start, window_end):
                    continue
                
                content = self._fetch_detail(detail_url)
                if content:
                    items.append(ContentItem(
                        title=title, summary=content[:600], date=date_str,
                        url=detail_url, source="Zeta Global"
                    ))
                    print(f"    ✓ {title[:40]}... ({date_str})")
                    
            except Exception as e:
                continue
        
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
                        
                        if not date_str:
                            detail_page.close()
                            continue
                        
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
                        source="mobvista"
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
    
    def fetch_magnite(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Magnite"""
        items = []
        url = COMPETITOR_SOURCES["Magnite"]["url"]
        print("  [Stealth] 抓取 Magnite...")
        
        html = self.fetch_page(url, wait_for="article", timeout=60000)
        if not html:
            return items
        
        soup = BeautifulSoup(html, 'html.parser')
        articles = soup.find_all('article') or soup.find_all('div', class_=re.compile('press|news'))
        print(f"    找到 {len(articles)} 篇文章")
        
        for article in articles[:10]:
            try:
                link = article.find('a', href=True)
                if not link:
                    continue
                
                title = self.clean_text(link.get_text())
                if not title or len(title) < 10:
                    continue
                
                detail_url = urljoin(url, link['href'])
                
                # 获取日期
                date_elem = article.find('time') or article.find(class_=re.compile('date'))
                date_str = ""
                if date_elem:
                    date_str = self.parse_date(date_elem.get_text())
                
                if not date_str:
                    continue
                
                if not self.is_in_date_window(date_str, window_start, window_end):
                    continue
                
                content = self._fetch_detail(detail_url)
                if content:
                    items.append(ContentItem(
                        title=title, summary=content[:600], date=date_str,
                        url=detail_url, source="Magnite"
                    ))
                    print(f"    ✓ {title[:40]}... ({date_str})")
                    
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
