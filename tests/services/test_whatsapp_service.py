"""DEV-334: Tests for WhatsAppService — wa.me link generation.

Tests cover:
- Basic wa.me link generation
- Italian phone number normalization (+39 prefix)
- Message URL encoding
- Bulk link generation for multiple recipients
- Invalid phone number validation
"""

from uuid import uuid4

import pytest

from app.services.whatsapp_service import WhatsAppService


@pytest.fixture
def whatsapp_service() -> WhatsAppService:
    return WhatsAppService()


class TestWhatsAppServiceLinkGeneration:
    """Test WhatsAppService.generate_link()."""

    def test_generate_link_basic(
        self,
        whatsapp_service: WhatsAppService,
    ) -> None:
        """Happy path: basic wa.me link generation."""
        result = whatsapp_service.generate_link(
            phone="+393331234567",
            message="Buongiorno, le scrivo per la scadenza IVA.",
        )

        assert result is not None
        assert "wa.me" in result
        assert "393331234567" in result

    def test_phone_normalization_italian(
        self,
        whatsapp_service: WhatsAppService,
    ) -> None:
        """Italian phone number normalization with +39 prefix."""
        # Various Italian phone formats that should normalize to 393331234567
        test_cases = [
            ("3331234567", "393331234567"),
            ("+39 333 1234567", "393331234567"),
            ("+39 333-123-4567", "393331234567"),
        ]

        for input_phone, expected_normalized in test_cases:
            result = whatsapp_service.generate_link(
                phone=input_phone,
                message="Test",
            )

            assert expected_normalized in result, f"Phone '{input_phone}' should normalize to '{expected_normalized}'"

    def test_url_encoding_message(
        self,
        whatsapp_service: WhatsAppService,
    ) -> None:
        """Message is properly URL-encoded."""
        result = whatsapp_service.generate_link(
            phone="+393331234567",
            message="Gentile cliente, la scadenza è il 16/03. Può confermare?",
        )

        assert result is not None
        # URL should contain ?text= with encoded message
        assert "?text=" in result
        # Spaces should be encoded (as %20 or +)
        text_part = result.split("?text=")[1]
        assert " " not in text_part

    def test_generate_link_no_message(
        self,
        whatsapp_service: WhatsAppService,
    ) -> None:
        """Link without message has no ?text= parameter."""
        result = whatsapp_service.generate_link(
            phone="+393331234567",
        )

        assert "wa.me/393331234567" in result
        assert "?text=" not in result


class TestWhatsAppServiceBulkLinks:
    """Test WhatsAppService.generate_bulk_links()."""

    def test_bulk_link_generation(
        self,
        whatsapp_service: WhatsAppService,
    ) -> None:
        """Bulk generation for multiple recipients."""
        phones = ["+393331234567", "+393489876543", "+393201112233"]

        results = whatsapp_service.generate_bulk_links(
            phones=phones,
            message="Gentile cliente, le ricordiamo la scadenza.",
        )

        assert len(results) == 3
        # Each result should contain a link
        for entry in results:
            assert entry["link"] is not None
            assert "wa.me" in entry["link"]
            assert entry["error"] is None


class TestWhatsAppServiceValidation:
    """Test WhatsAppService phone validation."""

    def test_invalid_phone_raises(
        self,
        whatsapp_service: WhatsAppService,
    ) -> None:
        """Invalid phone number raises ValueError."""
        invalid_phones = ["abc", "123", "+39"]

        for phone in invalid_phones:
            with pytest.raises(ValueError, match="[Nn]umero.*non valido|troppo corto"):
                whatsapp_service.generate_link(
                    phone=phone,
                    message="Test",
                )

    def test_empty_phone_raises(
        self,
        whatsapp_service: WhatsAppService,
    ) -> None:
        """Empty phone raises ValueError."""
        with pytest.raises(ValueError):
            whatsapp_service.generate_link(
                phone="",
                message="Test",
            )
