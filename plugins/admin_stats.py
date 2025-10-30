"""
دستور /stats برای نمایش آمار ربات به ادمین
"""
from pyrogram import Client, filters
from pyrogram.types import Message
from plugins.admin import ADMIN
from plugins.simple_metrics import metrics
from plugins.concurrency import get_queue_stats
import psutil
import os


@Client.on_message(filters.command("stats") & filters.user(ADMIN))
async def show_stats_command(client: Client, message: Message):
    """
    نمایش آمار کامل ربات برای ادمین
    """
    try:
        # دریافت آمار از metrics
        stats = metrics.get_stats()
        
        # دریافت آمار صف
        queue_stats = get_queue_stats()
        
        # دریافت آمار سیستم
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # ساخت متن آمار
        text = "📊 **آمار کامل ربات**\n\n"
        
        # زمان فعالیت
        text += f"⏱️ **زمان فعالیت:** {stats['uptime_hours']:.1f} ساعت\n\n"
        
        # آمار درخواست‌ها
        text += "📨 **درخواست‌ها:**\n"
        text += f"• کل: {stats['total_requests']}\n"
        text += f"• سرعت: {stats['requests_per_minute']:.0f}/دقیقه\n\n"
        
        # آمار دانلود/آپلود
        text += "📥 **دانلود و آپلود:**\n"
        text += f"• دانلودها: {stats['total_downloads']}\n"
        text += f"• آپلودها: {stats['total_uploads']}\n"
        text += f"• خطاها: {stats['total_errors']}\n"
        text += f"• نرخ موفقیت: {stats['success_rate']:.1f}%\n\n"
        
        # زمان‌ها
        if stats['avg_download_time'] > 0 or stats['avg_upload_time'] > 0:
            text += "⏱️ **میانگین زمان‌ها:**\n"
            if stats['avg_download_time'] > 0:
                text += f"• دانلود: {stats['avg_download_time']:.1f}s\n"
            if stats['avg_upload_time'] > 0:
                text += f"• آپلود: {stats['avg_upload_time']:.1f}s\n"
            text += "\n"
        
        # صف دانلود
        text += "🔄 **صف دانلود:**\n"
        text += f"• ظرفیت: {queue_stats['capacity']}\n"
        text += f"• فعال: {queue_stats['active']}\n"
        text += f"• در انتظار: {queue_stats['waiting']}\n"
        text += f"• آزاد: {queue_stats['available']}\n\n"
        
        # منابع سیستم
        text += "💻 **منابع سیستم:**\n"
        text += f"• CPU: {cpu_percent:.1f}%\n"
        text += f"• RAM: {stats['memory_mb']:.0f} MB / {memory.total / 1024 / 1024:.0f} MB ({memory.percent:.1f}%)\n"
        text += f"• Disk: {disk.used / 1024 / 1024 / 1024:.1f} GB / {disk.total / 1024 / 1024 / 1024:.1f} GB ({disk.percent:.1f}%)\n\n"
        
        # آمار پلتفرم‌ها
        if stats['platform_stats']:
            text += "📱 **آمار پلتفرم‌ها:**\n"
            for platform, pstats in sorted(stats['platform_stats'].items(), 
                                          key=lambda x: x[1]['downloads'], 
                                          reverse=True):
                if pstats['downloads'] > 0 or pstats['errors'] > 0:
                    success_rate = (pstats['downloads'] / (pstats['downloads'] + pstats['errors']) * 100) if (pstats['downloads'] + pstats['errors']) > 0 else 0
                    text += f"• {platform}: {pstats['downloads']} ✅ | {pstats['errors']} ❌ ({success_rate:.0f}%)\n"
        
        await message.reply_text(text)
        
    except Exception as e:
        await message.reply_text(f"❌ خطا در دریافت آمار: {e}")


