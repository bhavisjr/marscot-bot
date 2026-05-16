import os
import json
import uuid
from typing import Optional

PRODUCTS_FILE = "data/products.json"

SEED_PRODUCTS = [
    # Free Fire iOS
    {"name": "Fluorite (FF iOS)",          "description": "Free Fire iOS — Fluorite hack. Lightning-fast aimbot, full ESP, and anti-ban protection built-in.", "emoji": "⚡", "prices": {"1day": 5.00,  "7day": 15.00, "31day": 23.00}},
    {"name": "Migul PRO (FF iOS)",         "description": "Free Fire iOS — Migul PRO hack. Premium features with aimbot and ESP.",                             "emoji": "⚡", "prices": {"1day": 3.00,  "7day": 10.00, "31day": 20.00}},
    {"name": "FFH4X (FF iOS)",             "description": "Free Fire iOS — The most popular FFH4X hack. Lightning-fast aimbot, full ESP, and anti-ban protection built-in.", "emoji": "⚡", "prices": {"1day": 5.00, "7day": 15.00, "31day": 25.00}},
    {"name": "iMAZING (FF iOS)",           "description": "Free Fire iOS — iMAZING hack. Advanced features for iOS players.",                                  "emoji": "⚡", "prices": {"1day": 0,     "7day": 0,     "31day": 9.00}},
    # Free Fire Android
    {"name": "HG-Cheats Root (FF And)",    "description": "Free Fire Android — HG-Cheats (Root). Requires rooted device.",                                    "emoji": "🔥", "prices": {"1day": 4.00,  "7day": 5.50,  "31day": 13.00}},
    {"name": "HG-Cheats NoRoot (FF And)",  "description": "Free Fire Android — HG-Cheats (Non-Root). No root required.",                                      "emoji": "🔥", "prices": {"1day": 4.00,  "7day": 5.50,  "31day": 13.00}},
    {"name": "PatoTeam NoRoot (FF And)",   "description": "Free Fire Android — PatoTeam (Non-Root). No root required.",                                       "emoji": "🦆", "prices": {"1day": 2.50,  "7day": 6.00,  "31day": 12.50}},
    {"name": "Drip-Client Root (FF And)",  "description": "Free Fire Android — Drip-Client (Root). Requires rooted device.",                                  "emoji": "💧", "prices": {"1day": 2.00,  "7day": 4.50,  "31day": 12.00}},
    {"name": "Drip-Client NoRoot (FF And)","description": "Free Fire Android — Drip-Client (Non-Root). No root required.",                                    "emoji": "💧", "prices": {"1day": 2.00,  "7day": 4.50,  "31day": 12.00}},
    # 8 Ball Pool iOS
    {"name": "Wizard iOS (8BP)",           "description": "8 Ball Pool iOS — Wizard hack. Auto-aim and guideline extension.",                                  "emoji": "🎱", "prices": {"1day": 2.00,  "7day": 8.00,  "31day": 18.00}},
    {"name": "Star Wolf GBD Pixel (8BP)",  "description": "8 Ball Pool iOS — Star Wolf GBD Pixel hack.",                                                      "emoji": "🎱", "prices": {"1day": 2.00,  "7day": 5.50,  "31day": 12.00}},
    {"name": "iOS-Viet (8BP)",             "description": "8 Ball Pool iOS — iOS-Viet hack. Extended guideline and anti-ban.",                                 "emoji": "🎱", "prices": {"1day": 4.00,  "7day": 10.00, "31day": 20.00}},
    {"name": "Potassium iOS (8BP)",        "description": "8 Ball Pool iOS — Potassium hack. Full features with anti-ban.",                                    "emoji": "🎱", "prices": {"1day": 4.00,  "7day": 8.00,  "31day": 14.00}},
    # Certificate iOS
    {"name": "iPhone Certificate",         "description": "iOS Certificate for iPhone. 300-day validity. Required to run hacks on iOS devices.",              "emoji": "📜", "prices": {"1day": 0,     "7day": 0,     "31day": 10.00}},
    {"name": "iPad Certificate",           "description": "iOS Certificate for iPad. 300-day validity. Required to run hacks on iOS devices.",                "emoji": "📜", "prices": {"1day": 0,     "7day": 0,     "31day": 10.00}},
    # Mobile Legends iOS
    {"name": "Fluorite MLBB (ML iOS)",     "description": "Mobile Legends iOS — Fluorite MLBB hack. Aimbot, map hack and ESP.",                               "emoji": "⚔️", "prices": {"1day": 5.00,  "7day": 15.00, "31day": 23.00}},
    # PUBG Mobile iOS
    {"name": "Dolphin iOS (PUBG)",         "description": "PUBG Mobile iOS — Dolphin hack. Aimbot and ESP built-in.",                                         "emoji": "🔫", "prices": {"1day": 3.50,  "7day": 8.00,  "31day": 14.00}},
    {"name": "Star Win iOS (PUBG)",        "description": "PUBG Mobile iOS — Star Win hack. Full features with anti-ban.",                                    "emoji": "🔫", "prices": {"1day": 3.50,  "7day": 8.00,  "31day": 15.00}},
    {"name": "GroX iOS (PUBG)",            "description": "PUBG Mobile iOS — GroX hack. Premium aimbot and wall ESP.",                                        "emoji": "🔫", "prices": {"1day": 6.00,  "7day": 12.00, "31day": 18.00}},
    # PUBG Mobile Android
    {"name": "Zolo NoRoot (PUBG And)",     "description": "PUBG Mobile Android — Zolo (Non-Root). No root required.",                                        "emoji": "🔫", "prices": {"1day": 2.00,  "7day": 6.00,  "31day": 15.00}},
    {"name": "aXel PM (PUBG And)",         "description": "PUBG Mobile Android — aXel PM hack. Premium features.",                                           "emoji": "🔫", "prices": {"1day": 6.00,  "7day": 12.00, "31day": 20.00}},
    {"name": "Fluxo SRS (PUBG And)",       "description": "PUBG Mobile Android — Fluxo SRS hack. Advanced ESP and aimbot.",                                   "emoji": "🔫", "prices": {"1day": 6.00,  "7day": 12.00, "31day": 20.00}},
]

