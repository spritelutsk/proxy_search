#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Asynchronous Proxy Checker
Checks proxy functionality from input files and saves working proxies to output files.
"""

import asyncio
import aiohttp
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from termcolor import colored

console = Console()

# Configuration
PROXY_IN_DIR = "proxy_in"
PROXY_OUT_DIR = "proxy_out"
CHECK_TIMEOUT = 10  # seconds
MAX_CONCURRENT_CHECKS = 100
TEST_URL = "https://httpbin.org/ip"


class ProxyChecker:
    """Handles asynchronous proxy checking operations."""
    
    def __init__(self, 
                 proxy_in_dir: str = PROXY_IN_DIR,
                 proxy_out_dir: str = PROXY_OUT_DIR,
                 check_timeout: int = CHECK_TIMEOUT,
                 max_concurrent: int = MAX_CONCURRENT_CHECKS,
                 test_url: str = TEST_URL):
        self.proxy_in_dir = Path(proxy_in_dir)
        self.proxy_out_dir = Path(proxy_out_dir)
        self.check_timeout = check_timeout
        self.max_concurrent = max_concurrent
        self.test_url = test_url
        
        self.stats = {
            'total': 0,
            'checked': 0,
            'working': 0,
            'failed': 0
        }
        
        self.proxy_out_dir.mkdir(parents=True, exist_ok=True)
    
    def load_proxies_from_file(self, filepath: Path) -> List[str]:
        """Loads proxies from a file."""
        proxies = []
        if not filepath.exists():
            print(f"File {filepath} not found")
            return proxies
        
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and ':' in line:
                    proxies.append(line)
        
        return proxies
    
    def save_proxies_to_file(self, filepath: Path, proxies: List[str]) -> None:
        """Saves proxies to a file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            for proxy in proxies:
                f.write(f"{proxy}\n")
    
    async def check_proxy(self, session: aiohttp.ClientSession, 
                         proxy: str) -> Tuple[str, bool, float]:
        """
        Checks a single proxy.
        
        Returns:
            Tuple of (proxy_address, is_working, response_time)
        """
        proxy_url = f"http://{proxy}"
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            timeout = aiohttp.ClientTimeout(total=self.check_timeout)
            async with session.get(self.test_url, timeout=timeout) as response:
                if response.status == 200:
                    end_time = asyncio.get_event_loop().time()
                    response_time = end_time - start_time
                    return (proxy, True, response_time)
                else:
                    return (proxy, False, 0)
        
        except Exception:
            return (proxy, False, 0)
    
    async def process_proxies(self, proxies: List[str], 
                            proxy_type: str) -> List[Tuple[str, float]]:
        """
        Processes a list of proxies asynchronously.
        
        Returns:
            List of tuples (proxy_address, response_time) for working proxies
        """
        working_proxies = []
        
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            async def check_with_semaphore(proxy: str):
                async with semaphore:
                    return await self.check_proxy(session, proxy)
            
            tasks = [check_with_semaphore(proxy) for proxy in proxies]
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                task = progress.add_task(f"Checking {proxy_type} proxies...", total=len(proxies))
                
                for coro in asyncio.as_completed(tasks):
                    result = await coro
                    proxy, is_working, response_time = result
                    
                    self.stats['checked'] += 1
                    
                    if is_working:
                        working_proxies.append((proxy, response_time))
                        self.stats['working'] += 1
                    else:
                        self.stats['failed'] += 1
                    
                    progress.update(task, advance=1)
        
        return working_proxies
    
    async def check_all_proxies(self) -> int:
        """Main method to check all proxies."""
        print(colored("=" * 60, "cyan"))
        print(colored("Asynchronous Proxy Checker", "cyan", attrs=["bold"]))
        print(colored("=" * 60, "cyan"))
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Check timeout: {self.check_timeout} sec")
        print(f"Max concurrent checks: {self.max_concurrent}")
        print()
        
        proxy_types = ['http', 'https', 'socks4', 'socks5']
        all_working_proxies: Dict[str, List[str]] = {ptype: [] for ptype in proxy_types}
        
        for proxy_type in proxy_types:
            input_file = self.proxy_in_dir / f"{proxy_type}.txt"
            output_file = self.proxy_out_dir / f"{proxy_type}_checked.txt"
            
            print(colored(f"\n{'='*60}", "yellow"))
            print(colored(f"Checking {proxy_type.upper()} proxies", "yellow", attrs=["bold"]))
            print(colored(f"{'='*60}", "yellow"))
            
            proxies = self.load_proxies_from_file(input_file)
            
            if not proxies:
                print(f"No proxies to check in {input_file}")
                continue
            
            self.stats['total'] += len(proxies)
            print(f"Loaded {len(proxies)} proxies")
            
            working = await self.process_proxies(proxies, proxy_type)
            
            # Sort by response time (fastest first)
            working.sort(key=lambda x: x[1])
            
            # Extract just the addresses
            working_addresses = [addr for addr, _ in working]
            all_working_proxies[proxy_type] = working_addresses
            
            if working_addresses:
                self.save_proxies_to_file(output_file, working_addresses)
                print(colored(f"\n✓ Found {len(working_addresses)} working {proxy_type} proxies", "green"))
                print(f"Results saved to {output_file}")
            else:
                print(colored(f"\n✗ No working {proxy_type} proxies found", "red"))
        
        # Print statistics
        self.print_summary(all_working_proxies)
        
        # Save statistics to JSON
        self.save_stats(all_working_proxies, proxy_types)
        
        return self.stats['working']
    
    def print_summary(self, all_working_proxies: Dict[str, List[str]]) -> None:
        """Prints final statistics."""
        print(colored(f"\n{'='*60}", "cyan"))
        print(colored("FINAL STATISTICS", "cyan", attrs=["bold"]))
        print(colored(f"{'='*60}", "cyan"))
        print(f"Total proxies: {self.stats['total']}")
        print(f"Checked: {self.stats['checked']}")
        print(colored(f"Working: {self.stats['working']}", "green"))
        print(colored(f"Failed: {self.stats['failed']}", "red"))
        
        if self.stats['total'] > 0:
            success_rate = (self.stats['working'] / self.stats['total']) * 100
            print(f"Success rate: {success_rate:.2f}%")
        
        print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def save_stats(self, all_working_proxies: Dict[str, List[str]], 
                   proxy_types: List[str]) -> None:
        """Saves statistics to a JSON file."""
        stats_file = self.proxy_out_dir / "check_stats.json"
        stats_data = {
            'timestamp': datetime.now().isoformat(),
            'total': self.stats['total'],
            'checked': self.stats['checked'],
            'working': self.stats['working'],
            'failed': self.stats['failed'],
            'by_type': {
                ptype: len(all_working_proxies[ptype]) for ptype in proxy_types
            }
        }
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nStatistics saved to {stats_file}")


async def main():
    """Main entry point."""
    checker = ProxyChecker()
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
