#!/usr/bin/env python3
"""测试 PubMatic 和 Magnite 抓取器 - 使用 curl 详细模式"""
import sys
sys.path.insert(0, 'src')

import re
import subprocess
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

def fetch_with_curl(url, timeout=60):
    """使用 curl 获取页面"""
    try:
        result = subprocess.run([
            'curl', '-s', '-L', '--http1.1', url,
            '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            '-H', 'Accept-Language: en-US,en;q=0.9',
            '-H', 'Accept-Encoding: gzip, deflate, br',
            '-H', 'Connection: keep-alive',
            '-H', 'Upgrade-Insecure-Requests: 1',
            '-H', 'Sec-Fetch-Dest: document',
            '-H', 'Sec-Fetch-Mode: navigate',
            '-H', 'Sec-Fetch-Site: none',
            '-H', 'Cache-Control: max-age=0',
            '--max-time', str(timeout),
            '--compressed',
        ], capture_output=True, text=True, timeout=timeout+10)
        
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return None, str(e), -1

def test_site(name, url, window_start, window_end):
    """测试网站抓取"""
    print("\n" + "="*70)
    print(f"{name} 抓取测试 - 使用 curl")
    print(f"时间窗口: {window_start.date()} ~ {window_end.date()}")
    print(f"URL: {url}")
    print("="*70)
    
    print(f"\n[1] 获取列表页...")
    html, stderr, code = fetch_with_curl(url, timeout=60)
    
    print(f"    返回码: {code}")
    print(f"    内容长度: {len(html) if html else 0} 字符")
    
    if stderr:
        print(f"    错误信息: {stderr[:200]}")
    
    if not html or len(html) < 1000:
        print(f"    ❌ 无法获取有效内容")
        return False
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # 显示页面标题
    title = soup.find('title')
    if title:
        print(f"    页面标题: {title.get_text(strip=True)}")
    
    # 尝试多种选择器查找新闻
    cards = []
    selectors = [
        ('.wd_item', 'wd_item'),
        ('.news-item', 'news-item'),
        ('.press-release', 'press-release'),
        ('article', 'article'),
        ('tr', 'tr'),
        ('.item', 'item'),
        ('.release', 'release'),
    ]
    
    for selector, label in selectors:
        elems = soup.select(selector)
        if elems:
            print(f"    选择器 '{selector}' ({label}): {len(elems)} 个元素")
            for card in elems[:3]:  # 只显示前3个
                link = card.find('a', href=True)
                if link:
                    title_text = clean_text(link.get_text())
                    href = link.get('href', '')
                    print(f"      - {title_text[:50]}... | {href[:50]}...")
                    
                    date_elem = card.find('time') or card.find(class_=re.compile('date'))
                    if date_elem:
                        print(f"        日期: {date_elem.get_text(strip=True)}")
        
        for card in elems:
            link = card.find('a', href=True)
            if not link:
                continue
            
            title_text = clean_text(link.get_text())
            if not title_text or len(title_text) < 10:
                continue
            
            href = link.get('href', '')
            detail_url = urljoin(url, href)
            
            date_text = ""
            date_elem = card.find('time') or card.find(class_=re.compile('date|published'))
            if date_elem:
                date_text = date_elem.get_text(strip=True)
            
            if title_text and href:
                cards.append((title_text, detail_url, date_text))
    
    # 如果没有找到，尝试直接查找所有链接
    if not cards:
        print(f"\n[2] 尝试直接查找所有链接...")
        all_links = soup.find_all('a', href=True)
        print(f"    找到 {len(all_links)} 个链接")
        
        for link in all_links:
            href = link.get('href', '')
            text = clean_text(link.get_text())
            
            # 只保留看起来像新闻的链接
            if '/news/' in href or '/press/' in href or '/release/' in href:
                if text and len(text) > 10 and len(text) < 200:
                    detail_url = urljoin(url, href)
                    cards.append((text, detail_url, ""))
    
    print(f"\n[3] 共找到 {len(cards)} 个新闻条目")
    
    # 显示前5个
    for i, (title, detail_url, date_text) in enumerate(cards[:5]):
        date_str = parse_date(date_text)
        print(f"\n    [{i+1}] {title[:60]}...")
        print(f"        链接: {detail_url[:70]}...")
        print(f"        日期: {date_text} -> {date_str}")
    
    return len(cards) > 0

if __name__ == "__main__":
    window_end = datetime(2026, 2, 12)
    window_start = window_end - timedelta(days=14)
    
    print("\n" + "="*70)
    print("PubMatic & Magnite 抓取器测试 - curl 方式")
    print("="*70)
    
    # PubMatic
    pubmatic_url = "https://investors.pubmatic.com/news-events/news-releases/"
    pubmatic_ok = test_site("PubMatic", pubmatic_url, window_start, window_end)
    
    # Magnite
    magnite_url = "https://investor.magnite.com/press-releases"
    magnite_ok = test_site("Magnite", magnite_url, window_start, window_end)
    
    print("\n" + "="*70)
    print("测试结果汇总")
    print("="*70)
    print(f"PubMatic: {'✅ 成功' if pubmatic_ok else '❌ 失败'}")
    print(f"Magnite:  {'✅ 成功' if magnite_ok else '❌ 失败'}")
    print("="*70)
