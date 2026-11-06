"""
test_kaggle_command_auth.py — Real Test Containers (Zero Mocks / Evidence Protocol).
==================================================================================
Strict Evidence Protocol:
  - Zero MagicMock / AsyncMock usage.
  - Real lightweight Discord interaction & context state containers.
  - Fail-closed admin check verification on slash commands, prefix commands, and UI views.
"""

from typing import List, Dict, Any, Optional
import asyncio
import pytest
from src.config.unified_config import unified_config
from src.controllers.kaggle_controller import (
    check_admin_auth,
    KaggleController,
    KaggleControlView,
    KaggleActionView,
    KaggleSubmitView,
)


class RealUser:
    def __init__(self, user_id: int):
        self.id = user_id


class RealResponse:
    def __init__(self):
        self.sent_messages: List[Dict[str, Any]] = []
        self.deferred: bool = False
        self._done: bool = False

    def is_done(self) -> bool:
        return self._done

    async def send_message(self, content=None, **kwargs):
        self._done = True
        self.sent_messages.append({"content": content, "kwargs": kwargs})

    async def defer(self, **kwargs):
        self.deferred = True
        self._done = True


class RealFollowup:
    def __init__(self):
        self.sent_messages: List[Dict[str, Any]] = []

    async def send(self, content=None, **kwargs):
        self.sent_messages.append({"content": content, "kwargs": kwargs})


class RealMessage:
    def __init__(self, content=None, **kwargs):
        self.content = content
        self.kwargs = kwargs
        self.edited_payloads: List[Dict[str, Any]] = []

    async def edit(self, **kwargs):
        self.edited_payloads.append(kwargs)


class RealChannel:
    def __init__(self):
        self.sent_messages: List[Dict[str, Any]] = []

    async def send(self, content=None, **kwargs):
        msg = RealMessage(content=content, **kwargs)
        self.sent_messages.append({"content": content, "kwargs": kwargs, "message": msg})
        return msg


class RealInteraction:
    def __init__(self, user_id: int):
        self.user = RealUser(user_id)
        self.response = RealResponse()
        self.followup = RealFollowup()
        self.channel = RealChannel()


class RealContext:
    def __init__(self, user_id: int):
        self.author = RealUser(user_id)
        self.channel = RealChannel()
        self.sent_messages: List[Dict[str, Any]] = []

    async def send(self, content=None, **kwargs):
        msg = RealMessage(content=content, **kwargs)
        self.sent_messages.append({"content": content, "kwargs": kwargs, "message": msg})
        return msg


def test_admin_auth_unset_fails_closed(monkeypatch):
    monkeypatch.setattr(unified_config.discord, "admin_user_id", None)
    interaction = RealInteraction(12345)
    assert check_admin_auth(interaction) is False


def test_non_admin_user_rejected(monkeypatch):
    monkeypatch.setattr(unified_config.discord, "admin_user_id", "12345")
    interaction = RealInteraction(99999)
    assert check_admin_auth(interaction) is False


def test_admin_user_authorized(monkeypatch):
    monkeypatch.setattr(unified_config.discord, "admin_user_id", "12345")
    interaction = RealInteraction(12345)
    assert check_admin_auth(interaction) is True


@pytest.mark.asyncio
async def test_button_view_interaction_check_blocks_non_admin(monkeypatch):
    monkeypatch.setattr(unified_config.discord, "admin_user_id", "12345")
    view = KaggleControlView(competition="name-that-llm")

    non_admin_interaction = RealInteraction(99999)
    allowed = await view.interaction_check(non_admin_interaction)
    assert allowed is False
    assert len(non_admin_interaction.response.sent_messages) == 1
    assert "Pristup odbijen" in non_admin_interaction.response.sent_messages[0]["content"]

    admin_interaction = RealInteraction(12345)
    allowed_admin = await view.interaction_check(admin_interaction)
    assert allowed_admin is True


@pytest.mark.asyncio
async def test_action_view_interaction_check_blocks_non_admin(monkeypatch):
    monkeypatch.setattr(unified_config.discord, "admin_user_id", "12345")
    view = KaggleActionView(competition="name-that-llm", code_path="/tmp/pipeline.py")

    non_admin_interaction = RealInteraction(99999)
    allowed = await view.interaction_check(non_admin_interaction)
    assert allowed is False
    assert len(non_admin_interaction.response.sent_messages) == 1
    assert "Pristup odbijen" in non_admin_interaction.response.sent_messages[0]["content"]

    admin_interaction = RealInteraction(12345)
    allowed_admin = await view.interaction_check(admin_interaction)
    assert allowed_admin is True


