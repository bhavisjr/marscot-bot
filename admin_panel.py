import discord
from discord.ui import View, Button, Modal, TextInput

from config import is_admin, add_admin, remove_admin, set_admin_channel, set_store_channel, config
from products import get_all_products, find_product, add_product, remove_product, update_product_prices, set_product_image
from keys import add_key, count_keys, get_keys, keys_db, save_keys
from payments import set_binance, set_upi_qr_url, get_binance, get_upi_qr_url
from settings import E_ADMIN, E_KEY, E_OK, E_WARN, E_GIFT, E_BIN, E_UPI, E_ARROW, ARROW, CHECK, CROSS, WARN, GIFT_CARD_PROVIDERS


def _guard(i):
    return is_admin(i.user.id)

def _ok(title, desc=""):
    return discord.Embed(title=f"✅ {title}", description=desc, color=0x57F287)

def _err(desc):
    return discord.Embed(title="❌ Error", description=desc, color=0xED4245)


# ─── Modals ────────────────────────────────────────────────────────────────────

class AddProductModal(Modal, title="Add Product"):
    name_emoji  = TextInput(label="Name  |  Emoji",              placeholder='e.g.  FFH4X (FF iOS)  |  ⚡',                     required=True,  max_length=100)
    description = TextInput(label="Description",                 placeholder='Short product description...',                     style=discord.TextStyle.paragraph, required=True, max_length=300)
    image_url   = TextInput(label="Image URL (optional)",        placeholder='https://i.imgur.com/example.png',                  required=False)
    prices      = TextInput(label="Prices: 1day / 7day / 31day", placeholder='e.g.  5.00 / 15.00 / 25.00   (0 = disabled)',     required=True)
    first_key   = TextInput(label="Add a Key (optional)",        placeholder='Paste a license key to add to 31day stock',        required=False, style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        parts = self.name_emoji.value.split("|")
        name  = parts[0].strip()
        emoji = parts[1].strip() if len(parts) > 1 else "📦"

        try:
            raw = [p.strip() for p in self.prices.value.replace(",", "/").split("/")]
            p1  = float(raw[0]) if len(raw) > 0 and raw[0] else 0
            p7  = float(raw[1]) if len(raw) > 1 and raw[1] else 0
            p31 = float(raw[2]) if len(raw) > 2 and raw[2] else 0
        except ValueError:
            await interaction.response.send_message(embed=_err("Invalid prices. Format: `5.00 / 15.00 / 25.00`"), ephemeral=True)
            return

        product = add_product(
            name=name,
            description=self.description.value.strip(),
            image_url=self.image_url.value.strip() if self.image_url.value else "",
            emoji=emoji,
            price_1d=p1, price_7d=p7, price_31d=p31,
        )

        key_added = ""
        if self.first_key.value.strip():
            kid = f"{product['id']}_31day"
            add_key(kid, self.first_key.value.strip())
            key_added = f"\n🔑 1 key added to **31day** stock."

        await interaction.response.send_message(
            embed=_ok(
                "Product Added",
                f"**Name:** {emoji} {name}\n"
                f"**ID:** `{product['id']}`\n"
                f"**Prices:** 1d `${p1:.2f}` · 7d `${p7:.2f}` · 31d `${p31:.2f}`"
                f"{key_added}\n\n"
                f"Use **Add Keys** to add more keys to any duration."
            ),
            ephemeral=True,
        )


class AddKeyModal(Modal, title="Add License Key"):
    product_id = TextInput(label="Product ID",  placeholder="Use 'View Stock' to see IDs", required=True)
    duration   = TextInput(label="Duration",    placeholder="1day  /  7day  /  31day",     required=True, max_length=5)
    key        = TextInput(label="License Key", placeholder="Paste the key here...",       style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        dur = self.duration.value.strip().lower()
        if dur not in ("1day","7day","31day"):
            await interaction.response.send_message(embed=_err("Duration must be `1day`, `7day`, or `31day`."), ephemeral=True)
            return
        product = find_product(self.product_id.value.strip())
        if not product:
            await interaction.response.send_message(embed=_err("Product not found. Click **View Stock** to see IDs."), ephemeral=True)
            return
        kid = f"{product['id']}_{dur}"
        add_key(kid, self.key.value.strip())
        await interaction.response.send_message(
            embed=_ok("Key Added", f"**Product:** {product['name']}\n**Duration:** {dur}\n**Stock now:** `{count_keys(kid)}` keys"),
            ephemeral=True,
        )


class BulkAddKeysModal(Modal, title="Bulk Add Keys"):
    product_id = TextInput(label="Product ID",          placeholder="Use 'View Stock' to see IDs",          required=True)
    duration   = TextInput(label="Duration",             placeholder="1day  /  7day  /  31day",              required=True, max_length=5)
    keys       = TextInput(label="Keys (one per line)",  placeholder="KEY-AAAA-1111\nKEY-BBBB-2222\n...",   style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        dur = self.duration.value.strip().lower()
        if dur not in ("1day","7day","31day"):
            await interaction.response.send_message(embed=_err("Duration must be `1day`, `7day`, or `31day`."), ephemeral=True)
            return
        product = find_product(self.product_id.value.strip())
        if not product:
            await interaction.response.send_message(embed=_err("Product not found."), ephemeral=True)
            return
        key_list = [k.strip() for k in self.keys.value.splitlines() if k.strip()]
        if not key_list:
            await interaction.response.send_message(embed=_err("No keys found. Enter one key per line."), ephemeral=True)
            return
        kid = f"{product['id']}_{dur}"
        for k in key_list:
            add_key(kid, k)
        await interaction.response.send_message(
            embed=_ok(
                f"{len(key_list)} Keys Added",
                f"**Product:** {product['name']}\n**Duration:** {dur}\n**Total stock now:** `{count_keys(kid)}` keys"
            ),
            ephemeral=True,
        )


class ClearKeysModal(Modal, title="Clear Keys"):
    product_id = TextInput(label="Product ID",              placeholder="Use 'View Stock' to see IDs",       required=True)
    duration   = TextInput(label="Duration (or 'all')",     placeholder="1day / 7day / 31day / all",         required=True, max_length=5)

    async def on_submit(self, interaction: discord.Interaction):
        product = find_product(self.product_id.value.strip())
        if not product:
            await interaction.response.send_message(embed=_err("Product not found."), ephemeral=True)
            return
        dur     = self.duration.value.strip().lower()
        cleared = 0
        if dur == "all":
            for d in ("1day","7day","31day"):
                kid = f"{product['id']}_{d}"
                cleared += len(keys_db.get(kid, []))
                keys_db[kid] = []
            save_keys(keys_db)
        elif dur in ("1day","7day","31day"):
            kid     = f"{product['id']}_{dur}"
            cleared = len(keys_db.get(kid, []))
            keys_db[kid] = []
            save_keys(keys_db)
        else:
            await interaction.response.send_message(embed=_err("Use `1day`, `7day`, `31day`, or `all`."), ephemeral=True)
            return
        await interaction.response.send_message(
            embed=_ok("Keys Cleared", f"**{product['name']}** ({dur}) — `{cleared}` keys removed."),
            ephemeral=True,
        )


class RemoveProductModal(Modal, title="Remove Product"):
    product_id = TextInput(label="Product ID", placeholder="Use 'View Stock' to see IDs", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        product = find_product(self.product_id.value.strip())
        if not product:
            await interaction.response.send_message(embed=_err("Product not found."), ephemeral=True)
            return
        remove_product(product["id"])
        await interaction.response.send_message(embed=_ok("Product Removed", f"**{product['name']}** deleted."), ephemeral=True)


class UpdatePriceModal(Modal, title="Update Prices"):
    product_id = TextInput(label="Product ID",                      placeholder="Use 'View Stock' to see IDs",    required=True)
    prices     = TextInput(label="New Prices: 1day / 7day / 31day", placeholder="e.g.  5.00 / 15.00 / 25.00",   required=True)

    async def on_submit(self, interaction: discord.Interaction):
        product = find_product(self.product_id.value.strip())
        if not product:
            await interaction.response.send_message(embed=_err("Product not found."), ephemeral=True)
            return
        try:
            raw = [p.strip() for p in self.prices.value.replace(",","/").split("/")]
            p1  = float(raw[0]) if len(raw)>0 and raw[0] else None
            p7  = float(raw[1]) if len(raw)>1 and raw[1] else None
            p31 = float(raw[2]) if len(raw)>2 and raw[2] else None
        except ValueError:
            await interaction.response.send_message(embed=_err("Invalid prices. Format: `5.00 / 15.00 / 25.00`"), ephemeral=True)
            return
        update_product_prices(product["id"], p1, p7, p31)
        await interaction.response.send_message(
            embed=_ok("Prices Updated", f"**{product['name']}**\n1d: `${p1 or '—'}` · 7d: `${p7 or '—'}` · 31d: `${p31 or '—'}`"),
            ephemeral=True,
        )


class SetUPIModal(Modal, title="Set UPI QR Code"):
    url = TextInput(label="UPI QR Image URL", placeholder="https://i.imgur.com/your-qr.png", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        set_upi_qr_url(self.url.value.strip())
        await interaction.response.send_message(embed=_ok("UPI QR Updated", f"New QR URL saved."), ephemeral=True)


class SetBinanceModal(Modal, title="Set Binance Pay ID"):
    binance_id = TextInput(label="Binance Pay ID", placeholder="Your Binance Pay ID...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        set_binance(self.binance_id.value.strip())
        await interaction.response.send_message(embed=_ok("Binance Pay ID Updated"), ephemeral=True)


class AddAdminModal(Modal, title="Add Admin"):
    user_id = TextInput(label="User ID", placeholder="Right-click user → Copy ID (Dev Mode on)", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            uid = int(self.user_id.value.strip())
        except ValueError:
            await interaction.response.send_message(embed=_err("Invalid User ID."), ephemeral=True)
            return
        add_admin(uid)
        await interaction.response.send_message(embed=_ok("Admin Added", f"User `{uid}` now has admin access."), ephemeral=True)


class RemoveAdminModal(Modal, title="Remove Admin"):
    user_id = TextInput(label="User ID", placeholder="Right-click user → Copy ID (Dev Mode on)", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            uid = int(self.user_id.value.strip())
        except ValueError:
            await interaction.response.send_message(embed=_err("Invalid User ID."), ephemeral=True)
            return
        remove_admin(uid)
        await interaction.response.send_message(embed=_ok("Admin Removed", f"User `{uid}` removed."), ephemeral=True)


class SetupChannelsModal(Modal, title="Setup Channels"):
    admin_ch = TextInput(label="Admin Channel ID (order reviews)",     placeholder="Right-click channel → Copy ID", required=False)
    store_ch = TextInput(label="Store Channel ID (post store panel)",  placeholder="Right-click channel → Copy ID", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        lines = []
        if self.admin_ch.value.strip():
            try:
                set_admin_channel(int(self.admin_ch.value.strip()))
                lines.append(f"✅ Admin channel → <#{self.admin_ch.value.strip()}>")
            except ValueError:
                lines.append("❌ Invalid admin channel ID")
        if self.store_ch.value.strip():
            try:
                set_store_channel(int(self.store_ch.value.strip()))
                lines.append(f"✅ Store channel → <#{self.store_ch.value.strip()}>")
            except ValueError:
                lines.append("❌ Invalid store channel ID")
        if not lines:
            await interaction.response.send_message(embed=_err("Enter at least one channel ID."), ephemeral=True)
            return
        await interaction.response.send_message(embed=_ok("Channels Updated", "\n".join(lines)), ephemeral=True)


# ─── Post Store — Channel Picker ──────────────────────────────────────────────

class PostStoreChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, parent: "PostStoreView"):
        self.parent = parent
        super().__init__(
            placeholder="Select channel to post store in...",
            channel_types=[discord.ChannelType.text],
            custom_id="ps_channel_select",
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        self.parent.channel_id = self.values[0].id
        self.parent.channel_mention = self.values[0].mention
        embed = discord.Embed(
            title="🛒 Post Store Panel",
            description=f"Selected channel: {self.values[0].mention}\n\nClick **Post Store** to send the store panel there.",
            color=0x5865F2,
        )
        await interaction.response.edit_message(embed=embed, view=self.parent)


class PostStoreView(View):
    def __init__(self):
        super().__init__(timeout=120)
        self.channel_id: int | None = None
        self.channel_mention: str = ""
        self.add_item(PostStoreChannelSelect(self))

    @discord.ui.button(label="Post Store", emoji="🛒", style=discord.ButtonStyle.primary, row=1)
    async def post(self, interaction: discord.Interaction, button: Button):
        if not self.channel_id:
            await interaction.response.send_message(embed=_err("Please select a channel first."), ephemeral=True)
            return
        from views import StoreView
        channel = interaction.client.get_channel(self.channel_id)
        if not channel:
            await interaction.response.send_message(embed=_err("Channel not found. Make sure the bot has access."), ephemeral=True)
            return
        set_store_channel(channel.id)
        store_embed = discord.Embed(
            title="🛒 Welcome to the Store",
            description=(
                f"{ARROW} Browse products using the dropdown below.\n"
                f"{ARROW} Select a product → choose duration → choose payment.\n"
                f"{ARROW} Submit proof → admin reviews → key delivered via DM.\n\n"
                f"*Delivery is automatic after admin approval.*"
            ),
            color=0x5865F2,
        )
        store_embed.set_footer(text="Select a product from the dropdown to get started.")
        await channel.send(embed=store_embed, view=StoreView())
        await interaction.response.edit_message(
            embed=_ok("Store Posted", f"Store panel sent to {self.channel_mention}."),
            view=None,
        )


# ─── Post Product — Product + Channel Pickers ─────────────────────────────────

class PostProductSelect(discord.ui.Select):
    def __init__(self, parent: "PostProductView", prods: list, page: int = 0):
        self.parent = parent
        self.page   = page
        chunk = prods[page * 25 : (page + 1) * 25]
        options = []
        for p in chunk:
            emoji     = p.get("emoji", "")
            use_emoji = emoji if emoji and emoji != "📦" else None
            prices    = p.get("prices", {})
            cheapest  = next(
                (f"From ${prices[d]:.2f}" for d in ("1day","7day","31day") if prices.get(d, 0) > 0),
                "No price set",
            )
            options.append(discord.SelectOption(
                label=p["name"][:100],
                value=p["id"],
                description=cheapest[:100],
                emoji=use_emoji,
            ))
        super().__init__(
            placeholder="Select a product...",
            options=options,
            custom_id=f"pp_product_select_{page}",
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        self.parent.product_id = self.values[0]
        product = find_product(self.values[0])
        self.parent.product_name = f"{product.get('emoji','')} {product['name']}"
        embed = _build_post_product_embed(self.parent)
        await interaction.response.edit_message(embed=embed, view=self.parent)


class PostProductChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, parent: "PostProductView"):
        self.parent = parent
        super().__init__(
            placeholder="Select channel to post in...",
            channel_types=[discord.ChannelType.text],
            custom_id="pp_channel_select",
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        self.parent.channel_id      = self.values[0].id
        self.parent.channel_mention = self.values[0].mention
        embed = _build_post_product_embed(self.parent)
        await interaction.response.edit_message(embed=embed, view=self.parent)


def _build_post_product_embed(view: "PostProductView") -> discord.Embed:
    lines = []
    if view.product_name:
        lines.append(f"**Product:** {view.product_name}")
    else:
        lines.append("**Product:** *(not selected)*")
    if view.channel_mention:
        lines.append(f"**Channel:** {view.channel_mention}")
    else:
        lines.append("**Channel:** *(not selected)*")
    embed = discord.Embed(
        title="📌 Post Product",
        description="Select a product and channel, then click **Post**.\n\n" + "\n".join(lines),
        color=0x5865F2,
    )
    return embed


class PostProductView(View):
    def __init__(self):
        super().__init__(timeout=120)
        self.product_id:      str | None = None
        self.product_name:    str        = ""
        self.channel_id:      int | None = None
        self.channel_mention: str        = ""
        self._page    = 0
        self._prods   = get_all_products()
        self._rebuild_items()

    def _rebuild_items(self):
        self.clear_items()
        self.add_item(PostProductSelect(self, self._prods, self._page))
        self.add_item(PostProductChannelSelect(self))
        # Pagination buttons if needed
        total_pages = max(1, (len(self._prods) + 24) // 25)
        if self._page > 0:
            self.add_item(_PageButton(self, "◀ Prev", self._page - 1, row=2))
        if self._page < total_pages - 1:
            self.add_item(_PageButton(self, "Next ▶", self._page + 1, row=2))
        self.add_item(_PostProductConfirmButton(row=3))


class _PageButton(Button):
    def __init__(self, parent: PostProductView, label: str, target_page: int, row: int):
        self.parent      = parent
        self.target_page = target_page
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=row)

    async def callback(self, interaction: discord.Interaction):
        self.parent._page = self.target_page
        self.parent._rebuild_items()
        await interaction.response.edit_message(
            embed=_build_post_product_embed(self.parent),
            view=self.parent,
        )


class _PostProductConfirmButton(Button):
    def __init__(self, row: int):
        super().__init__(label="Post to Channel", emoji="📌", style=discord.ButtonStyle.primary, row=row)

    async def callback(self, interaction: discord.Interaction):
        view: PostProductView = self.view
        if not view.product_id:
            await interaction.response.send_message(embed=_err("Please select a product first."), ephemeral=True)
            return
        if not view.channel_id:
            await interaction.response.send_message(embed=_err("Please select a channel first."), ephemeral=True)
            return
        from views import build_product_embed, DurationSelectView
        product = find_product(view.product_id)
        channel = interaction.client.get_channel(view.channel_id)
        if not channel:
            await interaction.response.send_message(embed=_err("Channel not found."), ephemeral=True)
            return
        embed = build_product_embed(product)
        await channel.send(embed=embed, view=DurationSelectView(product))
        await interaction.response.edit_message(
            embed=_ok("Product Posted", f"**{view.product_name}** posted to {view.channel_mention}."),
            view=None,
        )


class BroadcastModal(Modal, title="Broadcast Announcement"):
    title_text = TextInput(label="Title",                                    placeholder="Announcement title...", required=True,  max_length=100)
    message    = TextInput(label="Message",                                  placeholder="Your message...",       style=discord.TextStyle.paragraph, required=True, max_length=2000)
    channel_id = TextInput(label="Channel ID (blank = store channel)",       placeholder="Optional channel ID",   required=False)

    async def on_submit(self, interaction: discord.Interaction):
        ch_id = self.channel_id.value.strip() or str(config.get("store_channel_id",""))
        if not ch_id:
            await interaction.response.send_message(embed=_err("No channel set. Enter a channel ID."), ephemeral=True)
            return
        try:
            channel = interaction.client.get_channel(int(ch_id))
            if not channel:
                await interaction.response.send_message(embed=_err("Channel not found."), ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message(embed=_err("Invalid channel ID."), ephemeral=True)
            return
        embed = discord.Embed(title=f"📢 {self.title_text.value}", description=self.message.value, color=0xF5A623)
        embed.set_footer(text=f"Announcement by {interaction.user.display_name}")
        await channel.send(embed=embed)
        await interaction.response.send_message(embed=_ok("Broadcast Sent", f"Message sent to <#{channel.id}>."), ephemeral=True)


# ─── Admin Panel View ──────────────────────────────────────────────────────────

class AdminPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    # Row 0 — Products
    @discord.ui.button(label="Add Product",    emoji="➕",  style=discord.ButtonStyle.secondary, custom_id="ap_add_product",    row=0)
    async def add_product(self, i, b):
        if not _guard(i): return await _np(i)
        await i.response.send_modal(AddProductModal())

    @discord.ui.button(label="Remove Product", emoji="➖",  style=discord.ButtonStyle.secondary, custom_id="ap_remove_product", row=0)
    async def remove_product_btn(self, i, b):
        if not _guard(i): return await _np(i)
        await i.response.send_modal(RemoveProductModal())

    @discord.ui.button(label="Update Price",   emoji="💵",  style=discord.ButtonStyle.secondary, custom_id="ap_update_price",   row=0)
    async def update_price(self, i, b):
        if not _guard(i): return await _np(i)
        await i.response.send_modal(UpdatePriceModal())

    # Row 1 — Keys
    @discord.ui.button(label="Add Key",        style=discord.ButtonStyle.secondary, emoji=E_KEY,  custom_id="ap_add_key",        row=1)
    async def add_key_btn(self, i, b):
        if not _guard(i): return await _np(i)
        await i.response.send_modal(AddKeyModal())

    @discord.ui.button(label="Bulk Add Keys",  emoji="📥",  style=discord.ButtonStyle.secondary, custom_id="ap_bulk_keys",      row=1)
    async def bulk_keys(self, i, b):
        if not _guard(i): return await _np(i)
        await i.response.send_modal(BulkAddKeysModal())

    @discord.ui.button(label="View Stock",     emoji="📊",  style=discord.ButtonStyle.secondary, custom_id="ap_view_stock",     row=1)
    async def view_stock(self, i, b):
        if not _guard(i): return await _np(i)
        prods = get_all_products()
        dur_label = {"1day": "1 Day", "7day": "7 Days", "31day": "31 Days"}
        embed = discord.Embed(title="Key Stock", color=0x5865F2)
        for p in prods:
            lines = []
            for dur in ("1day","7day","31day"):
                if p["prices"].get(dur, 0) > 0:
                    stock = count_keys(f"{p['id']}_{dur}")
                    status = str(stock) if stock > 0 else "Out of stock"
                    lines.append(f"{dur_label[dur]}: **{status}**")
            if lines:
                embed.add_field(
                    name=p["name"],
                    value="\n".join(lines),
                    inline=True,
                )
        if not embed.fields:
            embed.description = "No products found."
        await i.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Clear Keys",     emoji="🗑️", style=discord.ButtonStyle.secondary, custom_id="ap_clear_keys",     row=1)
    async def clear_keys(self, i, b):
        if not _guard(i): return await _np(i)
        await i.response.send_modal(ClearKeysModal())

    # Row 2 — Payments
    @discord.ui.button(label="Set UPI",           style=discord.ButtonStyle.secondary, emoji=E_UPI,  custom_id="ap_set_upi",           row=2)
    async def set_upi(self, i, b):
        if not _guard(i): return await _np(i)
        await i.response.send_modal(SetUPIModal())

    @discord.ui.button(label="Set Binance",       style=discord.ButtonStyle.secondary, emoji=E_BIN,  custom_id="ap_set_binance",       row=2)
    async def set_binance_btn(self, i, b):
        if not _guard(i): return await _np(i)
        await i.response.send_modal(SetBinanceModal())

    @discord.ui.button(label="Gift Card Sites",   style=discord.ButtonStyle.secondary, emoji=E_GIFT, custom_id="ap_gift_card_sites",   row=2)
    async def gift_card_sites(self, i, b):
        if not _guard(i): return await _np(i)
        providers_list = "\n".join(f"• {p}" for p in GIFT_CARD_PROVIDERS)
        embed = discord.Embed(
            title="🎁 Accepted Gift Card Providers",
            description=(
                f"The following gift card providers are shown to customers during checkout:\n\n"
                f"{providers_list}\n\n"
                f"To change accepted providers, edit `GIFT_CARD_PROVIDERS` in `settings.py`."
            ),
            color=0x5865F2,
        )
        await i.response.send_message(embed=embed, ephemeral=True)

    # Row 3 — Admins & Setup
    @discord.ui.button(label="Add Admin",      style=discord.ButtonStyle.secondary, emoji=E_ADMIN, custom_id="ap_add_admin",     row=3)
    async def add_admin_btn(self, i, b):
        if not _guard(i): return await _np(i)
        await i.response.send_modal(AddAdminModal())

    @discord.ui.button(label="Remove Admin",   emoji="🚫",  style=discord.ButtonStyle.secondary, custom_id="ap_remove_admin",   row=3)
    async def remove_admin_btn(self, i, b):
        if not _guard(i): return await _np(i)
        await i.response.send_modal(RemoveAdminModal())

    @discord.ui.button(label="Setup Channels", emoji="⚙️",  style=discord.ButtonStyle.primary,   custom_id="ap_setup",          row=3)
    async def setup(self, i, b):
        if not _guard(i): return await _np(i)
        await i.response.send_modal(SetupChannelsModal())

    # Row 4 — Store & Broadcast
    @discord.ui.button(label="Post Store",   emoji="🛒",  style=discord.ButtonStyle.primary, custom_id="ap_post_store",   row=4)
    async def post_store(self, i, b):
        if not _guard(i): return await _np(i)
        embed = discord.Embed(
            title="🛒 Post Store Panel",
            description="Select the channel you want to post the store panel in.",
            color=0x5865F2,
        )
        await i.response.send_message(embed=embed, view=PostStoreView(), ephemeral=True)

    @discord.ui.button(label="Post Product", emoji="📌",  style=discord.ButtonStyle.primary, custom_id="ap_post_product", row=4)
    async def post_product(self, i, b):
        if not _guard(i): return await _np(i)
        embed = discord.Embed(
            title="📌 Post Product",
            description=(
                "Select a product and a channel below, then click **Post to Channel**.\n\n"
                "**Product:** *(not selected)*\n"
                "**Channel:** *(not selected)*"
            ),
            color=0x5865F2,
        )
        await i.response.send_message(embed=embed, view=PostProductView(), ephemeral=True)

    @discord.ui.button(label="Broadcast",    emoji="📢",  style=discord.ButtonStyle.danger,  custom_id="ap_broadcast",    row=4)
    async def broadcast(self, i, b):
        if not _guard(i): return await _np(i)
        await i.response.send_modal(BroadcastModal())


async def _np(i):
    await i.response.send_message(
        embed=discord.Embed(title="❌ No Permission", description="You don't have admin access.", color=0xED4245),
        ephemeral=True,
    )
