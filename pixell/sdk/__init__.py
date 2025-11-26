"""
PixellSDK Runtime - Import this in your agent code

Example:
    from pixell.sdk import UserContext, TaskConsumer

    class MyAgent:
        async def execute(self, context: UserContext):
            profile = await context.get_user_profile()
            return {"result": ...}

Note: SDK components will be implemented in subsequent phases.
"""

# SDK components will be added as they are implemented
__all__ = []
