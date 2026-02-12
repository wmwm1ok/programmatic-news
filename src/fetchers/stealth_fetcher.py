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
    """
    使用 stealth 技术的抓取器
    通过修改浏览器指纹、模拟真人行为来绕过 Cloudflare 等反爬虫检测
    """
    
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
                
                # 启动浏览器时使用 stealth 参数
                self.browser = self.pw.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--no-first-run',
                        '--no-zygote',
                        '--disable-gpu',
                        '--disable-extensions',
                        '--disable-default-apps',
                        '--disable-background-networking',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-breakpad',
                        '--disable-component-extensions-with-background-pages',
                        '--disable-features=TranslateUI,BlinkGenPropertyTrees',
                        '--disable-ipc-flooding-protection',
                        '--disable-renderer-backgrounding',
                        '--enable-features=NetworkService,NetworkServiceInProcess',
                        '--force-color-profile=srgb',
                        '--metrics-recording-only',
                        '--mute-audio',
                    ]
                )
                
                # 创建带有 stealth 配置的上下文
                self.context = self.browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    locale='en-US',
                    timezone_id='America/New_York',
                    geolocation={'latitude': 40.7128, 'longitude': -74.0060},  # NYC
                    permissions=['geolocation'],
                    color_scheme='light',
                    
                    # 禁用自动化标志
                    bypass_csp=True,
                    java_script_enabled=True,
                )
                
                # 注入 stealth 脚本来隐藏自动化痕迹
                self.context.add_init_script("""
                    // 覆盖 navigator.webdriver
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    
                    // 覆盖 chrome 对象
                    window.chrome = {
                        runtime: {},
                        loadTimes: function() {},
                        csi: function() {},
                        app: {}
                    };
                    
                    // 覆盖 permissions API
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                    
                    // 添加 Plugins 和 MimeTypes
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [
                            {
                                0: {
                                    type: "application/x-google-chrome-pdf",
                                    suffixes: "pdf",
                                    description: "Portable Document Format",
                                    enabledPlugin: Plugin
                                },
                                description: "Portable Document Format",
                                filename: "internal-pdf-viewer",
                                length: 1,
                                name: "Chrome PDF Plugin"
                            }
                        ]
                    });
                    
                    // 覆盖 notification 权限
                    const originalNotification = window.Notification;
                    Object.defineProperty(window, 'Notification', {
                        get: function() {
                            return originalNotification;
                        },
                        set: function(value) {
                            originalNotification = value;
                        }
                    });
                    
                    // 修改 canvas 指纹
                    const getContext = HTMLCanvasElement.prototype.getContext;
                    HTMLCanvasElement.prototype.getContext = function(type, ...args) {
                        const context = getContext.call(this, type, ...args);
                        if (type === '2d') {
                            const getImageData = context.getImageData;
                            context.getImageData = function(x, y, w, h) {
                                const data = getImageData.call(this, x, y, w, h);
                                // 添加微小随机噪声来避免指纹追踪
                                for (let i = 0; i < data.data.length; i += 4) {
                                    data.data[i] += Math.random() < 0.5 ? -1 : 1;
                                }
                                return data;
                            };
                        }
                        return context;
                    };
                """)
                
            except ImportError:
                print("  [!] Playwright 未安装")
                return False
            except Exception as e:
                print(f"  [!] Playwright 初始化失败: {e}")
                return False
        return True
    
    def _human_like_delay(self, min_ms=500, max_ms=2000):
        """模拟人类随机延迟"""
        time.sleep(random.uniform(min_ms, max_ms) / 1000)
    
    def _human_like_scroll(self, page):
        """模拟人类滚动行为"""
        for _ in range(random.randint(2, 5)):
            page.mouse.wheel(0, random.randint(300, 700))
            self._human_like_delay(300, 800)
    
    def _human_like_mouse_move(self, page):
        """模拟人类鼠标移动"""
        for _ in range(random.randint(3, 7)):
            x = random.randint(100, 1800)
            y = random.randint(100, 900)
            page.mouse.move(x, y, steps=random.randint(5, 15))
            self._human_like_delay(100, 300)
    
    def fetch_page(self, url: str, wait_for: str = None, timeout: int = 60000) -> str:
        """使用 stealth 方式获取页面"""
        if not self._init_browser():
            return None
        
        page = self.context.new_page()
        try:
            print(f"    [Stealth] 访问: {url[:60]}...")
            
            # 添加随机延迟，模拟真实用户输入 URL
            self._human_like_delay(500, 1500)
            
            # 访问页面
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            
            # 模拟人类行为
            self._human_like_mouse_move(page)
            self._human_like_scroll(page)
            
            # 等待特定元素
            if wait_for:
                try:
                    page.wait_for_selector(wait_for, timeout=10000)
                except:
                    pass
            
            # 额外等待让 JavaScript 渲染
            self._human_like_delay(3000, 5000)
            
            html = page.content()
            page.close()
            return html
            
        except Exception as e:
            print(f"    [Stealth] 错误: {e}")
            page.close()
            return None
    
    def close(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
        if self.pw:
            self.pw.stop()
    
    def parse_date(self, date_str: str) -> Optional[str]:
        """解析日期"""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
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
        html = self.fetch_page(url, timeout=30000)
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
        """抓取 Criteo - 使用 stealth 模式"""
        items = []
        url = COMPETITOR_SOURCES["Criteo"]["url"]
        
        print("  [Stealth] 抓取 Criteo...")
        
        if not self._init_browser():
            return items
        
        page = self.context.new_page()
        try:
            # 先访问主页
            print(f"    访问主页...")
            page.goto("https://www.criteo.com", wait_until="domcontentloaded", timeout=30000)
            self._human_like_delay(2000, 4000)
            self._human_like_scroll(page)
            
            # 再访问投资者页面
            print(f"    访问投资者页面...")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            self._human_like_delay(5000, 8000)  # 等待日历加载
            
            # 模拟人类滚动查看日历
            self._human_like_scroll(page)
            
            # 查找所有可点击的日期按钮
            date_buttons = page.query_selector_all('button.wd_wai_dateButton:not([disabled])')
            print(f"    找到 {len(date_buttons)} 个可点击日期")
            
            if len(date_buttons) == 0:
                print(f"    未找到日期按钮，可能是 Cloudflare 挑战")
                # 截图查看当前状态
                try:
                    page.screenshot(path='/tmp/criteo_debug.png')
                    print(f"    已截图到 /tmp/criteo_debug.png")
                except:
                    pass
            
            for button in date_buttons[:10]:
                try:
                    date_text = button.inner_text().strip()
                    if not date_text.isdigit():
                        continue
                    
                    day = int(date_text)
                    now = datetime.now()
                    date_str = f"{now.year}-{now.month:02d}-{day:02d}"
                    
                    if not self.is_in_date_window(date_str, window_start, window_end):
                        continue
                    
                    print(f"    点击日期: {date_str}")
                    
                    # 模拟人类点击
                    box = button.bounding_box()
                    if box:
                        page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
                        self._human_like_delay(200, 500)
                    
                    button.click()
                    self._human_like_delay(3000, 5000)  # 等待新闻加载
                    
                    # 获取页面内容
                    html = page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 查找新闻链接 - 使用多种选择器
                    news_links = soup.find_all('a', href=re.compile(r'news|press|release', re.I))
                    
                    print(f"    找到 {len(news_links)} 个新闻链接")
                    
                    for link in news_links[:3]:
                        title = self.clean_text(link.get_text())
                        if not title or len(title) < 10:
                            continue
                        
                        href = link.get('href', '')
                        if href.startswith('http'):
                            detail_url = href
                        else:
                            detail_url = urljoin(url, href)
                        
                        print(f"      处理: {title[:50]}...")
                        
                        # 在新标签页打开详情
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
