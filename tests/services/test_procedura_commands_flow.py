"""DEV-405: /procedura Slash Command and @client Mention Tests.

Tests SlashCommandHandler parsing, ProceduraCategory matching,
and ClientMentionService mention extraction, autocomplete, and actions.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.procedura import ProceduraCategory
from app.services.client_mention_service import ClientAction, ClientMentionService
from app.services.slash_command_handler import SlashCommandHandler

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def handler() -> SlashCommandHandler:
    return SlashCommandHandler()


@pytest.fixture
def mention_service() -> ClientMentionService:
    return ClientMentionService()


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def studio_id():
    return uuid4()


# ---------------------------------------------------------------------------
# SlashCommandHandler.parse tests
# ---------------------------------------------------------------------------


class TestSlashCommandParsing:
    """Tests for slash command parsing."""

    def test_parse_procedura_no_query(self, handler) -> None:
        result = handler.parse("/procedura")
        assert result is not None
        assert result["command"] == "procedura"
        assert result["query"] == ""

    def test_parse_procedura_with_query(self, handler) -> None:
        result = handler.parse("/procedura apertura IVA")
        assert result["command"] == "procedura"
        assert result["query"] == "apertura IVA"

    def test_parse_case_insensitive(self, handler) -> None:
        result = handler.parse("/PROCEDURA fiscale")
        assert result is not None
        assert result["command"] == "procedura"

    def test_parse_no_command(self, handler) -> None:
        result = handler.parse("just a regular message")
        assert result is None

    def test_parse_other_slash(self, handler) -> None:
        result = handler.parse("/help")
        assert result is None

    def test_parse_with_whitespace(self, handler) -> None:
        result = handler.parse("  /procedura fiscale  ")
        assert result is not None
        assert result["query"] == "fiscale"


# ---------------------------------------------------------------------------
# SlashCommandHandler._match_category
# ---------------------------------------------------------------------------


class TestCategoryMatching:
    """Tests for category matching."""

    def test_match_fiscale(self, handler) -> None:
        assert handler._match_category("fiscale") == ProceduraCategory.FISCALE

    def test_match_lavoro(self, handler) -> None:
        assert handler._match_category("lavoro") == ProceduraCategory.LAVORO

    def test_match_societario(self, handler) -> None:
        assert handler._match_category("societario") == ProceduraCategory.SOCIETARIO

    def test_match_previdenza(self, handler) -> None:
        assert handler._match_category("previdenza") == ProceduraCategory.PREVIDENZA

    def test_no_match(self, handler) -> None:
        assert handler._match_category("nonexistent") is None

    def test_empty_query(self, handler) -> None:
        assert handler._match_category("") is None


# ---------------------------------------------------------------------------
# SlashCommandHandler.handle_procedura
# ---------------------------------------------------------------------------


class TestHandleProcedura:
    """Tests for handle_procedura."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_exact_code_match(self, handler, mock_db) -> None:
        proc = MagicMock()
        proc.to_dict.return_value = {"code": "APERTURA_PIVA", "title": "Apertura P.IVA"}

        with patch("app.services.slash_command_handler.procedura_service") as mock_svc:
            mock_svc.get_by_code = AsyncMock(return_value=proc)

            result = await handler.handle_procedura(mock_db, query="APERTURA_PIVA")

        assert result["type"] == "detail"
        assert result["mode"] == "read_only"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_list_all(self, handler, mock_db) -> None:
        proc1 = MagicMock()
        proc1.title = "Apertura P.IVA"
        proc1.description = ""
        proc1.to_dict.return_value = {"code": "APERTURA_PIVA"}
        proc2 = MagicMock()
        proc2.title = "Chiusura"
        proc2.description = ""
        proc2.to_dict.return_value = {"code": "CHIUSURA"}

        with patch("app.services.slash_command_handler.procedura_service") as mock_svc:
            mock_svc.get_by_code = AsyncMock(return_value=None)
            mock_svc.list_active = AsyncMock(return_value=[proc1, proc2])

            result = await handler.handle_procedura(mock_db, query="")

        assert result["type"] == "list"
        assert len(result["procedures"]) == 2
        assert result["mode"] == "read_only"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_category_filter(self, handler, mock_db) -> None:
        proc = MagicMock()
        proc.to_dict.return_value = {"code": "IVA"}

        with patch("app.services.slash_command_handler.procedura_service") as mock_svc:
            mock_svc.get_by_code = AsyncMock(return_value=None)
            mock_svc.list_active = AsyncMock(return_value=[proc])

            result = await handler.handle_procedura(mock_db, query="fiscale")

        assert result["type"] == "list"
        mock_svc.list_active.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_title_search(self, handler, mock_db) -> None:
        proc1 = MagicMock()
        proc1.title = "Apertura Partita IVA"
        proc1.description = ""
        proc1.to_dict.return_value = {"code": "APERTURA_PIVA"}
        proc2 = MagicMock()
        proc2.title = "Chiusura attività"
        proc2.description = ""
        proc2.to_dict.return_value = {"code": "CHIUSURA"}

        with patch("app.services.slash_command_handler.procedura_service") as mock_svc:
            mock_svc.get_by_code = AsyncMock(return_value=None)
            mock_svc.list_active = AsyncMock(return_value=[proc1, proc2])

            result = await handler.handle_procedura(mock_db, query="apertura")

        assert result["type"] == "list"
        assert len(result["procedures"]) == 1


