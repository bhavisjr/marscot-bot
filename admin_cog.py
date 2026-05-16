import discord
from discord.ext import commands
from discord import app_commands

from config import is_admin, add_admin, remove_admin, set_admin_channel, set_store_channel, config
from products import get_all_products, find_product, update_product_prices, set_product_image, format_price
from keys import add_key, count_keys
from payments import set_binance, set_upi_qr_url, get_binance, get_upi_qr_url
from settings import ARROW, CHECK, CROSS, WARN, GIFT_CARD_PROVIDERS


def _ok(title, desc=""):
    return discord.Embed(title=f"✅ {title}", description=desc, color=0x57F287)

def _err(desc):
    return discord.Embed(title="❌ Error", description=desc, color=0xED4245)

def admin_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not is_admin(interaction.user.id):
            await interaction.response.send_message(
                embed=discord.Embed(title="❌ No Permission", description="You don't have admin access.", color=0xED4245),
                ephemeral=True,
            )
            return False
        return True
    return app_commands.check(predicate)


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── /panel ────────────────────────────────────────────────────────────────

    @app_commands.command(name="panel", description="Open the admin control panel")
    @admin_only()
    async def panel(self, interaction: discord.Interaction):
        from admin_panel import AdminPanelView
        from products import get_all_products
        from keys import count_keys

        prods      = get_all_products()
        total_keys = sum(
            count_keys(f"{p['id']}_{dur}")
            for p in prods
            for dur in ("1day","7day","31day")
        )
        out_of_stock = sum(
            1
            for p in prods
            for dur in ("1day","7day","31day")
            if p["prices"].get(dur, 0) > 0 and count_keys(f"{p['id']}_{dur}") == 0
        )

        store_ch = config.get("store_channel_id")
        admin_ch = config.get("admin_channel_id")
        admins   = config.get("admin_ids", [])

        store_ch_text = f"<#{store_ch}>" if store_ch else "`# owner`"
        admin_ch_text = f"<#{admin_ch}>" if admin_ch else "`# owner`"

        commands_text = (
            "`/list_products` · `/stock` · `/add_key`\n"
            "`/update_price` · `/set_upi` · `/set_binance`\n"
            "`/add_admin` · `/remove_admin`\n"
            "`/setup_admin_channel` · `/setup_store_channel`"
        )

        embed = discord.Embed(color=0x5865F2)
        embed.set_author(name=f"Logged in as {interaction.user.display_name}")
        embed.title = "Admin Panel"

        embed.add_field(name="Store Channel",  value=store_ch_text,               inline=True)
        embed.add_field(name="Admin Channel",  value=admin_ch_text,               inline=True)
        embed.add_field(name="Admins",         value=f"`{len(admins)} users`",     inline=True)
        embed.add_field(name="Products",       value=f"`{len(prods)}`",            inline=True)
        embed.add_field(name="Keys in Stock",  value=f"`{total_keys}`",            inline=True)
        embed.add_field(name="Out of Stock",   value=f"`{out_of_stock} plans`",    inline=True)
        embed.add_field(name="Slash Commands", value=commands_text,                inline=False)
        embed.set_footer(text="Use the buttons below for quick actions")

        await interaction.response.send_message(embed=embed, view=AdminPanelView(), ephemeral=True)

    # ── /list_products ────────────────────────────────────────────────────────

    @app_commands.command(name="list_products", description="List all products with their IDs")
    @admin_only()
    async def list_products(self, interaction: discord.Interaction):
        prods = get_all_products()
        if not prods:
            await interaction.response.send_message(embed=_err("No products found."), ephemeral=True)
            return
        embed = discord.Embed(title="📦 Product List", color=0x5865F2)
        for p in prods:
            prices = p["prices"]
            price_str = "  ·  ".join(
                f"{d}: `{format_price(prices.get(d,0))}`"
                for d in ("1day","7day","31day")
                if prices.get(d, 0) > 0
            )
            embed.add_field(
                name=f"{p.get('emoji','📦')} {p['name']}",
                value=f"ID: `{p['id']}`\n{price_str}",
                inline=True,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /stock ────────────────────────────────────────────────────────────────

    @app_commands.command(name="stock", description="View key stock levels for all products")
    @admin_only()
    async def stock(self, interaction: discord.Interaction):
        prods = get_all_products()
        dur_label = {"1day": "1 Day", "7day": "7 Days", "31day": "31 Days"}
        embed = discord.Embed(title="Key Stock", color=0x5865F2)
        for p in prods:
            lines = []
            for dur in ("1day","7day","31day"):
                if p["prices"].get(dur, 0) > 0:
                    n = count_keys(f"{p['id']}_{dur}")
                    status = str(n) if n > 0 else "Out of stock"
                    lines.append(f"{dur_label[dur]}: **{status}**")
            if lines:
                embed.add_field(
                    name=p["name"],
                    value="\n".join(lines),
                    inline=True,
                )
        if not embed.fields:
            embed.description = "No products with keys configured."
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /add_key ──────────────────────────────────────────────────────────────

    @app_commands.command(name="add_key", description="Add a license key to stock")
    @app_commands.describe(
        product_id="Product ID (use /list_products to find it)",
        duration="Duration: 1day, 7day, or 31day",
        key="License key to add",
    )
    @admin_only()
    async def add_key_cmd(self, interaction: discord.Interaction, product_id: str, duration: str, key: str):
        dur = duration.strip().lower()
        if dur not in ("1day","7day","31day"):
            await interaction.response.send_message(embed=_err("Duration must be `1day`, `7day`, or `31day`."), ephemeral=True)
            return
        product = find_product(product_id.strip())
        if not product:
            await interaction.response.send_message(embed=_err("Product not found. Use `/list_products` to see IDs."), ephemeral=True)
            return
        kid = f"{product['id']}_{dur}"
        add_key(kid, key.strip())
        await interaction.response.send_message(
            embed=_ok("Key Added", f"**Product:** {product['name']}\n**Duration:** {dur}\n**Stock now:** `{count_keys(kid)}` keys"),
            ephemeral=True,
        )

    # ── /update_price ─────────────────────────────────────────────────────────

    @app_commands.command(name="update_price", description="Update prices for a product")
    @app_commands.describe(
        product_id="Product ID",
        price_1day="1-day price (0 to disable)",
        price_7day="7-day price (0 to disable)",
        price_31day="31-day price (0 to disable)",
    )
    @admin_only()
    async def update_price(
        self,
        interaction: discord.Interaction,
        product_id: str,
        price_1day: float = None,
        price_7day: float = None,
        price_31day: float = None,
    ):
        from products import update_product_prices
        product = find_product(product_id.strip())
        if not product:
            await interaction.response.send_message(embed=_err("Product not found."), ephemeral=True)
            return
        update_product_prices(product["id"], price_1day, price_7day, price_31day)
        await interaction.response.send_message(
            embed=_ok(
                "Prices Updated",
                f"**{product['name']}**\n"
                f"1d: `{format_price(price_1day) if price_1day is not None else '—'}` · "
                f"7d: `{format_price(price_7day) if price_7day is not None else '—'}` · "
                f"31d: `{format_price(price_31day) if price_31day is not None else '—'}`"
            ),
            ephemeral=True,
        )

    # ── /set_product_image ────────────────────────────────────────────────────

    @app_commands.command(name="set_product_image", description="Set the image URL for a product")
    @app_commands.describe(product_id="Product ID", image_url="Direct image URL (imgur, etc.)")
    @admin_only()
    async def set_image(self, interaction: discord.Interaction, product_id: str, image_url: str):
        product = find_product(product_id.strip())
        if not product:
            await interaction.response.send_message(embed=_err("Product not found."), ephemeral=True)
            return
        set_product_image(product["id"], image_url.strip())
        embed = _ok("Image Updated", f"**{product['name']}** image updated.")
        embed.set_image(url=image_url.strip())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /set_upi ──────────────────────────────────────────────────────────────

    @app_commands.command(name="set_upi", description="Set your UPI QR code image URL")
    @app_commands.describe(image_url="Direct URL to your UPI QR code image")
    @admin_only()
    async def set_upi(self, interaction: discord.Interaction, image_url: str):
        set_upi_qr_url(image_url.strip())
        embed = _ok("UPI QR Updated", "New UPI QR code saved.")
        embed.set_image(url=image_url.strip())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /set_binance ──────────────────────────────────────────────────────────

    @app_commands.command(name="set_binance", description="Set your Binance Pay ID")
    @app_commands.describe(pay_id="Your Binance Pay ID")
    @admin_only()
    async def set_binance_cmd(self, interaction: discord.Interaction, pay_id: str):
        set_binance(pay_id.strip())
        await interaction.response.send_message(embed=_ok("Binance Pay ID Updated", f"ID saved."), ephemeral=True)

    # ── /add_admin ────────────────────────────────────────────────────────────

    @app_commands.command(name="add_admin", description="Grant admin access to a user")
    @app_commands.describe(user="The user to grant admin access")
    @admin_only()
    async def add_admin_cmd(self, interaction: discord.Interaction, user: discord.Member):
        add_admin(user.id)
        await interaction.response.send_message(
            embed=_ok("Admin Added", f"{user.mention} now has admin access."),
            ephemeral=True,
        )

    # ── /remove_admin ─────────────────────────────────────────────────────────

    @app_commands.command(name="remove_admin", description="Revoke admin access from a user")
    @app_commands.describe(user="The user to remove admin access from")
    @admin_only()
    async def remove_admin_cmd(self, interaction: discord.Interaction, user: discord.Member):
        remove_admin(user.id)
        await interaction.response.send_message(
            embed=_ok("Admin Removed", f"{user.mention} no longer has admin access."),
            ephemeral=True,
        )

    # ── /setup_admin_channel ──────────────────────────────────────────────────

    @app_commands.command(name="setup_admin_channel", description="Set the channel where new orders appear for review")
    @app_commands.describe(channel="The channel to receive order notifications")
    @admin_only()
    async def setup_admin_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        set_admin_channel(channel.id)
        await interaction.response.send_message(
            embed=_ok("Admin Channel Set", f"New orders will be sent to {channel.mention}."),
            ephemeral=True,
        )

    # ── /setup_store_channel ──────────────────────────────────────────────────

    @app_commands.command(name="setup_store_channel", description="Post the store panel to a channel")
    @app_commands.describe(channel="The channel to post the store in")
    @admin_only()
    async def setup_store_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        from views import StoreView
        set_store_channel(channel.id)
        embed = discord.Embed(
            title="🛒 Welcome to the Store",
            description=(
                f"{ARROW} Browse products using the dropdown below.\n"
                f"{ARROW} Select a product → choose duration → choose payment.\n"
                f"{ARROW} Submit proof → admin reviews → key delivered via DM.\n\n"
                f"*Delivery is automatic after admin approval.*"
            ),
            color=0x5865F2,
        )
        embed.set_footer(text="Select a product from the dropdown to get started.")
        await channel.send(embed=embed, view=StoreView())
        await interaction.response.send_message(
            embed=_ok("Store Posted", f"Store panel sent to {channel.mention}."),
            ephemeral=True,
        )

    # ── /gift_card_sites ──────────────────────────────────────────────────────

    @app_commands.command(name="gift_card_sites", description="View accepted gift card providers")
    @admin_only()
    async def gift_card_sites(self, interaction: discord.Interaction):
        providers_list = "\n".join(f"• {p}" for p in GIFT_CARD_PROVIDERS)
        embed = discord.Embed(
            title="🎁 Accepted Gift Card Providers",
            description=(
                f"These providers are shown to customers during checkout:\n\n"
                f"{providers_list}"
            ),
            color=0x5865F2,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
