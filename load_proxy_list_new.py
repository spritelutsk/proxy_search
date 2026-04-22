#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proxy List Downloader
Downloads proxy lists from multiple sources and organizes them by protocol type.
"""

import sys
import os
import re
import time
import json
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path

try:
    from pyfreeproxies import FreeProxies, UpdateAwareFreeProxies
except ImportError:
    FreeProxies = None
    UpdateAwareFreeProxies = None

# Configure stdout for UTF-8 encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Configuration
DEBUG_MODE = False
PROXY_OUTPUT_DIR = "proxy_in"
REQUEST_TIMEOUT = 15
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ru,en-US;q=0.9,en;q=0.8',
}


class ProxyDownloader:
    """Handles downloading and managing proxy lists from various sources."""
    
    def __init__(self, output_dir: str = PROXY_OUTPUT_DIR, debug: bool = DEBUG_MODE):
        self.output_dir = Path(output_dir)
        self.debug = debug
        self.stats = {
            'successful_downloads': 0,
            'failed_downloads': 0,
            'total_proxies': 0
        }
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def save_proxies(self, file_path: Path, proxies: List[str]) -> None:
        """
        Safely appends proxies to a file, ensuring each proxy is on a new line.
        
        Args:
            file_path: Path to the output file
            proxies: List of proxy strings to save
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Ensure file ends with newline before appending
        if file_path.exists() and file_path.stat().st_size > 0:
            with open(file_path, 'rb') as f:
                f.seek(-1, 2)
                if f.read(1) != b'\n':
                    with open(file_path, 'ab') as af:
                        af.write(b'\n')
        
        # Append proxies
        with open(file_path, 'a', encoding='utf-8') as f:
            if isinstance(proxies, (list, set)):
                f.write('\n'.join(str(p) for p in proxies) + '\n')
            else:
                f.write(f"{proxies}\n")



    def download_hidxxy_proxies(self) -> Tuple[int, int, int]:
        """
        Downloads proxies from hidxxy.name/proxy-list and saves to files by type.
        
        Returns:
            Tuple of (pages_loaded, failed_count, total_saved)
        """
        if self.debug:
            return 0, 0, 0
        
        proxies_by_protocol: Dict[str, Set[str]] = {
            'http': set(),
            'https': set(),
            'socks4': set(),
            'socks5': set()
        }

        headers = DEFAULT_HEADERS.copy()
        headers['Referer'] = 'https://hidxxy.name/proxy-list/#list'

        domains = ['hidxxy.name', 'hixxxx.name']
        session = requests.Session()
        session.headers.update(headers)

        pages_loaded = 0

        for page in range(20):
            start = page * 64
            page_loaded = False

            for domain in domains:
                url = f"https://{domain}/proxy-list/?start={start}#list" if start > 0 else f"https://{domain}/proxy-list/#list"

                try:
                    print(f"Loading page: {url}")
                    response = session.get(url, timeout=REQUEST_TIMEOUT)
                    response.raise_for_status()

                    soup = BeautifulSoup(response.text, 'html.parser')
                    table = soup.find('table', class_='table')
                    tbody = soup.find('tbody') or (table.find('tbody') if table else None)

                    if not tbody:
                        print(f"⚠ Table not found on page {url}")
                        continue

                    rows_found = 0
                    for row in tbody.find_all('tr'):
                        cols = row.find_all('td')
                        if len(cols) >= 5:
                            ip = cols[0].text.strip()
                            port = cols[1].text.strip()
                            proxy_type = cols[4].text.strip().lower()

                            if ip and port:
                                proxy_str = f"{ip}:{port}"

                                if proxy_type in proxies_by_protocol:
                                    proxies_by_protocol[proxy_type].add(proxy_str)
                                    rows_found += 1

                    if rows_found == 0:
                        print(f"⚠ No valid proxy rows found on page {url}")
                        continue

                    page_loaded = True
                    pages_loaded += 1
                    time.sleep(2)
                    break

                except Exception as e:
                    print(f"✗ Error downloading {url}: {e}")
                    continue

            if not page_loaded:
                break

        total_saved = 0
        for protocol, proxies in proxies_by_protocol.items():
            if proxies:
                filepath = self.output_dir / f"{protocol}.txt"
                self.save_proxies(filepath, list(proxies))
                print(f"✓ Saved {len(proxies)} {protocol} proxies to {filepath}")
                total_saved += len(proxies)

        return (pages_loaded, 0 if total_saved > 0 else 1, total_saved)


