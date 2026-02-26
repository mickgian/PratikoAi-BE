"""DEV-300: Tests for Studio SQLModel."""

import pytest

from app.models.studio import Studio


class TestStudioCreation:
    """Test Studio model creation and field defaults."""

    def test_studio_creation_valid(self) -> None:
        """Valid studio with required fields."""
        studio = Studio(name="Studio Rossi", slug="studio-rossi")

        assert studio.name == "Studio Rossi"
        assert studio.slug == "studio-rossi"
        assert studio.id is not None  # uuid4 auto-generated

    def test_studio_max_clients_default(self) -> None:
        """max_clients defaults to 100."""
        studio = Studio(name="Studio Bianchi", slug="studio-bianchi")
        assert studio.max_clients == 100

    def test_studio_max_clients_custom(self) -> None:
        """max_clients can be set to a custom value."""
        studio = Studio(name="Studio Verdi", slug="studio-verdi", max_clients=250)
        assert studio.max_clients == 250

    def test_studio_settings_jsonb(self) -> None:
        """JSONB settings field stores arbitrary dict."""
        settings = {"theme": "dark", "locale": "it_IT", "features": ["billing", "ocr"]}
        studio = Studio(name="Studio Config", slug="studio-config", settings=settings)

        assert studio.settings == settings
        assert studio.settings["theme"] == "dark"
        assert "ocr" in studio.settings["features"]

    def test_studio_settings_default_none(self) -> None:
        """Settings defaults to None when not provided."""
        studio = Studio(name="Studio Nulla", slug="studio-nulla")
        assert studio.settings is None

    def test_studio_uuid_uniqueness(self) -> None:
        """Two studios get different UUIDs."""
        s1 = Studio(name="A", slug="a")
        s2 = Studio(name="B", slug="b")
        assert s1.id != s2.id

    def test_studio_repr(self) -> None:
        """__repr__ includes name and slug."""
        studio = Studio(name="Studio Rossi", slug="studio-rossi")
        assert "Studio Rossi" in repr(studio)
        assert "studio-rossi" in repr(studio)

    def test_studio_to_dict(self) -> None:
        """to_dict returns serialisable dict."""
        studio = Studio(name="Studio Dict", slug="studio-dict", max_clients=50, settings={"k": "v"})
        d = studio.to_dict()

        assert d["name"] == "Studio Dict"
        assert d["slug"] == "studio-dict"
        assert d["max_clients"] == 50
        assert d["settings"] == {"k": "v"}
        assert isinstance(d["id"], str)
