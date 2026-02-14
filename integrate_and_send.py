#!/usr/bin/env python3
"""
整合脚本 - 只负责整合各分支的结果并发送邮件
不进行任何抓取操作
"""

import json
import os
import re
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
    
    # 查找所有 JSON 文件（包括子目录）
    json_files = list(artifacts_dir.glob('**/*_result.json'))
    print(f"  找到 {len(json_files)} 个结果文件")
    
    for json_file in json_files:
        # 跳过行业资讯结果
        if 'industry' in json_file.name:
            continue
            
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                company = data.get('company')
                items = data.get('items', [])
                if company:
                    results[company] = [ContentItem(**item) for item in items]
                    print(f"  ✓ {company}: {len(items)} 条")
        except Exception as e:
            print(f"  ✗ Error loading {json_file}: {e}")
    
    return results


def load_industry_results():
    """加载行业资讯结果"""
    artifacts_dir = Path('artifacts')
    
    # 查找行业资讯文件
    industry_files = list(artifacts_dir.glob('**/industry_result.json'))
    
    if not industry_files:
        print("⚠️ No industry result found")
        return {}
    
    industry_file = industry_files[0]
    
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


def generate_chinese_title_summary(title, summary):
    """使用 DeepSeek 生成中文标题和摘要"""
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        return title, summary[:200] if summary else "无摘要"
    
    try:
        from openai import OpenAI
        
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        
        prompt = f"""请将以下英文新闻标题和内容翻译成中文。

原标题：{title}

内容：{summary[:500]}

翻译要求：
1. 人名、公司名、品牌名、股票代码、产品名等专有名词保留英文，不要翻译
2. 例如：The Trade Desk/TTD、Criteo、Unity、AppLovin、Google、AI、CEO 等保留原样
3. 只翻译普通词汇和语句

请按以下格式返回：
中文标题：[翻译后的标题]
中文摘要：[80-100字的中文摘要]

请确保中文标题简洁明了，不超过30个字。"""
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7
        )
        
        result = response.choices[0].message.content.strip()
        
        # 解析结果
        chinese_title = title
        chinese_summary = summary[:200] if summary else "无摘要"
        
        for line in result.split('\n'):
            line = line.strip()
            if line.startswith('中文标题：') or line.startswith('中文标题:'):
                chinese_title = line.split('：', 1)[1].strip() if '：' in line else line.split(':', 1)[1].strip()
                # 保留分类标签格式如 [AI], [CTV], [Programmatic], [联网电视] 等
                # 分类标签特点：中括号内2-20个字符，后面跟着空格和正文
                category_match = re.match(r'^(\[[^\]]{2,20}\])\s*(.+)', chinese_title)
                if category_match:
                    # 是分类标签格式，保留标签 + 内容
                    chinese_title = category_match.group(1) + ' ' + category_match.group(2).strip()
                else:
                    # 不是分类标签，移除可能的纯方括号包裹
                    chinese_title = chinese_title.strip('[]')
            elif line.startswith('中文摘要：') or line.startswith('中文摘要:'):
                chinese_summary = line.split('：', 1)[1].strip() if '：' in line else line.split(':', 1)[1].strip()
                # 摘要一般没有分类标签，直接移除可能的方括号包裹
                chinese_summary = chinese_summary.strip('[]')
        
        return chinese_title, chinese_summary
        
    except Exception as e:
        print(f"      ⚠️ 中文翻译失败: {e}")
        return title, summary[:200] if summary else "无摘要"


def main():
    print("=" * 70)
    print("周报整合系统 - 纯整合模式")
    print("=" * 70)
    
    # 计算日期窗口
    window_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
    window_start = (window_end - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
    start_str = str(window_start.date())
    end_str = str(window_end.date())
    
    print(f"\n📅 报告周期: {start_str} ~ {end_str}")
    
    # 检查邮件配置
    email_username = os.getenv('EMAIL_USERNAME')
    email_password = os.getenv('EMAIL_PASSWORD')
    send_email = bool(email_username and email_password)
    
    # 检查 DeepSeek API
    api_key = os.getenv('DEEPSEEK_API_KEY')
    use_ai_summary = bool(api_key)
    
    if send_email:
        print(f"✓ 邮件配置就绪")
    else:
        print("⚠️ 邮件未配置，将只生成报告")
    
    if use_ai_summary:
        print("✓ DeepSeek API 已配置，将生成中文摘要")
    else:
        print("⚠️ DeepSeek API 未配置，将使用原文")
    
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
    
    # 3. 生成中文标题和摘要
    if use_ai_summary:
        print("\n[3/4] 生成中文标题和摘要...")
        
        # 竞品资讯
        for i, item in enumerate(competitor_items, 1):
            print(f"  [{i}/{len(competitor_items)}] {item.title[:40]}...")
            item.title, item.summary = generate_chinese_title_summary(item.title, item.summary)
        
        # 行业资讯
        for module, items in industry_results.items():
            for item in items:
                print(f"  [行业-{module}] {item.title[:40]}...")
                item.title, item.summary = generate_chinese_title_summary(item.title, item.summary)
    else:
        # 截断原文作为摘要
        for item in competitor_items:
            item.summary = item.summary[:200] if item.summary else "无摘要"
        for module, items in industry_results.items():
            for item in items:
                item.summary = item.summary[:200] if item.summary else "无摘要"
    
    # 4. 生成 HTML 报告
    print("\n[4/4] 生成 HTML 报告...")
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
