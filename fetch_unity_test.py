#!/usr/bin/env python3
"""
专门抓取 Unity 的测试脚本
Unity 网站有 Playwright 访问限制，使用 curl 绕过
时间窗口: 7天内
"""
import sys
sys.path.insert(0, 'src')

import os
import re
import subprocess
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

from fetchers.base import ContentItem
from summarizer import Summarizer
from renderer import HTMLRenderer

print("="*70)
print("Unity 专门抓取 - 最近7天")
print("URL: https://unity.com/news")
print("="*70)

# 计算7天前到今天的时间窗口
today = datetime(2026, 2, 12)  # 模拟今天为2月12日
window_start = today - timedelta(days=7)
window_end = today

target_start = window_start.strftime("%Y-%m-%d")
target_end = window_end.strftime("%Y-%m-%d")

print(f"\n时间窗口: {target_start} ~ {target_end}")
print(f"策略: 使用 curl 访问已知的新闻链接\n")

items = []

# 用户提供的已知新闻链接
news_urls = [
    "https://unity.com/news/unitys-fourth-quarter-and-fiscal-year-2025-financial-results-are-available",
    "https://unity.com/news/unity-appoints-bernard-kim-to-its-board-of-directors-and-announces-board-transitions"
]

print("[1] 开始抓取...\n")

for i, detail_url in enumerate(news_urls):
    try:
        print(f"[{i+1}] 访问: {detail_url[:70]}...")
        
        # 使用 curl 获取页面
        result = subprocess.run([
            'curl', '-s', detail_url,
            '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            '-H', 'Accept-Language: en-US,en;q=0.9',
        ], capture_output=True, text=True, timeout=30)
        
        html = result.stdout
        
        if 'Access Denied' in html:
            print(f"    ⚠️ Access Denied")
            continue
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 获取标题
        title = ""
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)
        else:
            title_elem = soup.find('title')
            if title_elem:
                title = title_elem.get_text(strip=True)
        
        if not title:
            print(f"    ✗ 无法获取标题")
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
            print(f"    ✗ 无法获取日期")
            continue
        
        print(f"    标题: {title[:60]}...")
        print(f"    日期: {date_str}", end="")
        
        # 检查日期窗口
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        if not (window_start <= date_obj <= window_end):
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
                    content = text
                    break
        
        if not content:
            for script in soup(["script", "style", "nav", "header"]):
                script.decompose()
            body = soup.find('body')
            if body:
                content = body.get_text(separator=' ', strip=True)
        
        if content:
            content = re.sub(r'\s+', ' ', content)
            items.append(ContentItem(
                title=title,
                summary=content[:600],
                date=date_str,
                url=detail_url,
                source="Unity"
            ))
            print(f"    ✓ 已添加 ({len(content)} 字符)")
        else:
            print(f"    ✗ 无法提取内容")
        
    except Exception as e:
        print(f"    ✗ 错误: {e}")
        continue

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
    print("\n[2] 生成报告...")
    try:
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if api_key:
            summarizer = Summarizer()
            for item in items:
                print(f"    生成摘要: {item.title[:40]}...")
                item.summary = summarizer.summarize(item.title, item.summary)
        
        renderer = HTMLRenderer()
        competitor_data = {"Unity": items}
        html = renderer.render(competitor_data, {}, target_start, target_end)
        output_path = renderer.save(html, target_start, target_end)
        
        print(f"\n✅ 报告已生成: {output_path}")
        
    except Exception as e:
        print(f"    ⚠️ 生成报告失败: {e}")
else:
    print("\n⚠️ 未抓到任何新闻")

print("\n完成!")
