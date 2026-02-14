#!/usr/bin/env python3
"""
抓取行业资讯 - 用于 industry-only 分支
抓取 AdExchanger Popular 前 5 条 + Search Engine Land 最新 3 条
"""
import json
import sys
import os
sys.path.insert(0, 'src')

from datetime import datetime, timedelta
from fetchers.industry_fetcher import IndustryFetcher

window_end = datetime.now()
window_start = window_end - timedelta(days=7)

print("="*70)
print("抓取行业资讯")
print(f"时间窗口: {window_start.date()} ~ {window_end.date()}")
print("="*70)

fetcher = IndustryFetcher()
results = fetcher.fetch_all(window_start, window_end)

# 转换为可序列化的格式
output = {}
total = 0
for module_name, items in results.items():
    output[module_name] = [
        {
            'title': item.title,
            'summary': item.summary,
            'date': item.date,
            'url': item.url,
            'source': item.source
        }
        for item in items
    ]
    total += len(items)
    print(f"  {module_name}: {len(items)} 条")

print(f"\n总计: {total} 条")

# 保存结果
os.makedirs('output', exist_ok=True)
output_file = 'output/industry_result.json'
with open(output_file, 'w') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n✅ 完成，保存到: {output_file}")
