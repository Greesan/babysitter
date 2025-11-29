"""
Hook implementations for Agent SDK.
Handles user prompts, tool usage tracking, and session management.
"""
# Import hooks as they're implemented
try:
    from src.hooks.user_prompt import user_prompt_submit_hook
    __all__ = ["user_prompt_submit_hook"]
except ImportError:
    __all__ = []

try:
    from src.hooks.post_tool_use import post_tool_use_hook
    __all__.append("post_tool_use_hook")
except ImportError:
    pass

try:
    from src.hooks.session_start import session_start_hook
    __all__.append("session_start_hook")
except ImportError:
    pass
