"""Translation Interface - Abstract base class for agent translators.

Agents implement this interface to provide translation capabilities.
The SDK provides the interface, but agents bring their own LLM for
translation (they pay for their own tokens).

Example implementation using OpenAI:

    from pixell.sdk.translation import Translator
    import openai

    class OpenAITranslator(Translator):
        def __init__(self, model: str = "gpt-4o-mini"):
            self.model = model
            self.client = openai.AsyncOpenAI()

        async def translate(self, text: str, from_lang: str, to_lang: str) -> str:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"Translate the following text from {from_lang} to {to_lang}. Only output the translation, nothing else."},
                    {"role": "user", "content": text}
                ]
            )
            return response.choices[0].message.content

        async def detect_language(self, text: str) -> str:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Detect the language of the following text. Reply with only the ISO 639-1 language code (e.g., 'en', 'ko', 'ja')."},
                    {"role": "user", "content": text}
                ]
            )
            return response.choices[0].message.content.strip().lower()
"""

from abc import ABC, abstractmethod
from typing import Optional


class Translator(ABC):
    """Abstract interface for translation.

    Agents implement this interface to provide translation capabilities.
    The implementation can use any LLM or translation service.

    Key design decisions:
    - SDK provides interface, agents bring own LLM
    - Agents pay for their own translation tokens
    - Interface is simple: translate() and detect_language()
    """

    @abstractmethod
    async def translate(
        self,
        text: str,
        from_lang: str,
        to_lang: str,
    ) -> str:
        """Translate text between languages.

        Args:
            text: Text to translate
            from_lang: Source language code (ISO 639-1, e.g., "en", "ko")
            to_lang: Target language code (ISO 639-1)

        Returns:
            Translated text
        """
        pass

    @abstractmethod
    async def detect_language(self, text: str) -> str:
        """Detect the language of text.

        Args:
            text: Text to analyze

        Returns:
            ISO 639-1 language code (e.g., "en", "ko", "ja")
        """
        pass

    async def translate_batch(
        self,
        texts: list[str],
        from_lang: str,
        to_lang: str,
    ) -> list[str]:
        """Translate multiple texts.

        Default implementation translates sequentially.
        Override for batch optimization.

        Args:
            texts: List of texts to translate
            from_lang: Source language code
            to_lang: Target language code

        Returns:
            List of translated texts
        """
        results = []
        for text in texts:
            translated = await self.translate(text, from_lang, to_lang)
            results.append(translated)
        return results


class NoOpTranslator(Translator):
    """No-op translator that returns text unchanged.

    Useful for testing or when translation is not needed.
    """

    async def translate(
        self,
        text: str,
        from_lang: str,
        to_lang: str,
    ) -> str:
        return text

    async def detect_language(self, text: str) -> str:
        return "en"
