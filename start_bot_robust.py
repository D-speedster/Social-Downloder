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
            
            # Also clean session files
            session_files = []
            for file in os.listdir('.'):
                if file.endswith('.session') or file.endswith('.session-journal'):
                    session_files.append(file)
            
            all_files = db_files + session_files
            
            for db_file in all_files:
                if os.path.exists(db_file):
                    try:
                        os.remove(db_file)
                        self.logger.info(f"Removed lock/session file: {db_file}")
                    except OSError as e:
                        if "being used by another process" in str(e) or "Device or resource busy" in str(e):
                            self.logger.warning(f"File {db_file} is locked by another process")
                            # Try to kill any python processes that might be holding the file
                            try:
                                if os.name != 'nt':  # Unix/Linux
                                    subprocess.run(['pkill', '-f', 'bot.py'], check=False)
                                    time.sleep(2)
                                    os.remove(db_file)
                                    self.logger.info(f"Force removed: {db_file}")
                            except:
                                pass
                        else:
                            raise e
                            
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
            
            # Check if bot.py exists
            if not os.path.exists(BOT_SCRIPT):
                self.logger.error(f"Bot script not found: {BOT_SCRIPT}")
                return False
            
            # Start bot process with better error handling
            self.process = subprocess.Popen(
                [sys.executable, BOT_SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=os.getcwd()
            )
            
            # Wait a moment to see if process starts successfully
            time.sleep(1)
            
            if self.process.poll() is not None:
                # Process already exited
                exit_code = self.process.poll()
                stdout, stderr = self.process.communicate()
                
                self.logger.error(f"Bot failed to start, exited immediately with code {exit_code}")
                if stdout:
                    self.logger.error(f"STDOUT: {stdout}")
                if stderr:
                    self.logger.error(f"STDERR: {stderr}")
                
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start bot: {e}")
            return False
    
    def monitor_bot(self):
        """Monitor bot process and handle output"""
        if not self.process:
            return False
        
        try:
            output_lines = []
            error_lines = []
            
            # Read output line by line
            while self.running and self.process.poll() is None:
                line = self.process.stdout.readline()
                if line:
                    line_stripped = line.strip()
                    output_lines.append(line_stripped)
                    
                    # Log bot output
                    self.logger.info(f"BOT: {line_stripped}")
                    
                    # Check for specific error patterns
                    if "database is locked" in line.lower():
                        self.logger.warning("Database lock detected, will restart...")
                        error_lines.append("Database lock error")
                        self.process.terminate()
                        return False
                    
                    if "bot startup failed" in line.lower():
                        self.logger.warning("Bot startup failed, will restart...")
                        error_lines.append("Bot startup failed")
                        self.process.terminate()
                        return False
                    
                    # Check for authentication errors
                    if "unauthorized" in line.lower() or "invalid token" in line.lower():
                        self.logger.error("Authentication error detected - check bot token")
                        error_lines.append("Authentication error")
                        self.process.terminate()
                        return False
                    
                    # Check for network errors
                    if "network" in line.lower() and "error" in line.lower():
                        self.logger.warning("Network error detected")
                        error_lines.append("Network error")
                
                time.sleep(0.1)
            
            # Process ended - capture any remaining output
            try:
                remaining_output, remaining_error = self.process.communicate(timeout=5)
                if remaining_output:
                    for line in remaining_output.split('\n'):
                        if line.strip():
                            self.logger.info(f"BOT: {line.strip()}")
                            output_lines.append(line.strip())
                if remaining_error:
                    for line in remaining_error.split('\n'):
                        if line.strip():
                            self.logger.error(f"BOT ERROR: {line.strip()}")
                            error_lines.append(line.strip())
            except subprocess.TimeoutExpired:
                self.logger.warning("Timeout waiting for process output")
            
            # Process ended
            exit_code = self.process.poll()
            
            # Log detailed exit information
            if exit_code == 0:
                self.logger.info("Bot exited normally")
                return True
            else:
                self.logger.error(f"Bot exited with code {exit_code}")
                
                # Log last few lines for debugging
                if output_lines:
                    self.logger.error("Last output lines:")
                    for line in output_lines[-5:]:
                        self.logger.error(f"  > {line}")
                
                if error_lines:
                    self.logger.error("Error summary:")
                    for error in error_lines:
                        self.logger.error(f"  ! {error}")
                
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