"""Unit tests for ItalianLawParser service (ADR-023).

Tests parsing of Italian legal documents including:
- Article extraction
- Comma parsing
- Cross-references
- Structure (Titoli, Capi)
- Topic detection
"""

import pytest

from app.services.italian_law_parser import (
    ItalianLawParser,
    LawArticle,
    LawComma,
    ParsedLaw,
)

# Sample Italian law text for testing
SAMPLE_LAW_TEXT = """LEGGE 30 dicembre 2025, n. 199

Bilancio di previsione dello Stato per l'anno finanziario 2026

Titolo I - MISURE IN MATERIA DI ENTRATE

Capo I - Disposizioni in materia di imposte

Art. 1 - Revisione dell'IRPEF

1. A decorrere dal 1° gennaio 2026, le aliquote dell'IRPEF sono rideterminate.

2. Le nuove aliquote sono le seguenti:
   a) fino a 28.000 euro: 23%;
   b) oltre 28.000 euro e fino a 50.000 euro: 35%;
   c) oltre 50.000 euro: 43%.

3. Per l'applicazione delle disposizioni di cui al comma 1, si rinvia all'articolo 10.

Art. 2 - Definizione agevolata dei carichi

1. I debiti risultanti dai singoli carichi affidati agli agenti della riscossione
dal 1° gennaio 2000 al 30 giugno 2024 possono essere estinti mediante
rottamazione quinquies.

2. Sono esclusi dalla definizione agevolata i carichi relativi a:
   a) risorse proprie tradizionali dell'Unione Europea;
   b) IVA all'importazione.

3. I debitori presentano la domanda entro il 30 aprile 2026.

4. Il pagamento può essere effettuato in un'unica soluzione entro il
31 luglio 2026, oppure in un massimo di 18 rate mensili.

Art. 3 - Bonus edilizi

1. Per le spese documentate relative agli interventi di cui all'articolo 2,
comma 1, spetta una detrazione dall'IRPEF.

2. La detrazione di cui al comma 1 è pari al 50% delle spese sostenute.

Titolo II - MISURE IN MATERIA DI LAVORO

Capo I - Disposizioni per i lavoratori

Art. 10 - Detrazioni per lavoro dipendente

1. Le detrazioni per i titolari di redditi di lavoro dipendente sono
rivalutate in base all'inflazione.

2. Per ulteriori dettagli si veda l'articolo 1.

ALLEGATO A - Tabelle delle aliquote

Le tabelle di seguito riportate...
"""


class TestItalianLawParserBasic:
    """Basic parsing tests."""

    @pytest.fixture
    def parser(self) -> ItalianLawParser:
        """Create parser with default config."""
        return ItalianLawParser()

    @pytest.fixture
    def parsed_law(self, parser: ItalianLawParser) -> ParsedLaw:
        """Parse sample law text."""
        return parser.parse(SAMPLE_LAW_TEXT, "LEGGE 30 dicembre 2025, n. 199")

    def test_parse_returns_parsed_law(self, parsed_law: ParsedLaw) -> None:
        """Parse returns a ParsedLaw object."""
        assert isinstance(parsed_law, ParsedLaw)

    def test_law_title_preserved(self, parsed_law: ParsedLaw) -> None:
        """Law title is preserved correctly."""
        assert parsed_law.title == "LEGGE 30 dicembre 2025, n. 199"

    def test_law_number_extracted(self, parsed_law: ParsedLaw) -> None:
        """Law number is extracted correctly."""
        assert parsed_law.law_number == "199/2025"

    def test_publication_date_extracted(self, parsed_law: ParsedLaw) -> None:
        """Publication date is extracted from title."""
        assert parsed_law.publication_date == "30 dicembre 2025"


class TestItalianLawParserArticles:
    """Tests for article extraction."""

    @pytest.fixture
    def parser(self) -> ItalianLawParser:
        return ItalianLawParser()

    @pytest.fixture
    def parsed_law(self, parser: ItalianLawParser) -> ParsedLaw:
        return parser.parse(SAMPLE_LAW_TEXT, "LEGGE 30 dicembre 2025, n. 199")

    def test_articles_extracted(self, parsed_law: ParsedLaw) -> None:
        """Articles are extracted from the law."""
        assert len(parsed_law.articles) == 4  # Art. 1, 2, 3, 10

    def test_article_numbers(self, parsed_law: ParsedLaw) -> None:
        """Article numbers are parsed correctly."""
        article_numbers = [a.article_number for a in parsed_law.articles]
        assert "Art. 1" in article_numbers
        assert "Art. 2" in article_numbers
        assert "Art. 3" in article_numbers
        assert "Art. 10" in article_numbers

    def test_articles_sorted_by_number(self, parsed_law: ParsedLaw) -> None:
        """Articles are sorted by number."""
        numbers = [a.article_number_int for a in parsed_law.articles]
        assert numbers == sorted(numbers)

    def test_article_title_extracted(self, parsed_law: ParsedLaw) -> None:
        """Article titles are extracted when present."""
        art1 = next(a for a in parsed_law.articles if a.article_number == "Art. 1")
        assert art1.title is not None
        assert "IRPEF" in art1.title

    def test_article_full_text_preserved(self, parsed_law: ParsedLaw) -> None:
        """Full article text is preserved."""
        art2 = next(a for a in parsed_law.articles if a.article_number == "Art. 2")
        assert "rottamazione quinquies" in art2.full_text

    def test_display_title_with_title(self, parsed_law: ParsedLaw) -> None:
        """Display title includes article title when present."""
        art1 = next(a for a in parsed_law.articles if a.article_number == "Art. 1")
        assert "Art. 1 - " in art1.display_title
        assert "IRPEF" in art1.display_title


