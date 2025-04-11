import asyncio
from db_logger import delete_orders_by_customer

async def main():
    await delete_orders_by_customer(386329540353458186)

asyncio.run(main())
