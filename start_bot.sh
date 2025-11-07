#!/bin/bash

# رنگ‌ها
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "======================================================================"
echo -e "${BLUE}🚀 راه‌اندازی ربات تلگرام${NC}"
echo "======================================================================"

# 1. بررسی virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${YELLOW}⚠️ Virtual environment فعال نیست${NC}"
    if [ -d "venv" ]; then
        echo -e "${GREEN}✅ فعال‌سازی venv...${NC}"
        source venv/bin/activate
    else
        echo -e "${RED}❌ venv یافت نشد!${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Virtual environment فعال است${NC}"
fi

# 2. توقف پروسس‌های قدیمی
echo -e "\n${YELLOW}🛑 بررسی پروسس‌های قدیمی...${NC}"
OLD_PIDS=$(ps aux | grep "[p]ython.*bot.py" | awk '{print $2}')
if [ -n "$OLD_PIDS" ]; then
    echo -e "${YELLOW}⚠️ پروسس‌های قدیمی یافت شد:${NC}"
    echo "$OLD_PIDS"
    echo -e "${YELLOW}در حال توقف...${NC}"
    echo "$OLD_PIDS" | xargs kill -9 2>/dev/null
    sleep 2
    echo -e "${GREEN}✅ پروسس‌های قدیمی متوقف شدند${NC}"
else
    echo -e "${GREEN}✅ هیچ پروسس قدیمی یافت نشد${NC}"
fi

# 3. پاکسازی session های قفل شده
echo -e "\n${YELLOW}🧹 پاکسازی session های قفل شده...${NC}"
JOURNAL_FILES=$(ls *.session-journal 2>/dev/null)
if [ -n "$JOURNAL_FILES" ]; then
    echo -e "${YELLOW}⚠️ Session های قفل شده یافت شد${NC}"
    rm -f *.session-journal
    echo -e "${GREEN}✅ Session های قفل شده پاک شدند${NC}"
else
    echo -e "${GREEN}✅ هیچ session قفل شده‌ای یافت نشد${NC}"
fi

# 4. بررسی فایل‌های ضروری
echo -e "\n${YELLOW}📋 بررسی فایل‌های ضروری...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ فایل .env یافت نشد!${NC}"
    exit 1
fi
if [ ! -f "bot.py" ]; then
    echo -e "${RED}❌ فایل bot.py یافت نشد!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ تمام فایل‌های ضروری موجود است${NC}"

# 5. ساخت پوشه‌های ضروری
echo -e "\n${YELLOW}📁 بررسی پوشه‌ها...${NC}"
mkdir -p logs downloads
echo -e "${GREEN}✅ پوشه‌ها آماده است${NC}"

# 6. راه‌اندازی ربات
echo -e "\n======================================================================"
echo -e "${GREEN}🚀 شروع ربات...${NC}"
echo -e "======================================================================"
echo ""

# اجرا با handling خطا
python bot.py

# بررسی exit code
EXIT_CODE=$?
echo ""
echo "======================================================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ ربات با موفقیت خاتمه یافت${NC}"
else
    echo -e "${RED}❌ ربات با خطا خاتمه یافت (Exit Code: $EXIT_CODE)${NC}"
    echo -e "${YELLOW}💡 برای بررسی خطا:${NC}"
    echo "   tail -n 50 logs/bot.log"
fi
echo "======================================================================"

exit $EXIT_CODE
