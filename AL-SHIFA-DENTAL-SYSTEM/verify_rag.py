
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from backend.agent.tools import AgentTools
from backend.rag.store import RAGStore

# Mock DB Session
class MockSession:
    def __init__(self):
        pass
    def query(self, *args):
        return self
    def all(self):
        return []

print("--- Testing RAG Integration ---")
try:
    # 1. Initialize Tools (which triggers RAG loading)
    print("Initializing Agent Tools...")
    tools = AgentTools(None, 1) # None db, Doc ID 1
    
    # 2. Check if documents loaded
    count = tools.rag_store.count()
    print(f"RAG Store contains {count} document chunks.")
    
    if count == 0:
        print("❌ Error: Knowledge base did not load.")
    else:
        print("✅ Knowledge base loaded successfully.")

    # 3. Test Query
    query = "What is the post op care for root canal?"
    print(f"\nQuerying: '{query}'")
    result = tools.consult_knowledge_base(query)
    
    print("\n--- Result ---")
    print(result)
    
    if "numbness" in result.lower() or "chewing" in result.lower():
        print("\n✅ Verification SUCCESS: Retrieved correct protocol.")
    else:
        print("\n❌ Verification FAILED: Did not retrieve relevant info.")

except Exception as e:
    print(f"\n❌ CRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()
