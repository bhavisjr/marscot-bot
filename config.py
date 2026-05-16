import os
import json

CONFIG_FILE = "data/config.json"

DEFAULT_CONFIG = {
    "admin_ids": [],
    "admin_channel_id": None,
    "store_channel_id": None,
    "log_channel_id": None,
}

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in data:
                    data[k] = v
            return data
    return DEFAULT_CONFIG.copy()

def save_config(cfg: dict):
    os.makedirs("data", exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

config = load_config()

def is_admin(user_id: int) -> bool:
    from settings import OWNER_IDS
    return user_id in config.get("admin_ids", []) or user_id in OWNER_IDS

def add_admin(user_id: int):
    if user_id not in config["admin_ids"]:
        config["admin_ids"].append(user_id)
        save_config(config)

def remove_admin(user_id: int):
    if user_id in config["admin_ids"]:
        config["admin_ids"].remove(user_id)
        save_config(config)

def set_admin_channel(channel_id: int):
    config["admin_channel_id"] = channel_id
    save_config(config)

def set_store_channel(channel_id: int):
    config["store_channel_id"] = channel_id
    save_config(config)

def set_log_channel(channel_id: int):
    config["log_channel_id"] = channel_id
    save_config(config)
