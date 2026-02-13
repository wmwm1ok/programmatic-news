#!/usr/bin/env python3
"""测试抓取 AdExchanger Popular 列表"""
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

url = 'https://www.adexchanger.com/'
print(f'Fetching {url}...')
resp = requests.get(url, timeout=30, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'})
resp.raise_for_status()

soup = BeautifulSoup(resp.text, 'html.parser')

# 找 Popular 区块
popular_heading = soup.find(['h2', 'h3', 'h4'], string=re.compile('popular', re.I))
if not popular_heading:
    # 尝试找 section-title 包含 Popular
    popular_heading = soup.find(class_=re.compile('section-title'), string=re.compile('popular', re.I))

print(f'\n=== Popular Section ===')
if popular_heading:
    print(f'Found: {popular_heading.get_text(strip=True)}')
    
    # 找父元素中的有序列表
    parent = popular_heading.find_parent(['aside', 'div', 'section'])
    if parent:
        ol = parent.find('ol', class_=re.compile('list-ordered'))
        if ol:
            items = ol.find_all('li', limit=5)
            print(f'\n找到 {len(items)} 条 Popular 文章:\n')
            
            for i, li in enumerate(items, 1):
                link = li.find('a', class_='link-post')
                if link:
                    title = link.get_text(strip=True)
                    href = link.get('href', '')
                    # 找分类
                    category_elem = li.find('a', class_='link-label')
                    category = category_elem.get_text(strip=True) if category_elem else 'N/A'
                    
                    print(f'[{i}] {title}')
                    print(f'    Category: {category}')
                    print(f'    URL: {href}')
                    print()
else:
    print('Popular section not found, trying alternative...')
    # 直接找所有 link-post
    links = soup.find_all('a', class_='link-post', limit=10)
    for i, link in enumerate(links[:5], 1):
        title = link.get_text(strip=True)
        href = link.get('href', '')
        print(f'[{i}] {title}')
        print(f'    URL: {href}')
        print()
