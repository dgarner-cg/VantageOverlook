from .verrors import VErrors
from .safeui import VErrorSafeView


async def setup(bot):
    await bot.add_cog(VErrors(bot))
