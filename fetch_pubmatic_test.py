#!/usr/bin/env python3
"""PubMatic 测试脚本 - 14天窗口 (尝试用 curl)"""
import sys
sys.path.insert(0, 'src')
import re
import subprocess
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from fetchers.base import ContentItem

url = "https://investors.pubmatic.com/news-events/news-releases/"
window_end = datetime(2026, 2, 12)
window_start = window_end - timedelta(days=14)

print("="*70)
print("PubMatic 抓取 - 14天窗口")
print(f"{window_start.date()} ~ {window_end.date()}")
print("="*70)
print("\n⚠️ 注意: PubMatic 网站有访问限制，尝试用 curl...\n")

try:
    result = subprocess.run([
        'curl', '-s', '--http1.1', url,
        '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        '--max-time', '30',
    ], capture_output=True, text=True, timeout=60)
    
    html = result.stdout
    print(f"获取到 HTML: {len(html)} 字符")
    
    if len(html) < 1000:
        print("❌ 内容太短，无法抓取")
    else:
        soup = BeautifulSoup(html, 'html.parser')
        
        # 尝试查找日期
        dates = []
        for elem in soup.find_all(text=re.compile(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}')):
            text = elem.strip()
            if len(text) < 100:
                dates.append(text)
        
        print(f"\n找到 {len(dates)} 个可能日期")
        for d in dates[:5]:
            print(f"  - {d}")
            
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n⚠️ PubMatic 暂时无法抓取，可能需要其他方法")
