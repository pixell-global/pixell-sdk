"""Shared fixtures for SDK tests."""

import pytest
import asyncio
from typing import AsyncGenerator, Any
from unittest.mock import AsyncMock, MagicMock

# A2A Protocol fixtures
from pixell.sdk.a2a.protocol import (
    A2AMessage,
    TextPart,
    DataPart,
    JSONRPCRequest,
    TaskState,
)
from pixell.sdk.a2a.streaming import SSEStream
from pixell.sdk.a2a.handlers import A2AHandler, MessageContext, ResponseContext

# Plan Mode fixtures
from pixell.sdk.plan_mode import (
    Phase,
    PlanModeContext,
    Question,
    QuestionType,
    QuestionOption,
    DiscoveredItem,
    ClarificationNeeded,
    SelectionRequired,
    SearchPlanPreview,
)

# Translation fixtures
from pixell.sdk.translation import Translator, TranslationContext


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# A2A Protocol Fixtures
# =============================================================================


@pytest.fixture
def sample_text_part() -> TextPart:
    """Sample text part."""
    return TextPart(text="Hello, world!")


@pytest.fixture
def sample_data_part() -> DataPart:
    """Sample data part."""
    return DataPart(data={"key": "value", "count": 42})


@pytest.fixture
def sample_user_message() -> A2AMessage:
    """Sample user message."""
    return A2AMessage.user("Find me some gaming content on TikTok")


@pytest.fixture
def sample_agent_message() -> A2AMessage:
    """Sample agent message."""
    return A2AMessage.agent("I found 10 relevant creators for you.")


@pytest.fixture
def sample_jsonrpc_request() -> JSONRPCRequest:
    """Sample JSON-RPC request."""
    return JSONRPCRequest(
        method="message/send",
        params={
            "message": {
                "messageId": "test-msg-123",
                "role": "user",
                "parts": [{"text": "Hello"}],
            },
            "sessionId": "test-session-456",
            "metadata": {"language": "en"},
        },
        id="req-001",
    )


@pytest.fixture
def sample_respond_request() -> JSONRPCRequest:
    """Sample respond JSON-RPC request."""
    return JSONRPCRequest(
        method="respond",
        params={
            "clarificationId": "clarify-123",
            "answers": {"topic": "gaming", "depth": "moderate"},
            "sessionId": "test-session-456",
        },
        id="req-002",
    )


@pytest.fixture
async def sse_stream() -> AsyncGenerator[SSEStream, None]:
    """Provide a fresh SSE stream."""
    stream = SSEStream()
    yield stream
    stream.close()


@pytest.fixture
def a2a_handler() -> A2AHandler:
    """Fresh A2A handler."""
    return A2AHandler()


# =============================================================================
# Plan Mode Fixtures
# =============================================================================


@pytest.fixture
def sample_questions() -> list[Question]:
    """Sample clarification questions."""
    return [
        Question(
            id="topic",
            type=QuestionType.FREE_TEXT,
            question="What topic are you interested in?",
            header="Topic",
            placeholder="e.g., gaming, fitness",
        ),
        Question(
            id="depth",
            type=QuestionType.SINGLE_CHOICE,
            question="How deep should the research be?",
            header="Depth",
            options=[
                QuestionOption(id="quick", label="Quick", description="Top 5 results"),
                QuestionOption(id="moderate", label="Moderate", description="Top 15 results"),
                QuestionOption(id="deep", label="Deep", description="30+ results"),
            ],
        ),
        Question(
            id="features",
            type=QuestionType.MULTIPLE_CHOICE,
            question="Which features do you want?",
            header="Features",
            options=[
                QuestionOption(id="analytics", label="Analytics"),
                QuestionOption(id="export", label="Export"),
                QuestionOption(id="alerts", label="Alerts"),
            ],
        ),
    ]


@pytest.fixture
def sample_discovered_items() -> list[DiscoveredItem]:
    """Sample discovered items."""
    return [
        DiscoveredItem(
            id="r/gaming",
            name="r/gaming",
            description="Gaming discussions and news",
            metadata={"subscribers": 35000000, "posts_per_day": 500},
        ),
        DiscoveredItem(
            id="r/pcgaming",
            name="r/pcgaming",
            description="PC gaming community",
            metadata={"subscribers": 5000000, "posts_per_day": 150},
        ),
        DiscoveredItem(
            id="r/indiegaming",
            name="r/indiegaming",
            description="Independent game development",
            metadata={"subscribers": 500000, "posts_per_day": 30},
        ),
    ]


@pytest.fixture
async def plan_mode_context(sse_stream: SSEStream) -> PlanModeContext:
    """Plan mode context with SSE stream."""
    return PlanModeContext(
        stream=sse_stream,
        supported_phases=[Phase.CLARIFICATION, Phase.DISCOVERY, Phase.SELECTION, Phase.PREVIEW],
        agent_id="test-agent",
    )


# =============================================================================
# Translation Fixtures
# =============================================================================


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


@pytest.fixture
def mock_translator() -> MockTranslator:
    """Mock translator instance."""
    return MockTranslator()


@pytest.fixture
def translation_context(mock_translator: MockTranslator) -> TranslationContext:
    """Translation context with mock translator."""
    return TranslationContext(
        translator=mock_translator,
        user_language="ko",
        agent_language="en",
    )


@pytest.fixture
def translation_context_same_lang(mock_translator: MockTranslator) -> TranslationContext:
    """Translation context where user and agent language match."""
    return TranslationContext(
        translator=mock_translator,
        user_language="en",
        agent_language="en",
    )


@pytest.fixture
def translation_context_no_translator() -> TranslationContext:
    """Translation context without translator."""
    return TranslationContext(
        translator=None,
        user_language="ko",
        agent_language="en",
    )
