"""Translation Context - Request-scoped translation context.

Provides convenient methods for translating to/from the user's language.

Example:
    translator = OpenAITranslator()
    ctx = TranslationContext(translator=translator, user_language="ko")

    # User sends Korean message
    english_input = await ctx.translate_from_user(user_message)

    # Process in English...

    # Translate response back to Korean
    korean_response = await ctx.translate_to_user(english_response)
"""

from typing import Optional
import logging

from pixell.sdk.translation.interface import Translator

logger = logging.getLogger(__name__)


class TranslationContext:
    """Translation context for a single request/session.

    Manages translation state and provides convenience methods
    for translating between the user's language and the agent's
    working language (typically English).

    Attributes:
        translator: Translator implementation (provided by agent)
        user_language: User's preferred language (from request metadata)
        agent_language: Agent's working language (default: English)
    """

    def __init__(
        self,
        translator: Optional[Translator] = None,
        user_language: str = "en",
        agent_language: str = "en",
    ) -> None:
        """Initialize translation context.

        Args:
            translator: Translator implementation (None disables translation)
            user_language: User's language code (ISO 639-1)
            agent_language: Agent's working language code
        """
        self.translator = translator
        self.user_language = user_language
        self.agent_language = agent_language

    @property
    def needs_translation(self) -> bool:
        """Check if translation is needed.

        Returns True if user language differs from agent language
        and a translator is available.
        """
        return self.translator is not None and self.user_language != self.agent_language

    async def translate_from_user(
        self,
        text: str,
        to_lang: Optional[str] = None,
    ) -> str:
        """Translate user input to agent's working language.

        If translation is not needed or not available, returns text unchanged.

        Args:
            text: User's input text (in user_language)
            to_lang: Target language (default: agent_language)

        Returns:
            Translated text
        """
        if not self.needs_translation:
            return text

        target = to_lang or self.agent_language

        if self.user_language == target:
            return text

        try:
            translated = await self.translator.translate(
                text,
                from_lang=self.user_language,
                to_lang=target,
            )
            logger.debug(
                f"Translated from {self.user_language} to {target}: "
                f"{text[:50]}... -> {translated[:50]}..."
            )
            return translated
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return text

    async def translate_to_user(
        self,
        text: str,
        from_lang: Optional[str] = None,
    ) -> str:
        """Translate agent output to user's language.

        If translation is not needed or not available, returns text unchanged.

        Args:
            text: Agent's output text (in agent_language)
            from_lang: Source language (default: agent_language)

        Returns:
            Translated text
        """
        if not self.needs_translation:
            return text

        source = from_lang or self.agent_language

        if source == self.user_language:
            return text

        try:
            translated = await self.translator.translate(
                text,
                from_lang=source,
                to_lang=self.user_language,
            )
            logger.debug(
                f"Translated from {source} to {self.user_language}: "
                f"{text[:50]}... -> {translated[:50]}..."
            )
            return translated
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return text

    async def detect_and_set_language(self, text: str) -> str:
        """Detect language from text and update user_language.

        Useful when user language is not known beforehand.

        Args:
            text: Text to detect language from

        Returns:
            Detected language code
        """
        if not self.translator:
            return self.user_language

        try:
            detected = await self.translator.detect_language(text)
            self.user_language = detected
            logger.debug(f"Detected user language: {detected}")
            return detected
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return self.user_language

    async def translate_batch_to_user(
        self,
        texts: list[str],
        from_lang: Optional[str] = None,
    ) -> list[str]:
        """Translate multiple texts to user's language.

        Args:
            texts: List of texts in agent language
            from_lang: Source language (default: agent_language)

        Returns:
            List of translated texts
        """
        if not self.needs_translation:
            return texts

        source = from_lang or self.agent_language

        if source == self.user_language:
            return texts

        try:
            return await self.translator.translate_batch(
                texts,
                from_lang=source,
                to_lang=self.user_language,
            )
        except Exception as e:
            logger.error(f"Batch translation failed: {e}")
            return texts
