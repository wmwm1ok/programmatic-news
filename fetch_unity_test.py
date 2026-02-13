#!/usr/bin/env python3
"""
专门抓取 Unity 的测试脚本
Unity 网站: https://unity.com/news
注意: Unity 网站有访问控制，可能需要特殊处理
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
print("Unity 专门抓取 - 最近7天")
print("URL: https://unity.com/news")
print("="*70)

url = "https://unity.com/news"

# 计算7天前到今天的时间窗口
today = datetime(2026, 2, 12)  # 模拟今天为2月12日
window_start = today - timedelta(days=7)
window_end = today

target_start = window_start.strftime("%Y-%m-%d")
target_end = window_end.strftime("%Y-%m-%d")

print(f"\n时间窗口: {target_start} ~ {target_end}")
print(f"策略: 尝试从 news 页面获取文章链接\n")

items = []

# 尝试使用 StealthFetcher
from fetchers.stealth_fetcher import StealthFetcher

print("[1] 使用 StealthFetcher 抓取 Unity...")
fetcher = StealthFetcher()
try:
    items = fetcher.fetch_unity(window_start, window_end)
    print(f"\n✓ 抓取完成，共 {len(items)} 条")
except Exception as e:
    print(f"\n✗ 抓取失败: {e}")
    print("\n注意: Unity 网站可能有访问限制")
finally:
    fetcher.close()

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
    print("\n提示: Unity 网站 (https://unity.com/news) 可能有访问限制")
    print("      您可以手动提供符合7天条件的新闻链接，我来调整抓取逻辑")

print("\n完成!")
