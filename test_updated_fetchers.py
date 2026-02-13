#!/usr/bin/env python3
"""测试更新后的 PubMatic 和 Magnite 抓取器"""
import sys
sys.path.insert(0, 'src')

from datetime import datetime, timedelta
from fetchers.stealth_fetcher import StealthFetcher

window_end = datetime(2026, 2, 12)
window_start = window_end - timedelta(days=14)

print("="*70)
print("测试更新后的 PubMatic 和 Magnite 抓取器")
print(f"时间窗口: {window_start.date()} ~ {window_end.date()}")
print("="*70)

stealth = StealthFetcher()

# 测试 PubMatic
print("\n" + "="*70)
print("测试 PubMatic 抓取器")
print("="*70)
pubmatic_items = stealth.fetch_pubmatic(window_start, window_end)
print(f"\n✅ PubMatic: 成功抓取 {len(pubmatic_items)} 条")
for item in pubmatic_items:
    print(f"  - {item.title[:60]}... ({item.date})")

# 测试 Magnite
print("\n" + "="*70)
print("测试 Magnite 抓取器")
print("="*70)
magnite_items = stealth.fetch_magnite(window_start, window_end)
print(f"\n✅ Magnite: 成功抓取 {len(magnite_items)} 条")
for item in magnite_items:
    print(f"  - {item.title[:60]}... ({item.date})")

stealth.close()

print("\n" + "="*70)
print("测试结果汇总")
print("="*70)
print(f"PubMatic: {len(pubmatic_items)} 条")
print(f"Magnite:  {len(magnite_items)} 条")
print("="*70)
