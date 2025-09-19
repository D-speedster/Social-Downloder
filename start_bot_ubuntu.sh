#!/bin/bash

# YouTube/Instagram Bot Ubuntu Startup Script
# This script sets up and runs the bot without sudo privileges

echo "🟢 Starting YouTube/Instagram Bot Setup for Ubuntu..."

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install packages without sudo (using user space)
install_user_packages() {
    echo "🔹 Setting up user-space package manager..."
    
    # Create local bin directory
    mkdir -p ~/.local/bin
    export PATH="$HOME/.local/bin:$PATH"
    
    # Add to bashrc for persistence
    if ! grep -q "export PATH=\$HOME/.local/bin:\$PATH" ~/.bashrc; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    fi
}

# 1️⃣ Check Python installation
echo "🔹 Checking Python installation..."
if ! command_exists python3; then
    echo "❌ Python3 not found. Please ask your hosting provider to install Python3."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Python $PYTHON_VERSION found"

# 2️⃣ Setup user-space tools
install_user_packages

# 3️⃣ Create and activate virtual environment
echo "🔹 Setting up Python virtual environment..."
if [ -d "venv" ]; then
    echo "🔸 Activating existing virtual environment..."
    source venv/bin/activate
else
    echo "🔸 Creating new virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
fi

# 4️⃣ Upgrade pip
echo "🔹 Upgrading pip..."
pip install --upgrade pip --user

# 5️⃣ Install Python dependencies
echo "🔹 Installing Python packages..."
pip install --upgrade \
    pyrogram==2.0.106 \
    tgcrypto \
    yt-dlp \
    pytube \
    instaloader \
    jdatetime \
    python-dateutil \
    requests \
    --user

# 6️⃣ Download and setup ffmpeg (user space)
echo "🔹 Setting up ffmpeg..."
FFMPEG_DIR="$HOME/.local/bin"
if [ ! -f "$FFMPEG_DIR/ffmpeg" ]; then
    echo "🔸 Downloading ffmpeg..."
    cd /tmp
    
    # Detect architecture
    ARCH=$(uname -m)
    if [ "$ARCH" = "x86_64" ]; then
        FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
        FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz"
    else
        echo "⚠️ Unsupported architecture: $ARCH. Trying amd64..."
        FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
    fi
    
    # Download and extract
    wget -q "$FFMPEG_URL" -O ffmpeg.tar.xz
    if [ $? -eq 0 ]; then
        tar -xf ffmpeg.tar.xz
        FFMPEG_EXTRACTED=$(find . -name "ffmpeg-*-static" -type d | head -1)
        if [ -n "$FFMPEG_EXTRACTED" ]; then
            cp "$FFMPEG_EXTRACTED/ffmpeg" "$FFMPEG_DIR/"
            cp "$FFMPEG_EXTRACTED/ffprobe" "$FFMPEG_DIR/"
            chmod +x "$FFMPEG_DIR/ffmpeg" "$FFMPEG_DIR/ffprobe"
            echo "✅ ffmpeg installed successfully"
        else
            echo "⚠️ ffmpeg extraction failed, continuing without it..."
        fi
        rm -rf ffmpeg* 2>/dev/null
    else
        echo "⚠️ ffmpeg download failed, continuing without it..."
    fi
    
    cd - > /dev/null
else
    echo "✅ ffmpeg already installed"
fi

# 7️⃣ Setup bot token
echo "🔹 Setting up bot token..."
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "📝 Creating .env template..."
    cat > .env << 'EOF'
# Telegram Bot Configuration
BOT_TOKEN=YOUR_BOT_TOKEN_HERE

# Instructions:
# 1. Go to @BotFather on Telegram
# 2. Send /newbot and follow instructions
# 3. Copy the token and replace YOUR_BOT_TOKEN_HERE above
# 4. Save this file and run the script again
EOF
    echo "📋 Please edit .env file and add your bot token, then run this script again."
    echo "💡 Use: nano .env"
    exit 1
