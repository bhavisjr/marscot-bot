import discord
from discord.ui import View, Button, Select, Modal, TextInput
from typing import Optional
import asyncio

from settings import (
    E_CART, E_KEY, E_OK, E_WARN, E_UPI, E_BIN, E_GIFT, E_ADMIN, E_ARROW,
    ARROW, CHECK, CROSS, WARN, KEY, CLOCK, MONEY, GIFT_CARD_PROVIDERS,
)
from products import get_all_products, find_product, format_price
from orders import create_order, get_order, set_order_proof, set_order_gift_code
from payments import get_binance, get_upi_qr_url
from config import config
import keys as keys_mod


def duration_label(d: str) -> str:
    return {"1day": "1 Day", "7day": "7 Days", "31day": "31 Days"}.get(d, d)


# ─── Product Embed ─────────────────────────────────────────────────────────────

def build_product_embed(product: dict) -> discord.Embed:
    prices = product["prices"]
    desc   = product.get("description", "")
    if desc.strip().lower() == product["name"].strip().lower():
        desc = ""

    embed = discord.Embed(title=product["name"], description=desc or None, color=0x5865F2)

    for dur, label in [("1day", "1 Day"), ("7day", "7 Days"), ("31day", "31 Days")]:
        price = prices.get(dur, 0)
        if price > 0:
            stock = keys_mod.count_keys(f"{product['id']}_{dur}")
            if stock > 0:
                embed.add_field(name=label, value=f"```${price:.2f}```**In Stock** ({stock})", inline=True)

    if product.get("image_url"):
        embed.set_image(url=product["image_url"])

    embed.set_footer(text="Select a duration below to purchase")
    return embed


# ─── Store View ────────────────────────────────────────────────────────────────

class ProductSelect(Select):
    def __init__(self):
        prods   = get_all_products()
        options = []
        for p in prods[:25]:
            prices   = p.get("prices", {})
            cheapest = next((f"From ${prices[d]:.2f}" for d in ("1day","7day","31day") if prices.get(d,0) > 0), "No price set")
            options.append(discord.SelectOption(
                label=p["name"][:100],
                value=p["id"],
                description=cheapest[:100],
            ))
        super().__init__(placeholder="Select a product...", options=options, custom_id="product_select")

    async def callback(self, interaction: discord.Interaction):
        product = find_product(self.values[0])
        if not product:
            await interaction.response.send_message("Product not found.", ephemeral=True)
            return
        await interaction.response.send_message(
            embed=build_product_embed(product),
            view=DurationSelectView(product),
            ephemeral=True,
        )


class StoreView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ProductSelect())


# ─── Duration Select ───────────────────────────────────────────────────────────

class DurationSelect(Select):
    def __init__(self, product: dict):
        self.product = product
        prices  = product["prices"]
        options = []
        for dur, label in [("1day","1 Day"),("7day","7 Days"),("31day","31 Days")]:
            price = prices.get(dur, 0)
            if price > 0:
                stock = keys_mod.count_keys(f"{product['id']}_{dur}")
                if stock > 0:
                    options.append(discord.SelectOption(
                        label=f"{label}  —  ${price:.2f}",
                        value=dur,
                        description=f"In stock ({stock})",
                    ))
        if not options:
            options = [discord.SelectOption(label="Currently out of stock", value="none")]
        super().__init__(placeholder="Choose your plan duration...", options=options, custom_id=f"dur_{product['id']}")

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("No plans available for this product.", ephemeral=True)
            return
        dur   = self.values[0]
        price = self.product["prices"][dur]
        await interaction.response.send_message(
            embed=build_checkout_embed(self.product, dur, price),
            view=PaymentMethodView(self.product, dur, price),
            ephemeral=True,
        )


class DurationSelectView(View):
    def __init__(self, product: dict):
        super().__init__(timeout=180)
        self.add_item(DurationSelect(product))


# ─── Checkout Embed ────────────────────────────────────────────────────────────

def build_checkout_embed(product: dict, duration: str, price: float) -> discord.Embed:
    embed = discord.Embed(
        title=product["name"],
        color=0x5865F2,
    )
    embed.add_field(name="Duration",  value=duration_label(duration), inline=True)
    embed.add_field(name="Amount",    value=f"**${price:.2f}**",      inline=True)
    embed.add_field(name="Delivery",  value="5 – 30 min",              inline=True)

    embed.description = (
        "**Checkout**\n\n"
        "Select a payment method below  ·  Key sent to DMs after verification"
    )

    if product.get("image_url"):
        embed.set_thumbnail(url=product["image_url"])

    embed.set_footer(text="All payments are manually verified before delivery.")
    return embed


