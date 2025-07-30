import asyncio
import importlib
import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import a2s
import discord
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import bot


@pytest.fixture(autouse=True)
def mock_env():
    """Mock environment variables for all tests."""
    with patch.dict(
        os.environ,
        {
            "DISCORD_TOKEN": "test_token",
            "DISCORD_CHANNEL_ID": "123456789",
            "DISCORD_MESSAGE_ID": "987654321",
            "VALHEIM_HOST": "test.host.com",
            "VALHEIM_QUERY_PORT": "2457",
            "UPDATE_PERIOD": "1",  # Faster for testing
        },
    ):
        importlib.reload(bot)
        yield


@pytest.fixture
def bot_instance():
    """Create a bot instance for testing."""
    intents = discord.Intents.none()
    instance = bot.ValheimBot(intents=intents)
    if hasattr(instance, "update_status"):
        instance.update_status.cancel()
    return instance


def test_constants_are_loaded_from_env():
    """Test that constants are correctly loaded from environment variables."""
    assert bot.TOKEN == "test_token"
    assert bot.CHANNEL_ID == 123456789
    assert bot.MESSAGE_ID == 987654321
    assert bot.HOST == "test.host.com"
    assert bot.PORT == 2457
    assert bot.UPDATE_PERIOD == 1
    assert bot.ADDRESS == ("test.host.com", 2457)


@patch("discord.Client")
def test_bot_instantiation(mock_client):
    """Test that the ValheimBot is instantiated with the correct intents."""
    assert isinstance(bot.client, bot.ValheimBot)
    assert bot.client.intents.value == 0


@pytest.mark.asyncio
async def test_on_ready(bot_instance):
    """Test the on_ready method sets up the bot correctly."""
    bot_instance.fetch_channel = AsyncMock()
    mock_channel = AsyncMock()
    mock_message = AsyncMock()
    bot_instance.fetch_channel.return_value = mock_channel
    mock_channel.fetch_message = AsyncMock(return_value=mock_message)
    bot_instance.update_status = Mock()
    bot_instance.update_status.start = Mock()

    await bot_instance.on_ready()

    bot_instance.fetch_channel.assert_called_once_with(bot.CHANNEL_ID)
    mock_channel.fetch_message.assert_called_once_with(bot.MESSAGE_ID)
    assert bot_instance.channel == mock_channel
    assert bot_instance.message == mock_message
    bot_instance.update_status.start.assert_called_once()


@pytest.mark.asyncio
@patch("asyncio.to_thread")
@patch("discord.Embed")
async def test_update_status_online(mock_embed, mock_to_thread, bot_instance):
    """Test update_status when the server is online."""
    mock_info = Mock(player_count=5, max_players=10)
    mock_to_thread.return_value = mock_info
    mock_embed_instance = Mock()
    mock_embed.return_value = mock_embed_instance
    bot_instance.message = AsyncMock()

    await bot_instance.update_status()

    mock_to_thread.assert_called_once_with(a2s.info, bot.ADDRESS, timeout=3)
    mock_embed.assert_called_once()
    assert "🟢 **Online** – 5/10 players" in mock_embed.call_args.kwargs["description"]
    bot_instance.message.edit.assert_called_once_with(embed=mock_embed_instance)


@pytest.mark.asyncio
@patch("asyncio.to_thread")
@patch("discord.Embed")
async def test_update_status_offline(mock_embed, mock_to_thread, bot_instance):
    """Test update_status when the server is offline."""
    mock_to_thread.side_effect = Exception("Connection failed")
    mock_embed_instance = Mock()
    mock_embed.return_value = mock_embed_instance
    bot_instance.message = AsyncMock()

    await bot_instance.update_status()

    mock_to_thread.assert_called_once_with(a2s.info, bot.ADDRESS, timeout=3)
    mock_embed.assert_called_once()
    assert "🔴 **Offline / unreachable**" in mock_embed.call_args.kwargs["description"]
    bot_instance.message.edit.assert_called_once_with(embed=mock_embed_instance)


@pytest.mark.asyncio
async def test_before_update(bot_instance):
    """Test the before_update method."""
    bot_instance.wait_until_ready = AsyncMock()

    await bot_instance.before_update()

    bot_instance.wait_until_ready.assert_called_once()


@pytest.mark.asyncio
@patch("asyncio.to_thread")
@patch("discord.Embed")
@pytest.mark.parametrize(
    "player_count, max_players, expected_status",
    [
        (0, 10, "🟢 **Online** – 0/10 players"),
        (1, 1, "🟢 **Online** – 1/1 players"),
        (10, 10, "🟢 **Online** – 10/10 players"),
    ],
)
async def test_update_status_player_counts(
    mock_embed,
    mock_to_thread,
    bot_instance,
    player_count,
    max_players,
    expected_status,
):
    """Test update_status with various player counts."""
    mock_info = Mock(player_count=player_count, max_players=max_players)
    mock_to_thread.return_value = mock_info
    bot_instance.message = AsyncMock()
    mock_embed_instance = Mock()
    mock_embed.return_value = mock_embed_instance

    await bot_instance.update_status()

    mock_to_thread.assert_called_once_with(a2s.info, bot.ADDRESS, timeout=3)
    mock_embed.assert_called_once()
    assert expected_status in mock_embed.call_args.kwargs["description"]
    bot_instance.message.edit.assert_called_once_with(embed=mock_embed_instance)


@pytest.mark.asyncio
@patch("asyncio.to_thread")
@patch("discord.Embed")
@pytest.mark.parametrize(
    "exception",
    [
        ConnectionError("Connection refused"),
        TimeoutError("Request timed out"),
        OSError("Network is unreachable"),
        Exception("An unknown error occurred"),
    ],
)
async def test_update_status_exception_handling(
    mock_embed, mock_to_thread, bot_instance, exception
):
    """Test that update_status handles various exceptions gracefully."""
    mock_to_thread.side_effect = exception
    bot_instance.message = AsyncMock()
    mock_embed_instance = Mock()
    mock_embed.return_value = mock_embed_instance

    await bot_instance.update_status()  # Should not raise

    mock_to_thread.assert_called_once_with(a2s.info, bot.ADDRESS, timeout=3)
    mock_embed.assert_called_once()
    assert "🔴 **Offline / unreachable**" in mock_embed.call_args.kwargs["description"]
    bot_instance.message.edit.assert_called_once_with(embed=mock_embed_instance)


import runpy


@patch("discord.Client.run")
def test_main_execution(mock_run):
    """Running the module as a script should call client.run once with the token."""

    # Ensure environment has a token so the code path executes.
    with patch.dict(os.environ, {"DISCORD_TOKEN": "test_token"}):
        # Execute the module as __main__ (fresh namespace) – this simulates
        # `python -m bot` and triggers the bottom-of-file client.run call.
        runpy.run_module("bot", run_name="__main__")

    mock_run.assert_called_once_with("test_token")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
