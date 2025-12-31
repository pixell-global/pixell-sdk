"""Tests for Translation Context."""

import pytest
from pixell.sdk.translation.context import TranslationContext
from pixell.sdk.translation.interface import Translator, NoOpTranslator


class MockTranslator(Translator):
    """Mock translator for testing."""

    def __init__(self, translate_fn=None, detect_fn=None):
        self._translate_fn = translate_fn
        self._detect_fn = detect_fn
        self.translate_calls = []
        self.detect_calls = []

    async def translate(self, text: str, from_lang: str, to_lang: str) -> str:
        self.translate_calls.append((text, from_lang, to_lang))
        if self._translate_fn:
            return self._translate_fn(text, from_lang, to_lang)
        return f"[{to_lang}] {text}"

    async def detect_language(self, text: str) -> str:
        self.detect_calls.append(text)
        if self._detect_fn:
            return self._detect_fn(text)
        return "en"


class FailingTranslator(Translator):
    """Translator that always fails."""

    async def translate(self, text: str, from_lang: str, to_lang: str) -> str:
        raise Exception("Translation failed")

    async def detect_language(self, text: str) -> str:
        raise Exception("Detection failed")


class TestTranslationContextCreation:
    """Tests for TranslationContext initialization."""

    def test_create_default(self):
        ctx = TranslationContext()
        assert ctx.translator is None
        assert ctx.user_language == "en"
        assert ctx.agent_language == "en"

    def test_create_with_translator(self):
        translator = MockTranslator()
        ctx = TranslationContext(translator=translator, user_language="ko")
        assert ctx.translator is translator
        assert ctx.user_language == "ko"
        assert ctx.agent_language == "en"

    def test_create_with_all_params(self):
        translator = MockTranslator()
        ctx = TranslationContext(
            translator=translator,
            user_language="ko",
            agent_language="ja",
        )
        assert ctx.user_language == "ko"
        assert ctx.agent_language == "ja"


class TestNeedsTranslation:
    """Tests for needs_translation property."""

    def test_needs_translation_true(self):
        translator = MockTranslator()
        ctx = TranslationContext(translator=translator, user_language="ko")
        assert ctx.needs_translation is True

    def test_needs_translation_false_same_language(self):
        translator = MockTranslator()
        ctx = TranslationContext(translator=translator, user_language="en")
        assert ctx.needs_translation is False

    def test_needs_translation_false_no_translator(self):
        ctx = TranslationContext(translator=None, user_language="ko")
        assert ctx.needs_translation is False

    def test_needs_translation_false_both_conditions(self):
        ctx = TranslationContext(translator=None, user_language="en")
        assert ctx.needs_translation is False


class TestTranslateFromUser:
    """Tests for translate_from_user method."""

    @pytest.mark.asyncio
    async def test_translate_from_user_basic(self):
        translator = MockTranslator()
        ctx = TranslationContext(translator=translator, user_language="ko")

        result = await ctx.translate_from_user("안녕하세요")

        assert result == "[en] 안녕하세요"
        assert len(translator.translate_calls) == 1
        assert translator.translate_calls[0] == ("안녕하세요", "ko", "en")

    @pytest.mark.asyncio
    async def test_translate_from_user_custom_target(self):
        translator = MockTranslator()
        ctx = TranslationContext(translator=translator, user_language="ko")

        result = await ctx.translate_from_user("안녕하세요", to_lang="ja")

        assert result == "[ja] 안녕하세요"
        assert translator.translate_calls[0] == ("안녕하세요", "ko", "ja")

    @pytest.mark.asyncio
    async def test_translate_from_user_no_translation_needed(self):
        translator = MockTranslator()
        ctx = TranslationContext(translator=translator, user_language="en")

        result = await ctx.translate_from_user("Hello")

        # Same language, no translation
        assert result == "Hello"
        assert len(translator.translate_calls) == 0

    @pytest.mark.asyncio
    async def test_translate_from_user_no_translator(self):
        ctx = TranslationContext(translator=None, user_language="ko")

        result = await ctx.translate_from_user("안녕하세요")

        # No translator, returns unchanged
        assert result == "안녕하세요"

    @pytest.mark.asyncio
    async def test_translate_from_user_same_target(self):
        translator = MockTranslator()
        ctx = TranslationContext(translator=translator, user_language="ko")

        # Translate from ko to ko
        result = await ctx.translate_from_user("안녕하세요", to_lang="ko")

        # Same language, no translation
        assert result == "안녕하세요"
        assert len(translator.translate_calls) == 0

    @pytest.mark.asyncio
    async def test_translate_from_user_error_fallback(self):
        translator = FailingTranslator()
        ctx = TranslationContext(translator=translator, user_language="ko")

        result = await ctx.translate_from_user("안녕하세요")

        # On error, returns original text
        assert result == "안녕하세요"