# ─── Payment Method View ───────────────────────────────────────────────────────

class PaymentMethodView(View):
    def __init__(self, product: dict, duration: str, price: float):
        super().__init__(timeout=300)
        self.product  = product
        self.duration = duration
        self.price    = price

    @discord.ui.button(label="UPI",       style=discord.ButtonStyle.secondary, emoji=E_UPI,  custom_id="pay_upi",      row=0)
    async def pay_upi(self, interaction: discord.Interaction, button: Button):
        await self._handle(interaction, "upi")

    @discord.ui.button(label="Binance",   style=discord.ButtonStyle.secondary, emoji=E_BIN,  custom_id="pay_binance",  row=0)
    async def pay_binance(self, interaction: discord.Interaction, button: Button):
        await self._handle(interaction, "binance")

    @discord.ui.button(label="Gift Card", style=discord.ButtonStyle.secondary, emoji=E_GIFT, custom_id="pay_giftcard", row=0)
    async def pay_giftcard(self, interaction: discord.Interaction, button: Button):
        await self._handle(interaction, "giftcard")

    async def _handle(self, interaction: discord.Interaction, method: str):
        order_id = create_order(
            user_id=interaction.user.id, username=str(interaction.user),
            product=self.product, duration=self.duration,
            price=self.price, payment_method=method,
        )
        order = get_order(order_id)
        if method == "upi":
            await self._show_upi(interaction, order)
        elif method == "binance":
            await self._show_binance(interaction, order)
        else:
            await self._show_giftcard(interaction, order)

    async def _show_upi(self, interaction: discord.Interaction, order: dict):
        upi_qr = get_upi_qr_url()
        embed  = discord.Embed(
            title="Payment Instructions — UPI",
            color=0x5865F2,
        )
        embed.add_field(name="Order ID",  value=f"`{order['order_id']}`",   inline=True)
        embed.add_field(name="Product",   value=order["product_name"],       inline=True)
        embed.add_field(name="Duration",  value=duration_label(order["duration"]), inline=True)
        embed.add_field(name="Amount Due", value=f"**${order['price']:.2f}**", inline=True)
        embed.add_field(name="Payment Method", value="UPI",                  inline=True)
        embed.add_field(name="Delivery",  value="5 – 30 min after approval", inline=True)
        embed.add_field(
            name="How to Complete Payment",
            value=(
                "**1.** Scan the QR code shown below\n"
                "**2.** Enter the exact amount: **${:.2f}**\n"
                "**3.** Complete the payment in your UPI app\n"
                "**4.** Take a screenshot of the **success screen**\n"
                "**5.** Click **Submit Payment Proof** below and upload it"
            ).format(order["price"]),
            inline=False,
        )
        embed.add_field(
            name="Screenshot Requirements",
            value=(
                "Your screenshot must clearly show:\n"
                "> Transaction amount\n"
                "> Date & time\n"
                "> Transaction ID / UTR number\n"
                "> Success status"
            ),
            inline=False,
        )
        if upi_qr:
            embed.set_image(url=upi_qr)
        embed.set_footer(text="Your key will be delivered via DM within 5–30 minutes of approval  •  Keep your DMs open")
        await interaction.response.send_message(
            embed=embed,
            view=SubmitProofView(order["order_id"], "upi"),
            ephemeral=True,
        )

    async def _show_binance(self, interaction: discord.Interaction, order: dict):
        binance_id = get_binance()
        embed = discord.Embed(
            title="Payment Instructions — Binance Pay",
            color=0xF0B90B,
        )
        embed.add_field(name="Order ID",  value=f"`{order['order_id']}`",   inline=True)
        embed.add_field(name="Product",   value=order["product_name"],       inline=True)
        embed.add_field(name="Duration",  value=duration_label(order["duration"]), inline=True)
        embed.add_field(name="Amount Due", value=f"**${order['price']:.2f} USDT**", inline=True)
        embed.add_field(name="Payment Method", value="Binance Pay",          inline=True)
        embed.add_field(name="Delivery",  value="5 – 30 min after approval", inline=True)
        embed.add_field(
            name="Binance Pay ID",
            value=f"```{binance_id or 'Not configured — contact an admin'}```",
            inline=False,
        )
        embed.add_field(
            name="How to Complete Payment",
            value=(
                "**1.** Open **Binance** app → Pay → Send\n"
                "**2.** Enter the Pay ID shown above\n"
                "**3.** Send exactly **${:.2f} USDT**\n"
                "**4.** Take a screenshot of the **confirmation screen**\n"
                "**5.** Click **Submit Payment Proof** below and upload it"
            ).format(order["price"]),
            inline=False,
        )
        embed.add_field(
            name="Screenshot Requirements",
            value=(
                "Your screenshot must clearly show:\n"
                "> Transaction amount in USDT\n"
                "> Transaction hash / ID\n"
                "> Date & time\n"
                "> Success / Completed status"
            ),
            inline=False,
        )
        embed.set_footer(text="Your key will be delivered via DM within 5–30 minutes of approval  •  Keep your DMs open")
        await interaction.response.send_message(
            embed=embed,
            view=SubmitProofView(order["order_id"], "binance"),
            ephemeral=True,
        )

    async def _show_giftcard(self, interaction: discord.Interaction, order: dict):
        providers_list = "\n".join(f"> {p}" for p in GIFT_CARD_PROVIDERS)
        embed = discord.Embed(
            title="Payment Instructions — Gift Card",
            description="Select the platform you purchased your gift card from, then submit the redemption code.",
            color=0x5865F2,
        )
        embed.add_field(name="Order ID",   value=f"`{order['order_id']}`",  inline=True)
        embed.add_field(name="Product",    value=order["product_name"],      inline=True)
        embed.add_field(name="Duration",   value=duration_label(order["duration"]), inline=True)
        embed.add_field(name="Amount Due", value=f"**${order['price']:.2f}**", inline=True)
        embed.add_field(name="Delivery",   value="5 – 30 min after approval", inline=True)
        embed.add_field(name="\u200b",     value="\u200b",                    inline=True)
        embed.add_field(
            name="Accepted Providers",
            value=providers_list,
            inline=True,
        )
        embed.add_field(
            name="Important",
            value=(
                "> Purchase a gift card for the **exact amount**\n"
                "> Do **not** redeem the card yourself\n"
                "> Submit only unused codes\n"
                "> Used codes are detected and orders are rejected"
            ),
            inline=False,
        )
        embed.set_footer(text="Your key will be delivered via DM within 5–30 minutes of approval  •  Keep your DMs open")
        await interaction.response.send_message(
            embed=embed,
            view=GiftCardProviderView(order["order_id"], order["price"]),
            ephemeral=True,
        )


