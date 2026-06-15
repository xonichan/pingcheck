#!/usr/bin/env python3
"""
Ping Monitor - инструмент мониторинга доступности целей в стиле htop.

Использование:
    python monitor.py --targets ./hosts.txt

Управление:
    q / Ctrl+C - выход
    r - перечитать файл с целями
    p - пауза/запуск
    ↑ / ↓ - навигация по списку
"""

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

try:
    from icmplib import async_ping, ICMPLibError
except ImportError:
    print("Ошибка: установите icmplib через 'pip install icmplib'")
    sys.exit(1)


class Status(Enum):
    UP = "up"
    DOWN = "down"


@dataclass
class Target:
    """Состояние одной цели (IP/домен)."""
    ip: str
    status: Status = Status.DOWN
    rtt: Optional[float] = None
    rtt_history: list = field(default_factory=list)  # История RTT для среднего
    loss_count: int = 0
    success_count: int = 0
    total_attempts: int = 0
    recent_attempts: list = field(default_factory=list)  # Список последних 5 попыток (True/False)
    
    # Статистика за всё время
    min_rtt: Optional[float] = None
    max_rtt: Optional[float] = None
    total_rtt_sum: float = 0.0
    rtt_count: int = 0
    
    @property
    def loss_percentage(self) -> float:
        """Процент потерянных пакетов (последние 5 попыток)."""
        if len(self.recent_attempts) == 0:
            return 0.0
        failed = sum(1 for a in self.recent_attempts if not a)
        return (failed / len(self.recent_attempts)) * 100
    
    @property
    def avg_rtt(self) -> Optional[float]:
        """Среднее RTT за последние 10 попыток."""
        if not self.rtt_history:
            return None
        return sum(self.rtt_history) / len(self.rtt_history)
    
    def update(self, rtt: Optional[float], success: bool) -> None:
        """Обновить состояние цели после пинга."""
        self.total_attempts += 1
        self.rtt = rtt
        
        # Сохраняем в историю RTT (максимум 10 значений для среднего)
        if rtt is not None:
            self.rtt_history.append(rtt)
            if len(self.rtt_history) > 10:
                self.rtt_history.pop(0)
            
            # Обновляем глобальную статистику
            if self.min_rtt is None or rtt < self.min_rtt:
                self.min_rtt = rtt
            if self.max_rtt is None or rtt > self.max_rtt:
                self.max_rtt = rtt
            self.total_rtt_sum += rtt
            self.rtt_count += 1
        
        # Сохраняем в историю попыток (максимум 5 попыток)
        self.recent_attempts.append(success)
        if len(self.recent_attempts) > 5:
            self.recent_attempts.pop(0)
        
        if success:
            self.status = Status.UP
            self.success_count += 1
        else:
            self.status = Status.DOWN
            self.loss_count += 1
    
    def get_rtt_display(self) -> str:
        """Отобразить последний RTT."""
        if self.rtt is None:
            return "-"
        return f"{self.rtt:.1f}"
    
    def get_avg_rtt_display(self) -> str:
        """Отобразить средний RTT (последние 10)."""
        if len(self.rtt_history) < 10:
            return "---"
        if self.avg_rtt is None:
            return "-"
        return f"{self.avg_rtt:.1f}"
    
    def get_all_time_stats(self) -> str:
        """Отобразить статистику за всё время."""
        if self.rtt_count == 0:
            return "-"
        avg = self.total_rtt_sum / self.rtt_count
        return f"{avg:.1f}/{self.min_rtt:.1f}/{self.max_rtt:.1f}"
    
    def get_rtt_graph(self) -> str:
        """Построить ASCII-график последних RTT."""
        if not self.rtt_history:
            return "?"
        
        values = self.rtt_history[-10:]  # Берём последние 10
        max_val = max(values) if values else 1
        
        # Символы по степени тревожности
        # ? – нет данных / ошибка
        # ✓ – отлично (<10%)
        # ∘ – хорошо (10–30%)
        # ◌ – терпимо (30–50%)
        # ⚠ – высоко (50–70%)
        # ❗ – очень высоко (70–90%)
        # ✖ – критический (>90%)
        graph_chars = []
        for val in values:
            if val <= 0:
                graph_chars.append("?")
            else:
                ratio = val / max_val
                if ratio < 0.1:
                    graph_chars.append("✓")
                elif ratio < 0.3:
                    graph_chars.append("∘")
                elif ratio < 0.5:
                    graph_chars.append("◌")
                elif ratio < 0.7:
                    graph_chars.append("⚠")
                elif ratio < 0.9:
                    graph_chars.append("❗")
                else:
                    graph_chars.append("✖")
        
        return " ".join(graph_chars) if graph_chars else "?"
    
    def log_event(self, status: Status, rtt: Optional[float] = None, error: str = None, logfile: str = None, only_down: bool = False) -> None:
        """Записать событие в лог-файл."""
        if not logfile:
            return
        
        # Если only_down=True и событие UP, не логируем
        if only_down and status == Status.UP:
            return
        
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        if error:
            log_line = f"{timestamp} {self.ip} ERROR: {error}\n"
        elif status == Status.UP:
            log_line = f"{timestamp} {self.ip} UP RTT={rtt:.1f}ms\n"
        else:
            log_line = f"{timestamp} {self.ip} DOWN\n"
        
        try:
            with open(logfile, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception:
            pass


class PingManager:
    """Менеджер асинхронного пингования целей."""
    
    def __init__(self, targets: List[Target]):
        self.targets = targets
        self._ping_process = None
    
    async def ping_target(self, target: Target, logfile: str = None, only_down: bool = False) -> None:
        """Выполнить пинг одной цели."""
        try:
            # icmplib: ping с 1 пакетом, timeout 1 секунда
            result = await async_ping(
                target.ip,
                count=1,
                timeout=1.0
            )
            
            if result.is_alive:
                # result.avg_rtt возвращает среднее RTT
                rtt = result.avg_rtt or result.min_rtt or 1.0
                target.update(rtt, True)
                # Логирование успешного пинга
                target.log_event(Status.UP, rtt, logfile=logfile, only_down=only_down)
            else:
                # Пинг не удался
                target.update(None, False)
                # Логирование неудачного пинга
                target.log_event(Status.DOWN, logfile=logfile, only_down=only_down)
                
        except (asyncio.CancelledError, KeyboardInterrupt):
            raise
        except ICMPLibError as e:
            # Ошибка icmplib считается потерей
            target.update(None, False)
            target.log_event(Status.DOWN, error=str(e), logfile=logfile, only_down=only_down)
        except Exception as e:
            # Любая другая ошибка считается потерей
            target.update(None, False)
            target.log_event(Status.DOWN, error=str(e), logfile=logfile, only_down=only_down)
    
    async def ping_all(self, logfile: str = None, only_down: bool = False) -> None:
        """Пинговать все цели параллельно."""
        if not self.targets:
            return
        await asyncio.gather(*[self.ping_target(t, logfile, only_down) for t in self.targets], return_exceptions=True)


class Dashboard:
    """TUI-интерфейс для отображения целей."""
    
    def __init__(self, targets: List[Target], logfile: str = None, only_down: bool = False):
        self.targets = targets
        self.selected_index = 0
        self.start_time = time.time()
        self.last_update = time.time()
        self.update_count = 0
        self.paused = False  # Флаг паузы
        self.logfile = logfile  # Путь к лог-файлу
        self.only_down = only_down  # Логировать только DOWN
        self.log_file_handle = None  # Открытый файл для лога
        self._setup_curses()
    
    def _setup_curses(self) -> None:
        """Настроить curses."""
        self.stdscr = __import__("curses").initscr()
        __import__("curses").start_color()
        __import__("curses").use_default_colors()
        __import__("curses").noecho()
        __import__("curses").cbreak()
        __import__("curses").curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.keypad(True)
        
        # Открыть лог-файл если указан
        if self.logfile:
            try:
                self.log_file_handle = open(self.logfile, "a", encoding="utf-8")
            except Exception as e:
                print(f"Ошибка открытия лог-файла: {e}")
        
        # Инициализация цветов
        if __import__("curses").has_colors():
            __import__("curses").init_pair(1, __import__("curses").COLOR_GREEN, -1)   # Green
            __import__("curses").init_pair(2, __import__("curses").COLOR_YELLOW, -1)  # Yellow
            __import__("curses").init_pair(3, __import__("curses").COLOR_RED, -1)     # Red
            __import__("curses").init_pair(4, __import__("curses").COLOR_CYAN, -1)    # Header
            __import__("curses").init_pair(5, __import__("curses").COLOR_WHITE, -1)   # Normal
    
    def _get_color_for_target(self, target: Target) -> int:
        """Определить цвет для цели на основе RTT и потерь."""
        if target.status == Status.DOWN:
            return __import__("curses").color_pair(3)  # Red
        
        rtt = target.avg_rtt or 0
        loss = target.loss_percentage
        
        if loss > 50 or rtt >= 500:
            return __import__("curses").color_pair(3)  # Red
        elif loss > 20 or rtt >= 100:
            return __import__("curses").color_pair(2)  # Yellow
        else:
            return __import__("curses").color_pair(1)  # Green
    
    def _resize(self) -> None:
        """Обработать ресайз терминала."""
        __import__("curses").endwin()
        __import__("curses").refresh()
        self.stdscr = __import__("curses").initscr()
        __import__("curses").resizeterm(*__import__("curses").stdscr().getmaxyx())
    
    def _draw_header(self, width: int) -> None:
        """Нарисовать заголовок таблицы."""
        try:
            # Три столбца RTT: средний, последний и статистика за всё время + график
            header = f"{'IP Address':<20} {'Status':<8} {'RTT avg (ms)':<14} {'RTT last (ms)':<14} {'All-time':<14} {'Loss %':<10} {'Graph':<25}"
            self.stdscr.addstr(1, 0, header[:width-1].ljust(width-1), 
                             __import__("curses").color_pair(4) | __import__("curses").A_BOLD)
        except __import__("curses").error:
            pass
    
    def _draw_targets(self, width: int, height: int) -> None:
        """Нарисовать список целей."""
        start_row = 3  # Сдвигаем вниз на 2 строки для статуса и заголовка
        max_rows = height - 4  # Оставляем место для заголовка и статуса
        
        for i, target in enumerate(self.targets):
            if i >= max_rows:
                break
            
            row = start_row + i
            
            # Статус
            status_text = "UP" if target.status == Status.UP else "DOWN"
            
            # RTT средний
            avg_rtt_text = target.get_avg_rtt_display()
            
            # RTT последний
            last_rtt_text = target.get_rtt_display()
            
            # Статистика за всё время (среднее/мин/макс)
            all_time_text = target.get_all_time_stats()
            
            # Loss %
            loss_text = f"{target.loss_percentage:.1f}%"
            
            # ASCII-график RTT
            graph_text = target.get_rtt_graph()
            
            line = f"{target.ip:<20} {status_text:<8} {avg_rtt_text:<14} {last_rtt_text:<14} {all_time_text:<14} {loss_text:<10} {graph_text:<25}"
            
            color = self._get_color_for_target(target)
            if i == self.selected_index:
                self.stdscr.addstr(row, 0, line[:width-1].ljust(width-1),
                                 color | __import__("curses").A_REVERSE)
            else:
                self.stdscr.addstr(row, 0, line[:width-1].ljust(width-1), color)
    
    def _draw_status(self, width: int, height: int, ping_interval: float) -> None:
        """Нарисовать строку состояния."""
        try:
            elapsed = time.time() - self.start_time
            uptime = f"{int(elapsed // 3600):02d}:{int((elapsed % 3600) // 60):02d}:{int(elapsed % 60):02d}"
            
            targets_count = len(self.targets)
            update_rate = self.update_count / (time.time() - self.start_time) if elapsed > 0 else 0
            
            # Статус отправки
            status_send = "PAUSED" if self.paused else "SENDING"
            status_color = __import__("curses").color_pair(2) if self.paused else __import__("curses").color_pair(4)
            
            status_line = f"[{status_send}] | Targets: {targets_count} | Uptime: {uptime} | Updates/s: {update_rate:.1f} | Ping: {ping_interval}s"
            status_line += " | q/Ctrl+X:quit | r:reload | p:pause | ^↑/↓:navigate"
            
            self.stdscr.addstr(height - 1, 0, status_line[:width-1].ljust(width-1),
                             status_color)
        except __import__("curses").error:
            pass
    
    def draw(self, ping_interval: float) -> None:
        """Отрисовать весь дашборд."""
        try:
            height, width = self.stdscr.getmaxyx()
            
            # Обработка ресайза
            if height < 10 or width < 80:
                self.stdscr.clear()
                self.stdscr.addstr(0, 0, "Terminal too small", __import__("curses").A_BOLD)
                self.stdscr.refresh()
                return
            
            self.stdscr.clear()
            
            self._draw_header(width)
            self._draw_targets(width, height)
            self._draw_status(width, height, ping_interval)
            
            self.stdscr.refresh()
            self.last_update = time.time()
            if not self.paused:
                self.update_count += 1
            
        except __import__("curses").error:
            pass
    
    def cleanup(self) -> None:
        """Восстановить терминал."""
        try:
            __import__("curses").endwin()
            # Закрыть лог-файл
            if self.log_file_handle:
                self.log_file_handle.close()
        except Exception:
            pass


def load_targets(filepath: str) -> List[str]:
    """Загрузить список целей из файла."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            targets = []
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    targets.append(line)
            return targets
    except FileNotFoundError:
        print(f"Ошибка: файл '{filepath}' не найден")
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}")
        sys.exit(1)


async def main_loop(dashboard: Dashboard, ping_manager: PingManager, 
                   file_path: str, reload_event: asyncio.Event, ping_interval: float, logfile: str = None, only_down: bool = False) -> None:
    """Основной цикл программы."""
    targets_list = ping_manager.targets
    last_ping_time = 0
    refresh_interval = 0.15  # обновлять экран каждые 150мс
    
    while True:
        try:
            # Обработка ввода
            key = dashboard.stdscr.getch()
            
            if key == -1:
                pass
            elif key in (ord('q'), 3, ord('x')):  # q, Ctrl+C, Ctrl+X
                break
            elif key in (ord('r'), ord('R')):
                # Перечитать файл
                new_targets = load_targets(file_path)
                # Сопоставить с существующими целями
                old_targets_dict = {t.ip: t for t in targets_list}
                new_targets_list = []
                for ip in new_targets:
                    if ip in old_targets_dict:
                        new_targets_list.append(old_targets_dict[ip])
                    else:
                        new_targets_list.append(Target(ip=ip))
                
                targets_list.clear()
                targets_list.extend(new_targets_list)
                ping_manager.targets = targets_list
                
            elif key in (ord('p'), ord('P')):  # p - пауза/запуск
                dashboard.paused = not dashboard.paused
            elif key == __import__("curses").KEY_UP:
                if targets_list and dashboard.selected_index > 0:
                    dashboard.selected_index -= 1
            elif key == __import__("curses").KEY_DOWN:
                if targets_list and dashboard.selected_index < len(targets_list) - 1:
                    dashboard.selected_index += 1
            elif key == __import__("curses").KEY_RESIZE:
                dashboard._resize()
            
            # Пингование (не чаще чем раз в ping_interval, если не на паузе)
            if not dashboard.paused:
                current_time = time.time()
                if current_time - last_ping_time >= ping_interval:
                    await ping_manager.ping_all(logfile, only_down)
                    last_ping_time = current_time
            
            # Рисуем дашборд
            dashboard.draw(ping_interval)
            
            # Ждём перед следующим обновлением
            await asyncio.sleep(refresh_interval)
            
        except asyncio.CancelledError:
            break
        except Exception:
            pass


def main() -> None:
    """Точка входа."""
    parser = argparse.ArgumentParser(
        description="Ping Monitor - инструмент мониторинга доступности целей"
    )
    parser.add_argument(
        "--targets", "-t",
        default="targets.txt",
        help="Путь к файлу со списком целей (по умолчанию: targets.txt)"
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=1,
        choices=range(1, 1001),
        metavar="[1-1000]",
        help="Интервал между пингами в секундах (по умолчанию: 1, максимум: 1000)"
    )
    parser.add_argument(
        "--logfile", "-l",
        default=None,
        help="Путь к файлу лога (по умолчанию: нет логирования)"
    )
    parser.add_argument(
        "--only-down", "-d",
        action="store_true",
        help="Логировать только события DOWN (без RTT)"
    )
    
    args = parser.parse_args()
    
    # Загрузка целей
    target_ips = load_targets(args.targets)
    targets = [Target(ip=ip) for ip in target_ips]
    
    if not targets:
        print("Нет целей для мониторинга")
        sys.exit(1)
    
    # Инициализация
    ping_manager = PingManager(targets)
    dashboard = Dashboard(targets, args.logfile, args.only_down)
    
    try:
        # Запуск основного цикла
        asyncio.run(main_loop(dashboard, ping_manager, args.targets, asyncio.Event(), args.interval, args.logfile, args.only_down))
    finally:
        dashboard.cleanup()


if __name__ == "__main__":
    main()
