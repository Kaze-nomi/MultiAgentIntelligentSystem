import logging
import os
import shutil
from logging.handlers import RotatingFileHandler
import datetime
from pathlib import Path

def setup_logging(service_name):
    """
    Настраивает логирование для указанного сервиса.
    
    Структура папок:
    logs/                          - логи текущей сессии
        {service_name}.log
        all.log
    logs/history/                  - архивы всех логов
        {service_name}_history.log
        all_history.log
        {service_name}_{дата}.log  - отдельные архивы по датам
        all_{дата}.log
    
    :param service_name: Имя сервиса (строка)
    :return: Логгер для сервиса
    """
    # Создаем основную и историческую директории
    logs_dir = Path('logs')
    history_dir = logs_dir / 'history'
    
    logs_dir.mkdir(exist_ok=True, mode=0o755)
    history_dir.mkdir(exist_ok=True, mode=0o755)
    
    # Пути к файлам
    current_log_path = logs_dir / f'{service_name}.log'
    current_all_log_path = logs_dir / 'all.log'
    
    history_log_path = history_dir / f'{service_name}_history.log'
    history_all_log_path = history_dir / 'all_history.log'
    
    # Функция для архивации логов в историю
    def archive_to_history(current_path, history_path, service_label):
        if current_path.exists():
            try:
                # Получаем содержимое текущего лога
                with open(current_path, 'r', encoding='utf-8') as f:
                    current_content = f.read().strip()
                
                if not current_content:
                    print(f"Файл {current_path} пуст, архивация не требуется")
                    return
                
                # Создаем метку времени для сессии
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                date_only = datetime.datetime.now().strftime("%Y%m%d")
                
                # Формируем заголовок сессии
                separator = "=" * 80
                session_header = (
                    f"\n\n{separator}\n"
                    f"СЕССИЯ: {service_label}\n"
                    f"ВРЕМЯ НАЧАЛА: {timestamp}\n"
                    f"{separator}\n\n"
                )
                
                # Добавляем заголовок и текущие логи в историю
                with open(history_path, 'a', encoding='utf-8') as f:
                    f.write(session_header)
                    f.write(current_content)
                    f.write("\n")
                
                # Также сохраняем отдельный файл архива с датой
                archive_filename = history_dir / f"{service_label}_{date_only}.log"
                
                # Если файл за сегодня уже есть, добавляем к нему
                if archive_filename.exists():
                    with open(archive_filename, 'a', encoding='utf-8') as f:
                        f.write(session_header)
                        f.write(current_content)
                        f.write("\n")
                else:
                    with open(archive_filename, 'w', encoding='utf-8') as f:
                        f.write(session_header)
                        f.write(current_content)
                        f.write("\n")
                
                # Очищаем текущий лог-файл
                with open(current_path, 'w') as f:
                    pass
                
                print(f"✅ Архивировано: {current_path} -> {history_path}")
                print(f"📁 Также сохранено в: {archive_filename}")
                
            except Exception as e:
                print(f"⚠️ Ошибка при архивации логов {current_path}: {e}")
                # Резервное копирование на случай ошибки
                backup_path = current_path.with_suffix('.log.bak')
                try:
                    if current_path.exists():
                        shutil.copy2(current_path, backup_path)
                        print(f"Создана резервная копия: {backup_path}")
                except:
                    pass
    
    # Архивируем текущие логи в историю
    archive_to_history(current_log_path, history_log_path, service_name)
    
    # Архивируем all.log только при первом вызове
    if not hasattr(setup_logging, '_all_log_archived'):
        archive_to_history(current_all_log_path, history_all_log_path, 'all')
        setup_logging._all_log_archived = True
    
    # Форматтер для логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Хендлер для логов текущей сессии сервиса
    service_handler = RotatingFileHandler(
        str(current_log_path),
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    service_handler.setFormatter(formatter)
    service_handler.setLevel(logging.INFO)
    
    # Хендлер для общего лога текущей сессии
    all_handler = RotatingFileHandler(
        str(current_all_log_path),
        maxBytes=20*1024*1024,  # 20 MB (больше, т.к. общий)
        backupCount=5,
        encoding='utf-8'
    )
    all_handler.setFormatter(formatter)
    all_handler.setLevel(logging.INFO)
    
    # Получаем логгер для сервиса
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.INFO)
    
    # Очищаем существующие хендлеры
    logger.handlers = []
    
    # Добавляем хендлер для файла сервиса
    logger.addHandler(service_handler)
    
    # Также добавляем вывод в консоль (опционально)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    
    # Работа с корневым логгером для all.log
    root_logger = logging.getLogger()
    
    # Проверяем, не добавлен ли уже хендлер для all.log
    all_handler_exists = False
    for handler in root_logger.handlers:
        if (isinstance(handler, RotatingFileHandler) and 
            hasattr(handler, 'baseFilename') and 
            str(current_all_log_path) in handler.baseFilename):
            all_handler_exists = True
            break
    
    if not all_handler_exists:
        root_logger.addHandler(all_handler)
        root_logger.setLevel(logging.INFO)
        
    return logger


