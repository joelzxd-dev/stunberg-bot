-- ============================================================
-- Jalankan di DB BARU setelah semua data di-import
-- Supaya SERIAL sequence tidak bentrok dengan ID yang sudah ada
-- ============================================================

SELECT setval('satumimpi_cash_book_id_seq',    (SELECT MAX(id) FROM satumimpi_cash_book));
SELECT setval('satumimpi_transactions_id_seq', (SELECT MAX(id) FROM satumimpi_transactions));
SELECT setval('satumimpi_duty_log_id_seq',     (SELECT MAX(id) FROM satumimpi_duty_log));
SELECT setval('satumimpi_incoming_log_id_seq', (SELECT MAX(id) FROM satumimpi_incoming_log));

SELECT setval('cerita_cash_book_id_seq',    (SELECT MAX(id) FROM cerita_cash_book));
SELECT setval('cerita_transactions_id_seq', (SELECT MAX(id) FROM cerita_transactions));
SELECT setval('cerita_duty_log_id_seq',     (SELECT MAX(id) FROM cerita_duty_log));
SELECT setval('cerita_incoming_log_id_seq', (SELECT MAX(id) FROM cerita_incoming_log));
