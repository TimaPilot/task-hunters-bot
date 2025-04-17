import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
dsn = os.getenv("DATABASE_URL")

conn = psycopg2.connect(dsn)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS referrals (
    id SERIAL PRIMARY KEY,
    inviter_id BIGINT NOT NULL,
    invited_id BIGINT NOT NULL UNIQUE,
    confirmed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
cursor.close()
conn.close()
