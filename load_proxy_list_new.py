import sys
import os
import re
import time
import json
import shutil
import subprocess
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
try:
    from pyfreeproxies import FreeProxies, UpdateAwareFreeProxies
except ImportError:
    FreeProxies = None
    UpdateAwareFreeProxies = None
# from pyfreeproxies import FreeProxies, UpdateAwareFreeProxies  # Раскомментируйте, если установите библиотеку pip install pyfreeproxies

sys.stdout.reconfigure(encoding='utf-8')

otladka = False
proxy_in_dir = "proxy_in"
successful_downloads = 0


def safe_append_proxies(file_path, proxies):
    """
    Безопасно добавляет прокси в файл, гарантируя что каждый прокси на новой строке.
    Исправляет проблему со склеиванием адресов при добавлении в существующий файл.
    """
    os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
    
    # Проверяем, существует ли файл и не заканчивается ли на \n
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        with open(file_path, 'rb') as f:
            f.seek(-1, 2)  # Go to end and read last byte
            last_byte = f.read(1)
            # Если файл не заканчивается на \n, добавляем его
            if last_byte and last_byte != b'\n':
                with open(file_path, 'ab') as af:
                    af.write(b'\n')
    
    # Теперь безопасно добавляем прокси
    with open(file_path, 'a', encoding='utf-8') as f:
        if isinstance(proxies, (list, set)):
            f.write('\n'.join(str(p) for p in proxies) + '\n')
        else:
            f.write(str(proxies) + '\n')



def download_hidxxy_proxies():
    """
    Скачивает прокси с hidxxy.name/proxy-list и сохраняет в файлы по типам
    """
    if otladka:
        return 0, 0, 0
    # Словарь для хранения прокси по протоколам
    proxies_by_protocol = {
        'http': set(),
        'https': set(), 
        'socks4': set(),
        'socks5': set()
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ru,en-US;q=0.9,en;q=0.8',
        'Referer': 'https://hidxxy.name/proxy-list/#list',
    }

    domains = ['hidxxy.name', 'hixxxx.name']
    session = requests.Session()
    session.headers.update(headers)

    pages_loaded = 0

    # Скачиваем страницы пока не возникнет ошибка
    for page in range(20):
        start = page * 64
        page_loaded = False

        for domain in domains:
            url = f"https://{domain}/proxy-list/?start={start}#list" if start > 0 else f"https://{domain}/proxy-list/#list"

            try:
                print(f"Загружается страница {url}")
                response = session.get(url, timeout=15)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')
                table = soup.find('table', class_='table')
                tbody = soup.find('tbody') or (table.find('tbody') if table else None)

                if not tbody:
                    print(f"⚠ Таблица не найдена на странице {url}")
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

                            # Определяем тип прокси и добавляем в соответствующий список
                            if proxy_type == 'http':
                                proxies_by_protocol['http'].add(proxy_str)
                            elif proxy_type == 'https':
                                proxies_by_protocol['https'].add(proxy_str)
                            elif proxy_type == 'socks4':
                                proxies_by_protocol['socks4'].add(proxy_str)
                            elif proxy_type == 'socks5':
                                proxies_by_protocol['socks5'].add(proxy_str)
                            else:
                                continue
                            rows_found += 1

                if rows_found == 0:
                    print(f"⚠ На странице {url} не найдено подходящих строк прокси")
                    continue

                page_loaded = True
                pages_loaded += 1
                time.sleep(2)  # Небольшая задержка между запросами
                break

            except Exception as e:
                print(f"✗ Ошибка при скачивании {url}: {e}")
                continue

        if not page_loaded:
            break

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
    return pages_loaded, 0, total_saved


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

    def unpack_eval_script(script):
        """
        Handles common SPYS packed form:
        eval(function(p,r,o,x,y,s){...}('q=D^C;...',60,60,'...'.split('\\u005e'),0,{}))
        """
        packed_match = re.search(
            r"\('(.+?)',\s*(\d+),\s*(\d+),\s*'(.+?)'\.split\('(?:\\u005e|\^)'\)",
            script,
            flags=re.DOTALL
        )
        if not packed_match:
            return script

        packed_code = packed_match.group(1)
        radix = int(packed_match.group(2))
        dictionary = packed_match.group(4).split('^')

        def encode_index(num):
            # Matches y() encoder from the packed script for c in range [0, radix)
            if num < 10:
                return str(num)
            if num < 36:
                return chr(ord('a') + num - 10)
            return chr(num + 29)

        decoded = packed_code
        for idx in range(min(len(dictionary), radix) - 1, -1, -1):
            token = encode_index(idx)
            replacement = dictionary[idx]
            decoded = re.sub(rf'\b{re.escape(token)}\b', replacement, decoded)

        return decoded

    def resolve_token(token):
        token = token.strip()
        if not token:
            return None
        if re.fullmatch(r'0[xX][0-9a-fA-F]+', token):
            return int(token, 16)
        if re.fullmatch(r'\d+', token):
            return int(token)
        return values.get(token)

    for script in script_blocks:
        script = unpack_eval_script(script)

        assignments = re.findall(
            r'(?:^|[;\n])\s*(?:var|let)?\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^;\n]+)',
            script
        )
        for name, expr in assignments:
            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name):
                continue

            try:
                if '^' in expr:
                    left, right = (part.strip() for part in expr.split('^', 1))
                    left_val = resolve_token(left)
                    right_val = resolve_token(right)
                    if left_val is None or right_val is None:
                        continue
                    values[name] = left_val ^ right_val
                else:
                    resolved = resolve_token(expr)
                    if resolved is not None:
                        values[name] = resolved
            except ValueError:
                continue

    return values


