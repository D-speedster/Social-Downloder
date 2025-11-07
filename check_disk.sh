#!/bin/bash

# رنگ‌ها
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "======================================================================"
echo "🔍 بررسی وضعیت دیسک و فایل‌ها"
echo "======================================================================"

# 1. فضای دیسک
echo -e "\n${YELLOW}📊 فضای دیسک:${NC}"
df -h | grep -E "Filesystem|/$"

DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 90 ]; then
    echo -e "${RED}⚠️ هشدار: دیسک ${DISK_USAGE}% پر است!${NC}"
elif [ $DISK_USAGE -gt 80 ]; then
    echo -e "${YELLOW}⚠️ توجه: دیسک ${DISK_USAGE}% پر است${NC}"
else
    echo -e "${GREEN}✅ فضای دیسک کافی است (${DISK_USAGE}% استفاده شده)${NC}"
fi

# 2. فضای downloads
echo -e "\n${YELLOW}📁 پوشه downloads:${NC}"
if [ -d "downloads" ]; then
    DOWNLOADS_SIZE=$(du -sh downloads/ | cut -f1)
    FILE_COUNT=$(find downloads/ -type f | wc -l)
    echo "   حجم: $DOWNLOADS_SIZE"
    echo "   تعداد فایل: $FILE_COUNT"
    
    if [ $FILE_COUNT -gt 100 ]; then
        echo -e "${YELLOW}⚠️ تعداد فایل‌ها زیاد است!${NC}"
    fi
else
    echo -e "${RED}❌ پوشه downloads وجود ندارد${NC}"
fi

# 3. inode
echo -e "\n${YELLOW}🔢 وضعیت inode:${NC}"
df -i / | tail -1 | awk '{print "   استفاده: " $5 " از " $2}'

INODE_USAGE=$(df -i / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $INODE_USAGE -gt 90 ]; then
    echo -e "${RED}⚠️ هشدار: inode ${INODE_USAGE}% پر است!${NC}"
else
    echo -e "${GREEN}✅ inode کافی است${NC}"
fi

# 4. فایل‌های قدیمی
echo -e "\n${YELLOW}🕐 فایل‌های قدیمی (بیشتر از 2 ساعت):${NC}"
if [ -d "downloads" ]; then
    OLD_FILES=$(find downloads/ -type f -mmin +120 2>/dev/null | wc -l)
    if [ $OLD_FILES -gt 0 ]; then
        echo -e "${YELLOW}   $OLD_FILES فایل قدیمی یافت شد${NC}"
        echo "   برای پاکسازی: find downloads/ -type f -mmin +120 -delete"
    else
        echo -e "${GREEN}   ✅ هیچ فایل قدیمی یافت نشد${NC}"
    fi
fi

# 5. فایل‌های بزرگ
echo -e "\n${YELLOW}📦 بزرگ‌ترین فایل‌ها:${NC}"
if [ -d "downloads" ]; then
    find downloads/ -type f -exec du -h {} + 2>/dev/null | sort -rh | head -5
fi

# 6. دسترسی‌ها
echo -e "\n${YELLOW}🔐 دسترسی‌های downloads:${NC}"
if [ -d "downloads" ]; then
    ls -ld downloads/
else
    echo -e "${RED}❌ پوشه downloads وجود ندارد${NC}"
fi

echo ""
echo "======================================================================"
echo -e "${GREEN}✅ بررسی تمام شد${NC}"
echo "======================================================================"

# پیشنهادات
if [ $DISK_USAGE -gt 80 ] || [ $FILE_COUNT -gt 100 ]; then
    echo ""
    echo -e "${YELLOW}💡 پیشنهادات:${NC}"
    echo "   1. پاکسازی فایل‌های قدیمی:"
    echo "      find downloads/ -type f -mmin +120 -delete"
    echo ""
    echo "   2. پاکسازی کامل:"
    echo "      rm -rf downloads/*"
    echo ""
    echo "   3. بررسی لاگ‌ها:"
    echo "      du -sh logs/"
    echo "      find logs/ -type f -mtime +7 -delete"
fi
