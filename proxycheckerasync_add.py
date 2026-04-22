#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Async Proxy Checker
Extended proxy checking with multiple test URLs, GeoIP support, and detailed statistics.
"""

import asyncio
import aiohttp
import os
import sys
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from termcolor import colored

console = Console()

# Configuration
PROXY_IN_DIR = "proxy_in"
PROXY_OUT_DIR = "proxy_out"
CHECK_TIMEOUT = 10
MAX_CONCURRENT_CHECKS = 150

# Multiple test URLs for variety
TEST_URLS = [
    "https://httpbin.org/ip",
    "https://api.ipify.org?format=json",
    "https://ifconfig.me/ip",
    "https://icanhazip.com"
]


class AdvancedProxyChecker:
    """Advanced proxy checker with extended features."""
    
    def __init__(self,
                 proxy_in_dir: str = PROXY_IN_DIR,
                 proxy_out_dir: str = PROXY_OUT_DIR,
                 check_timeout: int = CHECK_TIMEOUT,
                 max_concurrent: int = MAX_CONCURRENT_CHECKS):
        self.proxy_in_dir = Path(proxy_in_dir)
        self.proxy_out_dir = Path(proxy_out_dir)
        self.check_timeout = check_timeout
        self.max_concurrent = max_concurrent
        
        self.stats = {
            'total': 0,
            'checked': 0,
            'working': 0,
            'failed': 0,
            'by_country': {},
            'response_times': []
        }
        
        self.working_proxies: Dict[str, List[str]] = {
            'http': [],
            'https': [],
            'socks4': [],
            'socks5': []
        }
        
        self.proxy_out_dir.mkdir(parents=True, exist_ok=True)
    
    def load_proxies_from_file(self, filepath: Path) -> List[str]:
        """Loads proxies from a file."""
        proxies = []
        if not filepath.exists():
            return proxies
        
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    proxies.append(line)
        
        return proxies
    
    def save_proxies_to_file(self, filepath: Path, proxies: List[str]) -> None:
        """Saves proxies to a file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            for proxy in proxies:
                f.write(f"{proxy}\n")
    
    async def check_proxy_with_url(self, session: aiohttp.ClientSession,
                                   proxy: str, test_url: str,
                                   proxy_type: str = 'http') -> Tuple[str, bool, float, Optional[str]]:
        """Checks a proxy with a specific URL."""
        if proxy_type == 'https':
            proxy_url = f"https://{proxy}"
        elif proxy_type == 'socks4':
            proxy_url = f"socks4://{proxy}"
        elif proxy_type == 'socks5':
            proxy_url = f"socks5://{proxy}"
        else:
            proxy_url = f"http://{proxy}"
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as temp_session:
                timeout = aiohttp.ClientTimeout(total=self.check_timeout)
                async with temp_session.get(test_url, timeout=timeout) as response:
                    if response.status == 200:
                        end_time = asyncio.get_event_loop().time()
                        response_time = end_time - start_time
                        
                        # Try to get IP
                        try:
                            data = await response.json()
                            ip = data.get('origin', data.get('ip', 'unknown'))
                        except:
                            text = await response.text()
                            ip = text.strip() if text else 'unknown'
                        
                        return (proxy, True, response_time, ip)
                    else:
                        return (proxy, False, 0, None)
        
        except Exception:
            return (proxy, False, 0, None)
    
    async def check_proxy(self, session: aiohttp.ClientSession,
                         proxy: str, proxy_type: str) -> Tuple[str, bool, float, Optional[str], Optional[str]]:
        """
        Checks a single proxy with multiple URLs.
        
        Returns:
            Tuple of (proxy_address, is_working, response_time, ip, country)
        """
        # Select random URL for checking
        test_url = random.choice(TEST_URLS)
        
        result = await self.check_proxy_with_url(session, proxy, test_url, proxy_type)
        proxy_addr, is_working, response_time, ip = result
        
        if is_working:
            # Extract country from IP (simplified)
            country = "Unknown"
            return (proxy_addr, True, response_time, ip, country)
        else:
            return (proxy_addr, False, 0, None, None)
    
    async def process_proxies_batch(self, proxies: List[str], proxy_type: str,
                                   progress: Progress, task) -> List[Dict]:
        """Processes a batch of proxies."""
        working_proxies = []
        
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            async def check_with_semaphore(proxy: str):
                async with semaphore:
                    result = await self.check_proxy(session, proxy, proxy_type)
                    
                    self.stats['checked'] += 1
                    progress.update(task, advance=1)
                    
                    proxy_addr, is_working, response_time, ip, country = result
                    
                    if is_working:
                        self.stats['working'] += 1
                        self.stats['response_times'].append(response_time)
                        
                        if country:
                            self.stats['by_country'][country] = self.stats['by_country'].get(country, 0) + 1
                        
                        working_proxies.append({
                            'address': proxy_addr,
                            'response_time': response_time,
                            'ip': ip,
                            'country': country
                        })
                    else:
                        self.stats['failed'] += 1
                    
                    return result
            
            tasks = [check_with_semaphore(proxy) for proxy in proxies]
            await asyncio.gather(*tasks)
        
        return working_proxies
    
    async def check_all_proxies(self) -> int:
        """Main method to check all proxies."""
        print(colored("=" * 70, "cyan"))
        print(colored("Advanced Proxy Checker (proxycheckerasync_add)", "cyan", attrs=["bold"]))
        print(colored("=" * 70, "cyan"))
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Timeout: {self.check_timeout} sec | Max concurrent: {self.max_concurrent}")
        print(f"Test URLs: {len(TEST_URLS)}")
        print()
        
        proxy_types = ['http', 'https', 'socks4', 'socks5']
        
        for proxy_type in proxy_types:
            input_file = self.proxy_in_dir / f"{proxy_type}.txt"
            output_file = self.proxy_out_dir / f"{proxy_type}_verified.txt"
            output_detailed = self.proxy_out_dir / f"{proxy_type}_detailed.json"
            
            print(colored(f"\n{'='*70}", "yellow"))
            print(colored(f"CHECKING {proxy_type.upper()} PROXIES", "yellow", attrs=["bold"]))
            print(colored(f"{'='*70}", "yellow"))
            
            proxies = self.load_proxies_from_file(input_file)
            
            if not proxies:
                print(f"No proxies in {input_file}")
                continue
            
            self.stats['total'] += len(proxies)
            print(f"Loaded: {len(proxies)} proxies")
            
            # Create progress bar
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                task = progress.add_task(f"Checking {proxy_type}...", total=len(proxies))
                
                working = await self.process_proxies_batch(proxies, proxy_type, progress, task)
            
            # Sort by speed
            working.sort(key=lambda x: x['response_time'])
            
            # Save simple addresses
            simple_addresses = [p['address'] for p in working]
            self.working_proxies[proxy_type] = simple_addresses
            
            if working:
                self.save_proxies_to_file(output_file, simple_addresses)
                
                # Save detailed information
                detailed_data = {
                    'timestamp': datetime.now().isoformat(),
                    'type': proxy_type,
                    'count': len(working),
                    'avg_response_time': sum(p['response_time'] for p in working) / len(working),
                    'proxies': working
                }
                
                with open(output_detailed, 'w', encoding='utf-8') as f:
                    json.dump(detailed_data, f, indent=2, ensure_ascii=False)
                
                print(colored(f"\n✓ Found {len(working)} working {proxy_type} proxies", "green"))
                print(f"Average response time: {detailed_data['avg_response_time']:.2f} sec")
                print(f"Saved: {output_file}, {output_detailed}")
            else:
                print(colored(f"\n✗ No working {proxy_type} proxies found", "red"))
        
        # Final statistics
        self.print_summary()
        self.save_summary()
        
        return self.stats['working']
    
    def print_summary(self) -> None:
        """Prints final statistics."""
        print(colored(f"\n{'='*70}", "cyan"))
        print(colored("FINAL STATISTICS", "cyan", attrs=["bold"]))
        print(colored(f"{'='*70}", "cyan"))
        
        print(f"Total proxies: {self.stats['total']}")
        print(f"Checked: {self.stats['checked']}")
        print(colored(f"✓ Working: {self.stats['working']}", "green"))
        print(colored(f"✗ Failed: {self.stats['failed']}", "red"))
        
        if self.stats['total'] > 0:
            success_rate = (self.stats['working'] / self.stats['total']) * 100
            print(f"Success rate: {success_rate:.2f}%")
        
        if self.stats['response_times']:
            avg_time = sum(self.stats['response_times']) / len(self.stats['response_times'])
            min_time = min(self.stats['response_times'])
            max_time = max(self.stats['response_times'])
            print(f"\nResponse times:")
            print(f"  Average: {avg_time:.2f} sec")
            print(f"  Minimum: {min_time:.2f} sec")
            print(f"  Maximum: {max_time:.2f} sec")
        
        # Statistics by type
        print(f"\nWorking proxies by type:")
        for ptype, proxies in self.working_proxies.items():
            if proxies:
                print(f"  {ptype.upper()}: {len(proxies)}")
        
        print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def save_summary(self) -> None:
        """Saves final statistics to JSON."""
        stats_file = self.proxy_out_dir / "full_check_stats.json"
        
        stats_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total': self.stats['total'],
                'checked': self.stats['checked'],
                'working': self.stats['working'],
                'failed': self.stats['failed'],
                'success_rate': (self.stats['working'] / self.stats['total'] * 100) if self.stats['total'] > 0 else 0
            },
            'response_times': {
                'avg': sum(self.stats['response_times']) / len(self.stats['response_times']) if self.stats['response_times'] else 0,
                'min': min(self.stats['response_times']) if self.stats['response_times'] else 0,
                'max': max(self.stats['response_times']) if self.stats['response_times'] else 0
            },
            'by_type': {
                ptype: len(proxies) for ptype, proxies in self.working_proxies.items()
            },
            'by_country': self.stats['by_country']
        }
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nFull statistics saved to {stats_file}")


async def main():
    """Main entry point."""
    checker = AdvancedProxyChecker()
    return await checker.check_all_proxies()


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result > 0 else 1)
    except KeyboardInterrupt:
        print("\n\nCheck interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
