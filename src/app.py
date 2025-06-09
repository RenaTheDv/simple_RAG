# Реализуем RAG - поиск и генерацию ответа

import os
from pathlib import Path
from typing import List, Dict, Any
import requests
from src.data_processing.vector_db import VectorDB
from dotenv import load_dotenv

# Load environment variables from .env.example in project root
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / '.env.example')

# Uncomment below for OpenAI
# from openai import OpenAI
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class LegalRAG:
    def __init__(self):
        """Initialize the RAG system using environment variables."""
        self.vector_db = VectorDB()
        self.vector_db.load_index()
        
        # YandexGPT API settings
        self.yandex_api_key = os.getenv("YANDEX_API_KEY")
        self.yandex_folder_id = os.getenv("YANDEX_FOLDER_ID")
        
        if not self.yandex_api_key or not self.yandex_folder_id:
            raise ValueError("YandexGPT API credentials not found in environment variables")
            
        # Get other settings from environment
        self.top_k = int(os.getenv('TOP_K_RESULTS', '5'))
        
    def format_prompt(self, query: str, relevant_chunks: List[Dict[str, Any]]) -> str:
        """Format the prompt for the LLM."""
        context = []
        for chunk in relevant_chunks:
            section_text = "фабула" if chunk["section"] == "fabula" else "решение"
            context.append(f"Из дела №{chunk['case_number']} от {chunk['date']}:")
            context.append(f"[{section_text}]")
            context.append(chunk.get("text", ""))  # Add chunk text if available
            context.append("Упомянутые статьи: " + ", ".join(chunk["articles"]))
            context.append("---")
        
        prompt = f"""Ты - опытный юрист, специализирующийся на российском праве. Используй предоставленные фрагменты судебных решений, чтобы ответить на вопрос пользователя.

Контекст из судебных решений:
{"".join(context)}

Вопрос пользователя: {query}

Дай развернутый ответ, опираясь на предоставленные прецеденты. Укажи конкретные статьи законов, если они релевантны.
"""
        return prompt
    
    def get_yandex_answer(self, prompt: str) -> str:
        """Get answer from YandexGPT."""
        url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        headers = {
            "Authorization": f"Api-Key {self.yandex_api_key}",
            "x-folder-id": self.yandex_folder_id
        }
        data = {
            "modelUri": f"gpt://{self.yandex_folder_id}/yandexgpt-lite",
            "completionOptions": {
                "stream": False,
                "temperature": 0.6,
                "maxTokens": 2000
            },
            "messages": [
                {
                    "role": "system",
                    "text": "Ты - опытный юрист, специализирующийся на российском праве."
                },
                {
                    "role": "user",
                    "text": prompt
                }
            ]
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result["result"]["alternatives"][0]["message"]["text"]
        except Exception as e:
            print(f"Error calling YandexGPT: {str(e)}")
            return self.get_openai_fallback(prompt)
    
    def get_openai_fallback(self, prompt: str) -> str:
        """Fallback to OpenAI if YandexGPT fails."""
        # Uncomment and modify below to use OpenAI
        # try:
        #     response = client.chat.completions.create(
        #         model="gpt-4",
        #         messages=[
        #             {"role": "system", "content": "Ты - опытный юрист, специализирующийся на российском праве."},
        #             {"role": "user", "content": prompt}
        #         ],
        #         temperature=0.7,
        #         max_tokens=2000
        #     )
        #     return response.choices[0].message.content
        # except Exception as e:
        #     print(f"Error calling OpenAI fallback: {str(e)}")
        #     return "Извините, произошла ошибка при получении ответа."
        
        return "OpenAI fallback не настроен. Раскомментируйте код для использования."
    
    def format_output(self, answer: str, relevant_chunks: List[Dict[str, Any]]) -> str:
        """Format the final output with sources."""
        # Get unique sources
        sources = set()
        articles = set()
        
        for chunk in relevant_chunks:
            sources.add(f"Решение суда №{chunk['case_number']} от {chunk['date']}")
            articles.update(chunk["articles"])
        
        # Format output
        output = [
            f"Ответ: {answer}\n",
            "Использованные источники:"
        ]
        
        for source in sorted(sources):
            output.append(f"- {source}")
            
        for article in sorted(articles):
            output.append(f"- {article}")
            
        return "\n".join(output)
    
    def get_answer(self, query: str) -> str:
        """
        Get answer for a user query.
        
        Args:
            query: User's question
            
        Returns:
            Formatted answer with sources
        """
        # Get relevant chunks using TOP_K from environment
        relevant_chunks = self.vector_db.search(query, k=self.top_k)
        
        # Format prompt
        prompt = self.format_prompt(query, relevant_chunks)
        
        # Get answer from LLM
        answer = self.get_yandex_answer(prompt)
        
        # Format output
        return self.format_output(answer, relevant_chunks)

if __name__ == "__main__":
    # Initialize RAG
    rag = LegalRAG()
    
    # Example query
    query = "Какие основания для расторжения договора аренды?"
    print(rag.get_answer(query))

