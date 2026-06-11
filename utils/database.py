import discord
from datetime import datetime


async def get_role_salaries(conn, config) -> dict:
    """Return {role_name: base_salary} from DB, fallback ke config jika tabel kosong."""
    rows = await conn.fetch(
        f"SELECT role_name, base_salary FROM {config.TABLE_ROLES} WHERE base_salary > 0"
    )
    if rows:
        return {row['role_name']: row['base_salary'] for row in rows}
    return dict(config.GAJI_POKOK_ROLES)


async def init_role_salaries(conn, config) -> None:
    """Seed tabel roles dengan nilai dari config jika belum ada."""
    for role_name, gaji in config.GAJI_POKOK_ROLES.items():
        await conn.execute(f"""
            INSERT INTO {config.TABLE_ROLES} (role_name, base_salary)
            VALUES ($1, $2)
            ON CONFLICT (role_name) DO NOTHING
        """, role_name, gaji)


async def get_warehouse_prices(conn, config) -> dict:
    rows = await conn.fetch(
        f"SELECT nama_barang, harga_satuan FROM {config.TABLE_WAREHOUSE}"
    )
    return {row['nama_barang']: row['harga_satuan'] for row in rows}


async def init_warehouse_prices(conn, config) -> None:
    await conn.execute(f"""
        ALTER TABLE {config.TABLE_WAREHOUSE}
        ADD COLUMN IF NOT EXISTS harga_satuan INTEGER NOT NULL DEFAULT 0
    """)
    for nama, harga in config.HARGA_MODAL.items():
        await conn.execute(f"""
            UPDATE {config.TABLE_WAREHOUSE}
            SET harga_satuan = $1
            WHERE nama_barang = $2 AND harga_satuan = 0
        """, harga, nama)


async def get_last_balance(conn, config) -> int:
    row = await conn.fetchrow(
        f"SELECT saldo_akhir FROM {config.TABLE_CASH_BOOK} ORDER BY id DESC LIMIT 1"
    )
    return row['saldo_akhir'] if row else 0


async def update_stock(bot, conn, config, nama_barang: str, perubahan: int) -> int:
    current = await conn.fetchval(
        f"SELECT stok FROM {config.TABLE_WAREHOUSE} WHERE nama_barang = $1", nama_barang
    )
    if current is None:
        await conn.execute(
            f"INSERT INTO {config.TABLE_WAREHOUSE} (nama_barang, stok) VALUES ($1, 0)",
            nama_barang
        )
        current = 0

    baru = current + perubahan
    if baru < 0:
        raise ValueError(f"Stok Kurang! Sisa: {current}")

    await conn.execute(
        f"UPDATE {config.TABLE_WAREHOUSE} SET stok = $1, last_update = NOW() WHERE nama_barang = $2",
        baru, nama_barang
    )

    # Low-stock alert (satumimpi only)
    if config.HAS_LOW_STOCK_ALERT and perubahan < 0 and baru <= 250 and config.ID_CHANNEL_ALERT_GUDANG != 0:
        channel_alert = bot.get_channel(config.ID_CHANNEL_ALERT_GUDANG)
        if channel_alert:
            guild        = channel_alert.guild
            target_roles = ["MANAGER", "BOSS GARAGE", "CEO"]
            roles_to_tag = [r.mention for r in guild.roles if r.name in target_roles]
            tag_text     = " ".join(roles_to_tag) if roles_to_tag else "@here"

            embed_alert = discord.Embed(
                title="🚨 PERINGATAN GUDANG (STOK KRITIS)", color=discord.Color.red()
            )
            embed_alert.description = "Segera lakukan `/biaya restock` untuk mencegah kehabisan barang!"
            embed_alert.add_field(name="📦 Nama Barang", value=f"**{nama_barang}**", inline=True)
            embed_alert.add_field(name="📉 Sisa Stok",   value=f"**{baru} pcs**",    inline=True)
            await channel_alert.send(
                content=f"{tag_text} Tolong cek gudang segera!", embed=embed_alert
            )

    return baru


async def refresh_dashboard(bot) -> None:
    config = bot.config
    if config.ID_CHANNEL_DASHBOARD == 0:
        return
    channel = bot.get_channel(config.ID_CHANNEL_DASHBOARD)
    if not channel:
        return

    async with bot.db_pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT nama_barang, stok FROM {config.TABLE_WAREHOUSE} ORDER BY nama_barang ASC"
        )

    embed = discord.Embed(title="🏭 GUDANG STUNBERG (LIVE)", color=discord.Color.red())
    embed.description = f"Last Update: **{datetime.now().strftime('%H:%M WIB')}**"

    for row in rows:
        nama, jml = row['nama_barang'], row['stok']
        icon = "🟢" if jml > 500 else "🟡" if jml > 250 else "🔴"
        embed.add_field(name=f"📦 {nama}", value=f"```\n{jml} pcs {icon}\n```", inline=False)

    embed.set_footer(text="⚡")

    try:
        msgs     = [m async for m in channel.history(limit=100)]
        last_msg = next(
            (m for m in msgs
             if m.author == bot.user and m.embeds and "GUDANG STUNBERG" in m.embeds[0].title),
            None
        )
        if last_msg:
            await last_msg.edit(embed=embed)
        else:
            await channel.send(embed=embed)
    except Exception as e:
        print(f"Gagal refresh dashboard: {e}")


async def refresh_finance(bot) -> None:
    config = bot.config
    if not config.HAS_FINANCE_DASHBOARD or config.ID_CHANNEL_FINANCE == 0:
        return
    channel = bot.get_channel(config.ID_CHANNEL_FINANCE)
    if not channel:
        return

    async with bot.db_pool.acquire() as conn:
        saldo   = await get_last_balance(conn, config)
        history = await conn.fetch(
            f"SELECT to_char(tanggal, 'DD/MM') as tgl, tipe, keterangan, nominal "
            f"FROM {config.TABLE_CASH_BOOK} ORDER BY id DESC LIMIT 5"
        )

    text_hist = ""
    for r in history:
        icon = "🟢" if "MASUK" in r['tipe'] else "🔴"
        ket  = r['keterangan'][:20] + ".." if len(r['keterangan']) > 20 else r['keterangan']
        text_hist += f"`{r['tgl']}` {icon} **{config.CURRENCY} {r['nominal']:,}**: {ket}\n"

    color = discord.Color.green() if saldo > 1000000 else discord.Color.red()
    embed = discord.Embed(title="💰 STUNBERG FINANCE (LIVE)", color=color)
    embed.description = f"Last Update: **{datetime.now().strftime('%H:%M:%S WIB')}**"
    embed.add_field(name="💵 SALDO SAAT INI",    value=f"# **{config.CURRENCY} {saldo:,}**",   inline=False)
    embed.add_field(name="📜 5 Mutasi Terakhir", value=text_hist or "Belum ada data",           inline=False)

    try:
        msgs     = [m async for m in channel.history(limit=5)]
        last_msg = next((m for m in msgs if m.author == bot.user), None)
        if last_msg:
            await last_msg.edit(embed=embed)
        else:
            await channel.send(embed=embed)
    except Exception:
        pass
