
import os
import glob
from rag.store import RAGStore

class DocumentLoader:
    def __init__(self, store: RAGStore):
        self.store = store

    def load_directory(self, directory_path: str):
        """
        Loads all .txt and .pdf files from a directory into the RAG store.
        """
        if not os.path.exists(directory_path):
            return f"Directory {directory_path} does not exist."
            
        count = 0
        
        # Load Text Files
        for file_path in glob.glob(os.path.join(directory_path, "*.txt")):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Split content by paragraphs or headings generally helps
                # For simplicity, we split by double newlines to get chunks
                chunks = content.split("\n\n")
                for chunk in chunks:
                    if len(chunk.strip()) > 20: # Ignore empty/tiny chunks
                        self.store.add_document(chunk.strip(), os.path.basename(file_path))
                        count += 1

        # Load PDF Files
        try:
            import pypdf
            for file_path in glob.glob(os.path.join(directory_path, "*.pdf")):
                reader = pypdf.PdfReader(file_path)
                full_text = ""
                for page in reader.pages:
                    full_text += page.extract_text() + "\n\n"
                
                chunks = full_text.split("\n\n")
                for chunk in chunks:
                    if len(chunk.strip()) > 20:
                         self.store.add_document(chunk.strip(), os.path.basename(file_path))
                         count += 1
        except ImportError:
            print("pypdf not installed, skipping PDFs")
            
        return f"Loaded {count} chunks from {directory_path}."

    def process_file(self, file_path: str):
        """
        Process a single file and add to RAG store.
        """
        if not os.path.exists(file_path):
             return False, "File not found"
             
        filename = os.path.basename(file_path)
        count = 0
        
        try:
            if filename.endswith(".txt"):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    chunks = content.split("\n\n")
                    for chunk in chunks:
                        if len(chunk.strip()) > 20: 
                            self.store.add_document(chunk.strip(), filename)
                            count += 1
                            
            elif filename.endswith(".pdf"):
                try:
                    import pypdf
                    reader = pypdf.PdfReader(file_path)
                    full_text = ""
                    for page in reader.pages:
                        full_text += page.extract_text() + "\n\n"
                    
                    chunks = full_text.split("\n\n")
                    for chunk in chunks:
                        if len(chunk.strip()) > 20:
                             self.store.add_document(chunk.strip(), filename)
                             count += 1
                except ImportError:
                    return False, "pypdf not installed"
            
            return True, f"Successfully indexed {count} chunks from {filename}."
            
        except Exception as e:
            return False, str(e)
