#!/usr/bin/env python3
"""
专门抓取 Teads 的测试脚本
Teads 日期在详情页 time 标签文本中，格式如 "February 5, 2026"
时间窗口：10天内
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
print("Teads 专门抓取 - 最近10天")
print("URL: https://www.teads.com/press-releases/")
print("="*70)

url = "https://www.teads.com/press-releases/"

# 计算10天前到今天的时间窗口
today = datetime(2026, 2, 12)  # 模拟今天为2月12日
window_start = today - timedelta(days=10)
window_end = today

target_start = window_start.strftime("%Y-%m-%d")
target_end = window_end.strftime("%Y-%m-%d")

print(f"\n时间窗口: {target_start} ~ {target_end}")
print(f"策略: 进入每个详情页提取日期\n")

items = []
processed_urls = set()

with sync_playwright() as p:
    print("[1] 启动浏览器...")
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    )
    
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    )
    
    page = context.new_page()
    
    try:
        print("[2] 访问 Teads Press Releases 页面...")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        print("    ✓ 页面加载完成")
        
        print("[3] 等待内容加载 (5秒)...")
        page.wait_for_timeout(5000)
        
        print("[4] 保存截图...")
        page.screenshot(path='teads_page.png', full_page=True)
        print("    ✓ 截图已保存: teads_page.png")
        
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        print("\n[5] 查找文章链接...")
        
        # Teads 使用 .card 类
        articles = soup.select('.card')
        if not articles:
            articles = soup.find_all('article') or soup.select('.press-item, .blog-post')
        
        print(f"    找到 {len(articles)} 篇文章")
        
        # 去重
        unique_articles = []
        seen_urls = set()
        for article in articles:
            link = article.find('a', href=True)
            if link:
                href = link.get('href', '')
                if href and href not in seen_urls:
                    seen_urls.add(href)
                    unique_articles.append(article)
        
        print(f"    去重后: {len(unique_articles)} 篇")
        print(f"\n[6] 逐个访问详情页查找 {target_start} ~ {target_end} 的新闻...\n")
        
        for i, article in enumerate(unique_articles[:5]):  # 检查前5篇
            try:
                link = article.find('a', href=True)
                if not link:
                    continue
                
                href = link.get('href', '')
                detail_url = urljoin(url, href)
                
                # 去重检查
                if detail_url in processed_urls:
                    continue
                processed_urls.add(detail_url)
                
                # Teads 的标题需要从其他元素获取
                title_elem = article.find(['h2', 'h3', 'h1', 'h4']) or article.find(class_=re.compile('title|heading'))
                if not title_elem:
                    title_elem = link
                title = title_elem.get_text(strip=True)
                
                # 如果标题是 "Read more"，尝试从图片 alt 获取
                if not title or len(title) < 10 or title.lower() == 'read more':
                    img = article.find('img')
                    if img and img.get('alt'):
                        title = img.get('alt').strip()
                    else:
                        continue
                
                print(f"[{i+1}] {title[:60]}...")
                print(f"    URL: {href[:70]}...")
                
                # 进入详情页获取日期
                detail_page = context.new_page()
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
                        
                        # 尝试标准格式
                        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', datetime_attr)
                        if match:
                            date_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                            print(f"    从 datetime 获取: {date_str}")
                        # 尝试文本格式 "February 5, 2026"
                        elif time_text:
                            match = re.match(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})', time_text, re.IGNORECASE)
                            if match:
                                months = {'january': '01', 'february': '02', 'march': '03', 'april': '04', 'may': '05', 'june': '06',
                                         'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12'}
                                month_num = months.get(match.group(1).lower(), '01')
                                date_str = f"{match.group(3)}-{month_num}-{match.group(2).zfill(2)}"
                                print(f"    从 time 文本获取: {date_str}")
                    
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
                                print(f"    从日期元素获取: {date_str}")
                    
                    if date_str:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                        if window_start <= date_obj <= window_end:
                            print(f"    ✅ 在时间窗口内!")
                            
                            # 提取内容
                            content = ""
                            for selector in ['article', '.content', '.main-content', 'main', '.post-content', '.entry-content', '.blog-content']:
                                elem = detail_soup.select_one(selector)
                                if elem:
                                    text = elem.get_text(separator=' ', strip=True)
                                    if len(text) > 200:
                                        content = text
                                        break
                            
                            if not content:
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
                                    source="Teads"
                                ))
                                print(f"    ✓ 已添加 ({len(content)} 字符)")
                            else:
                                print(f"    ✗ 无法提取内容")
                        else:
                            print(f"    - 不在时间窗口 ({date_str})")
                    else:
                        print(f"    ✗ 无法提取日期")
                    
                    detail_page.close()
                    
                except Exception as e:
                    print(f"    ✗ 详情页错误: {e}")
                    try:
                        detail_page.close()
                    except:
                        pass
                    continue
                
                print()
                
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
    print("\n[7] 生成报告...")
    try:
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if api_key:
            summarizer = Summarizer()
            for item in items:
                print(f"    生成摘要: {item.title[:40]}...")
                item.summary = summarizer.summarize(item.title, item.summary)
        
        renderer = HTMLRenderer()
        competitor_data = {"Teads": items}
        html = renderer.render(competitor_data, {}, target_start, target_end)
        output_path = renderer.save(html, target_start, target_end)
        
        print(f"\n✅ 报告已生成: {output_path}")
        
    except Exception as e:
        print(f"    ⚠️ 生成报告失败: {e}")
else:
    print("\n⚠️ 未抓到任何新闻")

print("\n完成!")
