import asyncpg
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Підключення до бази
async def get_connection():
    return await asyncpg.connect(DATABASE_URL)

# Ініціалізація таблиці (один раз при запуску)
async def init_db():
    conn = await get_connection()
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT NOW(),
            customer TEXT,
            customer_id BIGINT,
            type TEXT,
            details TEXT,
            hunter TEXT,
            status TEXT,
            finished_at TIMESTAMP
        );
    """)
    await conn.close()

# Зберегти замовлення
async def save_order_to_db(order_data):
    conn = await get_connection()
    await conn.execute("""
        INSERT INTO orders (customer, customer_id, type, details, hunter, status)
        VALUES ($1, $2, $3, $4, $5, $6);
    """, order_data["customer"], order_data["customer_id"], order_data["type"],
         order_data["details"], order_data["hunter"], order_data["status"])
    await conn.close()

# Отримати замовлення по ID користувача
async def get_orders_by_user(user_id):
    conn = await get_connection()
    rows = await conn.fetch("""
        SELECT * FROM orders WHERE customer_id = $1 ORDER BY id DESC LIMIT 10;
    """, user_id)
    await conn.close()
    return [dict(row) for row in rows]

# Оновити статус замовлення
async def update_order_status_by_id(order_id, new_status, hunter_name=None):
    conn = await get_connection()
    if new_status == "Виконано":
        await conn.execute("""
            UPDATE orders SET status=$1, hunter=$2, finished_at=NOW() WHERE id=$3;
        """, new_status, hunter_name, order_id)
    else:
        await conn.execute("""
            UPDATE orders SET status=$1, hunter=$2 WHERE id=$3;
        """, new_status, hunter_name, order_id)
    await conn.close()

# Отримати замовлення по ID
async def get_order_by_id(order_id):
    conn = await get_connection()
    row = await conn.fetchrow("SELECT * FROM orders WHERE id=$1;", order_id)
    await conn.close()
    return dict(row) if row else None
