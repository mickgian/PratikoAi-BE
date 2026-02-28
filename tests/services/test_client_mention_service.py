"""Tests for DEV-403: @client Mention System with Autocomplete."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.client_mention_service import ClientAction, ClientMentionService


@pytest.fixture
def service():
    return ClientMentionService()


@pytest.fixture
def studio_id():
    return uuid4()


@pytest.fixture
def mock_db():
    return AsyncMock()


class TestExtractMentions:
    """Tests for @mention extraction."""

    def test_single_mention(self, service):
        mentions = service.extract_mentions("Ciao @Mario come stai?")
        assert mentions == ["Mario"]

    def test_quoted_mention(self, service):
        mentions = service.extract_mentions('Info su @"Mario Rossi" per favore')
        assert mentions == ["Mario Rossi"]

    def test_multiple_mentions(self, service):
        mentions = service.extract_mentions("@Mario e @Luigi sono clienti")
        assert mentions == ["Mario", "Luigi"]

    def test_no_mentions(self, service):
        mentions = service.extract_mentions("Nessun mention qui")
        assert mentions == []

    def test_empty_text(self, service):
        mentions = service.extract_mentions("")
        assert mentions == []

    def test_mixed_quoted_unquoted(self, service):
        mentions = service.extract_mentions('@"Mario Rossi" e @Luigi')
        assert mentions == ["Mario Rossi", "Luigi"]


class TestAutocomplete:
    """Tests for client name autocomplete."""

    @pytest.mark.asyncio
    async def test_autocomplete_returns_results(self, service, mock_db, studio_id):
        mock_client = MagicMock()
        mock_client.id = 1
        mock_client.nome = "Mario Rossi"
        mock_client.tipo_cliente = "persona_fisica"
        mock_client.codice_fiscale = "RSSMRA80A01H501U"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_client]
        mock_db.execute.return_value = mock_result

        results = await service.autocomplete(mock_db, studio_id=studio_id, prefix="Mar")

        assert len(results) == 1
        assert results[0]["nome"] == "Mario Rossi"
        assert results[0]["id"] == 1

    @pytest.mark.asyncio
    async def test_autocomplete_short_prefix_returns_empty(self, service, mock_db, studio_id):
        """Prefix < 2 chars returns empty (debounce protection)."""
        results = await service.autocomplete(mock_db, studio_id=studio_id, prefix="M")
        assert results == []

    @pytest.mark.asyncio
    async def test_autocomplete_empty_prefix_returns_empty(self, service, mock_db, studio_id):
        results = await service.autocomplete(mock_db, studio_id=studio_id, prefix="")
        assert results == []


class TestResolveMention:
    """Tests for resolving @mentions to Client records."""

    @pytest.mark.asyncio
    async def test_resolve_found(self, service, mock_db, studio_id):
        mock_client = MagicMock()
        mock_client.id = 1
        mock_client.nome = "Mario Rossi"

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_client
        mock_db.execute.return_value = mock_result

        client = await service.resolve_mention(mock_db, studio_id=studio_id, client_name="Mario Rossi")
        assert client is not None
        assert client.id == 1

    @pytest.mark.asyncio
    async def test_resolve_not_found(self, service, mock_db, studio_id):
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_result

        client = await service.resolve_mention(mock_db, studio_id=studio_id, client_name="NonEsiste")
        assert client is None


class TestGetAvailableActions:
    """Tests for action picker."""

    def test_no_client_only_generic(self, service):
        actions = service.get_available_actions(client_id=None)
        assert len(actions) == 1
        assert actions[0]["action"] == ClientAction.GENERIC_QUESTION

    def test_with_client_all_actions(self, service):
        actions = service.get_available_actions(client_id=42)
        assert len(actions) == 4
        action_types = [a["action"] for a in actions]
        assert ClientAction.GENERIC_QUESTION in action_types
        assert ClientAction.CLIENT_QUESTION in action_types
        assert ClientAction.CLIENT_CARD in action_types
        assert ClientAction.START_PROCEDURE in action_types

    def test_actions_have_labels(self, service):
        actions = service.get_available_actions(client_id=1)
        for action in actions:
            assert "label" in action
            assert "description" in action
            assert len(action["label"]) > 0
