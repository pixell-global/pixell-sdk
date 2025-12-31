"""Example: Complete Plan Mode Agent with Translation

This example demonstrates how to build an agent using the new SDK features:
- AgentServer with FastAPI-style decorators
- Plan mode phases (clarification, discovery, selection, preview)
- Translation interface for i18n support
- SSE streaming for real-time progress

Run with:
    cd examples/plan_mode_agent
    python main.py
"""

import asyncio
from pixell.sdk import AgentServer, MessageContext, ResponseContext
from pixell.sdk.plan_mode import (
    Question,
    QuestionType,
    QuestionOption,
    DiscoveredItem,
    SearchPlanPreview,
)
from pixell.sdk.translation import Translator

# =============================================================================
# Translation Implementation (Agent pays for tokens)
# =============================================================================


class MockTranslator(Translator):
    """Mock translator for demonstration.

    In production, implement this with your own LLM:

        class OpenAITranslator(Translator):
            async def translate(self, text, from_lang, to_lang):
                response = await openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": f"Translate: {text}"}]
                )
                return response.choices[0].message.content
    """

    async def translate(self, text: str, from_lang: str, to_lang: str) -> str:
        # Mock: just return original text with language marker
        return f"[{to_lang}] {text}"

    async def detect_language(self, text: str) -> str:
        # Mock: always detect as English
        return "en"


# =============================================================================
# Agent Server Configuration
# =============================================================================

server = AgentServer(
    agent_id="reddit-research-agent",
    name="Reddit Research Agent",
    description="Research subreddits and gather insights",
    port=9999,
    translator=MockTranslator(),
    plan_mode_config={
        "phases": ["clarification", "discovery", "selection", "preview"],
        "discovery_type": "subreddits",
    },
)

# In-memory state for managing async responses
# (Agent manages their own async waiting pattern)
response_waiters: dict[str, asyncio.Future] = {}


# =============================================================================
# Message Handler
# =============================================================================


@server.on_message
async def handle_message(ctx: MessageContext):
    """Handle incoming messages and guide through plan mode phases."""

    plan = ctx.plan_mode
    trans = ctx.translation

    # Translate user input if needed
    user_message = ctx.text
    if trans and trans.needs_translation:
        user_message = await trans.translate_from_user(user_message)

    await ctx.emit_status("working", "Analyzing your request...")

    # -------------------------------------------------------------------------
    # Phase 1: Clarification
    # -------------------------------------------------------------------------
    await ctx.emit_status("working", "I need some information to help you...")

    clarification_id = await plan.request_clarification([
        Question(
            id="topic",
            type=QuestionType.FREE_TEXT,
            question="What topic would you like to research?",
            header="Topic",
            placeholder="e.g., machine learning, fitness, cooking",
        ),
        Question(
            id="depth",
            type=QuestionType.SINGLE_CHOICE,
            question="How deep should the research be?",
            header="Depth",
            options=[
                QuestionOption(id="quick", label="Quick scan", description="Top 5 subreddits"),
                QuestionOption(id="moderate", label="Moderate", description="Top 15 subreddits"),
                QuestionOption(id="deep", label="Deep dive", description="Top 30+ subreddits"),
            ],
        ),
    ])

    # Create waiter for clarification response
    waiter = asyncio.Future()
    response_waiters[clarification_id] = waiter

    # Wait for user response (agent manages async)
    # In real implementation, this would be handled by the respond handler
    # and the message handler would exit here, to be resumed later
    print(f"Waiting for clarification response: {clarification_id}")


# =============================================================================
# Respond Handler
# =============================================================================


@server.on_respond
async def handle_respond(ctx: ResponseContext):
    """Handle user responses to clarification/selection/preview."""

    plan = ctx.plan_mode
    trans = ctx.translation

    if ctx.response_type == "clarification":
        # User answered clarification questions
        plan.set_clarification_response(ctx.answers, ctx.clarification_id)

        topic = ctx.answers.get("topic", "general")
        ctx.answers.get("depth", "moderate")

        await ctx.emit_status("working", f"Searching for {topic} subreddits...")

        # -----------------------------------------------------------------
        # Phase 2: Discovery
        # -----------------------------------------------------------------
        # Simulate discovering subreddits
        discovered = [
            DiscoveredItem(
                id="r/machinelearning",
                name="r/machinelearning",
                description="A subreddit for machine learning news and discussion",
                metadata={"subscribers": 2500000, "posts_per_day": 50},
            ),
            DiscoveredItem(
                id="r/learnmachinelearning",
                name="r/learnmachinelearning",
                description="Learning resources for ML beginners",
                metadata={"subscribers": 500000, "posts_per_day": 30},
            ),
            DiscoveredItem(
                id="r/deeplearning",
                name="r/deeplearning",
                description="Deep learning papers and discussions",
                metadata={"subscribers": 150000, "posts_per_day": 15},
            ),
        ]

        await plan.emit_discovery(discovered, "subreddits", message=f"Found {len(discovered)} relevant subreddits")

        # -----------------------------------------------------------------
        # Phase 3: Selection
        # -----------------------------------------------------------------
        selection_id = await plan.request_selection(
            min_select=1,
            max_select=5,
            message="Select the subreddits you want to monitor",
        )

        response_waiters[selection_id] = asyncio.Future()
        print(f"Waiting for selection response: {selection_id}")

    elif ctx.response_type == "selection":
        # User selected items
        plan.set_selection_response(ctx.selected_ids, ctx.selection_id)

        selected_items = plan.get_selected_items()
        await ctx.emit_status("working", f"Preparing research plan for {len(selected_items)} subreddits...")

        # -----------------------------------------------------------------
        # Phase 4: Preview
        # -----------------------------------------------------------------
        preview = SearchPlanPreview(
            user_intent=plan.user_answers.get("topic", "research"),
            search_keywords=["discussion", "news", "tutorial"],
            hashtags=[],
            follower_min=0,
            follower_max=0,
            user_answers=plan.user_answers,
            message="Here's the research plan. Review and approve to start.",
        )

        await plan.emit_preview(preview)

        response_waiters[preview.plan_id] = asyncio.Future()
        print(f"Waiting for plan approval: {preview.plan_id}")

    elif ctx.response_type == "plan":
        # User approved/rejected plan
        plan.set_plan_approval(ctx.approved, ctx.plan_id)

        if ctx.approved:
            # -----------------------------------------------------------------
            # Phase 5: Execution
            # -----------------------------------------------------------------
            await plan.start_execution("Starting research...")

            # Simulate execution
            await ctx.emit_status("working", "Collecting posts from selected subreddits...")
            await asyncio.sleep(1)

            await ctx.emit_status("working", "Analyzing sentiment and topics...")
            await asyncio.sleep(1)

            # Complete with results
            result = {
                "subreddits_analyzed": len(plan.selected_ids),
                "posts_collected": 150,
                "top_topics": ["deep learning", "transformers", "reinforcement learning"],
                "sentiment": "positive",
            }

            # Translate results if needed
            if trans and trans.needs_translation:
                result["summary"] = await trans.translate_to_user(
                    "Research completed successfully. Found active discussions about machine learning topics."
                )

            await plan.complete(result, message="Research completed!")

        else:
            await ctx.emit_status("working", "Plan cancelled. Let me know if you want to try again.")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("Starting Reddit Research Agent on port 9999...")
    print("Agent card: http://localhost:9999/.well-known/agent.json")
    print("Health: http://localhost:9999/health")
    server.run()