# ─── Gift Card Provider Select ─────────────────────────────────────────────────

class GiftCardProviderSelect(Select):
    def __init__(self, order_id: str, price: float):
        self.order_id = order_id
        self.price    = price
        options = [
            discord.SelectOption(label=p, value=p)
            for p in GIFT_CARD_PROVIDERS
        ]
        super().__init__(
            placeholder="Select gift card provider...",
            options=options,
            custom_id=f"gc_provider_{order_id}",
        )

    async def callback(self, interaction: discord.Interaction):
        provider = self.values[0]
        await interaction.response.send_modal(GiftCardCodeModal(self.order_id, provider))


class GiftCardProviderView(View):
    def __init__(self, order_id: str, price: float):
        super().__init__(timeout=600)
        self.add_item(GiftCardProviderSelect(order_id, price))


# ─── Gift Card Code Modal ──────────────────────────────────────────────────────

class GiftCardCodeModal(Modal, title="Gift Card Code"):
    code = TextInput(
        label="Redemption Code",
        placeholder="Paste your gift card code here...",
        required=True,
        max_length=200,
        style=discord.TextStyle.paragraph,
    )

    def __init__(self, order_id: str, provider: str):
        super().__init__()
        self.order_id = order_id
        self.provider = provider

    async def on_submit(self, interaction: discord.Interaction):
        set_order_gift_code(self.order_id, self.code.value.strip(), site=self.provider)
        order = get_order(self.order_id)
        await send_admin_review(interaction.client, order, proof_url=None, gift_code=self.code.value.strip())
        await interaction.response.send_message(
            embed=_build_under_review_embed(order, self.provider),
            ephemeral=True,
        )


# ─── Under Review embed helper ────────────────────────────────────────────────

