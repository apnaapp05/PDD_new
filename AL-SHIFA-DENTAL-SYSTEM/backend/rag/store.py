
import chromadb
from chromadb.config import Settings
import uuid
import os

class RAGStore:
    def __init__(self, persist_directory="./data/chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Create or get the collection
        self.collection = self.client.get_or_create_collection(
            name="clinical_knowledge",
            metadata={"hnsw:space": "cosine"} # Cosine similarity for text matching
        )

    def add_document(self, text: str, source: str):
        """
        Add a document chunk to the vector store.
        """
        self.collection.add(
            documents=[text],
            metadatas=[{"source": source}],
            ids=[str(uuid.uuid4())]
        )

    def search(self, query: str, n_results: int = 3):
        """
        Search for relevant documents.
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results

    def reset(self):
        """
        Clear the database.
        """
        try:
            self.client.delete_collection("clinical_knowledge")
            self.collection = self.client.get_or_create_collection(name="clinical_knowledge")
            return True
        except Exception as e:
            print(f"Error resetting RAG store: {e}")
            return False
            
    def count(self):
        return self.collection.count()
