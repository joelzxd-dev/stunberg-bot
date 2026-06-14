import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

from utils.helpers import is_admin
from utils.database import (
    get_warehouse_prices, get_last_balance,
    update_stock, refresh_dashboard, refresh_finance,
)


# ==============================================================================
# VIEW: Tombol Approve / Tolak WD (shared)
# ==============================================================================
class WDApprovalView(discord.ui.View):
    def __init__(self, bot, data_transaksi, requester, total_uang):
        super().__init__(timeout=600)
        self.bot            = bot
        self.data_transaksi = data_transaksi
        self.requester      = requester
        self.total_uang     = total_uang
        self.is_processing  = False
        self.message        = None

    def unlock_user(self):
        self.bot.pending_wd_users.discard(self.requester.id)

    async def on_timeout(self):
        self.unlock_user()
        self.clear_items()
        if self.message:
            embed = self.message.embeds[0]
            embed.color = discord.Color.dark_grey()
            embed.title = "⌛ WD EXPIRED"
            embed.set_field_at(0, name="Status", value="Ditolak Otomatis", inline=False)
            try:
                await self.message.edit(embed=embed, view=self)
            except Exception as e:
                print(f"Gagal update pesan timeout: {e}")

    @discord.ui.button(label="✅ TERIMA (Approve)", style=discord.ButtonStyle.green)
    async def approve_btn(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not is_admin(interaction):
            return await interaction.response.send_message(
                "⛔ Hanya Manager yang dapat Approve.", ephemeral=True
            )
        if self.is_processing:
            return
        self.is_processing = True
        await interaction.response.defer()

        if not await self.bot.ensure_db():
            self.is_processing = False
            return await interaction.followup.send(
                "❌ Database tidak tersedia saat ini. Coba lagi dalam beberapa menit.",
                ephemeral=True
            )

        config       = self.bot.config
        manager_name = interaction.user.display_name
        now          = datetime.now()

        try:
            async with self.bot.db_pool.acquire() as conn:
                async with conn.transaction():
                    tot_items = 0
                    for nama, jumlah, harga in self.data_transaksi:
                        if jumlah > 0:
                            tot_items += jumlah
                            await update_stock(self.bot, conn, config, nama, -jumlah)
                            await conn.execute(f"""
                                INSERT INTO {config.TABLE_TRANSACTIONS}
                                    (nama_barang, qty, total_harga, penyetor, approver)
                                VALUES ($1, $2, $3, $4, $5)
                            """, nama, jumlah, jumlah * harga,
                                self.requester.display_name, manager_name)

                    saldo_now = await get_last_balance(conn, config)
                    saldo_new = saldo_now + self.total_uang
                    desc_kas  = f"Setoran WD: {self.requester.display_name} ({tot_items} items)"
                    await conn.execute(f"""
                        INSERT INTO {config.TABLE_CASH_BOOK}
                            (tipe, kategori, keterangan, nominal, saldo_akhir)
                        VALUES ('MASUK', 'WD', $1, $2, $3)
                    """, desc_kas, self.total_uang, saldo_new)

            await refresh_dashboard(self.bot)
            await refresh_finance(self.bot)

            cur      = config.CURRENCY
            desc_log = "".join(
                [f"• **{n}**: {j} pcs ({cur} {j*h:,})\n"
                 for n, j, h in self.data_transaksi if j > 0]
            )
            embed_log = discord.Embed(title="💰 STRUK SETORAN DITERIMA", color=discord.Color.green())
            embed_log.add_field(name="👤 Penyetor",       value=self.requester.mention,      inline=True)
            embed_log.add_field(name="👮 Penerima (ACC)", value=interaction.user.mention,     inline=True)
            embed_log.add_field(name="📦 Rincian",        value=desc_log,                    inline=False)
            embed_log.add_field(name="💵 TOTAL",          value=f"**{cur} {self.total_uang:,}**", inline=False)
            embed_log.set_footer(
                text=f"Mekanik: {self.requester.display_name} | "
                     f"Tercatat: {now.strftime('%d/%m %H:%M')}"
            )

            if config.ID_CHANNEL_UANG_MASUK:
                c = interaction.guild.get_channel(config.ID_CHANNEL_UANG_MASUK)
                if c: await c.send(embed=embed_log)

            if config.ID_CHANNEL_BRANKAS_KELUAR:
                c = interaction.guild.get_channel(config.ID_CHANNEL_BRANKAS_KELUAR)
                if c: await c.send(embed=embed_log)

            embed = interaction.message.embeds[0]
            embed.color = discord.Color.green()
            embed.title = "✅ WD DISETUJUI"
            embed.set_field_at(0, name="Status", value=f"ACC by {manager_name}", inline=False)

            self.unlock_user()
            self.clear_items()
            await interaction.edit_original_response(embed=embed, view=self)
            await interaction.channel.send(f"{self.requester.mention}, WD Berhasil di-ACC!")
            self.stop()

        except Exception as e:
            self.is_processing = False
            await interaction.followup.send(f"❌ Error Database: {e}", ephemeral=True)

    @discord.ui.button(label="❌ TOLAK", style=discord.ButtonStyle.red)
    async def reject_btn(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not is_admin(interaction):
            return await interaction.response.send_message("⛔ Hanya Manager.", ephemeral=True)
        if self.is_processing:
            return
        self.is_processing = True

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = "❌ WD DITOLAK"
        embed.set_field_at(
            0, name="Status",
            value=f"Ditolak by {interaction.user.display_name}", inline=False
        )

        self.unlock_user()
        self.clear_items()
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()


# ==============================================================================
# MODAL: Input jumlah WD — diisi dinamis dari tabel warehouse
# ==============================================================================
class WDModal(discord.ui.Modal, title="Ajukan Penjualan (WD)"):
    def __init__(self, bot, items_harga: list, requester: discord.Member):
        super().__init__()
        self.bot_ref     = bot
        self.items_harga = items_harga  # [(nama, harga), ...]
        self.requester   = requester
        config           = bot.config

        for nama, harga in items_harga[:5]:  # Discord modal maks 5 input
            placeholder = (
                f"Jumlah pcs (@ {config.CURRENCY} {harga:,}/pcs)" if harga > 0
                else "Masukkan jumlah pcs"
            )
            self.add_item(discord.ui.TextInput(
                label=nama,
                placeholder=placeholder,
                required=False,
                max_length=6,
            ))

    async def on_submit(self, interaction: discord.Interaction):
        if self.requester.id in self.bot_ref.pending_wd_users:
            return await interaction.response.send_message(
                "⛔ Anda masih punya WD Pending.", ephemeral=True
            )

        data = []
        for i, (nama, harga) in enumerate(self.items_harga[:5]):
            val = self.children[i].value.strip()
            try:
                qty = int(val) if val else 0
            except ValueError:
                qty = 0
            if qty > 0:
                data.append((nama, qty, harga))

        if not data:
            return await interaction.response.send_message(
                "❌ Isi setidaknya satu barang.", ephemeral=True
            )

        self.bot_ref.pending_wd_users.add(self.requester.id)
        config = self.bot_ref.config
        cur    = config.CURRENCY
        total  = sum(q * h for _, q, h in data)
        desc   = "".join(f"• **{n}**: {q} pcs ({cur} {q*h:,})\n" for n, q, h in data)

        embed = discord.Embed(title="⏳ PENDING APPROVAL", color=discord.Color.orange())
        embed.add_field(name="Status",           value="Menunggu Manager...",    inline=False)
        embed.add_field(name="Pengaju",          value=self.requester.mention,   inline=True)
        embed.add_field(name="Total Uang Fisik", value=f"**{cur} {total:,}**",  inline=True)
        embed.add_field(name="Rincian Barang",   value=desc,                     inline=False)
        embed.set_footer(text="Manager: Cek fisik sebelum ACC.")

        view = WDApprovalView(self.bot_ref, data, self.requester, total)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()


# ==============================================================================
# COG: Dynamic Warehouse — barang diambil dari DB, tidak perlu hardcode
# ==============================================================================
class WarehouseCog(commands.Cog):
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

    # ---- autocomplete: ambil nama_barang dari tabel warehouse ----
    async def _item_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        if not self.bot.db_pool:
            return []
        config = self.bot.config
        async with self.bot.db_pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT nama_barang FROM {config.TABLE_WAREHOUSE} ORDER BY nama_barang"
            )
        return [
            app_commands.Choice(name=r['nama_barang'], value=r['nama_barang'])
            for r in rows if current.lower() in r['nama_barang'].lower()
        ][:25]

    @app_commands.command(name="wd", description="Ajukan Penjualan")
    async def wd(self, interaction: discord.Interaction):
        if interaction.user.id in self.bot.pending_wd_users:
            return await interaction.response.send_message(
                "⛔ Anda masih punya WD Pending.", ephemeral=True
            )

        config = self.bot.config
        async with self.bot.db_pool.acquire() as conn:
            harga_db = await get_warehouse_prices(conn, config)

        def harga(nama: str) -> int:
            h = harga_db.get(nama, 0)
            return h if h > 0 else config.HARGA_MODAL.get(nama, 0)

        items_harga = [(nama, harga(nama)) for nama in sorted(harga_db.keys())]

        if not items_harga:
            return await interaction.response.send_message(
                "❌ Tidak ada barang di gudang.", ephemeral=True
            )

        modal = WDModal(self.bot, items_harga, interaction.user)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="add", description="Masukan barang fisik ke Gudang (Admin Only)")
    @app_commands.autocomplete(item=_item_autocomplete)
    async def add(self, interaction: discord.Interaction, item: str, jumlah: int):
        if not is_admin(interaction):
            return await interaction.response.send_message(
                "⛔ Khusus Manager/Admin.", ephemeral=True
            )
        if jumlah <= 0:
            return await interaction.response.send_message(
                "❌ Jumlah harus lebih dari 0.", ephemeral=True
            )

        await interaction.response.defer()
        config     = self.bot.config
        admin_name = interaction.user.display_name

        try:
            async with self.bot.db_pool.acquire() as conn:
                async with conn.transaction():
                    stok_baru = await update_stock(self.bot, conn, config, item, jumlah)
                    await conn.execute(f"""
                        INSERT INTO {config.TABLE_INCOMING_LOG}
                            (nama_barang, jumlah, penanggung_jawab)
                        VALUES ($1, $2, $3)
                    """, item, jumlah, admin_name)

            await refresh_dashboard(self.bot)

            embed = discord.Embed(title="📦 STOK DITAMBAHKAN", color=discord.Color.blue())
            embed.add_field(name="Barang",          value=item,               inline=True)
            embed.add_field(name="Jumlah",          value=f"+{jumlah} pcs",   inline=True)
            embed.add_field(name="Total di Gudang", value=f"{stok_baru} pcs", inline=False)
            embed.set_footer(text=f"Diinput oleh: {admin_name}")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Error Database: {e}")


async def setup(bot):
    await bot.add_cog(WarehouseCog(bot))
