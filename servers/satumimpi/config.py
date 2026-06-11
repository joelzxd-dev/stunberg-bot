import os
import dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv.load_dotenv(os.path.join(BASE_DIR, ".env"))

BOT_ID        = "satumimpi"
TOKEN_DISCORD = os.getenv("DISCORD_TOKEN")
DATABASE_URL  = os.getenv("DATABASE_URL")

# --- Table names ---
TABLE_WAREHOUSE    = "satumimpi_warehouse"
TABLE_CASH_BOOK    = "satumimpi_cash_book"
TABLE_TRANSACTIONS = "satumimpi_transactions"
TABLE_DUTY_LOG     = "satumimpi_duty_log"
TABLE_INCOMING_LOG = "satumimpi_incoming_log"
TABLE_ROLES        = "satumimpi_roles"

# --- Channel IDs ---
try:
    ID_CHANNEL_DASHBOARD      = int(os.getenv("ID_CHANNEL_DASHBOARD",      "0"))
    ID_CHANNEL_UANG_MASUK     = int(os.getenv("ID_CHANNEL_UANG_MASUK",     "0"))
    ID_CHANNEL_UANG_KANTOR    = int(os.getenv("ID_CHANNEL_UANG_KANTOR",    "0"))
    ID_CHANNEL_BRANKAS_KELUAR = int(os.getenv("ID_CHANNEL_BRANKAS_KELUAR", "0"))
    ID_CHANNEL_LOG_DUTY       = int(os.getenv("ID_CHANNEL_LOG_DUTY",       "0"))
    ID_CHANNEL_ALERT_GUDANG   = int(os.getenv("ID_CHANNEL_ALERT_GUDANG",   "0"))
except Exception:
    ID_CHANNEL_DASHBOARD = ID_CHANNEL_UANG_MASUK = ID_CHANNEL_UANG_KANTOR = 0
    ID_CHANNEL_BRANKAS_KELUAR = ID_CHANNEL_LOG_DUTY = ID_CHANNEL_ALERT_GUDANG = 0

ID_CHANNEL_FINANCE = 0

# --- Roles ---
ROLES_ADMIN = ["CEO", "BOSS GARAGE", "Manager", "MANAGER", "Board of Manager"]
ROLES_WD    = ["CEO", "BOSS GARAGE", "Manager", "MANAGER", "Board of Manager",
               "MAGANG", "HEAD", "MEKANIK", "Stunberg Crew"]

# --- Display ---
CURRENCY = "Rp"

# --- Items & Prices (seed fallback) ---
HARGA_MODAL = {
    "Repair Kit":   15000,
    "Cleaning Kit":  4000,
    "Tire Kit":     13000,
    "Nitrous":     150000,
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
HAS_WEEKLY_ARCHIVE    = True
HAS_FINANCE_DASHBOARD = False
HAS_LOW_STOCK_ALERT   = True
HAS_MANUAL_SALARY     = False
HAS_SALARY_DB_CACHE   = True
