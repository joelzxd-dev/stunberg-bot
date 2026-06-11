import re
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta

from utils.helpers import is_admin, parse_durasi_ke_menit
from utils.database import get_last_balance, get_role_salaries, refresh_finance


# ==============================================================================
# VIEW: Tombol Cairkan Dana (Gaji)
# ==============================================================================
class PayoutView(discord.ui.View):
    def __init__(self, bot, user: discord.Member, total_gaji: int, rincian: str):
        super().__init__(timeout=None)
        self.bot          = bot
        self.user         = user
        self.total_gaji   = total_gaji
        self.rincian      = rincian
        self.is_processed = False

    @discord.ui.button(label="💸 CAIRKAN DANA (Transfer)", style=discord.ButtonStyle.green)
    async def bayar_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction):
            return await interaction.response.send_message(
                "⛔ Hanya Manager Keuangan yang boleh mencairkan.", ephemeral=True
            )
        if self.is_processed:
            return
        self.is_processed = True
        await interaction.response.defer()

        if not await self.bot.ensure_db():
            self.is_processed = False
            return await interaction.followup.send(
                "❌ Database tidak tersedia saat ini. Coba lagi dalam beberapa menit.",
                ephemeral=True
            )

        config   = self.bot.config
        approver = interaction.user.display_name
        now      = datetime.now()

        try:
            async with self.bot.db_pool.acquire() as conn:
                saldo_kantor = await get_last_balance(conn, config)
                if saldo_kantor < self.total_gaji:
                    self.is_processed = False
                    return await interaction.followup.send(
                        "⚠️ **GAGAL CAIR:** Saldo Kas tidak cukup!"
                    )

                saldo_baru = saldo_kantor - self.total_gaji
                await conn.execute(f"""
                    INSERT INTO {config.TABLE_CASH_BOOK}
                        (tipe, kategori, keterangan, nominal, saldo_akhir)
                    VALUES ('KELUAR', 'GAJI', $1, $2, $3)
                """, f"Gaji Mingguan: {self.user.display_name}", self.total_gaji, saldo_baru)

            if config.ID_CHANNEL_UANG_KANTOR != 0:
                channel_kantor = self.bot.get_channel(config.ID_CHANNEL_UANG_KANTOR)
                if channel_kantor:
                    embed_kantor = discord.Embed(
                        title="💸 LAPORAN GAJI DIBAYARKAN", color=discord.Color.red()
                    )
                    embed_kantor.add_field(name="👤 Penerima",   value=self.user.mention,                             inline=True)
                    embed_kantor.add_field(name="👮 Bendahara",  value=interaction.user.mention,                      inline=True)
                    embed_kantor.add_field(name="💵 Nominal",    value=f"**{config.CURRENCY} {self.total_gaji:,}**",  inline=False)
                    embed_kantor.add_field(name="📝 Keterangan", value=f"```\n{self.rincian}\n```",                   inline=False)
                    embed_kantor.set_footer(text=f"Waktu: {now.strftime('%d/%m/%Y %H:%M WIB')}")
                    await channel_kantor.send(embed=embed_kantor)

            await refresh_finance(self.bot)

            slip_title = "GAJIAN" if config.BOT_ID == "satumimpi" else "SLIP GAJI"
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.blue() if config.BOT_ID == "satumimpi" else discord.Color.green()
            embed.title = f"✅ {slip_title} (LUNAS/PAID)"
            embed.set_footer(text=f"Dicairkan oleh: {approver} | Saldo Terpotong")

            button.label    = "✅ SUDAH DICAIRKAN"
            button.disabled = True
            button.style    = discord.ButtonStyle.grey

            await interaction.edit_original_response(embed=embed, view=self)
            await interaction.followup.send(
                f"💸 Gaji **{self.user.display_name}** sebesar "
                f"**{config.CURRENCY} {self.total_gaji:,}** berhasil dicairkan."
            )

        except Exception as e:
            self.is_processed = False
            await interaction.followup.send(f"❌ Error Database: {e}")


