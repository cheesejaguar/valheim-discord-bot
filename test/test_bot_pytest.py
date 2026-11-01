import importlib
import json
import os
import runpy
import socket
import sys
import time
import urllib.request
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import a2s
import discord
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import bot  # noqa: E402
import health  # noqa: E402


@pytest.fixture(autouse=True)
def mock_env():
    """Set environment variables for all tests and reload the bot module."""
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
    # Discord API boundary: the status message lives on Discord's servers.
    instance.message = AsyncMock(spec=discord.Message)
    yield instance
    instance.update_status.cancel()


@pytest.fixture
def a2s_server():
    """
    Stand in for the Valheim server's A2S query endpoint (external network).

    Yields a namespace whose ``info`` and ``rules`` attributes are the mocks
    patched over ``a2s.info`` / ``a2s.rules``.
    """
    with patch.object(a2s, "info") as info, patch.object(a2s, "rules") as rules:
        yield SimpleNamespace(info=info, rules=rules)


def make_info(**overrides):
    """Build an A2S info response shaped like python-a2s' SourceInfo."""
    fields = dict(
        server_name="Test Server",
        map_name="Valheim",
        player_count=5,
        max_players=10,
        version="0.217.46",
        password_protected=False,
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def sent_embed(instance) -> discord.Embed:
    """Return the embed passed to the (single) Discord message edit."""
    instance.message.edit.assert_awaited_once()
    embed = instance.message.edit.await_args.kwargs["embed"]
    assert isinstance(embed, discord.Embed)
    return embed


def assert_address_field(embed: discord.Embed) -> None:
    assert len(embed.fields) == 1
    field = embed.fields[0]
    assert field.name == "🌍 Address"
    assert field.value == "`test.host.com:2457`"
    assert field.inline is False


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def get_json(url: str, timeout: float = 5.0):
    """GET a URL, retrying until the server thread is accepting connections."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:  # noqa: S310
                return resp.status, json.loads(resp.read())
        except OSError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.05)


# ---------------------------------------------------------------- config ----


def test_constants_are_loaded_from_env():
    """Test that constants are correctly loaded from environment variables."""
    assert bot.TOKEN == "test_token"
    assert bot.CHANNEL_ID == 123456789
    assert bot.MESSAGE_ID == 987654321
    assert bot.HOST == "test.host.com"
    assert bot.PORT == 2457
    assert bot.UPDATE_PERIOD == 1
    assert bot.ADDRESS == ("test.host.com", 2457)


def test_constants_strip_inline_comments_and_use_defaults():
    """Inline '# comments' are stripped and unset/empty vars fall back."""
    with patch.dict(
        os.environ,
        {
            "VALHEIM_HOST": "  example.org   # my server",
            "VALHEIM_QUERY_PORT": "2459 # query port",
            "UPDATE_PERIOD": "   # nothing but a comment",
        },
    ):
        os.environ.pop("DISCORD_CHANNEL_ID")
        importlib.reload(bot)
        assert bot.HOST == "example.org"
        assert bot.PORT == 2459
        assert bot.UPDATE_PERIOD == 60
        assert bot.CHANNEL_ID == 0
        assert bot.ADDRESS == ("example.org", 2459)


@pytest.mark.parametrize(
    "value, default, expected",
    [
        (None, "fallback", "fallback"),
        ("", "fallback", "fallback"),
        ("  value  ", "", "value"),
        ("value # comment", "", "value"),
        ("#only a comment", "d", "d"),
    ],
)
def test_clean_env_var(value, default, expected):
    assert bot.clean_env_var(value, default) == expected


def test_bot_instantiation():
    """The module-level client is a ValheimBot with no privileged intents."""
    assert isinstance(bot.client, bot.ValheimBot)
    assert bot.client.intents.value == 0


# -------------------------------------------------------------- on_ready ----


@pytest.mark.asyncio
async def test_on_ready(bot_instance):
    """on_ready fetches the channel and message and starts the update loop."""
    mock_channel = Mock(spec=discord.TextChannel)
    mock_message = AsyncMock(spec=discord.Message)
    mock_channel.fetch_message = AsyncMock(return_value=mock_message)
    bot_instance.fetch_channel = AsyncMock(return_value=mock_channel)

    await bot_instance.on_ready()

    bot_instance.fetch_channel.assert_awaited_once_with(123456789)
    mock_channel.fetch_message.assert_awaited_once_with(987654321)
    assert bot_instance.channel is mock_channel
    assert bot_instance.message is mock_message
    assert bot_instance.update_status.is_running()


@pytest.mark.asyncio
async def test_on_ready_accepts_thread(bot_instance):
    """Threads are valid targets for the status message too."""
    mock_thread = Mock(spec=discord.Thread)
    mock_message = AsyncMock(spec=discord.Message)
    mock_thread.fetch_message = AsyncMock(return_value=mock_message)
    bot_instance.fetch_channel = AsyncMock(return_value=mock_thread)

    await bot_instance.on_ready()

    assert bot_instance.message is mock_message


@pytest.mark.asyncio
async def test_on_ready_invalid_channel(bot_instance, caplog):
    """A non-text channel is logged, no message is fetched, loop still starts."""
    mock_channel = Mock(spec=discord.VoiceChannel)
    bot_instance.fetch_channel = AsyncMock(return_value=mock_channel)

    with caplog.at_level("ERROR"):
        await bot_instance.on_ready()

    assert "Channel 123456789 is not a text channel or thread." in caplog.text
    assert bot_instance.message is None
    assert bot_instance.channel is mock_channel
    mock_channel.fetch_message.assert_not_called()
    assert bot_instance.update_status.is_running()


@pytest.mark.asyncio
async def test_before_update_waits_for_ready(bot_instance):
    """The update loop waits for the gateway connection before polling."""
    bot_instance.wait_until_ready = AsyncMock()

    await bot_instance.before_update()

    bot_instance.wait_until_ready.assert_awaited_once_with()


# --------------------------------------------------------- update_status ----


@pytest.mark.asyncio
async def test_update_status_online(bot_instance, a2s_server):
    """Online server: queries A2S and renders every status line."""
    a2s_server.info.return_value = make_info(password_protected=True)
    a2s_server.rules.return_value = {
        "world_name": "Midgard",
        "uptime": "1h23m",
        "map_enabled": "1",
    }

    await bot_instance.update_status()

    a2s_server.info.assert_called_once_with(("test.host.com", 2457), timeout=3)
    a2s_server.rules.assert_called_once_with(("test.host.com", 2457), timeout=3)
    embed = sent_embed(bot_instance)
    assert embed.title == "⚔️ Test Server"
    assert embed.description == (
        "🟢 **Online**\n"
        "👥 5/10 players\n"
        "🛠️ Version: 0.217.46\n"
        "🔐 Password: Required\n"
        "🌍 World: Midgard\n"
        "⏱️ Uptime: 1h23m\n"
        "🗺️ Map: Visible"
    )
    assert_address_field(embed)


@pytest.mark.asyncio
async def test_update_status_rules_fails(bot_instance, a2s_server):
    """If only the rules query fails, info-derived values and defaults are used."""
    a2s_server.info.return_value = make_info(
        server_name="Test Server Rules-Fail",
        player_count=2,
        version="0.217.47",
        map_name="Valheim",
    )
    a2s_server.rules.side_effect = a2s.BrokenMessageError("bad rules packet")

    await bot_instance.update_status()

    embed = sent_embed(bot_instance)
    assert embed.title == "⚔️ Test Server Rules-Fail"
    assert embed.description == (
        "🟢 **Online**\n"
        "👥 2/10 players\n"
        "🛠️ Version: 0.217.47\n"
        "🔐 Password: Not required\n"
        "🌍 World: Valheim\n"  # Falls back to info.map_name
        "⏱️ Uptime: Unknown\n"  # Falls back to default
        "🗺️ Map: Visible"  # Falls back to default
    )
    assert_address_field(embed)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "rules, info_overrides, expected_lines",
    [
        # "world" is used when "world_name" is absent
        ({"world": "Ashlands"}, {}, ["🌍 World: Ashlands"]),
        # world_name takes priority over world
        ({"world_name": "A", "world": "B"}, {}, ["🌍 World: A"]),
        # no world info anywhere -> Unknown
        ({}, {"map_name": ""}, ["🌍 World: Unknown"]),
        # map hidden via rules, case-insensitive
        ({"map_enabled": "FALSE"}, {}, ["🗺️ Map: Hidden"]),
        ({"map_enabled": 0}, {}, ["🗺️ Map: Hidden"]),
        ({"map_enabled": "Yes"}, {}, ["🗺️ Map: Visible"]),
        # password flagged via rules even if info says unprotected
        ({"password_required": "true"}, {}, ["🔐 Password: Required"]),
        ({"password_required": "0"}, {}, ["🔐 Password: Not required"]),
    ],
)
async def test_update_status_rule_variants(
    bot_instance, a2s_server, rules, info_overrides, expected_lines
):
    """Rule keys drive world name, map visibility and password flag."""
    a2s_server.info.return_value = make_info(**info_overrides)
    a2s_server.rules.return_value = rules

    await bot_instance.update_status()

    lines = sent_embed(bot_instance).description.split("\n")
    for expected in expected_lines:
        assert expected in lines


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "player_count, max_players, players_line",
    [
        (0, 10, "👥 0/10 players"),
        (1, 1, "👥 1/1 players"),
        (10, 10, "👥 10/10 players"),
    ],
)
async def test_update_status_player_counts(
    bot_instance, a2s_server, player_count, max_players, players_line
):
    """Player counts are rendered as current/max."""
    a2s_server.info.return_value = make_info(
        player_count=player_count, max_players=max_players
    )
    a2s_server.rules.return_value = {"world_name": "Midgard", "uptime": "1h23m"}

    await bot_instance.update_status()

    assert sent_embed(bot_instance).description.split("\n")[1] == players_line


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exception",
    [
        ConnectionError("Connection refused"),
        TimeoutError("Request timed out"),
        socket.timeout("timed out"),
        OSError("Network is unreachable"),
        a2s.BrokenMessageError("garbled reply"),
    ],
)
async def test_update_status_offline(bot_instance, a2s_server, exception):
    """Any failure of the info query renders the offline embed."""
    a2s_server.info.side_effect = exception

    await bot_instance.update_status()  # Should not raise

    a2s_server.info.assert_called_once_with(("test.host.com", 2457), timeout=3)
    a2s_server.rules.assert_not_called()
    embed = sent_embed(bot_instance)
    assert embed.title == "⚠️ Valheim Server"
    assert embed.description == "🔴 **Offline / unreachable**"
    assert_address_field(embed)


@pytest.mark.asyncio
async def test_update_status_without_message_does_not_edit(bot_instance, a2s_server):
    """With no status message (invalid channel), polling is a no-op on Discord."""
    a2s_server.info.return_value = make_info()
    a2s_server.rules.return_value = {}
    bot_instance.message = None

    await bot_instance.update_status()  # Should not raise

    a2s_server.info.assert_called_once()


# ----------------------------------------------------------- entrypoint ----


@patch("discord.Client.run")
def test_main_execution(mock_run):
    """
    Running the module as a script starts the health server and calls
    client.run once with the token.
    """
    port = free_port()
    with patch.dict(os.environ, {"HEALTH_HOST": "127.0.0.1", "HEALTH_PORT": str(port)}):
        runpy.run_module("bot", run_name="__main__")

    mock_run.assert_called_once_with("test_token")
    assert get_json(f"http://127.0.0.1:{port}/healthz") == (200, {"status": "ok"})


# ---------------------------------------------------------------- health ----


@pytest.mark.parametrize(
    "path, status",
    [("/healthz", "ok"), ("/readyz", "ready"), ("/livez", "alive")],
)
def test_health_endpoints(path, status):
    response = health.app.test_client().get(path)
    assert response.status_code == 200
    assert response.get_json() == {"status": status}


def test_health_unknown_path_is_404():
    assert health.app.test_client().get("/nope").status_code == 404


def test_start_health_server_serves_requests():
    """start_health_server runs a real server in a daemon thread."""
    port = free_port()

    thread = health.start_health_server(host="127.0.0.1", port=port)

    assert thread.daemon
    assert thread.is_alive()
    assert get_json(f"http://127.0.0.1:{port}/livez") == (200, {"status": "alive"})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
