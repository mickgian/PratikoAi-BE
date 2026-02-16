"""Tests for HTML content extraction and quality validation."""

import pytest

from app.core.text.clean import (
    chunk_contains_navigation,
    clean_html,
    clean_italian_text,
    is_valid_text,
    normalize_whitespace,
    validate_extracted_content,
)


class TestCleanHtml:
    """Tests for HTML content extraction."""

    def test_extracts_main_content_from_complex_page(self):
        """Test that navigation/footer are removed."""
        html = """
        <html>
        <body>
            <nav>Navigation menu here</nav>
            <header>Site header</header>
            <main>
                <article>
                    <h1>Main Article Title</h1>
                    <p>This is the actual content that should be extracted.
                    It contains important information about the topic.
                    We need enough text here to pass the minimum length check.
                    Adding more content to make this a substantial article.
                    The extraction should focus on this main content area.</p>
                </article>
            </main>
            <aside>Sidebar content</aside>
            <footer>Footer links</footer>
        </body>
        </html>
        """
        result = clean_html(html)

        assert "actual content" in result.lower()
        assert "navigation menu" not in result.lower()
        assert "footer links" not in result.lower()
        assert "sidebar content" not in result.lower()

    def test_handles_empty_html(self):
        """Test empty HTML handling."""
        result = clean_html("")
        assert result == ""

    def test_handles_whitespace_only_html(self):
        """Test whitespace-only HTML handling."""
        result = clean_html("   \n\t  ")
        assert result == ""

    def test_extracts_article_content(self):
        """Test extraction from article tag."""
        html = """
        <html>
        <body>
            <nav>Menu items here</nav>
            <article>
                <h1>Article Title</h1>
                <p>This is the main article content that should be extracted.
                It contains multiple sentences with meaningful information.
                The article discusses important regulatory updates.</p>
            </article>
            <footer>Copyright info</footer>
        </body>
        </html>
        """
        result = clean_html(html)

        assert "article content" in result.lower()
        assert "menu items" not in result.lower()

    def test_removes_script_and_style(self):
        """Test that script and style tags are removed."""
        html = """
        <html>
        <head>
            <style>.menu { color: red; }</style>
        </head>
        <body>
            <script>alert('test');</script>
            <main>
                <p>This is the actual content that matters for extraction.
                We need sufficient text length to pass validation checks.
                Adding more meaningful content about regulatory documents.</p>
            </main>
        </body>
        </html>
        """
        result = clean_html(html)

        assert "alert" not in result
        assert "color: red" not in result
        assert "actual content" in result.lower()

    def test_extracts_from_body_when_no_main(self):
        """Test fallback to body when no main/article element."""
        html = """
        <html>
        <body>
            <div id="content">
                <h1>Page Title</h1>
                <p>This is body content when no semantic elements exist.
                The extractor should still find this content and return it.
                Adding more text to ensure we pass minimum length requirements.</p>
            </div>
        </body>
        </html>
        """
        result = clean_html(html)

        assert "body content" in result.lower()


