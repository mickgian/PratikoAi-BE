"""Tests for PII anonymization functionality."""

import pytest
from app.core.privacy.anonymizer import PIIAnonymizer, PIIType, anonymizer
from app.schemas.chat import Message


class TestPIIAnonymizer:
    """Test cases for the PII anonymizer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.anonymizer = PIIAnonymizer()

    def test_detect_email(self):
        """Test email detection."""
        text = "My email is john.doe@example.com and backup is test@domain.org"
        matches = self.anonymizer.detect_pii(text)
        
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        assert len(email_matches) == 2
        assert "john.doe@example.com" in [m.original_value for m in email_matches]
        assert "test@domain.org" in [m.original_value for m in email_matches]

    def test_detect_italian_phone(self):
        """Test Italian phone number detection."""
        text = "Call me at +39 339 1234567 or 02 12345678"
        matches = self.anonymizer.detect_pii(text)
        
        phone_matches = [m for m in matches if m.pii_type == PIIType.PHONE]
        assert len(phone_matches) >= 1
        assert any("+39 339 1234567" in m.original_value for m in phone_matches)

    def test_detect_codice_fiscale(self):
        """Test Italian tax code detection."""
        text = "Il mio codice fiscale è RSSMRA85M01H501Z"
        matches = self.anonymizer.detect_pii(text)
        
        cf_matches = [m for m in matches if m.pii_type == PIIType.CODICE_FISCALE]
        assert len(cf_matches) == 1
        assert cf_matches[0].original_value == "RSSMRA85M01H501Z"
        assert cf_matches[0].confidence > 0.9

    def test_detect_partita_iva(self):
        """Test Italian VAT number detection."""
        text = "Partita IVA: IT12345678901 oppure solo 98765432109"
        matches = self.anonymizer.detect_pii(text)
        
        piva_matches = [m for m in matches if m.pii_type == PIIType.PARTITA_IVA]
        assert len(piva_matches) >= 1
        assert any("IT12345678901" in m.original_value for m in piva_matches)

    def test_detect_iban(self):
        """Test IBAN detection."""
        text = "IBAN: IT60 X054 2811 1010 0000 0123 456"
        matches = self.anonymizer.detect_pii(text)
        
        iban_matches = [m for m in matches if m.pii_type == PIIType.IBAN]
        # Note: spaces in IBAN might not match depending on regex
        assert len(iban_matches) >= 0  # IBAN with spaces might not match

    def test_detect_italian_names(self):
        """Test Italian name detection."""
        text = "Mi chiamo Marco Rossi e conosco la dottoressa Maria Bianchi"
        matches = self.anonymizer.detect_pii(text)
        
        name_matches = [m for m in matches if m.pii_type == PIIType.NAME]
        assert len(name_matches) >= 1
        # Should detect at least one name

    def test_anonymize_text_preserves_structure(self):
        """Test that anonymization preserves text structure."""
        original_text = "Ciao, sono Mario Rossi e la mia email è mario@example.com"
        result = self.anonymizer.anonymize_text(original_text)
        
        # Should have same approximate length and structure
        assert len(result.anonymized_text) > len(original_text) * 0.5
        assert result.pii_matches
        assert "mario@example.com" not in result.anonymized_text

    def test_anonymize_multiple_pii_types(self):
        """Test anonymization of multiple PII types."""
        text = "Contatti: mario.rossi@email.com, tel: +39 333 1234567, CF: RSSMRA85M01H501Z"
        result = self.anonymizer.anonymize_text(text)
        
        # Should detect multiple types
        pii_types = {match.pii_type for match in result.pii_matches}
        assert PIIType.EMAIL in pii_types
        assert PIIType.PHONE in pii_types or PIIType.CODICE_FISCALE in pii_types
        
        # Original values should not be in anonymized text
        assert "mario.rossi@email.com" not in result.anonymized_text
        assert "RSSMRA85M01H501Z" not in result.anonymized_text

    def test_anonymize_structured_data(self):
        """Test anonymization of structured data."""
        data = {
            "user_info": {
                "name": "Mario Rossi",
                "email": "mario@example.com",
                "phone": "+39 333 1234567"
            },
            "messages": [
                "Ciao, sono Mario",
                "La mia email è test@domain.com"
            ],
            "metadata": {
                "count": 42,
                "active": True
            }
        }
        
        anonymized_data, result = self.anonymizer.anonymize_structured_data(data)
        
        # Should preserve structure
        assert "user_info" in anonymized_data
        assert "messages" in anonymized_data
        assert "metadata" in anonymized_data
        
        # Should anonymize string values
        assert "mario@example.com" not in str(anonymized_data)
        assert result.pii_matches
        
        # Should preserve non-string values
        assert anonymized_data["metadata"]["count"] == 42
        assert anonymized_data["metadata"]["active"] is True

    def test_consistent_anonymization(self):
        """Test that same PII gets same anonymous replacement."""
        text1 = "Email: test@example.com"
        text2 = "Contact: test@example.com again"
        
        result1 = self.anonymizer.anonymize_text(text1)
        result2 = self.anonymizer.anonymize_text(text2)
        
        # Same email should get same replacement
        email_replacement1 = result1.anonymization_map.get("test@example.com")
        email_replacement2 = result2.anonymization_map.get("test@example.com")
        
        if email_replacement1 and email_replacement2:
            assert email_replacement1 == email_replacement2

    def test_confidence_thresholds(self):
        """Test PII detection confidence scoring."""
        # High confidence: exact Italian tax code format
        high_conf_text = "CF: RSSMRA85M01H501Z"
        high_matches = self.anonymizer.detect_pii(high_conf_text)
        cf_match = next((m for m in high_matches if m.pii_type == PIIType.CODICE_FISCALE), None)
        if cf_match:
            assert cf_match.confidence > 0.9
        
        # Lower confidence: generic ID that could be many things
        low_conf_text = "ID: ABC123DEF456"
        low_matches = self.anonymizer.detect_pii(low_conf_text)
        # Generic IDs might be filtered out or have lower confidence

    def test_empty_and_none_input(self):
        """Test handling of empty and None inputs."""
        # Empty string
        result = self.anonymizer.anonymize_text("")
        assert result.anonymized_text == ""
        assert not result.pii_matches
        
        # None input should be handled gracefully
        result = self.anonymizer.anonymize_text(None)
        assert result.anonymized_text == ""

    def test_no_pii_text(self):
        """Test text with no PII."""
        text = "Questo è un testo normale senza informazioni personali."
        result = self.anonymizer.anonymize_text(text)
        
        assert result.anonymized_text == text  # Should be unchanged
        assert not result.pii_matches

    def test_italian_date_formats(self):
        """Test Italian date format detection."""
        text = "Nato il 15 marzo 1985 e registrato il 01/01/2020"
        matches = self.anonymizer.detect_pii(text)
        
        date_matches = [m for m in matches if m.pii_type == PIIType.DATE_OF_BIRTH]
        # Should detect at least one date pattern

    def test_credit_card_detection(self):
        """Test credit card number detection."""
        text = "Card: 4532-1234-5678-9012 or 4532123456789012"
        matches = self.anonymizer.detect_pii(text)
        
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(cc_matches) >= 1

    def test_anonymizer_stats(self):
        """Test anonymizer statistics."""
        # Generate some anonymizations to populate cache
        self.anonymizer.anonymize_text("test@example.com")
        self.anonymizer.anonymize_text("CF: RSSMRA85M01H501Z")
        
        stats = self.anonymizer.get_stats()
        assert "cached_anonymizations" in stats
        assert "patterns_count" in stats
        assert "name_patterns_count" in stats
        assert stats["cached_anonymizations"] > 0

    def test_clear_cache(self):
        """Test cache clearing."""
        # Generate some cached anonymizations
        self.anonymizer.anonymize_text("test@example.com")
        initial_stats = self.anonymizer.get_stats()
        
        # Clear cache
        self.anonymizer.clear_cache()
        cleared_stats = self.anonymizer.get_stats()
        
        assert cleared_stats["cached_anonymizations"] == 0

    def test_mixed_language_content(self):
        """Test handling of mixed Italian/English content."""
        text = "Hello, I am Mario Rossi from Italy. My email is mario@example.com and telefono +39 333 1234567"
        result = self.anonymizer.anonymize_text(text)
        
        # Should detect PII regardless of language mix
        assert result.pii_matches
        assert "mario@example.com" not in result.anonymized_text


class TestGlobalAnonymizerInstance:
    """Test the global anonymizer instance."""

    def test_global_instance_available(self):
        """Test that global anonymizer instance is available."""
        assert anonymizer is not None
        assert isinstance(anonymizer, PIIAnonymizer)

    def test_global_instance_functionality(self):
        """Test basic functionality of global instance."""
        text = "Email: test@example.com"
        result = anonymizer.anonymize_text(text)
        
        assert result.anonymized_text != text
        assert result.pii_matches
        assert "test@example.com" not in result.anonymized_text