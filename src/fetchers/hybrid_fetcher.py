"""
混合抓取器 - 结合 Requests、Playwright 和 Stealth 模式
"""

from datetime import datetime
from typing import Dict, List

from .base import ContentItem
from .competitor_fetcher_v2 import CompetitorFetcherV2
from .playwright_fetcher import PlaywrightFetcher
from .stealth_fetcher import StealthFetcher

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
from config.settings import COMPETITOR_SOURCES


class HybridCompetitorFetcher:
    """混合竞品抓取器"""
    
    def __init__(self):
        self.requests_fetcher = CompetitorFetcherV2()
        self.pw_fetcher = None
        self.stealth_fetcher = None
    
    def _get_pw_fetcher(self):
        """延迟初始化 Playwright"""
        if self.pw_fetcher is None:
            try:
                self.pw_fetcher = PlaywrightFetcher()
            except Exception as e:
                print(f"  [!] Playwright 初始化失败: {e}")
        return self.pw_fetcher
    
    def _get_stealth_fetcher(self):
        """延迟初始化 Stealth Fetcher"""
        if self.stealth_fetcher is None:
            try:
                self.stealth_fetcher = StealthFetcher()
            except Exception as e:
                print(f"  [!] Stealth 初始化失败: {e}")
        return self.stealth_fetcher
    
    def fetch_all(self, window_start: datetime, window_end: datetime) -> Dict[str, List[ContentItem]]:
        """抓取所有竞品资讯"""
        results = {}
        
        # 先用 requests 抓取
        print("\n[2/6] 抓取竞品资讯 (Phase 1: HTTP)...")
        results = self.requests_fetcher.fetch_all(window_start, window_end)
        
        # 检查哪些公司没有抓到内容
        missing_companies = []
        for key in COMPETITOR_SOURCES.keys():
            name = COMPETITOR_SOURCES[key]["name"]
            if name not in results or not results[name]:
                missing_companies.append((key, name))
        
        # Phase 2: 使用 Playwright 抓取
        still_missing = []
        if missing_companies:
            print(f"\n  [Phase 2: Playwright] 补充抓取 {len(missing_companies)} 家公司...")
            pw = self._get_pw_fetcher()
            if pw:
                for key, name in missing_companies:
                    try:
                        if key == "AppLovin":
                            items = pw.fetch_applovin(window_start, window_end)
                        elif key == "Unity":
                            items = pw.fetch_unity(window_start, window_end)
                        elif key == "Criteo":
                            items = pw.fetch_criteo(window_start, window_end)
                        elif key == "Taboola":
                            items = pw.fetch_taboola(window_start, window_end)
                        elif key == "Teads":
                            items = pw.fetch_teads(window_start, window_end)
                        elif key == "Zeta Global":
                            items = pw.fetch_zeta(window_start, window_end)
                        else:
                            still_missing.append((key, name))
                            continue
                        
                        if items:
                            results[name] = items
                            print(f"    ✓ {name}: {len(items)} 条 (Playwright)")
                        else:
                            still_missing.append((key, name))
                    except Exception as e:
                        print(f"    ✗ {name}: {e}")
                        still_missing.append((key, name))
                
                pw.close()
            else:
                still_missing = missing_companies
        
        # Phase 3: 使用 Stealth 模式抓取剩余的有反爬虫保护的网站
        if still_missing:
            print(f"\n  [Phase 3: Stealth] 高级抓取 {len(still_missing)} 家公司...")
            stealth = self._get_stealth_fetcher()
            if stealth:
                for key, name in still_missing:
                    try:
                        if key == "Criteo":
                            # Criteo 有 Cloudflare，使用 stealth
                            items = stealth.fetch_criteo(window_start, window_end)
                        else:
                            continue
                        
                        if items:
                            results[name] = items
                            print(f"    ✓ {name}: {len(items)} 条 (Stealth)")
                    except Exception as e:
                        print(f"    ✗ {name}: {e}")
                
                stealth.close()
        
        return results
