#!/bin/bash

echo "🔍 بررسی تغییرات عملکرد"
echo "================================"

# رنگ‌ها
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# تابع بررسی
check_fix() {
    local name="$1"
    local pattern="$2"
    local file="$3"
    
    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo -e "${GREEN}✅ $name${NC}"
        return 0
    else
        echo -e "${RED}❌ $name${NC}"
        return 1
    fi
}

echo ""
echo "📁 بررسی فایل youtube_helpers.py:"
echo "-----------------------------------"

# بررسی FFmpegVideoRemuxer
check_fix "FFmpegVideoRemuxer" "FFmpegVideoRemuxer" "plugins/youtube_helpers.py"

# بررسی stream copy
check_fix "Stream Copy (-c:v copy)" "'-c:v', 'copy'" "plugins/youtube_helpers.py"

# بررسی faststart
check_fix "Faststart flag" "'+faststart'" "plugins/youtube_helpers.py"

# بررسی throttling 3 ثانیه
check_fix "Progress throttling (3s)" "3.0 or" "plugins/youtube_helpers.py"

# بررسی 15% threshold
check_fix "Progress threshold (15%)" "15" "plugins/youtube_helpers.py"

# بررسی /dev/shm
check_fix "RAM disk (/dev/shm)" "/dev/shm" "plugins/youtube_helpers.py"

# بررسی حذف unwanted files
check_fix "Disable thumbnail" "writethumbnail.*False" "plugins/youtube_helpers.py"
check_fix "Disable infojson" "writeinfojson.*False" "plugins/youtube_helpers.py"

echo ""
echo "🔧 بررسی محیط سیستم:"
echo "-----------------------------------"

# بررسی FFmpeg
if command -v ffmpeg &> /dev/null; then
    echo -e "${GREEN}✅ FFmpeg نصب شده${NC}"
    ffmpeg -version | head -n 1
else
    echo -e "${RED}❌ FFmpeg نصب نیست${NC}"
fi

# بررسی /dev/shm
if [ -d "/dev/shm" ] && [ -w "/dev/shm" ]; then
    echo -e "${GREEN}✅ /dev/shm قابل نوشتن است${NC}"
    df -h /dev/shm | tail -n 1
else
    echo -e "${YELLOW}⚠️ /dev/shm در دسترس نیست (Windows یا محدودیت)${NC}"
fi

# بررسی CPU cores
echo -e "${GREEN}✅ CPU Cores: $(nproc)${NC}"

# بررسی RAM
echo -e "${GREEN}✅ RAM: $(free -h | awk '/^Mem:/ {print $2}')${NC}"

echo ""
echo "🤖 بررسی وضعیت ربات:"
echo "-----------------------------------"

if pgrep -f "main.py" > /dev/null; then
    echo -e "${GREEN}✅ ربات در حال اجرا است${NC}"
    echo "PID: $(pgrep -f main.py)"
    echo ""
    echo -e "${YELLOW}💡 برای اعمال تغییرات، ربات را ری‌استارت کنید:${NC}"
    echo "   pkill -f main.py && python3 main.py"
else
    echo -e "${RED}❌ ربات در حال اجرا نیست${NC}"
    echo ""
    echo -e "${YELLOW}💡 برای شروع ربات:${NC}"
    echo "   python3 main.py"
fi

echo ""
echo "================================"
echo "✅ بررسی تکمیل شد"
echo ""
echo "📊 انتظار بهبود عملکرد:"
echo "   - ویدیوی 10 دقیقه‌ای: 60% سریع‌تر"
echo "   - ویدیوی 862MB: 80% سریع‌تر"
echo "   - CPU usage در FFmpeg: 15-25% (به جای 95-100%)"