def _build_under_review_embed(order: dict, method_display: str) -> discord.Embed:
    embed = discord.Embed(
        title="Payment Received — Under Review",
        description=(
            "Your payment has been submitted and is now being reviewed by our team.\n"
            "Your license key will be delivered to your **DMs** automatically once approved."
        ),
        color=0xF5A623,
    )
    embed.add_field(name="Order ID",  value=f"`{order['order_id']}`",         inline=True)
    embed.add_field(name="Product",   value=order["product_name"],             inline=True)
    embed.add_field(name="Duration",  value=duration_label(order["duration"]), inline=True)
    embed.add_field(name="Amount",    value=f"**${order['price']:.2f}**",      inline=True)
    embed.add_field(name="Payment",   value=method_display,                    inline=True)
    embed.add_field(name="Est. Wait", value="5 – 30 minutes",                  inline=True)
    embed.add_field(
        name="What Happens Next",
        value=(
            "> Our team verifies your payment\n"
            "> Your license key is assigned to your order\n"
            "> Key is sent to you via Discord DM\n"
            "> You can start using it immediately"
        ),
        inline=False,
    )
    embed.add_field(
        name="Need Help?",
        value=f"Contact support and quote Order ID `{order['order_id']}`",
        inline=False,
    )
    embed.set_footer(text="Keep your DMs open to receive your key  •  Do not place duplicate orders")
    return embed


# ─── Submit Proof (screenshot upload) ─────────────────────────────────────────

class SubmitProofView(View):
    def __init__(self, order_id: str, method: str):
        super().__init__(timeout=600)
        self.order_id = order_id
        self.method   = method

    @discord.ui.button(label="Submit Payment Proof", style=discord.ButtonStyle.success, emoji=E_OK, custom_id="submit_proof")
    async def submit(self, interaction: discord.Interaction, button: Button):
        order = get_order(self.order_id)
        embed = discord.Embed(
            title="Upload Payment Screenshot",
            color=0x5865F2,
        )
        embed.add_field(name="Order ID", value=f"`{self.order_id}`", inline=True)
        embed.add_field(name="Amount",   value=f"**${order['price']:.2f}**", inline=True)
        embed.add_field(name="\u200b",   value="\u200b", inline=True)
        embed.add_field(
            name="Instructions",
            value=(
                "Send your screenshot as the **next message** in this channel.\n"
                "Drag & drop the image or use the attachment button.\n\n"
                "Your screenshot **must** clearly show:\n"
                "> Payment amount\n"
                "> Transaction ID or reference number\n"
                "> Date and time\n"
                "> Success / Completed status"
            ),
            inline=False,
        )
        embed.set_footer(text="You have 3 minutes to upload  •  Blurry or cropped screenshots will be rejected")
        await interaction.response.send_message(embed=embed, ephemeral=True)

        def check(m: discord.Message):
            return (
                m.author.id == interaction.user.id
                and m.channel.id == interaction.channel.id
                and len(m.attachments) > 0
            )

        try:
            msg       = await interaction.client.wait_for("message", check=check, timeout=180)
            proof_url = msg.attachments[0].url
            set_order_proof(self.order_id, proof_url)
            order = get_order(self.order_id)
            await send_admin_review(interaction.client, order, proof_url)
            try:
                await msg.delete()
            except Exception:
                pass

            method_display = {"upi": "UPI", "binance": "Binance Pay"}.get(self.method, self.method.title())
            await interaction.followup.send(
                embed=_build_under_review_embed(order, method_display),
                ephemeral=True,
            )

        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="Upload Timed Out",
                description=(
                    "You didn't upload a screenshot within 3 minutes.\n\n"
                    "Please start your order again from the store.\n"
                    f"If you need help, quote Order ID `{self.order_id}` when contacting support."
                ),
                color=0xED4245,
            )
            embed.set_footer(text="Your order has been cancelled due to inactivity")
            await interaction.followup.send(embed=embed, ephemeral=True)


# ─── Send to Admin Channel ─────────────────────────────────────────────────────

