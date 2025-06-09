# Простенький web-интерфейс для теста работоспособности на streamlit

import os
import sys
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
import traceback

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from src.app import LegalRAG

# Load environment variables from .env.example in project root
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / '.env.example')

# Set page config
st.set_page_config(
    page_title="Юридический помощник",
    page_icon="⚖️",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stTextInput > div > div > input {
        font-size: 20px;
    }
    .stTextArea > div > div > textarea {
        font-size: 18px;
    }
    .main {
        padding: 2rem;
    }
    .stMarkdown {
        font-size: 18px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize RAG system
@st.cache_resource
def get_rag():
    return LegalRAG()

try:
    rag = get_rag()
except ValueError as e:
    st.error(f"Error initializing RAG system: {str(e)}")
    st.stop()

# Header
st.title("🏛️ Юридический помощник")
st.markdown("""
Задайте вопрос по российскому праву, и я найду релевантные судебные решения и нормативные акты.
""")

# User input
query = st.text_area(
    "Ваш вопрос:",
    height=100,
    placeholder="Например: Какие основания для расторжения договора аренды?"
)

# Add a submit button
if st.button("Получить ответ", type="primary"):
    if query:
        with st.spinner("Анализирую судебную практику..."):
            try:
                answer = rag.get_answer(query)
                st.markdown("---")
                st.markdown(answer)
            except Exception as e:
                st.error(f"Произошла ошибка: {str(e)}")
                st.text("Подробности ошибки:")
                st.text(traceback.format_exc())
    else:
        st.warning("Пожалуйста, введите ваш вопрос.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>Система использует российскую судебную практику и законодательство для поиска ответов.</p>
    <p>Ответы генерируются с помощью YandexGPT.</p>
</div>
""", unsafe_allow_html=True)

