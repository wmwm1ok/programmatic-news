#!/usr/bin/env python3
"""测试行业资讯抓取"""
import sys
sys.path.insert(0, 'src')

from datetime import datetime, timedelta
from fetchers.industry_fetcher import IndustryFetcher

window_end = datetime(2026, 2, 12)
window_start = window_end - timedelta(days=7)  # 行业资讯用7天窗口

print("="*70)
print("测试行业资讯抓取")
print(f"时间窗口: {window_start.date()} ~ {window_end.date()}")
print("="*70)

fetcher = IndustryFetcher()
results = fetcher.fetch_all(window_start, window_end)

print("\n" + "="*70)
print("测试结果汇总")
print("="*70)

total = 0
for module_name, items in results.items():
    print(f"\n【{module_name}】: {len(items)} 条")
    total += len(items)
    for item in items:
        print(f"  📰 {item.title[:65]}...")
        print(f"     📅 {item.date} | 🔗 {item.url[:50]}...")

print("\n" + "="*70)
print(f"总计: {total} 条")
print("="*70)
