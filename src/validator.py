"""
链接验证和内容校验模块
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Tuple
from urllib.parse import urlparse

import requests

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
from fetchers.base import ContentItem
from config.settings import SCRAPER_CONFIG, CONTENT_CONFIG


@dataclass
class ValidationError:
    """验证错误"""
    module: str  # 模块名称（如：竞品/行业 + 公司/子模块）
    title: str   # 条目标题
    reason: str  # 失败原因
    url: str     # 对应 URL


class Validator:
    """内容验证器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": SCRAPER_CONFIG["user_agent"],
        })
        self.timeout = 15
        self.min_length = CONTENT_CONFIG["summary_min_length"]
        self.max_length = CONTENT_CONFIG["summary_max_length"]
    
    def validate_competitor_items(self, items: Dict[str, List[ContentItem]], 
                                   window_start: datetime, window_end: datetime) -> Tuple[Dict[str, List[ContentItem]], List[ValidationError]]:
        """
        验证竞品资讯
        :param items: {公司名称: 内容列表}
        :param window_start: 窗口开始日期
        :param window_end: 窗口结束日期
        :return: (过滤后的内容, 错误列表)
        """
        validated = {}
        errors = []
        
        for company, company_items in items.items():
            validated[company] = []
            for item in company_items:
                is_valid, error = self._validate_item(item, window_start, window_end, f"竞品-{company}")
                if is_valid:
                    validated[company].append(item)
                else:
                    errors.append(error)
        
        return validated, errors
    
    def validate_industry_items(self, items: Dict[str, List[ContentItem]],
                                 window_start: datetime, window_end: datetime) -> Tuple[Dict[str, List[ContentItem]], List[ValidationError]]:
        """
        验证行业资讯
        :param items: {子模块名称: 内容列表}
        :param window_start: 窗口开始日期
        :param window_end: 窗口结束日期
        :return: (过滤后的内容, 错误列表)
        """
        validated = {}
        errors = []
        
        for module, module_items in items.items():
            validated[module] = []
            for item in module_items:
                is_valid, error = self._validate_item(item, window_start, window_end, f"行业-{module}")
                if is_valid:
                    validated[module].append(item)
                else:
                    errors.append(error)
        
        return validated, errors
    
    def _validate_item(self, item: ContentItem, window_start: datetime, 
                       window_end: datetime, module: str) -> Tuple[bool, ValidationError]:
        """
        验证单个条目
        :return: (是否通过, 错误信息)
        """
        # 1. 验证链接可用性
        if not self._validate_link(item.url):
            return False, ValidationError(
                module=module,
                title=item.title,
                reason="链接不可用（404或访问错误）",
                url=item.url
            )
        
        # 2. 验证日期格式和窗口
        if not item.date:
            return False, ValidationError(
                module=module,
                title=item.title,
                reason="日期缺失或无法解析",
                url=item.url
            )
        
        try:
            date_obj = datetime.strptime(item.date, "%Y-%m-%d")
            if not (window_start.date() <= date_obj.date() <= window_end.date()):
                return False, ValidationError(
                    module=module,
                    title=item.title,
                    reason=f"日期不在窗口范围内 ({item.date})",
                    url=item.url
                )
        except ValueError:
            return False, ValidationError(
                module=module,
                title=item.title,
                reason=f"日期格式错误 ({item.date})",
                url=item.url
            )
        
        # 3. 验证摘要长度
        summary_length = len(item.summary)
        if summary_length < self.min_length or summary_length > self.max_length:
            return False, ValidationError(
                module=module,
                title=item.title,
                reason=f"摘要长度不符合要求 ({summary_length}字，应为{self.min_length}-{self.max_length}字)",
                url=item.url
            )
        
        # 4. 验证摘要质量（是否包含关键指标/事实）
        if not self._validate_summary_quality(item.summary):
            return False, ValidationError(
                module=module,
                title=item.title,
                reason="摘要未包含关键指标或关键事实",
                url=item.url
            )
        
        return True, None
    
    def _validate_link(self, url: str) -> bool:
        """
        验证链接可用性
        :param url: 链接 URL
        :return: 是否可用
        """
        try:
            response = self.session.head(url, timeout=self.timeout, allow_redirects=True)
            # HTTP 状态码 < 400 且非 404
            if response.status_code < 400:
                return True
            
            # 如果 HEAD 请求失败，尝试 GET 请求
            if response.status_code in [405, 403]:  # Method Not Allowed or Forbidden
                response = self.session.get(url, timeout=self.timeout, stream=True)
                response.close()
                return response.status_code < 400
            
            return False
        except Exception as e:
            return False
    
    def _validate_summary_quality(self, summary: str) -> bool:
        """
        验证摘要质量（是否包含关键指标/事实）
        :param summary: 摘要内容
        :return: 是否包含关键信息
        """
        if not summary:
            return False
        
        # 检查摘要中是否包含数字（指标/数据）或特定关键词
        # 数字模式（包括百分比、金额、年份等）
        number_patterns = [
            r'\d+',  # 普通数字
            r'\d+\.\d+',  # 小数
            r'\d+%',  # 百分比
            r'\$\d+',  # 金额
            r'\d{4}',  # 年份
            r'20\d{2}',  # 2000+ 年份
        ]
        
        # 关键事实关键词
        fact_keywords = [
            '营收', '收入', '增长', '下降', '同比', '环比', '合作', '发布', '推出',
            '收购', '并购', '融资', '投资', '用户', '客户', '市场', '份额',
            'revenue', 'growth', 'decline', 'partnership', 'launch', 'acquire',
            'merger', 'funding', 'investment', 'users', 'customers', 'market',
            'million', 'billion', 'percent', '%', '$', '€', '£',
            '亿', '万', '千', '百', '百万', '千万', '十亿',
            '产品', '功能', '平台', '技术', '解决方案', '服务',
            'product', 'feature', 'platform', 'technology', 'solution', 'service',
            '第一', '第二', '第三', '首', '新', '最新',
        ]
        
        # 检查是否包含数字
        has_number = any(re.search(pattern, summary) for pattern in number_patterns)
        
        # 检查是否包含关键词
        has_keyword = any(keyword in summary.lower() for keyword in fact_keywords)
        
        # 至少需要满足一项
        return has_number or has_keyword
    
    def validate_pr_section_empty(self, html_content: str) -> Tuple[bool, str]:
        """
        验证 PR 区块是否为空
        :param html_content: HTML 内容
        :return: (是否通过, 错误信息)
        """
        # 检查 PR 相关关键词
        pr_keywords = [
            'pr section', 'pr_section', 'press release', 'press_release',
            'pr content', 'pr_content', 'pr区块', 'pr 区块'
        ]
        
        html_lower = html_content.lower()
        
        for keyword in pr_keywords:
            if keyword in html_lower:
                # 检查是否是注释或确实包含内容
                # 简单检查：如果关键词后跟有实际内容标签，则认为包含 PR 内容
                pattern = rf'{keyword}.*<[a-z]+[^>]*>[^<]{{10,}}'
                if re.search(pattern, html_lower, re.DOTALL):
                    return False, f"HTML 包含 PR 内容: {keyword}"
        
        return True, ""
    
    def generate_error_report(self, errors: List[ValidationError]) -> str:
        """
        生成错误报告
        :param errors: 错误列表
        :return: 格式化错误报告
        """
        if not errors:
            return "无错误"
        
        report = f"验证失败，共 {len(errors)} 个错误:\n\n"
        
        for i, error in enumerate(errors, 1):
            report += f"[{i}]\n"
            report += f"  模块: {error.module}\n"
            report += f"  标题: {error.title[:50]}...\n" if len(error.title) > 50 else f"  标题: {error.title}\n"
            report += f"  原因: {error.reason}\n"
            report += f"  URL: {error.url}\n\n"
        
        return report
