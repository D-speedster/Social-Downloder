#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""نمایش آمار Instagram"""

import sys
import os

# اضافه کردن مسیر plugins
sys.path.insert(0, os.path.dirname(__file__))

from plugins.insta_stats import insta_stats

def main():
    print(insta_stats.get_summary())

if __name__ == "__main__":
    main()
