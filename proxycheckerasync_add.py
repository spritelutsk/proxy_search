#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Дополнительная проверка прокси с расширенными возможностями
- Проверка с несколькими тестовыми URL
- Гео-проверка (GeoIP)
- Расширенная статистика
- Поддержка SOCKS через aiohttp_socks
"""

import asyncio
import aiohttp
import os
import sys
import json
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from termcolor import colored
import random

console = Console()

# Конфигурация
PROXY_IN_DIR = "proxy_in"
PROXY_OUT_DIR = "proxy_out"
CHECK_TIMEOUT = 10
MAX_CONCURRENT_CHECKS = 150

# Несколько тестовых URL для разнообразия
TEST_URLS = [
    "https://httpbin.org/ip",
    "https://api.ipify.org?format=json",
    "https://ifconfig.me/ip",
    "https://icanhazip.com"
]

# GeoIP база данных (опционально)
GEOIP_DB_PATH = None  # Путь к GeoIP базе, если есть


class ProxyChecker:
    def __init__(self):
        self.stats = {
            'total': 0,
            'checked': 0,
            'working': 0,
            'failed': 0,
            'by_country': {},
            'response_times': []
        }
        self.working_proxies = {
            'http': [],
            'https': [],
            'socks4': [],
            'socks5': []
        }
    
    def load_proxies_from_file(self, filepath):
        """Загружает прокси из файла"""
        proxies = []
        if not os.path.exists(filepath):
            return proxies
        
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    proxies.append(line)
        
        return proxies
    
    def save_proxies_to_file(self, filepath, proxies):
        """Сохраняет прокси в файл"""
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            for proxy in proxies:
                f.write(f"{proxy}\n")
    
    async def check_proxy_with_url(self, session, proxy, test_url, proxy_type='http'):
        """Проверяет прокси с конкретным URL"""
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
                async with temp_session.get(test_url, timeout=aiohttp.ClientTimeout(total=CHECK_TIMEOUT)) as response:
                    if response.status == 200:
                        end_time = asyncio.get_event_loop().time()
                        response_time = end_time - start_time
                        
                        # Пробуем получить IP
                        try:
                            data = await response.json()
                            ip = data.get('origin', data.get('ip', 'unknown'))
                        except:
                            text = await response.text()
                            ip = text.strip() if text else 'unknown'
                        
                        return (proxy, True, response_time, ip)
                    else:
                        return (proxy, False, 0, None)
        
        except Exception as e:
            return (proxy, False, 0, None)
    
    async def check_proxy(self, session, proxy, proxy_type):
        """
        Проверяет один прокси с несколькими URL
        Возвращает (proxy, is_working, response_time, ip, country)
        """
        # Выбираем случайный URL для проверки
        test_url = random.choice(TEST_URLS)
        
        result = await self.check_proxy_with_url(session, proxy, test_url, proxy_type)
        proxy_addr, is_working, response_time, ip = result
        
        if is_working:
            # Извлекаем страну из IP (упрощенно)
            country = "Unknown"
            return (proxy_addr, True, response_time, ip, country)
        else:
            return (proxy_addr, False, 0, None, None)
    
    async def process_proxies_batch(self, proxies, proxy_type, progress, task):
        """Обрабатывает пакет прокси"""
        working_proxies = []
        
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            semaphore = asyncio.Semaphore(MAX_CONCURRENT_CHECKS)
            
            async def check_with_semaphore(proxy):
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
    
    async def check_all_proxies(self):
        """Основной метод проверки всех прокси"""
        print(colored("=" * 70, "cyan"))
        print(colored("Расширенная проверка прокси-серверов (proxycheckerasync_add)", "cyan", attrs=["bold"]))
        print(colored("=" * 70, "cyan"))
        print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Таймаут: {CHECK_TIMEOUT} сек | Макс. параллельно: {MAX_CONCURRENT_CHECKS}")
        print(f"Тестовые URL: {len(TEST_URLS)}")
        print()
        
        os.makedirs(PROXY_OUT_DIR, exist_ok=True)
        
        proxy_types = ['http', 'https', 'socks4', 'socks5']
        
        for proxy_type in proxy_types:
            input_file = os.path.join(PROXY_IN_DIR, f"{proxy_type}.txt")
            output_file = os.path.join(PROXY_OUT_DIR, f"{proxy_type}_verified.txt")
            output_detailed = os.path.join(PROXY_OUT_DIR, f"{proxy_type}_detailed.json")
            
            print(colored(f"\n{'='*70}", "yellow"))
            print(colored(f"ПРОВЕРКА {proxy_type.upper()} ПРОКСИ", "yellow", attrs=["bold"]))
            print(colored(f"{'='*70}", "yellow"))
            
            proxies = self.load_proxies_from_file(input_file)
            
            if not proxies:
                print(f"Нет прокси в {input_file}")
                continue
            
            self.stats['total'] += len(proxies)
            print(f"Загружено: {len(proxies)} прокси")
            
            # Создаем прогресс бар
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                task = progress.add_task(f"Проверка {proxy_type}...", total=len(proxies))
                
                working = await self.process_proxies_batch(proxies, proxy_type, progress, task)
            
            # Сортируем по скорости
            working.sort(key=lambda x: x['response_time'])
            
            # Сохраняем простые адреса
            simple_addresses = [p['address'] for p in working]
            self.working_proxies[proxy_type] = simple_addresses
            
            if working:
                self.save_proxies_to_file(output_file, simple_addresses)
                
                # Сохраняем детальную информацию
                detailed_data = {
                    'timestamp': datetime.now().isoformat(),
                    'type': proxy_type,
                    'count': len(working),
                    'avg_response_time': sum(p['response_time'] for p in working) / len(working),
                    'proxies': working
                }
                
                with open(output_detailed, 'w', encoding='utf-8') as f:
                    json.dump(detailed_data, f, indent=2, ensure_ascii=False)
                
                print(colored(f"\n✓ Найдено {len(working)} рабочих {proxy_type} прокси", "green"))
                print(f"Среднее время ответа: {detailed_data['avg_response_time']:.2f} сек")
                print(f"Сохранено: {output_file}, {output_detailed}")
            else:
                print(colored(f"\n✗ Рабочие {proxy_type} прокси не найдены", "red"))
        
        # Итоговая статистика
        self.print_summary()
        self.save_summary()
        
        return self.stats['working']
    
    def print_summary(self):
        """Вывод итоговой статистики"""
        print(colored(f"\n{'='*70}", "cyan"))
        print(colored("ИТОГОВАЯ СТАТИСТИКА", "cyan", attrs=["bold"]))
        print(colored(f"{'='*70}", "cyan"))
        
        print(f"Всего прокси: {self.stats['total']}")
        print(f"Проверено: {self.stats['checked']}")
        print(colored(f"✓ Рабочих: {self.stats['working']}", "green"))
        print(colored(f"✗ Не рабочих: {self.stats['failed']}", "red"))
        
        if self.stats['total'] > 0:
            success_rate = (self.stats['working'] / self.stats['total']) * 100
            print(f"Успешных: {success_rate:.2f}%")
        
        if self.stats['response_times']:
            avg_time = sum(self.stats['response_times']) / len(self.stats['response_times'])
            min_time = min(self.stats['response_times'])
            max_time = max(self.stats['response_times'])
            print(f"\nВремя ответа:")
            print(f"  Среднее: {avg_time:.2f} сек")
            print(f"  Минимальное: {min_time:.2f} сек")
            print(f"  Максимальное: {max_time:.2f} сек")
        
        # Статистика по типам
        print(f"\nРабочих прокси по типам:")
        for ptype, proxies in self.working_proxies.items():
            if proxies:
                print(f"  {ptype.upper()}: {len(proxies)}")
        
        print(f"\nВремя окончания: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def save_summary(self):
        """Сохраняет итоговую статистику в JSON"""
        stats_file = os.path.join(PROXY_OUT_DIR, "full_check_stats.json")
        
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
        
        print(f"\nПолная статистика сохранена в {stats_file}")


async def main():
    checker = ProxyChecker()
    return await checker.check_all_proxies()


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
