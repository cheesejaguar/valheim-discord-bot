import os
import asyncio
import logging
import a2s
import discord
from discord.ext import tasks

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
MESSAGE_ID = int(os.getenv("DISCORD_MESSAGE_ID", "0"))
HOST = os.getenv("VALHEIM_HOST", "localhost")
PORT = int(os.getenv("VALHEIM_QUERY_PORT", "2457"))
UPDATE_PERIOD = int(os.getenv("UPDATE_PERIOD", "60"))

ADDRESS = (HOST, PORT)

# -------- Discord client --------
class ValheimBot(discord.Client):
    async def on_ready(self):
        self.channel = await self.fetch_channel(CHANNEL_ID)
        self.message = await self.channel.fetch_message(MESSAGE_ID)
        logging.info(f"Connected as {self.user} – monitoring {ADDRESS}")
        self.update_status.start()

    @tasks.loop(seconds=UPDATE_PERIOD)
    async def update_status(self):
        try:
            info = await asyncio.to_thread(a2s.info, ADDRESS, timeout=3)
            status_line = f"🟢 **Online** – {info.player_count}/{info.max_players} players"
        except Exception:
            status_line = "🔴 **Offline / unreachable**"

        embed = discord.Embed(description=status_line)
        if self.message is not None:
            await self.message.edit(embed=embed)

    @update_status.before_loop
    async def before_update(self):
        await self.wait_until_ready()

intents = discord.Intents.none()  # no privileged intents needed
client = ValheimBot(intents=intents)

if __name__ == "__main__":
    client.run(TOKEN)