def decode_spys_proxy(cell_html, script_vars):
    """Extracts IP:PORT from SPYS.ONE cell HTML."""
    ip_match = re.search(r'(\d{1,3}(?:\.\d{1,3}){3})', cell_html)
    script_matches = re.findall(r'<script[^>]*>(.*?)</script>', cell_html, flags=re.DOTALL | re.IGNORECASE)
    if not ip_match or not script_matches:
        return None

    script_code = ' '.join(script_matches)
    port_parts = re.findall(r'\(\s*([A-Za-z0-9_]+)\s*\^\s*([A-Za-z0-9_]+)\s*\)', script_code)
    if not port_parts:
        # Иногда порт уже доступен как текст, если JS-обфускация отключена
        plain_text = BeautifulSoup(cell_html, 'html.parser').get_text(' ', strip=True)
        plain_port_match = re.search(r'\b(\d{2,5})\b', plain_text)
        if plain_port_match:
            proxy = f"{ip_match.group(1)}:{plain_port_match.group(1)}"
            return proxy if is_valid_proxy(proxy) else None
        return None

    port_digits = []

    def resolve_part(token):
        if re.fullmatch(r'0[xX][0-9a-fA-F]+', token):
            return int(token, 16)
        if token.isdigit():
            return int(token)
        return script_vars.get(token)

    for left, right in port_parts:
        left_val = resolve_part(left)
        right_val = resolve_part(right)
        if left_val is None or right_val is None:
            return None
        port_digits.append(str(left_val ^ right_val))

    proxy = f"{ip_match.group(1)}:{''.join(port_digits)}"
    return proxy if is_valid_proxy(proxy) else None


