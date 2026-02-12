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
        if self.pw_fetcher is None:
            try:
                self.pw_fetcher = PlaywrightFetcher()
            except Exception as e:
                print(f"  [!] Playwright 初始化失败: {e}")
        return self.pw_fetcher
    
    def _get_stealth_fetcher(self):
        if self.stealth_fetcher is None:
            try:
                self.stealth_fetcher = StealthFetcher()
            except Exception as e:
                print(f"  [!] Stealth 初始化失败: {e}")
        return self.stealth_fetcher
    
    def fetch_all(self, window_start: datetime, window_end: datetime) -> Dict[str, List[ContentItem]]:
        """抓取所有竞品资讯"""
        results = {}
        
        # Phase 1: HTTP 抓取
        print("\n[1/3] 抓取竞品资讯 (HTTP)...")
        results = self.requests_fetcher.fetch_all(window_start, window_end)
        
        # 找出未抓到的公司
        missing = []
        for key in COMPETITOR_SOURCES.keys():
            name = COMPETITOR_SOURCES[key]["name"]
            if name not in results or not results[name]:
                missing.append((key, name))
        
        if not missing:
            print("  所有公司已通过 HTTP 抓取成功")
            return results
        
        print(f"  {len(missing)} 家公司需要进一步抓取")
        
        # Phase 2: Playwright 抓取
        still_missing = []
        print("\n[2/3] 抓取竞品资讯 (Playwright)...")
        pw = self._get_pw_fetcher()
        if pw:
            for key, name in missing:
                try:
                    items = []
                    if key == "AppLovin":
                        items = pw.fetch_applovin(window_start, window_end)
                    elif key == "Unity":
                        items = pw.fetch_unity(window_start, window_end)
                    elif key == "Taboola":
                        items = pw.fetch_taboola(window_start, window_end)
                    elif key == "Teads":
                        items = pw.fetch_teads(window_start, window_end)
                    elif key == "Zeta Global":
                        items = pw.fetch_zeta(window_start, window_end)
                    elif key == "Criteo":
                        items = pw.fetch_criteo(window_start, window_end)
                    
                    if items:
                        results[name] = items
                        print(f"    ✓ {name}: {len(items)} 条")
                    else:
                        still_missing.append((key, name))
                except Exception as e:
                    print(f"    ✗ {name}: {e}")
                    still_missing.append((key, name))
            pw.close()
        else:
            still_missing = missing
        
        if not still_missing:
            return results
        
        # Phase 3: Stealth 模式抓取
        print("\n[3/3] 抓取竞品资讯 (Stealth)...")
        stealth = self._get_stealth_fetcher()
        if stealth:
            for key, name in still_missing:
                try:
                    items = []
                    if key == "Criteo":
                        items = stealth.fetch_criteo(window_start, window_end)
                    elif key == "Teads":
                        items = stealth.fetch_teads(window_start, window_end)
                    elif key == "AppLovin":
                        items = stealth.fetch_applovin(window_start, window_end)
                    elif key == "Unity":
                        items = stealth.fetch_unity(window_start, window_end)
                    elif key == "Zeta Global":
                        items = stealth.fetch_zeta(window_start, window_end)
                    elif key == "Moloco":
                        items = stealth.fetch_moloco(window_start, window_end)
                    elif key == "Magnite":
                        items = stealth.fetch_magnite(window_start, window_end)
                    else:
                        items = stealth.fetch_generic(key, window_start, window_end)
                    
                    if items:
                        results[name] = items
                        print(f"    ✓ {name}: {len(items)} 条 (Stealth)")
                except Exception as e:
                    print(f"    ✗ {name}: {e}")
            
            stealth.close()
        
        return results
