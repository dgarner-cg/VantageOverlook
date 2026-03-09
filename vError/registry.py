from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class PublicErrorInfo:
    """Information shown to end-users when they run ?error <code>."""

    code: str
    title: str
    summary: str
    fix: str
    example: Optional[str] = None


PUBLIC_ERROR_REGISTRY: dict[str, PublicErrorInfo] = {
    "SYS-ARG-001": PublicErrorInfo(
        code="SYS-ARG-001",
        title="Missing Required Argument",
        summary="You forgot to include something that command needs.",
        fix="Run the command again and include every required part of the syntax.",
        example="?kick @User spamming",
    ),
    "SYS-ARG-002": PublicErrorInfo(
        code="SYS-ARG-002",
        title="Invalid Argument",
        summary="One of the values you entered could not be understood.",
        fix="Double-check the value you entered and make sure it matches the command's expected format.",
        example="?tempban @User 7d repeated spam",
    ),
    "SYS-CHK-001": PublicErrorInfo(
        code="SYS-CHK-001",
        title="No Permissions",
        summary="You do not have permission to run that command.",
        fix="Ask a server admin or bot owner to grant the right role or permission, or use a command you already have access to.",
    ),
    "SYS-CHK-002": PublicErrorInfo(
        code="SYS-CHK-002",
        title="Bot Missing Permissions",
        summary="The bot does not have the permissions it needs to finish that command.",
        fix="Ask a server admin to update the bot's role permissions and channel overrides.",
    ),
    "SYS-CTX-001": PublicErrorInfo(
        code="SYS-CTX-001",
        title="Server Only Command",
        summary="That command can only be used in a server.",
        fix="Run the command in a server channel instead of DMs.",
    ),
    "SYS-CTX-002": PublicErrorInfo(
        code="SYS-CTX-002",
        title="DM Only Command",
        summary="That command can only be used in DMs with the bot.",
        fix="Open a direct message with the bot and run the command there.",
    ),
    "SYS-CTX-003": PublicErrorInfo(
        code="SYS-CTX-003",
        title="Command Disabled",
        summary="That command is currently disabled.",
        fix="Try again later or contact the bot owners if you believe this command should be available.",
    ),
    "SYS-CD-001": PublicErrorInfo(
        code="SYS-CD-001",
        title="Command Cooldown",
        summary="That command is on cooldown right now.",
        fix="Wait for the cooldown to end, then try the command again.",
    ),
}
