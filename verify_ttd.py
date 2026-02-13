#!/usr/bin/env python3
"""验证TTD抓取 - 扩大日期窗口来测试"""
import sys
sys.path.insert(0, 'src')

from datetime import datetime, timedelta
from fetchers.competitor_fetcher_v2 import CompetitorFetcherV2

print("="*60)
print("TTD 抓取验证")
print("="*60)

# 测试1：当前窗口（2月6日-13日）
print("\n[测试1] 当前窗口（2月6日-13日）:")
window_end = datetime.now().replace(hour=23, minute=59, second=59)
window_start = (window_end - timedelta(days=7)).replace(hour=0, minute=0, second=0)
print(f"窗口: {window_start.date()} ~ {window_end.date()}")

fetcher = CompetitorFetcherV2()
items = fetcher._fetch_ttd("https://www.thetradedesk.com/press-room", window_start, window_end)
print(f"抓到 {len(items)} 条")

# 测试2：扩大窗口到1月1日-2月13日（应该能抓到1月的新闻）
print("\n[测试2] 扩大窗口（1月1日-2月13日）:")
window_start = datetime(2026, 1, 1)
window_end = datetime(2026, 2, 13, 23, 59, 59)
print(f"窗口: {window_start.date()} ~ {window_end.date()}")

items = fetcher._fetch_ttd("https://www.thetradedesk.com/press-room", window_start, window_end)
print(f"抓到 {len(items)} 条")

if items:
    print("\n抓到的新闻:")
    for item in items:
        print(f"  - [{item.date}] {item.title[:60]}...")
    print("\n✅ TTD 抓取逻辑正常！")
else:
    print("\n❌ 未抓到任何新闻")

print("="*60)