def download_geonode_proxies():
    if otladka:
        return 0, 0, 0

    """
    Скачивает прокси с geonode.com/free-proxy-list и сохраняет в файлы по типам
    """
    url = "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=http%2Csocks4%2Csocks5&anonymityLevel=elite&anonymityLevel=anonymous"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        print(f"Загружается страница {url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        # Словарь для хранения прокси по протоколам
        proxies_by_protocol = {
            'http': [],
            'https': [],
            'socks4': [],
            'socks5': []
        }
        
        # Распределяем прокси по протоколам
        for proxy in data.get('data', []):
            ip = proxy.get('ip')
            port = proxy.get('port')
            protocols = proxy.get('protocols', [])
            
            if ip and port:
                proxy_str = f"{ip}:{port}"
                for protocol in protocols:
                    if protocol in proxies_by_protocol:
                        proxies_by_protocol[protocol].append(proxy_str)
        
        # Записываем в соответствующие файлы
        total_saved = 0
        for protocol, proxies in proxies_by_protocol.items():
            if proxies:
                filename = f"{protocol}.txt"
                filepath = os.path.join(proxy_in_dir, filename)
                safe_append_proxies(filepath, proxies)
                print(f"✓ Сохранено {len(proxies)} {protocol} прокси в {filepath}")
                total_saved += len(proxies)

        if total_saved == 0:
            return 0, 1, 0
        return 1, 0, total_saved

    except Exception as e:
        print(f"✗ Ошибка при скачивании {url}: {e}")
        return 0, 1, 0


def download_free_proxy_list_net():
    if  otladka:
        return 0, 0, 0
    """
    Скачивает исходный код страницы free-proxy-list.net
    и сохраняет в файлы с очисткой строк
    """
    url = "https://free-proxy-list.net"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        print(f"Загружается страница {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Получаем исходный код страницы
        source_code = response.text

        # Парсим HTML с помощью BeautifulSoup
        soup = BeautifulSoup(source_code, 'html.parser')
        
        # Находим таблицу с прокси
        table = soup.find('tbody')
        proxies_by_protocol = {
            'http': [],
            'https': [],
        }
        
        if table:
            # Проходим по всем строкам таблицы
            for row in table.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) >= 7:
                    ip = cols[0].text.strip()
                    port = cols[1].text.strip()
                    if ip and port:
                        proxy = f"{ip}:{port}"
                        proxies_by_protocol['http'].append(proxy)
                        if cols[6].text.strip().lower() == 'yes':
                            proxies_by_protocol['https'].append(proxy)
             
            # Записываем найденные прокси в файлы в каталог proxy_in_dir
            total_saved = 0
            for protocol, proxies in proxies_by_protocol.items():
                if proxies:
                    filepath = os.path.join(proxy_in_dir, f"{protocol}.txt")
                    safe_append_proxies(filepath, proxies)
                    print(f"✓ Сохранено {len(proxies)} {protocol} прокси в {filepath}")
                    total_saved += len(proxies)

            if total_saved == 0:
                print("⚠ Прокси не найдены в таблице")
                return 0, 1, 0
            return 1, 0, total_saved

        else:
            print("⚠ Таблица с прокси не найдена")
            return 0, 1, 0


    except Exception as e:
        print(f"✗ Ошибка при скачивании {url}: {e}")
        return 0, 1, 0



def is_valid_proxy(proxy_str):
    """Checks if the string is a valid proxy format IP:PORT"""
    # Simple format check for IP:PORT
    proxy_pattern = re.compile(r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})$')
    if proxy_pattern.match(proxy_str):
        # Check IP values (0-255) and port (1-65535)
        parts = proxy_str.split(':')
        ip_parts = parts[0].split('.')
        if all(0 <= int(part) <= 255 for part in ip_parts) and 1 <= int(parts[1]) <= 65535:
            return True
    return False


