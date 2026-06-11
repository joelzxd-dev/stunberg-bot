import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import is_admin
from utils.database import get_last_balance, update_stock, refresh_dashboard, refresh_finance


class FinanceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not await self.bot.ensure_db():
            await interaction.response.send_message(
                "❌ Database sedang tidak tersedia. Coba lagi dalam beberapa menit.",
                ephemeral=True
            )
            return False
        return True

    biaya = app_commands.Group(name="biaya", description="Manajemen Keuangan")

    @biaya.command(name="restock", description="Catat pembelian stok & masukkan ke gudang")
    @app_commands.describe(barang="Nama barang", jumlah="Jumlah item", harga="Harga per item")
    async def restock(
        self,
        interaction: discord.Interaction,
        barang: str,
        jumlah: int,
        harga:  int,
    ):
        if not is_admin(interaction):
            return await interaction.response.send_message(
                "⛔ Khusus Manager/Admin.", ephemeral=True
            )

        config = self.bot.config
        total  = jumlah * harga
        await interaction.response.defer()

        async with self.bot.db_pool.acquire() as conn:
            saldo = await get_last_balance(conn, config)
            if saldo < total:
                return await interaction.followup.send(
                    f"⚠️ Saldo Kurang! Saldo: **{config.CURRENCY} {saldo:,}**, "
                    f"butuh **{config.CURRENCY} {total:,}**"
                )

            await conn.execute(f"""
                INSERT INTO {config.TABLE_CASH_BOOK} (tipe, kategori, keterangan, nominal, saldo_akhir)
                VALUES ('KELUAR', 'RESTOCK', $1, $2, $3)
            """, f"Beli {jumlah} {barang}", total, saldo - total)

            await update_stock(self.bot, conn, config, barang, jumlah)

        await refresh_dashboard(self.bot)
        await refresh_finance(self.bot)
        await interaction.followup.send(
            f"✅ Restock **{jumlah} pcs {barang}** "
            f"({config.CURRENCY} {total:,}) berhasil dicatat & masuk gudang."
        )

    @biaya.command(name="gaji", description="Catat pengeluaran gaji manual ke buku kas")
    @app_commands.describe(kategori="Kategori gaji", total="Jumlah", ket="Keterangan")
    async def gaji(
        self,
        interaction: discord.Interaction,
        kategori: str,
        total:    int,
        ket:      str,
    ):
        if not self.bot.config.HAS_MANUAL_SALARY:
            return await interaction.response.send_message(
                "❌ Command ini tidak tersedia untuk bot ini.", ephemeral=True
            )
        if not is_admin(interaction):
            return await interaction.response.send_message(
                "⛔ Khusus Manager/Admin.", ephemeral=True
            )

        config = self.bot.config
        await interaction.response.defer()

        async with self.bot.db_pool.acquire() as conn:
            saldo = await get_last_balance(conn, config)
            if saldo < total:
                return await interaction.followup.send(
                    f"⚠️ Saldo Kurang! Saldo: **{config.CURRENCY} {saldo:,}**, "
                    f"butuh **{config.CURRENCY} {total:,}**"
                )

            await conn.execute(f"""
                INSERT INTO {config.TABLE_CASH_BOOK} (tipe, kategori, keterangan, nominal, saldo_akhir)
                VALUES ('KELUAR', 'GAJI', $1, $2, $3)
            """, f"[{kategori}] {ket}", total, saldo - total)

        await refresh_finance(self.bot)
        await interaction.followup.send(
            f"✅ Gaji Total {config.CURRENCY} {total:,} dicatat."
        )


async def setup(bot):
    await bot.add_cog(FinanceCog(bot))
