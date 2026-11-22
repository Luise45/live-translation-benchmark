
from app.integrations import i_deepl


def test_deepl_uebersetzung(monkeypatch):
    """Prüft, ob DeepL die konfigurierte Zielsprache erhält."""

    monkeypatch.setenv("DEEPL_API_KEY", "test-key")

    class FakeDeepLClient:
        def __init__(self, api_key, **kwargs):
            assert api_key == "test-key"

        def close(self):
            pass

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


def test_streaming_reuses_client_and_isolates_runs(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setenv("DEEPL_API_KEY", "test-key")
    clients = []

    class FakeClient:
        def __init__(self, api_key, **options):
            assert options == {"timeout_s": 10, "max_retries": 0}
            self.closed = False
            clients.append(self)

        def translate_text(self, text, **languages):
            assert not self.closed
            return SimpleNamespace(text="translated " + text)

        def close(self):
            self.closed = True

    monkeypatch.setattr(i_deepl.deepl, "DeepLClient", FakeClient)
    first = i_deepl.DeepLTranslator()
    assert first.translate("one") == "translated one"
    assert first.translate("two") == "translated two"
    assert len(clients) == 1
    first.close()
    assert clients[0].closed

    second = i_deepl.DeepLTranslator()
    second.translate("three")
    assert len(clients) == 2
    second.close()


def test_standalone_translation_closes_client_on_failure(monkeypatch):
    import pytest
    from types import SimpleNamespace

    monkeypatch.setenv("DEEPL_API_KEY", "test-key")
    closed = []

    def fail(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(i_deepl.deepl, "DeepLClient", lambda *args, **kwargs:
        SimpleNamespace(translate_text=fail, close=lambda: closed.append(True)))
    with pytest.raises(RuntimeError, match="simulated failure"):
        i_deepl.translate_text("text")
    assert closed == [True]
