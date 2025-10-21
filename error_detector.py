#!/usr/bin/env python3
"""
سیستم تشخیص خطا و گزارش‌دهی جامع برای ربات
این ماژول انواع مختلف خطاها را تشخیص داده و گزارش مفصلی ارائه می‌دهد
"""

import os
import sys
import traceback
import logging
import json
import platform
import subprocess
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any
import importlib.util

class ErrorDetector:
    """کلاس اصلی تشخیص خطا و گزارش‌دهی"""
    
    def __init__(self, log_dir: str = "./logs"):
        self.log_dir = log_dir
        self.crash_log_file = os.path.join(log_dir, "crash_report.log")
        self.detailed_report_file = os.path.join(log_dir, "detailed_error_report.json")
        
        # ایجاد دایرکتوری لاگ
        os.makedirs(log_dir, exist_ok=True)
        
        # تنظیم لاگر مخصوص خطاهای کرش
        self.crash_logger = self._setup_crash_logger()
        
    def _setup_crash_logger(self) -> logging.Logger:
        """تنظیم لاگر مخصوص خطاهای کرش"""
        logger = logging.getLogger('crash_detector')
        logger.setLevel(logging.ERROR)
        
        # حذف هندلرهای قبلی
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # هندلر فایل
        file_handler = logging.FileHandler(self.crash_log_file, encoding='utf-8')
        file_handler.setLevel(logging.ERROR)
        
        # هندلر کنسول
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        
        # فرمت لاگ
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def check_environment(self) -> Dict[str, Any]:
        """بررسی محیط سیستم و شناسایی مشکلات احتمالی"""
        issues = []
        system_info = {}
        
        try:
            # اطلاعات سیستم
            system_info = {
                'platform': platform.platform(),
                'python_version': sys.version,
                'python_executable': sys.executable,
                'working_directory': os.getcwd(),
                'timestamp': datetime.now().isoformat()
            }
            
            # بررسی فایل .env
            if not os.path.exists('.env'):
                issues.append({
                    'type': 'missing_file',
                    'severity': 'critical',
                    'message': 'فایل .env یافت نشد',
                    'solution': 'فایل .env را ایجاد کنید و متغیرهای محیطی مورد نیاز را تنظیم کنید'
                })
            
            # بررسی config.py
            if not os.path.exists('config.py'):
                issues.append({
                    'type': 'missing_file',
                    'severity': 'critical',
                    'message': 'فایل config.py یافت نشد',
                    'solution': 'فایل config.py را ایجاد کنید'
                })
            
            # بررسی دایرکتوری plugins
            if not os.path.exists('plugins'):
                issues.append({
                    'type': 'missing_directory',
                    'severity': 'critical',
                    'message': 'دایرکتوری plugins یافت نشد',
                    'solution': 'دایرکتوری plugins را ایجاد کنید'
                })
            
            # بررسی requirements.txt
            if os.path.exists('requirements.txt'):
                missing_packages = self._check_required_packages()
                if missing_packages:
                    issues.append({
                        'type': 'missing_dependencies',
                        'severity': 'high',
                        'message': f'پکیج‌های مورد نیاز نصب نشده: {", ".join(missing_packages)}',
                        'solution': 'دستور pip install -r requirements.txt را اجرا کنید'
                    })
            
            # بررسی FFmpeg
            ffmpeg_path = shutil.which('ffmpeg')
            if not ffmpeg_path:
                issues.append({
                    'type': 'missing_tool',
                    'severity': 'medium',
                    'message': 'FFmpeg در PATH سیستم یافت نشد',
                    'solution': 'FFmpeg را نصب کنید یا مسیر آن را در متغیر محیطی FFMPEG_PATH تنظیم کنید'
                })
            else:
                system_info['ffmpeg_path'] = ffmpeg_path
            
            # بررسی دسترسی نوشتن
            test_dirs = ['./logs', './downloads', './data']
            for test_dir in test_dirs:
                try:
                    os.makedirs(test_dir, exist_ok=True)
                    test_file = os.path.join(test_dir, 'test_write.tmp')
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                except Exception as e:
                    issues.append({
                        'type': 'permission_error',
                        'severity': 'high',
                        'message': f'عدم دسترسی نوشتن در دایرکتوری {test_dir}: {str(e)}',
                        'solution': 'دسترسی‌های فایل سیستم را بررسی کنید'
                    })
            
        except Exception as e:
            issues.append({
                'type': 'environment_check_error',
                'severity': 'high',
                'message': f'خطا در بررسی محیط: {str(e)}',
                'solution': 'لاگ‌های سیستم را بررسی کنید'
            })
        
        return {
            'system_info': system_info,
            'issues': issues,
            'total_issues': len(issues),
            'critical_issues': len([i for i in issues if i['severity'] == 'critical'])
        }
    
    def _check_required_packages(self) -> List[str]:
        """بررسی پکیج‌های مورد نیاز"""
        missing_packages = []
        
        # نگاشت نام پکیج به نام ماژول
        package_to_module_map = {
            "mysql-connector-python": "mysql.connector",
            "python-dotenv": "dotenv",
            "Pillow": "PIL",
            "Pyrogram": "pyrogram",
            "python-dateutil": "dateutil"
        }
        
        try:
            with open('requirements.txt', 'r', encoding='utf-8') as f:
                requirements = f.read().splitlines()
            
            for requirement in requirements:
                if requirement.strip() and not requirement.startswith('#'):
                    package_name = requirement.split('==')[0].split('>=')[0].split('<=')[0].strip()
                    module_name = package_to_module_map.get(package_name, package_name.replace('-', '_'))
                    try:
                        importlib.import_module(module_name)
                    except ImportError:
                        missing_packages.append(package_name)
        
        except Exception:
            pass
        
        return missing_packages
    
    def analyze_exception(self, exc_type, exc_value, exc_traceback) -> Dict[str, Any]:
        """تجزیه و تحلیل دقیق خطا"""
        error_analysis = {
            'timestamp': datetime.now().isoformat(),
            'error_type': exc_type.__name__ if exc_type else 'Unknown',
            'error_message': str(exc_value) if exc_value else 'No message',
            'traceback': traceback.format_exception(exc_type, exc_value, exc_traceback),
            'suggestions': []
        }
        
        # تحلیل انواع مختلف خطا و ارائه راه‌حل
        error_message = str(exc_value).lower() if exc_value else ''
        
        if exc_type == ImportError:
            error_analysis['suggestions'].extend([
                'پکیج مورد نیاز نصب نشده است',
                'دستور pip install -r requirements.txt را اجرا کنید',
                'نسخه Python را بررسی کنید'
            ])
        
        elif exc_type == FileNotFoundError:
            error_analysis['suggestions'].extend([
                'فایل یا دایرکتوری مورد نیاز وجود ندارد',
                'مسیر فایل را بررسی کنید',
                'دسترسی‌های فایل سیستم را چک کنید'
            ])
        
        elif exc_type == PermissionError:
            error_analysis['suggestions'].extend([
                'عدم دسترسی کافی به فایل یا دایرکتوری',
                'دسترسی‌های فایل سیستم را بررسی کنید',
                'ربات را با دسترسی مناسب اجرا کنید'
            ])
        
        elif 'token' in error_message or 'api' in error_message:
            error_analysis['suggestions'].extend([
                'توکن ربات یا اطلاعات API نامعتبر است',
                'فایل .env را بررسی کنید',
                'توکن جدید از BotFather دریافت کنید'
            ])
        
        elif 'database' in error_message or 'sqlite' in error_message:
            error_analysis['suggestions'].extend([
                'مشکل در اتصال یا عملیات پایگاه داده',
                'فایل پایگاه داده را بررسی کنید',
                'دسترسی نوشتن در دایرکتوری را چک کنید'
            ])
        
        elif 'network' in error_message or 'connection' in error_message:
            error_analysis['suggestions'].extend([
                'مشکل در اتصال شبکه',
                'اتصال اینترنت را بررسی کنید',
                'تنظیمات فایروال را چک کنید'
            ])
        
        elif exc_type == AttributeError:
            error_analysis['suggestions'].extend([
                'متغیر یا متد مورد نظر وجود ندارد',
                'فایل config.py را بررسی کنید',
                'نسخه پکیج‌ها را چک کنید'
            ])
        
        else:
            error_analysis['suggestions'].extend([
                'خطای غیرمنتظره رخ داده است',
                'لاگ‌های کامل را بررسی کنید',
                'کد مربوطه را دیباگ کنید'
            ])
        
        return error_analysis
    
    def generate_crash_report(self, exc_type, exc_value, exc_traceback) -> str:
        """تولید گزارش کامل کرش"""
        
        # بررسی محیط
        env_check = self.check_environment()
        
        # تحلیل خطا
        error_analysis = self.analyze_exception(exc_type, exc_value, exc_traceback)
        
        # تولید گزارش متنی
        report = f"""
{'='*80}
🚨 گزارش کرش ربات - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*80}

📋 اطلاعات سیستم:
- پلتفرم: {env_check['system_info'].get('platform', 'نامشخص')}
- نسخه Python: {env_check['system_info'].get('python_version', 'نامشخص')}
- دایرکتوری کاری: {env_check['system_info'].get('working_directory', 'نامشخص')}

🔥 جزئیات خطا:
- نوع خطا: {error_analysis['error_type']}
- پیام خطا: {error_analysis['error_message']}

📍 مکان خطا:
{''.join(error_analysis['traceback'])}

💡 راه‌حل‌های پیشنهادی:
"""
        
        for i, suggestion in enumerate(error_analysis['suggestions'], 1):
            report += f"{i}. {suggestion}\n"
        
        if env_check['issues']:
            report += f"\n⚠️  مشکلات محیط ({env_check['total_issues']} مورد):\n"
            for i, issue in enumerate(env_check['issues'], 1):
                report += f"{i}. [{issue['severity'].upper()}] {issue['message']}\n"
                report += f"   راه‌حل: {issue['solution']}\n\n"
        
        report += f"\n{'='*80}\n"
        
        # ذخیره گزارش در فایل JSON
        detailed_report = {
            'timestamp': datetime.now().isoformat(),
            'system_info': env_check['system_info'],
            'error_analysis': error_analysis,
            'environment_issues': env_check['issues']
        }
        
        try:
            with open(self.detailed_report_file, 'w', encoding='utf-8') as f:
                json.dump(detailed_report, f, ensure_ascii=False, indent=2)
        except Exception as e:
            report += f"\n⚠️ خطا در ذخیره گزارش تفصیلی: {e}\n"
        
        return report
    
    def log_crash(self, exc_type, exc_value, exc_traceback):
        """ثبت کرش در لاگ"""
        report = self.generate_crash_report(exc_type, exc_value, exc_traceback)
        
        # نمایش در کنسول
        print(report)
        
        # ثبت در لاگ
        self.crash_logger.error(f"Bot crashed: {exc_type.__name__}: {exc_value}")
        self.crash_logger.error(report)
        
        return report

# تابع سراسری برای استفاده آسان
_error_detector = None

def get_error_detector() -> ErrorDetector:
    """دریافت نمونه سراسری ErrorDetector"""
    global _error_detector
    if _error_detector is None:
        _error_detector = ErrorDetector()
    return _error_detector

def setup_crash_handler():
    """تنظیم هندلر کرش سراسری"""
    detector = get_error_detector()
    
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        detector.log_crash(exc_type, exc_value, exc_traceback)
    
    sys.excepthook = handle_exception

def quick_environment_check() -> bool:
    """بررسی سریع محیط - True اگر همه چیز OK باشد"""
    detector = get_error_detector()
    env_check = detector.check_environment()
    
    if env_check['critical_issues'] > 0:
        print("🚨 مشکلات حیاتی در محیط شناسایی شد:")
        for issue in env_check['issues']:
            if issue['severity'] == 'critical':
                print(f"❌ {issue['message']}")
                print(f"   راه‌حل: {issue['solution']}")
        return False
    
    if env_check['total_issues'] > 0:
        print("⚠️ مشکلات غیرحیاتی شناسایی شد:")
        for issue in env_check['issues']:
            if issue['severity'] != 'critical':
                print(f"⚠️ {issue['message']}")
    
    return True