#!/usr/bin/env python3
"""
专门抓取 Mobvista 的测试脚本
Mobvista 日期在 announce-item-time 类中，格式 "February 6, 2026"
链接通常是外部 PDF (hkexnews.hk)
时间窗口: 7天内
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
print("Mobvista 专门抓取 - 最近7天")
print("URL: https://www.mobvista.com/en/investor-relations/overview")
print("="*70)

url = "https://www.mobvista.com/en/investor-relations/overview"

# 计算7天前到今天的时间窗口
today = datetime(2026, 2, 12)  # 模拟今天为2月12日
window_start = today - timedelta(days=7)
window_end = today

target_start = window_start.strftime("%Y-%m-%d")
target_end = window_end.strftime("%Y-%m-%d")

print(f"\n时间窗口: {target_start} ~ {target_end}")
print(f"策略: 从公告列表提取日期和链接\n")

items = []

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
        print("[2] 访问 Mobvista 投资者页面...")
        page.goto(url, wait_until="load", timeout=120000)
        page.wait_for_timeout(5000)
        print("    ✓ 页面加载完成")
        
        print("[3] 保存截图...")
        page.screenshot(path='mobvista_page.png', full_page=True)
        print("    ✓ 截图已保存: mobvista_page.png")
        
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        print("\n[4] 查找公告列表...")
        
        # 查找公告项
        announce_items = soup.select('.announce-item')
        print(f"    找到 {len(announce_items)} 个公告")
        
        for i, item in enumerate(announce_items[:10]):
            try:
                # 获取标题
                title_elem = item.find('h2', class_='announce-item-title')
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                
                # 获取日期
                time_elem = item.find('p', class_='announce-item-time')
                if not time_elem:
                    continue
                date_text = time_elem.get_text(strip=True)
                
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
                if not link_elem:
                    continue
                detail_url = link_elem.get('href', '')
                
                # 如果是相对链接，补全
                if detail_url.startswith('/'):
                    detail_url = urljoin(url, detail_url)
                
                print(f"\n[{i+1}] {title[:60]}...")
                print(f"    日期: {date_text} -> {date_str}")
                print(f"    URL: {detail_url[:70]}...")
                
                # 检查日期窗口
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                if not (window_start <= date_obj <= window_end):
                    print(f"    - 不在时间窗口")
                    continue
                
                print(f"    ✅ 在时间窗口内")
                
                # 对于外部 PDF，使用标题作为摘要
                content = f"Mobvista announcement: {title}"
                
                items.append(ContentItem(
                    title=title,
                    summary=content[:600],
                    date=date_str,
                    url=detail_url,
                    source="mobvista"
                ))
                print(f"    ✓ 已添加")
                
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
        competitor_data = {"mobvista": items}
        html = renderer.render(competitor_data, {}, target_start, target_end)
        output_path = renderer.save(html, target_start, target_end)
        
        print(f"\n✅ 报告已生成: {output_path}")
        
    except Exception as e:
        print(f"    ⚠️ 生成报告失败: {e}")
else:
    print("\n⚠️ 未抓到任何新闻")

print("\n完成!")
