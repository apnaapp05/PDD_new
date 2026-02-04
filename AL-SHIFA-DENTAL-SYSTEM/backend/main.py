
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.init import lifespan
from api import public, auth, doctor, admin, organization
import agent_routes
import patient_agent_routes

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- APP INITIALIZATION ---
app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- ROUTERS ---
app.include_router(auth.router)
app.include_router(public.router)
app.include_router(doctor.router)
app.include_router(admin.router)
app.include_router(organization.router)

# --- AGENT ROUTERS ---
app.include_router(agent_routes.router)
app.include_router(patient_agent_routes.router)

# --- STATIC FILES ---
os.makedirs("media", exist_ok=True)
app.mount("/media", StaticFiles(directory="media"), name="media")

@app.get("/")
def root():
    return {"message": "Al-Shifa Dental System API is Running"}