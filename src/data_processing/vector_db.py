# Реализовываем локальное хранилище (поскольку тест), FAISS

import os
import json
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables from .env.example in project root
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / '.env.example')

# Uncomment below for OpenAI embeddings
# from openai import OpenAI
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class VectorDB:
    def __init__(self):
        """Initialize the vector database using environment variables."""
        project_root = Path(__file__).resolve().parents[2]  # подняться на 2 уровня выше от этого файла
        
        data_dir = os.getenv('DATA_DIR', 'data')
        self.data_root = (project_root / data_dir).resolve()

        self.processed_dir = self.data_root / os.getenv('PROCESSED_DATA_DIR', 'processed')
        vector_db_dir = os.getenv('VECTOR_DB_DIR', 'data/vector_db')
        self.vector_db_dir = (project_root / vector_db_dir).resolve()
        self.vector_db_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize the embedding model
        self.model_name = os.getenv('EMBEDDING_MODEL', 'cointegrated/LaBSE-en-ru')
        self.model = SentenceTransformer(self.model_name)
        self.vector_size = self.model.get_sentence_embedding_dimension()
        
        # Initialize FAISS index
        self.index = faiss.IndexFlatL2(self.vector_size)
        self.documents: List[Dict[str, Any]] = []


        
    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks using chunk size from environment."""
        chunk_size = int(os.getenv('CHUNK_SIZE', '400'))
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)
            
        return chunks
    
    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        # Using sentence-transformers (default)
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        
        # Uncomment below for OpenAI embeddings
        # response = client.embeddings.create(
        #     input=texts,
        #     model="text-embedding-3-large"
        # )
        # embeddings = np.array([e.embedding for e in response.data])
        
        return embeddings
    
    def process_document(self, doc: Dict[str, Any]) -> tuple[List[str], List[Dict]]:
        """Process a single document into chunks with metadata."""
        chunks = []
        chunk_metadata = []

        # Разбиваем фабулу на чанки
        fabula_chunks = self.chunk_text(doc.get("фабула", ""))
        for i, chunk in enumerate(fabula_chunks):
            chunks.append(chunk)
            chunk_metadata.append({
                "тип_акта": doc.get("тип_акта", None),
                "section": "фабула",
                "chunk_index": i,
                "статьи": doc.get("статьи", []),
                "номер_дела": doc.get("номер_дела", "неизвестен"),
                "дата": doc.get("дата", "неизвестна"),
                "фабула": chunk  # если хочешь сразу текст чанка хранить
            })


        # Разбиваем решение на чанки
        decision_chunks = self.chunk_text(doc.get("решение", ""))
        for i, chunk in enumerate(decision_chunks):
            chunks.append(chunk)
            chunk_metadata.append({
                "тип_акта": doc.get("тип_акта", None),
                "section": "решение",
                "chunk_index": i,
                "статьи": doc.get("статьи", [])
            })

        return chunks, chunk_metadata
    
    def build_index(self):
        """Build the FAISS index from all documents in the processed directory."""
        all_chunks = []
        all_metadata = []
        
        # Process all JSON files
        json_files = list(self.processed_dir.glob("*.json"))
        for json_file in tqdm(json_files, desc="Processing documents"):
            with open(json_file, 'r', encoding='utf-8') as f:
                doc = json.load(f)
                
            chunks, metadata = self.process_document(doc)
            all_chunks.extend(chunks)
            all_metadata.extend(metadata)
        
        # Generate embeddings and add to index
        embeddings = self.get_embeddings(all_chunks)
        self.index.add(embeddings.astype(np.float32))
        
        # Save metadata
        self.documents = all_metadata
        
        # Save index and metadata
        self.save_index()
    
    def save_index(self):
        """Save the FAISS index and document metadata."""
        index_path = self.vector_db_dir / "legal_docs.index"
        metadata_path = self.vector_db_dir / "metadata.json"
        
        # Save FAISS index
        faiss.write_index(self.index, str(index_path))
        
        # Save metadata
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.documents, f, ensure_ascii=False, indent=2)
    
    def load_index(self):
        """Load the FAISS index and document metadata."""
        index_path = self.vector_db_dir / "legal_docs.index"
        metadata_path = self.vector_db_dir / "metadata.json"
        
        if not index_path.exists() or not metadata_path.exists():
            raise FileNotFoundError("Index or metadata file not found. Run build_index() first.")
        
        # Load FAISS index
        self.index = faiss.read_index(str(index_path))
        
        # Load metadata
        with open(metadata_path, 'r', encoding='utf-8') as f:
            self.documents = json.load(f)
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar chunks.
        
        Args:
            query: The search query
            k: Number of results to return
            
        Returns:
            List of dictionaries containing the chunks and their metadata
        """
        # Generate query embedding
        query_embedding = self.get_embeddings([query])
        
        # Search in FAISS index
        distances, indices = self.index.search(query_embedding.astype(np.float32), k)
        
        # Get results with metadata
        results = []
        for idx in indices[0]:
            if idx != -1:  # FAISS returns -1 for not enough results
                results.append(self.documents[idx])
                
        return results

if __name__ == "__main__":
    # Initialize and build index
    db = VectorDB()
    db.build_index()