def decode_spys_ports_with_node(row_script_codes):
    """Uses Node.js VM to evaluate row scripts and extract rendered ports."""
    if not row_script_codes or shutil.which('node') is None:
        return []

    node_script = (
        "const vm=require('vm');"
        "const fs=require('fs');"
        "const payload=JSON.parse(fs.readFileSync(0,'utf8'));"
        "const out=[];"
        "const createCtx=()=>{"
        " const c={window:{},self:{},globalThis:{},__buf:''};"
        " c.document={write:(s)=>{c.__buf+=String(s ?? '')}};"
        " c.navigator={userAgent:'Mozilla/5.0'};"
        " c.location={href:'https://spys.one/'};"
        " c.screen={width:1920,height:1080};"
        " c.history={length:1};"
        " c.setTimeout=()=>0; c.clearTimeout=()=>{};"
        " c.setInterval=()=>0; c.clearInterval=()=>{};"
        " c.window=c; c.self=c; c.globalThis=c;"
        " return c;"
        "};"
        "for(const row of payload.rows){"
        " const context=createCtx();"
        " vm.createContext(context);"
        " for(const s of row.globalScripts){try{vm.runInContext(s,context)}catch(e){}}"
        " context.__buf='';"
        " try{vm.runInContext(row.rowScript,context)}catch(e){}"
        " const m=(context.__buf||'').match(/(\\d{2,5})/);"
        " out.push(m?m[1]:null);"
        "}"
        "process.stdout.write(JSON.stringify(out));"
    )

    payload = {'rows': row_script_codes}
    try:
        proc = subprocess.run(
            ['node', '-e', node_script],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=20
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return []
        ports = json.loads(proc.stdout)
        return ports if isinstance(ports, list) else []
    except Exception:
        return []


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


def collect_spys_proxies_from_html(html, proxies_by_protocol):
    """Collects proxies from a SPYS.ONE HTML page into protocol buckets."""
    script_vars = parse_spys_script_vars(html)
    soup = BeautifulSoup(html, 'html.parser')

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

    return rows_found


def save_spys_proxies(output_dir, proxies_by_protocol, source_label):
    total_saved = 0
    for protocol, proxies in proxies_by_protocol.items():
        if proxies:
            file_path = os.path.join(output_dir, f"{protocol}.txt")
            safe_append_proxies(file_path, proxies)
            print(f"✓ Сохранено {len(proxies)} {protocol} прокси из {source_label} в {file_path}")
            total_saved += len(proxies)
    return total_saved

def parse_spys_one(output_dir='proxy_in'):
    if otladka:
        return 0, 0, 0

    # Важно: Spys требует правильные Cookie и Referer
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*(/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        'Origin': 'https://spys.one',
        'Referer': 'https://spys.one/en/free-proxy-list/',
    }
    
    urls = [
        'https://spys.one/en/free-proxy-list/',
        'https://spys.one/en/socks-proxy-list/',
        'https://spys.one/en/https-ssl-proxy/',
    ]
    
    proxies_by_protocol = {'http': set(), 'https': set(), 'socks4': set(), 'socks5': set()}
    successful_pages = 0
    failed_pages = 0

    for url in urls:
        try:
            print(f"Загружается Spys.one: {url}")
            
            # Первый запрос для получения начальных кук и переменных
            response = session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            initial_html = response.text
            
            # Извлекаем параметры для POST-запроса (чтобы получить больше прокси)
            # xf0 - это обычно скрытый параметр формы на Spys
            xf0_match = re.search(r'name="xf0" value="([^"]+)"', response.text)
            payload = {
                'xf0': xf0_match.group(1) if xf0_match else '',
                'xpp': '3', # Параметр выбора количества (3 = 500 штук)
                'xf1': '0'
            }
            
            # Второй запрос (POST), имитирующий выбор "показать 500"
            response = session.post(url, headers=headers, data=payload, timeout=15)
            html_variants = [response.text]
            if initial_html and initial_html != response.text:
                html_variants.append(initial_html)

            rows_found = 0
            for html_variant in html_variants:
                script_vars = parse_spys_script_vars(html_variant)
                if not script_vars:
                    print(f"⚠ Переменные JS не извлечены на {url}, пробуем парсить fallback-логикой")

                soup = BeautifulSoup(html_variant, 'html.parser')
                rows = soup.find_all('tr', class_=['spy1xx', 'spy1x'])
                global_scripts = [
                    code for code in re.findall(r'<script[^>]*>(.*?)</script>', html_variant, flags=re.DOTALL | re.IGNORECASE)
                    if '^' in code or 'eval(function(p,r,o,x,y,s)' in code
                ]
                node_payload = []
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) < 2:
                        continue
                    row_script_match = re.search(
                        r'<script[^>]*>(.*?)</script>',
                        str(cols[0]),
                        flags=re.DOTALL | re.IGNORECASE
                    )
                    if not row_script_match:
                        continue
                    node_payload.append({
                        'globalScripts': global_scripts,
                        'rowScript': row_script_match.group(1)
                    })
                node_ports = decode_spys_ports_with_node(node_payload)
                node_idx = 0

                # Прокси на Spys обычно в строках с классом spy1xx или spy1x
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) < 2:
                        continue

                    # Первая колонка содержит IP и скрипт порта
                    first_cell_html = str(cols[0])
                    proxy = decode_spys_proxy(first_cell_html, script_vars)
                    if not proxy:
                        ip_match = re.search(r'(\d{1,3}(?:\.\d{1,3}){3})', first_cell_html)
                        if ip_match and node_idx < len(node_ports) and node_ports[node_idx]:
                            candidate = f"{ip_match.group(1)}:{node_ports[node_idx]}"
                            if is_valid_proxy(candidate):
                                proxy = candidate
                        if re.search(r'<script[^>]*>.*?</script>', first_cell_html, flags=re.DOTALL | re.IGNORECASE):
                            node_idx += 1
                    
                    # Вторая колонка — тип прокси
                    protocol_text = cols[1].get_text(strip=True)
                    protocol = get_spys_protocol(protocol_text)
                    
                    if proxy and protocol:
                        proxies_by_protocol[protocol].add(proxy)
                        rows_found += 1

            if rows_found:
                print(f"✓ Найдено {rows_found} прокси на {url}")
                successful_pages += 1
            else:
                failed_pages += 1

        except Exception as e:
            print(f"✗ Критическая ошибка Spys.one ({url}): {e}")
            failed_pages += 1
        
        time.sleep(2) # Задержка, чтобы не забанили

    # Сохранение результатов
    total_saved = 0
    for protocol, proxies in proxies_by_protocol.items():
        if proxies:
            file_path = os.path.join(output_dir, f"{protocol}.txt")
            safe_append_proxies(file_path, proxies)
            total_saved += len(proxies)

    return successful_pages, failed_pages, total_saved

