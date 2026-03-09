from __future__ import annotations

from typing import Optional

import discord
from redbot.core import commands

from .registry import PUBLIC_ERROR_REGISTRY, PublicErrorInfo


def resolve_system_prefix(ctx: commands.Context) -> str:
    """Pick a short system prefix for the command's cog."""

    cog_name = (ctx.cog.qualified_name if ctx.cog else "").lower()
    if cog_name.startswith("vhelp"):
        return "VH"
    if cog_name.startswith("vmod") or cog_name.startswith("vantage"):
        return "VM"
    return "SYS"


def public_code_for_error(error: Exception) -> Optional[str]:
    """Return a stable public-facing error code for user/admin-fixable issues."""

    if isinstance(error, commands.MissingRequiredArgument):
        return "SYS-ARG-001"
    if isinstance(error, commands.BadUnionArgument):
        return "SYS-ARG-002"
    if isinstance(error, (commands.BadArgument, commands.UserInputError)):
        return "SYS-ARG-002"
    if isinstance(error, commands.BotMissingPermissions):
        return "SYS-CHK-002"
    if isinstance(error, commands.CheckFailure):
        return "SYS-CHK-001"
    if isinstance(error, commands.NoPrivateMessage):
        return "SYS-CTX-001"
    if isinstance(error, commands.PrivateMessageOnly):
        return "SYS-CTX-002"
    if isinstance(error, commands.DisabledCommand):
        return "SYS-CTX-003"
    if isinstance(error, commands.CommandOnCooldown):
        return "SYS-CD-001"
    return None


def usage_for_command(ctx: commands.Context) -> str:
    """Return a readable command usage line."""

    if not ctx.command:
        return f"{ctx.clean_prefix}help"
    signature = ctx.command.signature or ""
    base = f"{ctx.clean_prefix}{ctx.command.qualified_name}"
    return f"{base} {signature}".strip()


def missing_argument_name(error: Exception) -> Optional[str]:
    if isinstance(error, commands.MissingRequiredArgument):
        return getattr(error.param, "name", None)
    return None


def internal_error_embed(command_display: str, code: str) -> discord.Embed:
    embed = discord.Embed(
        title="Internal Error",
        description=(
            f"Hmm, looks like `{command_display}` has failed. I'll let the devs know.\n\n"
            f"**Error code:** `{code}`"
        ),
        color=discord.Color.red(),
    )
    return embed


def public_error_embed(info: PublicErrorInfo) -> discord.Embed:
    embed = discord.Embed(title=f"Error {info.code}", color=discord.Color.orange())
    embed.add_field(name="What happened", value=info.summary, inline=False)
    embed.add_field(name="How to fix it", value=info.fix, inline=False)
    if info.example:
        embed.add_field(name="Example", value=f"```\n{info.example}\n```", inline=False)
    return embed


def internal_lookup_embed(code: str) -> discord.Embed:
    return discord.Embed(
        title=f"Error {code}",
        description=(
            "If you got this error, it means that an internal error with Vantage has occurred.\n"
            "Our developers should have been notified of this error and will fix it as soon as possible.\n\n"
            "We apologise for the inconvenience this may cause."
        ),
        color=discord.Color.red(),
    )


def not_found_embed(code: str) -> discord.Embed:
    return discord.Embed(
        title="Unknown Error Code",
        description=f"I couldn't find any information for `{code}`.",
        color=discord.Color.orange(),
    )


def fixable_error_reply(ctx: commands.Context, error: Exception, code: str) -> discord.Embed:
    """Build the user-facing embed for a known, fixable command error."""

    usage = usage_for_command(ctx)
    if isinstance(error, commands.CheckFailure):
        description = (
            "Looks like you can't run this command.\n"
            f"For more info, run `{ctx.clean_prefix}error {code}`"
        )
        title = "No Permissions Error"
    elif isinstance(error, commands.MissingRequiredArgument):
        missing = missing_argument_name(error) or "something"
        description = (
            "Looks like you forgot something in that command.\n"
            f"Try:\n```\n{usage}\n```\n"
            f"Missing: `{missing}`\n"
            f"For more info on this error, run `{ctx.clean_prefix}error {code}`"
        )
        title = "Missing Something Error"
    elif isinstance(error, commands.CommandOnCooldown):
        retry_after = getattr(error, "retry_after", None)
        extra = f"\nTry again in about `{round(retry_after, 1)}` seconds." if retry_after is not None else ""
        description = (
            "Looks like that command is on cooldown right now."
            f"{extra}\nFor more info, run `{ctx.clean_prefix}error {code}`"
        )
        title = "Cooldown Error"
    elif isinstance(error, commands.BotMissingPermissions):
        missing = ", ".join(getattr(error, "missing_permissions", [])) or "unknown permissions"
        description = (
            "Looks like the bot is missing permissions it needs to finish that command.\n"
            f"Missing permissions: `{missing}`\n"
            f"For more info, run `{ctx.clean_prefix}error {code}`"
        )
        title = "Bot Permissions Error"
    else:
        description = (
            "Looks like something in that command needs fixing.\n"
            f"Try:\n```\n{usage}\n```\n"
            f"For more info on this error, run `{ctx.clean_prefix}error {code}`"
        )
        title = "Command Error"

    return discord.Embed(title=title, description=description, color=discord.Color.orange())


def command_display(ctx: commands.Context) -> str:
    if ctx.command:
        return f"{ctx.clean_prefix}{ctx.command.qualified_name}"
    return f"{ctx.clean_prefix}command"
