#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robust Bot Startup Script with Auto-Restart and Error Handling
"""

import os
import sys
import time
import subprocess
import signal
import logging
from pathlib import Path
from datetime import datetime

# Configuration
MAX_RESTARTS = 10
RESTART_DELAY = 5  # seconds
LOG_FILE = "startup.log"
BOT_SCRIPT = "bot.py"

class BotManager:
    def __init__(self):
        self.restart_count = 0
        self.running = True
        self.process = None
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        if self.process:
            self.process.terminate()
    
    def cleanup_database_files(self):
        """Clean up database lock files"""
        try:
            db_files = [
                "plugins/bot_database.db-shm",
                "plugins/bot_database.db-wal"
            ]
            
            for db_file in db_files:
                if os.path.exists(db_file):
                    os.remove(db_file)
                    self.logger.info(f"Removed database lock file: {db_file}")
        except Exception as e:
            self.logger.warning(f"Could not clean database files: {e}")
    
    def check_dependencies(self):
        """Check if required files exist"""
        required_files = [BOT_SCRIPT, ".env", "config.py"]
        
        for file in required_files:
            if not os.path.exists(file):
                self.logger.error(f"Required file missing: {file}")
                return False
        
        # Check if plugins directory exists
        if not os.path.exists("plugins"):
            self.logger.error("Plugins directory missing")
            return False
        
        return True
    
    def install_dependencies(self):
        """Install missing Python dependencies"""
        try:
            self.logger.info("Checking Python dependencies...")
            
            # Check if requirements.txt exists
            if os.path.exists("requirements.txt"):
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    self.logger.info("Dependencies installed successfully")
                else:
                    self.logger.warning(f"Dependency installation warning: {result.stderr}")
            
            # Install TgCrypto for better performance
            try:
                import TgCrypto
                self.logger.info("TgCrypto is available")
            except ImportError:
                self.logger.info("Installing TgCrypto for better performance...")
                subprocess.run([sys.executable, "-m", "pip", "install", "TgCrypto"])
                
        except Exception as e:
            self.logger.warning(f"Could not install dependencies: {e}")
    
    def start_bot(self):
        """Start the bot process"""
        try:
            self.logger.info(f"Starting bot (attempt {self.restart_count + 1})...")
            
            # Clean up database files before starting
            self.cleanup_database_files()
            
            # Start bot process
            self.process = subprocess.Popen(
                [sys.executable, BOT_SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start bot: {e}")
            return False
    
    def monitor_bot(self):
        """Monitor bot process and handle output"""
        if not self.process:
            return False
        
        try:
            # Read output line by line
            while self.running and self.process.poll() is None:
                line = self.process.stdout.readline()
                if line:
                    # Log bot output
                    self.logger.info(f"BOT: {line.strip()}")
                    
                    # Check for specific error patterns
                    if "database is locked" in line.lower():
                        self.logger.warning("Database lock detected, will restart...")
                        self.process.terminate()
                        return False
                    
                    if "bot startup failed" in line.lower():
                        self.logger.warning("Bot startup failed, will restart...")
                        self.process.terminate()
                        return False
                
                time.sleep(0.1)
            
            # Process ended
            exit_code = self.process.poll()
            if exit_code == 0:
                self.logger.info("Bot exited normally")
                return True
            else:
                self.logger.warning(f"Bot exited with code {exit_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error monitoring bot: {e}")
            return False
    
    def run(self):
        """Main run loop with auto-restart"""
        self.logger.info("=" * 50)
        self.logger.info("Bot Manager Started")
        self.logger.info(f"Max restarts: {MAX_RESTARTS}")
        self.logger.info(f"Restart delay: {RESTART_DELAY} seconds")
        self.logger.info("=" * 50)
        
        # Check dependencies
        if not self.check_dependencies():
            self.logger.error("Dependency check failed, exiting...")
            return False
        
        # Install dependencies
        self.install_dependencies()
        
        while self.running and self.restart_count < MAX_RESTARTS:
            # Start bot
            if not self.start_bot():
                self.restart_count += 1
                if self.restart_count < MAX_RESTARTS:
                    self.logger.info(f"Waiting {RESTART_DELAY} seconds before restart...")
                    time.sleep(RESTART_DELAY)
                continue
            
            # Monitor bot
            success = self.monitor_bot()
            
            if not success and self.running:
                self.restart_count += 1
                if self.restart_count < MAX_RESTARTS:
                    self.logger.info(f"Restarting bot in {RESTART_DELAY} seconds... (attempt {self.restart_count + 1}/{MAX_RESTARTS})")
                    time.sleep(RESTART_DELAY)
                else:
                    self.logger.error(f"Maximum restart attempts ({MAX_RESTARTS}) reached")
                    break
            else:
                # Bot exited normally
                break
        
        # Cleanup
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
            except:
                self.process.kill()
        
        self.logger.info("Bot Manager stopped")
        return True

def main():
    """Main function"""
    print("🤖 Robust Bot Startup Manager")
    print("Press Ctrl+C to stop")
    print("-" * 40)
    
    manager = BotManager()
    try:
        manager.run()
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
    
    print("👋 Goodbye!")

if __name__ == "__main__":
    main()