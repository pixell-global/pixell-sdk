"""
Schedule Proposal Test Agent

A simple agent that demonstrates the emit_schedule_proposal() feature.
When asked to schedule a task, it proposes a schedule for user approval.

Run with:
    python main.py

Test with:
    curl -X POST http://localhost:8080/ \
      -H "Content-Type: application/json" \
      -H "Accept: text/event-stream" \
      -d '{
        "jsonrpc": "2.0",
        "method": "message/stream",
        "params": {
          "message": {
            "role": "user",
            "parts": [{"type": "text", "text": "Schedule a daily report every morning"}]
          }
        },
        "id": "test-1"
      }'
"""

from datetime import datetime, timedelta
from pixell.sdk import AgentServer, MessageContext


server = AgentServer(
    agent_id="schedule-test-agent",
    name="Schedule Test Agent",
    description="Test agent for schedule proposal feature",
    plan_mode_config={
        "phases": ["schedule_proposal"],
    },
)


def generate_next_runs_preview(count: int = 5) -> list[str]:
    """Generate preview of next run times (weekdays at 9 AM)."""
    runs = []
    current = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    if current <= datetime.now():
        current += timedelta(days=1)

    while len(runs) < count:
        # Skip weekends
        if current.weekday() < 5:  # Monday=0, Friday=4
            runs.append(current.isoformat())
        current += timedelta(days=1)

    return runs


@server.on_message
async def handle_message(ctx: MessageContext):
    """Handle incoming messages."""
    # Extract text from message parts
    message_text = ""
    if ctx.message and ctx.message.parts:
        for part in ctx.message.parts:
            if hasattr(part, "text"):
                message_text += part.text
            elif isinstance(part, dict) and part.get("type") == "text":
                message_text += part.get("text", "")

    message_lower = message_text.lower()
    plan = ctx.plan_mode

    # Detect scheduling intent
    scheduling_keywords = [
        "schedule",
        "every",
        "daily",
        "weekly",
        "recurring",
        "automated",
        "remind",
    ]
    has_scheduling_intent = any(kw in message_lower for kw in scheduling_keywords)

    if has_scheduling_intent:
        await ctx.emit_status("working", "Analyzing your scheduling request...")

        # Propose a schedule - this emits the schedule_proposal event
        proposal_id = await plan.emit_schedule_proposal(
            name="Automated Task",
            prompt=message_text,  # Use original message as prompt
            schedule="0 9 * * 1-5",
            schedule_display="Every weekday at 9:00 AM",
            schedule_type="cron",
            description="This task will run automatically based on your request",
            rationale="Based on your message, I detected a scheduling intent and am proposing a weekday schedule",
            timezone="America/New_York",
            next_runs_preview=generate_next_runs_preview(5),
        )

        # Log proposal ID for debugging
        print(f"Schedule proposal emitted with ID: {proposal_id}")

        # Note: In a real workflow, the agent would wait for user response
        # via on_respond handler. For this test, we just show the proposal.
        # The user can then confirm/edit/cancel via the UI, which calls the
        # orchestrator's schedule API directly.
    else:
        # Regular response - complete immediately
        await plan.complete(
            result={"echo": message_text},
            message=(
                f"I received your message: '{message_text[:100] if message_text else '(empty)'}'. "
                "To test scheduling, try saying 'schedule this task daily' or 'remind me every morning'"
            ),
        )


if __name__ == "__main__":
    import uvicorn

    print("Starting Schedule Proposal Test Agent on http://localhost:8080")
    print("Test with: curl -X POST http://localhost:8080/ ...")
    uvicorn.run(server.app, host="0.0.0.0", port=8080)