@pytest.mark.asyncio
async def test_submit_view_interaction_check_blocks_non_admin(monkeypatch):
    monkeypatch.setattr(unified_config.discord, "admin_user_id", "12345")
    view = KaggleSubmitView(
        competition="name-that-llm",
        kernel_slug="ntl-test",
        submission_path="/tmp/submission.parquet",
    )

    non_admin_interaction = RealInteraction(99999)
    allowed = await view.interaction_check(non_admin_interaction)
    assert allowed is False
    assert len(non_admin_interaction.response.sent_messages) == 1
    assert "Pristup odbijen" in non_admin_interaction.response.sent_messages[0]["content"]

    admin_interaction = RealInteraction(12345)
    allowed_admin = await view.interaction_check(admin_interaction)
    assert allowed_admin is True


@pytest.mark.asyncio
async def test_handle_kaggle_start_rejects_malicious_slug(monkeypatch):
    monkeypatch.setattr(unified_config.discord, "admin_user_id", "12345")
    controller = KaggleController()
    interaction = RealInteraction(12345)

    await controller.handle_kaggle_start(interaction, "comp; rm -rf /")
    assert len(interaction.response.sent_messages) == 1
    assert "Nevalidan naziv takmičenja" in interaction.response.sent_messages[0]["content"]


@pytest.mark.asyncio
async def test_handle_kaggle_start_rejects_non_admin(monkeypatch):
    monkeypatch.setattr(unified_config.discord, "admin_user_id", "12345")
    controller = KaggleController()
    interaction = RealInteraction(99999)

    await controller.handle_kaggle_start(interaction, "name-that-llm")
    assert len(interaction.response.sent_messages) == 1
    assert "Pristup odbijen" in interaction.response.sent_messages[0]["content"]


@pytest.mark.asyncio
async def test_handle_kaggle_start_admin_success_with_telemetry(monkeypatch):
    monkeypatch.setattr(unified_config.discord, "admin_user_id", "12345")
    controller = KaggleController()
    interaction = RealInteraction(12345)

    recorded_dispatches = []

    async def record_dispatch(channel, comp):
        recorded_dispatches.append((channel, comp))

    monkeypatch.setattr(controller, "_run_debate_task", record_dispatch)

    await controller.handle_kaggle_start(interaction, "name-that-llm")
    await asyncio.sleep(0.05)
    assert interaction.response.deferred is True
    assert len(interaction.followup.sent_messages) == 1

    embed = interaction.followup.sent_messages[0]["kwargs"]["embed"]
    assert "name-that-llm" in embed.title
    assert "0.604" in embed.description or "Kaggle Telemetrija" in embed.description
    assert len(recorded_dispatches) == 1
    assert recorded_dispatches[0][1] == "name-that-llm"


@pytest.mark.asyncio
async def test_handle_kaggle_start_prefix_rejects_non_admin(monkeypatch):
    monkeypatch.setattr(unified_config.discord, "admin_user_id", "12345")
    controller = KaggleController()
    ctx = RealContext(99999)

    await controller.handle_kaggle_start_prefix(ctx, "name-that-llm")
    assert len(ctx.sent_messages) == 1
    assert "Pristup odbijen" in ctx.sent_messages[0]["content"]


@pytest.mark.asyncio
async def test_handle_kaggle_start_prefix_admin_success(monkeypatch):
    monkeypatch.setattr(unified_config.discord, "admin_user_id", "12345")
    controller = KaggleController()
    ctx = RealContext(12345)

    recorded_dispatches = []

    async def record_dispatch(channel, comp):
        recorded_dispatches.append((channel, comp))

    monkeypatch.setattr(controller, "_run_debate_task", record_dispatch)

    await controller.handle_kaggle_start_prefix(ctx, "name-that-llm")
    await asyncio.sleep(0.05)
    assert len(ctx.sent_messages) >= 1

    status_msg = ctx.sent_messages[0]["message"]
    assert len(status_msg.edited_payloads) == 1
    embed = status_msg.edited_payloads[0]["embed"]
    assert "name-that-llm" in embed.title
    assert len(recorded_dispatches) == 1
    assert recorded_dispatches[0][1] == "name-that-llm"
