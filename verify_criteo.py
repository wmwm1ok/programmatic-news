#!/usr/bin/env python3
"""
单独验证 Criteo 抓取
目标：抓取 Feb 5 和 Feb 11, 2026 的新闻
"""
import sys
sys.path.insert(0, 'src')

from datetime import datetime
from fetchers.stealth_fetcher import StealthFetcher

print("="*70)
print("Criteo 抓取验证")
print("目标日期: Feb 5, 2026 和 Feb 11, 2026")
print("="*70)

# 设置日期窗口
window_start = datetime(2026, 2, 1)
window_end = datetime(2026, 2, 15, 23, 59, 59)

print(f"\n日期窗口: {window_start.date()} ~ {window_end.date()}")
print("开始抓取...\n")

fetcher = StealthFetcher()
items = fetcher.fetch_criteo(window_start, window_end)
fetcher.close()

print(f"\n{'='*70}")
print(f"抓取完成！总共: {len(items)} 条")
print('='*70)

# 检查结果
feb5 = [i for i in items if i.date == '2026-02-05']
feb11 = [i for i in items if i.date == '2026-02-11']

if feb5:
    print(f"\n✅ Feb 5, 2026 ({len(feb5)} 条):")
    for item in feb5:
        print(f"   - {item.title}")
else:
    print(f"\n❌ Feb 5, 2026: 未抓到")

if feb11:
    print(f"\n✅ Feb 11, 2026 ({len(feb11)} 条):")
    for item in feb11:
        print(f"   - {item.title}")
else:
    print(f"\n❌ Feb 11, 2026: 未抓到")

if items:
    print(f"\n所有抓到的新闻:")
    for item in items:
        print(f"   [{item.date}] {item.title[:60]}...")
else:
    print(f"\n⚠️ 未抓到任何新闻")

print('='*70)
