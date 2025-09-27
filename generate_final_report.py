"""
Final Test Report Generator
گزارش نهایی تست‌ها
"""

import json
import os
from datetime import datetime
from pathlib import Path

class FinalReportGenerator:
    def __init__(self):
        self.test_files = [
            'final_integration_test_results.json',
            'bot_integration_test_results.json', 
            'performance_test_results.json',
            'error_handling_test_results.json'
        ]
        self.report_data = {}
        
    def load_test_results(self):
        """Load all test result files"""
        print("📊 بارگذاری نتایج تست‌ها...")
        
        for test_file in self.test_files:
            if os.path.exists(test_file):
                try:
                    with open(test_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        test_name = test_file.replace('_test_results.json', '').replace('_results.json', '')
                        self.report_data[test_name] = data
                        print(f"  ✅ {test_file} بارگذاری شد")
                except Exception as e:
                    print(f"  ❌ خطا در بارگذاری {test_file}: {e}")
            else:
                print(f"  ⚠️ فایل {test_file} یافت نشد")
    
    def analyze_integration_tests(self):
        """Analyze integration test results"""
        integration_data = self.report_data.get('final_integration', {})
        # Check both 'results' and 'tests' keys for different test result formats
        results = integration_data.get('results', integration_data.get('tests', {}))
        
        analysis = {
            'total_tests': len(results),
            'passed_tests': sum(1 for r in results.values() if r.get('status') in ['success', 'PASS']),
            'failed_tests': sum(1 for r in results.values() if r.get('status') in ['failed', 'FAIL']),
            'skipped_tests': sum(1 for r in results.values() if r.get('status') in ['skipped', 'SKIP']),
            'success_rate': 0,
            'critical_issues': [],
            'recommendations': []
        }
        
        if analysis['total_tests'] > 0:
            analysis['success_rate'] = (analysis['passed_tests'] / analysis['total_tests']) * 100
        
        # Identify critical issues
        for test_name, result in results.items():
            if result.get('status') in ['failed', 'FAIL']:
                error_msg = result.get('error', result.get('details', {}).get('error', 'Unknown error'))
                analysis['critical_issues'].append({
                    'test': test_name,
                    'error': error_msg,
                    'severity': 'high' if 'error_handling' in test_name.lower() else 'medium'
                })
        
        # Generate recommendations
        if analysis['success_rate'] < 90:
            analysis['recommendations'].append("بهبود پایداری سیستم - نرخ موفقیت کمتر از 90%")
        
        if any('network' in issue['error'].lower() for issue in analysis['critical_issues']):
            analysis['recommendations'].append("بهبود مدیریت خطاهای شبکه")
            
        return analysis
    
    def analyze_bot_integration(self):
        """Analyze bot integration test results"""
        bot_data = self.report_data.get('bot_integration', {})
        results = bot_data.get('results', {})
        
        analysis = {
            'total_tests': len(results),
            'passed_tests': sum(1 for r in results.values() if r.get('status') == 'success'),
            'success_rate': 0,
            'async_issues': [],
            'recommendations': []
        }
        
        if analysis['total_tests'] > 0:
            analysis['success_rate'] = (analysis['passed_tests'] / analysis['total_tests']) * 100
        
        # Check for async-related issues
        for test_name, result in results.items():
            if result.get('status') == 'failed' and 'async' in result.get('error', '').lower():
                analysis['async_issues'].append(test_name)
        
        # Generate recommendations
        if analysis['success_rate'] == 100:
            analysis['recommendations'].append("عملکرد عالی - تمام تست‌های ربات موفق")
        elif analysis['async_issues']:
            analysis['recommendations'].append("بررسی مدیریت async/await در ربات")
            
        return analysis
    
    def analyze_performance_tests(self):
        """Analyze performance test results"""
        perf_data = self.report_data.get('performance', {})
        results = perf_data.get('results', {})
        
        analysis = {
            'download_speed': 0,
            'memory_usage': 0,
            'concurrent_ops': 0,
            'performance_grade': 'Unknown',
            'bottlenecks': [],
            'recommendations': []
        }
        
        # Extract performance metrics
        if 'download_performance' in results:
            download_perf = results['download_performance']
            analysis['download_speed'] = download_perf.get('average_speed_mbps', 0)
        
        if 'memory_usage' in results:
            memory_perf = results['memory_usage']
            analysis['memory_usage'] = memory_perf.get('memory_increase_mb', 0)
        
        if 'concurrent_operations' in results:
            concurrent_perf = results['concurrent_operations']
            analysis['concurrent_ops'] = concurrent_perf.get('operations_per_second', 0)
        
        # Grade performance
        if analysis['download_speed'] > 10:
            analysis['performance_grade'] = 'Excellent'
        elif analysis['download_speed'] > 5:
            analysis['performance_grade'] = 'Good'
        elif analysis['download_speed'] > 2:
            analysis['performance_grade'] = 'Fair'
        else:
            analysis['performance_grade'] = 'Poor'
        
        # Identify bottlenecks
        if analysis['memory_usage'] > 100:
            analysis['bottlenecks'].append('High memory usage')
        
        if analysis['concurrent_ops'] < 1000:
            analysis['bottlenecks'].append('Low concurrent operation performance')
        
        # Generate recommendations
        if analysis['performance_grade'] in ['Poor', 'Fair']:
            analysis['recommendations'].append('بهینه‌سازی سرعت دانلود')
        
        if analysis['memory_usage'] > 50:
            analysis['recommendations'].append('بهینه‌سازی مصرف حافظه')
            
        return analysis
    
    def analyze_error_handling(self):
        """Analyze error handling test results"""
        error_data = self.report_data.get('error_handling', {})
        results = error_data.get('results', {})
        
        analysis = {
            'total_categories': len(results),
            'robust_categories': sum(1 for r in results.values() if r.get('status') == 'success'),
            'overall_robustness': 0,
            'weak_areas': [],
            'recommendations': []
        }
        
        if analysis['total_categories'] > 0:
            analysis['overall_robustness'] = (analysis['robust_categories'] / analysis['total_categories']) * 100
        
        # Identify weak areas
        for category, result in results.items():
            if result.get('status') == 'failed':
                success_rate = result.get('success_rate', 0)
                analysis['weak_areas'].append({
                    'category': category,
                    'success_rate': success_rate
                })
        
        # Generate recommendations
        if analysis['overall_robustness'] == 100:
            analysis['recommendations'].append('مدیریت خطای عالی - سیستم بسیار مقاوم')
        elif analysis['overall_robustness'] >= 80:
            analysis['recommendations'].append('مدیریت خطای خوب - نیاز به بهبودهای جزئی')
        else:
            analysis['recommendations'].append('نیاز به بهبود قابل توجه در مدیریت خطا')
            
        return analysis
    
    def generate_summary_statistics(self):
        """Generate overall summary statistics"""
        # Integration tests
        integration_analysis = self.analyze_integration_tests()
        
        # Bot integration
        bot_analysis = self.analyze_bot_integration()
        
        # Performance
        performance_analysis = self.analyze_performance_tests()
        
        # Error handling
        error_analysis = self.analyze_error_handling()
        
        summary = {
            'overall_health': 'Unknown',
            'total_tests_run': (
                integration_analysis['total_tests'] + 
                bot_analysis['total_tests'] + 
                error_analysis['total_categories']
            ),
            'overall_success_rate': 0,
            'key_strengths': [],
            'areas_for_improvement': [],
            'critical_recommendations': []
        }
        
        # Calculate overall success rate
        success_rates = [
            integration_analysis['success_rate'],
            bot_analysis['success_rate'],
            error_analysis['overall_robustness']
        ]
        
        if success_rates:
            summary['overall_success_rate'] = sum(success_rates) / len(success_rates)
        
        # Determine overall health
        if summary['overall_success_rate'] >= 95:
            summary['overall_health'] = 'Excellent'
        elif summary['overall_success_rate'] >= 85:
            summary['overall_health'] = 'Good'
        elif summary['overall_success_rate'] >= 70:
            summary['overall_health'] = 'Fair'
        else:
            summary['overall_health'] = 'Poor'
        
        # Identify key strengths
        if bot_analysis['success_rate'] == 100:
            summary['key_strengths'].append('Telegram Bot Integration')
        
        if error_analysis['overall_robustness'] == 100:
            summary['key_strengths'].append('Error Handling & Recovery')
        
        if performance_analysis['performance_grade'] in ['Excellent', 'Good']:
            summary['key_strengths'].append('Download Performance')
        
        # Areas for improvement
        if integration_analysis['success_rate'] < 95:
            summary['areas_for_improvement'].append('Core Integration Stability')
        
        if performance_analysis['bottlenecks']:
            summary['areas_for_improvement'].extend(performance_analysis['bottlenecks'])
        
        # Critical recommendations
        all_recommendations = (
            integration_analysis['recommendations'] +
            bot_analysis['recommendations'] +
            performance_analysis['recommendations'] +
            error_analysis['recommendations']
        )
        
        # Prioritize unique recommendations
        summary['critical_recommendations'] = list(set(all_recommendations))
        
        return summary, integration_analysis, bot_analysis, performance_analysis, error_analysis
    
    def generate_markdown_report(self):
        """Generate comprehensive markdown report"""
        summary, integration, bot, performance, error = self.generate_summary_statistics()
        
        report = f"""# 📊 گزارش نهایی تست سیستم دانلودر یوتیوب
## Final Test Report - YouTube Downloader System

**تاریخ گزارش:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**وضعیت کلی سیستم:** {summary['overall_health']}  
**نرخ موفقیت کلی:** {summary['overall_success_rate']:.1f}%

---

## 🎯 خلاصه اجرایی (Executive Summary)

سیستم دانلودر یوتیوب تحت {summary['total_tests_run']} تست جامع قرار گرفت که شامل تست‌های یکپارچگی، عملکرد، مدیریت خطا و ربات تلگرام می‌باشد.

### 🏆 نقاط قوت کلیدی:
"""
        
        for strength in summary['key_strengths']:
            report += f"- ✅ {strength}\n"
        
        if not summary['key_strengths']:
            report += "- نقاط قوت خاصی شناسایی نشد\n"
        
        report += f"""
### ⚠️ نواحی نیازمند بهبود:
"""
        
        for improvement in summary['areas_for_improvement']:
            report += f"- 🔧 {improvement}\n"
        
        if not summary['areas_for_improvement']:
            report += "- همه بخش‌ها در وضعیت مطلوب\n"
        
        report += f"""
---

## 🔗 نتایج تست یکپارچگی (Integration Tests)

**نرخ موفقیت:** {integration['success_rate']:.1f}%  
**تست‌های موفق:** {integration['passed_tests']}/{integration['total_tests']}  
**تست‌های ناموفق:** {integration['failed_tests']}  
**تست‌های رد شده:** {integration['skipped_tests']}

### مسائل بحرانی:
"""
        
        for issue in integration['critical_issues']:
            severity_icon = "🚨" if issue['severity'] == 'high' else "⚠️"
            report += f"- {severity_icon} **{issue['test']}**: {issue['error']}\n"
        
        if not integration['critical_issues']:
            report += "- هیچ مسئله بحرانی شناسایی نشد\n"
        
        report += f"""
---

## 🤖 نتایج تست ربات تلگرام (Bot Integration)

**نرخ موفقیت:** {bot['success_rate']:.1f}%  
**تست‌های موفق:** {bot['passed_tests']}/{bot['total_tests']}

### مسائل Async:
"""
        
        for issue in bot['async_issues']:
            report += f"- 🔄 {issue}\n"
        
        if not bot['async_issues']:
            report += "- هیچ مسئله async شناسایی نشد\n"
        
        report += f"""
---

## ⚡ نتایج تست عملکرد (Performance Tests)

**درجه عملکرد:** {performance['performance_grade']}  
**سرعت دانلود:** {performance['download_speed']:.2f} MB/s  
**مصرف حافظه:** {performance['memory_usage']:.2f} MB  
**عملیات همزمان:** {performance['concurrent_ops']:.0f} ops/s

### گلوگاه‌های عملکرد:
"""
        
        for bottleneck in performance['bottlenecks']:
            report += f"- 🐌 {bottleneck}\n"
        
        if not performance['bottlenecks']:
            report += "- هیچ گلوگاه عملکردی شناسایی نشد\n"
        
        report += f"""
---

## 🛡️ نتایج تست مدیریت خطا (Error Handling)

**مقاومت کلی:** {error['overall_robustness']:.1f}%  
**دسته‌های مقاوم:** {error['robust_categories']}/{error['total_categories']}

### نواحی ضعیف:
"""
        
        for weak_area in error['weak_areas']:
            report += f"- 🔴 **{weak_area['category']}**: {weak_area['success_rate']:.1f}% موفقیت\n"
        
        if not error['weak_areas']:
            report += "- همه دسته‌ها مقاومت مطلوب دارند\n"
        
        report += f"""
---

## 📋 توصیه‌های بحرانی (Critical Recommendations)

### اولویت بالا:
"""
        
        high_priority = summary['critical_recommendations'][:3]  # Top 3 recommendations
        for i, rec in enumerate(high_priority, 1):
            report += f"{i}. 🎯 {rec}\n"
        
        if len(summary['critical_recommendations']) > 3:
            report += f"\n### سایر توصیه‌ها:\n"
            for rec in summary['critical_recommendations'][3:]:
                report += f"- 💡 {rec}\n"
        
        report += f"""
---

## 📈 نتیجه‌گیری و مسیر آینده

"""
        
        if summary['overall_health'] == 'Excellent':
            report += """🎉 **سیستم در وضعیت عالی قرار دارد!**

سیستم دانلودر یوتیوب عملکرد بسیار مطلوبی از خود نشان داده و آماده استفاده در محیط تولید می‌باشد. تمام اجزای اصلی به درستی کار می‌کنند و مدیریت خطا در سطح مطلوبی قرار دارد.
"""
        elif summary['overall_health'] == 'Good':
            report += """✅ **سیستم در وضعیت خوبی قرار دارد**

سیستم عملکرد قابل قبولی دارد اما برای بهبود کیفیت، توصیه می‌شود موارد ذکر شده در بالا بررسی و اصلاح شوند.
"""
        elif summary['overall_health'] == 'Fair':
            report += """⚠️ **سیستم نیاز به بهبود دارد**

قبل از استفاده در محیط تولید، لازم است مسائل شناسایی شده برطرف شوند. توصیه می‌شود ابتدا مسائل بحرانی حل شوند.
"""
        else:
            report += """🚨 **سیستم نیاز به بازنگری جدی دارد**

سیستم در وضعیت فعلی آماده استفاده در تولید نیست. لازم است تمام مسائل شناسایی شده به طور کامل برطرف شوند.
"""
        
        report += f"""
### مراحل بعدی پیشنهادی:

1. **بررسی و رفع مسائل بحرانی** - اولویت اول
2. **بهینه‌سازی عملکرد** - بهبود سرعت و کاهش مصرف منابع  
3. **تقویت مدیریت خطا** - افزایش مقاومت سیستم
4. **تست‌های اضافی** - تست در شرایط واقعی و بار بالا
5. **مستندسازی** - تکمیل مستندات فنی و راهنمای کاربر

---

**📝 این گزارش به صورت خودکار در تاریخ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} تولید شده است.**

**🔍 برای جزئیات بیشتر، فایل‌های JSON نتایج تست‌ها را مطالعه کنید.**
"""
        
        return report
    
    def save_report(self):
        """Save the final report"""
        print("\n📝 تولید گزارش نهایی...")
        
        # Generate markdown report
        markdown_report = self.generate_markdown_report()
        
        # Save markdown report
        with open('FINAL_TEST_REPORT.md', 'w', encoding='utf-8') as f:
            f.write(markdown_report)
        
        # Generate JSON summary
        summary, integration, bot, performance, error = self.generate_summary_statistics()
        
        json_report = {
            'report_timestamp': datetime.now().isoformat(),
            'summary': summary,
            'detailed_analysis': {
                'integration_tests': integration,
                'bot_integration': bot,
                'performance_tests': performance,
                'error_handling': error
            },
            'raw_data': self.report_data
        }
        
        # Save JSON report
        with open('final_test_report_summary.json', 'w', encoding='utf-8') as f:
            json.dump(json_report, f, ensure_ascii=False, indent=2)
        
        print("✅ گزارش نهایی تولید شد:")
        print("  📄 FINAL_TEST_REPORT.md - گزارش کامل")
        print("  📊 final_test_report_summary.json - خلاصه JSON")
        
        return summary['overall_health'], summary['overall_success_rate']

def main():
    """Main report generation function"""
    print("🚀 شروع تولید گزارش نهایی...")
    print("=" * 60)
    
    generator = FinalReportGenerator()
    
    # Load test results
    generator.load_test_results()
    
    # Generate and save report
    health, success_rate = generator.save_report()
    
    print("\n" + "=" * 60)
    print("📊 خلاصه نهایی:")
    print("=" * 60)
    print(f"🏥 وضعیت سیستم: {health}")
    print(f"📈 نرخ موفقیت کلی: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("\n🎉 سیستم آماده استفاده در تولید!")
        return 0
    elif success_rate >= 75:
        print("\n⚠️ سیستم نیاز به بهبودهای جزئی دارد")
        return 1
    else:
        print("\n🚨 سیستم نیاز به بازنگری جدی دارد")
        return 2

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)