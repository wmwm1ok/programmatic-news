#!/usr/bin/env python3
"""Zeta Global 测试脚本 - 14天窗口"""
import sys
sys.path.insert(0, 'src')
import re
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from fetchers.base import ContentItem
from summarizer import Summarizer
from renderer import HTMLRenderer

url = "https://investors.zetaglobal.com/news/default.aspx"
window_end = datetime(2026, 2, 12)
window_start = window_end - timedelta(days=14)

print("="*70)
print("Zeta Global 抓取 - 14天窗口")
print(f"{window_start.date()} ~ {window_end.date()}")
print("="*70)

items = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page()
    
    page.goto(url, wait_until="load", timeout=120000)
    page.wait_for_timeout(5000)
    
    html = page.content()
    soup = BeautifulSoup(html, 'html.parser')
    
    date_elems = soup.find_all('div', class_=re.compile('evergreen-item-date-time|evergreen-news-date'))
    print(f"\n找到 {len(date_elems)} 个日期元素\n")
    
    for i, date_elem in enumerate(date_elems):
        date_text = date_elem.get_text(strip=True)
        
        match = re.match(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})', date_text, re.IGNORECASE)
        if not match:
            continue
        
        months = {'january': '01', 'february': '02', 'march': '03', 'april': '04', 'may': '05', 'june': '06',
                 'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12'}
        date_str = f"{match.group(3)}-{months.get(match.group(1).lower(), '01')}-{match.group(2).zfill(2)}"
        
        parent = date_elem.find_parent()
        if not parent:
            continue
        
        link_elem = parent.find('a', href=re.compile('/news/'))
        if not link_elem:
            continue
        
        title = link_elem.get_text(strip=True)
        href = link_elem.get('href', '')
        detail_url = urljoin(url, href)
        
        print(f"[{i+1}] {title[:50]}...")
        print(f"    日期: {date_str}", end="")
        
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        if not (window_start <= date_obj <= window_end):
            print(" -")
            continue
        
        print(" ✅")
        
        detail_page = browser.new_page()
        try:
            detail_page.goto(detail_url, wait_until="load", timeout=30000)
            detail_page.wait_for_timeout(3000)
            
            detail_html = detail_page.content()
            detail_soup = BeautifulSoup(detail_html, 'html.parser')
            
            content = ""
            for selector in ['article', '.content', 'main']:
                elem = detail_soup.select_one(selector)
                if elem:
                    text = elem.get_text(separator=' ', strip=True)
                    if len(text) > 200:
                        content = re.sub(r'\s+', ' ', text)
                        break
            
            if content:
                items.append(ContentItem(title=title, summary=content[:600], date=date_str, url=detail_url, source="Zeta Global"))
                print(f"    ✓ 已添加")
            
            detail_page.close()
        except Exception as e:
            print(f"    ✗ 错误: {e}")
            detail_page.close()
        
        print()
    
    browser.close()

print(f"\n抓取完成: {len(items)} 条")
for item in items:
    print(f"\n日期: {item.date}")
    print(f"标题: {item.title}")

if items:
    print("\n生成报告...")
    summarizer = Summarizer()
    for item in items:
        item.summary = summarizer.summarize(item.title, item.summary)
    
    renderer = HTMLRenderer()
    html = renderer.render({"Zeta Global": items}, {}, window_start.strftime("%Y-%m-%d"), window_end.strftime("%Y-%m-%d"))
    output_path = renderer.save(html, window_start.strftime("%Y-%m-%d"), window_end.strftime("%Y-%m-%d"))
    print(f"✅ 报告: {output_path}")