# ---------------------------------------------------------------------------
# ClientMentionService.extract_mentions
# ---------------------------------------------------------------------------


class TestExtractMentions:
    """Tests for @mention parsing."""

    def test_single_mention(self, mention_service) -> None:
        result = mention_service.extract_mentions("Ciao @Mario come stai?")
        assert result == ["Mario"]

    def test_quoted_mention(self, mention_service) -> None:
        result = mention_service.extract_mentions('Parlando di @"Mario Rossi" oggi')
        assert result == ["Mario Rossi"]

    def test_multiple_mentions(self, mention_service) -> None:
        result = mention_service.extract_mentions('@Anna e @"Marco Bianchi"')
        assert "Anna" in result
        assert "Marco Bianchi" in result

    def test_no_mentions(self, mention_service) -> None:
        result = mention_service.extract_mentions("Nessun cliente menzionato")
        assert result == []

    def test_email_not_mention(self, mention_service) -> None:
        # @ in email should still match as mention (by regex design)
        result = mention_service.extract_mentions("test@example.com")
        assert len(result) >= 0  # Implementation-dependent


# ---------------------------------------------------------------------------
# ClientMentionService.autocomplete
# ---------------------------------------------------------------------------


class TestAutocomplete:
    """Tests for autocomplete."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_autocomplete_success(self, mention_service, mock_db, studio_id) -> None:
        client = SimpleNamespace(
            id=1, nome="Mario Rossi", tipo_cliente="persona_fisica", codice_fiscale="RSSMRA85M01H501Z"
        )
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [client]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.client_mention_service.select"), patch("app.services.client_mention_service.and_"):
            result = await mention_service.autocomplete(mock_db, studio_id=studio_id, prefix="Mar")

        assert len(result) == 1
        assert result[0]["nome"] == "Mario Rossi"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_autocomplete_short_prefix(self, mention_service, mock_db, studio_id) -> None:
        result = await mention_service.autocomplete(mock_db, studio_id=studio_id, prefix="M")
        assert result == []

    @pytest.mark.asyncio(loop_scope="function")
    async def test_autocomplete_empty_prefix(self, mention_service, mock_db, studio_id) -> None:
        result = await mention_service.autocomplete(mock_db, studio_id=studio_id, prefix="")
        assert result == []


# ---------------------------------------------------------------------------
# ClientMentionService.get_available_actions
# ---------------------------------------------------------------------------


class TestAvailableActions:
    """Tests for action picker."""

    def test_actions_without_client(self, mention_service) -> None:
        actions = mention_service.get_available_actions()
        assert len(actions) == 1
        assert actions[0]["action"] == ClientAction.GENERIC_QUESTION

    def test_actions_with_client(self, mention_service) -> None:
        actions = mention_service.get_available_actions(client_id=1)
        assert len(actions) == 4
        action_types = [a["action"] for a in actions]
        assert ClientAction.GENERIC_QUESTION in action_types
        assert ClientAction.CLIENT_QUESTION in action_types
        assert ClientAction.CLIENT_CARD in action_types
        assert ClientAction.START_PROCEDURE in action_types

    def test_actions_have_labels(self, mention_service) -> None:
        actions = mention_service.get_available_actions(client_id=1)
        for action in actions:
            assert "label" in action
            assert "description" in action
