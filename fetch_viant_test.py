#!/usr/bin/env python3
"""
专门抓取 Viant Technology 的测试脚本
Viant 日期在 PressRelease-post--date 类中，格式 "January 5, 2026"
需要进入详情页获取内容
时间窗口: 14天内
"""
import sys
sys.path.insert(0, 'src')

import os
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from playwright.sync_api import sync_playwright
from fetchers.base import ContentItem
from summarizer import Summarizer
from renderer import HTMLRenderer

print("="*70)
print("Viant Technology 专门抓取 - 最近14天")
print("URL: https://www.viantinc.com/company/news/press-releases/")
print("="*70)

url = "https://www.viantinc.com/company/news/press-releases/"

# 计算14天前到今天的时间窗口
today = datetime(2026, 2, 12)  # 模拟今天为2月12日
window_start = today - timedelta(days=14)
window_end = today

target_start = window_start.strftime("%Y-%m-%d")
target_end = window_end.strftime("%Y-%m-%d")

print(f"\n时间窗口: {target_start} ~ {target_end}")
print(f"策略: 从列表页提取日期，进入详情页获取内容\n")

items = []
processed_urls = set()

with sync_playwright() as p:
    print("[1] 启动 Stealth 浏览器...")
    browser = p.chromium.launch(
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
    
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        locale='en-US',
        timezone_id='America/New_York',
    )
    
    # 注入 stealth 脚本
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        window.chrome = {runtime: {}, loadTimes: function() {}, csi: function() {}, app: {}};
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
    """)
    
    page = context.new_page()
    
    try:
        print("[2] 访问 Viant Press Releases 页面...")
        page.goto(url, wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(5000)
        print("    ✓ 页面加载完成")
        
        print("[3] 保存截图...")
        page.screenshot(path='viant_page.png', full_page=True)
        print("    ✓ 截图已保存: viant_page.png")
        
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        print("\n[4] 查找 PressRelease-post--date 日期元素...")
        
        # 查找日期元素 - PressRelease-post--date 类
        date_divs = soup.find_all('div', class_='PressRelease-post--date')
        print(f"    找到 {len(date_divs)} 个日期元素")
        
        for i, date_div in enumerate(date_divs[:15]):
            try:
                date_text = date_div.get_text(strip=True)
                
                # 解析日期 "January 5, 2026" -> "2026-01-05"
                match = re.match(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})', date_text, re.IGNORECASE)
                if not match:
                    continue
                
                months = {'january': '01', 'february': '02', 'march': '03', 'april': '04', 'may': '05', 'june': '06',
                         'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12'}
                month_num = months.get(match.group(1).lower(), '01')
                date_str = f"{match.group(3)}-{month_num}-{match.group(2).zfill(2)}"
                
                # 查找对应的新闻标题和链接 - 从父元素中查找
                parent = date_div.find_parent()
                if not parent:
                    continue
                
                # 向上查找包含链接的元素
                link_elem = None
                for _ in range(3):
                    if not parent:
                        break
                    link_elem = parent.find('a', href=True)
                    if link_elem:
                        break
                    parent = parent.parent
                
                if not link_elem:
                    continue
                
                href = link_elem.get('href', '')
                if not href:
                    continue
                
                detail_url = urljoin(url, href)
                
                # 去重
                if detail_url in processed_urls:
                    continue
                processed_urls.add(detail_url)
                
                title = link_elem.get_text(strip=True)
                if not title or len(title) < 10:
                    continue
                
                print(f"\n[{i+1}] {title[:60]}...")
                print(f"    日期: {date_text} -> {date_str}")
                print(f"    URL: {href[:70]}...")
                
                # 检查日期窗口
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                if not (window_start <= date_obj <= window_end):
                    print(f"    - 不在时间窗口")
                    continue
                
                print(f"    ✅ 在时间窗口内，进入详情页...")
                
                # 进入详情页获取内容
                detail_page = context.new_page()
                try:
                    detail_page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
                    detail_page.wait_for_timeout(3000)
                    
                    detail_html = detail_page.content()
                    detail_soup = BeautifulSoup(detail_html, 'html.parser')
                    
                    # 提取内容
                    content = ""
                    for selector in ['.PressRelease-post', '.content', 'article', '.main-content', '.press-release', 'main']:
                        elem = detail_soup.select_one(selector)
                        if elem:
                            text = elem.get_text(separator=' ', strip=True)
                            if len(text) > 200:
                                content = text
                                break
                    
                    if not content:
                        # 备选：移除脚本样式后获取 body
                        for script in detail_soup(["script", "style", "nav", "header", "footer"]):
                            script.decompose()
                        body = detail_soup.find('body')
                        if body:
                            content = body.get_text(separator=' ', strip=True)
                    
                    if content:
                        content = re.sub(r'\s+', ' ', content)
                        items.append(ContentItem(
                            title=title,
                            summary=content[:600],
                            date=date_str,
                            url=detail_url,
                            source="Viant Technology"
                        ))
                        print(f"    ✓ 已添加 ({len(content)} 字符)")
                    else:
                        print(f"    ✗ 无法提取内容")
                    
                    detail_page.close()
                    
                except Exception as e:
                    print(f"    ✗ 详情页错误: {e}")
                    try:
                        detail_page.close()
                    except:
                        pass
                    continue
                    
            except Exception as e:
                print(f"    ✗ 处理出错: {e}")
                continue
                
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        browser.close()

# 结果输出
print("\n" + "="*70)
print(f"抓取完成！共 {len(items)} 条")
print("="*70)

for item in items:
    print(f"\n日期: {item.date}")
    print(f"标题: {item.title}")
    print(f"链接: {item.url}")

# 生成报告
if items:
    print("\n[5] 生成报告...")
    try:
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if api_key:
            summarizer = Summarizer()
            for item in items:
                print(f"    生成摘要: {item.title[:40]}...")
                item.summary = summarizer.summarize(item.title, item.summary)
        
        renderer = HTMLRenderer()
        competitor_data = {"Viant Technology": items}
        html = renderer.render(competitor_data, {}, target_start, target_end)
        output_path = renderer.save(html, target_start, target_end)
        
        print(f"\n✅ 报告已生成: {output_path}")
        
    except Exception as e:
        print(f"    ⚠️ 生成报告失败: {e}")
else:
    print("\n⚠️ 未抓到任何新闻")

print("\n完成!")
