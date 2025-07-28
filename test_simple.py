#!/usr/bin/env python3
"""
Simple test script to verify the new project structure works.
"""

import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    from bot import (
        ADDRESS,
        CHANNEL_ID,
        HOST,
        MESSAGE_ID,
        PORT,
        TOKEN,
        UPDATE_PERIOD,
        ValheimBot,
    )

    print("✅ Import successful!")
    print(f"ADDRESS: {ADDRESS}")
    print(f"HOST: {HOST}")
    print(f"PORT: {PORT}")
    print(f"UPDATE_PERIOD: {UPDATE_PERIOD}")

    # Test bot creation
    import discord

    intents = discord.Intents.none()
    bot = ValheimBot(intents=intents)
    print("✅ Bot creation successful!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc() 