def clean_proxy_line(line):
    """Cleans a proxy line from protocols and extra data"""
    # Remove protocols (http://, socks5:// etc.)
    line = re.sub(r'http://|https://|socks4://|socks5://|ftp://|file://', '', line.strip())
    # If there's more than one colon, take only the first part with IP:PORT
    if line.count(':') > 1:
        line = re.sub(r'^(.*?:.*?):.*$', r'\1', line)
    return line


def get_proxy_type_from_url(url):
    """Determines proxy type from URL"""
    filename = url.split('/')[-1].lower()
    
    if 'http' in filename and 'https' not in filename:
        return 'http'
    elif 'https' in filename:
        return 'https'
    elif 'socks4' in filename:
        return 'socks4'
    elif 'socks5' in filename:
        return 'socks5'
    else:
        # Default to http if type not explicitly specified
        return 'http'


def download_and_process_proxies(urls, output_dir):
    if otladka:
        return 0,0,0
    """Downloads proxy lists from specified URLs and processes them"""
    os.makedirs(output_dir, exist_ok=True)
    successful_downloads = 0
    # Download statistics
    total_urls = len(urls)
    
    failed_downloads = 0
    total_proxies = 0
    
    start_time = time.time()
    
    for url in urls:
        proxy_type = get_proxy_type_from_url(url)
        file_name = os.path.join(output_dir, f"{proxy_type}.txt")
        
        try:
            print(f"Downloading from {url}...")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            # Process each line
            processed_lines = []
            for line in response.text.splitlines():
                # Skip empty lines
                if not line.strip():
                    continue
                    
                clean_line = clean_proxy_line(line)
                
                # Optional: format check
                if is_valid_proxy(clean_line):
                    processed_lines.append(clean_line)
            
            # Write to file
            if processed_lines:
                safe_append_proxies(file_name, processed_lines)
                print(f"✓ Data from {url} written to {file_name} ({len(processed_lines)} proxies)")
                total_proxies += len(processed_lines)
                successful_downloads += 1
            else:
                print(f"⚠ No proxies found in {url}")
                
        except requests.RequestException as e:
            print(f"✗ Error downloading from {url}: {e}")
            failed_downloads += 1

    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\nDownload Summary:")
    print(f"Successful: {successful_downloads}/{total_urls}")
    print(f"Failed: {failed_downloads}")
    print(f"Total proxies: {total_proxies}")
    print(f"Execution time: {duration:.1f} sec")
    
    return successful_downloads, failed_downloads, total_proxies


def download_and_process_mixed_proxy_lists(urls_mixed, output_dir):
    if otladka:
        return 0,0,0
    """
    Downloads and processes proxy lists with mixed protocols.
    
    Args:
        urls_mixed: List of URLs with different proxy types
        output_dir: Directory for saving proxy files
    
    Returns:
        tuple: (successful_downloads, failed_downloads, total_proxies)
    """
    successful = 0
    failed = 0 
    total = 0
    
    # Dictionaries for storing proxies by type
    proxy_by_type = {
        'http': [],
        'https': [],
        'socks4': [],
        'socks5': []
    }
    
    for url in urls_mixed:
        try:
            print(f"Downloading mixed list from {url}...")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            # Process each line
            for line in response.text.splitlines():
                line = line.strip()
                if not line:
                    continue
                    
                # Determine proxy type by prefix
                if 'socks4://' in line:
                    proxy_type = 'socks4'
                    clean_line = line.replace('socks4://', '')
                elif 'socks5://' in line:
                    proxy_type = 'socks5'
                    clean_line = line.replace('socks5://', '')
                elif 'https://' in line:
                    proxy_type = 'https'
                    clean_line = line.replace('https://', '')
                elif 'http://' in line:
                    proxy_type = 'http'
                    clean_line = line.replace('http://', '')    
                else:
                    # Default to http for unknown formats
                    proxy_type = 'http'
                    clean_line = line
                
                clean_line = clean_proxy_line(clean_line)
                if clean_line and is_valid_proxy(clean_line):
                    proxy_by_type[proxy_type].append(clean_line)
                    
            successful += 1
                
        except requests.RequestException as e:
            print(f"✗ Error downloading from {url}: {e}")
            failed += 1
            continue
            
    # Write proxies to corresponding files
    for proxy_type, proxies in proxy_by_type.items():
        if proxies:
            file_name = os.path.join(output_dir, f"{proxy_type}.txt")
            safe_append_proxies(file_name, proxies)
            print(f"✓ Wrote {len(proxies)} {proxy_type} proxies to {file_name}")
            total += len(proxies)
            
    return successful, failed, total


