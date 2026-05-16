import os
import json
import uuid
from typing import Optional

ORDERS_FILE = "data/orders.json"

def load_orders() -> dict:
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_orders(data: dict):
    os.makedirs("data", exist_ok=True)
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

pending_orders: dict = load_orders()

def create_order(user_id: int, username: str, product: dict,
                 duration: str, price: float, payment_method: str) -> str:
    order_id = str(uuid.uuid4())[:8].upper()
    pending_orders[order_id] = {
        "order_id":        order_id,
        "user_id":         user_id,
        "username":        username,
        "product_id":      product["id"],
        "product_name":    product["name"],
        "duration":        duration,
        "price":           price,
        "payment_method":  payment_method,
        "status":          "pending",
        "proof":           None,
        "gift_code":       None,
        "gift_card_site":  None,
    }
    save_orders(pending_orders)
    return order_id

def get_order(order_id: str) -> Optional[dict]:
    return pending_orders.get(order_id)

def set_order_proof(order_id: str, proof_url: str):
    order = pending_orders.get(order_id)
    if order:
        order["proof"] = proof_url
        save_orders(pending_orders)

def set_order_gift_code(order_id: str, code: str, site: str = None):
    order = pending_orders.get(order_id)
    if order:
        order["gift_code"] = code
        if site:
            order["gift_card_site"] = site
        save_orders(pending_orders)

def set_order_status(order_id: str, status: str) -> Optional[dict]:
    order = pending_orders.get(order_id)
    if order:
        order["status"] = status
        save_orders(pending_orders)
    return order

def approve_order(order_id: str) -> Optional[dict]:
    return set_order_status(order_id, "approved")

def reject_order(order_id: str) -> Optional[dict]:
    return set_order_status(order_id, "rejected")

def delete_order(order_id: str):
    pending_orders.pop(order_id, None)
    save_orders(pending_orders)

def get_pending_orders() -> list:
    return [o for o in pending_orders.values() if o["status"] == "pending"]
