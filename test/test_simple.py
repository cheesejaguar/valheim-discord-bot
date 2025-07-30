import importlib
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import bot

import runpy


@patch("discord.Client.run")
def test_main_execution(mock_run):
    """Ensure executing the module as a script invokes client.run with the provided token."""

    env = {
        "DISCORD_TOKEN": "test_token",
        "DISCORD_CHANNEL_ID": "123456789",
        "DISCORD_MESSAGE_ID": "987654321",
        "VALHEIM_HOST": "test.host.com",
        "VALHEIM_QUERY_PORT": "2457",
        "UPDATE_PERIOD": "1",
    }

    with patch.dict(os.environ, env, clear=True):
        runpy.run_module("bot", run_name="__main__")

    mock_run.assert_called_once_with("test_token")
