#!/bin/bash

# رنگ‌ها برای خروجی بهتر
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "======================================================================"
echo -e "${BLUE}🔍 تشخیص مشکل کرش ربات${NC}"
echo "======================================================================"

# 1. بررسی Python
echo -e "\n${YELLOW}1️⃣ بررسی Python...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✅ $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ Python نصب نیست${NC}"
    exit 1
fi

# 2. بررسی Virtual Environment
echo -e "\n${YELLOW}2️⃣ بررسی Virtual Environment...${NC}"
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo -e "${GREEN}✅ venv فعال است: $VIRTUAL_ENV${NC}"
else
    echo -e "${RED}⚠️ venv فعال نیست${NC}"
    echo "   برای فعال‌سازی: source venv/bin/activate"
fi

# 3. بررسی فایل‌های ضروری
echo -e "\n${YELLOW}3️⃣ بررسی فایل‌های ضروری...${NC}"
FILES=(".env" "bot.py" "config.py" "requirements.txt")
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ $file${NC}"
    else
        echo -e "${RED}❌ $file یافت نشد${NC}"
    fi
done

# 4. بررسی پوشه‌ها
echo -e "\n${YELLOW}4️⃣ بررسی پوشه‌ها...${NC}"
DIRS=("plugins" "logs" "downloads")
for dir in "${DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✅ $dir/${NC}"
    else
        echo -e "${YELLOW}⚠️ $dir/ یافت نشد - در حال ساخت...${NC}"
        mkdir -p "$dir"
    fi
done

# 5. بررسی ماژول‌های Python
echo -e "\n${YELLOW}5️⃣ بررسی ماژول‌های Python...${NC}"
MODULES=("pyrogram" "yt_dlp" "requests" "aiohttp" "psutil")
for module in "${MODULES[@]}"; do
    if python3 -c "import $module" 2>/dev/null; then
        VERSION=$(python3 -c "import $module; print($module.__version__)" 2>/dev/null || echo "نامشخص")
        echo -e "${GREEN}✅ $module ($VERSION)${NC}"
    else
        echo -e "${RED}❌ $module نصب نیست${NC}"
    fi
done

# 6. بررسی .env
echo -e "\n${YELLOW}6️⃣ بررسی تنظیمات .env...${NC}"
if [ -f ".env" ]; then
    if grep -q "BOT_TOKEN=" .env && [ -n "$(grep BOT_TOKEN= .env | cut -d'=' -f2)" ]; then
        echo -e "${GREEN}✅ BOT_TOKEN تنظیم شده${NC}"
    else
        echo -e "${RED}❌ BOT_TOKEN خالی است${NC}"
    fi
    
    if grep -q "API_ID=" .env && [ -n "$(grep API_ID= .env | cut -d'=' -f2)" ]; then
        echo -e "${GREEN}✅ API_ID تنظیم شده${NC}"
    else
        echo -e "${RED}❌ API_ID خالی است${NC}"
    fi
    
    if grep -q "API_HASH=" .env && [ -n "$(grep API_HASH= .env | cut -d'=' -f2)" ]; then
        echo -e "${GREEN}✅ API_HASH تنظیم شده${NC}"
    else
        echo -e "${RED}❌ API_HASH خالی است${NC}"
    fi
else
    echo -e "${RED}❌ فایل .env یافت نشد${NC}"
fi

# 7. بررسی لاگ‌های اخیر
echo -e "\n${YELLOW}7️⃣ بررسی لاگ‌های اخیر...${NC}"
if [ -f "logs/bot.log" ]; then
    echo -e "${BLUE}آخرین 10 خط لاگ:${NC}"
    echo "----------------------------------------------------------------------"
    tail -n 10 logs/bot.log
    echo "----------------------------------------------------------------------"
    
    # جستجوی خطاها
    if grep -q "ERROR" logs/bot.log; then
        echo -e "\n${RED}⚠️ خطاهای یافت شده در لاگ:${NC}"
        grep "ERROR" logs/bot.log | tail -n 5
    fi
else
    echo -e "${YELLOW}⚠️ فایل لاگ یافت نشد${NC}"
fi

# 8. بررسی پروسس‌های در حال اجرا
echo -e "\n${YELLOW}8️⃣ بررسی پروسس‌های Python...${NC}"
RUNNING=$(ps aux | grep "[p]ython.*bot.py" | wc -l)
if [ $RUNNING -gt 0 ]; then
    echo -e "${GREEN}✅ ربات در حال اجرا است ($RUNNING پروسس)${NC}"
    ps aux | grep "[p]ython.*bot.py"
else
    echo -e "${YELLOW}⚠️ هیچ پروسس bot.py در حال اجرا نیست${NC}"
fi

# 9. بررسی منابع سیستم
echo -e "\n${YELLOW}9️⃣ بررسی منابع سیستم...${NC}"
echo -e "${BLUE}RAM:${NC}"
free -h | grep "Mem:"
echo -e "${BLUE}Disk:${NC}"
df -h . | tail -n 1

# 10. تست سریع
echo -e "\n${YELLOW}🔟 تست سریع اتصال...${NC}"
if [ -f "test_bot_startup.py" ]; then
    echo "در حال اجرای تست..."
    timeout 30 python3 test_bot_startup.py 2>&1 | head -n 20
else
    echo -e "${YELLOW}⚠️ فایل test_bot_startup.py یافت نشد${NC}"
fi

# نتیجه‌گیری
echo -e "\n======================================================================"
echo -e "${BLUE}📋 خلاصه:${NC}"
echo "======================================================================"

if [ -f ".env" ] && command -v python3 &> /dev/null; then
    echo -e "${GREEN}✅ تنظیمات اولیه OK${NC}"
    echo ""
    echo "برای یافتن مشکل دقیق:"
    echo "  1. اجرا کنید: python3 test_bot_startup.py"
    echo "  2. اجرا کنید: python3 run_bot_debug.py"
    echo "  3. لاگ را بررسی کنید: tail -f logs/bot.log"
    echo ""
    echo "برای اجرای ربات:"
    echo "  python3 bot.py"
else
    echo -e "${RED}❌ مشکلات اساسی وجود دارد${NC}"
    echo "لطفاً موارد بالا را بررسی کنید"
fi

echo "======================================================================"
