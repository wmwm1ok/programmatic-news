#!/usr/bin/env python3
"""
使用 DeepSeek API 生成真实摘要
从环境变量读取 API Key，支持 GitHub Actions 运行
"""

import os
import sys

# 从环境变量读取 API 配置（GitHub Actions 会自动注入）
# 不再硬编码 API key，确保安全性
sys.path.insert(0, 'src')

from datetime import datetime, timedelta
from fetchers.competitor_fetcher_v2 import CompetitorFetcherV2
from fetchers.industry_fetcher import IndustryFetcher
from summarizer import Summarizer
from renderer import HTMLRenderer

print("=" * 60)
print("使用 DeepSeek API 生成周报")
print("=" * 60)

# 使用当前日期作为窗口结束日期
window_end = datetime.now()
window_start = window_end - timedelta(days=7)  # 近7天
start_str = str(window_start.date())
end_str = str(window_end.date())

print(f"\n日期窗口: {start_str} ~ {end_str}")

# 1. 抓取所有竞品资讯
print("\n[1/4] 抓取竞品资讯...")
fetcher = CompetitorFetcherV2()
competitor_results = fetcher.fetch_all(window_start, window_end)
competitor_items = []
for company, items in competitor_results.items():
    competitor_items.extend(items)
    print(f"  {company}: {len(items)} 条")
print(f"  竞品总计: {len(competitor_items)} 条")

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
if competitor_items:
    for i, item in enumerate(competitor_items, 1):
        print(f"  [竞品 {i}/{len(competitor_items)}] {item.title[:35]}...")
        try:
            item.summary = summarizer.summarize(item.title, item.summary)
            print(f"      ✓ {len(item.summary)} 字")
        except Exception as e:
            print(f"      ✗ 摘要生成失败: {e}")

# 行业摘要
for module, items in industry_items.items():
    for item in items:
        print(f"  [行业-{module}] {item.title[:35]}...")
        try:
            item.summary = summarizer.summarize(item.title, item.summary)
            print(f"      ✓ {len(item.summary)} 字")
        except Exception as e:
            print(f"      ✗ 摘要生成失败: {e}")

# 4. 生成报告
print("\n[4/4] 生成 HTML...")
renderer = HTMLRenderer()
html = renderer.render(competitor_results, industry_items, start_str, end_str)
output_path = renderer.save(html, start_str, end_str)

print(f"\n{'=' * 60}")
print(f"✅ 周报已生成: {output_path}")
print(f"  竞品: {len(competitor_items)} 条")
print(f"  行业: {total_ind} 条")
print(f"  总计: {len(competitor_items) + total_ind} 条")
print('=' * 60)
