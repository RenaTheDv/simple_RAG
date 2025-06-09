# Парсим решение в JSON

import re
import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from PyPDF2 import PdfReader
from dataclasses import dataclass
import logging
import sys
import fitz  # PyMuPDF
from dotenv import load_dotenv

# Load environment variables from .env.example in project root
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / '.env.example')

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.utils.logger import get_module_logger

logger = get_module_logger('parser')

@dataclass
class DocumentPaths:
    raw: Path
    processed: Path

class RussianLegalDocParser:
    def __init__(self):
        """Initialize parser with paths from environment variables."""
        data_root = Path(os.getenv('DATA_ROOT', 'data'))
        self.raw_dir = data_root / os.getenv('RAW_DATA_DIR', 'raw')
        self.processed_dir = data_root / os.getenv('PROCESSED_DATA_DIR', 'processed')
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file."""
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    
    def extract_articles(self, text: str) -> List[str]:
        """Extract referenced legal articles using regex patterns."""
        # Common patterns in Russian legal documents
        patterns = [
            r'ст\.\s*(\d+)\s*ГК\s*РФ',
            r'статьи?\s*(\d+)\s*Гражданского\s*кодекса',
            r'статьи?\s*(\d+)\s*ГК\s*РФ'
        ]
        
        articles = set()
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                articles.add(f"Статья {match.group(1)} ГК РФ")
        
        return sorted(list(articles))
    
    def extract_sections(self, text: str) -> Dict[str, str]:
        """Extract fabula and decision sections from the text."""
        # This is a simplified version. In reality, you'd need more sophisticated
        # section detection based on your specific document format
        
        # Attempt to find the decision section (usually after "ПОСТАНОВИЛ:" or "РЕШИЛ:")
        decision_markers = ["ПОСТАНОВИЛ:", "РЕШИЛ:", "ОПРЕДЕЛИЛ:"]
        decision_start = -1
        for marker in decision_markers:
            pos = text.find(marker)
            if pos != -1:
                decision_start = pos
                break
        
        if decision_start == -1:
            # Fallback: assume last 30% is decision
            decision_start = int(len(text) * 0.7)
            
        return {
            "fabula": text[:decision_start].strip(),
            "decision": text[decision_start:].strip()
        }
    
    def parse_document(self, pdf_path: str) -> Dict:
        """Parse a single PDF document."""
        text = self.extract_text_from_pdf(pdf_path)
        sections = self.extract_sections(text)
        articles = self.extract_articles(text)
        
        # Extract case number and date (simplified)
        case_number = "Н/Д"  # In reality, you'd extract this
        date = "Н/Д"        # In reality, you'd extract this
        
        return {
            "case_number": case_number,
            "date": date,
            "fabula": sections["fabula"],
            "decision": sections["decision"],
            "articles": articles
        }
    
    def process_all_documents(self):
        """Process all PDF documents in the raw directory."""
        for pdf_file in self.raw_dir.glob("*.pdf"):
            try:
                result = self.parse_document(str(pdf_file))
                
                # Save to JSON
                output_file = self.processed_dir / f"{pdf_file.stem}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                    
                print(f"Successfully processed: {pdf_file.name}")
                
            except Exception as e:
                print(f"Error processing {pdf_file.name}: {str(e)}")

def main() -> int:
    try:
        parser = RussianLegalDocParser()
        parser.process_all_documents()
        return 0
    except Exception as e:
        logger.critical(f"Фатальная ошибка: {str(e)}", exc_info=True)
        return 1

if __name__ == '__main__':
    exit(main())