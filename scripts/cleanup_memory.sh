#!/bin/bash

echo "🧹 Memory Cleanup Script"
echo "======================="
echo ""

# 1. Clear temp downloads
echo "📁 Clearing temp downloads..."
if [ -d "Downloads" ]; then
    rm -rf Downloads/*
    echo "✅ Downloads cleared"
else
    echo "⚠️ Downloads folder not found"
fi
echo ""

# 2. Clear system temp files
echo "🗑️ Clearing system temp files..."
rm -rf /tmp/*downloader* /tmp/*youtube* /tmp/*instagram* 2>/dev/null
echo "✅ System temp cleared"
echo ""

# 3. Rotate large logs
echo "📝 Rotating large logs..."
for log in logs/*.log; do
    if [ -f "$log" ]; then
        size=$(du -m "$log" | cut -f1)
        if [ "$size" -gt 100 ]; then
            echo "  Rotating $log (${size}MB)"
            mv "$log" "${log}.old"
            touch "$log"
        fi
    fi
done
echo "✅ Logs rotated"
echo ""

# 4. Clear Python cache
echo "🐍 Clearing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
echo "✅ Python cache cleared"
echo ""

# 5. Check memory after cleanup
echo "💾 Memory after cleanup:"
free -h
echo ""

# 6. Suggest restart if needed
MEM_USAGE=$(free | grep Mem | awk '{print ($3/$2) * 100.0}')
if (( $(echo "$MEM_USAGE > 90" | bc -l) )); then
    echo "⚠️ Memory still high (${MEM_USAGE}%)"
    echo "💡 Recommended: Restart bot"
    echo "   systemctl restart bot"
else
    echo "✅ Memory usage OK (${MEM_USAGE}%)"
fi
echo ""

echo "✅ Cleanup complete!"
