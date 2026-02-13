#!/usr/bin/env python3
"""测试新闻去重功能"""
import sys
sys.path.insert(0, 'src')

from datetime import datetime, timedelta
from fetchers.stealth_fetcher import StealthFetcher

# 模拟测试去重功能
stealth = StealthFetcher()

# 测试标题相似度计算
test_cases = [
    (
        "Unity Software's Shares Fall On Disappointing Q1 Guide, ironSource Headwind",
        "Unity Software Shares Fall On Q1 Guide, ironSource Headwind",
        "相同新闻，略有不同的标题"
    ),
    (
        "PubMatic Appoints Marketing Veteran John Petralia as Chief Marketing Officer",
        "PubMatic Appoints John Petralia as Chief Marketing Officer",
        "相同新闻，略有不同的标题"
    ),
    (
        "New York Times opens mobile app ad access to brands via Magnite",
        "NYT opens mobile ad inventory to brands through Magnite partnership",
        "相同新闻，不同表述"
    ),
    (
        "Unity targets $1B+ annual run rate for Vector by end of 2026",
        "Unity's Vector platform aims for $1 billion revenue milestone",
        "相同新闻，不同表述"
    ),
    (
        "Apple announces new iPhone",
        "Google launches new Android update", 
        "完全不同的新闻"
    ),
]

print("="*70)
print("测试标题相似度计算")
print("="*70)

for title1, title2, desc in test_cases:
    similarity = stealth._title_similarity(title1, title2)
    is_duplicate = "🔴 重复" if similarity >= 0.6 else "✅ 不同"
    print(f"\n{desc}:")
    print(f"  标题1: {title1[:60]}...")
    print(f"  标题2: {title2[:60]}...")
    print(f"  相似度: {similarity:.2f} {is_duplicate}")

# 测试完整抓取流程
print("\n" + "="*70)
print("测试完整抓取（含去重）")
print("="*70)

window_end = datetime(2026, 2, 12)
window_start = window_end - timedelta(days=14)

print("\n【1】PubMatic 抓取")
print("-"*70)
pubmatic_items = stealth.fetch_pubmatic(window_start, window_end)

print("\n【2】Magnite 抓取")  
print("-"*70)
magnite_items = stealth.fetch_magnite(window_start, window_end)

print("\n【3】Unity 抓取（广告相关）")
print("-"*70)
unity_items = stealth.fetch_unity(window_start, window_end)

stealth.close()

print("\n" + "="*70)
print("测试结果汇总")
print("="*70)
print(f"✅ PubMatic: {len(pubmatic_items)} 条")
print(f"✅ Magnite:  {len(magnite_items)} 条")
print(f"✅ Unity:    {len(unity_items)} 条 (广告相关，已去重)")
print("="*70)
print(f"总计: {len(pubmatic_items) + len(magnite_items) + len(unity_items)} 条")
