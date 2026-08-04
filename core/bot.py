import asyncpg
import discord
from discord.ext import commands

EXTENSIONS = [
    "cogs.warehouse",
    "cogs.salary",
    "cogs.finance",
    "cogs.admin",
    "cogs.tasks",
]


class BaseBot(commands.Bot):
    def __init__(self, config):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.config = config
        self.db_pool: asyncpg.Pool | None = None
        self.pending_wd_users: set[int]   = set()
        self.warehouse_cache: dict[str, int] = {}  # {nama_barang: harga_satuan}, refreshed on startup/add

    async def refresh_warehouse_cache(self) -> bool:
        """Reload nama_barang + harga dari DB ke memori supaya /wd tidak perlu query DB
        sebelum merespons (modal harus dijawab <3 detik, tidak bisa di-defer)."""
        from utils.database import get_warehouse_prices
        if not await self.ensure_db():
            return False
        try:
            async with self.db_pool.acquire() as conn:
                self.warehouse_cache = await get_warehouse_prices(conn, self.config)
            return True
        except Exception as e:
            print(f"⚠️  Gagal refresh warehouse cache: {e}")
            return False

    async def ensure_db(self) -> bool:
        if self.db_pool and not self.db_pool._closed:
            return True
        try:
            self.db_pool = await asyncpg.create_pool(
                self.config.DATABASE_URL,
                min_size=1,
                max_size=5,
                command_timeout=60.0,
                max_inactive_connection_lifetime=300.0,
                statement_cache_size=0,
            )
            print("✅ (Re)connected to PostgreSQL!")
            return True
        except Exception as e:
            print(f"❌ DB reconnect gagal: {e}")
            self.db_pool = None
            return False

    async def setup_hook(self):
        from utils.database import init_warehouse_prices, init_role_salaries
        try:
            self.db_pool = await asyncpg.create_pool(
                self.config.DATABASE_URL,
                min_size=1,
                max_size=5,
                command_timeout=60.0,
                max_inactive_connection_lifetime=300.0,
                statement_cache_size=0,
            )
            print("✅ Terkoneksi ke PostgreSQL Supabase!")
            async with self.db_pool.acquire() as conn:
                await init_warehouse_prices(conn, self.config)
                print("✅ Harga warehouse diinisialisasi.")
                await init_role_salaries(conn, self.config)
                print("✅ Data roles diinisialisasi.")
            await self.refresh_warehouse_cache()
            print("✅ Warehouse cache dimuat.")
        except Exception as e:
            print(f"⚠️  Koneksi DB gagal saat startup: {e}")
            print("    Bot tetap jalan — DB akan dicoba reconnect saat command digunakan.")

        for ext in EXTENSIONS:
            await self.load_extension(ext)
            print(f"🔌 Loaded: {ext}")

        await self.tree.sync()

    async def on_ready(self):
        await self.change_presence(status=discord.Status.invisible)
        print(f"👻 Bot [{self.config.BOT_ID}] Siap! Login sebagai: {self.user}")
