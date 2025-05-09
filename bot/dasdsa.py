import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor = conn.cursor()

    # 🧱 Створюємо колонку hunter_accept_message_id, якщо її ще немає
    cursor.execute("""
        ALTER TABLE orders
        ADD COLUMN IF NOT EXISTS hunter_accept_message_id BIGINT
    """)

    print("✅ Колонку 'hunter_accept_message_id' додано (або вже існує).")

    # 🧹 Видаляємо стару колонку hunter_notify_message_id, якщо існує
    cursor.execute("""
        ALTER TABLE orders
        DROP COLUMN IF EXISTS hunter_notify_message_id
    """)

    print("🗑️ Колонку 'hunter_notify_message_id' видалено (якщо була).")

    conn.commit()
    cursor.close()
    conn.close()

except Exception as e:
    print(f"❌ Помилка: {e}")
