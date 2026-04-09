
from database import engine
import models
# This will emit CREATE TABLE statements
print("Creating tables...")
models.Base.metadata.create_all(bind=engine)
print("✅ Tables created or already exist.")