def _seed():
    os.makedirs("data", exist_ok=True)
    seeded = []
    for p in SEED_PRODUCTS:
        seeded.append({
            "id":          str(uuid.uuid4())[:8],
            "name":        p["name"],
            "description": p["description"],
            "image_url":   "",
            "emoji":       p.get("emoji", ""),
            "prices":      p["prices"],
        })
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(seeded, f, indent=2, ensure_ascii=False)
    return seeded

def load_products() -> list:
    if os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data:
            return data
    return _seed()

def save_products(prods: list):
    os.makedirs("data", exist_ok=True)
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(prods, f, indent=2, ensure_ascii=False)

products: list = load_products()

def get_all_products() -> list:
    return products

def find_product(product_id: str) -> Optional[dict]:
    return next((p for p in products if p["id"] == product_id), None)

def add_product(name: str, description: str, image_url: str, emoji: str = "",
                price_1d: float = 0, price_7d: float = 0, price_31d: float = 0) -> dict:
    product = {
        "id":          str(uuid.uuid4())[:8],
        "name":        name,
        "description": description,
        "image_url":   image_url,
        "emoji":       emoji,
        "prices":      {"1day": price_1d, "7day": price_7d, "31day": price_31d},
    }
    products.append(product)
    save_products(products)
    return product

def update_product_prices(product_id: str, price_1d: float = None,
                          price_7d: float = None, price_31d: float = None) -> bool:
    p = find_product(product_id)
    if not p:
        return False
    if price_1d is not None:
        p["prices"]["1day"] = price_1d
    if price_7d is not None:
        p["prices"]["7day"] = price_7d
    if price_31d is not None:
        p["prices"]["31day"] = price_31d
    save_products(products)
    return True

def set_product_image(product_id: str, image_url: str) -> bool:
    p = find_product(product_id)
    if not p:
        return False
    p["image_url"] = image_url
    save_products(products)
    return True

def remove_product(product_id: str) -> bool:
    global products
    original = len(products)
    products = [p for p in products if p["id"] != product_id]
    save_products(products)
    return len(products) < original

def format_price(amount: float) -> str:
    return f"${amount:.2f}" if amount > 0 else "—"
