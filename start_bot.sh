#!/bin/bash
echo "🟢 Starting full bot setup...."

# 1️⃣ Activate or create Python virtual environment
if [ -d "venv" ]; then
    echo "🔹 Activating existing virtualenv..."
    source venv/bin/activate
else
    echo "🔹 Creating virtualenv..."
    python3 -m venv venv
    source venv/bin/activate
fi

# 2️⃣ Upgrade pip
echo "🔹 Upgrading pip..."
pip install --upgrade pip

# 3️⃣ Install dependencies with Pyrogram 2.x
echo "🔹 Installing requirements..."
pip install --upgrade pyrogram==2.0.106 tgcrypto yt-dlp pytube instaloader jdatetime mysql-connector-python python-dateutil requests

# 4️⃣ Remove old sessions & Pyrogram cache
echo "🔹 Cleaning old Pyrogram sessions..."
rm -f *.session*
rm -rf ~/.pyrogram/

# 5️⃣ Ensure ffmpeg is installed
echo "🔹 Checking ffmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️ ffmpeg not found, installing..."
    sudo apt update
    sudo apt install -y ffmpeg
else
    echo "✅ ffmpeg already installed"
fi

# 6️⃣ Ensure system time is synced
echo "🔹 Syncing system time..."
sudo apt install -y chrony
sudo systemctl enable chrony
sudo systemctl start chrony
chronyc makestep
date -u

# 7️⃣ Run the bot with auto-restart
echo "🔹 Running the bot with auto-restart..."
while true; do
    python3 bot.py
    echo "⚠️ Bot crashed! Restarting in 5 seconds..."
    sleep 5
done
