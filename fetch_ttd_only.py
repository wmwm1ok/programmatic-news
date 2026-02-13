#!/usr/bin/env python3
"""
抓取 TTD - 使用 HTTP 直接请求（CompetitorFetcherV2）
这是今天上午成功的方案
"""
import json
import sys
import os
sys.path.insert(0, 'src')

from datetime import datetime, timedelta
from fetchers.competitor_fetcher_v2 import CompetitorFetcherV2

window_end = datetime.now()
window_start = window_end - timedelta(days=14)

print("="*70)
print("抓取 TTD (使用 HTTP 直接请求)")
print(f"时间窗口: {window_start.date()} ~ {window_end.date()}")
print("="*70)

fetcher = CompetitorFetcherV2()
items = fetcher._fetch_ttd(window_start, window_end)

# 保存结果
result = {
    'company': 'TTD',
    'items': [{'title': i.title, 'summary': i.summary, 'date': i.date, 'url': i.url, 'source': i.source} for i in items],
    'count': len(items)
}

os.makedirs('output', exist_ok=True)
output_file = 'output/ttd_result.json'
with open(output_file, 'w') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n✅ 完成: {len(items)} 条")
print(f"保存到: {output_file}")