class TestValidateExtractedContent:
    """Tests for content quality validation."""

    def test_valid_content_passes(self):
        """Test that valid content passes validation."""
        content = (
            """
        Questo è un documento importante che contiene informazioni
        sul messaggio INPS numero 3585. Il messaggio tratta di
        contributi previdenziali e scadenze per i pagamenti.
        Ulteriori dettagli sono disponibili nel documento completo.
        """
            * 3
        )  # Make it long enough

        is_valid, reason = validate_extracted_content(content)
        assert is_valid
        assert reason == "OK"

    def test_navigation_content_fails(self):
        """Test that navigation content is detected."""
        content = """
        Vai al menu principale Vai al contenuto Cookie policy
        Accedi a MyINPS Cedolino pensione Mappa del sito
        Privacy policy Seguici su Contatti
        """

        is_valid, reason = validate_extracted_content(content)
        assert not is_valid
        assert "navigation patterns" in reason

    def test_short_content_fails(self):
        """Test that very short content is flagged."""
        content = "Too short"

        is_valid, reason = validate_extracted_content(content)
        assert not is_valid
        assert "too short" in reason.lower()

    def test_starts_with_navigation_fails(self):
        """Test content starting with nav text is flagged."""
        content = "Vai al menu principale " + "x" * 300

        is_valid, reason = validate_extracted_content(content)
        assert not is_valid
        assert "navigation text" in reason.lower()

    def test_empty_content_fails(self):
        """Test that empty content fails validation."""
        is_valid, reason = validate_extracted_content("")
        assert not is_valid
        assert "Empty content" in reason

    def test_whitespace_only_fails(self):
        """Test that whitespace-only content fails validation."""
        is_valid, reason = validate_extracted_content("   \n\t   ")
        assert not is_valid
        assert "Empty content" in reason

    def test_high_navigation_ratio_fails(self):
        """Test content with high navigation word ratio fails."""
        # Create content with many navigation patterns
        nav_content = "vai al menu cookie policy privacy policy mappa del sito contatti "
        content = nav_content * 10 + "some actual content here"

        is_valid, reason = validate_extracted_content(content)
        assert not is_valid
        # Could be either ratio or pattern count

    def test_starts_with_menu_fails(self):
        """Test content starting with 'menu' is flagged."""
        content = "Menu principale e navigazione " + "x" * 300

        is_valid, reason = validate_extracted_content(content)
        assert not is_valid

    def test_starts_with_home_fails(self):
        """Test content starting with 'home' is flagged."""
        content = "Home page del sito " + "x" * 300

        is_valid, reason = validate_extracted_content(content)
        assert not is_valid

    def test_starts_with_accedi_fails(self):
        """Test content starting with 'accedi' is flagged."""
        content = "Accedi al tuo account " + "x" * 300

        is_valid, reason = validate_extracted_content(content)
        assert not is_valid

    def test_starts_with_skip_to_fails(self):
        """Test content starting with 'skip to' is flagged."""
        content = "Skip to main content " + "x" * 300

        is_valid, reason = validate_extracted_content(content)
        assert not is_valid

    def test_exactly_200_chars_passes(self):
        """Test content with exactly 200 chars passes length check."""
        content = "x" * 200
        is_valid, reason = validate_extracted_content(content)
        assert is_valid
        assert reason == "OK"

    def test_199_chars_fails(self):
        """Test content with 199 chars fails length check."""
        content = "x" * 199
        is_valid, reason = validate_extracted_content(content)
        assert not is_valid
        assert "too short" in reason.lower()


class TestNormalizeWhitespace:
    """Tests for whitespace normalization."""

    def test_multiple_spaces_reduced(self):
        """Test that multiple spaces become single space."""
        text = "Hello    world"
        result = normalize_whitespace(text)
        assert "    " not in result
        assert "Hello world" in result

    def test_multiple_newlines_reduced(self):
        """Test that multiple newlines become double newline."""
        text = "Hello\n\n\n\nworld"
        result = normalize_whitespace(text)
        assert "\n\n\n" not in result

    def test_line_whitespace_stripped(self):
        """Test that leading/trailing whitespace per line is stripped."""
        text = "  Hello  \n  World  "
        result = normalize_whitespace(text)
        assert result == "Hello\nWorld"

    def test_empty_lines_removed(self):
        """Test that empty lines are removed."""
        text = "Hello\n\n\nWorld"
        result = normalize_whitespace(text)
        # Empty lines should be removed, leaving just Hello\nWorld
        assert result.count("\n") <= 1

    def test_preserves_single_spaces(self):
        """Test that single spaces are preserved."""
        text = "Hello world test"
        result = normalize_whitespace(text)
        assert result == "Hello world test"


class TestCleanItalianText:
    """Tests for Italian text cleaning."""

    def test_decodes_html_entities(self):
        """Test that HTML entities are decoded."""
        text = "Ciao &amp; mondo"
        result = clean_italian_text(text)
        assert "&" in result
        assert "&amp;" not in result

    def test_normalizes_curly_quotes(self):
        """Test that curly quotes are normalized."""
        text = "\u201cHello\u201d and \u2018world\u2019"
        result = clean_italian_text(text)
        assert '"' in result
        assert "'" in result

    def test_normalizes_dashes(self):
        """Test that em/en dashes are normalized."""
        text = "test\u2013dash\u2014test"  # en-dash and em-dash
        result = clean_italian_text(text)
        assert "\u2013" not in result  # no en-dash
        assert "\u2014" not in result  # no em-dash
        assert "-" in result

    def test_removes_zero_width_chars(self):
        """Test that zero-width characters are removed."""
        text = "Hello\u200bWorld\u200c\u200d\ufeff"
        result = clean_italian_text(text)
        assert "\u200b" not in result
        assert "\u200c" not in result
        assert "\u200d" not in result
        assert "\ufeff" not in result