# ==============================================================================
# COG: Salary (Gaji & Duty)
# ==============================================================================
class SalaryCog(commands.Cog):
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

    @app_commands.command(name="cek_gaji", description="Hitung gaji minggu ini")
    @app_commands.describe(
        mekanik="Tag mekanik yang ingin dicek",
        minggu="Nomor minggu (opsional, hanya satumimpi)",
        refresh="Paksa baca ulang log Discord (hanya satumimpi)",
    )
    async def cek_gaji(
        self,
        interaction: discord.Interaction,
        mekanik:  discord.Member = None,
        minggu:   int            = None,
        refresh:  bool           = False,
    ):
        mekanik = mekanik or interaction.user
        await interaction.response.defer()

        config     = self.bot.config
        now        = datetime.now()
        target_yr  = now.year
        current_wk = now.isocalendar()[1]

        if minggu and config.HAS_SALARY_DB_CACHE:
            start_of_week = datetime.strptime(f'{target_yr}-W{minggu}-1', "%Y-W%W-%w")
            target_wk = minggu
        else:
            start_of_week = now - timedelta(days=now.weekday())
            target_wk = current_wk

        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week   = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59)

        total_menit   = 0
        nama_ic       = "Unknown"
        is_data_found = False

        # --- DB cache (satumimpi only) ---
        if config.HAS_SALARY_DB_CACHE and target_wk < current_wk and not refresh:
            async with self.bot.db_pool.acquire() as conn:
                row_db = await conn.fetchrow(f"""
                    SELECT total_menit, nama_ic FROM {config.TABLE_DUTY_LOG}
                    WHERE discord_id = $1 AND minggu_ke = $2 AND tahun = $3
                """, mekanik.display_name, target_wk, target_yr)
                if row_db:
                    total_menit   = row_db['total_menit']
                    nama_ic       = row_db['nama_ic']
                    is_data_found = True

        # --- Scraping Discord ---
        if not is_data_found:
            channel_log = self.bot.get_channel(config.ID_CHANNEL_LOG_DUTY)
            if not channel_log:
                return await interaction.followup.send("❌ Channel Log Duty tidak ditemukan!")

            try:
                history_kwargs: dict = {"limit": None, "after": start_of_week.astimezone()}
                if config.HAS_SALARY_DB_CACHE and minggu:
                    history_kwargs["before"] = end_of_week.astimezone()

                async for message in channel_log.history(**history_kwargs):
                    if not message.embeds:
                        continue
                    desc = message.embeds[0].description or ""

                    if config.HAS_SALARY_DB_CACHE:
                        # satumimpi: cari embed weekly summary
                        if "Total Mingguan:" not in desc:
                            continue
                        match_dc = re.search(r'DiscordID:\s*(.*)', desc)
                        raw_dc   = match_dc.group(1).strip() if match_dc else ""
                        match_id = re.search(r'(\d{17,20})', raw_dc)
                        user_id  = int(match_id.group(1)) if match_id else None

                        if (user_id == mekanik.id) or (mekanik.display_name.lower() in raw_dc.lower()):
                            match_total = re.search(r'Total Mingguan:\s*(.*)', desc)
                            if match_total:
                                total_menit = parse_durasi_ke_menit(match_total.group(1).strip())
                            match_nama = re.search(r'Player Name:\s*(.*)', desc)
                            raw_nama   = match_nama.group(1).strip() if match_nama else "Unknown"
                            nama_ic    = raw_nama.split('(')[0].replace('*', '').strip()
                    else:
                        # cerita: akumulasi per-shift
                        if "Shift Duration:" not in desc:
                            continue
                        match_dc = re.search(r'DiscordID:\s*(.*)', desc)
                        raw_dc   = match_dc.group(1).strip() if match_dc else ""
                        match_id = re.search(r'(\d{17,20})', raw_dc)
                        user_id  = int(match_id.group(1)) if match_id else None

                        if user_id == mekanik.id:
                            match_durasi = re.search(r'Shift Duration:\s*(.*)', desc)
                            teks_durasi  = match_durasi.group(1).strip() if match_durasi else "0 Menit"
                            total_menit += parse_durasi_ke_menit(teks_durasi)

                            match_nama = re.search(r'Player Name:\s*(.*)', desc)
                            raw_nama   = match_nama.group(1).strip() if match_nama else "Unknown"
                            nama_ic    = raw_nama.split('(')[0].strip()

            except Exception as e:
                return await interaction.followup.send(f"❌ Error scraping: {e}")

            # Cache ke DB (satumimpi only)
            if config.HAS_SALARY_DB_CACHE and total_menit > 0:
                async with self.bot.db_pool.acquire() as conn:
                    await conn.execute(f"""
                        INSERT INTO {config.TABLE_DUTY_LOG}
                            (discord_id, nama_ic, total_menit, minggu_ke, tahun)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (discord_id, minggu_ke, tahun)
                        DO UPDATE SET total_menit = EXCLUDED.total_menit,
                                      nama_ic     = EXCLUDED.nama_ic
                    """, mekanik.display_name, nama_ic, total_menit, target_wk, target_yr)

        # --- Perhitungan gaji ---
        total_jam  = total_menit / 60
        jam_bulat  = int(total_jam)
        menit_sisa = total_menit % 60

        async with self.bot.db_pool.acquire() as conn:
            gaji_per_role = await get_role_salaries(conn, config)

        gaji_pokok         = 0
        role_paling_tinggi = "Tidak Ada Role"
        user_roles = [r.name for r in mekanik.roles]
        for role_name, nominal in gaji_per_role.items():
            if role_name in user_roles and nominal > gaji_pokok:
                gaji_pokok         = nominal
                role_paling_tinggi = role_name

        status_gaji = "🟢 Memenuhi Syarat"
        warna       = discord.Color.blue()
        bonus       = 0
        ket_bonus   = "🔴 Tidak ada bonus"

        if total_jam < config.TARGET_MINIMAL:
            gaji_pokok  = 0
            status_gaji = f"🔴 KURANG DARI {config.TARGET_MINIMAL} JAM"
            warna       = discord.Color.red()
            ket_bonus   = "Hangus"
        else:
            if total_jam >= config.TARGET_BONUS_2:
                bonus, ket_bonus, warna = 500000, "✨ BONUS SULTAN", discord.Color.gold()
            elif total_jam >= config.TARGET_BONUS_1:
                bonus, ket_bonus = 200000, "✨ BONUS RAJIN"

        total_terima = gaji_pokok + bonus
        cur          = config.CURRENCY
        slip_title   = "REQUEST GAJI" if config.BOT_ID == "satumimpi" else "SLIP GAJI"

        embed = discord.Embed(
            title=f"🧾 {slip_title}: {mekanik.display_name}", color=warna
        )
        embed.description = f"Periode: **Minggu ke-{target_wk} Tahun {target_yr}**"
        embed.add_field(name="👤 Nama IC",   value=nama_ic,                                  inline=True)
        embed.add_field(name="⏱️ Total Jam", value=f"**{jam_bulat} Jam {menit_sisa} Menit**", inline=True)
        embed.add_field(name="👔 Jabatan",   value=role_paling_tinggi,                        inline=True)
        embed.add_field(name="📊 Status",    value=status_gaji,                               inline=True)

        txt_duit  = f"Gaji Pokok : {cur} {gaji_pokok:,}\nBonus      : {cur} {bonus:,} ({ket_bonus})\n"
        txt_duit += f"---------------------------\n**TOTAL      : {cur} {total_terima:,}**"
        embed.add_field(name="💰 Rincian", value=f"```\n{txt_duit}\n```", inline=False)

        if total_terima > 0:
            await interaction.followup.send(
                embed=embed, view=PayoutView(self.bot, mekanik, total_terima, txt_duit)
            )
        else:
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="cek_duty", description="Leaderboard Duty (Scrape Channel Log)")
    async def cek_duty(self, interaction: discord.Interaction):
        await interaction.response.defer()

        config = self.bot.config
        now    = datetime.now()
        start_of_week = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        channel_log = self.bot.get_channel(config.ID_CHANNEL_LOG_DUTY)
        if not channel_log:
            return await interaction.followup.send("❌ Channel Log Duty tidak ditemukan!")

        leaderboard_data: dict[str, int] = {}

        try:
            async for message in channel_log.history(
                limit=None, after=start_of_week.astimezone()
            ):
                if not message.embeds:
                    continue
                desc = message.embeds[0].description or ""
                if "Shift Duration:" not in desc:
                    continue

                match_nama   = re.search(r'Player Name:\s*(.*)', desc)
                raw_nama     = match_nama.group(1).strip() if match_nama else "Unknown"
                nama_ic      = raw_nama.split('(')[0].replace('*', '').strip()

                match_durasi = re.search(r'Shift Duration:\s*(.*)', desc)
                teks_durasi  = match_durasi.group(1).strip() if match_durasi else "0 Menit"
                durasi       = parse_durasi_ke_menit(teks_durasi)

                if durasi > 0:
                    leaderboard_data[nama_ic] = leaderboard_data.get(nama_ic, 0) + durasi

        except Exception as e:
            return await interaction.followup.send(f"❌ Error membaca history: {e}")

        if not leaderboard_data:
            return await interaction.followup.send("💤 Belum ada yang duty minggu ini.")

        sorted_data = sorted(leaderboard_data.items(), key=lambda x: x[1], reverse=True)

        embed = discord.Embed(title="⏱️ LEADERBOARD DUTY MINGGUAN", color=discord.Color.blue())
        embed.description = (
            f"Periode: **{start_of_week.strftime('%d/%m')}** s/d Sekarang\n"
            f"*(Data Live dari Channel)*"
        )

        text_list, part = "", 1
        for i, (nama, total_mnt) in enumerate(sorted_data, 1):
            jam      = total_mnt // 60
            sisa_mnt = total_mnt % 60
            icon     = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
            entry    = f"{icon} **{nama}**\n└ ⏳ {jam} Jam {sisa_mnt} Menit\n"

            if len(text_list) + len(entry) > 1000:
                embed.add_field(name=f"Top Rajin (Part {part})", value=text_list, inline=False)
                text_list = entry
                part += 1
            else:
                text_list += entry

        if text_list:
            embed.add_field(
                name=f"Top Rajin (Part {part})" if part > 1 else "Top Rajin",
                value=text_list, inline=False
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="leaderboard", description="Ranking Karyawan berdasarkan omzet/qty")
    @app_commands.describe(bulan="Bulan (1-12)", tahun="Tahun", urutkan="omzet/qty")
    @app_commands.choices(urutkan=[
        app_commands.Choice(name="Total Uang",   value="omzet"),
        app_commands.Choice(name="Total Barang", value="qty"),
    ])
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        bulan:   int = None,
        tahun:   int = None,
        urutkan: app_commands.Choice[str] = None,
    ):
        config = self.bot.config
        now    = datetime.now()
        bln    = bulan if bulan else now.month
        thn    = tahun if tahun else now.year
        mode   = urutkan.value if urutkan else "omzet"

        sort_sql = "SUM(total_harga)" if mode == "omzet" else "SUM(qty)"
        sql = f"""
            SELECT penyetor, SUM(qty) as t_qty, SUM(total_harga) as t_omzet
            FROM {config.TABLE_TRANSACTIONS}
            WHERE EXTRACT(MONTH FROM tanggal) = $1 AND EXTRACT(YEAR FROM tanggal) = $2
            GROUP BY penyetor
            ORDER BY {sort_sql} DESC
            LIMIT 10
        """

        await interaction.response.send_message("🏆 Mengambil data...", ephemeral=True)
        async with self.bot.db_pool.acquire() as conn:
            rows = await conn.fetch(sql, bln, thn)

        if not rows:
            return await interaction.edit_original_response(content="📉 Data kosong.")

        cur   = config.CURRENCY
        embed = discord.Embed(title=f"🏆 LEADERBOARD {bln}/{thn}", color=discord.Color.gold())
        text  = ""
        for i, r in enumerate(rows, 1):
            icon    = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
            val_qty = f"**{r['t_qty']}**"             if mode == "qty"   else str(r['t_qty'])
            val_omz = f"**{cur} {r['t_omzet']:,}**"  if mode == "omzet" else f"{cur} {r['t_omzet']:,}"
            text += f"{icon} **{r['penyetor']}**\n└ 📦 {val_qty} | 💰 {val_omz}\n\n"

        embed.add_field(name="TOP 10", value=text)
        await interaction.edit_original_response(content=None, embed=embed)


async def setup(bot):
    await bot.add_cog(SalaryCog(bot))
