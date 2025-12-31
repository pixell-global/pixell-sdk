"""Tests for Translation Interface."""

import pytest
from pixell.sdk.translation.interface import Translator, NoOpTranslator


class MockTranslator(Translator):
    """Mock translator for testing."""

    def __init__(self, translate_fn=None, detect_fn=None):
        self._translate_fn = translate_fn
        self._detect_fn = detect_fn
        self.translate_calls = []
        self.detect_calls = []
        self.batch_calls = []

    async def translate(self, text: str, from_lang: str, to_lang: str) -> str:
        self.translate_calls.append((text, from_lang, to_lang))
        if self._translate_fn:
            return self._translate_fn(text, from_lang, to_lang)
        # Default: prefix with target language marker
        return f"[{to_lang}] {text}"

    async def detect_language(self, text: str) -> str:
        self.detect_calls.append(text)
        if self._detect_fn:
            return self._detect_fn(text)
        return "en"


class FailingTranslator(Translator):
    """Translator that always fails."""

    async def translate(self, text: str, from_lang: str, to_lang: str) -> str:
        raise Exception("Translation service unavailable")

    async def detect_language(self, text: str) -> str:
        raise Exception("Detection service unavailable")


class TestTranslatorInterface:
    """Tests for Translator abstract class."""

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            Translator()

    @pytest.mark.asyncio
    async def test_mock_translator_works(self):
        translator = MockTranslator()
        result = await translator.translate("Hello", "en", "ko")
        assert result == "[ko] Hello"

    @pytest.mark.asyncio
    async def test_custom_translate_function(self):
        def custom_translate(text, from_lang, to_lang):
            if to_lang == "ko":
                return "안녕하세요"
            return text

        translator = MockTranslator(translate_fn=custom_translate)
        result = await translator.translate("Hello", "en", "ko")
        assert result == "안녕하세요"

    @pytest.mark.asyncio
    async def test_detect_language(self):
        def detect(text):
            if "안녕" in text:
                return "ko"
            elif "こんにちは" in text:
                return "ja"
            return "en"

        translator = MockTranslator(detect_fn=detect)

        assert await translator.detect_language("Hello") == "en"
        assert await translator.detect_language("안녕하세요") == "ko"
        assert await translator.detect_language("こんにちは") == "ja"


class TestTranslateBatch:
    """Tests for translate_batch default implementation."""

    @pytest.mark.asyncio
    async def test_translate_batch_default(self):
        translator = MockTranslator()

        texts = ["Hello", "World", "Test"]
        results = await translator.translate_batch(texts, "en", "ko")

        assert len(results) == 3
        assert results[0] == "[ko] Hello"
        assert results[1] == "[ko] World"
        assert results[2] == "[ko] Test"

    @pytest.mark.asyncio
    async def test_translate_batch_records_calls(self):
        translator = MockTranslator()

        texts = ["One", "Two"]
        await translator.translate_batch(texts, "en", "ja")

        # Should have made 2 individual translate calls
        assert len(translator.translate_calls) == 2
        assert translator.translate_calls[0] == ("One", "en", "ja")
        assert translator.translate_calls[1] == ("Two", "en", "ja")

    @pytest.mark.asyncio
    async def test_translate_batch_empty(self):
        translator = MockTranslator()
        results = await translator.translate_batch([], "en", "ko")
        assert results == []


class TestNoOpTranslator:
    """Tests for NoOpTranslator."""

    @pytest.mark.asyncio
    async def test_translate_returns_unchanged(self):
        translator = NoOpTranslator()
        result = await translator.translate("Hello, World!", "en", "ko")
        assert result == "Hello, World!"

    @pytest.mark.asyncio
    async def test_translate_any_language(self):
        translator = NoOpTranslator()

        # Any language combination returns unchanged
        assert await translator.translate("Text", "ko", "ja") == "Text"
        assert await translator.translate("안녕", "ko", "en") == "안녕"
        assert await translator.translate("Test", "zh", "es") == "Test"

    @pytest.mark.asyncio
    async def test_detect_language_returns_english(self):
        translator = NoOpTranslator()

        assert await translator.detect_language("Hello") == "en"
        assert await translator.detect_language("안녕하세요") == "en"
        assert await translator.detect_language("") == "en"

    @pytest.mark.asyncio
    async def test_batch_translate_returns_unchanged(self):
        translator = NoOpTranslator()
        texts = ["A", "B", "C"]
        results = await translator.translate_batch(texts, "en", "ko")
        assert results == texts


