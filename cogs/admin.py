import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import is_admin
from utils.database import refresh_dashboard, refresh_finance


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="start_dashboard", description="Inisialisasi embed gudang live")
    async def start_dashboard(self, interaction: discord.Interaction):
        if not await self.bot.ensure_db():
            return await interaction.response.send_message(
                "❌ Database tidak tersedia.", ephemeral=True
            )
        await interaction.response.send_message("✅ Dashboard DB Live")
        await refresh_dashboard(self.bot)

    @app_commands.command(name="start_finance", description="Inisialisasi embed finance live")
    async def start_finance(self, interaction: discord.Interaction):
        if not self.bot.config.HAS_FINANCE_DASHBOARD:
            return await interaction.response.send_message(
                "❌ Tidak tersedia untuk bot ini.", ephemeral=True
            )
        if not await self.bot.ensure_db():
            return await interaction.response.send_message(
                "❌ Database tidak tersedia.", ephemeral=True
            )
        await interaction.response.send_message("✅ Finance DB Live")
        await refresh_finance(self.bot)

    @app_commands.command(name="reset_wd_lock", description="Paksa buka WD lock user (Admin Only)")
    @app_commands.describe(user="User yang mau dibuka locknya")
    async def reset_lock(self, interaction: discord.Interaction, user: discord.Member):
        if not is_admin(interaction):
            return await interaction.response.send_message(
                "⛔ Khusus Manager/Admin.", ephemeral=True
            )

        if user.id in self.bot.pending_wd_users:
            self.bot.pending_wd_users.discard(user.id)
            await interaction.response.send_message(
                f"✅ Lock WD **{user.display_name}** berhasil dibuka."
            )
        else:
            await interaction.response.send_message(
                f"ℹ️ **{user.display_name}** tidak sedang terkunci.", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
