#!/bin/bash
# ============================================================
# Git Secrets Cleanup Script
# Phase 1 Final: Remove exposed cookie files from Git history
# ============================================================

set -e

echo "============================================================"
echo "🔒 Git Secrets Cleanup"
echo "   Removing exposed cookie files from Git history"
echo "============================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo -e "${RED}❌ Error: Not a git repository${NC}"
    echo "   Please run this script from the project root"
    exit 1
fi

# Backup warning
echo -e "${YELLOW}⚠️  WARNING: This will rewrite Git history${NC}"
echo ""
echo "This script will:"
echo "  1. Remove instagram_cookies.txt from all commits"
echo "  2. Remove cookie_youtube.txt from all commits"
echo "  3. Remove any other exposed cookie files"
echo ""
echo "Before proceeding:"
echo "  ✓ Make sure you have a backup"
echo "  ✓ All team members should re-clone after this"
echo "  ✓ Open PRs will need to be rebased"
echo ""

read -p "Continue? (type 'yes' to proceed): " -r
if [ "$REPLY" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "============================================================"
echo "Step 1: Installing git-filter-repo (if needed)"
echo "============================================================"

# Check if git-filter-repo is available
if ! command -v git-filter-repo &> /dev/null; then
    echo "git-filter-repo not found. Installing..."
    
    # Try pip install
    if command -v pip3 &> /dev/null; then
        pip3 install git-filter-repo
    elif command -v pip &> /dev/null; then
        pip install git-filter-repo
    else
        echo -e "${RED}❌ Error: Cannot install git-filter-repo${NC}"
        echo "   Please install manually:"
        echo "   pip install git-filter-repo"
        exit 1
    fi
fi

echo -e "${GREEN}✅ git-filter-repo is available${NC}"
echo ""

echo "============================================================"
echo "Step 2: Removing exposed files from Git history"
echo "============================================================"

# List of files to remove
FILES_TO_REMOVE=(
    "instagram_cookies.txt"
    "cookie_youtube.txt"
    "youtube_cookies.txt"
    "cookie.txt"
    "cookies/youtube_cookies.txt"
    "cookies/instagram_cookies.txt"
)

for file in "${FILES_TO_REMOVE[@]}"; do
    echo "🗑️  Removing: $file"
    
    # Check if file exists in history
    if git log --all --pretty=format: --name-only --diff-filter=A | grep -q "^${file}$"; then
        echo "   Found in history, removing..."
        git filter-repo --path "$file" --invert-paths --force
        echo -e "${GREEN}   ✅ Removed from history${NC}"
    else
        echo -e "${YELLOW}   ℹ️  Not found in history (already clean)${NC}"
    fi
done

echo ""
echo "============================================================"
echo "Step 3: Cleaning up refs and reflogs"
echo "============================================================"

# Remove backup refs created by filter-repo
if [ -d ".git/refs/original" ]; then
    echo "🗑️  Removing backup refs..."
    rm -rf .git/refs/original
    echo -e "${GREEN}✅ Backup refs removed${NC}"
fi

# Expire reflog
echo "🗑️  Expiring reflog..."
git reflog expire --expire=now --all
git gc --prune=now --aggressive
echo -e "${GREEN}✅ Reflog expired and garbage collected${NC}"

echo ""
echo "============================================================"
echo "Step 4: Verification"
echo "============================================================"

echo "🔍 Checking if secrets still exist in history..."

FOUND=0
for file in "${FILES_TO_REMOVE[@]}"; do
    if git log --all --pretty=format: --name-only --diff-filter=A | grep -q "^${file}$"; then
        echo -e "${RED}❌ Still found: $file${NC}"
        FOUND=1
    fi
done

if [ $FOUND -eq 0 ]; then
    echo -e "${GREEN}✅ All secrets successfully removed from history${NC}"
else
    echo -e "${RED}❌ Some files still present in history${NC}"
    echo "   You may need to run the cleanup again"
fi

echo ""
echo "============================================================"
echo "Step 5: Next Steps"
echo "============================================================"
echo ""
echo "✅ Git history has been cleaned"
echo ""
echo "📋 Required actions:"
echo ""
echo "1️⃣  Force push to remote:"
echo "    git push origin --force --all"
echo "    git push origin --force --tags"
echo ""
echo "2️⃣  Invalidate exposed cookies:"
echo "    • Instagram: Logout from all devices or change password"
echo "    • YouTube: Revoke sessions or change password"
echo "    • Go to: https://myaccount.google.com/permissions"
echo ""
echo "3️⃣  Update .gitignore (already done in Phase 1):"
echo "    ✓ *.txt (in cookies directory)"
echo "    ✓ instagram_cookies.txt"
echo "    ✓ youtube_cookies.txt"
echo ""
echo "4️⃣  Notify team members:"
echo "    • Everyone must re-clone the repository"
echo "    • Old clones will have diverged history"
echo "    • Open PRs need to be rebased"
echo ""
echo "⚠️  IMPORTANT: Do not skip step 2 (invalidate cookies)"
echo "    Exposed cookies can still be used until invalidated!"
echo ""
echo "============================================================"
echo ""
