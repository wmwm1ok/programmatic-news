#!/usr/bin/env python3
"""测试使用 Google News 抓取 PubMatic 和 Magnite"""
import sys
sys.path.insert(0, 'src')

import os
import re
import requests
from datetime import datetime, timedelta
from urllib.parse import quote_plus

def clean_text(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def parse_news_date(text, end_date):
    """解析相对日期文本"""
    if not text:
        return None
    text = text.lower().strip()
    
    # 处理 "X hours ago", "X days ago" 等
    if 'hour' in text or 'min' in text:
        return end_date.strftime('%Y-%m-%d')
    
    match = re.search(r'(\d+)\s+day', text)
    if match:
        days = int(match.group(1))
        date = end_date - timedelta(days=days)
        return date.strftime('%Y-%m-%d')
    
    # 尝试标准格式
    try:
        from dateutil import parser as dateparser
        dt = dateparser.parse(text, fuzzy=True)
        if dt:
            return dt.strftime('%Y-%m-%d')
    except:
        pass
    
    return None

def fetch_google_news_rss(query, window_start, window_end):
    """使用 Google News RSS 获取新闻"""
    items = []
    
    try:
        # 构建 RSS URL
        q = quote_plus(query)
        url = f"https://news.google.com/rss/search?q={q}&hl=en&gl=US&ceid=US:en"
        
        print(f"    请求: {url[:80]}...")
        
        resp = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        })
        resp.raise_for_status()
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, 'xml')
        
        for item in soup.find_all('item'):
            title = clean_text(item.title.get_text() if item.title else "")
            link = clean_text(item.link.get_text() if item.link else "")
            pub_date = clean_text(item.pubDate.get_text() if item.pubDate else "")
            
            if not title or not link:
                continue
            
            # 解析日期
            date_str = None
            if pub_date:
                try:
                    dt = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %Z')
                    date_str = dt.strftime('%Y-%m-%d')
                except:
                    date_str = parse_news_date(pub_date, window_end)
            
            if not date_str:
                date_str = window_end.strftime('%Y-%m-%d')
            
            items.append({
                'title': title,
                'url': link,
                'date': date_str,
                'source': 'Google News'
            })
        
        return items, None
        
    except Exception as e:
        return [], str(e)

def test_google_news(company_name, query, window_start, window_end):
    """测试 Google News 抓取"""
    print(f"\n{'='*70}")
    print(f"{company_name} - Google News 抓取测试")
    print(f"查询: {query}")
    print(f"时间窗口: {window_start.date()} ~ {window_end.date()}")
    print(f"{'='*70}")
    
    items, error = fetch_google_news_rss(query, window_start, window_end)
    
    if error:
        print(f"    ❌ 错误: {error}")
        return False
    
    print(f"    找到 {len(items)} 条新闻")
    
    # 筛选在时间窗口内的新闻
    valid_items = []
    for item in items:
        try:
            item_date = datetime.strptime(item['date'], '%Y-%m-%d')
            if window_start.date() <= item_date.date() <= window_end.date():
                valid_items.append(item)
        except:
            pass
    
    print(f"    在时间窗口内: {len(valid_items)} 条")
    
    for i, item in enumerate(valid_items[:5]):
        print(f"\n    [{i+1}] {item['title'][:60]}...")
        print(f"        日期: {item['date']}")
        print(f"        链接: {item['url'][:70]}...")
    
    return len(valid_items) > 0

if __name__ == "__main__":
    window_end = datetime(2026, 2, 12)
    window_start = window_end - timedelta(days=14)
    
    print("="*70)
    print("Google News 抓取测试 - PubMatic & Magnite")
    print("="*70)
    
    # PubMatic
    pubmatic_ok = test_google_news(
        "PubMatic", 
        "PubMatic news press release", 
        window_start, 
        window_end
    )
    
    # Magnite
    magnite_ok = test_google_news(
        "Magnite", 
        "Magnite advertising news press release", 
        window_start, 
        window_end
    )
    
    print("\n" + "="*70)
    print("测试结果汇总")
    print("="*70)
    print(f"PubMatic (Google News): {'✅ 成功' if pubmatic_ok else '❌ 失败'}")
    print(f"Magnite (Google News):  {'✅ 成功' if magnite_ok else '❌ 失败'}")
    print("="*70)
