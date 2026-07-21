#!/usr/bin/env python3
"""
SHORT USERNAME FINDER
Finds available Instagram usernames (1-4 characters)
Just run it and get a list of working usernames.
"""

import requests
import json
import time
import random
import sys
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from colorama import init, Fore, Style
from fake_useragent import UserAgent

init(autoreset=True)

# ============================================================
# CONFIG
# ============================================================

try:
    with open('config.json', 'r') as f:
        CONFIG = json.load(f)
except:
    CONFIG = {
        "min_length": 1,
        "max_length": 4,
        "threads": 30,
        "check_delay": 0.3,
        "max_results": 100,
        "output_file": "available_usernames.txt",
        "use_proxies": False
    }

print(f"""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     🎯 SHORT USERNAME FINDER                                ║
║                                                               ║
║     Finds available 1-4 character usernames                 ║
║     Letters | Numbers | _ | .                               ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")

# ============================================================
# USERNAME GENERATOR
# ============================================================

class UsernameGenerator:
    """Generate all valid 1-4 character usernames."""
    
    CHARS = 'abcdefghijklmnopqrstuvwxyz0123456789_.'
    
    @staticmethod
    def is_valid(username):
        """Check if username follows Instagram rules."""
        length = len(username)
        
        if length < 1 or length > 4:
            return False
        if username.isdigit():
            return False
        if username.startswith('.') or username.endswith('.'):
            return False
        if '..' in username:
            return False
        if not re.match(r'^[a-z0-9_.]+$', username):
            return False
        return True
    
    @staticmethod
    def generate_all():
        """Generate all valid 1-4 character usernames."""
        chars = UsernameGenerator.CHARS
        valid = []
        
        # Length 1
        for c1 in chars:
            u = c1
            if UsernameGenerator.is_valid(u):
                valid.append(u)
        
        # Length 2
        for c1 in chars:
            for c2 in chars:
                u = c1 + c2
                if UsernameGenerator.is_valid(u):
                    valid.append(u)
        
        # Length 3
        for c1 in chars:
            for c2 in chars:
                for c3 in chars:
                    u = c1 + c2 + c3
                    if UsernameGenerator.is_valid(u):
                        valid.append(u)
        
        # Length 4
        for c1 in chars:
            for c2 in chars:
                for c3 in chars:
                    for c4 in chars:
                        u = c1 + c2 + c3 + c4
                        if UsernameGenerator.is_valid(u):
                            valid.append(u)
        
        return valid

# ============================================================
# AVAILABILITY CHECKER
# ============================================================

class UsernameChecker:
    """Check if usernames are available on Instagram."""
    
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.proxy_pool = []
        self.available = []
        self.checked = 0
        self.lock = threading.Lock()
        self.running = True
        self._load_proxies()
    
    def _load_proxies(self):
        try:
            with open('proxies.txt', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self.proxy_pool.append(line)
            if self.proxy_pool:
                print(f"✅ Loaded {len(self.proxy_pool)} proxies")
        except:
            pass
    
    def _get_proxy(self):
        if self.proxy_pool and CONFIG.get('use_proxies', False):
            proxy = random.choice(self.proxy_pool)
            return {'http': proxy, 'https': proxy}
        return None
    
    def _get_headers(self):
        return {
            'User-Agent': self.ua.random,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.instagram.com/',
            'Origin': 'https://www.instagram.com',
        }
    
    def check_username(self, username):
        """Check if username is available on Instagram."""
        with self.lock:
            self.checked += 1
        
        try:
            # Fast check using profile page
            url = f'https://www.instagram.com/{username}/'
            headers = self._get_headers()
            proxies = self._get_proxy()
            
            response = self.session.get(
                url,
                headers=headers,
                proxies=proxies,
                timeout=5,
                allow_redirects=False
            )
            
            # 404 = username is AVAILABLE
            if response.status_code == 404:
                with self.lock:
                    self.available.append(username)
                    with open(CONFIG.get('output_file', 'available_usernames.txt'), 'a') as f:
                        f.write(f"{username}\n")
                return (username, True)
            
            # 200 or 302 = username is TAKEN
            if response.status_code in [200, 302]:
                return (username, False)
            
            # API fallback
            api_url = f'https://www.instagram.com/api/v1/users/web_profile_info/?username={username}'
            api_response = self.session.get(
                api_url,
                headers=headers,
                proxies=proxies,
                timeout=5
            )
            
            if api_response.status_code == 200:
                data = api_response.json()
                if 'data' in data and 'user' in data['data'] and data['data']['user']:
                    return (username, False)
                else:
                    with self.lock:
                        self.available.append(username)
                        with open(CONFIG.get('output_file', 'available_usernames.txt'), 'a') as f:
                            f.write(f"{username}\n")
                    return (username, True)
            
            return (username, False)
            
        except:
            return (username, False)
    
    def check_batch(self, usernames):
        """Check multiple usernames in parallel."""
        found = []
        
        with ThreadPoolExecutor(max_workers=CONFIG.get('threads', 30)) as executor:
            futures = {executor.submit(self.check_username, u): u for u in usernames}
            
            for future in as_completed(futures):
                if not self.running:
                    break
                try:
                    username, is_available = future.result()
                    if is_available:
                        found.append(username)
                        print(f"{Fore.GREEN}✅ @{username}{Style.RESET_ALL}")
                except:
                    pass
                
                with self.lock:
                    if self.checked % 100 == 0:
                        print(f"📊 Checked: {self.checked:,} | Found: {len(self.available)}")
        
        return found

# ============================================================
# MAIN FINDER
# ============================================================

class UsernameFinder:
    def __init__(self):
        self.generator = UsernameGenerator()
        self.checker = UsernameChecker()
        self.start_time = datetime.now()
        self.found = 0
        self.target = CONFIG.get('max_results', 100)
    
    def run(self):
        """Run the finder."""
        print("\n" + "=" * 60)
        print(f"🎯 Looking for {self.target} available usernames...")
        print(f"📏 Length: {CONFIG.get('min_length', 1)}-{CONFIG.get('max_length', 4)} characters")
        print("=" * 60 + "\n")
        
        # Generate all usernames
        print("🔄 Generating all valid usernames...")
        all_usernames = self.generator.generate_all()
        print(f"✅ Generated {len(all_usernames):,} total usernames\n")
        
        # Shuffle to get variety
        random.shuffle(all_usernames)
        
        # Check in batches
        batch_size = 200
        total_checked = 0
        
        for i in range(0, len(all_usernames), batch_size):
            if self.found >= self.target:
                break
            
            batch = all_usernames[i:i+batch_size]
            total_checked += len(batch)
            
            available = self.checker.check_batch(batch)
            self.found += len(available)
            
            print(f"📦 Batch {i//batch_size + 1}: Found {len(available)} available (Total: {self.found})")
            print("-" * 40)
            
            time.sleep(CONFIG.get('check_delay', 0.3))
        
        # Final summary
        elapsed = (datetime.now() - self.start_time).total_seconds()
        minutes = elapsed / 60
        
        print("\n" + "=" * 60)
        print("🏁 SCAN COMPLETE")
        print("=" * 60)
        print(f"✅ Available usernames found: {self.found}")
        print(f"📊 Total checked: {self.checker.checked:,}")
        print(f"⏱️  Time: {minutes:.1f} minutes")
        print(f"📁 Saved to: {CONFIG.get('output_file', 'available_usernames.txt')}")
        print("=" * 60)
        
        # Show results
        if self.checker.available:
            print(f"\n🔥 AVAILABLE USERNAMES ({len(self.checker.available)} total):")
            print("-" * 40)
            for i, name in enumerate(self.checker.available[:50], 1):
                print(f"{i:3}. @{name}")
            
            if len(self.checker.available) > 50:
                print(f"... and {len(self.checker.available) - 50} more")
            
            print("\n💡 To claim one:")
            print("   1. Go to Instagram Settings → Edit Profile")
            print("   2. Change your username to one from the list")
            print("   3. Save it")
        else:
            print("\n❌ No available usernames found. Try again later.")

# ============================================================
# ENTRY POINT
# ============================================================

def main():
    try:
        finder = UsernameFinder()
        finder.run()
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
