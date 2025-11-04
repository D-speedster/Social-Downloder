#!/bin/bash

echo "🔍 Memory Leak Detection Script"
echo "================================"
echo ""

# 1. Python process info
echo "📊 Python Process Info:"
ps aux | grep python | grep -v grep | awk '{print "PID: "$2" | CPU: "$3"% | MEM: "$4"% | RSS: "$6"KB | CMD: "$11" "$12" "$13}'
echo ""

# 2. Memory usage
echo "💾 System Memory:"
free -h
echo ""

# 3. Open files
echo "📁 Open Files by Bot:"
BOT_PID=$(pgrep -f bot.py)
if [ -n "$BOT_PID" ]; then
    echo "Bot PID: $BOT_PID"
    echo "Open files: $(lsof -p $BOT_PID 2>/dev/null | wc -l)"
    echo ""
    echo "Top 10 file types:"
    lsof -p $BOT_PID 2>/dev/null | awk '{print $NF}' | grep -E '\.(log|mp4|jpg|tmp|part)$' | sort | uniq -c | sort -rn | head -10
else
    echo "Bot process not found!"
fi
echo ""

# 4. Temp files
echo "🗑️ Temp Files:"
echo "Downloads folder: $(du -sh Downloads 2>/dev/null || echo '0')"
echo "Temp folder: $(du -sh /tmp/*downloader* 2>/dev/null | head -5 || echo 'None')"
echo ""

# 5. Log files size
echo "📝 Log Files:"
du -sh logs/ 2>/dev/null || echo "No logs folder"
echo "Largest logs:"
du -h logs/*.log 2>/dev/null | sort -rh | head -5
echo ""

# 6. Recent errors
echo "⚠️ Recent Errors (last 20):"
tail -100 logs/*.log 2>/dev/null | grep -i "error\|warning\|memory\|leak" | tail -20
echo ""

# 7. Process threads
echo "🧵 Process Threads:"
if [ -n "$BOT_PID" ]; then
    ps -T -p $BOT_PID | wc -l
    echo "threads"
fi
echo ""

# 8. Memory map
echo "🗺️ Memory Map (top 10):"
if [ -n "$BOT_PID" ]; then
    pmap -x $BOT_PID 2>/dev/null | sort -k3 -rn | head -10
fi
echo ""

echo "✅ Done!"
echo ""
echo "💡 To fix memory issues:"
echo "   1. Restart bot: systemctl restart bot"
echo "   2. Clear temp files: rm -rf Downloads/* /tmp/*downloader*"
echo "   3. Rotate logs: truncate -s 0 logs/*.log"
