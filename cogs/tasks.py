import re
import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta

from utils.helpers import parse_durasi_ke_menit


class TasksCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.task_auto_closing.is_running(): self.task_auto_closing.start()
        if not self.task_auto_mvp.is_running():     self.task_auto_mvp.start()
        if self.bot.config.HAS_WEEKLY_ARCHIVE:
            if not self.task_weekly_archive.is_running(): self.task_weekly_archive.start()

    def cog_unload(self):
        self.task_auto_closing.cancel()
        self.task_auto_mvp.cancel()
        if self.bot.config.HAS_WEEKLY_ARCHIVE:
            self.task_weekly_archive.cancel()

    # ------------------------------------------------------------------
    # TASK 1: Auto-Closing Harian (jam 23:59)
    # ------------------------------------------------------------------
    @tasks.loop(minutes=1)
    async def task_auto_closing(self):
        config = self.bot.config
        now    = datetime.now()
        if now.hour != 23 or now.minute != 59:
            return
        if config.ID_CHANNEL_UANG_MASUK == 0:
            return
        channel = self.bot.get_channel(config.ID_CHANNEL_UANG_MASUK)
        if not channel:
            return

        try:
            async with self.bot.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    f"SELECT SUM(total_harga) as omzet, SUM(qty) as qty "
                    f"FROM {config.TABLE_TRANSACTIONS} WHERE tanggal = CURRENT_DATE"
                )

            omzet = row['omzet'] or 0
            qty   = row['qty']   or 0

            if qty > 0:
                embed = discord.Embed(
                    title="📕 LAPORAN HARI INI", color=discord.Color.dark_red()
                )
                embed.add_field(name="Tanggal",         value=now.strftime("%d/%m/%Y"))
                embed.add_field(name="Total Transaksi", value=f"{qty} items")
                embed.add_field(name="Total Omzet",     value=f"{config.CURRENCY} {omzet:,}")
                embed.set_footer(text="System Auto-Close")
                await channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Auto Close Error: {e}")

    # ------------------------------------------------------------------
    # TASK 2: Auto-Announce MVP Bulanan (tanggal 1, jam 00:xx)
    # ------------------------------------------------------------------
    @tasks.loop(hours=1)
    async def task_auto_mvp(self):
        config = self.bot.config
        now    = datetime.now()
        if now.day != 1 or now.hour != 0:
            return
        if config.ID_CHANNEL_UANG_MASUK == 0:
            return
        channel = self.bot.get_channel(config.ID_CHANNEL_UANG_MASUK)
        if not channel:
            return

        last_month = now - timedelta(days=1)
        bln, thn   = last_month.month, last_month.year
        nama_bln   = last_month.strftime("%B %Y")

        try:
            async with self.bot.db_pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT penyetor, SUM(total_harga) as omzet
                    FROM {config.TABLE_TRANSACTIONS}
                    WHERE EXTRACT(MONTH FROM tanggal) = $1
                      AND EXTRACT(YEAR  FROM tanggal) = $2
                    GROUP BY penyetor ORDER BY omzet DESC LIMIT 5
                """, bln, thn)

            if rows:
                mvp = rows[0]
                embed = discord.Embed(
                    title=f"👑 MVP BULAN {nama_bln.upper()}", color=discord.Color.gold()
                )
                embed.description = (
                    f"Selamat kepada **{mvp['penyetor']}**!\n"
                    f"Kontribusi: **{config.CURRENCY} {mvp['omzet']:,}**"
                )
                txt_top = ""
                for i, r in enumerate(rows, 1):
                    icon     = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
                    txt_top += f"{icon} **{r['penyetor']}**: {config.CURRENCY} {r['omzet']:,}\n"
                embed.add_field(name="Top 5 Leaderboard", value=txt_top)
                await channel.send(content="@everyone", embed=embed)

        except Exception as e:
            print(f"❌ MVP Error: {e}")

    # ------------------------------------------------------------------
    # TASK 3: Auto-Archive Duty Mingguan (satumimpi only, setiap Senin)
    # ------------------------------------------------------------------
    @tasks.loop(hours=24)
    async def task_weekly_archive(self):
        config = self.bot.config
        now    = datetime.now()
        if now.weekday() != 0:
            return

        print("📦 Memulai Auto-Archive Mingguan...")
        target_date = now - timedelta(days=1)
        target_wk   = target_date.isocalendar()[1]
        target_yr   = target_date.year

        start_of_week = (target_date - timedelta(days=target_date.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59)

        channel_log  = self.bot.get_channel(config.ID_CHANNEL_LOG_DUTY)
        archive_data: dict = {}

        async for message in channel_log.history(
            limit=None,
            after=start_of_week.astimezone(),
            before=end_of_week.astimezone()
        ):
            if not message.embeds:
                continue
            desc = message.embeds[0].description or ""
            if "Shift Duration:" not in desc:
                continue

            match_id = re.search(r'(\d{17,20})', desc)
            if not match_id:
                continue
            uid = match_id.group(1)

            match_durasi = re.search(r'Shift Duration:\s*(.*)', desc)
            durasi       = parse_durasi_ke_menit(match_durasi.group(1)) if match_durasi else 0

            match_nama = re.search(r'Player Name:\s*(.*)', desc)
            raw_nama   = (
                match_nama.group(1).split('(')[0].replace('*', '').strip()
                if match_nama else "Unknown"
            )

            if uid not in archive_data:
                archive_data[uid] = {'nama': raw_nama, 'menit': 0}
            archive_data[uid]['menit'] += durasi

        async with self.bot.db_pool.acquire() as conn:
            for uid, data in archive_data.items():
                member = self.bot.get_user(int(uid))
                d_name = member.display_name if member else f"User-{uid}"
                await conn.execute(f"""
                    INSERT INTO {config.TABLE_DUTY_LOG}
                        (discord_id, nama_ic, total_menit, minggu_ke, tahun)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (discord_id, minggu_ke, tahun)
                    DO UPDATE SET total_menit = EXCLUDED.total_menit,
                                  nama_ic     = EXCLUDED.nama_ic
                """, d_name, data['nama'], data['menit'], target_wk, target_yr)

        print(f"✅ Arsip Minggu {target_wk}/{target_yr} Berhasil Disimpan!")


async def setup(bot):
    await bot.add_cog(TasksCog(bot))