class TestTranslatorImplementation:
    """Tests for implementing custom translators."""

    @pytest.mark.asyncio
    async def test_custom_implementation(self):
        """Test that custom implementations work."""

        class ReverseTranslator(Translator):
            """Silly translator that reverses text."""

            async def translate(self, text: str, from_lang: str, to_lang: str) -> str:
                return text[::-1]

            async def detect_language(self, text: str) -> str:
                return "reverse"

        translator = ReverseTranslator()
        assert await translator.translate("Hello", "en", "ko") == "olleH"
        assert await translator.detect_language("anything") == "reverse"

    @pytest.mark.asyncio
    async def test_stateful_translator(self):
        """Test translator that maintains state."""

        class CountingTranslator(Translator):
            def __init__(self):
                self.count = 0

            async def translate(self, text: str, from_lang: str, to_lang: str) -> str:
                self.count += 1
                return f"{text} (translation #{self.count})"

            async def detect_language(self, text: str) -> str:
                return "en"

        translator = CountingTranslator()

        r1 = await translator.translate("First", "en", "ko")
        r2 = await translator.translate("Second", "en", "ko")
        r3 = await translator.translate("Third", "en", "ko")

        assert r1 == "First (translation #1)"
        assert r2 == "Second (translation #2)"
        assert r3 == "Third (translation #3)"
        assert translator.count == 3

    @pytest.mark.asyncio
    async def test_overridden_batch_translate(self):
        """Test translator with custom batch implementation."""

        class EfficientTranslator(Translator):
            """Translator with optimized batch."""

            def __init__(self):
                self.batch_called = False

            async def translate(self, text: str, from_lang: str, to_lang: str) -> str:
                return f"[{to_lang}] {text}"

            async def detect_language(self, text: str) -> str:
                return "en"

            async def translate_batch(
                self, texts: list[str], from_lang: str, to_lang: str
            ) -> list[str]:
                self.batch_called = True
                # "Efficient" batch - single operation
                return [f"[{to_lang}:batch] {t}" for t in texts]

        translator = EfficientTranslator()
        results = await translator.translate_batch(["A", "B"], "en", "ko")

        assert translator.batch_called is True
        assert results[0] == "[ko:batch] A"
        assert results[1] == "[ko:batch] B"


class TestTranslatorEdgeCases:
    """Edge case tests for translators."""

    @pytest.mark.asyncio
    async def test_empty_string(self):
        translator = MockTranslator()
        result = await translator.translate("", "en", "ko")
        assert result == "[ko] "

    @pytest.mark.asyncio
    async def test_unicode_text(self):
        translator = MockTranslator()

        # Korean
        result = await translator.translate("안녕하세요", "ko", "en")
        assert result == "[en] 안녕하세요"

        # Japanese
        result = await translator.translate("こんにちは", "ja", "en")
        assert result == "[en] こんにちは"

        # Emoji
        result = await translator.translate("Hello 👋", "en", "ko")
        assert result == "[ko] Hello 👋"

    @pytest.mark.asyncio
    async def test_multiline_text(self):
        translator = MockTranslator()
        text = "Line 1\nLine 2\nLine 3"
        result = await translator.translate(text, "en", "ko")
        assert result == f"[ko] {text}"

    @pytest.mark.asyncio
    async def test_very_long_text(self):
        translator = MockTranslator()
        long_text = "x" * 10000
        result = await translator.translate(long_text, "en", "ko")
        assert result == f"[ko] {long_text}"

    @pytest.mark.asyncio
    async def test_same_language_translation(self):
        """Translating to same language."""
        translator = MockTranslator()
        await translator.translate("Hello", "en", "en")
        # Should still call translate (implementation decides behavior)
        assert len(translator.translate_calls) == 1

    @pytest.mark.asyncio
    async def test_unknown_language_codes(self):
        """Test with unusual language codes."""
        translator = MockTranslator()
        result = await translator.translate("Text", "xx", "yy")
        assert result == "[yy] Text"