fi

# Check if token is set
if grep -q "YOUR_BOT_TOKEN_HERE" .env; then
    echo "❌ Please set your bot token in .env file!"
    echo "💡 Edit with: nano .env"
    exit 1
fi

echo "✅ Bot token configuration found"

# 8️⃣ Clean old sessions
echo "🔹 Cleaning old sessions..."
rm -f *.session* 2>/dev/null
rm -rf ~/.pyrogram/ 2>/dev/null
echo "✅ Old sessions cleaned"

# 9️⃣ Sync system time (user space)
echo "🔹 Checking system time..."
echo "📅 Current system time: $(date)"
echo "🌐 Current UTC time: $(date -u)"

# Try to sync time if ntpdate is available
if command_exists ntpdate; then
    echo "🔸 Attempting time sync..."
    ntpdate -s time.nist.gov 2>/dev/null || echo "⚠️ Time sync failed, continuing..."
else
    echo "⚠️ ntpdate not available, skipping time sync"
fi

# 🔟 Create necessary directories
echo "🔹 Creating necessary directories..."
mkdir -p Downloads/youtube Downloads/instagram cookies reports logs
echo "✅ Directories created"

# 1️⃣1️⃣ Set permissions
echo "🔹 Setting file permissions..."
chmod +x *.py 2>/dev/null
chmod 755 Downloads cookies reports logs 2>/dev/null
echo "✅ Permissions set"

# 1️⃣2️⃣ Test bot configuration
echo "🔹 Testing bot configuration..."
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('BOT_TOKEN')
if not token or token == 'YOUR_BOT_TOKEN_HERE':
    print('❌ Bot token not configured properly')
    exit(1)
print('✅ Bot token configured')
" 2>/dev/null

if [ $? -ne 0 ]; then
    # Install python-dotenv if not available
    pip install python-dotenv --user
    echo "⚠️ Please ensure your bot token is properly set in .env file"
fi

# 1️⃣3️⃣ Create startup log
echo "🔹 Creating startup log..."
echo "$(date): Bot startup initiated" >> logs/startup.log

# 1️⃣4️⃣ Display system information
echo ""
echo "📊 System Information:"
echo "🖥️  OS: $(uname -s) $(uname -r)"
echo "🏗️  Architecture: $(uname -m)"
echo "🐍 Python: $(python3 --version)"
echo "📦 Pip: $(pip --version | cut -d' ' -f1,2)"
echo "📁 Working Directory: $(pwd)"
echo "👤 User: $(whoami)"
echo "🕐 System Time: $(date)"
echo "🌍 UTC Time: $(date -u)"
echo ""

# 1️⃣5️⃣ Final checks
echo "🔹 Performing final checks..."

# Check if main bot file exists
if [ ! -f "bot.py" ]; then
    echo "❌ bot.py not found in current directory!"
    echo "📁 Current directory contents:"
    ls -la
    exit 1
fi

# Check virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️ Virtual environment not activated, activating..."
    source venv/bin/activate
fi

echo "✅ All checks passed!"
echo ""
echo "🚀 Starting bot with auto-restart..."
echo "📝 Logs will be saved to logs/bot.log"
echo "🛑 Press Ctrl+C to stop the bot"
echo ""

# 1️⃣6️⃣ Run bot with auto-restart and logging
while true; do
    echo "$(date): Starting bot..." | tee -a logs/bot.log
    
    # Run bot and capture output
    python3 bot.py 2>&1 | tee -a logs/bot.log
    
    EXIT_CODE=$?
    echo "$(date): Bot stopped with exit code $EXIT_CODE" | tee -a logs/bot.log
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "✅ Bot stopped normally"
        break
    else
        echo "⚠️ Bot crashed! Restarting in 10 seconds..."
        echo "📋 Check logs/bot.log for details"
        sleep 10
    fi
done

echo "🏁 Bot startup script finished"
echo "$(date): Bot startup script finished" >> logs/startup.log