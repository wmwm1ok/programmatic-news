#!/usr/bin/env python3
"""
专门抓取 Magnite 的测试脚本
Magnite 有 HTTP2 错误，使用 curl 绕过
日期格式: "February 10, 2026"
时间窗口: 14天内
"""
import sys
sys.path.insert(0, 'src')

import os
import re
import subprocess
from datetime import datetime, timedelta
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from fetchers.base import ContentItem
from summarizer import Summarizer
from renderer import HTMLRenderer

print("="*70)
print("Magnite 专门抓取 - 最近14天")
print("URL: https://investor.magnite.com/press-releases")
print("="*70)

url = "https://investor.magnite.com/press-releases"

# 计算14天前到今天的时间窗口
today = datetime(2026, 2, 12)  # 模拟今天为2月12日
window_start = today - timedelta(days=14)
window_end = today

target_start = window_start.strftime("%Y-%m-%d")
target_end = window_end.strftime("%Y-%m-%d")

print(f"\n时间窗口: {target_start} ~ {target_end}")
print(f"策略: 使用 curl 获取列表页和详情页 (绕过 HTTP2 限制)\n")

items = []
processed_urls = set()

try:
    # 使用 curl 获取列表页
    print("[1] 使用 curl 获取列表页...")
    result = subprocess.run([
        'curl', '-s', url, '--http1.1',
        '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        '-H', 'Accept-Language: en-US,en;q=0.9',
    ], capture_output=True, text=True, timeout=30)
    
    html = result.stdout
    
    if not html or len(html) < 1000:
        print("    ✗ 无法获取页面内容")
        sys.exit(1)
    
    print(f"    ✓ 获取成功 ({len(html)} 字符)")
    
    soup = BeautifulSoup(html, 'html.parser')
    
    print("\n[2] 查找新闻项...")
    
    # 查找新闻项 - 尝试多种选择器
    news_items = []
    selectors = ['.press-item', '.news-item', 'article', '.item', '.views-row', '.node', 'tr']
    for selector in selectors:
        news_items = soup.select(selector)
        if news_items:
            print(f"    使用选择器: {selector}, 找到 {len(news_items)} 个")
            break
    
    print(f"\n[3] 处理新闻项...")
    
    for i, item in enumerate(news_items[:15]):
        try:
            # 查找链接
            link_elem = item.find('a', href=True)
            if not link_elem:
                continue
            
            href = link_elem.get('href', '')
            if not href:
                continue
            
            # 补全 URL
            if href.startswith('/'):
                detail_url = urljoin(url, href)
            elif href.startswith('http'):
                detail_url = href
            else:
                detail_url = urljoin(url, href)
            
            # 去重
            if detail_url in processed_urls:
                continue
            processed_urls.add(detail_url)
            
            title = link_elem.get_text(strip=True)
            if not title or len(title) < 10:
                continue
            
            print(f"\n[{i+1}] {title[:60]}...")
            print(f"    URL: {detail_url[:70]}...")
            
            # 获取日期 - 从列表项中查找
            date_str = ""
            date_elem = item.find('time') or item.find(class_=re.compile('date'))
            
            if date_elem:
                if hasattr(date_elem, 'get_text'):
                    date_text = date_elem.get_text(strip=True)
                else:
                    date_text = str(date_elem)
                
                print(f"    列表页日期文本: {date_text}")
                
                # 解析日期 "February 10, 2026"
                match = re.match(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})', date_text, re.IGNORECASE)
                if match:
                    months = {'january': '01', 'february': '02', 'march': '03', 'april': '04', 'may': '05', 'june': '06',
                             'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12'}
                    month_num = months.get(match.group(1).lower(), '01')
                    date_str = f"{match.group(3)}-{month_num}-{match.group(2).zfill(2)}"
                    print(f"    解析日期: {date_str}")
            
            # 使用 curl 获取详情页
            print(f"    获取详情页...")
            detail_result = subprocess.run([
                'curl', '-s', detail_url, '--http1.1',
                '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            ], capture_output=True, text=True, timeout=30)
            
            detail_html = detail_result.stdout
            
            if not detail_html or 'Access Denied' in detail_html:
                print(f"    ✗ 无法获取详情页")
                continue
            
            detail_soup = BeautifulSoup(detail_html, 'html.parser')
            
            # 如果从列表页没有获取到日期，尝试从详情页获取
            if not date_str:
                date_elem = detail_soup.find('time') or detail_soup.find(class_=re.compile('date'))
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    match = re.match(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})', date_text, re.IGNORECASE)
                    if match:
                        months = {'january': '01', 'february': '02', 'march': '03', 'april': '04', 'may': '05', 'june': '06',
                                 'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12'}
                        month_num = months.get(match.group(1).lower(), '01')
                        date_str = f"{match.group(3)}-{month_num}-{match.group(2).zfill(2)}"
                
                # 备选：从 body 文本查找
                if not date_str:
                    body_text = detail_soup.get_text()[:3000]
                    match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})', body_text, re.IGNORECASE)
                    if match:
                        months = {'january': '01', 'february': '02', 'march': '03', 'april': '04', 'may': '05', 'june': '06',
                                 'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12'}
                        month_num = months.get(match.group(1).lower(), '01')
                        date_str = f"{match.group(3)}-{month_num}-{match.group(2).zfill(2)}"
                
                if date_str:
                    print(f"    详情页日期: {date_str}")
            
            if not date_str:
                print(f"    ✗ 无法获取日期")
                continue
            
            # 检查日期窗口
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            if not (window_start <= date_obj <= window_end):
                print(f"    - 不在时间窗口")
                continue
            
            print(f"    ✅ 在时间窗口内")
            
            # 提取内容
            content = ""
            for selector in ['.content', 'article', '.main-content', '.press-release', '.news-content', 'main', '.field-body', '.body']:
                elem = detail_soup.select_one(selector)
                if elem:
                    text = elem.get_text(separator=' ', strip=True)
                    if len(text) > 200:
                        content = text
                        break
            
            if not content:
                # 备选
                for script in detail_soup(["script", "style", "nav", "header", "footer"]):
                    script.decompose()
                body = detail_soup.find('body')
                if body:
                    content = body.get_text(separator=' ', strip=True)
            
            if content:
                content = re.sub(r'\s+', ' ', content)
                items.append(ContentItem(
                    title=title,
                    summary=content[:600],
                    date=date_str,
                    url=detail_url,
                    source="Magnite"
                ))
                print(f"    ✓ 已添加 ({len(content)} 字符)")
            else:
                print(f"    ✗ 无法提取内容")
                
        except Exception as e:
            print(f"    ✗ 处理出错: {e}")
            continue
            
except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()

# 结果输出
print("\n" + "="*70)
print(f"抓取完成！共 {len(items)} 条")
print("="*70)

for item in items:
    print(f"\n日期: {item.date}")
    print(f"标题: {item.title}")
    print(f"链接: {item.url}")

# 生成报告
if items:
    print("\n[4] 生成报告...")
    try:
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if api_key:
            summarizer = Summarizer()
            for item in items:
                print(f"    生成摘要: {item.title[:40]}...")
                item.summary = summarizer.summarize(item.title, item.summary)
        
        renderer = HTMLRenderer()
        competitor_data = {"Magnite": items}
        html = renderer.render(competitor_data, {}, target_start, target_end)
        output_path = renderer.save(html, target_start, target_end)
        
        print(f"\n✅ 报告已生成: {output_path}")
        
    except Exception as e:
        print(f"    ⚠️ 生成报告失败: {e}")
else:
    print("\n⚠️ 未抓到任何新闻")

print("\n完成!")
