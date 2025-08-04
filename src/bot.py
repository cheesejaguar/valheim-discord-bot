import asyncio
import logging
import os
from datetime import timedelta
from typing import Union

import a2s
import discord
from discord.ext import tasks

logging.basicConfig(level=logging.INFO)


# Helper function to clean environment variables
def clean_env_var(value: Union[str, None], default: str = "") -> str:
    """Clean environment variable by removing comments and whitespace."""
    if value is None:
        return default
    # Split on '#' to remove inline comments, then strip whitespace
    return value.split("#")[0].strip() or default


TOKEN = clean_env_var(os.getenv("DISCORD_TOKEN"))
CHANNEL_ID = int(clean_env_var(os.getenv("DISCORD_CHANNEL_ID"), "0"))
MESSAGE_ID = int(clean_env_var(os.getenv("DISCORD_MESSAGE_ID"), "0"))
HOST = clean_env_var(os.getenv("VALHEIM_HOST"), "localhost")
PORT = int(clean_env_var(os.getenv("VALHEIM_QUERY_PORT"), "2457"))
UPDATE_PERIOD = int(clean_env_var(os.getenv("UPDATE_PERIOD"), "60"))

ADDRESS = (HOST, PORT)


# -------- Discord client --------
class ValheimBot(discord.Client):
    async def on_ready(self) -> None:
        channel = await self.fetch_channel(CHANNEL_ID)
        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            logging.error(f"Channel {CHANNEL_ID} is not a text channel or thread.")
            # You might want to handle this more gracefully
            self.message = None
        else:
            self.message = await channel.fetch_message(MESSAGE_ID)

        self.channel = channel
        logging.info(f"Connected as {self.user} – monitoring {ADDRESS}")
        self.update_status.start()

    @tasks.loop(seconds=UPDATE_PERIOD)
    async def update_status(self) -> None:
        try:
            info = await asyncio.to_thread(a2s.info, ADDRESS, timeout=3)
            try:
                rules = await asyncio.to_thread(a2s.rules, ADDRESS, timeout=3)
            except Exception:
                rules = {}

            status_line = (
                f"🟢 **Online** – {info.player_count}/{info.max_players} players"
            )
            title = f"⚔️ {info.server_name}"
            embed = discord.Embed(title=title, description=status_line)

            embed.add_field(
                name="👥 Players",
                value=f"{info.player_count}/{info.max_players}",
                inline=True,
            )
            embed.add_field(name="🛠️ Version", value=info.version, inline=True)
            embed.add_field(
                name="🔒 Password",
                value="Required" if info.password_protected else "Not required",
                inline=True,
            )

            world_name = (
                rules.get("world_name")
                or rules.get("world")
                or getattr(info, "map_name", None)
                or "Unknown"
            )
            embed.add_field(name="🌍 World", value=world_name, inline=True)

            uptime = rules.get("uptime")
            if uptime is None:
                uptime_str = "Unknown"
            else:
                try:
                    uptime_seconds = int(float(uptime))
                    uptime_str = str(timedelta(seconds=uptime_seconds))
                except (ValueError, TypeError):
                    uptime_str = str(uptime)
            embed.add_field(name="⏱️ Uptime", value=uptime_str, inline=True)

            map_enabled_val = rules.get("map_enabled")
            if map_enabled_val is None:
                map_status = "Unknown"
            else:
                map_status = (
                    "Visible"
                    if str(map_enabled_val).lower() in {"1", "true", "yes", "on"}
                    else "Hidden"
                )
            embed.add_field(name="🗺️ Map", value=map_status, inline=True)
        except Exception:
            status_line = "🔴 **Offline / unreachable**"
            title = "⚠️ Valheim Server"
            embed = discord.Embed(title=title, description=status_line)
            # Add all fields with placeholder values for offline status
            embed.add_field(
                name="👥 Players",
                value="Unknown",
                inline=True,
            )
            embed.add_field(name="🛠️ Version", value="Unknown", inline=True)
            embed.add_field(
                name="🔒 Password",
                value="Unknown",
                inline=True,
            )
            embed.add_field(name="🌍 World", value="Unknown", inline=True)
            embed.add_field(name="⏱️ Uptime", value="Unknown", inline=True)
            embed.add_field(name="🗺️ Map", value="Unknown", inline=True)

        embed.add_field(name="🌍 Address", value=f"`{HOST}:{PORT}`", inline=False)
        if self.message is not None:
            await self.message.edit(embed=embed)

    @update_status.before_loop
    async def before_update(self) -> None:
        await self.wait_until_ready()


intents = discord.Intents.none()  # no privileged intents needed
client = ValheimBot(intents=intents)

if __name__ == "__main__":
    client.run(TOKEN)