class TestTranslateToUser:
    """Tests for translate_to_user method."""

    @pytest.mark.asyncio
    async def test_translate_to_user_basic(self):
        translator = MockTranslator()
        ctx = TranslationContext(translator=translator, user_language="ko")

        result = await ctx.translate_to_user("Hello")

        assert result == "[ko] Hello"
        assert translator.translate_calls[0] == ("Hello", "en", "ko")

    @pytest.mark.asyncio
    async def test_translate_to_user_custom_source(self):
        translator = MockTranslator()
        ctx = TranslationContext(translator=translator, user_language="ko")

        result = await ctx.translate_to_user("こんにちは", from_lang="ja")

        assert result == "[ko] こんにちは"
        assert translator.translate_calls[0] == ("こんにちは", "ja", "ko")

    @pytest.mark.asyncio
    async def test_translate_to_user_no_translation_needed(self):
        translator = MockTranslator()
        ctx = TranslationContext(translator=translator, user_language="en")

        result = await ctx.translate_to_user("Hello")

        assert result == "Hello"
        assert len(translator.translate_calls) == 0

    @pytest.mark.asyncio
    async def test_translate_to_user_no_translator(self):
        ctx = TranslationContext(translator=None, user_language="ko")

        result = await ctx.translate_to_user("Hello")

        assert result == "Hello"

    @pytest.mark.asyncio
    async def test_translate_to_user_same_source(self):
        translator = MockTranslator()
        ctx = TranslationContext(translator=translator, user_language="ko")

        result = await ctx.translate_to_user("안녕하세요", from_lang="ko")

        assert result == "안녕하세요"
        assert len(translator.translate_calls) == 0

    @pytest.mark.asyncio
    async def test_translate_to_user_error_fallback(self):
        translator = FailingTranslator()
        ctx = TranslationContext(translator=translator, user_language="ko")

        result = await ctx.translate_to_user("Hello")

        assert result == "Hello"


class TestDetectAndSetLanguage:
    """Tests for detect_and_set_language method."""

    @pytest.mark.asyncio
    async def test_detect_and_set_language(self):
        def detect(text):
            if "안녕" in text:
                return "ko"
            return "en"

        translator = MockTranslator(detect_fn=detect)
        ctx = TranslationContext(translator=translator, user_language="en")

        result = await ctx.detect_and_set_language("안녕하세요")

        assert result == "ko"
        assert ctx.user_language == "ko"

    @pytest.mark.asyncio
    async def test_detect_and_set_language_no_translator(self):
        ctx = TranslationContext(translator=None, user_language="en")

        result = await ctx.detect_and_set_language("안녕하세요")

        # No translator, returns current user_language
        assert result == "en"
        assert ctx.user_language == "en"

    @pytest.mark.asyncio
    async def test_detect_and_set_language_error_fallback(self):
        translator = FailingTranslator()
        ctx = TranslationContext(translator=translator, user_language="en")

        result = await ctx.detect_and_set_language("안녕하세요")

        # On error, returns current user_language
        assert result == "en"
        assert ctx.user_language == "en"


class TestTranslateBatchToUser:
    """Tests for translate_batch_to_user method."""

    @pytest.mark.asyncio
    async def test_translate_batch_to_user(self):
        translator = MockTranslator()
        ctx = TranslationContext(translator=translator, user_language="ko")

        texts = ["Hello", "World", "Test"]
        results = await ctx.translate_batch_to_user(texts)

        assert len(results) == 3
        assert results[0] == "[ko] Hello"
        assert results[1] == "[ko] World"
        assert results[2] == "[ko] Test"

    @pytest.mark.asyncio
    async def test_translate_batch_to_user_custom_source(self):
        translator = MockTranslator()
        ctx = TranslationContext(translator=translator, user_language="ko")

        texts = ["こんにちは", "さようなら"]
        await ctx.translate_batch_to_user(texts, from_lang="ja")

        assert translator.translate_calls[0][1] == "ja"

    @pytest.mark.asyncio
    async def test_translate_batch_to_user_no_translation_needed(self):
        translator = MockTranslator()
        ctx = TranslationContext(translator=translator, user_language="en")

        texts = ["Hello", "World"]
        results = await ctx.translate_batch_to_user(texts)

        assert results == texts
        assert len(translator.translate_calls) == 0

    @pytest.mark.asyncio
    async def test_translate_batch_to_user_error_fallback(self):
        translator = FailingTranslator()
        ctx = TranslationContext(translator=translator, user_language="ko")

        texts = ["Hello", "World"]
        results = await ctx.translate_batch_to_user(texts)

        # On error, returns original texts
        assert results == texts

    @pytest.mark.asyncio
    async def test_translate_batch_to_user_empty(self):
        translator = MockTranslator()
        ctx = TranslationContext(translator=translator, user_language="ko")

        results = await ctx.translate_batch_to_user([])
        assert results == []