class TestItalianLawParserCommi:
    """Tests for comma (paragraph) parsing."""

    @pytest.fixture
    def parser(self) -> ItalianLawParser:
        return ItalianLawParser()

    @pytest.fixture
    def parsed_law(self, parser: ItalianLawParser) -> ParsedLaw:
        return parser.parse(SAMPLE_LAW_TEXT, "LEGGE 30 dicembre 2025, n. 199")

    def test_commi_extracted(self, parsed_law: ParsedLaw) -> None:
        """Commi are extracted from articles."""
        art1 = next(a for a in parsed_law.articles if a.article_number == "Art. 1")
        assert len(art1.commi) >= 2  # At least commi 1, 2

    def test_comma_numbers(self, parsed_law: ParsedLaw) -> None:
        """Comma numbers are correct."""
        art2 = next(a for a in parsed_law.articles if a.article_number == "Art. 2")
        comma_numbers = [c.number for c in art2.commi]
        assert 1 in comma_numbers
        assert 2 in comma_numbers

    def test_comma_text_preserved(self, parsed_law: ParsedLaw) -> None:
        """Comma text is preserved."""
        art2 = next(a for a in parsed_law.articles if a.article_number == "Art. 2")
        comma1 = next(c for c in art2.commi if c.number == 1)
        assert "debiti" in comma1.text.lower()


class TestItalianLawParserCrossReferences:
    """Tests for cross-reference extraction."""

    @pytest.fixture
    def parser(self) -> ItalianLawParser:
        return ItalianLawParser()

    @pytest.fixture
    def parsed_law(self, parser: ItalianLawParser) -> ParsedLaw:
        return parser.parse(SAMPLE_LAW_TEXT, "LEGGE 30 dicembre 2025, n. 199")

    def test_cross_references_extracted(self, parsed_law: ParsedLaw) -> None:
        """Cross-references to other articles are extracted."""
        art1 = next(a for a in parsed_law.articles if a.article_number == "Art. 1")
        # Art. 1 comma 3 references articolo 10
        assert any("10" in ref for ref in art1.cross_references)

    def test_cross_reference_with_comma(self, parsed_law: ParsedLaw) -> None:
        """Cross-references including comma numbers are captured."""
        art3 = next(a for a in parsed_law.articles if a.article_number == "Art. 3")
        # Art. 3 references articolo 2, comma 1
        refs_str = " ".join(art3.cross_references)
        assert "Art. 2" in refs_str


class TestItalianLawParserStructure:
    """Tests for Titolo/Capo structure parsing."""

    @pytest.fixture
    def parser(self) -> ItalianLawParser:
        return ItalianLawParser()

    @pytest.fixture
    def parsed_law(self, parser: ItalianLawParser) -> ParsedLaw:
        return parser.parse(SAMPLE_LAW_TEXT, "LEGGE 30 dicembre 2025, n. 199")

    def test_titoli_parsed(self, parsed_law: ParsedLaw) -> None:
        """Titoli are parsed from structure."""
        titoli_count = parsed_law.metadata.get("titoli_count", 0)
        assert titoli_count == 2  # Titolo I and Titolo II

    def test_capi_parsed(self, parsed_law: ParsedLaw) -> None:
        """Capi are parsed from structure."""
        capi_count = parsed_law.metadata.get("capi_count", 0)
        assert capi_count >= 1  # At least Capo I

    def test_article_parent_titolo(self, parsed_law: ParsedLaw) -> None:
        """Articles have parent Titolo assigned."""
        art1 = next(a for a in parsed_law.articles if a.article_number == "Art. 1")
        assert art1.titolo is not None
        assert "Titolo" in art1.titolo
        assert "I" in art1.titolo

    def test_article_parent_capo(self, parsed_law: ParsedLaw) -> None:
        """Articles have parent Capo assigned."""
        art1 = next(a for a in parsed_law.articles if a.article_number == "Art. 1")
        assert art1.capo is not None
        assert "Capo" in art1.capo


