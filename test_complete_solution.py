#!/usr/bin/env python3
"""
اسکریپت تست کامل راه‌حل احراز هویت کوکی
Complete Cookie Authentication Solution Test Script
"""

import os
import sys
import subprocess
import logging
import time
from pathlib import Path
import json

class CompleteSolutionTester:
    def __init__(self):
        self.setup_logging()
        self.test_results = {}
        self.test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll for testing
        
    def setup_logging(self):
        """تنظیم سیستم لاگ"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('complete_solution_test.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def print_header(self, title):
        """چاپ عنوان تست"""
        print("\n" + "="*60)
        print(f"🧪 {title}")
        print("="*60)
        self.logger.info(f"Starting test: {title}")
    
    def print_result(self, test_name, success, message=""):
        """چاپ نتیجه تست"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if message:
            print(f"   📝 {message}")
        
        self.test_results[test_name] = {
            'success': success,
            'message': message
        }
        
        self.logger.info(f"Test result - {test_name}: {'PASS' if success else 'FAIL'} - {message}")
    
    def test_dns_resolution(self):
        """تست DNS Resolution"""
        self.print_header("تست DNS Resolution")
        
        domains = ['youtube.com', 'www.youtube.com', 'googlevideo.com']
        
        for domain in domains:
            try:
                result = subprocess.run(
                    ['nslookup', domain],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0 and 'Address:' in result.stdout:
                    self.print_result(f"DNS Resolution - {domain}", True, "Resolved successfully")
                else:
                    self.print_result(f"DNS Resolution - {domain}", False, "Failed to resolve")
                    
            except Exception as e:
                self.print_result(f"DNS Resolution - {domain}", False, str(e))
    
    def test_file_existence(self):
        """تست وجود فایل‌های ضروری"""
        self.print_header("تست وجود فایل‌های ضروری")
        
        required_files = [
            'emergency_youtube_downloader.py',
            'auto_cookie_manager.py',
            'youtube_cookie_manager.py',
            'COOKIE_AUTHENTICATION_GUIDE.md'
        ]
        
        for file_path in required_files:
            if Path(file_path).exists():
                self.print_result(f"File Existence - {file_path}", True, "File exists")
            else:
                self.print_result(f"File Existence - {file_path}", False, "File missing")
    
    def test_python_dependencies(self):
        """تست وابستگی‌های Python"""
        self.print_header("تست وابستگی‌های Python")
        
        dependencies = [
            'yt_dlp',
            'requests',
            'sqlite3',
            'json',
            'pathlib'
        ]
        
        for dep in dependencies:
            try:
                __import__(dep)
                self.print_result(f"Python Dependency - {dep}", True, "Available")
            except ImportError:
                self.print_result(f"Python Dependency - {dep}", False, "Missing")
    
    def test_cookie_extraction(self):
        """تست استخراج کوکی‌ها"""
        self.print_header("تست استخراج کوکی‌ها")
        
        try:
            # اجرای مدیر خودکار کوکی
            result = subprocess.run(
                [sys.executable, 'auto_cookie_manager.py', 'extract'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                self.print_result("Cookie Extraction", True, "Cookies extracted successfully")
                
                # بررسی فایل‌های کوکی
                cookie_files = ['youtube_cookies.txt', 'youtube_cookies.json']
                for cookie_file in cookie_files:
                    if Path(cookie_file).exists():
                        file_size = Path(cookie_file).stat().st_size
                        self.print_result(f"Cookie File - {cookie_file}", True, f"Size: {file_size} bytes")
                    else:
                        self.print_result(f"Cookie File - {cookie_file}", False, "File not created")
            else:
                self.print_result("Cookie Extraction", False, result.stderr)
                
        except Exception as e:
            self.print_result("Cookie Extraction", False, str(e))
    
    def test_cookie_validation(self):
        """تست اعتبار کوکی‌ها"""
        self.print_header("تست اعتبار کوکی‌ها")
        
        try:
            # تست با مدیر خودکار کوکی
            result = subprocess.run(
                [sys.executable, 'auto_cookie_manager.py', 'test'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.print_result("Cookie Validation", True, "Cookies are valid")
            else:
                self.print_result("Cookie Validation", False, "Cookies validation failed")
                
        except Exception as e:
            self.print_result("Cookie Validation", False, str(e))
    
    def test_emergency_downloader(self):
        """تست دانلودر اضطراری"""
        self.print_header("تست دانلودر اضطراری")
        
        try:
            # تست اتصال
            result = subprocess.run(
                [sys.executable, 'emergency_youtube_downloader.py', 'test'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                self.print_result("Emergency Downloader - Connection Test", True, "Connection successful")
            else:
                # بررسی اگر فقط مشکل احراز هویت باشد
                if "Sign in to confirm" in result.stderr or "authentication" in result.stderr:
                    self.print_result("Emergency Downloader - Connection Test", True, "Connection OK, needs authentication")
                else:
                    self.print_result("Emergency Downloader - Connection Test", False, result.stderr)
                    
        except Exception as e:
            self.print_result("Emergency Downloader - Connection Test", False, str(e))
    
    def test_youtube_download_simulation(self):
        """تست شبیه‌سازی دانلود YouTube"""
        self.print_header("تست شبیه‌سازی دانلود YouTube")
        
        try:
            # تست با yt-dlp مستقیم
            cmd = ['yt-dlp', '--simulate', '--quiet']
            
            # اضافه کردن کوکی‌ها اگر موجود باشند
            if Path('youtube_cookies.txt').exists():
                cmd.extend(['--cookies', 'youtube_cookies.txt'])
            
            cmd.append(self.test_url)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.print_result("YouTube Download Simulation", True, "Simulation successful")
            else:
                if "Sign in to confirm" in result.stderr:
                    self.print_result("YouTube Download Simulation", False, "Authentication required")
                else:
                    self.print_result("YouTube Download Simulation", False, result.stderr)
                    
        except Exception as e:
            self.print_result("YouTube Download Simulation", False, str(e))
    
    def test_network_connectivity(self):
        """تست اتصال شبکه"""
        self.print_header("تست اتصال شبکه")
        
        urls = [
            'https://www.youtube.com',
            'https://www.google.com',
            'https://8.8.8.8'
        ]
        
        for url in urls:
            try:
                import requests
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    self.print_result(f"Network Connectivity - {url}", True, f"Status: {response.status_code}")
                else:
                    self.print_result(f"Network Connectivity - {url}", False, f"Status: {response.status_code}")
            except Exception as e:
                self.print_result(f"Network Connectivity - {url}", False, str(e))
    
    def generate_report(self):
        """تولید گزارش نهایی"""
        self.print_header("گزارش نهایی")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['success'])
        failed_tests = total_tests - passed_tests
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"📊 آمار کلی:")
        print(f"   🧪 تعداد کل تست‌ها: {total_tests}")
        print(f"   ✅ تست‌های موفق: {passed_tests}")
        print(f"   ❌ تست‌های ناموفق: {failed_tests}")
        print(f"   📈 درصد موفقیت: {success_rate:.1f}%")
        
        # ذخیره گزارش در فایل JSON
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': success_rate,
            'test_results': self.test_results
        }
        
        with open('test_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 گزارش کامل در فایل test_report.json ذخیره شد")
        
        # توصیه‌های بر اساس نتایج
        self.print_recommendations()
        
        return success_rate >= 80  # موفقیت اگر 80% یا بیشتر از تست‌ها موفق باشند
    
    def print_recommendations(self):
        """چاپ توصیه‌ها بر اساس نتایج تست"""
        print(f"\n💡 توصیه‌ها:")
        
        failed_tests = [name for name, result in self.test_results.items() if not result['success']]
        
        if not failed_tests:
            print("   🎉 همه تست‌ها موفق بودند! سیستم آماده استفاده است.")
            return
        
        if any('DNS' in test for test in failed_tests):
            print("   🌐 مشکل DNS: اسکریپت emergency_dns_fix.sh را اجرا کنید")
        
        if any('Cookie' in test for test in failed_tests):
            print("   🍪 مشکل کوکی: مرورگر را ببندید و کوکی‌ها را دوباره استخراج کنید")
            print("   📝 دستور: python3 auto_cookie_manager.py extract")
        
        if any('Network' in test for test in failed_tests):
            print("   🔌 مشکل شبکه: اتصال اینترنت و فایروال را بررسی کنید")
        
        if any('Dependency' in test for test in failed_tests):
            print("   📦 مشکل وابستگی‌ها: pip install -r requirements.txt")
        
        if any('File' in test for test in failed_tests):
            print("   📁 فایل‌های ناقص: فایل‌های ضروری را دوباره دانلود کنید")
    
    def run_all_tests(self):
        """اجرای تمام تست‌ها"""
        print("🚀 شروع تست کامل راه‌حل احراز هویت کوکی")
        print("="*60)
        
        # اجرای تست‌ها
        self.test_file_existence()
        self.test_python_dependencies()
        self.test_dns_resolution()
        self.test_network_connectivity()
        self.test_cookie_extraction()
        self.test_cookie_validation()
        self.test_emergency_downloader()
        self.test_youtube_download_simulation()
        
        # تولید گزارش نهایی
        success = self.generate_report()
        
        return success

def main():
    """تابع اصلی"""
    tester = CompleteSolutionTester()
    
    try:
        success = tester.run_all_tests()
        
        if success:
            print("\n🎉 تست کامل موفقیت‌آمیز بود!")
            sys.exit(0)
        else:
            print("\n⚠️ برخی تست‌ها ناموفق بودند. لطفاً توصیه‌ها را بررسی کنید.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️ تست توسط کاربر متوقف شد")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ خطای غیرمنتظره: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()