class TestTranslationContextIntegration:
    """Integration tests for TranslationContext."""

    @pytest.mark.asyncio
    async def test_full_translation_flow(self):
        """Test complete translation flow: user -> agent -> user."""
        translations = {
            (
                "안녕하세요, 게임 콘텐츠를 찾아주세요",
                "ko",
                "en",
            ): "Hello, please find gaming content",
            ("Found 10 gaming creators for you", "en", "ko"): "10명의 게임 크리에이터를 찾았습니다",
        }

        def translate_fn(text, from_lang, to_lang):
            key = (text, from_lang, to_lang)
            return translations.get(key, f"[{to_lang}] {text}")

        translator = MockTranslator(translate_fn=translate_fn)
        ctx = TranslationContext(translator=translator, user_language="ko")

        # User sends Korean message
        user_input = "안녕하세요, 게임 콘텐츠를 찾아주세요"
        english_input = await ctx.translate_from_user(user_input)
        assert english_input == "Hello, please find gaming content"

        # Agent processes in English and generates response
        agent_response = "Found 10 gaming creators for you"

        # Translate response back to Korean
        korean_response = await ctx.translate_to_user(agent_response)
        assert korean_response == "10명의 게임 크리에이터를 찾았습니다"

    @pytest.mark.asyncio
    async def test_language_detection_and_translation(self):
        """Test detecting language then translating."""

        def detect(text):
            if any(c >= "가" and c <= "힣" for c in text):
                return "ko"
            elif any(c >= "あ" and c <= "ん" for c in text):
                return "ja"
            return "en"

        translator = MockTranslator(detect_fn=detect)
        ctx = TranslationContext(translator=translator, user_language="en")

        # Detect Korean
        await ctx.detect_and_set_language("안녕하세요")
        assert ctx.user_language == "ko"

        # Now translate back to user
        result = await ctx.translate_to_user("Hello!")
        assert result == "[ko] Hello!"

    @pytest.mark.asyncio
    async def test_multilingual_batch(self):
        """Test batch translation for multiple items."""
        translator = MockTranslator()
        ctx = TranslationContext(translator=translator, user_language="ko")

        items = [
            "Gaming",
            "Fitness",
            "Cooking",
            "Music",
            "Travel",
        ]

        results = await ctx.translate_batch_to_user(items)

        assert len(results) == 5
        assert all("[ko]" in r for r in results)

    @pytest.mark.asyncio
    async def test_same_language_optimization(self):
        """Verify no unnecessary translations when languages match."""
        translator = MockTranslator()
        ctx = TranslationContext(translator=translator, user_language="en", agent_language="en")

        # Should not translate
        result1 = await ctx.translate_from_user("Hello")
        result2 = await ctx.translate_to_user("World")
        results = await ctx.translate_batch_to_user(["A", "B", "C"])

        assert result1 == "Hello"
        assert result2 == "World"
        assert results == ["A", "B", "C"]
        assert len(translator.translate_calls) == 0

    @pytest.mark.asyncio
    async def test_with_noop_translator(self):
        """Test using NoOpTranslator."""
        translator = NoOpTranslator()
        ctx = TranslationContext(translator=translator, user_language="ko")

        # NoOpTranslator returns text unchanged
        result = await ctx.translate_from_user("안녕하세요")
        assert result == "안녕하세요"

        result = await ctx.translate_to_user("Hello")
        assert result == "Hello"


class TestTranslationContextEdgeCases:
    """Edge case tests for TranslationContext."""

    @pytest.mark.asyncio
    async def test_empty_strings(self):
        translator = MockTranslator()
        ctx = TranslationContext(translator=translator, user_language="ko")

        result = await ctx.translate_from_user("")
        assert result == "[en] "

        result = await ctx.translate_to_user("")
        assert result == "[ko] "

    @pytest.mark.asyncio
    async def test_unicode_preservation(self):
        translator = MockTranslator()
        ctx = TranslationContext(translator=translator, user_language="ko")

        # Test various unicode
        texts = [
            "Hello 👋",
            "안녕하세요 🎮",
            "こんにちは 🍜",
            "مرحبا 🌍",
        ]

        for text in texts:
            result = await ctx.translate_to_user(text)
            assert text in result

    @pytest.mark.asyncio
    async def test_changing_user_language(self):
        """Test changing user language mid-session."""
        translator = MockTranslator()
        ctx = TranslationContext(translator=translator, user_language="ko")

        result1 = await ctx.translate_to_user("Hello")
        assert result1 == "[ko] Hello"

        # User switches to Japanese
        ctx.user_language = "ja"

        result2 = await ctx.translate_to_user("Hello")
        assert result2 == "[ja] Hello"

    @pytest.mark.asyncio
    async def test_three_way_translation(self):
        """Test translation between non-English languages."""
        translator = MockTranslator()
        ctx = TranslationContext(
            translator=translator,
            user_language="ko",
            agent_language="ja",
        )

        # Korean user, Japanese agent
        await ctx.translate_from_user("안녕하세요")
        assert translator.translate_calls[-1] == ("안녕하세요", "ko", "ja")

        await ctx.translate_to_user("こんにちは")
        assert translator.translate_calls[-1] == ("こんにちは", "ja", "ko")