def get_recent_history(service_name=None, lines=50, from_history=True):
    """
    Показывает последние записи из истории или текущих логов.
    
    :param service_name: Имя сервиса или 'all' для общего лога
    :param lines: Количество строк для показа
    :param from_history: True - из истории, False - из текущих логов
    :return: Список строк или сообщение об ошибке
    """
    if service_name is None:
        service_name = 'all'
    
    if from_history:
        file_path = Path('logs/history') / f'{service_name}_history.log'
    else:
        file_path = Path('logs') / f'{service_name}.log'
    
    if not file_path.exists():
        return [f"Файл не найден: {file_path}"]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.readlines()
        
        # Возвращаем последние N строк
        return content[-lines:] if len(content) > lines else content
    except Exception as e:
        return [f"Ошибка чтения файла: {e}"]


def cleanup_old_logs(days_to_keep=30, keep_daily_archives=True):
    """
    Очищает старые логи и архивы.
    
    :param days_to_keep: Сколько дней хранить отдельные архивные файлы
    :param keep_daily_archives: Сохранять ли ежедневные архивы
    :return: Словарь с результатами очистки
    """
    import time
    import glob
    
    results = {
        'deleted_files': [],
        'kept_files': [],
        'errors': []
    }
    
    history_dir = Path('logs/history')
    cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
    
    # Очистка старых отдельных архивных файлов
    if not keep_daily_archives:
        pattern = history_dir / '*_*.log'  # Файлы с датами: service_20240101.log
    else:
        pattern = history_dir / '*_*.log.*'  # Бекапы архивов
    
    for file_path in glob.glob(str(pattern)):
        try:
            # Пропускаем основные файлы истории
            if file_path.endswith('_history.log'):
                continue
            
            file_time = os.path.getmtime(file_path)
            if file_time < cutoff_time:
                os.remove(file_path)
                results['deleted_files'].append(file_path)
                print(f"🗑️  Удален старый архив: {file_path}")
            else:
                results['kept_files'].append(file_path)
        except Exception as e:
            results['errors'].append(f"{file_path}: {e}")
    
    # Очистка бекапов RotatingFileHandler в основной папке
    backup_patterns = [
        'logs/*.log.*',  # Бекапы текущих логов
        'logs/*.log.bak'  # Резервные копии
    ]
    
    for pattern in backup_patterns:
        for file_path in glob.glob(pattern):
            try:
                file_time = os.path.getmtime(file_path)
                if file_time < cutoff_time:
                    os.remove(file_path)
                    results['deleted_files'].append(file_path)
                    print(f"🗑️  Удален старый бэкап: {file_path}")
                else:
                    results['kept_files'].append(file_path)
            except Exception as e:
                results['errors'].append(f"{file_path}: {e}")
    
    # Статистика
    print(f"\n📊 Результаты очистки:")
    print(f"✅ Удалено файлов: {len(results['deleted_files'])}")
    print(f"📁 Сохранено файлов: {len(results['kept_files'])}")
    if results['errors']:
        print(f"❌ Ошибок: {len(results['errors'])}")
        for error in results['errors']:
            print(f"   {error}")
    
    return results


def get_log_summary():
    """
    Показывает сводку по логам.
    
    :return: Словарь с информацией о логах
    """
    logs_dir = Path('logs')
    history_dir = logs_dir / 'history'
    
    summary = {
        'current_logs': {},
        'history_logs': {},
        'total_size_current': 0,
        'total_size_history': 0
    }
    
    # Текущие логи
    for log_file in logs_dir.glob('*.log'):
        if log_file.is_file():
            size = log_file.stat().st_size
            summary['current_logs'][log_file.name] = {
                'size': size,
                'size_human': _human_readable_size(size)
            }
            summary['total_size_current'] += size
    
    # Исторические логи
    if history_dir.exists():
        for log_file in history_dir.glob('*.log'):
            if log_file.is_file():
                size = log_file.stat().st_size
                summary['history_logs'][log_file.name] = {
                    'size': size,
                    'size_human': _human_readable_size(size)
                }
                summary['total_size_history'] += size
    
    summary['total_size_current_human'] = _human_readable_size(summary['total_size_current'])
    summary['total_size_history_human'] = _human_readable_size(summary['total_size_history'])
    
    return summary


def _human_readable_size(size_bytes):
    """
    Преобразует размер в байтах в читаемый формат.
    """
    if size_bytes == 0:
        return "0 Б"
    
    size_names = ("Б", "КБ", "МБ", "ГБ", "ТБ")
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"


# Пример использования
if __name__ == "__main__":
    # Инициализация логгера
    logger = setup_logging("test_service")
    
    # Пример логов
    logger.info("Тестовое сообщение INFO")
    logger.warning("Тестовое сообщение WARNING")
    logger.error("Тестовое сообщение ERROR")
    
    # Просмотр последних логов из истории
    print("\n📖 Последние 10 строк из истории 'all':")
    recent = get_recent_history('all', lines=10)
    for line in recent:
        print(line.rstrip())
    
    # Сводка по логам
    print("\n📊 Сводка по логам:")
    summary = get_log_summary()
    print(f"Текущие логи: {summary['total_size_current_human']}")
    print(f"Исторические логи: {summary['total_size_history_human']}")
    
    # Очистка старых логов (демонстрация, без реального удаления)
    print("\n🧹 Очистка старых логов (демо):")
    cleanup_old_logs(days_to_keep=1, keep_daily_archives=False)