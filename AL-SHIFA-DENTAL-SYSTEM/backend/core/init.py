
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.orm import Session
import bcrypt

import models
import database
import config

def init_db():
    models.Base.metadata.create_all(bind=database.engine)

def create_default_admin(db: Session):
    admin_email = config.ADMIN_EMAIL
    new_password = config.ADMIN_PASSWORD
    
    user = db.query(models.User).filter(models.User.email == admin_email).first()
    if not user:
        pwd_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        db.add(models.User(
            email=admin_email, 
            full_name="System Admin", 
            role="admin", 
            is_email_verified=True, 
            password_hash=pwd_hash,
            phone_number="000-000-0000",
            address="Admin HQ"
        ))
        db.commit()
        print(f"✅ [Startup] Admin account created: {admin_email}")
    else:
        user.password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        db.commit()
        print(f"✅ [Startup] Admin password synced.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = database.SessionLocal()
    try:
        create_default_admin(db)
    finally:
        db.close()
    yield
