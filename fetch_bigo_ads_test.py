#!/usr/bin/env python3
"""
专门抓取 BIGO Ads 的测试脚本
BIGO Ads 从 blog 列表页获取链接，进入详情页提取日期
日期格式: "2026-02-03" (在 span 标签中)
时间窗口: 14天内，只检查前3个
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
print("BIGO Ads 专门抓取 - 最近14天 (前3个)")
print("URL: https://www.bigoads.com/resources/blog")
print("="*70)

url = "https://www.bigoads.com/resources/blog"

# 计算14天前到今天的时间窗口
today = datetime(2026, 2, 12)  # 模拟今天为2月12日
window_start = today - timedelta(days=14)
window_end = today

target_start = window_start.strftime("%Y-%m-%d")
target_end = window_end.strftime("%Y-%m-%d")

print(f"\n时间窗口: {target_start} ~ {target_end}")
print(f"策略: 从列表页获取前3个博客链接，进入详情页提取日期\n")

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
        ]
    )
    
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    )
    
    page = context.new_page()
    
    try:
        print("[2] 访问 BIGO Ads Blog...")
        page.goto(url, wait_until="load", timeout=120000)
        page.wait_for_timeout(5000)
        print("    ✓ 页面加载完成")
        
        print("[3] 保存截图...")
        page.screenshot(path='bigo_page.png', full_page=True)
        print("    ✓ 截图已保存: bigo_page.png")
        
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        print("\n[4] 查找博客链接...")
        
        # 查找博客链接
        blog_links = soup.find_all('a', href=re.compile(r'/resources/blog/\d+'))
        print(f"    找到 {len(blog_links)} 个博客链接")
        
        # 去重并只取前3个
        seen_urls = set()
        unique_links = []
        for link in blog_links:
            href = link.get('href', '')
            if href and href not in seen_urls:
                seen_urls.add(href)
                unique_links.append(href)
        
        print(f"    去重后: {len(unique_links)} 个，检查前3个\n")
        
        for i, href in enumerate(unique_links[:3]):
            try:
                detail_url = urljoin(url, href)
                
                # 去重检查
                if detail_url in processed_urls:
                    continue
                processed_urls.add(detail_url)
                
                print(f"[{i+1}] 访问: {href}")
                
                # 进入详情页
                detail_page = context.new_page()
                try:
                    detail_page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
                    detail_page.wait_for_timeout(3000)
                    
                    detail_html = detail_page.content()
                    detail_soup = BeautifulSoup(detail_html, 'html.parser')
                    
                    # 获取标题
                    title = ""
                    h1 = detail_soup.find('h1')
                    if h1:
                        title = h1.get_text(strip=True)
                    else:
                        title_elem = detail_soup.find('title')
                        if title_elem:
                            title = title_elem.get_text(strip=True).replace(' - BIGO Ads', '')
                    
                    if not title:
                        print(f"    ✗ 无法获取标题")
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
                        print(f"    ✗ 无法获取日期")
                        detail_page.close()
                        continue
                    
                    print(f"    标题: {title[:60]}...")
                    print(f"    日期: {date_str}", end="")
                    
                    # 检查日期窗口
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    if not (window_start <= date_obj <= window_end):
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
                                content = text
                                break
                    
                    if not content:
                        for script in detail_soup(["script", "style", "nav", "header"]):
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
                            source="BIGO Ads"
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
    print("\n[5] 生成报告...")
    try:
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if api_key:
            summarizer = Summarizer()
            for item in items:
                print(f"    生成摘要: {item.title[:40]}...")
                item.summary = summarizer.summarize(item.title, item.summary)
        
        renderer = HTMLRenderer()
        competitor_data = {"BIGO Ads": items}
        html = renderer.render(competitor_data, {}, target_start, target_end)
        output_path = renderer.save(html, target_start, target_end)
        
        print(f"\n✅ 报告已生成: {output_path}")
        
    except Exception as e:
        print(f"    ⚠️ 生成报告失败: {e}")
else:
    print("\n⚠️ 未抓到任何新闻")

print("\n完成!")
