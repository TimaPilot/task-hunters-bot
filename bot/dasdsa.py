import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def migrate_orders_table():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cursor = conn.cursor()

        cursor.execute("""
            DO $$
            BEGIN
                -- 🔁 Додаємо нову колонку, якщо ще не існує
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='orders' AND column_name='user_accept_message_id'
                ) THEN
                    ALTER TABLE orders ADD COLUMN user_accept_message_id BIGINT;
                END IF;

                -- ❌ Видаляємо стару колонку
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='orders' AND column_name='hunter_accept_message_id'
                ) THEN
                    ALTER TABLE orders DROP COLUMN hunter_accept_message_id;
                END IF;
            END
            $$;
        """)

        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Колонка замінена: hunter_accept_message_id → user_accept_message_id")

    except Exception as e:
        print("❌ Помилка при оновленні структури таблиці:", e)

if __name__ == "__main__":
    migrate_orders_table()
