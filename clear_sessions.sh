#!/bin/bash

# رنگ‌ها
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "======================================================================"
echo -e "${BLUE}🧹 پاکسازی Session ها و Cache${NC}"
echo "======================================================================"

# 1. حذف session ها (در پوشه فعلی و downloads)
SESSION_FILES=$(ls *.session* downloads/*.session* 2>/dev/null)
if [ -n "$SESSION_FILES" ]; then
    echo -e "\n${YELLOW}📁 Session های یافت شده:${NC}"
    echo "$SESSION_FILES" | while read file; do
        echo "   - $file"
    done
    
    echo -e "\n${YELLOW}⚠️ آیا می‌خواهید تمام session ها را حذف کنید؟${NC}"
    read -p "   (yes/no): " confirm
    
    if [[ "$confirm" == "yes" || "$confirm" == "y" || "$confirm" == "بله" ]]; then
        rm -f *.session* downloads/*.session*
        echo -e "${GREEN}✅ تمام session ها پاک شدند${NC}"
    else
        echo -e "${YELLOW}⏭️ لغو شد${NC}"
    fi
else
    echo -e "\n${GREEN}✅ هیچ session یافت نشد${NC}"
fi

# 2. حذف cache توکن
if [ -f ".token_cache" ]; then
    echo -e "\n${YELLOW}📁 فایل cache توکن یافت شد${NC}"
    rm -f .token_cache
    echo -e "${GREEN}✅ حذف شد: .token_cache${NC}"
else
    echo -e "\n${GREEN}✅ هیچ cache توکن یافت نشد${NC}"
fi

# 3. حذف پروسس‌های در حال اجرا
OLD_PIDS=$(ps aux | grep "[p]ython.*bot.py" | awk '{print $2}')
if [ -n "$OLD_PIDS" ]; then
    echo -e "\n${YELLOW}⚠️ پروسس‌های ربات در حال اجرا یافت شد${NC}"
    echo "$OLD_PIDS"
    echo -e "${YELLOW}در حال توقف...${NC}"
    echo "$OLD_PIDS" | xargs kill -9 2>/dev/null
    echo -e "${GREEN}✅ پروسس‌ها متوقف شدند${NC}"
fi

echo ""
echo "======================================================================"
echo -e "${GREEN}✅ پاکسازی تمام شد!${NC}"
echo "======================================================================"
echo ""
echo -e "${BLUE}💡 حالا می‌توانید ربات را اجرا کنید:${NC}"
echo "   python start_bot.py"
echo "   یا"
echo "   bash start_bot.sh"
echo "======================================================================"
