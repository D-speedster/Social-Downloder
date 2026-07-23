# این ماژول باید هنگام import ایمن باشد و فقط تابع محاسبه حجم را اکسپورت کند.
# هیچ کد اجرایی سراسری (نمونه/دمو) در سطح ماژول وجود ندارد تا خطای NameError رخ ندهد.

from plugins.logger_config import get_logger

filesize_calc_logger = get_logger("filesize_calculation_fix")


def calculate_total_filesize(format_id, formats_list, info_dict):
    """
    محاسبه حجم کل برای یک فرمت (تکی یا ترکیبی ویدیو+صدا) بر اساس اطلاعات yt-dlp.

    - اگر `filesize` / `filesize_approx` موجود باشد، از همان استفاده می‌شود.
    - در غیر این‌صورت، اگر مدت‌زمان (`duration`) و بیت‌ریت (`tbr`/`abr`) موجود باشد، حجم تخمینی محاسبه می‌گردد.
    - برای فرمت‌های ترکیبی مثل `137+251`، حجم هر بخش جداگانه محاسبه و سپس جمع می‌شود.
    - ضریب تصحیح 0.6 برای جبران فشرده‌سازی تلگرام و تخمین دقیق‌تر اعمال می‌شود.

    پارامترها:
    - format_id: شناسه فرمت انتخاب‌شده (ممکن است شامل "+" باشد)
    - formats_list: لیست فرمت‌ها از `info["formats"]`
    - info_dict: دیکشنری کامل `info` شامل کلیدهایی مانند `duration`

    خروجی:
    - اندازه بر حسب بایت (int) یا None اگر قابل محاسبه نباشد.
    """
    try:
        format_id_str = str(format_id)
        total_size = 0
        # ضریب تصحیح برای جبران فشرده‌سازی تلگرام و تخمین دقیق‌تر
        correction_factor = 0.5

        def _estimate_size(fmt):
            # تلاش برای خواندن اندازه واقعی
            size = fmt.get("filesize") or fmt.get("filesize_approx")
            if size:
                # اعمال ضریب تصحیح روی اندازه واقعی
                return int(int(size) * correction_factor)

            # اگر اندازه موجود نبود، از مدت‌زمان و بیت‌ریت تخمین می‌زنیم
            duration = info_dict.get("duration") or 0
            bitrate = fmt.get("tbr") or fmt.get("abr") or 0
            if duration and bitrate:
                try:
                    # bitrate به kbps است؛ تبدیل به Bytes: (kbps * 1000 / 8) * seconds
                    # اعمال ضریب تصحیح روی تخمین بیت‌ریت
                    return int((bitrate * 1000 / 8) * duration * correction_factor)
                except Exception:
                    return None
            return None

        if "+" in format_id_str:
            parts = format_id_str.split("+")
            for fid in parts:
                fmt = next((f for f in formats_list if str(f.get("format_id")) == str(fid)), None)
                if not fmt:
                    continue
                size_part = _estimate_size(fmt)
                if size_part:
                    total_size += size_part
                    try:
                        filesize_calc_logger.debug(
                            f"📦 حجم تخمینی بخش {fid}: {size_part / (1024*1024):.2f} MB"
                        )
                    except Exception:
                        pass
            return total_size if total_size > 0 else None

        # فرمت تکی
        fmt = next((f for f in formats_list if str(f.get("format_id")) == format_id_str), None)
        if not fmt:
            return None
        size_single = _estimate_size(fmt)
        return int(size_single) if size_single else None

    except Exception as e:
        try:
            filesize_calc_logger.warning(f"⚠️ خطا در calculate_total_filesize: {e}")
        except Exception:
            pass
        return None