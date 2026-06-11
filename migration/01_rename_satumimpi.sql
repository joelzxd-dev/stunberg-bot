-- ============================================================
-- LANGKAH 1: Jalankan di database SATUMIMPI (database utama)
-- Supabase → SQL Editor → paste & run
-- ============================================================

-- Rename tabel lama ke nama baru
ALTER TABLE gudang     RENAME TO satumimpi_warehouse;
ALTER TABLE buku_kas   RENAME TO satumimpi_cash_book;
ALTER TABLE transaksi  RENAME TO satumimpi_transactions;
ALTER TABLE log_duty   RENAME TO satumimpi_duty_log;
ALTER TABLE log_masuk  RENAME TO satumimpi_incoming_log;

-- Pastikan kolom harga_satuan ada (mungkin sudah ada)
ALTER TABLE satumimpi_warehouse
  ADD COLUMN IF NOT EXISTS harga_satuan INTEGER NOT NULL DEFAULT 0;

-- Tambah Foreign Key constraints
ALTER TABLE satumimpi_transactions
  ADD CONSTRAINT fk_satumimpi_transactions_warehouse
  FOREIGN KEY (nama_barang)
  REFERENCES satumimpi_warehouse(nama_barang)
  ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE satumimpi_incoming_log
  ADD CONSTRAINT fk_satumimpi_incoming_log_warehouse
  FOREIGN KEY (nama_barang)
  REFERENCES satumimpi_warehouse(nama_barang)
  ON UPDATE CASCADE ON DELETE RESTRICT;

-- Buat tabel roles satumimpi
CREATE TABLE IF NOT EXISTS satumimpi_roles (
  id          SERIAL PRIMARY KEY,
  role_name   TEXT UNIQUE NOT NULL,
  base_salary INTEGER NOT NULL DEFAULT 0,
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO satumimpi_roles (role_name, base_salary) VALUES
  ('MANAGER', 560000),
  ('HEAD',    490000),
  ('MEKANIK', 420000),
  ('MAGANG',  350000)
ON CONFLICT (role_name) DO NOTHING;
