# در youtube_callback_query.py
# خطوط 75-95 تقریباً - بخش download_video

# ❌ کد قدیمی (اشتباه):
# filesize = best_format.get('filesize') or best_format.get('filesize_approx')

# ✅ کد جدید (درست):
def calculate_total_filesize(format_id, formats_list, info_dict):
    """
    محاسبه حجم کل برای format های ترکیبی (video+audio)
    """
    total_size = 0
    
    # اگه format_id شامل + باشه (مثل 137+140)
    if '+' in format_id:
        format_ids = format_id.split('+')
        
        for fid in format_ids:
            # پیدا کردن format مربوطه
            fmt = next((f for f in formats_list if f.get('format_id') == fid), None)
            
            if fmt:
                size = fmt.get('filesize') or fmt.get('filesize_approx')
                
                # اگه size نداشت، تخمین بزن
                if not size:
                    duration = info_dict.get('duration') or 0
                    bitrate = fmt.get('tbr') or fmt.get('abr') or 0
                    
                    if duration and bitrate:
                        # تبدیل kbps به bytes
                        size = int((bitrate * 1000 / 8) * duration)
                
                if size:
                    total_size += size
                    youtube_callback_logger.debug(f"Format {fid}: {size / (1024*1024):.2f} MB")
        
        youtube_callback_logger.info(f"💾 حجم کل محاسبه شده: {total_size / (1024*1024):.2f} MB")
        return total_size
    
    else:
        # اگه format ساده باشه
        fmt = next((f for f in formats_list if f.get('format_id') == format_id), None)
        
        if fmt:
            size = fmt.get('filesize') or fmt.get('filesize_approx')
            
            if not size:
                duration = info_dict.get('duration') or 0
                bitrate = fmt.get('tbr') or 0
                
                if duration and bitrate:
                    size = int((bitrate * 1000 / 8) * duration)
            
            return size
    
    return None


# استفاده در کد:
# جایگزین این خط:
# filesize = best_format.get('filesize') or best_format.get('filesize_approx')

# با این:
filesize = calculate_total_filesize(
    step['format_id'], 
    info['formats'], 
    info
)

# بقیه کد مثل قبل
if not filesize:
    duration = info.get('duration') or 0
    kbps = best_format.get('tbr')
    if duration and kbps:
        try:
            filesize = int((kbps * 1000 / 8) * duration)
        except Exception:
            filesize = None

step['filesize'] = f"{(filesize/1024/1024):.2f} MB" if filesize else "نامشخص"
step['size_bytes'] = int(filesize) if filesize else None