async def send_admin_review(
    bot: discord.Client,
    order: dict,
    proof_url: Optional[str],
    gift_code: Optional[str] = None,
):
    admin_channel_id = config.get("admin_channel_id")
    if not admin_channel_id:
        return
    channel = bot.get_channel(int(admin_channel_id))
    if not channel:
        return

    method_map = {
        "upi":      "UPI",
        "binance":  "Binance Pay",
        "giftcard": f"Gift Card — {order.get('gift_card_site', 'Unknown')}",
    }
    method_display = method_map.get(order["payment_method"], order["payment_method"].title())

    embed = discord.Embed(
        title="New Order — Pending Approval",
        color=0xF5A623,
    )
    embed.add_field(name="Order ID",  value=f"`{order['order_id']}`",          inline=True)
    embed.add_field(name="Customer",  value=f"`{order['username']}`",           inline=True)
    embed.add_field(name="User ID",   value=f"`{order['user_id']}`",            inline=True)
    embed.add_field(name="Product",   value=order["product_name"],              inline=True)
    embed.add_field(name="Duration",  value=duration_label(order["duration"]),  inline=True)
    embed.add_field(name="Amount",    value=f"**${order['price']:.2f}**",       inline=True)
    embed.add_field(name="Payment",   value=method_display,                     inline=True)

    if order.get("gift_card_site") and order["payment_method"] == "giftcard":
        embed.add_field(name="Provider", value=order["gift_card_site"], inline=True)

    embed.add_field(name="\u200b", value="\u200b", inline=True)

    if gift_code:
        embed.add_field(name="Gift Card Code", value=f"```{gift_code}```", inline=False)

    if proof_url:
        embed.add_field(name="Payment Proof", value="Screenshot attached below.", inline=False)
        embed.set_image(url=proof_url)

    embed.set_footer(text=f"Submitted by {order['username']}  •  Use the buttons below to action this order")
    await channel.send(embed=embed, view=AdminApprovalView(order["order_id"]))


# ─── Admin Approval View ───────────────────────────────────────────────────────

class AdminApprovalView(View):
    def __init__(self, order_id: str):
        super().__init__(timeout=None)
        self.order_id = order_id

    @discord.ui.button(label="Approve & Send Key", style=discord.ButtonStyle.success, emoji=E_OK,   custom_id="approve_order", row=0)
    async def approve(self, interaction: discord.Interaction, button: Button):
        from config import is_admin
        if not is_admin(interaction.user.id):
            await interaction.response.send_message("❌ No permission.", ephemeral=True)
            return
        order = get_order(self.order_id)
        if not order:
            await interaction.response.send_message("Order not found.", ephemeral=True)
            return
        if order["status"] != "pending":
            await interaction.response.send_message(f"Order is already **{order['status']}**.", ephemeral=True)
            return
        key = keys_mod.pop_key(f"{order['product_id']}_{order['duration']}")
        if not key:
            await interaction.response.send_modal(ManualKeyModal(self.order_id))
            return
        await self._finalize(interaction, order, key)

    @discord.ui.button(label="Reject Order", style=discord.ButtonStyle.danger, emoji=E_WARN, custom_id="reject_order", row=0)
    async def reject(self, interaction: discord.Interaction, button: Button):
        from config import is_admin
        if not is_admin(interaction.user.id):
            await interaction.response.send_message("❌ No permission.", ephemeral=True)
            return
        order = get_order(self.order_id)
        if not order:
            await interaction.response.send_message("Order not found.", ephemeral=True)
            return
        if order["status"] != "pending":
            await interaction.response.send_message(f"Order is already **{order['status']}**.", ephemeral=True)
            return
        await interaction.response.send_modal(RejectReasonModal(self.order_id))

    async def _finalize(self, interaction: discord.Interaction, order: dict, key: str):
        from orders import approve_order
        approve_order(order["order_id"])
        user = await interaction.client.fetch_user(order["user_id"])
        dm_sent = False
        try:
            dm_embed = discord.Embed(
                title="Order Complete — License Key Delivered",
                description=(
                    "Your payment has been verified and your order is complete.\n"
                    "Your license key is below — copy it and keep it safe."
                ),
                color=0x57F287,
            )
            dm_embed.add_field(name="Order ID",  value=f"`{order['order_id']}`",         inline=True)
            dm_embed.add_field(name="Product",   value=order["product_name"],             inline=True)
            dm_embed.add_field(name="Duration",  value=duration_label(order["duration"]), inline=True)
            dm_embed.add_field(name="Amount Paid", value=f"**${order['price']:.2f}**",   inline=True)
            dm_embed.add_field(name="Status",    value="Approved",                        inline=True)
            dm_embed.add_field(name="\u200b",    value="\u200b",                          inline=True)
            dm_embed.add_field(
                name="Your License Key",
                value=f"```{key}```",
                inline=False,
            )
            dm_embed.add_field(
                name="Important",
                value=(
                    "> Do **not** share your key with anyone\n"
                    "> Each key is tied to one account\n"
                    "> Contact support if you have any issues"
                ),
                inline=False,
            )
            dm_embed.set_footer(text="Thank you for your purchase  •  Keep this message for your records")
            await user.send(embed=dm_embed)
            dm_sent = True
        except discord.Forbidden:
            pass

        admin_embed = discord.Embed(
            title="Order Approved",
            color=0x57F287,
        )
        admin_embed.add_field(name="Order ID",   value=f"`{order['order_id']}`",  inline=True)
        admin_embed.add_field(name="Customer",   value=f"`{order['username']}`",  inline=True)
        admin_embed.add_field(name="Approved By", value=interaction.user.mention, inline=True)
        admin_embed.add_field(
            name="Key Delivery",
            value="Sent via DM" if dm_sent else "DM failed — user may have DMs disabled",
            inline=False,
        )
        await interaction.response.edit_message(embed=admin_embed, view=None)


