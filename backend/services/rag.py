import os
import argparse
import glob
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import chromadb
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CHROMA_PERSIST_PATH = os.getenv("CHROMA_PERSIST_PATH", "./chroma_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# Module-level singleton so the model is loaded once
_rag_service_instance = None


def get_rag_service() -> "RAGService":
    """Return the shared RAGService singleton."""
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance

class KnowledgeBaseSeeder:
    def __init__(self):
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_PATH)
        self.collection = self.chroma_client.get_or_create_collection(name="knowledge_base")
        self.model = SentenceTransformer(EMBEDDING_MODEL)

    def chunk_text(self, text, chunk_size=300, overlap=50):
        # A simple word-based chunker to approximate token sizes
        words = text.split()
        if not words:
            return []
        chunks = []
        i = 0
        while i < len(words):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)
            i += chunk_size - overlap
            if i >= len(words):
                break
        return chunks

    def seed(self):
        print("Seeding knowledge base...")
        kb_path = os.path.join(os.path.dirname(__file__), "..", "knowledge_base", "*.md")
        files = glob.glob(kb_path)
        
        total_chunks = 0
        for file_path in files:
            filename = os.path.basename(file_path)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            chunks = self.chunk_text(content, chunk_size=300, overlap=50)
            
            if not chunks:
                continue
                
            embeddings = self.model.encode(chunks).tolist()
            
            ids = [f"{filename}_{i}" for i in range(len(chunks))]
            metadatas = [{"source_doc": filename} for _ in chunks]
            
            # Upsert avoids duplicating if run multiple times
            self.collection.upsert(
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            print(f"  {filename}    -> {len(chunks)} chunks")
            total_chunks += len(chunks)
            
        print(f"Done. {total_chunks} total chunks embedded and stored.")


class RAGService:
    """Service for querying the ChromaDB knowledge base."""

    def __init__(self) -> None:
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_PATH)
        self.collection = self.chroma_client.get_or_create_collection(name="knowledge_base")
        self.model = SentenceTransformer(EMBEDDING_MODEL)

    def search_knowledge_base(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Embed query and return top-k chunks with source doc and similarity score."""
        query_embedding = self.model.encode([query]).tolist()
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc, meta, dist in zip(documents, metadatas, distances):
            # ChromaDB returns L2 distance; convert to a 0-1 similarity score
            similarity = round(1 / (1 + dist), 4)
            chunks.append({
                "chunk_text": doc,
                "source_doc": meta.get("source_doc", "unknown"),
                "similarity_score": similarity,
            })

        return chunks


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", action="store_true", help="Seed the knowledge base")
    args = parser.parse_args()
    
    if args.seed:
        seeder = KnowledgeBaseSeeder()
        seeder.seed()
