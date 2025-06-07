# Собираем HTML-файлы этим скриптом. Количество можно изменить (через .env.example)

import os
import random
import time
from pathlib import Path
from dotenv import load_dotenv
import requests
from fake_useragent import UserAgent
from src.utils.logger import get_module_logger


# Инициализируем logger
logger = get_module_logger('collector')

# Создаем класс для сбора HTML-файлов
class HTMLCollector:
    def __init__(self):
        # Забираем параметры из .env
        load_dotenv()

        # Основные настройки
        self.data_dir = Path(os.getenv('DATA_DIR', './data'))     # Через путь, чтобы можно было как с путем работать дальше
        self.raw_dir = self.data_dir / 'raw'
        self.court_url = os.getenv('COURT_SITE_URL')
        self.max_cases = int(os.getenv('MAX_CASES'))
        self.delay = float(os.getenv('REQUEST_DELAY'))
        self.min_len = int(os.getenv('MIN_HTML_LENGTH'))

        # Проверка на папки, создаем если отсутствуют
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        # Настройка HTTP-сессии
        self.session = requests.Session()
        self.session.headers = {
            'User-Agent': UserAgent().chrome,
            'Accept-Language': 'ru-RU,ru;q=0.9'
        }

    def download_case(self, case_id: int) -> bool:
        # Пробуем загрузить один HTML-документ
        url = f'{self.court_url}/Case/DownloadDocument/{case_id}' 
