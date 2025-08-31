"""
Notebook-Style Script Support Module.

Модуль предоставляет функциональность для создания Python скриптов, 
имитирующих поведение Jupyter ноутбуков со step-by-step выполнением.

Основной компонент:
- NotebookSimulator: класс для имитации поведения Jupyter ноутбука

Usage:
    from bquant.core.nb import NotebookSimulator
    
    # Простейшее использование - все автоматически
    nb = NotebookSimulator()  # автоопределение всех парметров
    
    nb.step("Step 1: Data Loading")
    # ваш код для шага 1
    nb.wait()
    
    nb.step("Step 2: Analysis")
    # ваш код для шага 2
    nb.wait()
    
    nb.finish()
"""

import sys
import argparse
import traceback
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Union, IO, List
from contextlib import contextmanager

__all__ = [
    'NotebookSimulator'
]


class NotebookSimulator:
    """
    Класс для имитации поведения Jupyter ноутбука в Python скриптах.
    
    Автоматически определяет имя скрипта, настраивает логирование и парсинг аргументов.
    Предоставляет простой API для пошагового выполнения с интерактивным управлением.
    
    Example:
        >>> nb = NotebookSimulator()  # автоопределение всех параметров
        >>> 
        >>> nb.step("Loading Data")
        >>> # код загрузки данных
        >>> nb.wait()
        >>> 
        >>> nb.step("Processing Data")
        >>> # код обработки
        >>> nb.wait()
        >>> 
        >>> nb.finish()
    """
    
    def __init__(
        self, 
        description: Optional[str] = None,
        default_log_name: Optional[str] = None,
        auto_setup: bool = True,
        catch_traceback: bool = True
    ):
        """
        Инициализация NotebookSimulator.
        
        Args:
            description: Описание скрипта (если None - автоопределение из имени файла)
            default_log_name: Имя лог файла (если None - автогенерация на основе имени скрипта)
            auto_setup: Автоматически парсить аргументы и настроить логирование
            catch_traceback: Логировать полный трейсбек при ошибках
        """
        # Автоопределение имени скрипта
        self.script_path = Path(sys.argv[0]) if sys.argv[0] else Path("notebook_script.py")
        self.script_name = self.script_path.stem
        
        # Описание скрипта
        if description is None:
            # Автоопределение на основе имени файла
            description = self.script_name.replace('_', ' ').replace('-', ' ').title()
        self.description = description
        
        # Лог файл по умолчанию
        if default_log_name is None:
            default_log_name = f"{self.script_name}_log.txt"
        self.default_log_name = default_log_name
        
        # Внутренние переменные
        self.log_file: Optional[IO] = None
        self.enable_trap = True
        self.step_counter = 0
        self.start_time = datetime.now()
        self.catch_traceback = catch_traceback
        
        # Автонастройка
        if auto_setup:
            self._setup_from_args()
    
    def _setup_from_args(self) -> None:
        """Автоматическая настройка на основе аргументов командной строки."""
        parser = self._create_argument_parser()
        args = parser.parse_args()
        
        # Применяем настройки
        self.enable_trap = args.trap
        self.setup_logging(args.log)
        
        # Выводим заголовок
        self._print_script_header()
    
    def _create_argument_parser(self) -> argparse.ArgumentParser:
        """Создание парсера аргументов."""
        script_dir = self.script_path.parent
        default_log = script_dir / self.default_log_name
        
        examples = [
            f"python {self.script_path.name}                    # Default: console + file log, with traps",
            f"python {self.script_path.name} --log mylog.txt    # Custom log file", 
            f"python {self.script_path.name} --no-trap          # Run without step breaks",
            f"python {self.script_path.name} --log test.log --no-trap  # Custom log, no breaks"
        ]
        
        epilog = "\nExamples:\n  " + "\n  ".join(examples)
        
        parser = argparse.ArgumentParser(
            description=f'{self.description} - Notebook-style script',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=epilog
        )
        
        parser.add_argument(
            '--log', 
            default=str(default_log),
            help=f'Log file path (default: {default_log})'
        )
        
        trap_group = parser.add_mutually_exclusive_group()
        trap_group.add_argument(
            '--trap', 
            action='store_true',
            default=True,
            help='Enable step-by-step execution (default)'
        )
        trap_group.add_argument(
            '--no-trap',
            action='store_false', 
            dest='trap',
            help='Disable step-by-step execution'
        )
        
        return parser
    
    def _print_script_header(self) -> None:
        """Вывод заголовка скрипта."""
        self.log("[>>] Starting " + self.description)
        self.log("=" * max(50, len(self.description) + 20))
        self.log(f"[SCRIPT] {self.description}")
        self.log(f"[DATE] Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log("=" * max(50, len(self.description) + 20))
        
    def setup_logging(self, log_file_path: Optional[Union[str, Path]] = None) -> None:
        """
        Настройка логирования в файл и консоль.
        
        Args:
            log_file_path: Путь к файлу для логирования. 
                          Если None, логирование только в консоль.
        """
        if log_file_path:
            log_path = Path(log_file_path)
            self.log_file = open(log_path, 'w', encoding='utf-8')
            self.log(f"[LOG] Log started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}", to_file_only=True)
            self.log(f"[OUTPUT] Output will be written to: {log_path}")
    
    def set_trap_mode(self, enable: bool) -> None:
        """
        Установка режима пошагового выполнения.
        
        Args:
            enable: True для включения пошагового режима
        """
        self.enable_trap = enable
    
    def log(self, message: str, to_file_only: bool = False) -> None:
        """
        Вывод сообщения в консоль и/или файл.
        
        Args:
            message: Сообщение для вывода
            to_file_only: Если True, выводить только в файл
        """
        if not to_file_only:
            try:
                print(message)
            except UnicodeEncodeError:
                safe_message = message.encode('utf-8', errors='replace').decode(sys.stdout.encoding, errors='replace')
                print(safe_message)

        if self.log_file:
            self.log_file.write(message + '\n')
            self.log_file.flush()
    
    def step(self, title: str, level: int = 0, separator_char: str = "-") -> None:
        """
        Начало нового шага выполнения.
        
        Args:
            title: Название шага
            level: Уровень вложенности (0=основной, 1=подшаг)
            separator_char: Символ для разделителя
        """
        if level == 0:
            self.step_counter += 1
            separator_line = "=" * 80
            step_title = f"STEP {self.step_counter}: {title}"
            prefix = "[STEP]"
        else:
            separator_line = separator_char * max(40, len(title) + 10)
            step_title = title
            prefix = "[TEST]" if "Test" in title else "[SUBSTEP]"
            
        self.log(separator_line)
        self.log(f"{prefix} {step_title}")
        self.log(separator_char * max(30, len(step_title)))
    
    def substep(self, title: str) -> None:
        """
        Создание подшага.
        
        Args:
            title: Название подшага
        """
        self.step(title, level=1, separator_char="=")
    
    def wait(self) -> None:
        """
        Ожидание команды продолжения (если включен trap режим).
        
        Пользователь может нажать ENTER для продолжения или 'q' для выхода.
        При прерывании (Ctrl+C) скрипт корректно завершается.
        """
        if not self.enable_trap:
            return
            
        self.log("\n" + "=" * 60)
        try:
            user_input = input("Press ENTER to continue or 'q' to quit: ").strip().lower()
            if user_input == 'q':
                self.log("Exiting...")
                self.cleanup_and_exit(0)
        except KeyboardInterrupt:
            self.log("\nKeyboard interrupt received. Exiting...")
            self.cleanup_and_exit(1)
        self.log("=" * 60 + "\n")
    
    def info(self, message: str) -> None:
        """
        Вывод информационного сообщения с префиксом.
        
        Args:
            message: Информационное сообщение
        """
        self.log(f"[INFO] {message}")
    
    def success(self, message: str) -> None:
        """
        Вывод сообщения об успехе.
        
        Args:
            message: Сообщение об успешной операции
        """
        self.log(f"[OK] {message}")
    
    def error(self, message: str) -> None:
        """
        Вывод сообщения об ошибке.
        
        Args:
            message: Сообщение об ошибке
        """
        self.log(f"[FAIL] {message}")
    
    def warning(self, message: str) -> None:
        """
        Вывод предупреждения.
        
        Args:
            message: Текст предупреждения
        """
        self.log(f"[WARN] {message}")
    
    def data_info(self, label: str, value: Any) -> None:
        """
        Вывод информации с данными в структурированном формате.
        
        Args:
            label: Метка данных
            value: Значение для отображения
        """
        self.log(f"  {label}: {value}")
    
    def section_header(self, title: str) -> None:
        """
        Вывод заголовка секции.
        
        Args:
            title: Название секции
        """
        self.log(f"\n[SECTION] {title}:")
        self.log("=" * max(20, len(title)))
    
    def summary_item(self, label: str, value: Any, success: Optional[bool] = None) -> None:
        """
        Элемент для резюме/сводки.
        
        Args:
            label: Метка элемента
            value: Значение
            success: Если задано, показывает статус (✅/❌)
        """
        if success is True:
            prefix = "[OK]"
        elif success is False:
            prefix = "[FAIL]"
        else:
            prefix = "[DATA]"
        
        self.log(f"{prefix} {label}: {value}")
    
    def next_steps(self, steps: List[str]) -> None:
        """
        Вывод списка следующих шагов.
        
        Args:
            steps: Список следующих действий
        """
        self.log("\n[NEXT] Next Steps:")
        for step in steps:
            self.log(f"- {step}")
    
    def finish(self, message: str = "Script finished successfully!") -> None:
        """
        Завершение выполнения скрипта.
        
        Args:
            message: Сообщение о завершении
        """
        self.log(f"\n[END] {message}")
        self.cleanup_and_exit(0)
    
    def cleanup_and_exit(self, exit_code: int = 0) -> None:
        """
        Очистка ресурсов и выход.
        
        Args:
            exit_code: Код завершения (0=успех, 1=ошибка)
        """
        if self.log_file:
            end_time = datetime.now()
            duration = end_time - self.start_time
            self.log(f"[END] Log ended: {end_time.strftime('%Y-%m-%d %H:%M:%S')}", to_file_only=True)
            self.log(f"[TIME] Duration: {duration}", to_file_only=True)
            self.log_file.close()
        sys.exit(exit_code)
    
    @contextmanager
    def error_handling(self, operation_name: str, critical: bool = False):
        """
        Контекстный менеджер для обработки ошибок в операциях.
        
        Args:
            operation_name: Название операции
            critical: Если True, завершает скрипт при ошибке
            
        Usage:
            >>> with nb.error_handling("Loading data", critical=True):
            ...     data = load_data()
            >>> # Если ошибка и critical=True, скрипт завершится
        """
        try:
            yield
            self.success(f"{operation_name} completed successfully")
        except Exception as e:
            self.error(f"{operation_name} failed: {e}")
            if self.catch_traceback:
                tb_string = traceback.format_exc()
                self.log("\n--- TRACEBACK ---")
                self.log(tb_string)
                self.log("--- END TRACEBACK ---\n")
            if critical:
                self.cleanup_and_exit(1)
            raise

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        Форматирование размера файла в читаемый вид.
        
        Args:
            size_bytes: Размер в байтах
            
        Returns:
            str: Форматированный размер (например, "1.23 MB")
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024**2:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024**3:
            return f"{size_bytes / (1024**2):.2f} MB"
        else:
            return f"{size_bytes / (1024**3):.2f} GB"

    def format_duration(self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> str:
        """
        Форматирование длительности операции.
        
        Args:
            start_time: Время начала (по умолчанию время старта скрипта)
            end_time: Время окончания (по умолчанию текущее время)
            
        Returns:
            str: Форматированная длительность
        """
        if start_time is None:
            start_time = self.start_time
        if end_time is None:
            end_time = datetime.now()
        
        duration = end_time - start_time
        total_seconds = int(duration.total_seconds())
        
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
