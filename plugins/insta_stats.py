#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Instagram Statistics Logger"""

import time
from typing import Dict
from collections import defaultdict
from datetime import datetime

class InstaStats:
    """کلاس برای جمع‌آوری آمار Instagram"""
    
    def __init__(self):
        self.stats = {
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'by_layer': defaultdict(int),  # Layer 1, 2, 3
            'by_error': defaultdict(int),  # نوع خطاها
            'by_type': defaultdict(int),   # post, reel, story, etc
            'cache_hits': 0,
            'cache_misses': 0,
            'total_download_time': 0.0,
            'total_files_downloaded': 0,
        }
        self.start_time = time.time()
    
    def log_request(self, url: str):
        """ثبت یک درخواست جدید"""
        self.stats['total_requests'] += 1
        
        # تشخیص نوع
        if '/reel/' in url:
            self.stats['by_type']['reel'] += 1
        elif '/p/' in url:
            self.stats['by_type']['post'] += 1
        elif '/stories/' in url:
            self.stats['by_type']['story'] += 1
        elif '/tv/' in url:
            self.stats['by_type']['tv'] += 1
        elif '/igtv/' in url:
            self.stats['by_type']['igtv'] += 1
    
    def log_success(self, layer: int, download_time: float, files_count: int):
        """ثبت موفقیت"""
        self.stats['successful'] += 1
        self.stats['by_layer'][f'layer_{layer}'] += 1
        self.stats['total_download_time'] += download_time
        self.stats['total_files_downloaded'] += files_count
    
    def log_failure(self, error: str):
        """ثبت شکست"""
        self.stats['failed'] += 1
        self.stats['by_error'][error] += 1
    
    def log_cache_hit(self):
        """ثبت cache hit"""
        self.stats['cache_hits'] += 1
    
    def log_cache_miss(self):
        """ثبت cache miss"""
        self.stats['cache_misses'] += 1
    
    def get_summary(self) -> str:
        """دریافت خلاصه آمار"""
        uptime = time.time() - self.start_time
        uptime_hours = uptime / 3600
        
        total = self.stats['total_requests']
        success = self.stats['successful']
        failed = self.stats['failed']
        success_rate = (success / total * 100) if total > 0 else 0
        
        avg_time = (self.stats['total_download_time'] / success) if success > 0 else 0
        
        cache_total = self.stats['cache_hits'] + self.stats['cache_misses']
        cache_rate = (self.stats['cache_hits'] / cache_total * 100) if cache_total > 0 else 0
        
        summary = f"""
📊 Instagram Statistics
{'=' * 50}
⏱️  Uptime: {uptime_hours:.1f} hours
📈 Total Requests: {total}
✅ Successful: {success} ({success_rate:.1f}%)
❌ Failed: {failed}

📥 Downloads:
   Total Files: {self.stats['total_files_downloaded']}
   Avg Time: {avg_time:.2f}s

💾 Cache:
   Hits: {self.stats['cache_hits']}
   Misses: {self.stats['cache_misses']}
   Hit Rate: {cache_rate:.1f}%

📊 By Type:
"""
        for type_name, count in self.stats['by_type'].items():
            summary += f"   {type_name}: {count}\n"
        
        summary += "\n🎯 By Layer:\n"
        for layer, count in self.stats['by_layer'].items():
            summary += f"   {layer}: {count}\n"
        
        if self.stats['by_error']:
            summary += "\n⚠️  Top Errors:\n"
            sorted_errors = sorted(self.stats['by_error'].items(), key=lambda x: x[1], reverse=True)
            for error, count in sorted_errors[:5]:
                summary += f"   {error}: {count}\n"
        
        summary += "=" * 50
        return summary
    
    def reset(self):
        """ریست کردن آمار"""
        self.__init__()

# Global instance
insta_stats = InstaStats()
