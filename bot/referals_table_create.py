import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
dsn = os.getenv("DATABASE_URL")

conn = psycopg2.connect(dsn)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS invites (
        code TEXT PRIMARY KEY,
        uses INTEGER NOT NULL,
        inviter_id BIGINT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

conn.commit()
cursor.close()
conn.close()