class TestIsValidText:
    """Tests for text validity checking."""

    def test_empty_text_invalid(self):
        """Test that empty text is invalid."""
        assert not is_valid_text("")

    def test_whitespace_only_invalid(self):
        """Test that whitespace-only text is invalid."""
        assert not is_valid_text("   \n\t   ")

    def test_too_short_invalid(self):
        """Test that text below min_length is invalid."""
        assert not is_valid_text("Short", min_length=50)

    def test_sufficient_length_valid(self):
        """Test that text meeting min_length is valid."""
        text = "a" * 50
        assert is_valid_text(text, min_length=50)

    def test_special_chars_only_invalid(self):
        """Test that text with only special characters is invalid."""
        text = "!@#$%^&*()_+-=[]{}|;':\",./<>?" * 5
        assert not is_valid_text(text, min_length=10)

    def test_mixed_content_valid(self):
        """Test that text with alphanumeric content is valid."""
        text = "Questo è un documento italiano con numeri 12345"
        assert is_valid_text(text, min_length=10)

    def test_italian_accented_chars_valid(self):
        """Test that Italian accented characters are counted as valid."""
        text = "àèìòùéÀÈÌÒÙÉ" * 10
        assert is_valid_text(text, min_length=10)


class TestSanitizeHtmlEntities:
    """P1-B: Test HTML entity sanitization safety net."""

    def test_sanitize_decodes_named_entities(self):
        """Named HTML entities like &amp; are decoded."""
        from app.core.text.clean import sanitize_html_entities

        text = "lettera a) &amp; b) del D.Lgs."
        result = sanitize_html_entities(text)
        assert "&amp;" not in result
        assert "& b)" in result

    def test_sanitize_decodes_numeric_entities(self):
        """Numeric HTML entities like &#8217; are decoded."""
        from app.core.text.clean import sanitize_html_entities

        text = "l&#8217;articolo 42"
        result = sanitize_html_entities(text)
        assert "&#8217;" not in result
        assert "\u2019" in result or "'" in result

    def test_sanitize_decodes_hex_entities(self):
        """Hex HTML entities like &#xE0; are decoded."""
        from app.core.text.clean import sanitize_html_entities

        text = "l&#xE0; legge"
        result = sanitize_html_entities(text)
        assert "&#xE0;" not in result
        assert "à" in result

    def test_sanitize_leaves_clean_text_unchanged(self):
        """Clean text without HTML entities is returned unchanged."""
        from app.core.text.clean import sanitize_html_entities

        text = "Articolo 42 del decreto legislativo."
        result = sanitize_html_entities(text)
        assert result == text

    def test_sanitize_multiple_entities(self):
        """Multiple HTML entities in one text are all decoded."""
        from app.core.text.clean import sanitize_html_entities

        text = "&lt;Art. 1&gt; comma &amp; lettera"
        result = sanitize_html_entities(text)
        assert "&lt;" not in result
        assert "&gt;" not in result
        assert "&amp;" not in result
        assert "<Art. 1>" in result


class TestChunkContainsNavigation:
    """Tests for chunk-level navigation detection."""

    def test_multiple_patterns_detected(self):
        """Chunk with 2+ navigation patterns is flagged."""
        text = "Vai al menu principale. Cookie policy applicata. Contenuto reale del documento."
        assert chunk_contains_navigation(text) is True

    def test_single_pattern_short_chunk_detected(self):
        """Short chunk (<300 chars) with 1 navigation pattern is flagged."""
        text = "Vai al menu principale. Breve testo."
        assert len(text) < 300
        assert chunk_contains_navigation(text) is True

    def test_single_pattern_long_chunk_not_detected(self):
        """Long chunk (>=300 chars) with only 1 navigation pattern is NOT flagged."""
        text = "Cookie policy. " + "Questo documento contiene informazioni importanti. " * 20
        assert len(text) >= 300
        assert chunk_contains_navigation(text) is False

    def test_no_patterns_clean_text(self):
        """Clean text without any navigation patterns is NOT flagged."""
        text = (
            "L'articolo 42 del decreto legislativo stabilisce le modalità "
            "di calcolo dei contributi previdenziali per l'anno corrente."
        )
        assert chunk_contains_navigation(text) is False

    def test_case_insensitive(self):
        """Detection is case-insensitive."""
        text = "VAI AL MENU principale. COOKIE POLICY applicata."
        assert chunk_contains_navigation(text) is True

    def test_threshold_parameter(self):
        """Custom threshold is respected."""
        text = "Vai al menu. Cookie policy. Privacy policy. " + "x" * 300
        # 3 matches, default threshold=2 should flag
        assert chunk_contains_navigation(text, threshold=2) is True
        # But threshold=4 should not flag (only 3 matches, and text is long)
        assert chunk_contains_navigation(text, threshold=4) is False
