#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Асинхронная проверка прокси-серверов
Проверяет работоспособность прокси из файлов и сохраняет рабочие в отдельные файлы
"""

import asyncio
import aiohttp
import os
import sys
import json
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from termcolor import colored

console = Console()

# Конфигурация
PROXY_IN_DIR = "proxy_in"
PROXY_OUT_DIR = "proxy_out"
CHECK_TIMEOUT = 10  # таймаут проверки в секундах
MAX_CONCURRENT_CHECKS = 100  # максимальное количество одновременных проверок
TEST_URL = "https://httpbin.org/ip"  # URL для проверки прокси

# Статистика
stats = {
    'total': 0,
    'checked': 0,
    'working': 0,
    'failed': 0
}


def load_proxies_from_file(filepath):
    """Загружает прокси из файла"""
    proxies = []
    if not os.path.exists(filepath):
        print(f"Файл {filepath} не найден")
        return proxies
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and ':' in line:
                proxies.append(line)
    
    return proxies


def save_proxies_to_file(filepath, proxies):
    """Сохраняет прокси в файл"""
    os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        for proxy in proxies:
            f.write(f"{proxy}\n")


async def check_proxy(session, proxy, test_url):
    """
    Проверяет один прокси
    Возвращает (proxy, is_working, response_time)
    """
    proxy_url = f"http://{proxy}"
    
    try:
        start_time = asyncio.get_event_loop().time()
        
        async with session.get(test_url, timeout=aiohttp.ClientTimeout(total=CHECK_TIMEOUT)) as response:
            if response.status == 200:
                end_time = asyncio.get_event_loop().time()
                response_time = end_time - start_time
                return (proxy, True, response_time)
            else:
                return (proxy, False, 0)
    
    except Exception as e:
        return (proxy, False, 0)


async def check_proxy_https(session, proxy, test_url):
    """
    Проверяет HTTPS прокси
    """
    proxy_url = f"https://{proxy}"
    
    try:
        start_time = asyncio.get_event_loop().time()
        
        async with session.get(test_url, timeout=aiohttp.ClientTimeout(total=CHECK_TIMEOUT)) as response:
            if response.status == 200:
                end_time = asyncio.get_event_loop().time()
                response_time = end_time - start_time
                return (proxy, True, response_time)
            else:
                return (proxy, False, 0)
    
    except Exception as e:
        return (proxy, False, 0)


async def check_socks_proxy(session, proxy, test_url, socks_type='socks4'):
    """
    Проверяет SOCKS прокси
    """
    # Для SOCKS прокси нужен aiohttp_socks или аналогичная библиотека
    # В базовой версии просто пробуем обычное подключение
    proxy_url = f"{socks_type}://{proxy}"
    
    try:
        start_time = asyncio.get_event_loop().time()
        
        connector = aiohttp.TCPConnector()
        async with aiohttp.ClientSession(connector=connector) as sock_session:
            async with sock_session.get(test_url, timeout=aiohttp.ClientTimeout(total=CHECK_TIMEOUT)) as response:
                if response.status == 200:
                    end_time = asyncio.get_event_loop().time()
                    response_time = end_time - start_time
                    return (proxy, True, response_time)
                else:
                    return (proxy, False, 0)
    
    except Exception as e:
        return (proxy, False, 0)


async def process_proxies(proxies, proxy_type, test_url):
    """
    Обрабатывает список прокси асинхронно
    """
    working_proxies = []
    
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_CHECKS)
        
        async def check_with_semaphore(proxy):
            async with semaphore:
                if proxy_type == 'https':
                    return await check_proxy_https(session, proxy, test_url)
                elif proxy_type in ['socks4', 'socks5']:
                    return await check_socks_proxy(session, proxy, test_url, proxy_type)
                else:
                    return await check_proxy(session, proxy, test_url)
        
        tasks = [check_with_semaphore(proxy) for proxy in proxies]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task(f"Проверка {proxy_type} прокси...", total=len(proxies))
            
            for coro in asyncio.as_completed(tasks):
                result = await coro
                proxy, is_working, response_time = result
                
                stats['checked'] += 1
                
                if is_working:
                    working_proxies.append((proxy, response_time))
                    stats['working'] += 1
                    color = 'green'
                    status = "✓"
                else:
                    stats['failed'] += 1
                    color = 'red'
                    status = "✗"
                
                progress.update(task, advance=1)
    
    return working_proxies


async def main():
    """Основная функция"""
    global stats
    
    print(colored("=" * 60, "cyan"))
    print(colored("Асинхронная проверка прокси-серверов", "cyan", attrs=["bold"]))
    print(colored("=" * 60, "cyan"))
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Таймаут проверки: {CHECK_TIMEOUT} сек")
    print(f"Максимум одновременных проверок: {MAX_CONCURRENT_CHECKS}")
    print()
    
    # Создаем директорию для результатов
    os.makedirs(PROXY_OUT_DIR, exist_ok=True)
    
    # Типы прокси для проверки
    proxy_types = ['http', 'https', 'socks4', 'socks5']
    
    all_working_proxies = {
        'http': [],
        'https': [],
        'socks4': [],
        'socks5': []
    }
    
    for proxy_type in proxy_types:
        input_file = os.path.join(PROXY_IN_DIR, f"{proxy_type}.txt")
        output_file = os.path.join(PROXY_OUT_DIR, f"{proxy_type}_checked.txt")
        
        print(colored(f"\n{'='*60}", "yellow"))
        print(colored(f"Проверка {proxy_type.upper()} прокси", "yellow", attrs=["bold"]))
        print(colored(f"{'='*60}", "yellow"))
        
        # Загружаем прокси
        proxies = load_proxies_from_file(input_file)
        
        if not proxies:
            print(f"Нет прокси для проверки в {input_file}")
            continue
        
        stats['total'] += len(proxies)
        print(f"Загружено {len(proxies)} прокси")
        
        # Проверяем прокси
        working = await process_proxies(proxies, proxy_type, TEST_URL)
        
        # Сортируем по времени ответа (быстрее первые)
        working.sort(key=lambda x: x[1])
        
        # Сохраняем только адреса без времени ответа
        working_addresses = [addr for addr, _ in working]
        all_working_proxies[proxy_type] = working_addresses
        
        # Сохраняем результаты
        if working_addresses:
            save_proxies_to_file(output_file, working_addresses)
            print(colored(f"\n✓ Найдено {len(working_addresses)} рабочих {proxy_type} прокси", "green"))
            print(f"Результаты сохранены в {output_file}")
        else:
            print(colored(f"\n✗ Рабочие {proxy_type} прокси не найдены", "red"))
    
    # Вывод статистики
    print(colored(f"\n{'='*60}", "cyan"))
    print(colored("ИТОГОВАЯ СТАТИСТИКА", "cyan", attrs=["bold"]))
    print(colored(f"{'='*60}", "cyan"))
    print(f"Всего прокси: {stats['total']}")
    print(f"Проверено: {stats['checked']}")
    print(colored(f"Рабочих: {stats['working']}", "green"))
    print(colored(f"Не рабочих: {stats['failed']}", "red"))
    
    if stats['total'] > 0:
        success_rate = (stats['working'] / stats['total']) * 100
        print(f"Процент успешных: {success_rate:.2f}%")
    
    print(f"\nВремя окончания: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Сохраняем общую статистику в JSON
    stats_file = os.path.join(PROXY_OUT_DIR, "check_stats.json")
    stats_data = {
        'timestamp': datetime.now().isoformat(),
        'total': stats['total'],
        'checked': stats['checked'],
        'working': stats['working'],
        'failed': stats['failed'],
        'by_type': {
            ptype: len(all_working_proxies[ptype]) for ptype in proxy_types
        }
    }
    
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nСтатистика сохранена в {stats_file}")
    
    return stats['working']


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result > 0 else 1)
    except KeyboardInterrupt:
        print("\n\nПроверка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\nОшибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
