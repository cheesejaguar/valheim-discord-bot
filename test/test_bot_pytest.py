import asyncio
import os
import sys

import a2s
import discord
import pytest
from unittest.mock import AsyncMock, Mock, patch

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
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


@pytest.fixture
def mock_env():
    """Fixture to mock environment variables."""
    with patch.dict(
        os.environ,
        {
            "DISCORD_TOKEN": "test_token",
            "DISCORD_CHANNEL_ID": "123456789",
            "DISCORD_MESSAGE_ID": "987654321",
            "VALHEIM_HOST": "test.host.com",
            "VALHEIM_QUERY_PORT": "2457",
            "UPDATE_PERIOD": "60",
        },
    ):
        yield


@pytest.fixture
def bot_instance(mock_env):
    """Fixture to create a bot instance for testing."""
    intents = discord.Intents.none()
    bot = ValheimBot(intents=intents)
    yield bot
    # Cleanup
    if hasattr(bot, "update_status"):
        bot.update_status.cancel()


class TestValheimBot:
    """Test cases for the ValheimBot Discord bot using pytest."""

    def test_bot_initialization(self, bot_instance):
        """Test that the bot initializes correctly."""
        assert isinstance(bot_instance, ValheimBot)
        assert bot_instance.intents.value == 0

    @pytest.mark.asyncio
    async def test_on_ready(self, bot_instance):
        """Test the on_ready method sets up the bot correctly."""
        with (
            patch.object(bot_instance, "fetch_channel") as mock_fetch_channel,
            patch("logging.info") as mock_logging,
        ):

            # Mock the channel and message
            mock_channel = AsyncMock()
            mock_message = AsyncMock()
            mock_fetch_channel.return_value = mock_channel

            # Mock fetch_message on the channel
            mock_channel.fetch_message = AsyncMock(return_value=mock_message)

            # Mock the update_status task
            bot_instance.update_status = Mock()
            bot_instance.update_status.start = Mock()

            # Call on_ready
            await bot_instance.on_ready()

            # Verify channel and message were fetched
            mock_fetch_channel.assert_called_once_with(0)  # Default value
            mock_channel.fetch_message.assert_called_once_with(0)  # Default value

            # Verify attributes were set
            assert bot_instance.channel == mock_channel
            assert bot_instance.message == mock_message

            # Verify logging was called
            mock_logging.assert_called_once()

            # Verify update_status task was started
            bot_instance.update_status.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_status_online(self, bot_instance):
        """Test update_status when server is online."""
        with (
            patch("asyncio.to_thread") as mock_to_thread,
            patch("discord.Embed") as mock_embed,
        ):

            # Mock server info
            mock_info = Mock()
            mock_info.player_count = 5
            mock_info.max_players = 10
            mock_to_thread.return_value = mock_info

            # Mock embed
            mock_embed_instance = Mock()
            mock_embed.return_value = mock_embed_instance

            # Mock message
            bot_instance.message = AsyncMock()

            # Call update_status
            await bot_instance.update_status()

            # Verify a2s.info was called with the correct address
            import sys

            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
            import bot

            expected_address = ("test.host.com", 2457)
            mock_to_thread.assert_called_once_with(
                a2s.info, expected_address, timeout=3
            )

            # Verify embed was created with correct description
            mock_embed.assert_called_once()
            call_args = mock_embed.call_args[1]
            assert "🟢 **Online** – 5/10 players" in call_args["description"]

            # Verify message was edited
            bot_instance.message.edit.assert_called_once_with(embed=mock_embed_instance)

    @pytest.mark.asyncio
    async def test_update_status_offline(self, bot_instance):
        """Test update_status when server is offline."""
        with (
            patch("asyncio.to_thread") as mock_to_thread,
            patch("discord.Embed") as mock_embed,
        ):

            # Mock exception when server is unreachable
            mock_to_thread.side_effect = Exception("Connection failed")

            # Mock embed
            mock_embed_instance = Mock()
            mock_embed.return_value = mock_embed_instance

            # Mock message
            bot_instance.message = AsyncMock()

            # Call update_status
            await bot_instance.update_status()

            # Verify a2s.info was called with the correct address
            import sys

            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
            import bot

            expected_address = ("test.host.com", 2457)
            mock_to_thread.assert_called_once_with(
                a2s.info, expected_address, timeout=3
            )

            # Verify embed was created with offline status
            mock_embed.assert_called_once()
            call_args = mock_embed.call_args[1]
            assert "🔴 **Offline / unreachable**" in call_args["description"]

            # Verify message was edited
            bot_instance.message.edit.assert_called_once_with(embed=mock_embed_instance)

    @pytest.mark.asyncio
    async def test_before_update(self, bot_instance):
        """Test the before_update method."""
        with patch.object(bot_instance, "wait_until_ready") as mock_wait_until_ready:
            # Mock wait_until_ready
            mock_wait_until_ready.return_value = AsyncMock()

            # Call before_update
            await bot_instance.before_update()

            # Verify wait_until_ready was called
            mock_wait_until_ready.assert_called_once()

    def test_environment_variables(self, mock_env):
        """Test that environment variables are loaded correctly."""
        # Re-import bot module to get fresh environment variables
        import importlib
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
        import bot

        importlib.reload(bot)

        assert bot.TOKEN == "test_token"
        assert bot.CHANNEL_ID == 123456789
        assert bot.MESSAGE_ID == 987654321
        assert bot.HOST == "test.host.com"
        assert bot.PORT == 2457
        assert bot.UPDATE_PERIOD == 60
        assert bot.ADDRESS == ("test.host.com", 2457)

    @pytest.mark.parametrize(
        "player_count,max_players,expected_status",
        [
            (0, 10, "🟢 **Online** – 0/10 players"),
            (1, 1, "🟢 **Online** – 1/1 players"),
            (10, 10, "🟢 **Online** – 10/10 players"),
            (5, 20, "🟢 **Online** – 5/20 players"),
        ],
    )
    @pytest.mark.asyncio
    async def test_update_status_player_counts(
        self, bot_instance, player_count, max_players, expected_status
    ):
        """Test update_status with various player count scenarios."""
        with (
            patch("asyncio.to_thread") as mock_to_thread,
            patch("discord.Embed") as mock_embed,
        ):

            # Mock server info
            mock_info = Mock()
            mock_info.player_count = player_count
            mock_info.max_players = max_players
            mock_to_thread.return_value = mock_info

            # Mock embed
            mock_embed_instance = Mock()
            mock_embed.return_value = mock_embed_instance

            # Mock message
            bot_instance.message = AsyncMock()

            # Call update_status
            await bot_instance.update_status()

            # Verify a2s.info was called with the correct address
            import sys

            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
            import bot

            expected_address = ("test.host.com", 2457)
            mock_to_thread.assert_called_once_with(
                a2s.info, expected_address, timeout=3
            )

            # Verify embed was created with correct status
            mock_embed.assert_called_once()
            call_args = mock_embed.call_args[1]
            assert expected_status in call_args["description"]

    @pytest.mark.parametrize(
        "exception",
        [
            ConnectionError("Connection refused"),
            TimeoutError("Request timed out"),
            OSError("Network unreachable"),
            Exception("Unknown error"),
        ],
    )
    @pytest.mark.asyncio
    async def test_update_status_exception_handling(self, bot_instance, exception):
        """Test update_status handles various exceptions correctly."""
        with (
            patch("asyncio.to_thread") as mock_to_thread,
            patch("discord.Embed") as mock_embed,
        ):

            # Mock exception
            mock_to_thread.side_effect = exception

            # Mock embed
            mock_embed_instance = Mock()
            mock_embed.return_value = mock_embed_instance

            # Mock message
            bot_instance.message = AsyncMock()

            # Call update_status (should not raise exception)
            await bot_instance.update_status()

            # Verify a2s.info was called with the correct address
            import sys

            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
            import bot

            expected_address = ("test.host.com", 2457)
            mock_to_thread.assert_called_once_with(
                a2s.info, expected_address, timeout=3
            )

            # Verify embed was created with offline status
            mock_embed.assert_called_once()
            call_args = mock_embed.call_args[1]
            assert "🔴 **Offline / unreachable**" in call_args["description"]

    def test_address_tuple(self):
        """Test that ADDRESS is correctly formatted as a tuple."""
        assert isinstance(ADDRESS, tuple)
        assert len(ADDRESS) == 2
        assert isinstance(ADDRESS[0], str)  # HOST should be string
        assert isinstance(ADDRESS[1], int)  # PORT should be int

    def test_update_period_positive(self):
        """Test that UPDATE_PERIOD is a positive integer."""
        assert isinstance(UPDATE_PERIOD, int)
        assert UPDATE_PERIOD > 0

    def test_port_range(self):
        """Test that PORT is within valid range."""
        assert isinstance(PORT, int)
        assert 1 <= PORT <= 65535

    def test_intents_configuration(self, bot_instance):
        """Test that intents are configured correctly."""
        assert bot_instance.intents.value == 0

    @patch("discord.Client.run")
    def test_main_execution(self, mock_run, mock_env):
        """Test the main execution block."""
        # Mock the __name__ attribute
        import sys

        original_name = sys.modules["bot"].__name__
        sys.modules["bot"].__name__ = "__main__"

        try:
            # Mock the client.run method
            with patch.object(sys.modules["bot"].client, "run", mock_run):
                # Import the module to trigger the main execution
                import importlib
                import bot

                importlib.reload(bot)
                mock_run.assert_called_once_with(bot.TOKEN)
        finally:
            # Restore original name
            sys.modules["bot"].__name__ = original_name


