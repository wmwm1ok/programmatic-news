#!/usr/bin/env python3
"""
整合脚本 - 只负责整合各分支的结果并发送邮件
不进行任何抓取操作
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, 'src')

from fetchers.base import ContentItem
from renderer import HTMLRenderer
from email_sender import send_weekly_report


def load_company_results():
    """加载各公司抓取的结果"""
    artifacts_dir = Path('artifacts')
    results = {}
    
    if not artifacts_dir.exists():
        print("⚠️ No artifacts directory found")
        return results
    
    for json_file in artifacts_dir.glob('*-result.json'):
        # 跳过行业资讯结果
        if json_file.name == 'industry_result.json':
            continue
            
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                company = data.get('company')
                items = data.get('items', [])
                if company and items:
                    results[company] = [ContentItem(**item) for item in items]
                    print(f"  ✓ {company}: {len(items)} 条")
        except Exception as e:
            print(f"  ✗ Error loading {json_file}: {e}")
    
    return results


def load_industry_results():
    """加载行业资讯结果"""
    artifacts_dir = Path('artifacts')
    industry_file = artifacts_dir / 'industry_result.json'
    
    if not industry_file.exists():
        print("⚠️ No industry result found")
        return {}
    
    try:
        with open(industry_file, 'r') as f:
            data = json.load(f)
        
        # 转换回 ContentItem 对象
        results = {}
        total = 0
        for module_name, items in data.items():
            results[module_name] = [ContentItem(**item) for item in items]
            total += len(items)
            print(f"  ✓ {module_name}: {len(items)} 条")
        
        print(f"  行业总计: {total} 条")
        return results
        
    except Exception as e:
        print(f"  ✗ Error loading industry result: {e}")
        return {}


def main():
    print("=" * 70)
    print("周报整合系统 - 纯整合模式")
    print("=" * 70)
    
    # 计算日期窗口
    window_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
    window_start = (window_end - timedelta(days=14)).replace(hour=0, minute=0, second=0, microsecond=0)
    start_str = str(window_start.date())
    end_str = str(window_end.date())
    
    print(f"\n📅 报告周期: {start_str} ~ {end_str}")
    
    # 检查邮件配置
    email_username = os.getenv('EMAIL_USERNAME')
    email_password = os.getenv('EMAIL_PASSWORD')
    send_email = bool(email_username and email_password)
    
    if send_email:
        print(f"✓ 邮件配置就绪")
    else:
        print("⚠️ 邮件未配置，将只生成报告")
    
    # 1. 加载竞品资讯
    print("\n[1/3] 加载竞品资讯...")
    competitor_results = load_company_results()
    competitor_items = []
    for company, items in competitor_results.items():
        competitor_items.extend(items)
    print(f"  竞品总计: {len(competitor_items)} 条")
    
    # 2. 加载行业资讯
    print("\n[2/3] 加载行业资讯...")
    industry_results = load_industry_results()
    total_ind = sum(len(v) for v in industry_results.values())
    
    # 3. 生成 HTML 报告
    print("\n[3/3] 生成 HTML 报告...")
    try:
        renderer = HTMLRenderer()
        html = renderer.render(competitor_results, industry_results, start_str, end_str)
        
        # 保存到本地
        output_path = renderer.save(html, start_str, end_str)
        print(f"\n✅ 报告已保存: {output_path}")
        
        # 发送邮件
        if send_email:
            print("\n📧 发送邮件...")
            success = send_weekly_report(html, start_str, end_str)
            if success:
                print("\n" + "=" * 70)
                print("✅ 周报生成并发送成功!")
                print("=" * 70)
            else:
                print("\n⚠️ 邮件发送失败")
        else:
            print("\n" + "=" * 70)
            print("✅ 周报已生成")
            print("=" * 70)
        
        print(f"\n统计:")
        print(f"  竞品资讯: {len(competitor_items)} 条")
        print(f"  行业资讯: {total_ind} 条")
        print(f"  总计: {len(competitor_items) + total_ind} 条")
        
    except Exception as e:
        print(f"❌ 生成报告失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
