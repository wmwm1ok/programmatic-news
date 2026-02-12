"""
抓取器模块
用于抓取竞品和行业资讯
"""

from .base import BaseFetcher, ContentItem
from .competitor_fetcher import CompetitorFetcher
from .industry_fetcher import IndustryFetcher

__all__ = ['BaseFetcher', 'ContentItem', 'CompetitorFetcher', 'IndustryFetcher']