class ManualKeyModal(Modal, title="Enter Key Manually"):
    key = TextInput(
        label="License Key",
        placeholder="No key in stock — paste the key here manually...",
        style=discord.TextStyle.paragraph,
        required=True,
    )

    def __init__(self, order_id: str):
        super().__init__()
        self.order_id = order_id

    async def on_submit(self, interaction: discord.Interaction):
        order = get_order(self.order_id)
        view  = AdminApprovalView(self.order_id)
        await view._finalize(interaction, order, self.key.value.strip())


class RejectReasonModal(Modal, title="Rejection Reason"):
    reason = TextInput(
        label="Reason",
        placeholder="e.g. Invalid screenshot, wrong amount, used gift card...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500,
    )

    def __init__(self, order_id: str):
        super().__init__()
        self.order_id = order_id

    async def on_submit(self, interaction: discord.Interaction):
        from orders import reject_order
        order = get_order(self.order_id)
        reject_order(self.order_id)
        user = await interaction.client.fetch_user(order["user_id"])
        dm_sent = False
        try:
            dm_embed = discord.Embed(
                title="Order Rejected — Action Required",
                description=(
                    "Unfortunately your payment could not be verified and your order has been rejected.\n"
                    "Please review the reason below and re-submit if you believe this is a mistake."
                ),
                color=0xED4245,
            )
            dm_embed.add_field(name="Order ID",  value=f"`{order['order_id']}`",         inline=True)
            dm_embed.add_field(name="Product",   value=order["product_name"],             inline=True)
            dm_embed.add_field(name="Duration",  value=duration_label(order["duration"]), inline=True)
            dm_embed.add_field(name="Amount",    value=f"**${order['price']:.2f}**",      inline=True)
            dm_embed.add_field(name="Status",    value="Rejected",                        inline=True)
            dm_embed.add_field(name="\u200b",    value="\u200b",                          inline=True)
            dm_embed.add_field(
                name="Rejection Reason",
                value=f"> {self.reason.value}",
                inline=False,
            )
            dm_embed.add_field(
                name="What To Do Next",
                value=(
                    "> Fix the issue described above\n"
                    "> Place a new order from the store\n"
                    "> Contact support if you believe this is an error"
                ),
                inline=False,
            )
            dm_embed.set_footer(text=f"Quote Order ID {order['order_id']} when contacting support")
            await user.send(embed=dm_embed)
            dm_sent = True
        except discord.Forbidden:
            pass

        admin_embed = discord.Embed(
            title="Order Rejected",
            color=0xED4245,
        )
        admin_embed.add_field(name="Order ID",    value=f"`{self.order_id}`",       inline=True)
        admin_embed.add_field(name="Customer",    value=f"`{order['username']}`",   inline=True)
        admin_embed.add_field(name="Rejected By", value=interaction.user.mention,   inline=True)
        admin_embed.add_field(name="Reason",      value=self.reason.value,          inline=False)
        admin_embed.add_field(
            name="Buyer Notification",
            value="DM sent" if dm_sent else "DM failed — user may have DMs disabled",
            inline=False,
        )
        await interaction.response.edit_message(embed=admin_embed, view=None)
