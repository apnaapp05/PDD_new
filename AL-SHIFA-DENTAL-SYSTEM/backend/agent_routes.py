import models
from fastapi import APIRouter, Depends, Body, UploadFile, File
import shutil
import os
from sqlalchemy.orm import Session
from database import get_db
from models import User, Doctor
from agent.brain import ClinicAgent # Import the new brain
from dependencies import get_current_user

router = APIRouter(prefix="/doctor/agent", tags=["Agent"])
OBJECT_MEMORY = {} # Simple in-memory storage {user_id: [messages]}

@router.post("/chat")
def chat_with_agent(query: str = Body(..., embed=True), user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 1. Security Check
    if user.role != "doctor":
        return {"response": "Access Denied: Only doctors can use the Agent."}
    
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if not doctor:
        return {"response": "Doctor profile not found."}

    # 2. Retrieve History
    history = OBJECT_MEMORY.get(user.id, None)

    # 3. Instantiate the Agent with History
    agent = ClinicAgent(doctor.id, history=history)
    
    # 4. Process with fresh DB
    try:
        response_text = agent.process(query, db)
        
        # 5. Save History
        OBJECT_MEMORY[user.id] = agent.messages
        
        return {"response": response_text}

    except Exception as e:
        return {"response": f"❌ Agent Error: {str(e)}"}

@router.post("/upload")
def upload_knowledge(file: UploadFile = File(...), user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "doctor":
        return {"response": "Access Denied"}
        
    try:
        # 1. Save File
        kb_dir = os.path.join(os.path.dirname(__file__), "knowledge_base")
        if not os.path.exists(kb_dir):
            os.makedirs(kb_dir)
            
        file_path = os.path.join(kb_dir, file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Trigger RAG Loader
        # We need to instantiate loader. Since AgentTools does it, let's reuse a temp one or access via a service
        # For simplicity, we create a fresh RAGStore/Loader instance here
        from rag.store import RAGStore
        from rag.loader import DocumentLoader
        
        store = RAGStore()
        loader = DocumentLoader(store)
        
        success, msg = loader.process_file(file_path)
        
        if success:
            return {"status": "success", "message": msg}
        else:
            return {"status": "error", "message": msg}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}