def remove_duplicates(directory):
    """Removes duplicates in each file in the specified directory"""
    print("\nRemoving duplicates...")
    
    for file_name in os.listdir(directory):
        file_path = os.path.join(directory, file_name)
        
        if not os.path.isfile(file_path) or not file_name.endswith('.txt'):
            continue
            
        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()
                
            original_count = len(lines)
            
            # Remove duplicates while preserving order
            unique_lines = []
            seen = set()
            
            for line in lines:
                line = line.strip()
                if line and line not in seen:
                    seen.add(line)
                    unique_lines.append(line)
            
            # Write unique values back to file
            with open(file_path, 'w') as file:
                if unique_lines:
                    file.write('\n'.join(unique_lines) + '\n')
                
            print(f"✓ {file_name}: removed {original_count - len(unique_lines)} duplicates, {len(unique_lines)} proxies remain")
            
        except Exception as e:
            print(f"✗ Error processing {file_name}: {e}")


def parse_spys_script_vars(html):
    """Parses simple XOR-based JS assignments used by SPYS.ONE to obfuscate ports."""
    values = {}
    script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', html, flags=re.DOTALL | re.IGNORECASE)

    for script in script_blocks:
        if 'document.write' not in script and '^' not in script:
            continue

        for statement in script.split(';'):
            statement = statement.strip()
            if '=' not in statement or 'document.write' in statement:
                continue

            name, expr = statement.split('=', 1)
            name = name.strip()
            expr = expr.strip()
            if not re.match(r'^[A-Za-z0-9_]+$', name):
                continue

            try:
                if '^' in expr:
                    left, right = (part.strip() for part in expr.split('^', 1))
                    left_val = int(left) if left.isdigit() else values.get(left)
                    right_val = int(right) if right.isdigit() else values.get(right)
                    if left_val is None or right_val is None:
                        continue
                    values[name] = left_val ^ right_val
                elif expr.isdigit():
                    values[name] = int(expr)
            except ValueError:
                continue

    return values


def decode_spys_proxy(cell_html, script_vars):
    """Extracts IP:PORT from SPYS.ONE cell HTML."""
    ip_match = re.search(r'>(\d{1,3}(?:\.\d{1,3}){3})<script', cell_html)
    script_match = re.search(r'<script[^>]*>(.*?)</script>', cell_html, flags=re.DOTALL | re.IGNORECASE)
    if not ip_match or not script_match:
        return None

    port_parts = re.findall(r'\(([A-Za-z0-9_]+\^[A-Za-z0-9_]+)\)', script_match.group(1))
    port_digits = []
    for part in port_parts:
        left, right = (item.strip() for item in part.split('^', 1))
        left_val = script_vars.get(left)
        right_val = script_vars.get(right)
        if left_val is None or right_val is None:
            return None
        port_digits.append(str(left_val ^ right_val))

    proxy = f"{ip_match.group(1)}:{''.join(port_digits)}"
    return proxy if is_valid_proxy(proxy) else None


def get_spys_protocol(type_text):
    normalized = ' '.join(type_text.upper().split())
    if 'SOCKS5' in normalized:
        return 'socks5'
    if 'SOCKS4' in normalized:
        return 'socks4'
    if 'HTTPS' in normalized or normalized == 'HTTP S':
        return 'https'
    if 'HTTP' in normalized:
        return 'http'
    return None


