from __future__ import annotations

from collections import Counter
from typing import Optional

import discord
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, pagify

from .models import ErrorKind
from .registry import PUBLIC_ERROR_REGISTRY
from .reporter import ErrorReporter
from .utils import (
    fixable_error_reply,
    internal_lookup_embed,
    not_found_embed,
    public_code_for_error,
    public_error_embed,
    resolve_system_prefix,
)


class VErrors(commands.Cog):
    """Shared public/private error handling system for Vantage-related cogs."""

    __author__ = "OpenAI"
    __version__ = "1.0.0"

    default_global_settings = {
        "internal_errors": [],
        "max_internal_errors": 250,
    }

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=7028459110, force_registration=True)
        self.config.register_global(**self.default_global_settings)
        self.reporter = ErrorReporter(bot, self.config)

    def format_help_for_context(self, ctx: commands.Context) -> str:
        pre = super().format_help_for_context(ctx)
        return f"{pre}\n\nVersion: {self.__version__}"

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Handle unhandled command errors with public codes or internal reports.

        This listener intentionally backs off when a command or cog already has
        its own error handler.
        """

        if ctx.command and ctx.command.has_error_handler():
            return
        if ctx.cog and getattr(ctx.cog, "has_error_handler", lambda: False)():
            return
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.UserFeedbackCheckFailure):
            return

        public_code = public_code_for_error(error)
        if public_code is not None:
            try:
                await ctx.send(embed=fixable_error_reply(ctx, error, public_code))
            except discord.HTTPException:
                pass
            return

        system = resolve_system_prefix(ctx)
        await self.reporter.report_command_exception(ctx, error, system)

    async def report_interaction_error(
        self,
        *,
        interaction: discord.Interaction,
        error: Exception,
        system: str = "SYS",
        command_name: Optional[str] = None,
        location: Optional[str] = None,
    ) -> str:
        """Public helper for views/buttons/modals to report unexpected errors."""

        return await self.reporter.report_generic_exception(
            system=system,
            kind=ErrorKind.UI,
            summary=f"{type(error).__name__}: {error}",
            error=error,
            interaction=interaction,
            location=location,
            command_name=command_name,
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            user_id=interaction.user.id if interaction.user else None,
        )

    async def report_task_error(
        self,
        *,
        error: Exception,
        system: str = "SYS",
        command_name: Optional[str] = None,
        location: Optional[str] = None,
        guild_id: Optional[int] = None,
        channel_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> str:
        """Public helper for background tasks/listeners to report failures."""

        return await self.reporter.report_generic_exception(
            system=system,
            kind=ErrorKind.TASK,
            summary=f"{type(error).__name__}: {error}",
            error=error,
            interaction=None,
            location=location,
            command_name=command_name,
            guild_id=guild_id,
            channel_id=channel_id,
            user_id=user_id,
        )

    @commands.command(name="error")
    async def error_lookup(self, ctx: commands.Context, code: str) -> None:
        """Look up a public error code or check an internal incident code."""

        code = code.upper().strip()
        info = PUBLIC_ERROR_REGISTRY.get(code)
        if info is not None:
            await ctx.send(embed=public_error_embed(info))
            return

        entries = await self.config.internal_errors()
        if any(entry["code"] == code for entry in entries):
            await ctx.send(embed=internal_lookup_embed(code))
            return

        await ctx.send(embed=not_found_embed(code))

    @commands.group(name="errors", invoke_without_command=True)
    @commands.is_owner()
    async def errors_group(self, ctx: commands.Context) -> None:
        """Owner-only commands for browsing internal error reports."""

        await ctx.send_help()

    @errors_group.command(name="latest")
    async def errors_latest(self, ctx: commands.Context, limit: int = 10) -> None:
        """Show the most recent internal error reports."""

        limit = max(1, min(limit, 15))
        entries = (await self.config.internal_errors())[:limit]
        if not entries:
            await ctx.send("No internal errors are currently stored.")
            return

        lines = []
        for entry in entries:
            lines.append(
                f"`{entry['code']}` • {entry.get('system', 'SYS')} • "
                f"{entry.get('command_name') or 'Unknown command'} • "
                f"{entry.get('summary', 'Unknown error')[:60]}"
            )
        embed = discord.Embed(title="Recent Internal Errors", description="\n".join(lines), color=discord.Color.red())
        await ctx.send(embed=embed)

    @errors_group.command(name="show")
    async def errors_show(self, ctx: commands.Context, code: str) -> None:
        """Show details for one stored internal error."""

        code = code.upper().strip()
        entries = await self.config.internal_errors()
        match = next((entry for entry in entries if entry["code"] == code), None)
        if match is None:
            await ctx.send(f"I couldn't find an internal error with code `{code}`.")
            return

        embed = discord.Embed(title=f"Internal Error {code}", color=discord.Color.red())
        embed.add_field(name="System", value=match.get("system") or "Unknown")
        embed.add_field(name="Kind", value=match.get("kind") or "Unknown")
        embed.add_field(name="Command", value=match.get("command_name") or "Unknown", inline=False)
        embed.add_field(name="Location", value=match.get("location") or "Unknown", inline=False)
        embed.add_field(name="Summary", value=match.get("summary") or "Unknown", inline=False)
        meta = (
            f"Guild: `{match.get('guild_id')}`\n"
            f"Channel: `{match.get('channel_id')}`\n"
            f"User: `{match.get('user_id')}`"
        )
        embed.add_field(name="Context", value=meta, inline=False)
        await ctx.send(embed=embed)

    @errors_group.command(name="traceback")
    async def errors_traceback(self, ctx: commands.Context, code: Optional[str] = None) -> None:
        """Show the stored traceback for an internal error code.

        This is the owner-only replacement path that pairs well with disabling
        Red's built-in traceback command if you want one unified workflow.
        """

        entries = await self.config.internal_errors()
        if not entries:
            await ctx.send("No internal errors are currently stored.")
            return

        target = None
        if code is None:
            target = entries[0]
        else:
            code = code.upper().strip()
            target = next((entry for entry in entries if entry["code"] == code), None)

        if target is None:
            await ctx.send(f"I couldn't find an internal error with code `{code}`.")
            return

        header = f"Traceback for `{target['code']}`\n"
        pages = list(pagify(target.get("traceback_text", "No traceback stored."), page_length=1800)) or ["No traceback stored."]
        for index, page in enumerate(pages, start=1):
            prefix = header if index == 1 else f"Traceback for `{target['code']}` (cont.)\n"
            await ctx.send(f"{prefix}{box(page, lang='py')}")

    @errors_group.command(name="search")
    async def errors_search(self, ctx: commands.Context, *, query: str) -> None:
        """Search stored internal errors by code, command, system, or summary."""

        lowered = query.lower()
        matches = []
        for entry in await self.config.internal_errors():
            haystack = " ".join(
                str(entry.get(key, ""))
                for key in ("code", "system", "kind", "command_name", "location", "summary")
            ).lower()
            if lowered in haystack:
                matches.append(entry)
            if len(matches) >= 10:
                break

        if not matches:
            await ctx.send(f"No internal errors matched `{query}`.")
            return

        lines = [
            f"`{entry['code']}` • {entry.get('command_name') or 'Unknown'} • {entry.get('summary', 'Unknown')[:70]}"
            for entry in matches
        ]
        embed = discord.Embed(title=f"Search results for {query}", description="\n".join(lines), color=discord.Color.red())
        await ctx.send(embed=embed)

    @errors_group.command(name="stats")
    async def errors_stats(self, ctx: commands.Context) -> None:
        """Show a quick breakdown of stored internal error kinds."""

        entries = await self.config.internal_errors()
        if not entries:
            await ctx.send("No internal errors are currently stored.")
            return

        by_kind = Counter(entry.get("kind", "UNK") for entry in entries)
        by_system = Counter(entry.get("system", "SYS") for entry in entries)
        embed = discord.Embed(title="Internal Error Stats", color=discord.Color.red())
        embed.add_field(
            name="By Kind",
            value="\n".join(f"`{kind}`: {count}" for kind, count in by_kind.most_common()) or "None",
        )
        embed.add_field(
            name="By System",
            value="\n".join(f"`{system}`: {count}" for system, count in by_system.most_common()) or "None",
        )
        embed.set_footer(text=f"Stored reports: {len(entries)}")
        await ctx.send(embed=embed)

    @errors_group.command(name="clear")
    async def errors_clear(self, ctx: commands.Context) -> None:
        """Clear stored internal error reports."""

        await self.config.internal_errors.set([])
        await ctx.send("Cleared stored internal error reports.")

    @errors_group.command(name="maxstored")
    async def errors_maxstored(self, ctx: commands.Context, amount: int) -> None:
        """Set how many internal reports to keep in storage."""

        amount = max(25, min(amount, 1000))
        await self.config.max_internal_errors.set(amount)
        await ctx.send(f"Now storing up to `{amount}` internal error reports.")
