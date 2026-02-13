#!/usr/bin/env python3
"""测试 PubMatic 和 Magnite 抓取器 - 使用 requests Session"""
import sys
sys.path.insert(0, 'src')

import re
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def clean_text(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def parse_date(date_text):
    """解析日期文本"""
    if not date_text:
        return None
    match = re.match(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})', date_text, re.IGNORECASE)
    if match:
        months = {'january': '01', 'february': '02', 'march': '03', 'april': '04', 'may': '05', 'june': '06',
                 'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12'}
        return f"{match.group(3)}-{months.get(match.group(1).lower(), '01')}-{match.group(2).zfill(2)}"
    return None

def is_in_window(date_str, window_start, window_end):
    """检查日期是否在窗口内"""
    if not date_str:
        return False
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return window_start.date() <= date_obj.date() <= window_end.date()
    except:
        return False

def test_pubmatic():
    """测试 PubMatic 抓取"""
    url = "https://investors.pubmatic.com/news-events/news-releases/"
    window_end = datetime(2026, 2, 12)
    window_start = window_end - timedelta(days=14)
    
    print("="*70)
    print("PubMatic 抓取测试 - 使用 requests Session")
    print(f"时间窗口: {window_start.date()} ~ {window_end.date()}")
    print(f"URL: {url}")
    print("="*70)
    
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        
        print("\n[1] 获取列表页...")
        resp = session.get(url, timeout=30)
        print(f"    状态码: {resp.status_code}")
        print(f"    内容长度: {len(resp.text)} 字符")
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 查找新闻条目
        cards = []
        selectors = ['.news-item', '.press-release', 'article', 'tr', '.wd_item']
        for selector in selectors:
            elems = soup.select(selector)
            print(f"    选择器 '{selector}': {len(elems)} 个元素")
            for card in elems:
                link = card.find('a', href=True)
                if not link:
                    continue
                
                title = clean_text(link.get_text())
                if not title or len(title) < 10:
                    continue
                
                href = link.get('href', '')
                detail_url = urljoin(url, href)
                
                # 查找日期
                date_text = ""
                date_elem = card.find('time') or card.find(class_=re.compile('date|published|wd_date'))
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                
                if title and href:
                    cards.append((title, detail_url, date_text))
        
        print(f"\n[2] 找到 {len(cards)} 个新闻条目")
        
        items = []
        for title, detail_url, date_text in cards[:5]:
            date_str = parse_date(date_text)
            in_window = is_in_window(date_str, window_start, window_end) if date_str else False
            
            print(f"\n    标题: {title[:60]}...")
            print(f"    链接: {detail_url[:70]}...")
            print(f"    日期文本: {date_text}")
            print(f"    解析日期: {date_str}")
            print(f"    在窗口内: {'✅' if in_window else '❌'}")
            
            if in_window:
                try:
                    print(f"    [3] 获取详情页...", end="")
                    detail_resp = session.get(detail_url, timeout=30)
                    detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')
                    
                    content = ""
                    for selector in ['article', '.content', 'main', '.press-release', '.wd_body']:
                        elem = detail_soup.select_one(selector)
                        if elem:
                            text = elem.get_text(separator=' ', strip=True)
                            if len(text) > 200:
                                content = clean_text(text)
                                break
                    
                    if content:
                        items.append({
                            'title': title,
                            'date': date_str,
                            'url': detail_url,
                            'content_preview': content[:200]
                        })
                        print(f" ✅ 成功 ({len(content)} 字符)")
                    else:
                        print(f" ⚠️ 内容为空")
                except Exception as e:
                    print(f" ❌ 错误: {e}")
        
        print(f"\n[4] 结果: 成功抓取 {len(items)} 条")
        for item in items:
            print(f"\n    📰 {item['title'][:50]}...")
            print(f"       日期: {item['date']}")
            print(f"       预览: {item['content_preview'][:100]}...")
        
        return len(items) > 0
        
    except Exception as e:
        print(f"\n❌ PubMatic 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_magnite():
    """测试 Magnite 抓取"""
    url = "https://investor.magnite.com/press-releases"
    window_end = datetime(2026, 2, 12)
    window_start = window_end - timedelta(days=14)
    
    print("\n" + "="*70)
    print("Magnite 抓取测试 - 使用 requests Session")
    print(f"时间窗口: {window_start.date()} ~ {window_end.date()}")
    print(f"URL: {url}")
    print("="*70)
    
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        
        print("\n[1] 获取列表页...")
        resp = session.get(url, timeout=30)
        print(f"    状态码: {resp.status_code}")
        print(f"    内容长度: {len(resp.text)} 字符")
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 查找新闻条目
        cards = []
        selectors = ['.press-release-item', '.news-item', '.press-item', 'article', 'tr', '.wd_item']
        for selector in selectors:
            elems = soup.select(selector)
            print(f"    选择器 '{selector}': {len(elems)} 个元素")
            for card in elems:
                link = card.find('a', href=True)
                if not link:
                    continue
                
                title = clean_text(link.get_text())
                if not title or len(title) < 10:
                    continue
                
                href = link.get('href', '')
                detail_url = urljoin(url, href)
                
                # 查找日期
                date_text = ""
                date_elem = card.find('time') or card.find(class_=re.compile('date|published|wd_date'))
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                
                if title and href:
                    cards.append((title, detail_url, date_text))
        
        print(f"\n[2] 找到 {len(cards)} 个新闻条目")
        
        items = []
        for title, detail_url, date_text in cards[:5]:
            date_str = parse_date(date_text)
            
            # 从URL尝试提取日期作为备选
            if not date_str:
                url_match = re.search(r'/(\d{4})[-/](\d{2})[-/](\d{2})/', detail_url)
                if url_match:
                    date_str = f"{url_match.group(1)}-{url_match.group(2)}-{url_match.group(3)}"
            
            in_window = is_in_window(date_str, window_start, window_end) if date_str else False
            
            print(f"\n    标题: {title[:60]}...")
            print(f"    链接: {detail_url[:70]}...")
            print(f"    日期文本: {date_text}")
            print(f"    解析日期: {date_str}")
            print(f"    在窗口内: {'✅' if in_window else '❌'}")
            
            if in_window:
                try:
                    print(f"    [3] 获取详情页...", end="")
                    detail_resp = session.get(detail_url, timeout=30)
                    detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')
                    
                    content = ""
                    for selector in ['article', '.content', 'main', '.press-release', '.wd_body']:
                        elem = detail_soup.select_one(selector)
                        if elem:
                            text = elem.get_text(separator=' ', strip=True)
                            if len(text) > 200:
                                content = clean_text(text)
                                break
                    
                    if content:
                        items.append({
                            'title': title,
                            'date': date_str,
                            'url': detail_url,
                            'content_preview': content[:200]
                        })
                        print(f" ✅ 成功 ({len(content)} 字符)")
                    else:
                        print(f" ⚠️ 内容为空")
                except Exception as e:
                    print(f" ❌ 错误: {e}")
        
        print(f"\n[4] 结果: 成功抓取 {len(items)} 条")
        for item in items:
            print(f"\n    📰 {item['title'][:50]}...")
            print(f"       日期: {item['date']}")
            print(f"       预览: {item['content_preview'][:100]}...")
        
        return len(items) > 0
        
    except Exception as e:
        print(f"\n❌ Magnite 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n" + "="*70)
    print("PubMatic & Magnite 抓取器测试")
    print("="*70)
    
    pubmatic_ok = test_pubmatic()
    magnite_ok = test_magnite()
    
    print("\n" + "="*70)
    print("测试结果汇总")
    print("="*70)
    print(f"PubMatic: {'✅ 成功' if pubmatic_ok else '❌ 失败'}")
    print(f"Magnite:  {'✅ 成功' if magnite_ok else '❌ 失败'}")
    print("="*70)
