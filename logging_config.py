import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging(service_name):
    """
    Настраивает логирование для указанного сервиса.
    Создает индивидуальный файл логов logs/{service_name}.log и общий файл logs/all.log.

    :param service_name: Имя сервиса (строка)
    :return: Логгер для сервиса
    """
    # Создаем директорию logs, если она не существует
    os.makedirs('logs', exist_ok=True, mode=0o777)

    # Форматтер для логов
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Хендлер для индивидуального файла сервиса
    service_handler = RotatingFileHandler(
        f'logs/{service_name}.log',
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    service_handler.setFormatter(formatter)

    # Хендлер для общего файла all.log
    all_handler = RotatingFileHandler(
        'logs/all.log',
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    all_handler.setFormatter(formatter)

    # Получаем логгер для сервиса
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.INFO)
    logger.addHandler(service_handler)

    # Добавляем хендлер для all.log к корневому логгеру, если он еще не добавлен
    root_logger = logging.getLogger()
    if not any(isinstance(h, RotatingFileHandler) and h.baseFilename.endswith('all.log') for h in root_logger.handlers):
        root_logger.addHandler(all_handler)
        root_logger.setLevel(logging.INFO)

    return logger