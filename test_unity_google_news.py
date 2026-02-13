#!/usr/bin/env python3
"""测试 Unity 使用 Google News RSS 抓取 - 过滤广告相关新闻"""
import sys
sys.path.insert(0, 'src')

import re
import requests
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

def clean_text(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def is_ad_related(title):
    """检查标题是否与广告相关"""
    title_lower = title.lower()
    
    # 广告相关关键词
    ad_keywords = [
        'ad', 'ads', 'advertising', 'advertisement',
        'monetization', 'monetize',
        'monetisation', 'monetise',
        'programmatic',
        'dsp', 'ssp', 'exchange',
        'revenue', ' monet',
        'campaign', 'targeting',
        'attribution',
        'banner', 'interstitial', 'rewarded',
        'mediation', 'bidding',
        'growth', 'ua', 'user acquisition',
        'app store', 'aso',
    ]
    
    # 排除游戏引擎/开发相关的新闻
    exclude_keywords = [
        'game engine',
        'render',
        'graphics',
        'shader',
        'unity 6',
        'unity 5',
        'unity 3d',
        'tutorial',
        'asset store',
        'indie game',
        'game development',
        'unity learn',
        'unity forum',
    ]
    
    # 检查是否包含广告关键词
    is_ad = any(kw in title_lower for kw in ad_keywords)
    
    # 检查是否包含排除关键词
    is_excluded = any(kw in title_lower for kw in exclude_keywords)
    
    return is_ad and not is_excluded

def fetch_google_news_rss(query, window_start, window_end, max_items=10):
    """使用 Google News RSS 获取新闻"""
    items = []
    
    try:
        url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en&gl=US&ceid=US:en"
        print(f"    请求: {url[:100]}...")
        
        resp = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        })
        resp.raise_for_status()
        
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
                    date_match = re.search(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})', pub_date)
                    if date_match:
                        months = {'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
                                 'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'}
                        date_str = f"{date_match.group(3)}-{months.get(date_match.group(2).lower(), '01')}-{date_match.group(1).zfill(2)}"
            
            if not date_str:
                date_str = window_end.strftime('%Y-%m-%d')
            
            items.append({
                'title': title,
                'url': link,
                'date': date_str,
                'is_ad_related': is_ad_related(title)
            })
            
            if len(items) >= max_items:
                break
        
        return items, None
        
    except Exception as e:
        return [], str(e)

def test_unity_queries():
    """测试不同的 Unity 查询词"""
    window_end = datetime(2026, 2, 12)
    window_start = window_end - timedelta(days=14)
    
    queries = [
        "Unity advertising",
        "Unity monetization",
        "Unity Ads",
        "Unity programmatic",
        "Unity Grow",
        "Unity monetize",
    ]
    
    print("="*70)
    print("Unity Google News 抓取测试 - 不同查询词对比")
    print(f"时间窗口: {window_start.date()} ~ {window_end.date()}")
    print("="*70)
    
    all_items = []
    
    for query in queries:
        print(f"\n{'='*70}")
        print(f"查询: {query}")
        print('='*70)
        
        items, error = fetch_google_news_rss(query, window_start, window_end, max_items=10)
        
        if error:
            print(f"    ❌ 错误: {error}")
            continue
        
        print(f"    找到 {len(items)} 条新闻")
        
        # 分类统计
        ad_related = [i for i in items if i['is_ad_related']]
        not_ad_related = [i for i in items if not i['is_ad_related']]
        
        print(f"    ✅ 广告相关: {len(ad_related)} 条")
        print(f"    ❌ 非广告相关: {len(not_ad_related)} 条")
        
        if ad_related:
            print(f"\n    广告相关新闻:")
            for i, item in enumerate(ad_related[:3], 1):
                print(f"      [{i}] {item['title'][:70]}...")
                print(f"          日期: {item['date']}")
                all_items.append(item)
        
        if not_ad_related:
            print(f"\n    非广告相关新闻 (示例):")
            for i, item in enumerate(not_ad_related[:2], 1):
                print(f"      [{i}] {item['title'][:70]}...")
    
    # 去重
    seen_urls = set()
    unique_items = []
    for item in all_items:
        if item['url'] not in seen_urls:
            seen_urls.add(item['url'])
            unique_items.append(item)
    
    # 筛选在时间窗口内的
    valid_items = []
    for item in unique_items:
        try:
            item_date = datetime.strptime(item['date'], '%Y-%m-%d')
            if window_start.date() <= item_date.date() <= window_end.date():
                valid_items.append(item)
        except:
            pass
    
    print(f"\n{'='*70}")
    print("汇总结果")
    print(f"{'='*70}")
    print(f"去重后广告相关新闻: {len(valid_items)} 条")
    
    for i, item in enumerate(valid_items[:10], 1):
        print(f"\n  [{i}] {item['title']}")
        print(f"      日期: {item['date']}")
        print(f"      链接: {item['url'][:70]}...")
    
    return valid_items

if __name__ == "__main__":
    items = test_unity_queries()
