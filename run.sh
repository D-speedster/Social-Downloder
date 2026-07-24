#!/bin/bash
# ============================================================
# run.sh — Social-Downloader Direct Runner
# Simple script to run without Docker
# ============================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "============================================================"
echo " Social-Downloader - Direct Runner"
echo " Running without Docker"
echo "============================================================"
echo ""

# ============================================================
# Step 1: Check Python 3
# ============================================================
echo -e "${BLUE}[1/6] Checking Python installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ ERROR: Python 3 is not installed${NC}"
    echo "Please install Python 3.8 or higher:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "  Fedora: sudo dnf install python3 python3-pip"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✅ Python ${PYTHON_VERSION} found${NC}"
echo ""

# ============================================================
# Step 2: Check ffmpeg
# ============================================================
echo -e "${BLUE}[2/6] Checking ffmpeg installation...${NC}"
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}⚠️  WARNING: ffmpeg is not installed${NC}"
    echo "ffmpeg is required for video downloads and processing."
    echo "Please install it:"
    echo "  Ubuntu/Debian: sudo apt install ffmpeg"
    echo "  Fedora: sudo dnf install ffmpeg"
    echo ""
    read -p "Continue without ffmpeg? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    FFMPEG_VERSION=$(ffmpeg -version | head -1 | cut -d' ' -f3)
    echo -e "${GREEN}✅ ffmpeg ${FFMPEG_VERSION} found${NC}"
fi
echo ""

# ============================================================
# Step 3: Check .env file
# ============================================================
echo -e "${BLUE}[3/6] Checking environment configuration...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ ERROR: .env file not found${NC}"
    echo "Please create .env file from .env.example:"
    echo "  cp .env.example .env"
    echo "  nano .env  # Edit with your credentials"
    exit 1
fi

# Check required variables
REQUIRED_VARS=("BOT_TOKEN" "API_ID" "API_HASH")
MISSING_VARS=()

for VAR in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${VAR}=" .env || grep -q "^${VAR}=.*_here" .env; then
        MISSING_VARS+=("$VAR")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "${RED}❌ ERROR: Missing or invalid environment variables:${NC}"
    for VAR in "${MISSING_VARS[@]}"; do
        echo "  - $VAR"
    done
    echo ""
    echo "Please edit .env file and set proper values"
    exit 1
fi

echo -e "${GREEN}✅ Environment configuration OK${NC}"
echo ""

# ============================================================
# Step 4: Create virtual environment
# ============================================================
echo -e "${BLUE}[4/6] Setting up virtual environment...${NC}"
if [ ! -d "venv" ]; then
    echo "Creating new virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${GREEN}✅ Virtual environment already exists${NC}"
fi
echo ""

# ============================================================
# Step 5: Install dependencies
# ============================================================
echo -e "${BLUE}[5/6] Installing dependencies...${NC}"

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null

# Install requirements
if [ -f "requirements.txt" ]; then
    echo "Installing packages from requirements.txt..."
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${RED}❌ ERROR: requirements.txt not found${NC}"
    exit 1
fi
echo ""

# ============================================================
# Step 6: Create required directories
# ============================================================
echo -e "${BLUE}[6/6] Creating required directories...${NC}"
mkdir -p logs
mkdir -p downloads
mkdir -p data/cookies
mkdir -p data/cookies_tmp
mkdir -p data/sessions
mkdir -p data/database
echo -e "${GREEN}✅ Directories created${NC}"
echo ""

# ============================================================
# Launch bot
# ============================================================
echo "============================================================"
echo -e "${GREEN}✅ All checks passed - Starting bot...${NC}"
echo "============================================================"
echo ""
echo "Bot is starting. Press Ctrl+C to stop."
echo ""

# Run the bot
python3 bot.py
