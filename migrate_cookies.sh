#!/bin/bash
# ============================================================
# Phase 1: Cookie Migration Helper Script
# Helps migrate cookies from old location to secure directory
# ============================================================

set -e

echo "============================================================"
echo "🔒 Social-Downloader: Cookie Migration to Secure Directory"
echo "   Phase 1 Security Enhancement"
echo "============================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Secure cookie directory
SECURE_DIR="./data/cookies"

# Check if secure directory exists
if [ ! -d "$SECURE_DIR" ]; then
    echo -e "${YELLOW}📁 Creating secure cookie directory...${NC}"
    mkdir -p "$SECURE_DIR"
    echo -e "${GREEN}✅ Created: $SECURE_DIR${NC}"
else
    echo -e "${GREEN}✅ Secure directory exists: $SECURE_DIR${NC}"
fi

echo ""
echo "🔍 Searching for cookie files in old locations..."
echo ""

FOUND_COUNT=0
MIGRATED_COUNT=0
SKIPPED_COUNT=0

# Function to migrate a single file
migrate_file() {
    local source="$1"
    local dest_name="$2"
    local dest="$SECURE_DIR/$dest_name"
    
    if [ -f "$source" ]; then
        FOUND_COUNT=$((FOUND_COUNT + 1))
        echo -e "${YELLOW}Found:${NC} $source"
        
        # Check if destination already exists
        if [ -f "$dest" ]; then
            echo -e "${YELLOW}  ⚠️  Destination exists: $dest${NC}"
            echo -e "${YELLOW}  Creating backup: ${dest}.backup${NC}"
            cp "$dest" "${dest}.backup"
        fi
        
        # Copy (not move) to preserve original
        cp "$source" "$dest"
        echo -e "${GREEN}  ✅ Migrated to: $dest${NC}"
        MIGRATED_COUNT=$((MIGRATED_COUNT + 1))
        
        # Set secure permissions (read-only for group/others)
        chmod 644 "$dest"
        echo -e "${GREEN}  🔒 Permissions set: 644${NC}"
        echo ""
    fi
}

# Migrate known cookie files
echo "📋 Checking common cookie file locations..."
echo ""

migrate_file "./cookie_youtube.txt" "youtube_cookies.txt"
migrate_file "./youtube_cookies.txt" "youtube_cookies.txt"
migrate_file "./instagram_cookies.txt" "instagram_cookies.txt"
migrate_file "./cookie.txt" "youtube_cookies.txt"

# Migrate cookies directory
if [ -d "./cookies" ] && [ "$(ls -A ./cookies 2>/dev/null)" ]; then
    echo -e "${YELLOW}📂 Found old cookies directory${NC}"
    echo "   Migrating all files..."
    
    for file in ./cookies/*; do
        if [ -f "$file" ]; then
            basename=$(basename "$file")
            migrate_file "$file" "$basename"
        fi
    done
fi

# Search for .txt files in root that might be cookies
echo "🔍 Searching for other potential cookie files in root..."
for file in ./*.txt; do
    if [ -f "$file" ]; then
        # Skip if already processed or if it's in data directory
        if [[ "$file" != "./cookie_youtube.txt" ]] && \
           [[ "$file" != "./youtube_cookies.txt" ]] && \
           [[ "$file" != "./instagram_cookies.txt" ]] && \
           [[ "$file" != "./cookie.txt" ]]; then
            
            # Check if file contains cookie-like content
            if grep -q "youtube.com\|instagram.com\|twitter.com" "$file" 2>/dev/null; then
                echo -e "${YELLOW}⚠️  Potential cookie file: $file${NC}"
                echo "   Contains social media domains"
                read -p "   Migrate this file? (y/n): " -n 1 -r
                echo ""
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    basename=$(basename "$file")
                    migrate_file "$file" "$basename"
                else
                    echo -e "${YELLOW}   Skipped${NC}"
                    SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
                fi
            fi
        fi
    fi
done

echo ""
echo "============================================================"
echo "📊 Migration Summary"
echo "============================================================"
echo -e "Files found:     ${YELLOW}$FOUND_COUNT${NC}"
echo -e "Files migrated:  ${GREEN}$MIGRATED_COUNT${NC}"
echo -e "Files skipped:   ${YELLOW}$SKIPPED_COUNT${NC}"
echo ""

if [ $MIGRATED_COUNT -gt 0 ]; then
    echo -e "${GREEN}✅ Migration completed successfully!${NC}"
    echo ""
    echo "📋 Next steps:"
    echo "1. Verify files in $SECURE_DIR"
    echo "2. Update .env with: COOKIE_BASE_DIR=./data/cookies"
    echo "3. Test bot functionality"
    echo "4. (Optional) Remove old cookie files after verification"
    echo ""
    echo "🔒 Security: Cookie files are now in isolated directory"
else
    echo -e "${YELLOW}ℹ️  No files were migrated${NC}"
    echo ""
    echo "This could mean:"
    echo "- No cookie files found in old locations"
    echo "- Files already migrated"
    echo "- Cookies stored in different location"
fi

echo "============================================================"
echo ""

# Check if .env needs update
if [ -f ".env" ]; then
    if grep -q "COOKIE_BASE_DIR" .env; then
        echo -e "${GREEN}✅ .env already has COOKIE_BASE_DIR${NC}"
    else
        echo -e "${YELLOW}⚠️  .env doesn't have COOKIE_BASE_DIR${NC}"
        read -p "Add COOKIE_BASE_DIR=./data/cookies to .env? (y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "" >> .env
            echo "# Phase 1: Secure cookie directory" >> .env
            echo "COOKIE_BASE_DIR=./data/cookies" >> .env
            echo -e "${GREEN}✅ Added to .env${NC}"
        fi
    fi
fi

echo ""
echo "🎉 Cookie migration process complete!"
echo ""
