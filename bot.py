import sys, os
_here = os.path.dirname(os.path.abspath(__file__))
os.chdir(_here)
if _here not in sys.path:
    sys.path.insert(0, _here)

import discord
from discord.ext import commands

from settings import BOT_TOKEN
from admin_panel import AdminPanelView
from views import StoreView


class StoreBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(AdminPanelView())
        self.add_view(StoreView())
        from admin_cog import AdminCog
        await self.add_cog(AdminCog(self))
        await self.tree.sync()
        print("✅ Slash commands synced.")

    async def on_ready(self):
        print(f"✅ Logged in as {self.user} ({self.user.id})")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="the store | /panel",
            )
        )


bot = StoreBot()


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    await bot.process_commands(message)


if __name__ == "__main__":
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN environment variable is not set.")
        exit(1)
    bot.run(BOT_TOKEN)