def parse_spys_one(output_dir='proxy_in'):
    if otladka:
        return 0, 0, 0

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8'
    }
    urls = [
        'https://spys.one/en/free-proxy-list/',
        'https://spys.one/en/http-proxy-list/',
        'https://spys.one/en/https-ssl-proxy/',
        'https://spys.one/en/socks-proxy-list/',
    ]
    proxies_by_protocol = {
        'http': set(),
        'https': set(),
        'socks4': set(),
        'socks5': set()
    }

    successful_pages = 0
    failed_pages = 0

    for url in urls:
        try:
            print(f"Загружается страница {url}")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            script_vars = parse_spys_script_vars(response.text)
            soup = BeautifulSoup(response.text, 'html.parser')

            rows_found = 0
            for row in soup.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) < 9:
                    continue

                first_cell_html = str(cols[0])
                if 'document.write' not in first_cell_html:
                    continue

                proxy = decode_spys_proxy(first_cell_html, script_vars)
                protocol = get_spys_protocol(cols[1].get_text(' ', strip=True))
                if not proxy or not protocol:
                    continue

                proxies_by_protocol[protocol].add(proxy)
                rows_found += 1

            if rows_found:
                successful_pages += 1
            else:
                print(f"⚠ На странице {url} не найдено прокси")
                failed_pages += 1

        except Exception as e:
            print(f"✗ Ошибка при парсинге {url}: {e}")
            failed_pages += 1

    total_saved = 0
    for protocol, proxies in proxies_by_protocol.items():
        if proxies:
            file_path = os.path.join(output_dir, f"{protocol}.txt")
            safe_append_proxies(file_path, proxies)
            print(f"✓ Сохранено {len(proxies)} {protocol} прокси из SPYS.ONE в {file_path}")
            total_saved += len(proxies)

    return successful_pages, failed_pages, total_saved


def fetch_from_libraries(output_dir):
    """Получает прокси с помощью библиотеки pyfreeproxies"""
    os.makedirs(output_dir, exist_ok=True)
    
    print("\nПолучение прокси из библиотеки pyfreeproxies...")
    
    if FreeProxies is None or UpdateAwareFreeProxies is None:
        print("⚠ Библиотека pyfreeproxies не установлена, шаг пропущен")
        return False

    # Fetch SOCKS4 proxies
    try:
        proxy = FreeProxies()
        socks4_proxies = proxy.get_socks4_proxies()
        socks4_file = os.path.join(output_dir, 'socks4.txt')
        
        valid_proxies = [p for p in socks4_proxies if is_valid_proxy(p)]
        if valid_proxies:
            safe_append_proxies(socks4_file, valid_proxies)
            print(f"✓ Добавлено {len(valid_proxies)} SOCKS4 прокси в {socks4_file}")
    except Exception as e:
        print(f"✗ Ошибка получения SOCKS4 прокси: {e}")
    
    # Fetch SOCKS5 proxies
    try:
        proxy = FreeProxies()
        socks5_proxies = proxy.get_socks5_proxies()
        socks5_file = os.path.join(output_dir, 'socks5.txt')
        
        valid_proxies = [p for p in socks5_proxies if is_valid_proxy(p)]
        if valid_proxies:
            safe_append_proxies(socks5_file, valid_proxies)
            print(f"✓ Добавлено {len(valid_proxies)} SOCKS5 прокси в {socks5_file}")
    except Exception as e:
        print(f"✗ Ошибка получения SOCKS5 прокси: {e}")
    
    # Fetch HTTP proxies
    try:
        proxy = FreeProxies()
        http_proxies = proxy.get_http_proxies()
        http_file = os.path.join(output_dir, 'http.txt')
        
        valid_proxies = [p for p in http_proxies if is_valid_proxy(p)]
        if valid_proxies:
            safe_append_proxies(http_file, valid_proxies)
            print(f"✓ Добавлено {len(valid_proxies)} HTTP прокси в {http_file}")
    except Exception as e:
        print(f"✗ Ошибка получения HTTP прокси: {e}")
    
    # Optionally fetch proxies using UpdateAwareFreeProxies
    try:
        aware_proxy = UpdateAwareFreeProxies()
        http_proxies = aware_proxy.get_http_proxies()
        http_file = os.path.join(output_dir, 'http.txt')
        
        valid_proxies = [p for p in http_proxies if is_valid_proxy(p)]
        if valid_proxies:
            safe_append_proxies(http_file, valid_proxies)
            print(f"✓ Added {len(valid_proxies)} HTTP proxies from UpdateAwareFreeProxies to {http_file}")
    except Exception as e:
        print(f"✗ Error fetching HTTP proxies from UpdateAwareFreeProxies: {e}")


    return True

