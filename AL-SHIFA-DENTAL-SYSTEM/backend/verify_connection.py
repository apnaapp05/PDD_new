
from database import engine
from sqlalchemy import text

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("✅ CONNECTION SUCCESSFUL: App connected to PostgreSQL!")
except Exception as e:
    print(f"❌ CONNECTION FAILED: {e}")
