#!/usr/bin/env python3
"""
جایگزینی تمام print() با logger در admin.py
"""
import re

print("🔧 در حال اصلاح print statements...")

# خواندن فایل
with open('plugins/admin.py', 'r', encoding='utf-8') as f:
    content = f.read()

# تعداد print ها
print_count = content.count('print(')
print(f"📊 تعداد print یافت شده: {print_count}")

# جایگزینی print با admin_logger.debug
# الگوها:
# print("[ADMIN] ...") -> admin_logger.debug("[ADMIN] ...")
# print(f"[ADMIN] ...") -> admin_logger.debug(f"[ADMIN] ...")

patterns = [
    (r'print\(\[', 'admin_logger.debug(['),
    (r'print\(f"\[', 'admin_logger.debug(f"['),
    (r'print\(f\'\[', "admin_logger.debug(f'["),
    (r'print\("admin panel"\)', 'admin_logger.debug("admin panel")'),
]

for pattern, replacement in patterns:
    content = re.sub(pattern, replacement, content)

# ذخیره backup
with open('plugins/admin.py.backup', 'w', encoding='utf-8') as f:
    f.write(content)
print("✅ Backup ذخیره شد: plugins/admin.py.backup")

# ذخیره فایل جدید
with open('plugins/admin.py', 'w', encoding='utf-8') as f:
    f.write(content)

# بررسی نتیجه
new_print_count = content.count('print(')
fixed_count = print_count - new_print_count

print(f"✅ {fixed_count} print جایگزین شد")
print(f"⚠️ {new_print_count} print باقی مانده (احتمالاً print های عادی)")
print("\n💡 برای بازگردانی: mv plugins/admin.py.backup plugins/admin.py")
