#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اسکریپت تست برای محیط سرور لینوکس
تست DNS resolution و دانلود ویدیو یوتیوب
"""

import os
import sys
import asyncio
import socket
import urllib3
import time
from pathlib import Path

# اضافه کردن مسیر پروژه
sys.path.append(str(Path(__file__).parent))

from plugins.youtube_advanced_downloader import youtube_downloader
from plugins.logger_config import get_logger

# تنظیم logger
test_logger = get_logger('linux_server_test')

class LinuxServerTester:
    def __init__(self):
        self.test_url = "https://www.youtube.com/watch?v=dL_r_PPlFtI"
        self.test_results = {}
        
    async def test_dns_resolution(self):
        """تست DNS resolution"""
        test_logger.info("شروع تست DNS resolution...")
        
        try:
            # تست حل نام دامنه youtube.com
            start_time = time.time()
            socket.gethostbyname('youtube.com')
            dns_time = time.time() - start_time
            
            test_logger.info(f"DNS resolution موفق: {dns_time:.2f} ثانیه")
            self.test_results['dns_resolution'] = {
                'status': 'success',
                'time': dns_time
            }
            return True
            
        except Exception as e:
            test_logger.error(f"DNS resolution ناموفق: {e}")
            self.test_results['dns_resolution'] = {
                'status': 'failed',
                'error': str(e)
            }
            return False
    
    async def test_network_connectivity(self):
        """تست اتصال شبکه"""
        test_logger.info("شروع تست اتصال شبکه...")
        
        try:
            import urllib.request
            
            # تست اتصال به youtube.com
            start_time = time.time()
            response = urllib.request.urlopen('https://www.youtube.com', timeout=30)
            connect_time = time.time() - start_time
            
            if response.status == 200:
                test_logger.info(f"اتصال شبکه موفق: {connect_time:.2f} ثانیه")
                self.test_results['network_connectivity'] = {
                    'status': 'success',
                    'time': connect_time,
                    'status_code': response.status
                }
                return True
            else:
                test_logger.warning(f"اتصال شبکه با خطا: status={response.status}")
                self.test_results['network_connectivity'] = {
                    'status': 'warning',
                    'status_code': response.status
                }
                return False
                
        except Exception as e:
            test_logger.error(f"اتصال شبکه ناموفق: {e}")
            self.test_results['network_connectivity'] = {
                'status': 'failed',
                'error': str(e)
            }
            return False
    
    async def test_video_info_extraction(self):
        """تست استخراج اطلاعات ویدیو"""
        test_logger.info("شروع تست استخراج اطلاعات ویدیو...")
        
        try:
            start_time = time.time()
            video_info = await youtube_downloader.get_video_info(self.test_url)
            extract_time = time.time() - start_time
            
            if video_info:
                test_logger.info(f"استخراج اطلاعات موفق: {extract_time:.2f} ثانیه")
                test_logger.info(f"عنوان ویدیو: {video_info.get('title', 'نامشخص')}")
                test_logger.info(f"مدت زمان: {video_info.get('duration', 'نامشخص')} ثانیه")
                
                self.test_results['video_info_extraction'] = {
                    'status': 'success',
                    'time': extract_time,
                    'title': video_info.get('title', 'نامشخص'),
                    'duration': video_info.get('duration', 'نامشخص'),
                    'formats_count': len(video_info.get('formats', []))
                }
                return True
            else:
                test_logger.error("استخراج اطلاعات ناموفق: اطلاعات خالی")
                self.test_results['video_info_extraction'] = {
                    'status': 'failed',
                    'error': 'اطلاعات خالی'
                }
                return False
                
        except Exception as e:
            test_logger.error(f"استخراج اطلاعات ناموفق: {e}")
            self.test_results['video_info_extraction'] = {
                'status': 'failed',
                'error': str(e)
            }
            return False
    
    async def test_quality_analysis(self):
        """تست تحلیل کیفیت‌ها"""
        test_logger.info("شروع تست تحلیل کیفیت‌ها...")
        
        try:
            video_info = await youtube_downloader.get_video_info(self.test_url)
            if not video_info:
                raise Exception("عدم دریافت اطلاعات ویدیو")
            
            start_time = time.time()
            qualities = youtube_downloader.get_mergeable_qualities(video_info)
            analysis_time = time.time() - start_time
            
            if qualities:
                test_logger.info(f"تحلیل کیفیت‌ها موفق: {analysis_time:.2f} ثانیه")
                test_logger.info(f"تعداد کیفیت‌های موجود: {len(qualities)}")
                
                for quality in qualities[:3]:  # نمایش 3 کیفیت اول
                    test_logger.info(f"کیفیت: {quality.get('quality', 'نامشخص')} - {quality.get('format_note', 'نامشخص')}")
                
                self.test_results['quality_analysis'] = {
                    'status': 'success',
                    'time': analysis_time,
                    'qualities_count': len(qualities)
                }
                return True
            else:
                test_logger.error("تحلیل کیفیت‌ها ناموفق: کیفیت‌های خالی")
                self.test_results['quality_analysis'] = {
                    'status': 'failed',
                    'error': 'کیفیت‌های خالی'
                }
                return False
                
        except Exception as e:
            test_logger.error(f"تحلیل کیفیت‌ها ناموفق: {e}")
            self.test_results['quality_analysis'] = {
                'status': 'failed',
                'error': str(e)
            }
            return False
    
    async def test_dns_configuration(self):
        """تست تنظیمات DNS سفارشی"""
        test_logger.info("شروع تست تنظیمات DNS سفارشی...")
        
        try:
            # تست تنظیمات DNS
            original_timeout = socket.getdefaulttimeout()
            
            # اعمال تنظیمات DNS سفارشی
            youtube_downloader._setup_dns_config()
            
            new_timeout = socket.getdefaulttimeout()
            
            test_logger.info(f"DNS timeout قبلی: {original_timeout}")
            test_logger.info(f"DNS timeout جدید: {new_timeout}")
            
            # تست تنظیمات بهبود یافته
            enhanced_opts = youtube_downloader._get_enhanced_ydl_opts()
            
            test_logger.info(f"Socket timeout: {enhanced_opts.get('socket_timeout')}")
            test_logger.info(f"Connect timeout: {enhanced_opts.get('connect_timeout')}")
            test_logger.info(f"Retries: {enhanced_opts.get('retries')}")
            
            self.test_results['dns_configuration'] = {
                'status': 'success',
                'original_timeout': original_timeout,
                'new_timeout': new_timeout,
                'socket_timeout': enhanced_opts.get('socket_timeout'),
                'connect_timeout': enhanced_opts.get('connect_timeout'),
                'retries': enhanced_opts.get('retries')
            }
            return True
            
        except Exception as e:
            test_logger.error(f"تست تنظیمات DNS ناموفق: {e}")
            self.test_results['dns_configuration'] = {
                'status': 'failed',
                'error': str(e)
            }
            return False
    
    async def run_all_tests(self):
        """اجرای همه تست‌ها"""
        test_logger.info("=" * 60)
        test_logger.info("شروع تست‌های محیط سرور لینوکس")
        test_logger.info("=" * 60)
        
        tests = [
            ("DNS Resolution", self.test_dns_resolution),
            ("Network Connectivity", self.test_network_connectivity),
            ("DNS Configuration", self.test_dns_configuration),
            ("Video Info Extraction", self.test_video_info_extraction),
            ("Quality Analysis", self.test_quality_analysis),
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            test_logger.info(f"\n--- تست {test_name} ---")
            try:
                result = await test_func()
                if result:
                    passed_tests += 1
                    test_logger.info(f"✅ {test_name}: موفق")
                else:
                    test_logger.error(f"❌ {test_name}: ناموفق")
            except Exception as e:
                test_logger.error(f"❌ {test_name}: خطا - {e}")
        
        # گزارش نهایی
        test_logger.info("\n" + "=" * 60)
        test_logger.info("گزارش نهایی تست‌ها")
        test_logger.info("=" * 60)
        test_logger.info(f"تست‌های موفق: {passed_tests}/{total_tests}")
        test_logger.info(f"درصد موفقیت: {(passed_tests/total_tests)*100:.1f}%")
        
        # نمایش جزئیات
        for test_name, result in self.test_results.items():
            status = result.get('status', 'unknown')
            if status == 'success':
                test_logger.info(f"✅ {test_name}: {status}")
            elif status == 'warning':
                test_logger.warning(f"⚠️ {test_name}: {status}")
            else:
                test_logger.error(f"❌ {test_name}: {status}")
                if 'error' in result:
                    test_logger.error(f"   خطا: {result['error']}")
        
        return passed_tests, total_tests

async def main():
    """تابع اصلی"""
    tester = LinuxServerTester()
    
    try:
        passed, total = await tester.run_all_tests()
        
        if passed == total:
            test_logger.info("\n🎉 همه تست‌ها موفق بودند!")
            return 0
        elif passed > 0:
            test_logger.warning(f"\n⚠️ {passed} از {total} تست موفق بودند")
            return 1
        else:
            test_logger.error(f"\n💥 همه تست‌ها ناموفق بودند!")
            return 2
            
    except Exception as e:
        test_logger.error(f"خطا در اجرای تست‌ها: {e}")
        return 3

if __name__ == "__main__":
    # اجرای تست‌ها
    exit_code = asyncio.run(main())
    sys.exit(exit_code)