# Собираем HTML-файлы этим скриптом. Количество можно изменить (через .env.example)

import os
import time
from pathlib import Path
import sys
from dotenv import load_dotenv
import requests
from fake_useragent import UserAgent
import logging
sys.path.append(str(Path(__file__).resolve().parents[2]))   # для импорта get_module_logger
from src.utils.logger import get_module_logger


# Инициализируем logger
logger = get_module_logger('collector')

# Создаем класс для сбора HTML-файлов
class HTMLCollector:
    def __init__(self):
        # Забираем параметры из .env (пришлось указать пути потому что не видит)
        load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / '.env.example')


        # Основные настройки
        self.data_dir = Path(os.getenv('DATA_DIR', './data'))     # Через путь, чтобы можно было как с путем работать дальше
        self.raw_dir = self.data_dir / 'raw'
        self.court_url = os.getenv('COURT_SITE_URL')
        self.max_cases = int(os.getenv('MAX_CASES'))
        self.delay = float(os.getenv('REQUEST_DELAY'))
        self.min_len = int(os.getenv('MIN_HTML_LENGTH'))
        self.retry_attempts = int(os.getenv('RETRY_ATTEMPTS', 3))

        # Проверка на папки, создаем если отсутствуют
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self._init_session()

    def _init_session(self):
        # Инициализируем сессию для парсинга
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': UserAgent().chrome,
            'Accept-Language': 'ru-RU,ru;q=0.9',
            'Accept': 'application/json'
        })

    def _download_document(self, case_id: str) -> bool:
        # Скачивание и сохранение одного документа
        try:
            case_url = f'{self.court_url}/Card/{case_id}'
            response = self.session.get(case_url, timeout=15)
            response.raise_for_status()
            
            if len(response.text) < self.min_len:
                logger.debug(f'Skipped short document: {case_id}')
                return False
                
            filepath = self.raw_dir / f'{case_id}.html'
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(response.text)
            return True
            
        except Exception as e:
            logger.warning(f'Download failed for {case_id}: {str(e)}')
            return False

    def collect_from_kad(self) -> int:
        # Основной метод сбора данных
        search_url = f'{self.court_url}/Kad/SearchInstances'
        total_downloaded = 0
        page = 1

        logger.info(f"Starting collection (target: {self.max_cases} cases)")

        while total_downloaded < self.max_cases:
            payload = {
                'Page': page,
                'Count': 50,
                'SortType': 'Date',
                'SortDirection': 'Desc',
                'DateFrom': '2022-01-01',  # Более широкий диапазон
                'DateTo': '2023-12-31',
                'WithVKSInstances': True
            }

            for attempt in range(self.retry_attempts):
                try:
                    response = self.session.post(
                        search_url,
                        json=payload,
                        timeout=20
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    if not data.get('Success', False):
                        raise ValueError(f"API error: {data.get('Message')}")
                    
                    items = data.get('Result', {}).get('Items', [])
                    if not items:
                        logger.info("No more cases found")
                        return total_downloaded

                    for item in items:
                        if case_id := item.get('CaseId'):
                            if self._download_document(case_id):
                                total_downloaded += 1
                                logger.info(f'Progress: {total_downloaded}/{self.max_cases}')
                                
                                if total_downloaded >= self.max_cases:
                                    break
                                    
                            time.sleep(self.delay)
                    
                    break  # Успешная обработка страницы
                    
                except Exception as e:
                    logger.warning(f'Attempt {attempt + 1} failed: {str(e)}')
                    if attempt == self.retry_attempts - 1:
                        logger.error('Max retries reached')
                        return total_downloaded
                    time.sleep(5 * (attempt + 1))  # Увеличение задержки

            page += 1

        logger.info(f'Collection completed. Total downloaded: {total_downloaded}')
        return total_downloaded
    

def main():
    # Точка входа для запуска из командной строки
    try:
        logger.info("Initializing HTML collector")
        collector = HTMLCollector()
        
        logger.info("Starting document collection")
        downloaded_count = collector.collect_from_kad()
        
        logger.info(f"Successfully downloaded {downloaded_count} documents")
        return 0
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    # Настройка базового логгера для консоли
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Запуск главной функции
    exit_code = main()
    
    # Завершение программы с кодом возврата
    exit(exit_code)
