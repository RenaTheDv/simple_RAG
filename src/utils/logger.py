# Универсальная функция логирования для всех файлов. Логируем в папку logs.
import logging
from pathlib import Path
from datetime import datetime
import sys



def get_module_logger(module_name: str):
    logger = logging.getLogger(f"legal_rag.{module_name}")
    logger.setLevel(logging.INFO)
    
    # Формат
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Папка для модуля
    log_dir = Path("logs") / module_name
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Файловый обработчик (ротация по дням)
    today = datetime.now().strftime("%Y-%m-%d")
    file_handler = logging.FileHandler(log_dir / f"{module_name}_{today}.log")
    file_handler.setFormatter(formatter)
    
    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger