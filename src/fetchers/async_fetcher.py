"""
异步并发抓取器 - 提高抓取速度
"""

import concurrent.futures
from datetime import datetime
from typing import Dict, List

from .base import ContentItem
from .competitor_fetcher import CompetitorFetcher
from .industry_fetcher import IndustryFetcher


class AsyncCompetitorFetcher(CompetitorFetcher):
    """并发竞品抓取器"""
    
    def fetch_all(self, window_start: datetime, window_end: datetime) -> Dict[str, List[ContentItem]]:
        """并发抓取所有竞品资讯"""
        import sys
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sys.path.insert(0, project_root)
        from config.settings import COMPETITOR_SOURCES
        
        results = {}
        
        def fetch_single(company_key, config):
            print(f"  [抓取] {config['name']}...")
            fetch_func = self.fetchers.get(company_key)
            if fetch_func:
                try:
                    items = fetch_func(window_start, window_end)
                    return config['name'], items
                except Exception as e:
                    print(f"    ⚠️ {config['name']} 失败: {e}")
                    return config['name'], []
            return config['name'], []
        
        # 使用线程池并发抓取
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_company = {
                executor.submit(fetch_single, key, config): key 
                for key, config in COMPETITOR_SOURCES.items()
            }
            
            for future in concurrent.futures.as_completed(future_to_company):
                company_name, items = future.result()
                if items:
                    results[company_name] = items
        
        return results


class AsyncIndustryFetcher(IndustryFetcher):
    """并发行业抓取器"""
    
    def fetch_all(self, window_start: datetime, window_end: datetime) -> Dict[str, List[ContentItem]]:
        """并发抓取所有行业资讯"""
        import sys
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sys.path.insert(0, project_root)
        from config.settings import INDUSTRY_SOURCES
        
        results = {}
        
        def fetch_single(module_name, config):
            print(f"  [抓取] {config['name']}...")
            try:
                items = self._fetch_module(config, window_start, window_end)
                return config['name'], items
            except Exception as e:
                print(f"    ⚠️ {config['name']} 失败: {e}")
                return config['name'], []
        
        # 使用线程池并发抓取
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_module = {
                executor.submit(fetch_single, name, config): name 
                for name, config in INDUSTRY_SOURCES.items()
            }
            
            for future in concurrent.futures.as_completed(future_to_module):
                module_name, items = future.result()
                results[module_name] = items
        
        return results
