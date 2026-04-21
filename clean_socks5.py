#!/usr/bin/env python3
"""
Скрипт для очистки файла socks5.txt от некорректных прокси.
Фильтрует прокси с портами 80, 443, 8080 (HTTP/HTTPS порты).
"""

import re

def is_valid_socks5_proxy(proxy_str):
    """Проверяет, является ли прокси корректным SOCKS5 (не HTTP/HTTPS порт)"""
    proxy_pattern = re.compile(r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})$')
    match = proxy_pattern.match(proxy_str)
    if match:
        parts = proxy_str.split(':')
        ip_parts = parts[0].split('.')
        port = int(parts[1])
        
        # Проверка IP
        if not all(0 <= int(part) <= 255 for part in ip_parts):
            return False
        
        # Проверка порта
        if not (1 <= port <= 65535):
            return False
        
        # SOCKS5 не должен использовать HTTP/HTTPS порты
        if port in [80, 443, 8080]:
            return False
        
        return True
    return False

def clean_socks5_file(input_file, output_file=None):
    """Очищает файл socks5.txt от некорректных прокси"""
    if output_file is None:
        output_file = input_file
    
    valid_count = 0
    invalid_count = 0
    total_count = 0
    
    valid_proxies = []
    
    print(f"Чтение файла {input_file}...")
    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            total_count += 1
            
            if is_valid_socks5_proxy(line):
                valid_proxies.append(line)
                valid_count += 1
            else:
                invalid_count += 1
    
    print(f"Всего прокси: {total_count}")
    print(f"Корректных SOCKS5: {valid_count}")
    print(f"Некорректных (отфильтровано): {invalid_count}")
    
    print(f"Запись очищенных данных в {output_file}...")
    with open(output_file, 'w') as f:
        f.write('\n'.join(valid_proxies) + '\n')
    
    print(f"✓ Очистка завершена. {valid_count} прокси сохранено.")
    return valid_count, invalid_count

if __name__ == "__main__":
    import sys
    
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'proxy_in/socks5.txt'
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    clean_socks5_file(input_file, output_file)
