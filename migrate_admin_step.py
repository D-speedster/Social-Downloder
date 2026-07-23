#!/usr/bin/env python3
"""
اسکریپت مهاجرت خودکار admin_step به AdminUserState
این اسکریپت تمام استفاده‌های admin_step را پیدا و جایگزین می‌کند
"""

import re
import sys

def migrate_admin_step(filepath='plugins/admin.py'):
    """مهاجرت admin_step به AdminUserState"""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes_made = []
    
    # الگوهای مهاجرت
    replacements = [
        # Pattern 1: admin_step['key'] = value
        (
            r"admin_step\['manual_recovery'\]\s*=\s*(\d+)",
            lambda m: f"state.manual_recovery['step'] = {m.group(1)}"
        ),
        (
            r"admin_step\['broadcast'\]\s*=\s*(\d+)",
            lambda m: f"state.broadcast['step'] = {m.group(1)}"
        ),
        (
            r"admin_step\['sp'\]\s*=\s*(\d+)",
            lambda m: f"state.sp = {m.group(1)}"
        ),
        (
            r"admin_step\['advertisement'\]\s*=\s*(\d+)",
            lambda m: f"state.advertisement['step'] = {m.group(1)}"
        ),
        (
            r"admin_step\['waiting_msg'\]\s*=\s*(\d+)",
            lambda m: f"state.waiting_msg['step'] = {m.group(1)}"
        ),
        (
            r"admin_step\['pending_update'\]\s*=\s*(\d+)",
            lambda m: f"state.pending_update = {m.group(1)}"
        ),
        (
            r"admin_step\['help_setup'\]\s*=\s*(\d+)",
            lambda m: f"state.help_setup = {m.group(1)}"
        ),
        (
            r"admin_step\['add_cookie'\]\s*=\s*'(text|file)'",
            lambda m: f"state.add_cookie = '{m.group(1)}'"
        ),
        (
            r"admin_step\['broadcast_type'\]\s*=\s*'(\w+)'",
            lambda m: f"state.broadcast['type'] = '{m.group(1)}'"
        ),
        (
            r"admin_step\['broadcast_content'\]\s*=\s*(None|.*)",
            lambda m: f"state.broadcast['content'] = {m.group(1)}"
        ),
        
        # Pattern 2: admin_step.get('key')
        (
            r"admin_step\.get\('manual_recovery'(?:,\s*\d+)?\)",
            "state.manual_recovery['step']"
        ),
        (
            r"admin_step\.get\('broadcast'(?:,\s*\d+)?\)",
            "state.broadcast['step']"
        ),
        (
            r"admin_step\.get\('sp'(?:,\s*\d+)?\)",
            "state.sp"
        ),
        (
            r"admin_step\.get\('advertisement'(?:,\s*\d+)?\)",
            "state.advertisement['step']"
        ),
        (
            r"admin_step\.get\('waiting_msg'(?:,\s*\d+)?\)",
            "state.waiting_msg['step']"
        ),
        (
            r"admin_step\.get\('add_cookie'\)",
            "state.add_cookie"
        ),
        (
            r"admin_step\.get\('pending_update'(?:,\s*\d+)?\)",
            "state.pending_update"
        ),
        (
            r"admin_step\.get\('help_setup'(?:,\s*\d+)?\)",
            "state.help_setup"
        ),
        (
            r"admin_step\.get\('broadcast_type'(?:,\s*'')?\)",
            "state.broadcast['type']"
        ),
        
        # Pattern 3: admin_step['key'] (read access)
        (
            r"admin_step\['manual_recovery'\]",
            "state.manual_recovery['step']"
        ),
        (
            r"admin_step\['broadcast'\]",
            "state.broadcast['step']"
        ),
        (
            r"admin_step\['sp'\]",
            "state.sp"
        ),
        (
            r"admin_step\['advertisement'\]",
            "state.advertisement['step']"
        ),
        (
            r"admin_step\['waiting_msg'\]",
            "state.waiting_msg['step']"
        ),
        (
            r"admin_step\['broadcast_type'\]",
            "state.broadcast['type']"
        ),
        (
            r"admin_step\['broadcast_content'\]",
            "state.broadcast['content']"
        ),
        
        # Pattern 4: del admin_step['add_cookie']
        (
            r"del admin_step\['add_cookie'\]",
            "state.add_cookie = None"
        ),
        
        # Pattern 5: admin_step.pop('add_cookie', None)
        (
            r"admin_step\.pop\('add_cookie',\s*None\)",
            "state.add_cookie = None"
        ),
        
        # Pattern 6: 'add_cookie' in admin_step
        (
            r"'add_cookie' in admin_step",
            "state.add_cookie is not None"
        ),
    ]
    
    # اعمال تغییرات
    for pattern, replacement in replacements:
        if callable(replacement):
            # regex با lambda
            content = re.sub(pattern, replacement, content)
        else:
            # جایگزینی ساده
            content = re.sub(pattern, replacement, content)
    
    # شمارش تغییرات
    changes = original_content.count('admin_step') - content.count('admin_step')
    
    if content != original_content:
        # نوشتن فایل
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ مهاجرت انجام شد: {changes} مورد admin_step جایگزین شد")
        print(f"⚠️  موارد باقی‌مانده: {content.count('admin_step')}")
        return True
    else:
        print("❌ هیچ تغییری لازم نبود")
        return False

if __name__ == '__main__':
    filepath = 'plugins/admin.py' if len(sys.argv) < 2 else sys.argv[1]
    migrate_admin_step(filepath)
