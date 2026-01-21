"""
PixellSDK - Build and deploy AI agent applications

This package provides:
- CLI tool: `pixell` command for creating, building, and deploying agents
- Runtime SDK: Import from pixell.sdk for agent development

Example usage:

    # CLI
    $ pixell init my-agent
    $ pixell build
    $ pixell deploy

    # Runtime (in agent code)
    from pixell.sdk import UserContext, TaskConsumer

    class MyAgent:
        async def execute(self, context: UserContext):
            profile = await context.get_user_profile()
            return {"result": ...}
"""

__version__ = "0.4.22"
__author__ = "Pixell Team"
__email__ = "dev@pixell.global"