class TestItalianLawParserTopics:
    """Tests for topic detection."""

    @pytest.fixture
    def parser(self) -> ItalianLawParser:
        return ItalianLawParser(
            topic_keywords={
                "rottamazione": ["rottamazione", "definizione agevolata"],
                "irpef": ["IRPEF", "imposta sul reddito"],
                "bonus": ["bonus", "detrazione"],
            }
        )

    @pytest.fixture
    def parsed_law(self, parser: ItalianLawParser) -> ParsedLaw:
        return parser.parse(SAMPLE_LAW_TEXT, "LEGGE 30 dicembre 2025, n. 199")

    def test_rottamazione_topic_detected(self, parsed_law: ParsedLaw) -> None:
        """Rottamazione topic is detected in Art. 2."""
        art2 = next(a for a in parsed_law.articles if a.article_number == "Art. 2")
        assert "rottamazione" in art2.topics

    def test_irpef_topic_detected(self, parsed_law: ParsedLaw) -> None:
        """IRPEF topic is detected in Art. 1."""
        art1 = next(a for a in parsed_law.articles if a.article_number == "Art. 1")
        assert "irpef" in art1.topics

    def test_bonus_topic_detected(self, parsed_law: ParsedLaw) -> None:
        """Bonus topic is detected in Art. 3."""
        art3 = next(a for a in parsed_law.articles if a.article_number == "Art. 3")
        assert "bonus" in art3.topics


class TestItalianLawParserAllegati:
    """Tests for allegati (attachment) parsing."""

    @pytest.fixture
    def parser(self) -> ItalianLawParser:
        return ItalianLawParser()

    @pytest.fixture
    def parsed_law(self, parser: ItalianLawParser) -> ParsedLaw:
        return parser.parse(SAMPLE_LAW_TEXT, "LEGGE 30 dicembre 2025, n. 199")

    def test_allegati_extracted(self, parsed_law: ParsedLaw) -> None:
        """Allegati are extracted from the law."""
        assert len(parsed_law.allegati) >= 1

    def test_allegato_id(self, parsed_law: ParsedLaw) -> None:
        """Allegato ID is extracted."""
        allegato = parsed_law.allegati[0]
        assert allegato["id"] == "A"


class TestItalianLawParserEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def parser(self) -> ItalianLawParser:
        return ItalianLawParser()

    def test_empty_text(self, parser: ItalianLawParser) -> None:
        """Empty text returns empty articles list."""
        result = parser.parse("", "Empty Law")
        assert result.articles == []

    def test_no_articles_text(self, parser: ItalianLawParser) -> None:
        """Text without articles returns empty list."""
        result = parser.parse("This is a document without articles.", "No Articles")
        assert result.articles == []

    def test_unknown_law_number(self, parser: ItalianLawParser) -> None:
        """Missing law number returns 'unknown'."""
        result = parser.parse("Some text", "Some Title")
        assert result.law_number == "unknown"

    def test_article_bis_pattern(self, parser: ItalianLawParser) -> None:
        """Art. 2-bis pattern is parsed correctly."""
        text = """
        Art. 2-bis - Disposizioni aggiuntive

        1. Le disposizioni del presente articolo si applicano...
        """
        result = parser.parse(text, "Test Law n. 1/2025")
        assert len(result.articles) == 1
        assert result.articles[0].article_number == "Art. 2-bis"

    def test_alternative_articolo_spelling(self, parser: ItalianLawParser) -> None:
        """'Articolo' spelled out is also recognized."""
        text = """
        Articolo 1 - Test

        1. Test content.
        """
        result = parser.parse(text, "Test Law n. 1/2025")
        assert len(result.articles) == 1
        assert result.articles[0].article_number == "Art. 1"


class TestLawArticleDataclass:
    """Tests for LawArticle dataclass."""

    def test_display_title_without_title(self) -> None:
        """Display title shows only article number when no title."""
        article = LawArticle(
            article_number="Art. 5",
            article_number_int=5,
            title=None,
            full_text="Content",
            commi=[],
            cross_references=[],
            topics=[],
            titolo=None,
            capo=None,
        )
        assert article.display_title == "Art. 5"

    def test_display_title_with_title(self) -> None:
        """Display title includes title when present."""
        article = LawArticle(
            article_number="Art. 5",
            article_number_int=5,
            title="Test Title",
            full_text="Content",
            commi=[],
            cross_references=[],
            topics=[],
            titolo=None,
            capo=None,
        )
        assert article.display_title == "Art. 5 - Test Title"


class TestLawCommaDataclass:
    """Tests for LawComma dataclass."""

    def test_law_comma_creation(self) -> None:
        """LawComma can be created with all fields."""
        comma = LawComma(
            number=1,
            text="Test comma text",
            cross_references=["Art. 2"],
        )
        assert comma.number == 1
        assert comma.text == "Test comma text"
        assert comma.cross_references == ["Art. 2"]

    def test_law_comma_default_cross_refs(self) -> None:
        """LawComma has empty cross_references by default."""
        comma = LawComma(number=1, text="Test")
        assert comma.cross_references == []