@Client.on_message(filters.command("health") & filters.user(ADMIN))
async def health_check_command(client: Client, message: Message):
    """
    بررسی سلامت سیستم
    """
    try:
        # بررسی CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_status = "✅" if cpu_percent < 80 else "⚠️" if cpu_percent < 95 else "🔴"
        
        # بررسی RAM
        memory = psutil.virtual_memory()
        ram_status = "✅" if memory.percent < 80 else "⚠️" if memory.percent < 95 else "🔴"
        
        # بررسی Disk
        disk = psutil.disk_usage('/')
        disk_status = "✅" if disk.percent < 80 else "⚠️" if disk.percent < 95 else "🔴"
        
        # بررسی صف
        queue_stats = get_queue_stats()
        queue_usage = (queue_stats['active'] / queue_stats['capacity'] * 100) if queue_stats['capacity'] > 0 else 0
        queue_status = "✅" if queue_usage < 80 else "⚠️" if queue_usage < 100 else "🔴"
        
        # وضعیت کلی
        all_ok = all(s == "✅" for s in [cpu_status, ram_status, disk_status, queue_status])
        overall_status = "✅ سالم" if all_ok else "⚠️ نیاز به توجه" if "🔴" not in [cpu_status, ram_status, disk_status, queue_status] else "🔴 مشکل حیاتی"
        
        text = f"🏥 **بررسی سلامت سیستم**\n\n"
        text += f"**وضعیت کلی:** {overall_status}\n\n"
        text += f"{cpu_status} **CPU:** {cpu_percent:.1f}%\n"
        text += f"{ram_status} **RAM:** {memory.percent:.1f}%\n"
        text += f"{disk_status} **Disk:** {disk.percent:.1f}%\n"
        text += f"{queue_status} **Queue:** {queue_usage:.0f}% ({queue_stats['active']}/{queue_stats['capacity']})\n\n"
        
        if not all_ok:
            text += "⚠️ **توصیه‌ها:**\n"
            if cpu_status != "✅":
                text += "• CPU بالاست - بررسی process های سنگین\n"
            if ram_status != "✅":
                text += "• RAM بالاست - ممکن است نیاز به restart باشد\n"
            if disk_status != "✅":
                text += "• Disk پر است - فایل‌های قدیمی را پاک کنید\n"
            if queue_status != "✅":
                text += "• صف پر است - افزایش capacity یا منتظر بمانید\n"
        
        await message.reply_text(text)
        
    except Exception as e:
        await message.reply_text(f"❌ خطا در بررسی سلامت: {e}")


@Client.on_message(filters.command("reset_stats") & filters.user(ADMIN))
async def reset_stats_command(client: Client, message: Message):
    """
    ریست کردن آمار (برای تست)
    """
    try:
        from plugins.simple_metrics import SimpleMetrics
        global metrics
        
        # ایجاد instance جدید
        metrics = SimpleMetrics()
        
        await message.reply_text("✅ آمار با موفقیت ریست شد!")
        
    except Exception as e:
        await message.reply_text(f"❌ خطا در ریست آمار: {e}")


@Client.on_message(filters.command("circuit") & filters.user(ADMIN))
async def circuit_breaker_status(client: Client, message: Message):
    """
    نمایش وضعیت circuit breakers
    """
    try:
        from plugins.circuit_breaker import circuit_manager
        
        stats = circuit_manager.get_all_stats()
        
        if not stats:
            await message.reply_text("⚡ هیچ circuit breaker فعالی وجود ندارد.")
            return
        
        text = "⚡ **وضعیت Circuit Breakers**\n\n"
        
        for name, breaker_stats in stats.items():
            state = breaker_stats['state']
            
            # انتخاب emoji بر اساس وضعیت
            if state == 'closed':
                emoji = "✅"
                state_text = "عادی"
            elif state == 'open':
                emoji = "🔴"
                state_text = "خطا"
            else:  # half_open
                emoji = "⚠️"
                state_text = "تست"
            
            text += f"{emoji} **{name}**\n"
            text += f"   وضعیت: {state_text}\n"
            text += f"   خطاها: {breaker_stats['failure_count']}\n"
            text += f"   موفقیت‌ها: {breaker_stats['success_count']}\n"
            text += f"   زمان: {breaker_stats['uptime']:.0f}s\n\n"
        
        await message.reply_text(text)
        
    except Exception as e:
        await message.reply_text(f"❌ خطا در دریافت وضعیت: {e}")


@Client.on_message(filters.command("cleanup") & filters.user(ADMIN))
async def manual_cleanup_command(client: Client, message: Message):
    """
    اجرای دستی پاکسازی
    """
    try:
        from plugins.auto_cleanup import auto_cleanup
        
        await message.reply_text("🧹 در حال پاکسازی...")
        
        stats = auto_cleanup.cleanup_temp_files()
        
        text = "✅ **پاکسازی انجام شد**\n\n"
        text += f"📁 فایل‌های پاک شده: {stats['deleted_count']}\n"
        text += f"💾 فضای آزاد شده: {stats['freed_mb']:.2f} MB"
        
        await message.reply_text(text)
        
    except Exception as e:
        await message.reply_text(f"❌ خطا در پاکسازی: {e}")


print("✅ Admin stats commands loaded")
print("   - /stats: نمایش آمار کامل")
print("   - /health: بررسی سلامت سیستم")
print("   - /reset_stats: ریست آمار")
print("   - /circuit: وضعیت circuit breakers")
print("   - /cleanup: پاکسازی دستی")
