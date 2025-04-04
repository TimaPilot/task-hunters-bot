import json
import os
from datetime import datetime

import os
ORDERS_FILE = os.path.join(os.path.dirname(__file__), "orders.json")

def load_orders():
    if not os.path.exists(ORDERS_FILE):
        return []
    try:
        with open(ORDERS_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except json.JSONDecodeError:
        return []

def save_orders(orders):
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, indent=2, ensure_ascii=False)

def save_order_to_json(order_data):
    orders = load_orders()
    order_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    order_data["id"] = len(orders) + 1
    orders.append(order_data)
    save_orders(orders)
    return order_data["id"]

def update_order_status_by_id(order_id, new_status, hunter_name=None):
    orders = load_orders()
    for order in orders:
        if order["id"] == order_id:
            order["status"] = new_status
            if hunter_name:
                order["hunter"] = hunter_name
            if new_status == "Виконано":
                order["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            break
    save_orders(orders)

def get_order_by_id(order_id):
    orders = load_orders()
    for order in orders:
        if order.get("id") == order_id:
            return order
    return None

def get_orders_by_user(user_id):
    orders = load_orders()
    user_orders = [order for order in orders if order.get("customer_id") == user_id]
    return user_orders

