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
                self.browser = self.pw.chromium.launch(headless=True)
                self.context = self.browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            except ImportError:
                print("  [!] Playwright 未安装，使用 requests 模式")
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
    
    def fetch_criteo(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Criteo - 使用日历控件（增强版）"""
        items = []
        url = COMPETITOR_SOURCES["Criteo"]["url"]
        
        print("  [Playwright] 抓取 Criteo...")
        
        if not self._init_browser():
            return items
        
        page = self.context.new_page()
        # 用于去重
        processed_urls = set()
        
        try:
            # 增加超时到 120 秒
            print(f"    访问 {url}...")
            page.goto(url, wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(8000)  # 等待日历控件加载
            
            # 检查是否有 Cloudflare 挑战
            content = page.content()
            if 'cloudflare' in content.lower() or 'checking your browser' in content.lower():
                print("    ⚠️ 检测到 Cloudflare，等待挑战完成...")
                page.wait_for_timeout(10000)
            
            # 查找所有可点击的日期按钮
            date_buttons = page.query_selector_all('button.wd_wai_dateButton:not([disabled])')
            print(f"    找到 {len(date_buttons)} 个可点击日期")
            
            for i, button in enumerate(date_buttons[:20]):  # 处理前20个日期
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
                    
                    # 使用 evaluate 点击（带有 scrollIntoView）
                    button.evaluate('el => { el.scrollIntoView({block: "center"}); setTimeout(() => el.click(), 100); }')
                    page.wait_for_timeout(4000)  # 等待新闻加载
                    
                    # 获取显示的新闻
                    html = page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 查找新闻链接 - 更宽松的选择器
                    news_links = soup.find_all('a', href=re.compile(r'202[0-9]'))
                    print(f"      找到 {len(news_links)} 个潜在新闻")
                    
                    for link in news_links[:10]:  # 每天最多10条
                        title = self.clean_text(link.get_text())
                        if not title or len(title) < 10 or 'photo' in title.lower():
                            continue
                        
                        href = link.get('href', '')
                        if not href.startswith('http'):
                            detail_url = urljoin(url, href)
                        else:
                            detail_url = href
                        
                        # 去重检查
                        if href in processed_urls:
                            continue
                        processed_urls.add(href)
                        
                        print(f"      处理新闻: {title[:50]}...")
                        
                        # 获取详情内容 - 尝试更多选择器
                        detail_page = self.context.new_page()
                        try:
                            detail_page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
                            detail_page.wait_for_timeout(3000)
                            
                            detail_html = detail_page.content()
                            detail_soup = BeautifulSoup(detail_html, 'html.parser')
                            
                            content = ""
                            for selector in ['article', '.content', '.main-content', 'main', '.wd_body', '.wd_content', '.press-release', '.news-content', 'body']:
                                content_elem = detail_soup.select_one(selector)
                                if content_elem:
                                    text = content_elem.get_text(separator=' ', strip=True)
                                    if len(text) > 200:
                                        content = text
                                        break
                            
                            if content:
                                content = re.sub(r'\s+', ' ', content)
                                items.append(ContentItem(
                                    title=title,
                                    summary=content[:600],
                                    date=date_str,
                                    url=detail_url,
                                    source="Criteo"
                                ))
                                print(f"        ✓ 已添加")
                            else:
                                print(f"        ✗ 无法提取内容")
                                
                        except Exception as e:
                            print(f"        ✗ 获取详情失败: {e}")
                        finally:
                            detail_page.close()
                            
                except Exception as e:
                    print(f"    处理日期出错: {e}")
                    continue
                    
        except Exception as e:
            print(f"    ✗ Playwright 错误: {e}")
        finally:
            page.close()
        
        print(f"    Criteo: {len(items)} 条（去重后）")
        return items
    
    def fetch_applovin(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 AppLovin - 投资者网站 https://investors.applovin.com/
        日期在 evergreen-item-date-time / evergreen-news-date 类中，格式 "February 11, 2026"
        """
        items = []
        url = COMPETITOR_SOURCES["AppLovin"]["url"]
        
        print("  [Playwright] 抓取 AppLovin...")
        
        # 独立启动浏览器（需要特殊参数）
        try:
            from playwright.sync_api import sync_playwright
            pw = sync_playwright().start()
            browser = pw.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
        except Exception as e:
            print(f"    ✗ 浏览器启动失败: {e}")
            return items
        
        page = context.new_page()
        processed_urls = set()
        
        try:
            # 使用 networkidle 等待页面完全加载
            page.goto(url, wait_until="networkidle", timeout=90000)
            page.wait_for_timeout(5000)
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找日期元素 (evergreen-item-date-time 或 evergreen-news-date)
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
                    if not href:
                        continue
                    
                    # 检查是否是新闻链接 (/news/news-details/...)
                    if '/news/' not in href or '/events-and-presentations/' in href:
                        continue
                    
                    detail_url = urljoin(url, href)
                    
                    # 去重
                    if detail_url in processed_urls:
                        continue
                    processed_urls.add(detail_url)
                    
                    title = self.clean_text(link_elem.get_text())
                    if not title or len(title) < 10:
                        continue
                    
                    print(f"    [{len(items)+1}] {title[:50]}... | 日期: {date_str}", end="")
                    
                    # 检查日期窗口
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    if not (window_start <= date_obj <= window_end):
                        print(f" - 不在时间窗口")
                        continue
                    
                    # 进入详情页获取内容
                    detail_page = context.new_page()
                    try:
                        detail_page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
                        detail_page.wait_for_timeout(3000)
                        
                        detail_html = detail_page.content()
                        detail_soup = BeautifulSoup(detail_html, 'html.parser')
                        
                        # 提取内容
                        content = ""
                        for selector in ['.module_body', '.news-body', '.content', 'article', '.main-content', '.press-release']:
                            elem = detail_soup.select_one(selector)
                            if elem:
                                text = elem.get_text(separator=' ', strip=True)
                                if len(text) > 200:
                                    content = self.clean_text(text)
                                    break
                        
                        if not content:
                            # 备选：移除脚本样式后获取 body
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
                                source="AppLovin"
                            ))
                            print(f" ✓ 已添加")
                        else:
                            print(f" ✗ 无法提取内容")
                        
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
            print(f"    ✗ AppLovin 错误: {e}")
        finally:
            page.close()
            browser.close()
            pw.stop()
        
        print(f"    AppLovin: {len(items)} 条")
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
    
    def fetch_criteo_legacy(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Criteo"""
        items = []
        url = COMPETITOR_SOURCES["Criteo"]["url"]
        
        print("  [Playwright] 抓取 Criteo...")
        html = self.fetch_page(url, wait_for="table, .item, .release")
        if not html:
            return items
        
        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.find_all('tr') or soup.select('.item, .release-item')
        
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
                            source="Criteo"
                        ))
                        
            except Exception as e:
                continue
        
        return items
    
    def fetch_taboola(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Taboola - 日期在详情页 time 标签中"""
        items = []
        url = COMPETITOR_SOURCES["Taboola"]["url"]
        
        print("  [Playwright] 抓取 Taboola...")
        if not self._init_browser():
            return items
        
        page = self.context.new_page()
        processed_urls = set()
        
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            articles = soup.find_all('article') or soup.select('.post, .entry')
            print(f"    找到 {len(articles)} 篇文章")
            
            for article in articles[:15]:
                try:
                    link_elem = article.find('a', href=True)
                    if not link_elem:
                        continue
                    
                    detail_url = urljoin(url, link_elem['href'])
                    if detail_url in processed_urls:
                        continue
                    processed_urls.add(detail_url)
                    
                    title_elem = article.find(['h2', 'h3', 'h1']) or link_elem
                    title = self.clean_text(title_elem.get_text())
                    if not title or len(title) < 10:
                        continue
                    
                    # 进入详情页获取日期
                    detail_page = self.context.new_page()
                    try:
                        detail_page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
                        detail_page.wait_for_timeout(3000)
                        
                        detail_html = detail_page.content()
                        detail_soup = BeautifulSoup(detail_html, 'html.parser')
                        
                        # 提取日期 - Taboola 使用非标准格式 "2026-Feb-Thu"
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
                        
                        if date_str and self.is_in_date_window(date_str, window_start, window_end):
                            # 直接从详情页提取内容（已经在详情页了）
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
    
    def fetch_teads(self, window_start: datetime, window_end: datetime) -> List[ContentItem]:
        """抓取 Teads - 日期在详情页 time 标签文本中，如 'February 5, 2026'"""
        items = []
        url = COMPETITOR_SOURCES["Teads"]["url"]
        
        print("  [Playwright] 抓取 Teads...")
        if not self._init_browser():
            return items
        
        page = self.context.new_page()
        processed_urls = set()
        
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Teads 使用 .card 类
            articles = soup.select('.card')
            if not articles:
                articles = soup.find_all('article') or soup.select('.press-item, .blog-post')
            
            print(f"    找到 {len(articles)} 篇文章")
            
            for article in articles[:5]:  # 检查前5个
                try:
                    link_elem = article.find('a', href=True)
                    if not link_elem:
                        continue
                    
                    detail_url = urljoin(url, link_elem['href'])
                    if detail_url in processed_urls:
                        continue
                    processed_urls.add(detail_url)
                    
                    # Teads 的标题需要从其他元素获取，链接文本通常是 "Read more..."
                    title_elem = article.find(['h2', 'h3', 'h1', 'h4']) or article.find(class_=re.compile('title|heading'))
                    if not title_elem:
                        title_elem = link_elem
                    title = self.clean_text(title_elem.get_text())
                    if not title or len(title) < 10 or title.lower() == 'read more':
                        # 尝试从图片 alt 或其他属性获取标题
                        img = article.find('img')
                        if img and img.get('alt'):
                            title = self.clean_text(img.get('alt'))
                        else:
                            continue
                    
                    # 进入详情页获取日期
                    detail_page = self.context.new_page()
                    try:
                        detail_page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
                        detail_page.wait_for_timeout(3000)
                        
                        detail_html = detail_page.content()
                        detail_soup = BeautifulSoup(detail_html, 'html.parser')
                        
                        # 提取日期 - Teads 使用 "February 5, 2026" 格式
                        date_str = None
                        time_elem = detail_soup.find('time')
                        
                        if time_elem:
                            datetime_attr = time_elem.get('datetime', '')
                            time_text = time_elem.get_text(strip=True)
                            
                            # 尝试标准格式 datetime="2026-02-05"
                            match = re.search(r'(\d{4})-(\d{2})-(\d{2})', datetime_attr)
                            if match:
                                date_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                            # 尝试文本格式 "February 5, 2026"
                            elif not date_str and time_text:
                                match = re.match(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})', time_text, re.IGNORECASE)
                                if match:
                                    months = {'january': '01', 'february': '02', 'march': '03', 'april': '04', 'may': '05', 'june': '06',
                                             'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12'}
                                    month_num = months.get(match.group(1).lower(), '01')
                                    date_str = f"{match.group(3)}-{month_num}-{match.group(2).zfill(2)}"
                        
                        # 备选：查找日期类元素
                        if not date_str:
                            date_elem = detail_soup.find(class_=re.compile('date|published|time'))
                            if date_elem:
                                date_text = date_elem.get_text(strip=True)
                                match = re.match(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})', date_text, re.IGNORECASE)
                                if match:
                                    months = {'january': '01', 'february': '02', 'march': '03', 'april': '04', 'may': '05', 'june': '06',
                                             'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12'}
                                    month_num = months.get(match.group(1).lower(), '01')
                                    date_str = f"{match.group(3)}-{month_num}-{match.group(2).zfill(2)}"
                        
                        if date_str:
                            print(f"    [{len(items)+1}] {title[:50]}... | 日期: {date_str}", end="")
                        
                        if date_str and self.is_in_date_window(date_str, window_start, window_end):
                            # 从详情页提取内容
                            content = ""
                            for selector in ['article', '.content', '.main-content', 'main', '.post-content', '.entry-content', '.blog-content']:
                                elem = detail_soup.select_one(selector)
                                if elem:
                                    text = elem.get_text(separator=' ', strip=True)
                                    if len(text) > 200:
                                        content = self.clean_text(text)
                                        break
                            
                            if not content:
                                # 备选：获取 body
                                body = detail_soup.find('body')
                                if body:
                                    content = self.clean_text(body.get_text(separator=' ', strip=True))
                            
                            if content:
                                items.append(ContentItem(
                                    title=title,
                                    summary=content[:600],
                                    date=date_str,
                                    url=detail_url,
                                    source="Teads"
                                ))
                                print(f" ✓ 已添加")
                            else:
                                print(f" ✗ 无内容")
                        elif date_str:
                            print(f" - 不在时间窗口")
                        else:
                            print(f"    无法提取日期: {title[:40]}...")
                        
                        detail_page.close()
                    except Exception as e:
                        print(f"    详情页错误: {e}")
                        try:
                            detail_page.close()
                        except:
                            pass
                        continue
                        
                except Exception as e:
                    print(f"    处理错误: {e}")
                    continue
                    
        except Exception as e:
            print(f"    ✗ Teads 错误: {e}")
        finally:
            page.close()
        
        print(f"    Teads: {len(items)} 条")
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
