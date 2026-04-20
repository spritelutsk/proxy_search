import sys
import os
import re
import time
import json
import requests
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



def download_hidxxy_proxies():
    """
    Скачивает прокси с hidxxy.name/proxy-list и сохраняет в файлы по типам
    """
    if otladka:
        return
    # Словарь для хранения прокси по протоколам
    proxies_by_protocol = {
        'http': set(),
        'https': set(), 
        'socks4': set(),
        'socks5': set()
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # Скачиваем страницы пока не возникнет ошибка
    for page in range(20):
        start = page * 64
        url = f"https://hidxxy.name/proxy-list/?start={start}#list" if start > 0 else "https://hidxxy.name/proxy-list/#list"
        
        try:
            print(f"Загружается страница {url}")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            tbody = soup.find('tbody')
            
            if not tbody:
                print(f"⚠ Таблица не найдена на странице {url}")
                continue
                
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
            
            time.sleep(2)  # Небольшая задержка между запросами
            
        except Exception as e:
            print(f"✗ Ошибка при скачивании {url}: {e}")
            break

    # Записываем в соответствующие файлы
    for protocol, proxies in proxies_by_protocol.items():
        if proxies:
            filename = f"{protocol}.txt"
            filepath = os.path.join(proxy_in_dir, filename)
            with open(filepath, 'a') as f:
                f.write('\n'.join(proxies) + '\n')
            print(f"✓ Сохранено {len(proxies)} {protocol} прокси в {filepath}")


def download_geonode_proxies():
    if otladka:
        return

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
        for protocol, proxies in proxies_by_protocol.items():
            if proxies:
                filename = f"{protocol}.txt"
                filepath = os.path.join(proxy_in_dir, filename)
                with open(filepath, 'a') as f:
                    f.write('\n'.join(proxies) + '\n')
                print(f"✓ Сохранено {len(proxies)} {protocol} прокси в {filepath}")
            
    except Exception as e:
        print(f"✗ Ошибка при скачивании {url}: {e}")


def download_free_proxy_list_net():
    if  otladka:
        return 
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
        proxies = []
        
        if table:
            # Проходим по всем строкам таблицы
            for row in table.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) >= 2:
                    ip = cols[0].text.strip()
                    port = cols[1].text.strip()
                    if ip and port:
                        proxy = f"{ip}:{port}"
                        proxies.append(proxy)
            
            # Записываем найденные прокси в файлы в каталог proxy_in_dir
            if proxies:
                filenames = ['http.txt']  # Исправлено: сохраняем только в http.txt, так как free-proxy-list.net предоставляет HTTP прокси
                for filename in filenames:
                    filepath = os.path.join(proxy_in_dir, filename)
                    with open(filepath, 'a') as f:
                        f.write('\n'.join(proxies))
                    print(f"✓ Сохранено {len(proxies)} прокси в {filepath}")
            else:
                print("⚠ Прокси не найдены в таблице")            
            
        else:
            print("⚠ Таблица с прокси не найдена")

       
    except Exception as e:
        print(f"✗ Ошибка при скачивании {url}: {e}")



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
    """Cleans a proxy line from protocols and extra data.
    Returns a list of valid IP:PORT strings found in the line."""
    # Remove protocols (http://, socks5:// etc.)
    line = re.sub(r'http://|https://|socks4://|socks5://|ftp://|file://', '', line.strip())
    
    # Find ALL IP:PORT patterns in the line
    # This handles cases where multiple proxies are concatenated on one line
    ip_pattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}'
    matches = re.findall(ip_pattern, line)
    
    if matches:
        return matches
    
    # If no IP:PORT pattern found, return original cleaned line as single-item list
    return [line]


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
                    
                clean_lines = clean_proxy_line(line)
                
                # Optional: format check
                for clean_line in clean_lines:
                    if is_valid_proxy(clean_line):
                        processed_lines.append(clean_line)
            
            # Write to file
            if processed_lines:
                with open(file_name, 'a') as f:
                    f.write('\n'.join(processed_lines) + '\n')
                    
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
                
                clean_lines = clean_proxy_line(clean_line)
                for clean_line in clean_lines:
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
            with open(file_name, 'a') as f:
                f.write('\n'.join(proxies) + '\n')
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
                file.write('\n'.join(unique_lines))
                
            print(f"✓ {file_name}: removed {original_count - len(unique_lines)} duplicates, {len(unique_lines)} proxies remain")
            
        except Exception as e:
            print(f"✗ Error processing {file_name}: {e}")


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
        
        valid_count = 0
        with open(socks4_file, 'a') as f:
            for proxy in socks4_proxies:
                if is_valid_proxy(proxy):
                    f.write(f"{proxy}\n")
                    valid_count += 1
        
        print(f"✓ Добавлено {valid_count} SOCKS4 прокси в {socks4_file}")
    except Exception as e:
        print(f"✗ Ошибка получения SOCKS4 прокси: {e}")
    
    # Fetch SOCKS5 proxies
    try:
        proxy = FreeProxies()
        socks5_proxies = proxy.get_socks5_proxies()
        socks5_file = os.path.join(output_dir, 'socks5.txt')
        
        valid_count = 0
        with open(socks5_file, 'a') as f:
            for proxy in socks5_proxies:
                if is_valid_proxy(proxy):
                    f.write(f"{proxy}\n")
                    valid_count += 1
        
        print(f"✓ Добавлено {valid_count} SOCKS5 прокси в {socks5_file}")
    except Exception as e:
        print(f"✗ Ошибка получения SOCKS5 прокси: {e}")
    
    # Fetch HTTP proxies
    try:
        proxy = FreeProxies()
        http_proxies = proxy.get_http_proxies()
        http_file = os.path.join(output_dir, 'http.txt')
        
        valid_count = 0
        with open(http_file, 'a') as f:
            for proxy in http_proxies:
                if is_valid_proxy(proxy):
                    f.write(f"{proxy}\n")
                    valid_count += 1
        
        print(f"✓ Добавлено {valid_count} HTTP прокси в {http_file}")
    except Exception as e:
        print(f"✗ Ошибка получения HTTP прокси: {e}")
    
    # Optionally fetch proxies using UpdateAwareFreeProxies
    try:
        aware_proxy = UpdateAwareFreeProxies()
        http_proxies = aware_proxy.get_http_proxies()
        http_file = os.path.join(output_dir, 'http.txt')
        
        valid_count = 0
        with open(http_file, 'a') as f:
            for proxy in http_proxies:
                if is_valid_proxy(proxy):
                    f.write(f"{proxy}\n")
                    valid_count += 1
        
        print(f"✓ Added {valid_count} HTTP proxies from UpdateAwareFreeProxies to {http_file}")
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
                continue

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
                        elif proxy_type == 'socks':  # иногда бывает просто "socks"
                            proxies['socks5'].append(proxy_str)
        except Exception as e:
            print(f"✗ Ошибка на странице {page}: {e}")

    # Сохраняем с удалением дубликатов
    for proxy_type, proxy_list in proxies.items():
        if proxy_list:
            file_path = os.path.join(output_dir, f"{proxy_type}.txt")

            existing = set()
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    existing = set(line.strip() for line in f if line.strip())

            all_unique = existing.union(proxy_list)

            with open(file_path, 'w') as f:
                f.write('\n'.join(sorted(all_unique)))  # можно убрать sorted() если не нужно

            print(f"✓ Сохранено {len(all_unique)} уникальных {proxy_type} прокси в {file_path}")



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
                    clean_lines = clean_proxy_line(line)
                    for clean_line in clean_lines:
                        if is_valid_proxy(clean_line):
                            lines.append(clean_line)
                if lines:
                    with open(file_path, 'a') as f:
                        f.write('\n'.join(lines) + '\n')
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
    parse_freeproxylist_ru(max_pages=20, output_dir=output_dir)

    print("\n===== Шаг 5: Скачивание прокси с free-proxy-list.net =====")
    download_free_proxy_list_net()

    print("\n===== Шаг 6: Скачивание прокси с geonode.com/free-proxy-list =====")
    download_geonode_proxies()

    print("\n===== Шаг 7: Скачивание прокси с hidxxy.name/proxy-list =====")
    download_hidxxy_proxies()
    
    # Print final statistics
    elapsed_time = time.time() - start_time
    print(f"\n===== Итоговая статистика =====")
    print(f"Успешных загрузок: {successful_downloads}")
    print(f"Ошибок загрузки: {failed_downloads}")
    print(f"Общее время выполнения: {elapsed_time:.2f} секунд")
    print("Примечание: итоговое количество прокси может измениться после удаления дубликатов")

    # Step 8: Remove duplicates
    print("\n===== Шаг 8: Удаление дубликатов =====")
    remove_duplicates(output_dir)

if __name__ == "__main__":
    main()
