"""
抓取器基类
"""

import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
from config.settings import SCRAPER_CONFIG


@dataclass
class ContentItem:
    """内容条目"""
    title: str
    summary: str
    date: str  # YYYY-MM-DD
    url: str
    source: str
    
    def __post_init__(self):
        # 验证日期格式
        if self.date:
            try:
                datetime.strptime(self.date, "%Y-%m-%d")
            except ValueError:
                self.date = ""


class BaseFetcher:
    """抓取器基类"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": SCRAPER_CONFIG["user_agent"],
            **SCRAPER_CONFIG["headers"]
        })
        self.timeout = SCRAPER_CONFIG["timeout"]
        self.retry_times = SCRAPER_CONFIG["retry_times"]
        self.retry_delay = SCRAPER_CONFIG["retry_delay"]
    
    def fetch(self, url: str, **kwargs) -> Optional[str]:
        """
        发送 HTTP 请求获取页面内容
        :param url: 目标 URL
        :return: HTML 内容或 None
        """
        for attempt in range(self.retry_times):
            try:
                response = self.session.get(
                    url, 
                    timeout=self.timeout,
                    **kwargs
                )
                response.raise_for_status()
                return response.text
            except Exception as e:
                print(f"    [!] 请求失败 (尝试 {attempt + 1}/{self.retry_times}): {str(e)[:80]}")
                if attempt < self.retry_times - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                return None
        return None
    
    def parse_date(self, date_str: str) -> Optional[str]:
        """
        解析日期字符串，返回 YYYY-MM-DD 格式
        :param date_str: 日期字符串
        :return: YYYY-MM-DD 或 None
        """
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # 常见日期格式
        patterns = [
            (r"(\d{4})-(\d{1,2})-(\d{1,2})", lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"),
            (r"(\d{1,2})/(\d{1,2})/(\d{4})", lambda m: f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"),
            (r"(\d{1,2})-(\d{1,2})-(\d{4})", lambda m: f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"),
            (r"(\d{4})/(\d{1,2})/(\d{1,2})", lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"),
            (r"(\d{4})\.(\d{1,2})\.(\d{1,2})", lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"),
            # 英文月份格式
            (r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})", 
             lambda m: f"{m.group(3)}-{self._month_abbr_to_num(m.group(2)):02d}-{int(m.group(1)):02d}"),
            (r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2}),?\s+(\d{4})", 
             lambda m: f"{m.group(3)}-{self._month_abbr_to_num(m.group(1)):02d}-{int(m.group(2)):02d}"),
            # ISO 格式
            (r"(\d{4}-\d{2}-\d{2})T", lambda m: m.group(1)),
        ]
        
        for pattern, formatter in patterns:
            match = re.search(pattern, date_str, re.IGNORECASE)
            if match:
                try:
                    return formatter(match)
                except:
                    continue
        
        return None
    
    def _month_abbr_to_num(self, month_abbr: str) -> int:
        """月份缩写转数字"""
        months = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        return months.get(month_abbr.lower()[:3], 1)
    
    def is_in_date_window(self, date_str: str, window_start: datetime, window_end: datetime) -> bool:
        """
        检查日期是否在时间窗口内
        :param date_str: YYYY-MM-DD 格式的日期
        :param window_start: 窗口开始日期
        :param window_end: 窗口结束日期
        :return: 是否在窗口内
        """
        if not date_str:
            return False
        
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return window_start.date() <= date_obj.date() <= window_end.date()
        except:
            return False
    
    def normalize_url(self, base_url: str, relative_url: str) -> str:
        """
        规范化 URL
        :param base_url: 基础 URL
        :param relative_url: 相对 URL
        :return: 完整 URL
        """
        return urljoin(base_url, relative_url)
    
    def clean_text(self, text: str) -> str:
        """
        清理文本
        :param text: 原始文本
        :return: 清理后的文本
        """
        if not text:
            return ""
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        # 移除特殊字符
        text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        return text.strip()
