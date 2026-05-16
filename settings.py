import os
import discord

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

OWNER_IDS = [
    int(x.strip())
    for x in os.environ.get("OWNER_IDS", "").split(",")
    if x.strip()
]

# ── Custom Emoji objects ──────────────────────────────────────────────────────
E_CART  = discord.PartialEmoji(name="carrinho",  id=1466466067743244431)
E_KEY   = discord.PartialEmoji(name="KeyBlank",  id=1333832294334595153)
E_OK    = discord.PartialEmoji(name="confirmar", id=1466466203341029396, animated=True)
E_WARN  = discord.PartialEmoji(name="alerta",    id=1442207137982841032)
E_UPI   = discord.PartialEmoji(name="upi",       id=1426247267492429824)
E_BIN   = discord.PartialEmoji(name="binance",   id=1426247080258699425)
E_GIFT  = discord.PartialEmoji(name="giftcard",  id=1466466165265141914)
E_ADMIN = discord.PartialEmoji(name="admin",     id=1466465960897806489)
E_ARROW = discord.PartialEmoji(name="arrow",     id=1446878964504072435, animated=True)

# ── Unicode fallbacks for embed text ──────────────────────────────────────────
ARROW = "➤"
CHECK = "✅"
CROSS = "❌"
WARN  = "⚠️"
KEY   = "🔑"
STORE = "🛒"
CLOCK = "⏱️"
MONEY = "💵"
ADMIN = "👑"

# ── Gift Card Providers ───────────────────────────────────────────────────────
GIFT_CARD_PROVIDERS = [
    "Binance Gift Card",
    "G2A",
    "Coinsbees",
]
