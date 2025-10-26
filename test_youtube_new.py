"""
تست سیستم جدید یوتیوب
"""

import asyncio
from plugins.youtube_handler import extract_video_info, create_quality_keyboard

async def test_extract_info():
    """تست استخراج اطلاعات ویدیو"""
    print("🧪 تست استخراج اطلاعات ویدیو...")
    
    # یک لینک تست (ویدیو کوتاه)
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    try:
        info = await extract_video_info(test_url)
        
        if info:
            print("✅ استخراج موفق!")
            print(f"   عنوان: {info['title']}")
            print(f"   مدت زمان: {info['duration']} ثانیه")
            print(f"   کانال: {info['uploader']}")
            print(f"   کیفیت‌های موجود: {list(info['qualities'].keys())}")
            
            # تست ایجاد کیبورد
            keyboard = create_quality_keyboard(info['qualities'])
            print(f"✅ کیبورد ایجاد شد با {len(keyboard.inline_keyboard)} ردیف")
            
            return True
        else:
            print("❌ استخراج ناموفق")
            return False
            
    except Exception as e:
        print(f"❌ خطا: {e}")
        return False

async def main():
    """تست اصلی"""
    print("=" * 50)
    print("تست سیستم جدید یوتیوب")
    print("=" * 50)
    
    success = await test_extract_info()
    
    print("=" * 50)
    if success:
        print("✅ همه تست‌ها موفق بودند!")
    else:
        print("❌ برخی تست‌ها ناموفق بودند")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
