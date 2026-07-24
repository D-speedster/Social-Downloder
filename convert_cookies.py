#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
تبدیل cookie.json به فرمت Netscape
"""

import json
import time

def convert_json_to_netscape(json_file, output_file):
    """تبدیل فایل JSON cookie به فرمت Netscape"""
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # هدر Netscape
            f.write("# Netscape HTTP Cookie File\n")
            f.write("# This is a generated file! Do not edit.\n\n")
            
            for cookie in cookies:
                # استخراج فیلدها
                domain = cookie.get('domain', '')
                flag = 'TRUE' if domain.startswith('.') else 'FALSE'
                path = cookie.get('path', '/')
                secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
                
                # محاسبه expiry
                expires = cookie.get('expirationDate', 0)
                if expires == 0:
                    expires = int(time.time()) + 365*24*3600  # یک سال از الان
                else:
                    expires = int(expires)
                
                name = cookie.get('name', '')
                value = cookie.get('value', '')
                
                # نوشتن خط cookie در فرمت Netscape
                # domain	flag	path	secure	expires	name	value
                line = f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}\n"
                f.write(line)
        
        print(f"✅ تبدیل موفق: {json_file} → {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ خطا در تبدیل: {str(e)}")
        return False

if __name__ == "__main__":
    # تبدیل cookie.json به فرمت Netscape
    success = convert_json_to_netscape("cookie.json", "cookie_netscape.txt")
    
    if success:
        print("🎉 فایل کوکی آماده استفاده است: cookie_netscape.txt")
    else:
        print("❌ خطا در تبدیل فایل کوکی")