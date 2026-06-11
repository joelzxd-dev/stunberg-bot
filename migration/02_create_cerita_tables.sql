-- ============================================================
-- LANGKAH 2: Jalankan di database SATUMIMPI (database utama)
-- Buat semua tabel cerita yang masih kosong
-- ============================================================

CREATE TABLE IF NOT EXISTS cerita_roles (
  id          SERIAL PRIMARY KEY,
  role_name   TEXT UNIQUE NOT NULL,
  base_salary INTEGER NOT NULL DEFAULT 0,
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cerita_warehouse (
  id           SERIAL PRIMARY KEY,
  nama_barang  TEXT UNIQUE NOT NULL,
  stok         INTEGER NOT NULL DEFAULT 0,
  harga_satuan INTEGER NOT NULL DEFAULT 0,
  last_update  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cerita_cash_book (
  id          SERIAL PRIMARY KEY,
  tipe        TEXT NOT NULL,
  kategori    TEXT NOT NULL,
  keterangan  TEXT NOT NULL,
  nominal     INTEGER NOT NULL,
  saldo_akhir INTEGER NOT NULL,
  tanggal     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cerita_transactions (
  id          SERIAL PRIMARY KEY,
  nama_barang TEXT NOT NULL
    REFERENCES cerita_warehouse(nama_barang)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  qty         INTEGER NOT NULL,
  total_harga INTEGER NOT NULL,
  penyetor    TEXT NOT NULL,
  approver    TEXT NOT NULL,
  tanggal     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cerita_incoming_log (
  id               SERIAL PRIMARY KEY,
  nama_barang      TEXT NOT NULL
    REFERENCES cerita_warehouse(nama_barang)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  jumlah           INTEGER NOT NULL,
  penanggung_jawab TEXT NOT NULL,
  waktu            TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cerita_duty_log (
  id          SERIAL PRIMARY KEY,
  discord_id  TEXT NOT NULL,
  nama_ic     TEXT NOT NULL,
  total_menit INTEGER NOT NULL DEFAULT 0,
  minggu_ke   INTEGER NOT NULL,
  tahun       INTEGER NOT NULL,
  UNIQUE (discord_id, minggu_ke, tahun)
);

-- Seed roles
INSERT INTO cerita_roles (role_name, base_salary) VALUES
  ('MANAGER', 560000),
  ('HEAD',    490000),
  ('MEKANIK', 420000),
  ('MAGANG',  350000)
ON CONFLICT (role_name) DO NOTHING;
