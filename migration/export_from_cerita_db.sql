-- ============================================================
-- Jalankan di database LAMA cerita
-- Supabase → SQL Editor → copy hasil query → paste ke DB baru
-- ============================================================

-- 1. cerita_warehouse (dari tabel gudang)
SELECT 'INSERT INTO cerita_warehouse (nama_barang, stok, harga_satuan) VALUES ('
  || quote_literal(nama_barang) || ', '
  || stok || ', '
  || harga_satuan
  || ') ON CONFLICT (nama_barang) DO UPDATE SET stok = EXCLUDED.stok, harga_satuan = EXCLUDED.harga_satuan;'
FROM gudang
ORDER BY id;

-- 2. cerita_cash_book (dari tabel buku_kas)
SELECT 'INSERT INTO cerita_cash_book (id, tipe, kategori, keterangan, nominal, saldo_akhir, tanggal) VALUES ('
  || id || ', '
  || quote_literal(tipe) || ', '
  || quote_literal(kategori) || ', '
  || quote_literal(keterangan) || ', '
  || nominal || ', '
  || saldo_akhir || ', '
  || quote_literal(tanggal::text)
  || ');'
FROM buku_kas
ORDER BY id;

-- 3. cerita_transactions (dari tabel transaksi)
SELECT 'INSERT INTO cerita_transactions (id, nama_barang, qty, total_harga, penyetor, approver, tanggal) VALUES ('
  || id || ', '
  || quote_literal(nama_barang) || ', '
  || qty || ', '
  || total_harga || ', '
  || quote_literal(penyetor) || ', '
  || quote_literal(approver) || ', '
  || quote_literal(tanggal::text)
  || ');'
FROM transaksi
ORDER BY id;

-- 4. cerita_duty_log (dari tabel log_duty)
SELECT 'INSERT INTO cerita_duty_log (id, discord_id, nama_ic, total_menit, minggu_ke, tahun, tanggal_log) VALUES ('
  || id || ', '
  || quote_literal(discord_id) || ', '
  || quote_literal(nama_ic) || ', '
  || total_menit || ', '
  || minggu_ke || ', '
  || tahun || ', '
  || quote_literal(COALESCE(tanggal_log, NOW())::text)
  || ') ON CONFLICT (discord_id, minggu_ke, tahun) DO NOTHING;'
FROM log_duty
ORDER BY id;

-- 5. cerita_incoming_log (dari tabel log_masuk)
SELECT 'INSERT INTO cerita_incoming_log (id, nama_barang, jumlah, penanggung_jawab, waktu) VALUES ('
  || id || ', '
  || quote_literal(nama_barang) || ', '
  || jumlah || ', '
  || quote_literal(penanggung_jawab) || ', '
  || quote_literal(COALESCE(waktu, NOW())::text)
  || ');'
FROM log_masuk
ORDER BY id;
