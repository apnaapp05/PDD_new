
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Params from env or default
user = os.getenv("DB_USER", "postgres")
password = os.getenv("DB_PASSWORD", "ADLAB")
host = os.getenv("DB_HOST", "localhost")
port = os.getenv("DB_PORT", "5432")
db_name = os.getenv("DB_NAME", "dental_clinic")

try:
    # Connect to default 'postgres' db to create the new db
    conn = psycopg2.connect(dbname="postgres", user=user, password=password, host=host, port=port)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    # Check if database exists
    cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{db_name}'")
    exists = cursor.fetchone()
    
    if not exists:
        print(f"Creating database {db_name}...")
        cursor.execute(f"CREATE DATABASE {db_name}")
        print("Database created successfully!")
    else:
        print(f"Database {db_name} already exists.")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error creating database: {e}")
