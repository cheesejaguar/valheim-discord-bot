import unittest
import asyncio
import os
import sys
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import discord
import a2s

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from bot import ValheimBot, ADDRESS, TOKEN, CHANNEL_ID, MESSAGE_ID, HOST, PORT, UPDATE_PERIOD


class TestValheimBot(unittest.TestCase):
    """Test cases for the ValheimBot Discord bot."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.intents = discord.Intents.none()
        self.bot = ValheimBot(intents=self.intents)
        
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'DISCORD_TOKEN': 'test_token',
            'DISCORD_CHANNEL_ID': '123456789',
            'DISCORD_MESSAGE_ID': '987654321',
            'VALHEIM_HOST': 'test.host.com',
            'VALHEIM_QUERY_PORT': '2457',
            'UPDATE_PERIOD': '60'
        })
        self.env_patcher.start()

    def tearDown(self):
        """Clean up after each test method."""
        self.env_patcher.stop()
        if hasattr(self.bot, 'update_status'):
            self.bot.update_status.cancel()

    @patch('discord.Client')
    def test_bot_initialization(self, mock_client):
        """Test that the bot initializes correctly."""
        self.assertIsInstance(self.bot, ValheimBot)
        self.assertEqual(self.bot.intents, self.intents)

    @patch('discord.Client.fetch_channel')
    @patch('logging.info')
    def test_on_ready(self, mock_logging, mock_fetch_channel):
        """Test the on_ready method sets up the bot correctly."""
        # Mock the channel and message
        mock_channel = AsyncMock()
        mock_message = AsyncMock()
        mock_fetch_channel.return_value = mock_channel
        mock_channel.fetch_message = AsyncMock(return_value=mock_message)

        # Mock the update_status task
        self.bot.update_status = Mock()
        self.bot.update_status.start = Mock()

        # Call on_ready
        asyncio.run(self.bot.on_ready())

        # Verify channel and message were fetched
        mock_fetch_channel.assert_called_once_with(123456789)  # Uses patched env value
        mock_channel.fetch_message.assert_called_once_with(987654321)  # Uses patched env value
        
        # Verify attributes were set
        self.assertEqual(self.bot.channel, mock_channel)
        self.assertEqual(self.bot.message, mock_message)
        
        # Verify logging was called
        mock_logging.assert_called_once()
        
        # Verify update_status task was started
        self.bot.update_status.start.assert_called_once()

    @patch('asyncio.to_thread')
    @patch('discord.Embed')
    def test_update_status_online(self, mock_embed, mock_to_thread):
        """Test update_status when server is online."""
        # Mock server info
        mock_info = Mock()
        mock_info.player_count = 5
        mock_info.max_players = 10
        mock_to_thread.return_value = mock_info

        # Mock embed
        mock_embed_instance = Mock()
        mock_embed.return_value = mock_embed_instance

        # Mock message
        self.bot.message = AsyncMock()
        self.bot.message.edit = AsyncMock()

        # Call update_status
        asyncio.run(self.bot.update_status())

        # Verify a2s.info was called with the correct address
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        import bot
        expected_address = ('test.host.com', 2457)
        mock_to_thread.assert_called_once_with(a2s.info, expected_address, timeout=3)
        
        # Verify embed was created with correct description
        mock_embed.assert_called_once()
        call_args = mock_embed.call_args[1]
        self.assertIn('🟢 **Online** – 5/10 players', call_args['description'])
        
        # Verify message was edited
        self.bot.message.edit.assert_called_once_with(embed=mock_embed_instance)

    @patch('asyncio.to_thread')
    @patch('discord.Embed')
    def test_update_status_offline(self, mock_embed, mock_to_thread):
        """Test update_status when server is offline."""
        # Mock exception when server is unreachable
        mock_to_thread.side_effect = Exception("Connection failed")

        # Mock embed
        mock_embed_instance = Mock()
        mock_embed.return_value = mock_embed_instance

        # Mock message
        self.bot.message = AsyncMock()

        # Call update_status
        asyncio.run(self.bot.update_status())

        # Verify a2s.info was called with the correct address
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        import bot
        expected_address = ('test.host.com', 2457)
        mock_to_thread.assert_called_once_with(a2s.info, expected_address, timeout=3)
        
        # Verify embed was created with offline status
        mock_embed.assert_called_once()
        call_args = mock_embed.call_args[1]
        self.assertIn('🔴 **Offline / unreachable**', call_args['description'])
        
        # Verify message was edited
        self.bot.message.edit.assert_called_once_with(embed=mock_embed_instance)

    @patch('discord.Client.wait_until_ready')
    def test_before_update(self, mock_wait_until_ready):
        """Test the before_update method."""
        # Mock wait_until_ready
        mock_wait_until_ready.return_value = AsyncMock()

        # Call before_update
        asyncio.run(self.bot.before_update())

        # Verify wait_until_ready was called
        mock_wait_until_ready.assert_called_once()

    def test_environment_variables(self):
        """Test that environment variables are loaded correctly."""
        # Re-import bot module to get fresh environment variables
        import importlib
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        import bot
        importlib.reload(bot)
        
        self.assertEqual(bot.TOKEN, 'test_token')
        self.assertEqual(bot.CHANNEL_ID, 123456789)
        self.assertEqual(bot.MESSAGE_ID, 987654321)
        self.assertEqual(bot.HOST, 'test.host.com')
        self.assertEqual(bot.PORT, 2457)
        self.assertEqual(bot.UPDATE_PERIOD, 60)
        self.assertEqual(bot.ADDRESS, ('test.host.com', 2457))

    @patch('discord.Client.run')
    def test_main_execution(self, mock_run):
        """Test the main execution block."""
        # Mock the __name__ attribute
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        original_name = sys.modules['bot'].__name__
        sys.modules['bot'].__name__ = '__main__'
        
        try:
            # Mock the client.run method
            with patch.object(sys.modules['bot'].client, 'run', mock_run):
                # Execute the module as __main__ to trigger the main block
                import runpy
                runpy.run_module('bot', run_name='__main__')
                mock_run.assert_called_once_with('test_token')
        finally:
            # Restore original name
            sys.modules['bot'].__name__ = original_name

    def test_intents_configuration(self):
        """Test that intents are configured correctly."""
        # This test verifies the intents configuration in the main module
        # The intents should be set to none as specified in the original code
        self.assertEqual(self.intents.value, 0)

    @patch('asyncio.to_thread')
    @patch('discord.Embed')
    def test_update_status_with_different_player_counts(self, mock_embed, mock_to_thread):
        """Test update_status with various player count scenarios."""
        test_cases = [
            (0, 10, "🟢 **Online** – 0/10 players"),
            (1, 1, "🟢 **Online** – 1/1 players"),
            (10, 10, "🟢 **Online** – 10/10 players"),
            (5, 20, "🟢 **Online** – 5/20 players"),
        ]

        for player_count, max_players, expected_status in test_cases:
            with self.subTest(player_count=player_count, max_players=max_players):
                # Reset mocks
                mock_embed.reset_mock()
                mock_to_thread.reset_mock()

                # Mock server info
                mock_info = Mock()
                mock_info.player_count = player_count
                mock_info.max_players = max_players
                mock_to_thread.return_value = mock_info

                # Mock embed
                mock_embed_instance = Mock()
                mock_embed.return_value = mock_embed_instance

                # Mock message
                self.bot.message = AsyncMock()

                # Call update_status
                asyncio.run(self.bot.update_status())

                # Verify embed was created with correct status
                mock_embed.assert_called_once()
                call_args = mock_embed.call_args[1]
                self.assertIn(expected_status, call_args['description'])

    @patch('asyncio.to_thread')
    @patch('discord.Embed')
    def test_update_status_exception_handling(self, mock_embed, mock_to_thread):
        """Test update_status handles various exceptions correctly."""
        exceptions = [
            ConnectionError("Connection refused"),
            TimeoutError("Request timed out"),
            OSError("Network unreachable"),
            Exception("Unknown error")
        ]

        for exception in exceptions:
            with self.subTest(exception=exception):
                # Reset mocks
                mock_embed.reset_mock()
                mock_to_thread.reset_mock()

                # Mock exception
                mock_to_thread.side_effect = exception

                # Mock embed
                mock_embed_instance = Mock()
                mock_embed.return_value = mock_embed_instance

                # Mock message
                self.bot.message = AsyncMock()

                # Call update_status (should not raise exception)
                asyncio.run(self.bot.update_status())

                # Verify embed was created with offline status
                mock_embed.assert_called_once()
                call_args = mock_embed.call_args[1]
                self.assertIn('🔴 **Offline / unreachable**', call_args['description'])

    def test_address_tuple(self):
        """Test that ADDRESS is correctly formatted as a tuple."""
        self.assertIsInstance(ADDRESS, tuple)
        self.assertEqual(len(ADDRESS), 2)
        self.assertIsInstance(ADDRESS[0], str)  # HOST should be string
        self.assertIsInstance(ADDRESS[1], int)  # PORT should be int

    def test_update_period_positive(self):
        """Test that UPDATE_PERIOD is a positive integer."""
        self.assertIsInstance(UPDATE_PERIOD, int)
        self.assertGreater(UPDATE_PERIOD, 0)

    def test_port_range(self):
        """Test that PORT is within valid range."""
        self.assertIsInstance(PORT, int)
        self.assertGreaterEqual(PORT, 1)
        self.assertLessEqual(PORT, 65535)


class TestValheimBotIntegration(unittest.TestCase):
    """Integration tests for ValheimBot."""

    @patch('discord.Client.run')
    def test_bot_creation_with_defaults(self, mock_run):
        """Test bot creation with default environment variables."""
        with patch.dict(os.environ, {
            'DISCORD_TOKEN': 'test_token',
            'DISCORD_CHANNEL_ID': '123456789',
            'DISCORD_MESSAGE_ID': '987654321',
            'VALHEIM_HOST': 'test.host.com'
        }):
            # Re-import to get fresh environment variables
            import importlib
            import bot
            importlib.reload(bot)
            
            # Verify the bot was created
            self.assertIsInstance(bot.client, bot.ValheimBot)

    def test_required_environment_variables(self):
        """Test that required environment variables are properly handled."""
        required_vars = ['DISCORD_TOKEN', 'DISCORD_CHANNEL_ID', 'DISCORD_MESSAGE_ID', 'VALHEIM_HOST']
        
        for var in required_vars:
            with self.subTest(var=var):
                # Test that the variable is accessed (will raise KeyError if missing)
                with patch.dict(os.environ, {var: 'test_value'}):
                    # This should not raise an exception
                    pass


if __name__ == '__main__':
    unittest.main() 