def parse_freeproxylist_ru(max_pages=20, output_dir='proxy_in'):
    if otladka:
        return 0,0,0
        
    """
    Парсит прокси с сайта freeproxylist.ru с нескольких страниц,
    сохраняет в файлы по типу и удаляет дубликаты.
    """
    base_url = "https://freeproxylist.ru/proxy-list?page={}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    proxies = {
        'http': [],
        'https': [],
        'socks4': [],
        'socks5': []
    }

    os.makedirs(output_dir, exist_ok=True)
    successful_pages = 0
    failed_pages = 0

    for page in range(1, max_pages + 1):
        url = base_url.format(page)
        print(f"🔄 Загружается страница {page}: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            table = soup.find('tbody', class_='table-proxy-list')
            if not table:
                print(f"⚠ Таблица не найдена на странице {page}")
                failed_pages += 1
                continue

            page_has_proxies = False
            for row in table.find_all('tr'):
                cols = row.find_all(['th', 'td'])
                if len(cols) >= 4:
                    ip = cols[0].text.strip()
                    port = cols[1].text.strip()
                    type_cell = cols[3].find('a')
                    if type_cell:
                        proxy_type = type_cell.text.strip().lower()
                        proxy_str = f"{ip}:{port}"

                        if proxy_type in proxies:
                            proxies[proxy_type].append(proxy_str)
                            page_has_proxies = True
                        elif proxy_type == 'socks':  # иногда бывает просто "socks"
                            proxies['socks5'].append(proxy_str)
                            page_has_proxies = True
            if page_has_proxies:
                successful_pages += 1
            else:
                failed_pages += 1
        except Exception as e:
            print(f"✗ Ошибка на странице {page}: {e}")
            failed_pages += 1

    # Сохраняем с удалением дубликатов
    total_added = 0
    for proxy_type, proxy_list in proxies.items():
        if proxy_list:
            file_path = os.path.join(output_dir, f"{proxy_type}.txt")

            existing = set()
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    existing = set(line.strip() for line in f if line.strip())

            all_unique = existing.union(proxy_list)
            added_count = len(all_unique) - len(existing)

            with open(file_path, 'w') as f:
                if all_unique:
                    f.write('\n'.join(sorted(all_unique)) + '\n')  # можно убрать sorted() если не нужно

            print(f"✓ Сохранено {len(all_unique)} уникальных {proxy_type} прокси в {file_path}")
            total_added += added_count

    return successful_pages, failed_pages, total_added



def download_proxies_by_protocol(urls_by_protocol, output_dir):
    """
    Загружает прокси из словаря urls_by_protocol и сохраняет в соответствующие файлы по протоколу.
    """
    if otladka:
        return {}
    os.makedirs(output_dir, exist_ok=True)
    stats = {}
    for protocol, urls in urls_by_protocol.items():
        file_path = os.path.join(output_dir, f"{protocol}.txt")
        total = 0
        success = 0
        failed = 0
        for url in urls:
            try:
                print(f"Downloading {protocol} proxies from {url}...")
                response = requests.get(url, timeout=15)
                response.raise_for_status()
                lines = []
                for line in response.text.splitlines():
                    clean_line = clean_proxy_line(line)
                    if is_valid_proxy(clean_line):
                        lines.append(clean_line)
                if lines:
                    safe_append_proxies(file_path, lines)
                    print(f"✓ Saved {len(lines)} {protocol} proxies to {file_path}")
                    total += len(lines)
                    success += 1
                else:
                    print(f"No valid {protocol} proxies found in {url}")
            except Exception as e:
                print(f"✗ Error downloading {url}: {e}")
                failed += 1
        stats[protocol] = {'success': success, 'failed': failed, 'total': total}
    return stats

def main():
    # Output directory
    output_dir = 'proxy_in'
    os.makedirs(output_dir, exist_ok=True)
    
    start_time = time.time()
    
    # Load URLs from JSON file
    try:
        with open('URLs.json', 'r') as f:
            urls_data = json.load(f)
    except Exception as e:
        print(f"Error loading URLs.json: {e}")
        return

    # Convert lists to sets for consistency with original code
    # Формируем URLs_by_protocol из urls_data, где каждый протокол содержит set из url (берём только поле 'url')
    URLs_by_protocol = {
        'http': set(item['url'] for item in urls_data.get('http', []) if 'url' in item),
        'https': set(item['url'] for item in urls_data.get('https', []) if 'url' in item),
        'socks4': set(item['url'] for item in urls_data.get('socks4', []) if 'url' in item),
        'socks5': set(item['url'] for item in urls_data.get('socks5', []) if 'url' in item)
    }    

    # Lists of proxy URLs with mixed protocols
    #URLs_mixed = set(urls_data.get('mixed', [])) 
    URLs_mixed = {item['url'] for item in urls_data.get('mixed', []) if 'url' in item}
    
    successful_downloads = 0
    failed_downloads = 0
    total_proxies = 0   

    # Step 1: Download proxies from URLs
    print("===== Шаг 1: Загрузка прокси из URL =====")
    stats = download_proxies_by_protocol(URLs_by_protocol, output_dir)
    successful_downloads = sum(v['success'] for v in stats.values())
    failed_downloads = sum(v['failed'] for v in stats.values())
    total_proxies = sum(v['total'] for v in stats.values())

    # Step 2: Process mixed proxy lists
    print("\n===== Шаг 2: Обработка смешанных прокси URL =====")
    mixed_successful, mixed_failed, mixed_total = download_and_process_mixed_proxy_lists(URLs_mixed, output_dir)
    successful_downloads += mixed_successful
    failed_downloads += mixed_failed
    total_proxies += mixed_total
    
    # Step 3: Fetch proxies using library
    print("\n===== Шаг 3: Получение прокси из библиотеки pyfreeproxies =====")
########################fetch_from_libraries(output_dir) 


    print("\n===== Шаг 4: Парсинг сайта freeproxylist.ru =====")
    ru_successful, ru_failed, ru_total = parse_freeproxylist_ru(max_pages=20, output_dir=output_dir)
    successful_downloads += ru_successful
    failed_downloads += ru_failed
    total_proxies += ru_total

    print("\n===== Шаг 5: Скачивание прокси с free-proxy-list.net =====")
    free_successful, free_failed, free_total = download_free_proxy_list_net()
    successful_downloads += free_successful
    failed_downloads += free_failed
    total_proxies += free_total

    print("\n===== Шаг 6: Скачивание прокси с geonode.com/free-proxy-list =====")
    geonode_successful, geonode_failed, geonode_total = download_geonode_proxies()
    successful_downloads += geonode_successful
    failed_downloads += geonode_failed
    total_proxies += geonode_total

    print("\n===== Шаг 7: Скачивание прокси с hidxxy.name/proxy-list =====")
    hidxxy_successful, hidxxy_failed, hidxxy_total = download_hidxxy_proxies()
    successful_downloads += hidxxy_successful
    failed_downloads += hidxxy_failed
    total_proxies += hidxxy_total

    print("\n===== Шаг 8: Парсинг сайта SPYS.ONE =====")
    spys_successful, spys_failed, spys_total = parse_spys_one(output_dir=output_dir)
    successful_downloads += spys_successful
    failed_downloads += spys_failed
    total_proxies += spys_total

    # Print final statistics
    elapsed_time = time.time() - start_time
    print(f"\n===== Итоговая статистика =====")
    print(f"Успешных загрузок: {successful_downloads}")
    print(f"Ошибок загрузки: {failed_downloads}")
    print(f"Общее время выполнения: {elapsed_time:.2f} секунд")
    print("Примечание: итоговое количество прокси может измениться после удаления дубликатов")

    # Step 9: Remove duplicates
    print("\n===== Шаг 9: Удаление дубликатов =====")
    remove_duplicates(output_dir)

if __name__ == "__main__":
    main()
