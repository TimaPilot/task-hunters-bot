import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def migrate_notify_column():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cursor = conn.cursor()

        cursor.execute("""
            DO $$
            BEGIN
                -- 🗑 Видаляємо hunter_notify_message_id, якщо існує
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='orders' AND column_name='hunter_notify_message_id'
                ) THEN
                    ALTER TABLE orders DROP COLUMN hunter_notify_message_id;
                END IF;

                -- 🆕 Додаємо hunter_notify_message_id, якщо немає
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='orders' AND column_name='hunter_notify_message_id'
                ) THEN
                    ALTER TABLE orders ADD COLUMN hunter_notify_message_id BIGINT;
                END IF;
            END
            $$;
        """)

        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Колонка оновлена: hunter_notify_message_id додана, стара видалена (якщо була).")

    except Exception as e:
        print("❌ Помилка при оновленні структури таблиці:", e)

if __name__ == "__main__":
    migrate_notify_column()
