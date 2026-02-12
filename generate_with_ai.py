#!/usr/bin/env python3
"""
使用 DeepSeek API 生成真实摘要
"""

import os
import sys

# 必须先设置 API Key，再导入其他模块
os.environ['DEEPSEEK_API_KEY'] = 'sk-82204813c03a4aaeb1e4ab23eb6d4749'
os.environ['DEEPSEEK_API_BASE'] = 'https://api.deepseek.com'
os.environ['DEEPSEEK_MODEL'] = 'deepseek-chat'

sys.path.insert(0, 'src')

from datetime import datetime, timedelta
from fetchers.competitor_fetcher_v2 import CompetitorFetcherV2
from fetchers.industry_fetcher import IndustryFetcher
from summarizer import Summarizer
from renderer import HTMLRenderer

print("=" * 60)
print("使用 DeepSeek API 生成周报")
print("=" * 60)

window_end = datetime(2026, 2, 12)
window_start = window_end - timedelta(days=30)
start_str = str(window_start.date())
end_str = str(window_end.date())

# 1. 抓取竞品
print("\n[1/4] 抓取竞品资讯...")
fetcher = CompetitorFetcherV2()
competitor_items = fetcher._fetch_ttd("https://www.thetradedesk.com/press-room", window_start, window_end)
print(f"  TTD: {len(competitor_items)} 条")

# 2. 抓取行业资讯
print("\n[2/4] 抓取行业资讯...")
ind_fetcher = IndustryFetcher()
industry_items = ind_fetcher.fetch_all(window_start, window_end)
total_ind = sum(len(v) for v in industry_items.values())
print(f"  行业资讯: {total_ind} 条")
for module, items in industry_items.items():
    if items:
        print(f"    - {module}: {len(items)} 条")

# 3. 使用 DeepSeek 生成摘要
print("\n[3/4] 使用 DeepSeek 生成中文摘要...")
summarizer = Summarizer()

# 竞品摘要
for i, item in enumerate(competitor_items, 1):
    print(f"  [竞品 {i}/{len(competitor_items)}] {item.title[:35]}...")
    item.summary = summarizer.summarize(item.title, item.summary)
    print(f"      ✓ {len(item.summary)} 字")

# 行业摘要
for module, items in industry_items.items():
    for item in items:
        print(f"  [行业-{module}] {item.title[:35]}...")
        item.summary = summarizer.summarize(item.title, item.summary)
        print(f"      ✓ {len(item.summary)} 字")

# 4. 生成报告
print("\n[4/4] 生成 HTML...")
renderer = HTMLRenderer()
competitor_data = {"TTD": competitor_items}
html = renderer.render(competitor_data, industry_items, start_str, end_str)
output_path = renderer.save(html, start_str, end_str)

print(f"\n{'=' * 60}")
print(f"✅ 周报已生成: {output_path}")
print(f"  竞品: {len(competitor_items)} 条")
print(f"  行业: {total_ind} 条")
print(f"  总计: {len(competitor_items) + total_ind} 条")
print('=' * 60)
