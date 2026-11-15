
from backend.app.integrations import i_deepl


def test_deepl_uebersetzung(monkeypatch):
    """Prüft, ob DeepL die konfigurierte Zielsprache erhält."""

    monkeypatch.setenv("DEEPL_API_KEY", "test-key")

    class FakeDeepLClient:
        def __init__(self, api_key, **kwargs):
            assert api_key == "test-key"

        def translate_text(self, text, source_lang, target_lang):
            assert text == "Guten Tag"
            assert source_lang == "DE"
            assert target_lang == "EN-US"

            class Result:
                text = "Hello"

            return Result()

    monkeypatch.setattr(
        i_deepl.deepl,
        "DeepLClient",
        FakeDeepLClient,
    )

    result = i_deepl.translate_text(
        "Guten Tag",
        target_lang="EN-US",
    )

    assert result == "Hello"
