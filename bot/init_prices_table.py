import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime

# Завантаження змінних з .env
load_dotenv()

# Підключення до Railway PostgreSQL
conn = psycopg2.connect(
    dbname=os.getenv("PGDATABASE"),
    user=os.getenv("PGUSER"),
    password=os.getenv("PGPASSWORD"),
    host=os.getenv("PGHOST"),
    port=os.getenv("PGPORT")
)

cursor = conn.cursor()

# === 1. Створюємо таблицю для історії цін ===
cursor.execute("""
CREATE TABLE IF NOT EXISTS resource_prices (
    id SERIAL PRIMARY KEY,
    resource TEXT NOT NULL,
    price INTEGER NOT NULL,
    effective_from TIMESTAMP NOT NULL
)
""")

# === 2. Додаємо колонку знижки в таблицю orders, якщо ще нема ===
cursor.execute("""
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'orders' AND column_name = 'discount_percent'
    ) THEN
        ALTER TABLE orders ADD COLUMN discount_percent INTEGER;
    END IF;
END$$;
""")

# === 3. Додаємо тестові ціни ===
cursor.execute("""
INSERT INTO resource_prices (resource, price, effective_from) VALUES
('🪨 Камінь', 90000, '2025-04-01 00:00:00'),
('🪨 Камінь', 100000, '2025-04-04 00:00:00'),
('🐟 Риба', 20000, '2025-04-01 00:00:00'),
('🥫 Миючі засоби', 30000, '2025-04-01 00:00:00')
ON CONFLICT DO NOTHING
""")

conn.commit()
cursor.close()
conn.close()

print("✅ Таблиця `resource_prices` створена, колонка `discount_percent` додана, ціни залито.")
