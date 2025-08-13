import asyncio
import logging
import os
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

            world_name = (
                rules.get("world_name")
                or rules.get("world")
                or getattr(info, "map_name", "Unknown")
                or "Unknown"
            )
            uptime = rules.get("uptime", "Unknown")
            map_enabled_raw = str(rules.get("map_enabled", "1")).lower()
            map_visible = map_enabled_raw in {"1", "true", "yes"}
            password_required = bool(
                getattr(info, "password_protected", False)
                or str(rules.get("password_required", "")).lower()
                in {"1", "true", "yes"}
            )

            status_line = (
                "🟢 **Online**\n"
                f"👥 {info.player_count}/{info.max_players} players\n"
                f"🛠️ Version: {getattr(info, 'version', 'Unknown')}\n"
                f"🔐 Password: "
                f"{'Required' if password_required else 'Not required'}\n"
                f"🌍 World: {world_name}\n"
                f"⏱️ Uptime: {uptime}\n"
                f"🗺️ Map: {'Visible' if map_visible else 'Hidden'}"
            )
            title = f"⚔️ {info.server_name}"
        except Exception:
            status_line = "🔴 **Offline / unreachable**"
            title = "⚠️ Valheim Server"

        embed = discord.Embed(title=title, description=status_line)
        embed.add_field(name="🌍 Address", value=f"`{HOST}:{PORT}`", inline=False)
        if self.message is not None:
            await self.message.edit(embed=embed)

    @update_status.before_loop
    async def before_update(self) -> None:
        await self.wait_until_ready()


intents = discord.Intents.none()  # no privileged intents needed
client = ValheimBot(intents=intents)

if __name__ == "__main__":
    # Start a tiny Flask health server for Docker/K8s
    health_host = os.getenv("HEALTH_HOST", "0.0.0.0")
    health_port = int(os.getenv("HEALTH_PORT", "8080"))
    import importlib

    try:
        _health_mod = importlib.import_module("src.health")
    except Exception:
        _health_mod = importlib.import_module("health")

    _health_mod.start_health_server(host=health_host, port=health_port)
    client.run(TOKEN)
