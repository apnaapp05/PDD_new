
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
            success, msg = self.process_file(file_path)
            if success:
                # Extract count from message "Successfully indexed X chunks..."
                try:
                    count += int(msg.split(" ")[2])
                except:
                    pass

        # Load PDF Files
        try:
            import pypdf
            for file_path in glob.glob(os.path.join(directory_path, "*.pdf")):
                success, msg = self.process_file(file_path)
                if success:
                    try:
                        count += int(msg.split(" ")[2])
                    except:
                        pass
        except ImportError:
            print("pypdf not installed, skipping PDFs")
            
        return f"Loaded {count} chunks total from {directory_path}."

    def process_file(self, file_path: str):
        """
        Process a single file and add to RAG store using header-aware chunking.
        """
        if not os.path.exists(file_path):
             return False, "File not found"
             
        filename = os.path.basename(file_path)
        
        try:
            content = ""
            if filename.endswith(".txt"):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            elif filename.endswith(".pdf"):
                import pypdf
                reader = pypdf.PdfReader(file_path)
                for page in reader.pages:
                    content += page.extract_text() + "\n\n"
            else:
                return False, "Unsupported file format"

            chunks = self._chunk_by_headers(content)
            count = 0
            for chunk in chunks:
                if len(chunk.strip()) > 20: 
                    self.store.add_document(chunk.strip(), filename)
                    count += 1
            
            return True, f"Successfully indexed {count} chunks from {filename}."
            
        except Exception as e:
            return False, str(e)

    def _chunk_by_headers(self, text: str):
        """
        Splits text into chunks based on Markdown headers (# or ##).
        Each chunk includes its header.
        """
        lines = text.split("\n")
        chunks = []
        current_chunk = []
        
        main_header = ""
        sub_header = ""
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# "):
                # If we have a previous chunk, save it
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                main_header = stripped
                sub_header = ""
                current_chunk = [line]
            elif stripped.startswith("## "):
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                sub_header = stripped
                # New chunk starts with main header (if any) and then sub-header
                current_chunk = []
                if main_header:
                    current_chunk.append(main_header)
                current_chunk.append(line)
            else:
                current_chunk.append(line)
                
        if current_chunk:
            chunks.append("\n".join(current_chunk))
            
        return chunks