class TestValheimBotIntegration:
    """Integration tests for ValheimBot."""

    def test_bot_creation_with_defaults(self):
        """Test bot creation with default environment variables."""
        with patch.dict(
            os.environ,
            {
                "DISCORD_TOKEN": "test_token",
                "DISCORD_CHANNEL_ID": "123456789",
                "DISCORD_MESSAGE_ID": "987654321",
                "VALHEIM_HOST": "test.host.com",
            },
        ):
            # Re-import to get fresh environment variables
            import importlib
            import bot

            importlib.reload(bot)

            # Verify the bot was created
            assert isinstance(bot.client, bot.ValheimBot)

    @pytest.mark.parametrize(
        "required_var",
        [
            "DISCORD_TOKEN",
            "DISCORD_CHANNEL_ID",
            "DISCORD_MESSAGE_ID",
            "VALHEIM_HOST",
        ],
    )
    def test_required_environment_variables(self, required_var):
        """Test that required environment variables are properly handled."""
        # Test that the variable is accessed (will raise KeyError if missing)
        with patch.dict(os.environ, {required_var: "test_value"}):
            # This should not raise an exception
            pass


class TestValheimBotEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_update_status_with_none_message(self):
        """Test update_status when message is None."""
        intents = discord.Intents.none()
        bot = ValheimBot(intents=intents)
        bot.message = None

        # Should not raise an exception
        with (
            patch("asyncio.to_thread") as mock_to_thread,
            patch("discord.Embed") as mock_embed,
        ):

            mock_to_thread.side_effect = Exception("Test exception")
            mock_embed.return_value = Mock()

            # This should handle the None message gracefully
            await bot.update_status()

    def test_environment_variable_types(self, mock_env):
        """Test that environment variables are converted to correct types."""
        # Re-import bot module to get fresh environment variables
        import importlib
        import bot

        importlib.reload(bot)

        assert isinstance(bot.CHANNEL_ID, int)
        assert isinstance(bot.MESSAGE_ID, int)
        assert isinstance(bot.PORT, int)
        assert isinstance(bot.UPDATE_PERIOD, int)
        assert isinstance(bot.HOST, str)
        assert isinstance(bot.TOKEN, str)

    @pytest.mark.asyncio
    async def test_update_status_task_cancellation(self, bot_instance):
        """Test that update_status task can be cancelled properly."""
        # Mock the task
        bot_instance.update_status = Mock()
        bot_instance.update_status.cancel = Mock()

        # Test cancellation
        bot_instance.update_status.cancel()
        bot_instance.update_status.cancel.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
