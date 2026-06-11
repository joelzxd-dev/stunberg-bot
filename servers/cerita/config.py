import os
import dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv.load_dotenv(os.path.join(BASE_DIR, ".env"))

BOT_ID        = "cerita"
TOKEN_DISCORD = os.getenv("DISCORD_TOKEN")
DATABASE_URL  = os.getenv("DATABASE_URL")

# --- Table names ---
TABLE_WAREHOUSE    = "cerita_warehouse"
TABLE_CASH_BOOK    = "cerita_cash_book"
TABLE_TRANSACTIONS = "cerita_transactions"
TABLE_DUTY_LOG     = "cerita_duty_log"
TABLE_INCOMING_LOG = "cerita_incoming_log"
TABLE_ROLES        = "cerita_roles"

# --- Channel IDs ---
try:
    ID_CHANNEL_DASHBOARD      = int(os.getenv("ID_CHANNEL_DASHBOARD",      "0"))
    ID_CHANNEL_UANG_MASUK     = int(os.getenv("ID_CHANNEL_UANG_MASUK",     "0"))
    ID_CHANNEL_BRANKAS_KELUAR = int(os.getenv("ID_CHANNEL_BRANKAS_KELUAR", "0"))
    ID_CHANNEL_LOG_DUTY       = int(os.getenv("ID_CHANNEL_LOG_DUTY",       "0"))
    ID_CHANNEL_FINANCE        = int(os.getenv("ID_CHANNEL_FINANCE",        "0"))
except Exception:
    ID_CHANNEL_DASHBOARD = ID_CHANNEL_UANG_MASUK = ID_CHANNEL_BRANKAS_KELUAR = 0
    ID_CHANNEL_LOG_DUTY = ID_CHANNEL_FINANCE = 0

ID_CHANNEL_UANG_KANTOR  = 0
ID_CHANNEL_ALERT_GUDANG = 0

# --- Roles ---
ROLES_ADMIN = [
    "CEO", "Wakil CEO", "Asisten Wakil CEO",
    "Manager", "MANAGER", "Sekretaris Manager", "Head Mechanic",
]
ROLES_WD = [
    "CEO", "Wakil CEO", "Asisten Wakil CEO",
    "Manager", "MANAGER", "Sekretaris Manager",
    "Magang", "Junior", "Head Mechanic", "Senior Mechanic", "Senior",
]

# --- Display ---
CURRENCY = "$"

# --- Items & Prices (seed fallback) ---
HARGA_MODAL = {
    "ADV Repair Kit": 200,
    "Repair Kit":     100,
    "Cleaning Kit":    50,
    "Stancer Kit":    350,
}

# --- Salary (seed fallback) ---
GAJI_POKOK_ROLES = {
    "MANAGER": 560000,
    "HEAD":    490000,
    "MEKANIK": 420000,
    "MAGANG":  350000,
}
TARGET_MINIMAL = 15
TARGET_BONUS_1 = 17
TARGET_BONUS_2 = 41

# --- Feature flags ---
HAS_WEEKLY_ARCHIVE    = False
HAS_FINANCE_DASHBOARD = True
HAS_LOW_STOCK_ALERT   = False
HAS_MANUAL_SALARY     = True
HAS_SALARY_DB_CACHE   = False
