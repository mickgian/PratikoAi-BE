"""Tests for DEV-402: /procedura Slash Command Handler."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.slash_command_handler import SlashCommandHandler


@pytest.fixture
def handler():
    return SlashCommandHandler()


@pytest.fixture
def mock_db():
    return AsyncMock()


class TestParse:
    """Tests for slash command parsing."""

    def test_parse_procedura_no_query(self, handler):
        result = handler.parse("/procedura")
        assert result == {"command": "procedura", "query": ""}

    def test_parse_procedura_with_query(self, handler):
        result = handler.parse("/procedura apertura partita iva")
        assert result["command"] == "procedura"
        assert result["query"] == "apertura partita iva"

    def test_parse_procedura_case_insensitive(self, handler):
        result = handler.parse("/PROCEDURA test")
        assert result["command"] == "procedura"

    def test_parse_procedura_with_whitespace(self, handler):
        result = handler.parse("  /procedura   test  ")
        assert result["command"] == "procedura"
        assert result["query"] == "test"

    def test_parse_no_slash_command(self, handler):
        result = handler.parse("ciao, come posso aprire una partita iva?")
        assert result is None

    def test_parse_unknown_command(self, handler):
        result = handler.parse("/unknown test")
        assert result is None

    def test_parse_empty_string(self, handler):
        result = handler.parse("")
        assert result is None


class TestHandleProcedura:
    """Tests for /procedura command handling."""

    @pytest.mark.asyncio
    async def test_exact_code_match(self, handler, mock_db):
        """Exact code match returns detail view."""
        mock_proc = MagicMock()
        mock_proc.to_dict.return_value = {"code": "APERTURA_PIVA", "title": "Apertura P.IVA"}

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "app.services.slash_command_handler.procedura_service.get_by_code",
                AsyncMock(return_value=mock_proc),
            )
            result = await handler.handle_procedura(mock_db, query="APERTURA_PIVA")

        assert result["type"] == "detail"
        assert result["mode"] == "read_only"
        assert result["procedure"]["code"] == "APERTURA_PIVA"

    @pytest.mark.asyncio
    async def test_list_all_procedures(self, handler, mock_db):
        """No query returns all active procedures."""
        mock_proc1 = MagicMock()
        mock_proc1.to_dict.return_value = {"code": "A", "title": "Proc A"}
        mock_proc1.title = "Proc A"
        mock_proc1.description = ""

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "app.services.slash_command_handler.procedura_service.get_by_code",
                AsyncMock(return_value=None),
            )
            mp.setattr(
                "app.services.slash_command_handler.procedura_service.list_active",
                AsyncMock(return_value=[mock_proc1]),
            )
            result = await handler.handle_procedura(mock_db)

        assert result["type"] == "list"
        assert result["mode"] == "read_only"
        assert len(result["procedures"]) == 1

    @pytest.mark.asyncio
    async def test_search_by_title(self, handler, mock_db):
        """Text query filters by title match."""
        mock_proc = MagicMock()
        mock_proc.to_dict.return_value = {"code": "A", "title": "Apertura P.IVA"}
        mock_proc.title = "Apertura P.IVA"
        mock_proc.description = ""

        mock_no_match = MagicMock()
        mock_no_match.to_dict.return_value = {"code": "B", "title": "Chiusura Bilancio"}
        mock_no_match.title = "Chiusura Bilancio"
        mock_no_match.description = ""

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "app.services.slash_command_handler.procedura_service.get_by_code",
                AsyncMock(return_value=None),
            )
            mp.setattr(
                "app.services.slash_command_handler.procedura_service.list_active",
                AsyncMock(return_value=[mock_proc, mock_no_match]),
            )
            result = await handler.handle_procedura(mock_db, query="apertura")

        assert result["type"] == "list"
        assert len(result["procedures"]) == 1
        assert result["procedures"][0]["title"] == "Apertura P.IVA"

    @pytest.mark.asyncio
    async def test_no_progress_created(self, handler, mock_db):
        """Generic mode creates no ProceduraProgress (read-only)."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "app.services.slash_command_handler.procedura_service.get_by_code",
                AsyncMock(return_value=None),
            )
            mp.setattr(
                "app.services.slash_command_handler.procedura_service.list_active",
                AsyncMock(return_value=[]),
            )
            mock_start = AsyncMock()
            mp.setattr(
                "app.services.slash_command_handler.procedura_service.start_progress",
                mock_start,
            )
            await handler.handle_procedura(mock_db, query="test")

        mock_start.assert_not_called()


class TestMatchCategory:
    """Tests for category matching."""

    def test_exact_match(self, handler):
        assert handler._match_category("fiscale") is not None

    def test_partial_match(self, handler):
        assert handler._match_category("fisc") is not None

    def test_no_match(self, handler):
        assert handler._match_category("xyz") is None

    def test_empty_query(self, handler):
        assert handler._match_category("") is None