def parse_spys_country_pages(output_dir='proxy_in', max_country_pages=12):
    if otladka:
        return 0, 0, 0

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8'
    }
    index_url = 'https://spys.one/en/proxy-by-country/'
    proxies_by_protocol = {
        'http': set(),
        'https': set(),
        'socks4': set(),
        'socks5': set()
    }

    try:
        print(f"Загружается страница {index_url}")
        response = requests.get(index_url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"✗ Ошибка при загрузке {index_url}: {e}")
        return 0, 1, 0

    soup = BeautifulSoup(response.text, 'html.parser')
    country_urls = []
    seen = set()
    for link in soup.find_all('a', href=True):
        href = link['href']
        if not re.match(r'^/free-proxy-list/[A-Z]{2}/$', href):
            continue
        full_url = urljoin(index_url, href)
        if full_url in seen:
            continue
        seen.add(full_url)
        country_urls.append(full_url)
        if len(country_urls) >= max_country_pages:
            break

    if not country_urls:
        print("⚠ На странице стран SPYS.ONE не найдены country links")
        return 0, 1, 0

    successful_pages = 0
    failed_pages = 0

    for url in country_urls:
        try:
            print(f"Загружается страница {url}")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            rows_found = collect_spys_proxies_from_html(response.text, proxies_by_protocol)
            if rows_found:
                successful_pages += 1
            else:
                print(f"⚠ На странице {url} не найдено прокси")
                failed_pages += 1
        except Exception as e:
            print(f"✗ Ошибка при парсинге {url}: {e}")
            failed_pages += 1

    total_saved = save_spys_proxies(output_dir, proxies_by_protocol, "SPYS.ONE country pages")
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

    print("\n===== Шаг 9: Парсинг country pages на SPYS.ONE =====")
    spys_country_successful, spys_country_failed, spys_country_total = parse_spys_country_pages(output_dir=output_dir)
    successful_downloads += spys_country_successful
    failed_downloads += spys_country_failed
    total_proxies += spys_country_total

    # Print final statistics
    elapsed_time = time.time() - start_time
    print(f"\n===== Итоговая статистика =====")
    print(f"Успешных загрузок: {successful_downloads}")
    print(f"Ошибок загрузки: {failed_downloads}")
    print(f"Общее время выполнения: {elapsed_time:.2f} секунд")
    print("Примечание: итоговое количество прокси может измениться после удаления дубликатов")

    # Step 10: Remove duplicates
    print("\n===== Шаг 9: Удаление дубликатов =====")
    remove_duplicates(output_dir)

if __name__ == "__main__":
    main()
